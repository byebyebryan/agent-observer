#!/usr/bin/env python3
"""Bounded remote-proof SDK pipeline qualification over trusted local IPC.

V3.6 named trial mode measures one 500- or 2,000-row variant per fresh process,
for three anchored-clock generations and four detached local facade copies per
generation. The ABBA controller serializes full, working, working, full trials
under the shared lock and persists each process result before proceeding.
Functional acceptance is target/proof/hash/DTO/cleanup; public channel counters
are phase-by-phase diagnostics and do not enforce cross-peer equality. The only timed workload is
one public Reader.watch_admitted event per generation plus local facade copies;
copies are not additional SDK deliveries. Ordinary Mesh proof/line deadlines
remain unchanged. Timed trials require the exact approved Observer/Mesh pair.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import gc
import hashlib
import importlib.util
import json
import os
import socket
import stat
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any
from uuid import UUID


# Keep cyclic collection out of source imports and every later measurement.
# Objects are explicitly released, but their physical retirement is not
# inferred from this process-level prototype.
gc.disable()


PRIVATE_ROOT = Path(__file__).resolve().parent
DEFAULT_OBSERVER_SOURCE = Path(
    "/home/bryan/.cache/agent-observer-working-set-20261018/"
    "final-source-b176ac06"
)
DEFAULT_OBSERVER_TESTS = DEFAULT_OBSERVER_SOURCE / "tests"
DEFAULT_OBSERVER_REPO = Path("/home/bryan/code/agent-observer-working-set")
DEFAULT_MESH_REPO = Path("/home/bryan/code/mesh-plus-working-set")
DEFAULT_MESH_SOURCE = Path(
    "/home/bryan/.cache/agent-observer-working-set-20261018/"
    "final-mesh-b9e8488e/src"
)
DEFAULT_MATCHED_SOURCE = (
    DEFAULT_OBSERVER_SOURCE
    / "docs/evidence/2026-10-18-working-set/performance-source/read_matched.py"
)
DEFAULT_OBSERVER_ID = "b176ac06b39daeead4be0a33ff9d781304091fe0"
DEFAULT_MESH_ID = "b9e8488e0f0fa438119e36848ac7c9887038ea1c"
WINDOW_MS = 72 * 60 * 60 * 1000
ROW_COUNTS = (100, 500, 2000)
SELECTED_COUNTS = {100: 2, 500: 4, 2000: 20}
MAX_SCALAR_AUDIT = 64
MAX_MESH_CHANNEL_AUDIT = 16
MAX_EVENT_AUDIT = 128
V3_CONTEXT: dict[str, Any] = {}
V3_FAILURES: list[dict[str, Any]] = []
EXPECTED_LIMITS = {
    "ledgerBytes": 1_048_576,
    "identities": 4096,
    "frameBytes": 8_404_992,
    "encodedBytes": 64 * 1024 * 1024,
    "serviceClients": 16,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _digest(value: Any, canonical) -> str:
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def _safe_failure_code(error: BaseException) -> str:
    code = getattr(error, "code", None)
    if type(code) is str and code and all(char.islower() or char.isdigit() or char == "_" for char in code):
        return code[:128]
    if isinstance(error, AssertionError) and len(error.args) == 1:
        value = error.args[0]
        if type(value) is str and value and all(
            char.islower() or char.isdigit() or char == "_" for char in value
        ):
            return value[:128]
    return type(error).__name__.lower()


def _safe_protocol_code(error: BaseException) -> str | None:
    code = getattr(error, "code", None)
    if (type(code) is str and 1 <= len(code) <= 128
            and code[0].islower()
            and all(char.islower() or char.isdigit() or char == "_" for char in code)):
        return code
    return None


def _write_private_output(target: Path, content: str) -> None:
    """Atomically persist one trial or failure before a controller advances."""
    target = target.resolve()
    if not target.is_relative_to(PRIVATE_ROOT):
        raise ValueError("output_must_remain_private")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    with temporary.open("x", encoding="utf-8") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, target)


def _load_reference(path: Path):
    spec = importlib.util.spec_from_file_location("working_set_read_matched", path)
    if spec is None or spec.loader is None:
        raise ValueError("matched_reference_import")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _insert_import_roots(observer_source: Path, observer_tests: Path, mesh_source: Path) -> None:
    for path in (mesh_source, observer_tests, observer_source):
        if not path.is_dir():
            raise ValueError(f"source_path_missing:{path}")
    # Agent Observer source wins over the mutable checkout; test files are
    # allowed only as fixture helpers, and Mesh comes from the registered tree.
    sys.path[0:0] = [str(observer_source), str(observer_tests), str(mesh_source)]


def _capture_project_modules(observer_source: Path, mesh_source: Path) -> dict[str, dict[str, str]]:
    roots = {
        "agent_observer": observer_source.resolve(),
        "mesh_plus": mesh_source.resolve(),
    }
    loaded: dict[str, dict[str, str]] = {}
    found = {name: 0 for name in roots}
    for name, module in tuple(sys.modules.items()):
        root_name = next((root for root in roots if name == root or name.startswith(root + ".")), None)
        if root_name is None:
            continue
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).resolve()
        root = roots[root_name]
        if not path.is_relative_to(root) or path.suffix != ".py":
            raise ValueError(f"unexpected_loaded_module:{name}")
        found[root_name] += 1
        loaded[name] = {
            "root": root_name,
            "path": str(path.relative_to(root)),
            "sha256": _sha256(path),
        }
    if any(count == 0 for count in found.values()):
        raise ValueError("source_module_roots_not_loaded")
    return dict(sorted(loaded.items()))


def _read_rss(phase: str) -> dict[str, int | str]:
    fields: dict[str, int] = {}
    with Path("/proc/self/status").open("r", encoding="ascii") as stream:
        for line in stream:
            if line.startswith(("VmRSS:", "VmHWM:")):
                name, rest = line.split(":", 1)
                fields[name] = int(rest.split()[0]) * 1024
    if set(fields) != {"VmRSS", "VmHWM"}:
        raise ValueError("rss_snapshot_unavailable")
    return {
        "phase": phase,
        "pid": os.getpid(),
        "rssBytes": fields["VmRSS"],
        "processHighWaterRssBytes": fields["VmHWM"],
    }


def _reader_clock() -> dict[str, str]:
    return {
        "bootId": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "timeNamespace": os.readlink("/proc/self/ns/time").replace("[", "").replace("]", ""),
    }


def _reader_now() -> int:
    return int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)


def _native_runtime_accepted(header: dict[str, Any]) -> int | None:
    hosts = header.get("mesh", {}).get("hosts", [])
    if not hosts or hosts[0].get("owner") is None:
        return None
    service = hosts[0]["owner"].get("service") or {}
    for source in service.get("sources", []):
        if source.get("provider") != "codex":
            continue
        for component in source.get("components", []):
            if component.get("name") == "runtime":
                accepted = component.get("accepted")
                return accepted if type(accepted) is int else None
    return None


def _frame_header(frame: Any) -> dict[str, Any] | None:
    context = getattr(frame, "context", None)
    if callable(context):
        value = context()
        return value if type(value) is dict else None
    return frame if type(frame) is dict else None


def _frame_row_count(frame: dict[str, Any]) -> int:
    snapshot = frame.get("snapshot")
    if type(snapshot) is dict:
        return len(snapshot.get("sessions", []))
    projection = frame.get("projection")
    if type(projection) is dict:
        return len(projection.get("sessions", []))
    return 0


def _accepted_from_native(frame: dict[str, Any]) -> int | None:
    for source in frame.get("sources", []):
        if source.get("provider") != "codex":
            continue
        for component in source.get("components", []):
            if component.get("name") == "runtime":
                accepted = component.get("accepted")
                return accepted if type(accepted) is int else None
    return None


class NativeScalarAudit:
    """Bounded scalars only; never retains a native frame or row roster."""

    def __init__(self):
        self.frames: list[dict[str, Any]] = []
        self.snapshots = 0
        self.watchFrames = 0

    def record(self, operation: str, frame: dict[str, Any]) -> None:
        item = {
            "operation": operation,
            "serviceId": frame.get("serviceId"),
            "viewRevision": frame.get("viewRevision"),
            "runtimeAccepted": _accepted_from_native(frame),
            "nativeKind": frame.get("kind"),
            "ownerSequence": frame.get("sequence"),
            "rowCount": _frame_row_count(frame),
        }
        self.frames.append(item)
        if len(self.frames) > MAX_SCALAR_AUDIT:
            del self.frames[0]
        if operation == "snapshot":
            self.snapshots += 1
        else:
            self.watchFrames += 1

    async def snapshot(self, source):
        frame = await source.snapshot()
        self.record("snapshot", frame)
        return frame

    async def watch(self, source):
        iterator = source.watch().__aiter__()
        try:
            async for publication in iterator:
                self.record("watch", publication.frame)
                yield publication
        finally:
            close = getattr(iterator, "aclose", None)
            if callable(close):
                await close()

    def matching(self, *, operation: str, service_id: str, view_revision: int,
                 accepted: int, owner_sequence: int, native_kind: str,
                 row_count: int) -> list[dict[str, Any]]:
        return [item for item in self.frames
                if item["operation"] == operation
                and item["serviceId"] == service_id
                and item["viewRevision"] == view_revision
                and item["runtimeAccepted"] == accepted
                and item["ownerSequence"] == owner_sequence
                and item["nativeKind"] == native_kind
                and item["rowCount"] == row_count]


class PublishedOwnerDigestAudit:
    """Bounded scalars copied from public CachedPublisher return values."""

    def __init__(self):
        self.envelopes: list[dict[str, Any]] = []
        self._pending_nonce_values: list[tuple[dict[str, Any], str]] = []

    def record(self, operation: str, payload: dict[str, Any]) -> None:
        frame = payload.get("ownerFrame")
        owner_digest = payload.get("ownerDigest")
        if type(frame) is not dict or type(owner_digest) is not str:
            raise ValueError("public_publisher_owner_digest_missing")
        nonce = payload.get("nonce")
        item = {
            "operation": operation,
            "ownerDigest": owner_digest,
            "serviceId": frame.get("serviceId"),
            "viewRevision": frame.get("viewRevision"),
            "runtimeAccepted": _accepted_from_native(frame),
            "nativeKind": frame.get("kind"),
            "ownerSequence": frame.get("sequence"),
            "rowCount": _frame_row_count(frame),
            "bridgeId": payload.get("bridgeId"),
            "envelopeSequence": payload.get("sequence"),
            "payloadEncodedAtMs": payload.get("encodedAtMs"),
            "nonceSha256": None,
            "kind": payload.get("kind"),
        }
        self.envelopes.append(item)
        if type(nonce) is str:
            self._pending_nonce_values.append((item, nonce))
        if len(self.envelopes) > MAX_SCALAR_AUDIT:
            del self.envelopes[0]
        if len(self._pending_nonce_values) > MAX_SCALAR_AUDIT:
            del self._pending_nonce_values[0]

    def seal_pending_nonces(self) -> None:
        """Hash bounded challenge scalars after the measured CPU interval."""
        for item, nonce in self._pending_nonce_values:
            item["nonceSha256"] = hashlib.sha256(nonce.encode()).hexdigest()
        self._pending_nonce_values.clear()

    def matching(self, *, operation: str, service_id: str, view_revision: int,
                 accepted: int, owner_sequence: int, native_kind: str,
                 row_count: int, bridge_id: str, payload_encoded_at_ms: int,
                 nonce_sha256: str) -> list[dict[str, Any]]:
        return [item for item in self.envelopes
                if item["operation"] == operation
                and item["serviceId"] == service_id
                and item["viewRevision"] == view_revision
                and item["runtimeAccepted"] == accepted
                and item["ownerSequence"] == owner_sequence
                and item["nativeKind"] == native_kind
                and item["rowCount"] == row_count
                and item["bridgeId"] == bridge_id
                and item["payloadEncodedAtMs"] == payload_encoded_at_ms
                and item["nonceSha256"] == nonce_sha256]


class _AuditedCachedPublisher:
    """Transparent adapter over the SDK CachedPublisher public surface."""

    def __init__(self, publisher, audit: PublishedOwnerDigestAudit,
                 exceptions: "PublicExceptionAudit"):
        self._publisher, self._audit, self._exceptions = publisher, audit, exceptions

    @property
    def host(self):
        return self._publisher.host

    @property
    def source(self):
        return self._publisher.source

    @property
    def profile(self):
        return self._publisher.profile

    @property
    def capabilities(self):
        return self._publisher.capabilities

    def validate(self, payload):
        return self._publisher.validate(payload)

    async def snapshot(self, parameters):
        try:
            payload = await self._publisher.snapshot(parameters)
        except BaseException as error:
            self._exceptions.record("CachedPublisher.snapshot", error)
            raise
        self._audit.record("snapshot", payload)
        return payload

    async def proof(self, parameters):
        try:
            payload = await self._publisher.proof(parameters)
        except BaseException as error:
            self._exceptions.record("CachedPublisher.proof", error)
            raise
        self._audit.record("proof", payload)
        return payload

    def watch(self):
        return self._watch()

    async def _watch(self):
        iterator = self._publisher.watch().__aiter__()
        try:
            async for publication in iterator:
                self._audit.record("watch", publication.payload)
                yield publication
        except BaseException as error:
            self._exceptions.record("CachedPublisher.watch", error)
            raise
        finally:
            close = getattr(iterator, "aclose", None)
            if callable(close):
                await close()


class MeshChannelAudit:
    """Bounded references/scalars from public IPCServer handler channels."""

    def __init__(self):
        self.channels: list[Any] = []
        self.completed: list[dict[str, Any] | None] = []
        self.overflow = _empty_channel_metrics()
        self.overflowConnections = 0
        self.overflowActive = 0

    @staticmethod
    def _inspect(channel) -> dict[str, Any]:
        inspect = getattr(channel, "inspect", None)
        if not callable(inspect):
            raise ValueError("mesh_public_channel_metrics_missing")
        metrics = inspect()
        if metrics.get("byteScope") != "completed-json-lines":
            raise ValueError("mesh_channel_byte_scope_unexpected")
        return _channel_metrics(metrics)

    def start(self, channel) -> int | None:
        if len(self.channels) < MAX_MESH_CHANNEL_AUDIT:
            self.channels.append(channel)
            self.completed.append(None)
            return len(self.channels) - 1
        self.overflowActive += 1
        return None

    def finish(self, channel, token: int | None) -> None:
        metrics = self._inspect(channel)
        if token is None:
            _add_channel_metrics(self.overflow, metrics)
            self.overflowConnections += 1
            self.overflowActive -= 1
        else:
            self.completed[token] = metrics

    def after_current_accept_done(self, token: int | None) -> None:
        """Drop one raw channel only after its owning IPC accept task exits."""
        if token is None:
            return
        task = asyncio.current_task()
        if task is None:
            return
        task.add_done_callback(
            lambda completed_task, audit=self, slot=token:
                audit.retire_after_accept_done(completed_task, slot)
        )

    def retire_after_accept_done(self, task, token: int | None) -> bool:
        """Release a finished slot only when both scalar capture and close are proven."""
        if token is None or not task.done():
            return False
        if not 0 <= token < len(self.channels) or self.completed[token] is None:
            return False
        channel = self.channels[token]
        if channel is None:
            return True
        writer = getattr(channel, "writer", None)
        is_closing = getattr(writer, "is_closing", None)
        if not getattr(channel, "closed", False) or not callable(is_closing):
            return False
        if not is_closing():
            return False
        self.channels[token] = None
        return True

    @property
    def retained_channel_references(self) -> int:
        return sum(channel is not None for channel in self.channels)

    def snapshot(self) -> dict[str, Any]:
        connections = []
        for channel, completed in zip(self.channels, self.completed, strict=True):
            if channel is not None:
                connections.append(self._inspect(channel))
            elif completed is not None:
                connections.append(copy.deepcopy(completed))
            else:
                raise ValueError("mesh_channel_audit_retired_without_metrics")
        totals = _sum_channel_audit(connections)
        _add_channel_metrics(totals, self.overflow)
        return {
            "metrics": totals,
            "connections": connections,
            "overflowConnections": self.overflowConnections,
            "overflowActiveConnections": self.overflowActive,
            "retainedChannelReferences": self.retained_channel_references,
            "completedConnectionRecords": sum(item is not None for item in self.completed),
            "overflowMetrics": copy.deepcopy(self.overflow),
        }


class PublicExceptionAudit:
    """Bounded exception type/code scalars; never retains messages or traces."""

    def __init__(self):
        self.records: list[dict[str, Any]] = []
        self.dropped = 0

    def record(self, operation: str, error: BaseException) -> None:
        code = _safe_protocol_code(error)
        item = {"operation": operation, "errorType": type(error).__name__, "code": code}
        if len(self.records) < MAX_SCALAR_AUDIT:
            self.records.append(item)
        else:
            self.dropped += 1


class ClientChannelAudit:
    """Scalar totals for public connection attempts outside the Reader roster."""

    def __init__(self):
        self.failedConnect = _empty_channel_metrics()
        self.refusedConnected = _empty_channel_metrics()
        self.failedConnectCount = 0
        self.refusedConnectedCount = 0

    def record_failed_connect(self, channel) -> None:
        _add_channel_metrics(self.failedConnect, MeshChannelAudit._inspect(channel))
        self.failedConnectCount += 1

    def record_refused_connected(self, client) -> None:
        _add_channel_metrics(self.refusedConnected, MeshChannelAudit._inspect(client.channel))
        self.refusedConnectedCount += 1


class HarnessConnectionHistoryBound(RuntimeError):
    code = "harness_connection_history_bound"


def _client_channel_snapshot(client_refs: list[Any], audit: ClientChannelAudit) -> dict[str, Any]:
    accepted_connections = [_channel_metrics(client.channel.inspect()) for client in client_refs]
    accepted = _sum_channel_audit(accepted_connections)
    all_attempts = _sum_channel_audit([
        *accepted_connections,
        audit.failedConnect,
        audit.refusedConnected,
    ])
    return {
        "accepted": accepted,
        "all": all_attempts,
        "acceptedConnections": accepted_connections,
        "failedConnect": copy.deepcopy(audit.failedConnect),
        "failedConnectCount": audit.failedConnectCount,
        "refusedConnected": copy.deepcopy(audit.refusedConnected),
        "refusedConnectedCount": audit.refusedConnectedCount,
        "retainedClientReferences": len(client_refs),
    }


class SelectorBoundaryPause:
    """Test-only pause at the Runtime loop's existing selector boundary."""

    def __init__(self):
        self._condition = threading.Condition()
        self._requested = False
        self._entered = False
        self._released = False

    @property
    def held(self) -> bool:
        with self._condition:
            return self._entered

    def request_and_wait(self, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        with self._condition:
            if self._requested or self._entered:
                raise AssertionError("selector_pause_already_requested")
            self._requested = True
            self._released = False
            self._condition.notify_all()
            while not self._entered:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._requested = False
                    self._released = True
                    self._condition.notify_all()
                    raise TimeoutError("runtime_selector_pause_timeout")
                self._condition.wait(remaining)

    def at_boundary(self, timeout: float = 10.0) -> None:
        deadline = time.monotonic() + timeout
        with self._condition:
            if not self._requested:
                return
            self._entered = True
            self._condition.notify_all()
            while self._requested and not self._released:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._requested = False
                    self._entered = False
                    self._condition.notify_all()
                    raise TimeoutError("runtime_selector_release_timeout")
                self._condition.wait(remaining)
            self._entered = False
            self._requested = False
            self._released = False
            self._condition.notify_all()

    def resume_and_wait(self, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        with self._condition:
            if not self._entered:
                raise AssertionError("runtime_selector_not_held")
            self._released = True
            self._condition.notify_all()
            while self._entered:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError("runtime_selector_resume_timeout")
                self._condition.wait(remaining)

    def release_for_cleanup(self) -> None:
        with self._condition:
            self._requested = False
            self._released = True
            self._condition.notify_all()


class _SelectorPauseProxy:
    """Delegate all selector behavior except a requested test pause."""

    def __init__(self, selector, pause: SelectorBoundaryPause):
        self._selector, self._pause = selector, pause

    def __getattr__(self, name):
        return getattr(self._selector, name)

    def select(self, *args, **kwargs):
        self._pause.at_boundary()
        return self._selector.select(*args, **kwargs)


class RuntimeThread:
    """Use the public local Runtime loop in this process; collect stays off."""

    def __init__(self, state, path: Path, Runtime):
        self.runtime = Runtime(
            state,
            path,
            collect=False,
            max_clients=EXPECTED_LIMITS["serviceClients"],
            encoded_limit=EXPECTED_LIMITS["encodedBytes"],
            heartbeat_ms=200,
        )
        self._selector = self.runtime.selector
        self.pause = SelectorBoundaryPause()
        self.runtime.selector = _SelectorPauseProxy(self._selector, self.pause)
        self.stop = threading.Event()
        self.errors: list[BaseException] = []
        self.thread = threading.Thread(target=self._run, name="working-set-runtime")
        self.cleanup_counts: dict[str, Any] | None = None

    def _run(self) -> None:
        try:
            self.runtime.run(self.stop)
        except BaseException as error:
            self.errors.append(error)

    def __enter__(self):
        self.thread.start()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline and not self.errors:
            try:
                node = self.runtime.path.stat()
                if stat.S_IMODE(node.st_mode) == 0o600:
                    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as probe:
                        probe.settimeout(0.2)
                        probe.connect(str(self.runtime.path))
                    break
            except OSError:
                time.sleep(0.01)
        if self.errors or not self.runtime.path.exists():
            self.__exit__(None, None, None)
            raise AssertionError("runtime_start_failed") from (self.errors[0] if self.errors else None)
        return self

    def __exit__(self, *_args):
        # Always release a held or pending test barrier before stopping Runtime.
        self.pause.release_for_cleanup()
        self.stop.set()
        self.thread.join(5)
        if self.thread.is_alive():
            raise AssertionError("runtime_cleanup_timeout")
        self.runtime.selector = self._selector
        selector_map = self._selector.get_map()
        self.cleanup_counts = {
            "runtimePeersAfterRun": len(self.runtime.peers),
            "selectorRegistrationsAfterRun": 0 if selector_map is None else len(selector_map),
            "selectorClosed": selector_map is None,
            "runtimeThreadAlive": self.thread.is_alive(),
            "selectorHookRestored": self.runtime.selector is self._selector,
        }
        if self.errors:
            raise AssertionError("runtime_thread_failed") from self.errors[0]


def _synthetic_workload(reference, scoped_snapshot, canonical, rows: int):
    seed = scoped_snapshot()
    seed, wall, small, expected_ids_from_fixture, _running_ids = reference.build_workload(
        seed, rows, canonical
    )
    # Adversarial E check: this row is both active and recent, while its kind
    # keeps it out of the eligible set. The matched reference filter must omit it.
    excluded = seed["sessions"][-1]
    excluded["kind"] = "system"
    excluded["runtime"] = copy.deepcopy(seed["sessions"][0]["runtime"])
    excluded["phase"] = copy.deepcopy(seed["sessions"][0]["phase"])
    excluded["blockedReasons"] = copy.deepcopy(seed["sessions"][0]["blockedReasons"])
    excluded["activity"] = copy.deepcopy(seed["sessions"][small]["activity"])
    expected = reference.full_consumer_rows({"sessions": seed["sessions"]})
    if {reference.native_id(row) for row in expected} != expected_ids_from_fixture:
        raise AssertionError("independent_reference_expected_ids_changed")
    if len(expected) != SELECTED_COUNTS[rows]:
        raise AssertionError("selected_count_preflight")
    if reference.native_id(excluded) in {reference.native_id(row) for row in expected}:
        raise AssertionError("eligibility_exclusion_fixture_invalid")
    return seed, wall, expected, excluded["identity"]["nativeId"]


def _accepted_sample(template: dict[str, Any], wall: int, generation: int):
    sample = copy.deepcopy(template)
    sample["collectionId"] = str(UUID(int=100 + generation))
    sample["collectedAt"] = wall
    return sample


def _event_scalars(frame: Any, *, observed_at_ms: int) -> dict[str, Any]:
    header = _frame_header(frame)
    if header is None:
        error = frame.get("error") if type(frame) is dict else None
        error = error if type(error) is dict else {}
        return {
            "eventType": type(frame).__name__,
            "headerAvailable": False,
            "meshErrorCode": error.get("code"),
            "meshErrorReasonCode": error.get("reasonCode"),
        }
    mesh = header.get("mesh", {})
    hosts = mesh.get("hosts", [])
    host = hosts[0] if hosts else {}
    owner = host.get("owner") or {}
    service = owner.get("service") or {}
    metadata = owner.get("metadata") or {}
    scopes = metadata.get("scopes", [])
    scope = scopes[0] if scopes else {}
    coverage = scope.get("coverage") or {}
    delivery = host.get("delivery") or {}
    delivery_error = delivery.get("error") or {}
    proof = delivery.get("proof") or {}
    sent = proof.get("sentAtMs")
    received = proof.get("receivedAtMs")
    proof_rtt = received - sent if type(sent) is int and type(received) is int else None
    proof_fresh = (
        type(sent) is int and type(received) is int
        and sent <= received <= observed_at_ms
        and 0 <= proof_rtt <= 2_000
    )
    runtime_receipts = [
        {"accepted": receipt.get("accepted"), "health": receipt.get("health")}
        for receipt in host.get("receipts", [])
        if receipt.get("component") == "runtime"
    ]
    return {
        "headerAvailable": True,
        "meshKind": mesh.get("kind"),
        "meshStatus": mesh.get("status"),
        "meshSequence": (mesh.get("reader") or {}).get("sequence"),
        "meshRevision": (mesh.get("reader") or {}).get("revision"),
        "hostDeliveryStatus": delivery.get("status"),
        "hostDeliveryErrorCode": delivery_error.get("code"),
        "hostDeliveryErrorReasonCode": delivery_error.get("reasonCode"),
        "hostDeliveryErrorPresent": bool(delivery_error),
        "hostDeliveryPath": delivery.get("path"),
        "hostDeliveryEpoch": delivery.get("epoch"),
        "hostViewState": host.get("viewState"),
        "serviceId": service.get("serviceId"),
        "serviceViewRevision": service.get("viewRevision"),
        "serviceObservationRevision": service.get("observationRevision"),
        "serviceSequence": service.get("sequence"),
        "serviceKind": service.get("kind"),
        "runtimeAccepted": _native_runtime_accepted(header),
        "clockGeneration": service.get("clockGeneration"),
        "clockCeiling": service.get("clockCeiling"),
        "scopeMemberCount": len(scope.get("members", [])),
        "coverageStatus": coverage.get("status"),
        "coverageReason": coverage.get("reason"),
        "receiptRuntime": runtime_receipts,
        "proofPresent": bool(proof),
        "proofFresh": proof_fresh,
        "proofRttMs": proof_rtt,
        "proofObservedAgeMs": observed_at_ms - received if type(received) is int else None,
        "proofSentAtMs": sent,
        "proofReceivedAtMs": received,
        "proofBridgeId": proof.get("bridgeId"),
        "proofBridgeEncodedAtMs": proof.get("bridgeEncodedAtMs"),
        "proofPayloadDigest": proof.get("payloadDigest"),
        "observedAtMs": observed_at_ms,
    }


def _record_failure(code: str, evidence: dict[str, Any], *, defer: bool = False) -> None:
    if len(V3_FAILURES) < MAX_EVENT_AUDIT:
        V3_FAILURES.append({"code": code, **evidence})
    if not defer:
        raise AssertionError(code)


def _assert_detached(copies: list[list[dict[str, Any]]]) -> tuple[bool, bool]:
    if len({id(rows) for rows in copies}) != len(copies):
        return False, False
    row_objects = [[id(row) for row in rows] for rows in copies]
    distinct = len({item for group in row_objects for item in group}) == sum(map(len, row_objects))
    return True, distinct


def _empty_channel_metrics() -> dict[str, Any]:
    return {
        "byteScope": "completed-json-lines",
        "sentFrames": 0,
        "sentBytes": 0,
        "receivedFrames": 0,
        "receivedBytes": 0,
        "byKind": {"sent": {}, "received": {}},
    }


def _channel_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    if metrics.get("byteScope") != "completed-json-lines":
        raise ValueError("mesh_channel_byte_scope_unexpected")
    return {
        "byteScope": metrics["byteScope"],
        "sentFrames": metrics["sentFrames"],
        "sentBytes": metrics["sentBytes"],
        "receivedFrames": metrics["receivedFrames"],
        "receivedBytes": metrics["receivedBytes"],
        "byKind": copy.deepcopy(metrics["byKind"]),
    }


def _add_channel_metrics(total: dict[str, Any], metrics: dict[str, Any]) -> None:
    if metrics.get("byteScope") != "completed-json-lines":
        raise ValueError("mesh_channel_byte_scope_unexpected")
    for key in ("sentFrames", "sentBytes", "receivedFrames", "receivedBytes"):
        total[key] += metrics[key]
    for direction, values in metrics["byKind"].items():
        for kind, counts in values.items():
            entry = total["byKind"][direction].setdefault(kind, {"frames": 0, "bytes": 0})
            entry["frames"] += counts["frames"]
            entry["bytes"] += counts["bytes"]


def _sum_channel_audit(connections: list[dict[str, Any]]) -> dict[str, Any]:
    total = _empty_channel_metrics()
    for connection in connections:
        _add_channel_metrics(total, connection)
    return total


def _by_kind_delta(left: dict[str, Any], right: dict[str, Any]) -> dict[str, dict[str, int]]:
    return {
        kind: {
            "frames": left.get(kind, {}).get("frames", 0) - right.get(kind, {}).get("frames", 0),
            "bytes": left.get(kind, {}).get("bytes", 0) - right.get(kind, {}).get("bytes", 0),
        }
        for kind in sorted(set(left) | set(right))
    }


def _all_by_kind_deltas_zero(deltas: dict[str, dict[str, int]]) -> bool:
    return all(value["frames"] == 0 and value["bytes"] == 0 for value in deltas.values())


def _direction_delta(sender: dict[str, Any], receiver: dict[str, Any],
                     direction: str) -> dict[str, Any]:
    sent = sender["byKind"]["sent"]
    received = receiver["byKind"]["received"]
    return {
        "frames": sender["sentFrames"] - receiver["receivedFrames"],
        "bytes": sender["sentBytes"] - receiver["receivedBytes"],
        "byKind": _by_kind_delta(sent, received),
        "direction": direction,
    }


def _direction_non_close_zero(delta: dict[str, Any]) -> bool:
    return all(value["frames"] == 0 and value["bytes"] == 0
               for kind, value in delta["byKind"].items() if kind != "close")


def _direction_exact_zero(delta: dict[str, Any]) -> bool:
    return delta["frames"] == 0 and delta["bytes"] == 0 and _all_by_kind_deltas_zero(delta["byKind"])


def _mesh_counter_snapshot(reader: dict[str, Any], clients: dict[str, Any],
                           all_clients: dict[str, Any],
                           bridge: dict[str, Any]) -> dict[str, Any]:
    reader_client = {
        "sent": _by_kind_delta(reader["byKind"]["sent"], clients["byKind"]["sent"]),
        "received": _by_kind_delta(reader["byKind"]["received"], clients["byKind"]["received"]),
    }
    client_bridge = {
        "clientSentMinusBridgeReceived": _direction_delta(all_clients, bridge, "client_to_bridge"),
        "clientReceivedMinusBridgeSent": {
            "frames": all_clients["receivedFrames"] - bridge["sentFrames"],
            "bytes": all_clients["receivedBytes"] - bridge["sentBytes"],
            "byKind": _by_kind_delta(all_clients["byKind"]["received"], bridge["byKind"]["sent"]),
            "direction": "bridge_to_client",
        },
    }
    return {"readerClientByKindDeltas": reader_client,
            "clientBridgeDeltas": client_bridge}


def _close_deltas_by_direction(snapshot: dict[str, Any]) -> dict[str, dict[str, int]]:
    result = {}
    for name, delta in snapshot["clientBridgeDeltas"].items():
        result[name] = delta["byKind"].get("close", {"frames": 0, "bytes": 0})
    return result


def _classify_mesh_byte_delivery(
    diagnostic: dict[str, Any], cleanup: dict[str, Any]
) -> str | None:
    """Keep public byte-counter deltas diagnostic; only cleanup can fail here."""
    pre = diagnostic["preShutdown"]
    post = diagnostic["postShutdown"]
    pre_counts = _mesh_counter_snapshot(
        pre["reader"], pre["clients"]["accepted"], pre["clients"]["all"], pre["bridge"]
    )
    post_counts = _mesh_counter_snapshot(
        post["reader"], post["clients"]["accepted"], post["clients"]["all"], post["bridge"]
    )
    diagnostic["preShutdownCounterDeltas"] = pre_counts
    diagnostic["postShutdownCounterDeltas"] = post_counts

    diagnostic["bidirectionalByteCountsMatch"] = all(
        _direction_exact_zero(delta)
        for delta in post_counts["clientBridgeDeltas"].values()
    ) and all(_all_by_kind_deltas_zero(deltas)
              for deltas in post_counts["readerClientByKindDeltas"].values())
    diagnostic["terminalCloseOnlyDelta"] = {
        "basis": "signed difference in completed public close-kind counters from pre-shutdown to post-shutdown",
        "clientSentMinusBridgeReceived": {
            key: post_counts["clientBridgeDeltas"]["clientSentMinusBridgeReceived"]["byKind"].get(
                "close", {"frames": 0, "bytes": 0}
            )[key] - pre_counts["clientBridgeDeltas"]["clientSentMinusBridgeReceived"]["byKind"].get(
                "close", {"frames": 0, "bytes": 0}
            )[key] for key in ("frames", "bytes")
        },
        "clientReceivedMinusBridgeSent": {
            key: post_counts["clientBridgeDeltas"]["clientReceivedMinusBridgeSent"]["byKind"].get(
                "close", {"frames": 0, "bytes": 0}
            )[key] - pre_counts["clientBridgeDeltas"]["clientReceivedMinusBridgeSent"]["byKind"].get(
                "close", {"frames": 0, "bytes": 0}
            )[key] for key in ("frames", "bytes")
        },
        "physicalOrRawSocketDeliveryClaimed": False,
    }

    cleanup_zero = (
        cleanup["readerActiveConnections"] == 0
        and cleanup["readerCleanupFailures"] == 0
        and cleanup["readerConnectionsOpened"] == cleanup["readerConnectionsClosed"]
        and cleanup["cachedSourceWrapper"] == {
            "activeSourceOperations": 0,
            "pendingSnapshotCalls": 0,
            "openWatchIterators": 0,
        }
        and cleanup["runtime"] is not None
        and cleanup["runtime"]["runtimePeersAfterRun"] == 0
        and cleanup["runtime"]["selectorRegistrationsAfterRun"] == 0
        and cleanup["runtime"]["selectorClosed"]
        and not cleanup["runtime"]["runtimeThreadAlive"]
        and cleanup["runtime"]["selectorHookRestored"]
        and cleanup["bridgeHandlersStarted"] == (
            cleanup["bridgeHandlersReturned"] + cleanup["bridgeHandlersRaised"]
        )
        and cleanup["bridgeActiveHandlers"] == 0
        and cleanup["retainedReaderClients"] <= MAX_MESH_CHANNEL_AUDIT
        and cleanup["retainedBridgeChannels"] <= MAX_MESH_CHANNEL_AUDIT
    )
    diagnostic["cleanupZero"] = cleanup_zero

    def differing_kinds(counts):
        differences = []
        for direction, delta in counts["clientBridgeDeltas"].items():
            for kind, value in sorted(delta["byKind"].items()):
                if value["frames"] or value["bytes"]:
                    differences.append({
                        "path": direction,
                        "kind": kind,
                        "frames": value["frames"],
                        "bytes": value["bytes"],
                    })
        for direction, deltas in counts["readerClientByKindDeltas"].items():
            for kind, value in sorted(deltas.items()):
                if value["frames"] or value["bytes"]:
                    differences.append({
                        "path": "reader_client_" + direction,
                        "kind": kind,
                        "frames": value["frames"],
                        "bytes": value["bytes"],
                    })
        return differences

    reader = post["readerState"]
    pre_differences = differing_kinds(pre_counts)
    post_differences = differing_kinds(post_counts)
    diagnostic["counterDiagnostics"] = {
        "scope": "public completed application-channel counters; write completion and validated receive only, not raw wire or proof of peer parsing",
        "allCompletedSenderWritesIncludedThroughTeardown": True,
        "preShutdownQuiescenceRequired": False,
        "counterEqualityUsedForFunctionalAcceptance": False,
        "nativeIpcBytesMeasured": False,
        "readerMetricsPartial": bool(reader["partial"] or reader["uninstrumentedConnections"]),
        "bridgeAuditOverflow": bool(
            pre["bridgeAudit"]["overflowActiveConnections"]
            or post["bridgeAudit"]["overflowActiveConnections"]
            or pre["bridgeAudit"]["overflowConnections"]
            or post["bridgeAudit"]["overflowConnections"]
        ),
        "publicClientRefusalOrHistoryOverflow": bool(
            pre["clients"]["refusedConnectedCount"]
            or post["clients"]["refusedConnectedCount"]
        ),
        "preShutdownDifferencesByPathAndKind": pre_differences,
        "postShutdownDifferencesByPathAndKind": post_differences,
        "terminalCloseOnlyDelta": diagnostic["terminalCloseOnlyDelta"],
    }

    # Public application counters do not promise a simultaneous sender/reader
    # observation during caller cancellation. Keep every phase/kind delta in
    # the report; only incomplete resource retirement remains a hard failure.
    if not cleanup_zero:
        return "mesh_pipeline_cleanup_incomplete"
    return None


async def _run_variant(
    *,
    variant: str,
    rows: int,
    generations: int,
    reads_per_generation: int,
    trial_index: int,
    variant_order: list[str],
    timed: bool,
    diagnostic_acquisition_timeout: float | None,
    complete_pair_after_byte_mismatch: bool,
    source_inputs: dict[str, Any],
    reference,
    rss: list[dict[str, Any]],
) -> dict[str, Any]:
    from mesh_plus.api import (
        Bridge,
        Client,
        Endpoint,
        Reader,
        reconstructed,
    )
    from mesh_plus.transport import IPCServer as PublicIPCServer
    from mesh_plus.transport import connect_ipc
    from mesh_plus.evidence import digest as mesh_digest
    from agent_observer.contract import canonical
    from agent_observer.service_runtime import Runtime
    from agent_observer.service_state import ServiceState
    from agent_observer.working_set_contract import MAX_IDENTITIES, MAX_LEDGER_BYTES
    from agent_observer.active_contract import MAX_FRAME_BYTES
    from agent_observer.working_set_policy import DEFAULT_WINDOW_MS
    from agent_observer.mesh_profile import AgentProfile
    from agent_observer.mesh_read import PreparedAgentWatch
    from agent_observer.mesh_working_set_profile import WorkingSetAgentProfile
    from agent_observer.mesh_working_set_read import PreparedWorkingSetAgentWatch
    from agent_observer.mesh_publisher import make_publisher
    from agent_observer.mesh_working_set_publisher import make_working_set_publisher
    from test_service_runtime import scoped_snapshot

    if variant not in {"full", "working"}:
        raise ValueError("variant")
    template, wall, fixture_expected_rows, excluded_id = _synthetic_workload(
        reference, scoped_snapshot, canonical, rows
    )
    fixture_expected_ids = [reference.native_id(row) for row in fixture_expected_rows]
    fixture_expected_hash = reference.digest(fixture_expected_rows, canonical)
    fixture_expected_ids_hash = reference.digest(fixture_expected_ids, canonical)
    fixture_activity_signature = tuple(
        (reference.native_id(row), row["activity"].get("at"),
         row["activity"].get("health"), row["activity"].get("source"),
         row["activity"].get("reason"))
        for row in template["sessions"]
    )
    # The independent filter and input ID/hash oracle are complete before CPU.
    if len(fixture_expected_rows) != SELECTED_COUNTS[rows]:
        raise AssertionError("expected_selection_size")

    profile = WorkingSetAgentProfile(DEFAULT_WINDOW_MS) if variant == "working" else AgentProfile()
    source_id = "working" if variant == "working" else "full"
    state = ServiceState(
        host_scope="fixture",
        configs={"codex": ("/fixture/codex", "explicit")},
        uid=os.geteuid(),
        working_set_window_ms=DEFAULT_WINDOW_MS if variant == "working" else None,
    )
    scalar_audit = NativeScalarAudit()
    published_audit = PublishedOwnerDigestAudit()
    exception_audit = PublicExceptionAudit()
    client_channel_audit = ClientChannelAudit()
    mesh_audit = MeshChannelAudit()
    runtime_thread = None
    server = None
    stream = None
    facade = None
    reader = None
    publisher = None
    source_audit = None
    bridge = None
    client_refs = []
    mesh_close_order: list[dict[str, Any]] = []
    bridge_handler_counts = {"started": 0, "returned": 0, "raised": 0, "active": 0}

    def close_event(event: str, **fields) -> None:
        if len(mesh_close_order) < 32:
            mesh_close_order.append({
                "sequence": len(mesh_close_order) + 1,
                "event": event,
                **fields,
            })

    copies_for_generation: list[list[dict[str, Any]]] = []
    generation_outputs = []
    mesh_metrics = None
    bridge_metrics = None
    terminal_client_snapshot = None
    terminal_bridge_snapshot = None
    runtime_max_clients = None
    runtime_encoded_limit = None
    runtime_cleanup_counts = None
    trial_context = None
    temp = tempfile.TemporaryDirectory(prefix="ao-ws-")
    temp_root = Path(temp.name)
    native_socket = temp_root / "private" / "read.sock"
    mesh_socket = temp_root / "mesh.sock"
    try:
        runtime_thread = RuntimeThread(state, native_socket, Runtime)
        runtime_thread.__enter__()
        runtime_max_clients = runtime_thread.runtime.max_clients
        runtime_encoded_limit = runtime_thread.runtime.encoded_limit

        if variant == "working":
            publisher = make_working_set_publisher(
                "fixture", source_id, native_socket, window_ms=DEFAULT_WINDOW_MS
            )
        else:
            publisher = make_publisher("fixture", source_id, native_socket)
        source_audit = _AuditedCachedSource(publisher.native, scalar_audit)
        publisher.native = source_audit
        publisher = _AuditedCachedPublisher(publisher, published_audit, exception_audit)
        bridge = Bridge(publisher)

        async def serve_with_scalar_audit(channel):
            token = mesh_audit.start(channel)
            bridge_handler_counts["started"] += 1
            bridge_handler_counts["active"] += 1
            close_event("bridge_handler_started")
            try:
                await bridge.serve(channel)
            except BaseException as error:
                bridge_handler_counts["raised"] += 1
                close_event("bridge_serve_raised", errorType=type(error).__name__)
                raise
            else:
                bridge_handler_counts["returned"] += 1
                close_event("bridge_serve_returned")
            finally:
                close_event("bridge_channel_inspect_started")
                try:
                    mesh_audit.finish(channel, token)
                finally:
                    bridge_handler_counts["active"] -= 1
                    try:
                        close_event("bridge_channel_inspect_completed")
                    finally:
                        mesh_audit.after_current_accept_done(token)

        server = await PublicIPCServer(mesh_socket, serve_with_scalar_audit).start()
        codec = profile.bind("fixture", source_id)

        async def connect():
            close_event("public_client_connect_started")
            try:
                channel = await connect_ipc(mesh_socket)
            except BaseException as error:
                exception_audit.record("connect_ipc", error)
                close_event("public_client_connect_raised", errorType=type(error).__name__, code=_safe_protocol_code(error))
                raise
            try:
                client = await Client.connect(
                    channel,
                    host="fixture",
                    source=source_id,
                    profile=profile.descriptor.profile_id,
                    codec=codec.validate_bridge,
                )
            except BaseException as error:
                exception_audit.record("Client.connect", error)
                client_channel_audit.record_failed_connect(channel)
                close_event("public_client_connect_raised", errorType=type(error).__name__, code=_safe_protocol_code(error))
                raise
            if len(client_refs) >= MAX_MESH_CHANNEL_AUDIT:
                close_event("public_client_connection_history_refused")
                try:
                    await client.close()
                except BaseException as error:
                    exception_audit.record("Client.close.history_cap", error)
                    close_event("public_client_history_refusal_close_raised", errorType=type(error).__name__, code=_safe_protocol_code(error))
                    raise
                finally:
                    client_channel_audit.record_refused_connected(client)
                raise HarnessConnectionHistoryBound("public_client_connection_history_refused")
            client_refs.append(client)
            close_event("public_client_connect_returned")
            return client

        revision = "sha256:" + hashlib.sha256(
            f"catalog:{trial_index}:{rows}:{variant}".encode()
        ).hexdigest()

        async def catalog_check():
            return revision

        endpoint = Endpoint("fixture", False, revision, connect, codec)
        reader = Reader(
            "agent", [endpoint], local_host="reader", catalog_revision=revision,
            catalog_check=catalog_check, profile=profile,
        )
        request_id = hashlib.sha256(
            f"working-set-v3:{trial_index}:{rows}:{variant}".encode()
        ).hexdigest()[:32]
        stream = reader.watch_admitted(
            request_id=request_id, proof_interval=.1, catalog_interval=5
        )
        facade = (
            PreparedWorkingSetAgentWatch(request_id, profile=profile, window_ms=DEFAULT_WINDOW_MS)
            if variant == "working"
            else PreparedAgentWatch(request_id, profile=profile)
        )
        rss.append(_read_rss(f"{variant}-{rows}-pipeline-ready"))

        trial_context = {
            "trialIndex": trial_index,
            "variant": variant,
            "variantOrder": list(variant_order),
            "rows": rows,
            "detachedLocalFacadeCopiesPerGeneration": reads_per_generation,
            "events": [],
            "clockAnchors": [],
        }
        V3_CONTEXT.setdefault("trials", []).append(trial_context)
        anchor_sampled_ms = None
        previous_interval = None
        previous_nonce_value = None
        diagnostic_loop = asyncio.get_running_loop()

        for generation in range(generations):
            # Fixture construction is outside the CPU window; accepted producer
            # generation, acquisition, staging, normal admission and facade
            # copies are inside it for a measured matrix run.
            runtime_thread.pause.request_and_wait()
            if not runtime_thread.pause.held:
                raise AssertionError("runtime_selector_barrier_not_held")
            sample = _accepted_sample(template, wall, generation)
            started_cpu = time.process_time_ns() if timed else None
            sample_clock = state.clock()
            if anchor_sampled_ms is None:
                anchor_sampled_ms = sample_clock
            sample_wall = wall + (sample_clock - anchor_sampled_ms)
            sample["collectedAt"] = sample_wall
            if not runtime_thread.pause.held:
                raise AssertionError("runtime_selector_barrier_lost_before_attempt")
            acquisition_started = diagnostic_loop.time()
            acquisition_deadline = (
                acquisition_started + diagnostic_acquisition_timeout
                if diagnostic_acquisition_timeout is not None else None
            )
            state.attempt("codex", "runtime")
            if not runtime_thread.pause.held:
                raise AssertionError("runtime_selector_barrier_lost_before_accept")
            accepted_clock = state.clock()
            accepted = state.accept(
                "codex",
                "runtime",
                sample,
                sampled_ms=sample_clock,
                ttl_ms=120_000,
                accepted_boottime_ms=accepted_clock,
            )
            if accepted is not True:
                raise AssertionError("synthetic_generation_rejected")
            if not runtime_thread.pause.held:
                raise AssertionError("runtime_selector_barrier_lost_after_accept")
            interval_lower = sample_wall - accepted_clock - 1
            interval_upper = sample_wall - sample_clock + 1
            clock_anchor = {
                "fixtureWallMs": wall,
                "firstSampleLowerBoottimeMs": anchor_sampled_ms,
                "sampleLowerBoottimeMs": sample_clock,
                "acceptedUpperBoottimeMs": accepted_clock,
                "syntheticCollectedAtMs": sample_wall,
                "derivedLowerIntervalMs": interval_lower,
                "derivedUpperIntervalMs": interval_upper,
                "overlapsPreviousInterval": (
                    previous_interval is None or max(
                        interval_lower, previous_interval[0]
                    ) <= min(interval_upper, previous_interval[1])
                ),
                "activityTimestampsRenewed": None,
            }
            trial_context["clockAnchors"].append(clock_anchor)
            runtime_thread.pause.resume_and_wait()

            expected_accepted = generation + 1
            expected_rows_count = rows if variant == "full" else SELECTED_COUNTS[rows]
            target_event = None
            target_nonce_value = None
            generation_events = []
            for event_index in range(128):
                if acquisition_deadline is None:
                    event_timeout = 5.0
                else:
                    event_timeout = acquisition_deadline - diagnostic_loop.time()
                    if event_timeout <= 0:
                        _record_failure("ordinary_reader_did_not_admit_fresh_complete_target", {
                            "trialIndex": trial_index, "variant": variant,
                            "rows": rows, "generation": expected_accepted,
                            "lastEvents": generation_events[-16:],
                            "clockBracket": clock_anchor,
                            "acquisitionWaitBudgetSeconds": diagnostic_acquisition_timeout,
                            "acquisitionElapsedSeconds": diagnostic_loop.time() - acquisition_started,
                            "acquisitionTimeoutPhase": "reader_event_outer_deadline",
                        })
                try:
                    frame = await asyncio.wait_for(anext(stream), timeout=event_timeout)
                except asyncio.TimeoutError:
                    if acquisition_deadline is None:
                        raise
                    _record_failure("ordinary_reader_did_not_admit_fresh_complete_target", {
                        "trialIndex": trial_index, "variant": variant,
                        "rows": rows, "generation": expected_accepted,
                        "lastEvents": generation_events[-16:],
                        "clockBracket": clock_anchor,
                        "acquisitionWaitBudgetSeconds": diagnostic_acquisition_timeout,
                        "acquisitionElapsedSeconds": diagnostic_loop.time() - acquisition_started,
                        "acquisitionTimeoutPhase": "reader_event_outer_deadline",
                    })
                facade.accept(frame)
                observed_at_ms = _reader_now()
                event = _event_scalars(frame, observed_at_ms=observed_at_ms)
                event["eventIndex"] = event_index
                generation_events.append(event)
                if len(trial_context["events"]) < MAX_EVENT_AUDIT:
                    trial_context["events"].append({
                        "generation": expected_accepted, **event,
                    })
                if not event.get("headerAvailable"):
                    continue
                event_accepted = event.get("runtimeAccepted")
                if event_accepted is None or event_accepted < expected_accepted:
                    continue
                if event_accepted > expected_accepted:
                    _record_failure("reader_skipped_expected_generation", {
                        "trialIndex": trial_index, "variant": variant,
                        "rows": rows, "generation": expected_accepted,
                        "event": event,
                    })

                if variant == "working":
                    if event.get("clockGeneration") != 0:
                        _record_failure("working_clock_generation_changed", {
                            "trialIndex": trial_index, "variant": variant,
                            "rows": rows, "generation": expected_accepted,
                            "clockBracket": {
                                "sampleWallMs": sample_wall,
                                "lowerBoottimeMs": sample_clock,
                                "upperBoottimeMs": accepted_clock,
                                "intervalLowerMs": sample_wall - accepted_clock - 1,
                                "intervalUpperMs": sample_wall - sample_clock + 1,
                                "previousInterval": previous_interval,
                            },
                            "event": event,
                        })
                    if (event.get("coverageStatus") != "complete"
                            or event.get("scopeMemberCount") != SELECTED_COUNTS[rows]):
                        _record_failure("working_target_generation_incomplete", {
                            "trialIndex": trial_index, "variant": variant,
                            "rows": rows, "generation": expected_accepted,
                            "clockBracket": {
                                "sampleWallMs": sample_wall,
                                "lowerBoottimeMs": sample_clock,
                                "upperBoottimeMs": accepted_clock,
                                "intervalLowerMs": sample_wall - accepted_clock - 1,
                                "intervalUpperMs": sample_wall - sample_clock + 1,
                                "previousInterval": previous_interval,
                            },
                            "event": event,
                        })

                if (event.get("meshStatus") != "complete"
                        or event.get("hostDeliveryStatus") != "ready"
                        or event.get("hostViewState") != "current"):
                    continue
                if not any(item.get("accepted") == expected_accepted
                           and item.get("health") == "current"
                           for item in event.get("receiptRuntime", [])):
                    continue
                if not event.get("proofPresent") or not event.get("proofFresh"):
                    continue
                proof_header = _frame_header(frame) or {}
                proof_hosts = proof_header.get("mesh", {}).get("hosts", [])
                proof_delivery = proof_hosts[0].get("delivery", {}) if proof_hosts else {}
                nonce_value = (proof_delivery.get("proof") or {}).get("nonce")
                if type(nonce_value) is not str or nonce_value == previous_nonce_value:
                    continue
                target_event = event
                target_nonce_value = nonce_value
                previous_nonce_value = nonce_value
                break
            else:
                _record_failure("ordinary_reader_did_not_admit_fresh_complete_target", {
                    "trialIndex": trial_index, "variant": variant,
                    "rows": rows, "generation": expected_accepted,
                    "lastEvents": generation_events[-16:],
                    "clockBracket": {
                        "sampleWallMs": sample_wall,
                        "lowerBoottimeMs": sample_clock,
                        "upperBoottimeMs": accepted_clock,
                        "intervalLowerMs": sample_wall - accepted_clock - 1,
                        "intervalUpperMs": sample_wall - sample_clock + 1,
                        "previousInterval": previous_interval,
                    },
                    "acquisitionWaitBudgetSeconds": diagnostic_acquisition_timeout,
                    "acquisitionElapsedSeconds": diagnostic_loop.time() - acquisition_started,
                })

            for _read in range(reads_per_generation):
                current_now = _reader_now()
                current_clock = _reader_clock()
                if variant == "working":
                    result = facade.read(current_now, current_clock)
                    copied_rows = result.members
                else:
                    result = facade.read(current_now, current_clock)
                    copied_rows = reference.full_consumer_rows({"sessions": result.sessions})
                copies_for_generation.append(copied_rows)
                del result

            cpu_ms = None if started_cpu is None else (
                time.process_time_ns() - started_cpu
            ) / 1_000_000
            # Challenge hashing and public digest cross-check happen after CPU.
            published_audit.seal_pending_nonces()
            target_nonce_hash = hashlib.sha256(target_nonce_value.encode()).hexdigest()
            target_event["proofNonceSha256"] = target_nonce_hash
            target_event["proofNonceFreshFromPreviousGeneration"] = True
            for trace in reversed(trial_context["events"]):
                if (trace.get("generation") == expected_accepted
                        and trace.get("eventIndex") == target_event.get("eventIndex")):
                    trace["proofNonceSha256"] = target_nonce_hash
                    trace["proofNonceFreshFromPreviousGeneration"] = True
                    break
            matched_target_proof = published_audit.matching(
                operation="proof",
                service_id=target_event["serviceId"],
                view_revision=target_event["serviceViewRevision"],
                accepted=expected_accepted,
                owner_sequence=target_event["serviceSequence"],
                native_kind=target_event.get("serviceKind"),
                row_count=expected_rows_count,
                bridge_id=target_event["proofBridgeId"],
                payload_encoded_at_ms=target_event["proofBridgeEncodedAtMs"],
                nonce_sha256=target_nonce_hash,
            )
            if len(matched_target_proof) != 1:
                _record_failure("exact_public_proof_witness_count", {
                    "trialIndex": trial_index, "variant": variant,
                    "rows": rows, "generation": expected_accepted,
                    "event": target_event,
                    "publicProofCandidateCount": len(matched_target_proof),
                    "publicProofCandidates": matched_target_proof,
                })
            if matched_target_proof[0]["ownerDigest"] != target_event["proofPayloadDigest"]:
                _record_failure("delivered_proof_digest_does_not_match_publisher", {
                    "trialIndex": trial_index, "variant": variant,
                    "rows": rows, "generation": expected_accepted,
                    "event": target_event,
                    "publicProofCandidates": matched_target_proof,
                })
            source_matches = scalar_audit.matching(
                operation="snapshot",
                service_id=target_event["serviceId"],
                view_revision=target_event["serviceViewRevision"],
                accepted=expected_accepted,
                owner_sequence=target_event["serviceSequence"],
                native_kind=target_event.get("serviceKind"),
                row_count=expected_rows_count,
            )
            if not source_matches:
                _record_failure("native_source_scalar_witness_missing", {
                    "trialIndex": trial_index, "variant": variant,
                    "rows": rows, "generation": expected_accepted,
                    "event": target_event,
                })
            activity_signature = tuple(
                (reference.native_id(row), row["activity"].get("at"),
                 row["activity"].get("health"), row["activity"].get("source"),
                 row["activity"].get("reason"))
                for row in sample["sessions"]
            )
            activity_timestamps_renewed = activity_signature != fixture_activity_signature
            if activity_timestamps_renewed:
                raise AssertionError("synthetic_activity_T_changed")
            rss.append(_read_rss(
                f"{variant}-{rows}-generation-{generation + 1}-{reads_per_generation}-reads"
            ))

            detached_lists, detached_rows = _assert_detached(copies_for_generation)
            if reads_per_generation and (not detached_lists or not detached_rows):
                raise AssertionError("facade_reads_not_detached")

            # Derive exact expected DTOs from the producer's accepted full
            # source view, using the independent reference filter after the
            # CPU window. The fixture's expected IDs were fixed pre-window.
            full_frame = state.frame("status", generation + 1)
            if full_frame.get("snapshot") is None:
                raise AssertionError("accepted_full_snapshot_missing")
            full_rows = full_frame["snapshot"]["sessions"]
            expected_rows = reference.full_consumer_rows({"sessions": full_rows})
            expected_ids = [reference.native_id(row) for row in expected_rows]
            expected_hash = reference.digest(expected_rows, canonical)
            expected_ids_hash = reference.digest(expected_ids, canonical)
            if expected_ids != fixture_expected_ids:
                raise AssertionError("accepted_full_filter_ids_differ_from_fixture")
            if len(expected_rows) != SELECTED_COUNTS[rows]:
                raise AssertionError("accepted_full_filter_count_mismatch")
            verification_rows = None
            verification_read_outside_cpu = reads_per_generation == 0
            if verification_read_outside_cpu:
                current_now = _reader_now()
                current_clock = _reader_clock()
                result = facade.read(current_now, current_clock)
                if variant == "working":
                    verification_rows = result.members
                else:
                    verification_rows = reference.full_consumer_rows({"sessions": result.sessions})
                del result
                if verification_rows != expected_rows:
                    raise AssertionError("outside_window_facade_verification_mismatch")
            for copied_rows in copies_for_generation:
                if copied_rows != expected_rows:
                    raise AssertionError("full_and_working_dto_mismatch")
                if reference.digest(copied_rows, canonical) != expected_hash:
                    raise AssertionError("facade_dto_hash_mismatch")
                if [reference.native_id(row) for row in copied_rows] != expected_ids:
                    raise AssertionError("facade_identity_order_mismatch")

            # The Mesh response's detached export is used only after CPU
            # accounting. Its service identity/revision/count must match the
            # native IPC scalar audit, and its DTOs must match the direct full
            # Runtime view or its independently selected working-set rows.
            response = facade.snapshot()
            host_record = response["mesh"]["hosts"][0]
            native = reconstructed(response, host_record, profile=profile)
            native_hash = _digest(native, canonical)
            native_owner_digest = mesh_digest(native)
            matched_native = scalar_audit.matching(
                operation="snapshot",
                service_id=native["serviceId"],
                view_revision=native["viewRevision"],
                accepted=expected_accepted,
                owner_sequence=native["sequence"],
                native_kind=native["kind"],
                row_count=_frame_row_count(native),
            )
            if not matched_native:
                raise AssertionError("mesh_reconstruction_not_equal_to_native_ipc_frame")
            delivered_proof = target_event
            matched_published = published_audit.matching(
                operation="proof",
                service_id=native["serviceId"],
                view_revision=native["viewRevision"],
                accepted=expected_accepted,
                owner_sequence=native["sequence"],
                native_kind=native["kind"],
                row_count=_frame_row_count(native),
                bridge_id=delivered_proof["proofBridgeId"],
                payload_encoded_at_ms=delivered_proof["proofBridgeEncodedAtMs"],
                nonce_sha256=delivered_proof["proofNonceSha256"],
            )
            if len(matched_published) != 1:
                raise AssertionError("mesh_reconstruction_not_matched_to_public_owner_digest")
            if native_owner_digest != matched_published[0]["ownerDigest"]:
                raise AssertionError("mesh_reconstructed_native_public_digest_mismatch")
            if variant == "working":
                native_rows = native["projection"]["sessions"]
                if native_rows != expected_rows:
                    raise AssertionError("native_working_set_dto_mismatch")
                if host_record["owner"]["metadata"]["scopes"][0]["coverage"]["status"] != "complete":
                    raise AssertionError("working_set_coverage_not_complete")
            else:
                native_rows = native["snapshot"]["sessions"]
                if native_rows != full_rows:
                    raise AssertionError("native_full_dto_mismatch")
                if reference.full_consumer_rows({"sessions": native_rows}) != expected_rows:
                    raise AssertionError("native_full_selection_mismatch")

            clock_anchor["activityTimestampsRenewed"] = activity_timestamps_renewed
            generation_outputs.append({
                "generation": expected_accepted,
                "accepted": True,
                "targetEvent": target_event,
                "rowsInNativeFullInput": rows,
                "selectedRows": len(expected_rows),
                "expectedIds": expected_ids,
                "expectedIdsSha256": expected_ids_hash,
                "expectedDtoSha256": expected_hash,
                "inputFixtureExpectedIdsSha256": fixture_expected_ids_hash,
                "inputFixtureExpectedDtoSha256": fixture_expected_hash,
                "acceptedFullDtoSha256": reference.digest(full_rows, canonical),
                "facadeReads": reads_per_generation,
                "facadeReadDtoSha256": [reference.digest(value, canonical)
                                         for value in copies_for_generation],
                "facadeVerificationReadOutsideCpu": verification_read_outside_cpu,
                "facadeVerificationDtoSha256": (
                    None if verification_rows is None
                    else reference.digest(verification_rows, canonical)
                ),
                "detachedLists": detached_lists,
                "detachedRows": detached_rows,
                "reconstructedNativeFrameSha256": native_hash,
                "reconstructedNativeOwnerDigest": native_owner_digest,
                "nativeFrameAudit": matched_native,
                "nativeScalarCandidatesForProofFrame": source_matches,
                "publicPublisherDigestAudit": matched_published[0],
                "generationProcessCpuMs": cpu_ms,
                "clockAnchor": clock_anchor,
            })
            previous_interval = (
                sample_wall - accepted_clock - 1,
                sample_wall - sample_clock + 1,
            )
            copies_for_generation.clear()
            copied_rows = None
            del native, response, host_record, native_rows, sample, frame
            del full_frame, full_rows, expected_rows, expected_ids, expected_hash, expected_ids_hash
            if verification_rows is not None:
                del verification_rows
            rss.append(_read_rss(f"{variant}-{rows}-generation-{generation + 1}-copies-released"))

        # Capture all required public counters before shutdown, once every
        # generation, proof, DTO comparison, and facade read has completed.
        close_event("pre_shutdown_public_metrics_started")
        pre_reader_raw = reader.inspect()
        pre_client_snapshot = _client_channel_snapshot(client_refs, client_channel_audit)
        pre_bridge_snapshot = mesh_audit.snapshot()
        pre_shutdown = {
            "reader": _channel_metrics(pre_reader_raw),
            "readerState": {
                "partial": pre_reader_raw["partial"],
                "uninstrumentedConnections": pre_reader_raw["uninstrumentedConnections"],
                "activeConnections": pre_reader_raw["activeConnections"],
                "connectionsOpened": pre_reader_raw["connectionsOpened"],
                "connectionsClosed": pre_reader_raw["connectionsClosed"],
                "cleanupFailures": pre_reader_raw["cleanupFailures"],
            },
            "clients": pre_client_snapshot,
            "bridge": pre_bridge_snapshot["metrics"],
            "bridgeAudit": pre_bridge_snapshot,
            "bridgeHandlerCounts": dict(bridge_handler_counts),
        }
        trial_context["preShutdownPublicCounters"] = pre_shutdown
        close_event("pre_shutdown_public_metrics_completed")

        close_event("facade_disconnect_started")
        facade.disconnect()
        close_event("facade_disconnect_completed")
        close_event("reader_stream_aclose_started")
        await stream.aclose()
        close_event("reader_stream_aclose_completed")
        stream = None
        facade = None
        if server is not None:
            close_event("ipc_server_close_started")
            await server.close()
            close_event("ipc_server_close_completed")
        server = None
        published_audit.seal_pending_nonces()
        mesh_metrics = reader.inspect()
        post_client_snapshot = _client_channel_snapshot(client_refs, client_channel_audit)
        post_bridge_snapshot = mesh_audit.snapshot()
        terminal_client_snapshot = post_client_snapshot
        terminal_bridge_snapshot = post_bridge_snapshot
        bridge_metrics = post_bridge_snapshot["metrics"]
        client_channel_metrics = post_client_snapshot["accepted"]
        post_shutdown = {
            "reader": _channel_metrics(mesh_metrics),
            "readerState": {
                "partial": mesh_metrics["partial"],
                "uninstrumentedConnections": mesh_metrics["uninstrumentedConnections"],
                "activeConnections": mesh_metrics["activeConnections"],
                "connectionsOpened": mesh_metrics["connectionsOpened"],
                "connectionsClosed": mesh_metrics["connectionsClosed"],
                "cleanupFailures": mesh_metrics["cleanupFailures"],
            },
            "clients": post_client_snapshot,
            "bridge": bridge_metrics,
            "bridgeAudit": post_bridge_snapshot,
            "bridgeHandlerCounts": dict(bridge_handler_counts),
        }
        trial_context["postShutdownPublicCounters"] = post_shutdown
        mesh_byte_diagnostic = {
            "scope": "partial completed application-level JSON-line counters from public Reader, Client LineChannel, and Bridge IPCServer channels; not raw wire bytes or proof of peer parsing",
            "preShutdown": pre_shutdown,
            "postShutdown": post_shutdown,
            "publicClientChannel": client_channel_metrics,
            "publicClientAllAttemptChannels": post_client_snapshot["all"],
            "bridge": bridge_metrics,
            "bridgeConnections": post_bridge_snapshot["connections"],
            "bridgeOverflow": post_bridge_snapshot["overflowMetrics"],
            "closeOrder": mesh_close_order,
            "publicExceptionAudit": {
                "records": exception_audit.records,
                "droppedRecords": exception_audit.dropped,
                "messageOrTracebackRetained": False,
            },
            "publicClientConnectionReferencesRetained": len(client_refs),
            "boundedConnectionHistory": MAX_MESH_CHANNEL_AUDIT,
        }
        trial_context["byteDiagnostic"] = mesh_byte_diagnostic
        source_cleanup = source_audit.outstanding()
        if source_cleanup != {
            "activeSourceOperations": 0,
            "pendingSnapshotCalls": 0,
            "openWatchIterators": 0,
        }:
            raise AssertionError("cached_source_calls_not_retired")
        if mesh_metrics["activeConnections"] != 0 or mesh_metrics["cleanupFailures"] != 0:
            raise AssertionError("reader_connections_not_retired")
        if runtime_thread is not None:
            runtime_thread.__exit__(None, None, None)
            runtime_cleanup = runtime_thread.cleanup_counts
            runtime_cleanup_counts = runtime_cleanup
            runtime_thread = None
        else:
            runtime_cleanup = None
        cleanup_counts = {
            "readerActiveConnections": mesh_metrics["activeConnections"],
            "readerConnectionsOpened": mesh_metrics["connectionsOpened"],
            "readerConnectionsClosed": mesh_metrics["connectionsClosed"],
            "readerCleanupFailures": mesh_metrics["cleanupFailures"],
            "cachedSourceWrapper": source_cleanup,
            "runtime": runtime_cleanup,
            "bridgeHandlersStarted": sum(
                event["event"] == "bridge_handler_started" for event in mesh_close_order
            ),
            "bridgeHandlersReturned": sum(
                event["event"] == "bridge_serve_returned" for event in mesh_close_order
            ),
            "bridgeHandlersRaised": sum(
                event["event"] == "bridge_serve_raised" for event in mesh_close_order
            ),
            "bridgeActiveHandlers": bridge_handler_counts["active"],
            "retainedReaderClients": len(client_refs),
            "retainedBridgeChannels": mesh_audit.retained_channel_references,
            "failedPublicConnects": client_channel_audit.failedConnectCount,
            "refusedConnectedClients": client_channel_audit.refusedConnectedCount,
            "bridgeOverflowConnections": mesh_audit.overflowConnections,
            "nativeSourcePrivateActivePendingCountersRead": False,
        }
        mesh_byte_diagnostic["cleanupCounts"] = cleanup_counts
        metric_failure = _classify_mesh_byte_delivery(
            mesh_byte_diagnostic, cleanup_counts
        )
        mesh_byte_diagnostic["totalDelivery"] = {
            "basis": "sum of all completed sender counters and validated receiver counters across public channels, including terminal shutdown, failed/refused attempts, and any completed in-flight writes; not raw socket bytes or proof of peer parsing",
            "completedSenderBytes": bridge_metrics["sentBytes"] + post_client_snapshot["all"]["sentBytes"],
            "completedSenderFrames": bridge_metrics["sentFrames"] + post_client_snapshot["all"]["sentFrames"],
            "validatedReceiverBytes": bridge_metrics["receivedBytes"] + post_client_snapshot["all"]["receivedBytes"],
            "validatedReceiverFrames": bridge_metrics["receivedFrames"] + post_client_snapshot["all"]["receivedFrames"],
        }
        if metric_failure is not None:
            _record_failure(metric_failure, {
                "trialIndex": trial_index, "variant": variant,
                "rows": rows, "byteDiagnostic": mesh_byte_diagnostic,
            }, defer=True)
        client_refs.clear()

        return {
            "trialIndex": trial_index,
            "variant": variant,
            "variantOrder": list(variant_order),
            "rows": rows,
            "selectedRows": SELECTED_COUNTS[rows],
            "windowMs": WINDOW_MS,
            "trialAudit": trial_context,
            "generations": generation_outputs,
            "meshPublicCompletedJsonLineCounters": {
                "scope": "partial public application-channel counters from IPCServer, Client LineChannel, and Reader.inspect; write completion/validated receive, not raw wire or proof of peer parsing",
                "bridge": bridge_metrics,
                "reader": {
                    "sentFrames": mesh_metrics["sentFrames"],
                    "sentBytes": mesh_metrics["sentBytes"],
                    "receivedFrames": mesh_metrics["receivedFrames"],
                    "receivedBytes": mesh_metrics["receivedBytes"],
                    "byteScope": mesh_metrics["byteScope"],
                },
                "bidirectionalByteCountsMatch": mesh_byte_diagnostic[
                    "bidirectionalByteCountsMatch"
                ],
                "completedSenderBytes": mesh_byte_diagnostic["totalDelivery"][
                    "completedSenderBytes"
                ],
                "completedSenderFrames": mesh_byte_diagnostic["totalDelivery"][
                    "completedSenderFrames"
                ],
                "validatedReceiverBytes": mesh_byte_diagnostic["totalDelivery"][
                    "validatedReceiverBytes"
                ],
                "terminalCloseOnlyDelta": mesh_byte_diagnostic[
                    "terminalCloseOnlyDelta"
                ],
                "physicalOrRawSocketDeliveryClaimed": False,
            },
            "meshByteDiagnostic": mesh_byte_diagnostic,
            "ownerNativeIpcWrittenBytes": {
                "value": None,
                "reason": "Observer Runtime has no public completed native-IPC write-byte counter",
                "availableDiagnostic": "bounded operation, service, revision, accepted-generation and row-count scalars only; no canonical size is labeled as wire bytes",
            },
            "nativeScalarAudit": {
                "snapshots": scalar_audit.snapshots,
                "watchFrames": scalar_audit.watchFrames,
                "retainedRecords": len(scalar_audit.frames),
                "retainedFullFrames": False,
                "frames": scalar_audit.frames,
            },
            "publicPublisherOwnerDigestAudit": {
                "retainedRecords": len(published_audit.envelopes),
                "retainedFullFrames": False,
                "envelopes": published_audit.envelopes,
                "witnessBasis": "public CachedPublisher envelope ownerDigest; canonical hash of reconstructed native frame compared outside CPU window",
                "rawSocketByteIdentityClaimed": False,
            },
            "cleanupCounts": cleanup_counts,
            "limits": {
                "workingSetLedgerBytes": MAX_LEDGER_BYTES,
                "workingSetMaxIdentities": MAX_IDENTITIES,
                "workingSetFrameBytes": MAX_FRAME_BYTES,
                "serviceRuntimeEncodedBytes": runtime_encoded_limit,
                "serviceRuntimeMaxClients": runtime_max_clients,
                "experimentalSync": False,
            },
            "sourceInputs": source_inputs,
        }
    finally:
        if facade is not None:
            facade.disconnect()
        if stream is not None:
            await stream.aclose()
        if server is not None:
            close_event("ipc_server_close_started")
            await server.close()
            close_event("ipc_server_close_completed")
        if runtime_thread is not None:
            runtime_thread.__exit__(None, None, None)
            runtime_cleanup_counts = runtime_thread.cleanup_counts
        if reader is not None and mesh_metrics is None:
            mesh_metrics = reader.inspect()
        if terminal_client_snapshot is None:
            try:
                terminal_client_snapshot = _client_channel_snapshot(
                    client_refs, client_channel_audit
                )
            except Exception as error:
                terminal_client_snapshot = {
                    "captureErrorType": type(error).__name__,
                    "messageOrTracebackRetained": False,
                }
        if terminal_bridge_snapshot is None:
            try:
                terminal_bridge_snapshot = mesh_audit.snapshot()
            except Exception as error:
                terminal_bridge_snapshot = {
                    "captureErrorType": type(error).__name__,
                    "messageOrTracebackRetained": False,
                }
        # Keep only scalar audit outputs. Owner, Reader, input, oracle, and all
        # detached rows are released before the final post-cleanup RSS sample.
        copies_for_generation.clear()
        copied_rows = None
        retained_reader_client_count = len(client_refs)
        client_refs.clear()
        del state, template, fixture_expected_rows, fixture_expected_ids
        del fixture_expected_hash, fixture_expected_ids_hash
        profile = publisher = bridge = reader = runtime_thread = None
        temp.cleanup()
        rss.append(_read_rss(f"{variant}-{rows}-cleanup-complete"))
        if trial_context is not None:
            cleanup_mesh = mesh_metrics
            cleanup_source = None if source_audit is None else source_audit.outstanding()
            trial_context["cleanupCounts"] = {
                "readerActiveConnections": (
                    None if cleanup_mesh is None else cleanup_mesh["activeConnections"]
                ),
                "readerConnectionsOpened": (
                    None if cleanup_mesh is None else cleanup_mesh["connectionsOpened"]
                ),
                "readerConnectionsClosed": (
                    None if cleanup_mesh is None else cleanup_mesh["connectionsClosed"]
                ),
                "readerCleanupFailures": (
                    None if cleanup_mesh is None else cleanup_mesh["cleanupFailures"]
                ),
                "cachedSourceWrapper": cleanup_source,
                "runtime": runtime_cleanup_counts,
                "bridgeHandlersStarted": sum(
                    event["event"] == "bridge_handler_started" for event in mesh_close_order
                ),
                "bridgeHandlersReturned": sum(
                    event["event"] == "bridge_serve_returned" for event in mesh_close_order
                ),
                "bridgeHandlersRaised": sum(
                    event["event"] == "bridge_serve_raised" for event in mesh_close_order
                ),
                "bridgeActiveHandlers": bridge_handler_counts["active"],
                "retainedReaderClients": retained_reader_client_count,
                "retainedBridgeChannels": mesh_audit.retained_channel_references,
                "failedPublicConnects": client_channel_audit.failedConnectCount,
                "refusedConnectedClients": client_channel_audit.refusedConnectedCount,
                "bridgeOverflowConnections": mesh_audit.overflowConnections,
                "privateNativeSourceActivePendingCountersRead": False,
            }
            trial_context["boundedAudits"] = {
                "nativeScalar": {
                    "snapshots": scalar_audit.snapshots,
                    "watchFrames": scalar_audit.watchFrames,
                    "records": scalar_audit.frames,
                    "retainedFullFrames": False,
                },
                "publicPublisherDigest": {
                    "records": published_audit.envelopes,
                    "retainedFullFrames": False,
                    "rawNoncesRetainedAtReport": False,
                },
                "meshChannels": terminal_bridge_snapshot,
                "publicExceptions": {
                    "records": exception_audit.records,
                    "droppedRecords": exception_audit.dropped,
                    "messageOrTracebackRetained": False,
                },
                "publicClientChannels": terminal_client_snapshot,
            }


class _AuditedCachedSource:
    """Source-interface wrapper with bounded frame and call-lifetime audit."""

    def __init__(self, source, audit: NativeScalarAudit):
        self.source, self.audit = source, audit
        self._active_source_operations = 0
        self._pending_snapshot_calls = 0
        self._open_watch_iterators = 0

    async def snapshot(self):
        self._active_source_operations += 1
        self._pending_snapshot_calls += 1
        try:
            return await self.audit.snapshot(self.source)
        finally:
            self._pending_snapshot_calls -= 1
            self._active_source_operations -= 1

    def watch(self):
        return self._watch()

    async def _watch(self):
        self._active_source_operations += 1
        self._open_watch_iterators += 1
        iterator = self.source.watch().__aiter__()
        try:
            async for publication in iterator:
                self.audit.record("watch", publication.frame)
                yield publication
        finally:
            try:
                close = getattr(iterator, "aclose", None)
                if callable(close):
                    await close()
            finally:
                self._open_watch_iterators -= 1
                self._active_source_operations -= 1

    def outstanding(self) -> dict[str, int]:
        return {
            "activeSourceOperations": self._active_source_operations,
            "pendingSnapshotCalls": self._pending_snapshot_calls,
            "openWatchIterators": self._open_watch_iterators,
        }


def _preflight(args, timed: bool) -> tuple[dict[str, Any], Any]:
    _insert_import_roots(args.observer_source, args.observer_tests, args.mesh_source)
    reference = _load_reference(args.matched_source)
    from mesh_plus.api import SDK_INTERFACE_VERSION, descriptor
    from agent_observer.working_set_contract import MAX_IDENTITIES, MAX_LEDGER_BYTES
    from agent_observer.active_contract import MAX_FRAME_BYTES
    from agent_observer.working_set_policy import DEFAULT_WINDOW_MS
    from agent_observer.mesh_working_set_profile import WorkingSetAgentProfile

    expected = dict(EXPECTED_LIMITS)
    actual = {
        "ledgerBytes": MAX_LEDGER_BYTES,
        "identities": MAX_IDENTITIES,
        "frameBytes": MAX_FRAME_BYTES,
        "encodedBytes": EXPECTED_LIMITS["encodedBytes"],
        "serviceClients": EXPECTED_LIMITS["serviceClients"],
    }
    if actual != expected:
        raise ValueError(f"source_limits_changed:{actual}")
    if DEFAULT_WINDOW_MS != WINDOW_MS or SDK_INTERFACE_VERSION != 1:
        raise ValueError("working_set_sdk_preflight_mismatch")
    working_descriptor = descriptor("agent", profile_id="agent-observer.mesh-working-set.v1")
    profile = WorkingSetAgentProfile(WINDOW_MS)
    if profile.descriptor != working_descriptor or working_descriptor.frame_bytes != EXPECTED_LIMITS["frameBytes"]:
        raise ValueError("registered_working_set_descriptor_mismatch")
    pair = f"{args.observer_id}+{args.mesh_id}"
    if pair != f"{DEFAULT_OBSERVER_ID}+{DEFAULT_MESH_ID}":
        raise ValueError("only_the_final_approved_immutable_source_pair_is_supported")
    if (args.observer_source.resolve() != DEFAULT_OBSERVER_SOURCE.resolve()
            or args.observer_tests.resolve() != DEFAULT_OBSERVER_TESTS.resolve()
            or args.mesh_source.resolve() != DEFAULT_MESH_SOURCE.resolve()
            or args.matched_source.resolve() != DEFAULT_MATCHED_SOURCE.resolve()):
        raise ValueError("source_paths_must_match_the_final_approved_pair")
    if args.approved_source_pair != pair:
        raise ValueError("requires_root_approved_exact_source_pair")

    fixture_paths = {
        "matchedReference": args.matched_source,
        "serviceRuntimeFixture": args.observer_tests / "test_service_runtime.py",
        "serviceStateFixture": args.observer_tests / "test_service_state.py",
    }
    for path in fixture_paths.values():
        if not path.is_file():
            raise ValueError(f"fixture_input_missing:{path}")
    source_inputs = {
        "observerId": args.observer_id,
        "meshId": args.mesh_id,
        "observerSource": str(args.observer_source.resolve()),
        "meshSource": str(args.mesh_source.resolve()),
        "fixtureInputs": {key: {"path": str(path), "sha256": _sha256(path)}
                           for key, path in fixture_paths.items()},
        "limits": actual,
        "windowMs": WINDOW_MS,
        "meshWorkingSetProfile": working_descriptor.profile_id,
        "meshSdkVersion": SDK_INTERFACE_VERSION,
        "approvedSourcePair": pair,
    }
    return source_inputs, reference


def _parse_variant_order(value: str) -> list[str]:
    variants = value.split(",")
    if not variants or any(item not in {"full", "working"} for item in variants):
        raise argparse.ArgumentTypeError("variant order must contain full and/or working")
    if variants.count("full") != variants.count("working") or not variants.count("full"):
        raise argparse.ArgumentTypeError("variant order needs equal positive full/working counts")
    return variants


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("functional", "diagnostic", "trial"), default="functional")
    parser.add_argument("--observer-source", type=Path, default=DEFAULT_OBSERVER_SOURCE)
    parser.add_argument("--observer-tests", type=Path, default=DEFAULT_OBSERVER_TESTS)
    parser.add_argument("--mesh-source", type=Path, default=DEFAULT_MESH_SOURCE)
    parser.add_argument("--matched-source", type=Path, default=DEFAULT_MATCHED_SOURCE)
    parser.add_argument("--observer-id", default=DEFAULT_OBSERVER_ID)
    parser.add_argument("--mesh-id", default=DEFAULT_MESH_ID)
    parser.add_argument("--approved-source-pair", default=None)
    parser.add_argument("--reads-per-generation", type=int, choices=(0, 1, 4, 16), default=4)
    parser.add_argument("--variant-order", type=_parse_variant_order,
                        default=_parse_variant_order("full,working"))
    parser.add_argument("--diagnostic-variant", choices=("full", "working"), default="full")
    parser.add_argument("--diagnostic-rows", type=int, choices=(100, 500, 2000), default=2000)
    parser.add_argument("--trial-variant", choices=("full", "working"), default="full")
    parser.add_argument("--trial-rows", type=int, choices=(500, 2000), default=500)
    parser.add_argument("--trial-index", type=int, default=None)
    parser.add_argument("--complete-pair-after-byte-mismatch", action="store_true",
                        help="diagnostic only: record byte mismatch, finish both functional variants, then exit failed")
    parser.add_argument("--output", type=Path, default=None)
    return parser


async def _run(args) -> dict[str, Any]:
    if args.mode == "functional":
        rows, generations, reads, timed = 100, 3, 4, False
        if args.reads_per_generation != 4:
            raise ValueError("functional_mode_is_fixed_at_four_facade_reads")
        variant_order = args.variant_order
        if sorted(variant_order) != ["full", "working"]:
            raise ValueError("functional_mode_requires_one_full_and_one_working_trial")
        diagnostic_acquisition_timeout = None
    elif args.mode == "diagnostic":
        rows, generations, reads, timed = args.diagnostic_rows, 3, 4, False
        variant_order = [args.diagnostic_variant]
        diagnostic_acquisition_timeout = 15.0
    elif args.mode == "trial":
        rows, generations, reads, timed = args.trial_rows, 3, 4, True
        variant_order = args.variant_order
        diagnostic_acquisition_timeout = 15.0
        if args.trial_index is None or args.trial_index < 0:
            raise ValueError("trial_mode_requires_nonnegative_trial_index")
        V3_CONTEXT.update({
            "trialIndex": args.trial_index,
            "trialVariant": args.trial_variant,
            "trialRows": args.trial_rows,
            "workloadPattern": "one public Reader.watch_admitted generation plus four detached local facade copies per synthetic generation",
        })
    else:
        raise ValueError("unsupported_mode")
    if args.complete_pair_after_byte_mismatch and args.mode != "functional":
        raise ValueError("complete_pair_after_byte_mismatch_requires_untimed_functional_mode")
    source_inputs, reference = _preflight(args, timed=timed)
    V3_CONTEXT.update({
        "mode": args.mode,
        "sourcePair": f"{args.observer_id}+{args.mesh_id}",
        "observerSource": str(args.observer_source.resolve()),
        "meshSource": str(args.mesh_source.resolve()),
        "detachedLocalFacadeCopiesPerGeneration": reads,
        "variantOrder": list(variant_order),
        "timed": timed,
        "diagnosticAcquisitionTimeoutSeconds": diagnostic_acquisition_timeout,
        "completePairAfterByteMismatch": args.complete_pair_after_byte_mismatch,
        "sourceInputs": source_inputs,
    })
    rss = [_read_rss("preflight-imports-complete")]
    cases = []
    trial_index = 0
    for row_count in ((rows,) if type(rows) is int else rows):
        trial_variants = [args.trial_variant] if args.mode == "trial" else variant_order
        for variant in trial_variants:
            case = await _run_variant(
                variant=variant,
                rows=row_count,
                generations=generations,
                reads_per_generation=reads,
                trial_index=(args.trial_index if args.mode == "trial" else trial_index),
                variant_order=variant_order,
                timed=timed,
                diagnostic_acquisition_timeout=diagnostic_acquisition_timeout,
                complete_pair_after_byte_mismatch=args.complete_pair_after_byte_mismatch,
                source_inputs=source_inputs,
                reference=reference,
                rss=rss,
            )
            cases.append(case)
            trial_index += 1
    loaded = _capture_project_modules(args.observer_source, args.mesh_source)
    source_module_map_sha = hashlib.sha256(
        json.dumps(loaded, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    return {
        "format": "agent-observer.working-set.sdk-pipeline-matrix.v3.6",
        "classification": "controlled synthetic SDK1 remote-proof semantics over same-process trusted local IPC",
        "mode": args.mode,
        "timed": timed,
        "cyclicGc": {
            "enabled": gc.isenabled(),
            "explicitCollections": 0,
            "physicalRetirementClaim": False,
            "v1Note": "v1 invoked gc.collect during generation cleanup; its RSS snapshots are not evidence of physical object retirement",
        },
        "sourcePair": f"{args.observer_id}+{args.mesh_id}",
        "sourceModuleMapSha256": source_module_map_sha,
        "loadedProjectModules": loaded,
        "cases": cases,
        "rssSnapshots": rss,
        "rssScope": "single process; includes input, oracle, Runtime, native source, Mesh Reader, admitted state and facade copies",
        "configuredShape": {
            "rows": [rows] if type(rows) is int else list(rows),
            "selectedRowsByRows": {str(key): value for key, value in SELECTED_COUNTS.items()},
            "generations": generations,
            "detachedLocalFacadeCopiesPerGeneration": reads,
            "deliveryPattern": "one public Reader.watch_admitted generation followed by local facade reads/copies; copy cadence does not create independent native or SDK deliveries or simultaneous clients",
            "variantOrder": list(variant_order),
            "diagnosticAcquisitionTimeoutSeconds": diagnostic_acquisition_timeout,
        },
        "exclusions": [
            "No native provider invocation or independent provider evidence",
            "No installed wheel or selected service process",
            "No SSH transport, remote authentication, external fleet/catalog authority, WSS or network listener; Endpoint(local=False) exercises public remote proof/expiry semantics over trusted local IPC with a fixed synthetic catalog check",
            "Functional and diagnostic modes are untimed; diagnostic uses one chosen row count, one variant, three generations, four facade reads and the existing 15-second outer Reader-acquisition budget; timed trial mode also retains that limit and ordinary Mesh deadlines",
            "Observer Runtime native IPC written-byte totals are unavailable without a public byte counter",
            "Mesh public completed JSON-line counters are partial application-channel sender writes and validated receives, reported by phase/kind/connection and independent of local facade-copy cadence; counter equality is diagnostic only, not raw wire or peer-parse evidence",
            "Detached local facade copies are a separate workload from read_matched.py's four serialized consumer reads per generation",
            "Canonical native-frame size diagnostics are not labeled as actual wire bytes",
            "No retained full native frame or row roster in measurement audit",
            "Public ownerDigest witness is an already-computed CachedPublisher envelope digest, not raw native socket byte identity",
            "A test-only selector.select boundary pause synchronizes synthetic ServiceState attempt/accept; no production admission guard/API is added",
            "Native source active/pending implementation counters are not read; only wrapper-observed outstanding calls and iterator cleanup are reported",
            "Diagnostic and timed-trial acquisition budgets bound only the harness wait for an ordinary public Reader event to the existing 15-second outer limit; they do not extend or replace proof, line, service, or producer deadlines",
            "Cyclic GC is disabled and no explicit collection occurs; process RSS does not establish physical retirement",
            "No delta-sync or 32/64 MiB sync resource path",
            "No deployment, selection, rollback, consumer adoption or device acceptance",
        ],
    }


def main() -> int:
    args = _parser().parse_args()
    try:
        result = asyncio.run(_run(args))
    except Exception as error:
        try:
            loaded_after_failure = _capture_project_modules(args.observer_source, args.mesh_source)
            loaded_after_failure_sha = hashlib.sha256(
                json.dumps(loaded_after_failure, sort_keys=True, separators=(",", ":")).encode()
            ).hexdigest()
        except Exception:
            loaded_after_failure, loaded_after_failure_sha = None, None
        failure = {
            "format": "agent-observer.working-set.sdk-pipeline-matrix.v3.6.failure",
            "errorType": type(error).__name__,
            "code": _safe_failure_code(error),
            "context": V3_CONTEXT,
            "failures": V3_FAILURES,
            "loadedProjectModules": loaded_after_failure,
            "sourceModuleMapSha256": loaded_after_failure_sha,
            "cyclicGc": {
                "enabled": gc.isenabled(),
                "explicitCollections": 0,
                "physicalRetirementClaim": False,
            },
            "sensitivePayloadsRetainedOrReported": False,
        }
        if args.output is not None:
            target = args.output.resolve()
            if not target.is_relative_to(PRIVATE_ROOT):
                print(json.dumps({"error": "output_must_remain_private"}, sort_keys=True))
                return 2
            _write_private_output(target, json.dumps(failure, sort_keys=True, indent=2) + "\n")
            failure["output"] = str(target)
        print(json.dumps(failure, sort_keys=True))
        return 1
    if V3_FAILURES:
        failure = {
            "format": "agent-observer.working-set.sdk-pipeline-matrix.v3.6.failure",
            "errorType": "AssertionError",
            "code": V3_FAILURES[0]["code"],
            "context": V3_CONTEXT,
            "failures": V3_FAILURES,
            "diagnosticResult": result,
            "loadedProjectModules": result["loadedProjectModules"],
            "sourceModuleMapSha256": result["sourceModuleMapSha256"],
            "cyclicGc": result["cyclicGc"],
            "sensitivePayloadsRetainedOrReported": False,
        }
        if args.output is not None:
            target = args.output.resolve()
            if not target.is_relative_to(PRIVATE_ROOT):
                print(json.dumps({"error": "output_must_remain_private"}, sort_keys=True))
                return 2
            _write_private_output(target, json.dumps(failure, sort_keys=True, indent=2) + "\n")
            summary = {
                "status": "failed_diagnostic_complete",
                "code": failure["code"],
                "failures": [item["code"] for item in V3_FAILURES],
                "output": str(target),
                "timed": result["timed"],
                "cases": [
                    {
                        "variant": case["variant"],
                        "rows": case["rows"],
                        "generations": len(case["generations"]),
                        "bidirectionalByteCountsMatch": case[
                            "meshPublicCompletedJsonLineCounters"
                        ]["bidirectionalByteCountsMatch"],
                    }
                    for case in result["cases"]
                ],
            }
            print(json.dumps(summary, sort_keys=True, indent=2))
        else:
            print(json.dumps(failure, sort_keys=True))
        return 1
    output = json.dumps(result, sort_keys=True, indent=2) + "\n"
    if args.output is not None:
        target = args.output.resolve()
        if not target.is_relative_to(PRIVATE_ROOT):
            print(json.dumps({"error": "output_must_remain_private"}, sort_keys=True))
            return 2
        _write_private_output(target, output)
        summary = {
            "status": "pass",
            "output": str(target),
            "sourcePair": result["sourcePair"],
            "timed": result["timed"],
            "moduleMapSha256": result["sourceModuleMapSha256"],
            "cases": [
                {
                    "trialIndex": case["trialIndex"],
                    "variant": case["variant"],
                    "rows": case["rows"],
                    "selectedRows": case["selectedRows"],
                    "generations": len(case["generations"]),
                    "detachedLocalFacadeCopiesPerGeneration": case["generations"][0]["facadeReads"],
                    "dtoEquality": all(
                        (
                            len(set(item["facadeReadDtoSha256"])) == 1
                            and item["facadeReadDtoSha256"][0] == item["expectedDtoSha256"]
                        ) if item["facadeReads"] else (
                            item["facadeVerificationDtoSha256"] == item["expectedDtoSha256"]
                            and item["facadeVerificationReadOutsideCpu"]
                        )
                        for item in case["generations"]
                    ),
                    "meshCompletedSenderBytes": case["meshPublicCompletedJsonLineCounters"]["bridge"]["sentBytes"],
                    "meshReaderValidatedReceivedBytes": case["meshPublicCompletedJsonLineCounters"]["reader"]["receivedBytes"],
                }
                for case in result["cases"]
            ],
        }
        print(json.dumps(summary, sort_keys=True, indent=2))
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
