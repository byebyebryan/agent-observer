"""Finite, isolated working-set reads through the public Mesh SDK and facade."""

from __future__ import annotations

import asyncio
import json
import re
import uuid

from .config import TerminalSource
from .model import identity_tuple

TICK_SECONDS = 0.2
SETUP_CONCURRENCY = 4
_CODE = re.compile(r"[a-z][a-z0-9_]{0,127}\Z")
_FINAL = object()
_EOF = object()


class TerminalDependencyError(RuntimeError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class _SourceFailure(Exception):
    def __init__(self, code: str, *, blocked: bool = False):
        super().__init__(code)
        self.code = code if _CODE.fullmatch(code) else "source_read_failed"
        self.blocked = blocked


class _FinalRequested(Exception):
    pass


def _dependencies():
    """Load the optional Mesh stack only for a live sessions read."""
    try:
        from mesh_plus.api import SDK_INTERFACE_VERSION, AdmittedResponse, configured_reader
        from mesh_plus.evidence import clock_domain
        from mesh_plus.transport import boottime_ms

        from agent_observer.mesh_working_set_profile import WorkingSetAgentProfile
        from agent_observer.mesh_working_set_read import (
            WORKING_SET_MEMBER_LEASE_INTERFACE_VERSION,
            WORKING_SET_READ_INTERFACE_VERSION,
            WORKING_SET_SCOPE_LEASE_INTERFACE_VERSION,
            PreparedWorkingSetAgentWatch,
        )
    except (ImportError, AttributeError, ModuleNotFoundError):
        raise TerminalDependencyError("mesh_dependency_missing_or_incompatible") from None
    if (
        SDK_INTERFACE_VERSION != 1
        or WORKING_SET_READ_INTERFACE_VERSION != 1
        or WORKING_SET_MEMBER_LEASE_INTERFACE_VERSION != 1
        or WORKING_SET_SCOPE_LEASE_INTERFACE_VERSION != 1
    ):
        raise TerminalDependencyError("mesh_dependency_incompatible")
    return {
        "AdmittedResponse": AdmittedResponse,
        "configured_reader": configured_reader,
        "clock_domain": clock_domain,
        "boottime_ms": boottime_ms,
        "WorkingSetAgentProfile": WorkingSetAgentProfile,
        "PreparedWorkingSetAgentWatch": PreparedWorkingSetAgentWatch,
    }


async def _or_final(awaitable, final_event: asyncio.Event):
    operation = asyncio.create_task(awaitable)
    stopper = asyncio.create_task(final_event.wait())
    try:
        done, _ = await asyncio.wait({operation, stopper}, return_when=asyncio.FIRST_COMPLETED)
        if stopper in done and operation not in done:
            operation.cancel()
            await asyncio.gather(operation, return_exceptions=True)
            raise _FinalRequested
        return operation.result()
    except asyncio.CancelledError:
        operation.cancel()
        await asyncio.gather(operation, return_exceptions=True)
        raise
    finally:
        if not stopper.done():
            stopper.cancel()
        await asyncio.gather(stopper, return_exceptions=True)


async def _ticked(stream, final_event: asyncio.Event):
    """Yield quiet ticks with one pending ``anext`` per source."""
    pending = asyncio.create_task(anext(stream))
    stop = asyncio.create_task(final_event.wait())
    try:
        while True:
            done, _ = await asyncio.wait(
                {pending, stop}, timeout=TICK_SECONDS, return_when=asyncio.FIRST_COMPLETED
            )
            if pending in done:
                try:
                    frame = pending.result()
                except StopAsyncIteration:
                    yield _EOF
                    return
                pending = asyncio.create_task(anext(stream))
                yield frame
                continue
            if stop in done:
                yield _FINAL
                return
            yield None
    finally:
        if not pending.done():
            pending.cancel()
        if not stop.done():
            stop.cancel()
        await asyncio.gather(pending, stop, return_exceptions=True)


def _frame_kind(frame, admitted_type) -> str | None:
    if isinstance(frame, admitted_type):
        context = frame.context()
        mesh = context.get("mesh", {}) if type(context) is dict else {}
        return mesh.get("kind") if type(mesh) is dict else None
    if type(frame) is dict:
        mesh = frame.get("mesh", {})
        return mesh.get("kind") if type(mesh) is dict else None
    return None


def _delivery_error(context, host: str) -> str | None:
    """Retain a source-specific bounded failure code, never transport text."""
    if type(context) is not dict:
        return None
    if type(context.get("mesh")) is dict:
        context = context["mesh"]
    hosts = context.get("hosts", ())
    if type(hosts) not in {list, tuple}:
        return None
    for item in hosts:
        if type(item) is not dict or item.get("hostId") != host:
            continue
        delivery = item.get("delivery")
        error = delivery.get("error") if type(delivery) is dict else None
        code = error.get("code") if type(error) is dict else None
        if type(code) is str and _CODE.fullmatch(code):
            return code
    return None


def _frame_snapshot(frame, admitted_type) -> dict:
    if not isinstance(frame, admitted_type):
        raise _SourceFailure("frame_not_admitted", blocked=True)
    try:
        snapshot = frame.snapshot()
    except Exception:
        raise _SourceFailure("frame_snapshot_unavailable", blocked=True) from None
    if type(snapshot) is not dict:
        raise _SourceFailure("frame_shape", blocked=True)
    return snapshot


def _frame_size_and_identity_count(snapshot: dict) -> tuple[int, int]:
    try:
        encoded = json.dumps(
            snapshot, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise _SourceFailure("frame_encoding", blocked=True) from None
    identities = set()
    mesh = snapshot.get("mesh", {})
    hosts = mesh.get("hosts", ()) if type(mesh) is dict else ()
    if type(hosts) in {list, tuple}:
        for host in hosts:
            owner = host.get("owner") if type(host) is dict else None
            metadata = owner.get("metadata") if type(owner) is dict else None
            scopes = metadata.get("scopes", ()) if type(metadata) is dict else ()
            if type(scopes) not in {list, tuple}:
                continue
            for scope in scopes:
                if type(scope) is not dict:
                    continue
                for field in ("members", "uncertain", "nonmembers"):
                    entries = scope.get(field, ())
                    if type(entries) not in {list, tuple}:
                        continue
                    for entry in entries:
                        identity = entry.get("identity") if type(entry) is dict else None
                        if type(identity) is dict:
                            try:
                                identities.add(identity_tuple(identity))
                            except ValueError:
                                raise _SourceFailure("frame_identity_shape", blocked=True) from None
    return len(encoded), len(identities)


def _check_source_binding(read, config: dict) -> str | None:
    context = getattr(read, "context", None)
    if context is None:
        return None
    if type(context) is not dict:
        raise _SourceFailure("mesh_context_shape", blocked=True)
    hosts = context.get("hosts", ())
    if type(hosts) not in {list, tuple}:
        raise _SourceFailure("mesh_host_shape", blocked=True)
    if hosts and (len(hosts) != 1 or hosts[0].get("hostId") != config["host"]):
        raise _SourceFailure("host_binding_mismatch", blocked=True)
    observed = set()
    for scope in getattr(read, "scopes", ()):
        if scope.get("hostScope") != config["host"] or scope.get("provider") != "codex":
            raise _SourceFailure("scope_binding_mismatch", blocked=True)
        namespace = scope.get("namespace")
        if namespace != config["namespace"]:
            raise _SourceFailure("namespace_mismatch", blocked=True)
        observed.add(namespace)
    for rows in (
        getattr(read, "members", ()),
        getattr(read, "uncertain", ()),
        getattr(read, "nonmembers", ()),
        getattr(read, "member_leases", ()),
    ):
        for row in rows:
            identity = row.get("identity") if type(row) is dict else None
            try:
                identity_tuple(identity)
            except ValueError:
                raise _SourceFailure("identity_shape", blocked=True) from None
            if (
                identity["hostScope"] != config["host"]
                or identity["provider"] != "codex"
                or identity["namespace"] != config["namespace"]
            ):
                raise _SourceFailure("namespace_mismatch", blocked=True)
            observed.add(identity["namespace"])
    if len(observed) > 1:
        raise _SourceFailure("namespace_mismatch", blocked=True)
    return next(iter(observed), None)


def _failure_code(error: BaseException) -> str:
    code = getattr(error, "code", None)
    if type(code) is str and _CODE.fullmatch(code):
        return code
    name = type(error).__name__.lower()
    return name if _CODE.fullmatch(name) else "source_read_failed"


def _source_config(source: TerminalSource) -> dict:
    return source.as_dict()


def _new_state(source: TerminalSource, clock_binding: dict) -> dict:
    return {
        "config": _source_config(source),
        "lifecycle": "warming",
        "reason": None,
        "delivery_error": None,
        "baseline": False,
        "read": None,
        "last_frame_boottime_ms": None,
        "capture_boottime_ms": None,
        "observed_namespace": None,
        "clock": {
            "kind": "CLOCK_BOOTTIME",
            **clock_binding,
            "clockDomain": "time:[" + clock_binding["timeNamespace"].split(":", 1)[-1] + "]",
        },
        "settled": asyncio.Event(),
        "frozen": asyncio.Event(),
        "cleanup_error": None,
    }


async def _source_worker(
    state: dict,
    source: TerminalSource,
    *,
    dependencies: dict,
    semaphore: asyncio.Semaphore,
    final_event: asyncio.Event,
    final_reason: list[str | None],
    clock_binding: dict,
):
    reader = None
    guard = None
    stream = None
    events = None
    acquired = False
    admitted_type = dependencies["AdmittedResponse"]

    def fail(code: str, *, blocked: bool = False):
        state["lifecycle"] = "blocked" if blocked else "failed"
        state["reason"] = code
        state["baseline"] = False
        if state["capture_boottime_ms"] is None:
            state["capture_boottime_ms"] = dependencies["boottime_ms"]()
        state["settled"].set()
        state["frozen"].set()

    async def refresh(read, now):
        state["read"] = read
        state["capture_boottime_ms"] = now
        delivery_error = _delivery_error(getattr(read, "context", None), source.host)
        if delivery_error:
            state["delivery_error"] = delivery_error
        observed_namespaces = {
            item.get("namespace")
            for item in getattr(read, "scopes", ())
            if type(item.get("namespace")) is str
        }
        if len(observed_namespaces) == 1:
            state["observed_namespace"] = next(iter(observed_namespaces))
        observed = _check_source_binding(read, state["config"])
        if observed is not None:
            state["observed_namespace"] = observed
        if read is not None and read.context is not None:
            state["baseline"] = True
            hosts = read.context.get("hosts", ())
            if hosts and all(
                item.get("delivery", {}).get("status") != "connecting" for item in hosts
            ):
                state["settled"].set()
        if read is not None and read.context is not None:
            disconnected = any(
                item.get("delivery", {}).get("status") in {"unavailable", "disconnected"}
                for item in read.context.get("hosts", ())
            )
            if disconnected:
                raise _SourceFailure("mesh_delivery_disconnected")

    try:
        await _or_final(semaphore.acquire(), final_event)
        acquired = True
        profile = dependencies["WorkingSetAgentProfile"](source.window_ms)
        reader = await _or_final(
            dependencies["configured_reader"](
                "agent",
                source=source.mesh_source,
                socket=source.socket,
                scope=source.scope,
                hosts=[source.host] if source.scope == "hosts" else [],
                local_host=source.host if source.scope == "local" else None,
                report_routes=False,
                profile=profile,
            ),
            final_event,
        )
        request_id = uuid.uuid4().hex
        guard = dependencies["PreparedWorkingSetAgentWatch"](
            request_id,
            host_ids=[source.host] if source.scope == "hosts" else None,
            window_ms=source.window_ms,
            profile=profile,
        )
        request = {
            "meshProtocol": 1,
            "requestId": request_id,
            "operation": "watch",
            "profile": profile.descriptor.profile_id,
            "access": "cached",
            "selection": {
                "mode": source.scope,
                "hostIds": [source.host] if source.scope == "hosts" else [],
            },
            "extensions": {},
        }
        stream = reader.execute_admitted(request)
        events = _ticked(stream, final_event)
        async for frame in events:
            now = dependencies["boottime_ms"]()
            if frame is _FINAL:
                if guard is not None:
                    read = guard.read(now, clock_binding)
                    await refresh(read, now)
                    if state["baseline"]:
                        state["lifecycle"] = "observing"
                    if final_reason[0] and not state["settled"].is_set():
                        state["lifecycle"] = "timed_out"
                        state["reason"] = final_reason[0]
                        state["baseline"] = False
                else:
                    final_code = final_reason[0]
                    state["lifecycle"] = (
                        "timed_out" if final_code == "deadline_timeout" else "failed"
                    )
                    state["reason"] = final_code or "setup_incomplete"
                    state["baseline"] = False
                state["frozen"].set()
                return
            if frame is _EOF:
                raise _SourceFailure("mesh_stream_ended")
            if frame is not None:
                if type(frame) is dict and type(frame.get("error")) is dict:
                    raise _SourceFailure(_failure_code_from_frame(frame))
                context = (
                    frame.context()
                    if isinstance(frame, admitted_type)
                    else frame.get("mesh", {})
                    if type(frame) is dict
                    else None
                )
                delivery_error = _delivery_error(context, source.host)
                if delivery_error:
                    state["delivery_error"] = delivery_error
                kind = _frame_kind(frame, admitted_type)
                if kind in {"gap", "resync"}:
                    raise _SourceFailure("mesh_gap" if kind == "gap" else "mesh_resync")
                if kind != "heartbeat":
                    snapshot = _frame_snapshot(frame, admitted_type)
                    payload_size, identity_count = _frame_size_and_identity_count(snapshot)
                    if identity_count > source.max_identities:
                        raise _SourceFailure("source_identity_capacity", blocked=True)
                    if payload_size > source.max_payload_mib * 1024 * 1024:
                        raise _SourceFailure("source_payload_capacity", blocked=True)
                try:
                    guard.accept(frame)
                except asyncio.CancelledError:
                    raise
                except Exception as error:
                    raise _SourceFailure(_failure_code(error), blocked=True) from None
                state["last_frame_boottime_ms"] = now
            read = guard.read(now, clock_binding)
            await refresh(read, now)
            if state["settled"].is_set() and acquired:
                semaphore.release()
                acquired = False
            if final_event.is_set():
                state["frozen"].set()
                return
            state["lifecycle"] = "observing" if state["baseline"] else "warming"
    except _FinalRequested:
        final_code = final_reason[0]
        state["lifecycle"] = "timed_out" if final_code == "deadline_timeout" else "failed"
        state["reason"] = final_code or "setup_incomplete"
        state["baseline"] = False
        state["capture_boottime_ms"] = dependencies["boottime_ms"]()
        state["settled"].set()
        state["frozen"].set()
    except _SourceFailure as error:
        fail(error.code, blocked=error.blocked)
    except asyncio.CancelledError:
        fail(final_reason[0] or "cancelled")
        raise
    except Exception as error:
        fail(_failure_code(error), blocked=False)
    finally:
        if acquired:
            semaphore.release()
        if guard is not None:
            try:
                guard.disconnect()
            except BaseException as error:
                state["cleanup_error"] = _failure_code(error)
        for iterator in (events, stream):
            if iterator is None:
                continue
            try:
                close = getattr(iterator, "aclose", None)
                if close is not None:
                    await close()
            except BaseException as error:
                state["cleanup_error"] = _failure_code(error)
        state["frozen"].set()


def _failure_code_from_frame(frame: dict) -> str:
    error = frame.get("error", {})
    code = error.get("code") if type(error) is dict else None
    return code if type(code) is str and _CODE.fullmatch(code) else "mesh_read_failed"


async def read_sources(
    sources: tuple[TerminalSource, ...],
    *,
    timeout: float = 10.0,
    interrupt_event: asyncio.Event | None = None,
    terminate_event: asyncio.Event | None = None,
) -> dict:
    """Read independent configured source pairs until settled or one deadline.

    Every source keeps its admitted stream alive while slower peers settle. The
    final report model is captured before the guards and streams are retired.
    """
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    dependencies = _dependencies()
    clock_binding = dependencies["clock_domain"]()
    semaphore = asyncio.Semaphore(SETUP_CONCURRENCY)
    final_event = asyncio.Event()
    final_reason: list[str | None] = [None]
    states = [_new_state(source, clock_binding) for source in sources]
    workers = [
        asyncio.create_task(
            _source_worker(
                state,
                source,
                dependencies=dependencies,
                semaphore=semaphore,
                final_event=final_event,
                final_reason=final_reason,
                clock_binding=clock_binding,
            )
        )
        for state, source in zip(states, sources, strict=True)
    ]
    waits = [asyncio.create_task(state["settled"].wait()) for state in states]
    interrupt_wait = (
        None if interrupt_event is None else asyncio.create_task(interrupt_event.wait())
    )
    terminate_wait = (
        None if terminate_event is None else asyncio.create_task(terminate_event.wait())
    )
    settlement = asyncio.gather(*waits)
    exit_signal = 0
    cleanup_error = None
    try:
        pending = {settlement}
        if interrupt_wait is not None:
            pending.add(interrupt_wait)
        if terminate_wait is not None:
            pending.add(terminate_wait)
        done, _ = await asyncio.wait(
            pending, timeout=max(0.0, deadline - loop.time()), return_when=asyncio.FIRST_COMPLETED
        )
        if interrupt_wait is not None and interrupt_wait in done:
            final_reason[0] = "interrupted"
            exit_signal = 130
        elif terminate_wait is not None and terminate_wait in done:
            final_reason[0] = "terminated"
            exit_signal = 143
        elif settlement in done:
            pass
        else:
            final_reason[0] = "deadline_timeout"
        final_event.set()
        try:
            await asyncio.wait_for(
                asyncio.gather(*(state["frozen"].wait() for state in states)), timeout=1.0
            )
        except TimeoutError:
            final_reason[0] = final_reason[0] or "final_capture_timeout"
            for worker in workers:
                if not worker.done():
                    worker.cancel()
        # All final model reads are now frozen. Cleanup may disconnect the
        # source facade and close pending reads without changing the report.
        try:
            await asyncio.wait_for(asyncio.gather(*workers, return_exceptions=True), timeout=5.0)
        except TimeoutError:
            cleanup_error = "cleanup_timeout"
            for worker in workers:
                if not worker.done():
                    worker.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
        cleanup_error = cleanup_error or next(
            (state["cleanup_error"] for state in states if state["cleanup_error"]), None
        )
    except asyncio.CancelledError:
        final_reason[0] = "interrupted"
        final_event.set()
        cleanup = asyncio.gather(*workers, return_exceptions=True)
        try:
            await asyncio.wait_for(asyncio.shield(cleanup), timeout=5.0)
        except TimeoutError:
            for worker in workers:
                if not worker.done():
                    worker.cancel()
            await asyncio.gather(*workers, return_exceptions=True)
        raise
    finally:
        for task in waits:
            if not task.done():
                task.cancel()
        for task in (interrupt_wait, terminate_wait):
            if task is not None and not task.done():
                task.cancel()
        await asyncio.gather(
            *(task for task in [*waits, interrupt_wait, terminate_wait] if task is not None),
            return_exceptions=True,
        )
    captured = [
        state["capture_boottime_ms"]
        for state in states
        if type(state["capture_boottime_ms"]) is int
    ]
    now = max(captured, default=dependencies["boottime_ms"]())
    clock = {
        "kind": "CLOCK_BOOTTIME",
        **clock_binding,
        "clockDomain": "time:[" + clock_binding["timeNamespace"].split(":", 1)[-1] + "]",
        "nowBoottimeMs": now,
    }
    return {
        "states": states,
        "clock": clock,
        "nowBoottimeMs": now,
        "timedOut": final_reason[0] == "deadline_timeout",
        "exitSignal": exit_signal,
        "cleanupError": cleanup_error,
    }
