"""Private joined API 4 producer plus Mesh SDK full/working-set trial.

This runner is intentionally inert unless ``--run-reviewed-trial`` is passed.
It is preparation for a primary-reviewed controlled fixture, not native-provider
evidence. It uses one real b176 ServiceState, actual canonical workers and the
ordinary bfa91a69 Mesh Reader/Publisher/Bridge path.
"""

from __future__ import annotations

import argparse
import ast
import asyncio
import gc
import hashlib
import importlib
import importlib.util
import json
import os
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

BASE = Path(__file__).resolve().parent
ROOT = Path("/home/bryan/.cache/agent-observer-working-set-20261018")
OBSERVER = ROOT / "final-source-b176ac06"
OBSERVER_MANIFEST = ROOT / "final-source-b176ac06-manifest.json"
OBSERVER_MANIFEST_SHA256 = "c6128a1090e0d36c761e6442dcac3ec3312c07969afc5d4b641f87ca4e94b877"
MESH = ROOT / "final-mesh-bfa91a69"
MESH_MANIFEST = ROOT / "final-mesh-bfa91a69-manifest.json"
MESH_MANIFEST_SHA256 = "d9d9c97f3171c0f6ec3bedcebafad86ee0d16e58b22e5024dbae1a79f5ad7f6a"
MESH_COMMIT = "bfa91a6936a089d37c1a83752d3267148ba7dc69"
MESH_SOURCE = MESH / "src"
V6_ROOT = ROOT / "canonical-worker-cost-measure-v6"
V6_HELPER = V6_ROOT / "measure_common_cost.py"
V6_HELPER_SHA256 = "e2ca768a31085cdae261d10095d6db7dca7cbfbf0368c7d70b2869d548f92a01"
LOCK = Path("/home/bryan/.cache/agent-active-feed-cpu.lock")
ROWS = 500
LOADED = 2
SAVED = ROWS - LOADED
RECENT_PARKED = 2
OLD_PARKED = SAVED - RECENT_PARKED
GENERATIONS = 3
WATCHES_PER_PROFILE_GENERATION = 4
WORKER_TIMEOUT_MS = 10_000
CASE_WALL_TIMEOUT_SECONDS = 300
READ_ADMISSION_TIMEOUT_SECONDS = 15
UNIX_SOCKET_PATH_LIMIT = 104
UNIX_SOCKET_BASENAMES = {
    "observerService": "service.sock",
    "producerUnused": "producer-unused.sock",
    "meshFullReader": "mesh-full.sock",
    "meshWorkingReader": "mesh-working.sock",
}
PROFILE_ORDER = {1: ("full", "working"), 2: ("working", "full")}
INTERPRETERS = {
    "py311": Path("/home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python"),
    "py314": Path("/home/bryan/code/mesh-plus/.venv/bin/python"),
}
REFERENCE_PATH = (
    OBSERVER / "docs/evidence/2026-10-18-working-set/performance-source/read_matched.py"
)
FIXTURE_FACTORY_PATH = OBSERVER / "tests/test_codex_snapshot.py"


class TrialFailure(RuntimeError):
    pass


def _unix_socket_path_sizes(root: Path) -> dict[str, int]:
    return {
        name: len(os.fsencode(root / basename))
        for name, basename in UNIX_SOCKET_BASENAMES.items()
    }


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_v6_helpers():
    if sha256(V6_HELPER.read_bytes()) != V6_HELPER_SHA256:
        raise TrialFailure("v6_helper_pin_mismatch")
    spec = importlib.util.spec_from_file_location("joined_v6_helpers", V6_HELPER)
    if spec is None or spec.loader is None:
        raise TrialFailure("v6_helper_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.BASE = BASE
    module.SERVER = BASE / "fixture_server.py"
    return module


def _manifest(path: Path, expected_hash: str, expected_commit: str, expected_root: Path) -> dict:
    data = path.read_bytes()
    if sha256(data) != expected_hash:
        raise TrialFailure("source_manifest_digest_mismatch")
    value = json.loads(data)
    root_value = value.get("root")
    if (
        value.get("commit") != expected_commit
        or (root_value is not None and Path(root_value).resolve() != expected_root.resolve())
        or not expected_root.is_dir()
    ):
        raise TrialFailure("source_manifest_identity_mismatch")
    return value


def _verify_source_manifests() -> dict[str, Any]:
    observer_manifest = _manifest(
        OBSERVER_MANIFEST,
        OBSERVER_MANIFEST_SHA256,
        "b176ac06b39daeead4be0a33ff9d781304091fe0",
        OBSERVER,
    )
    mesh_manifest = _manifest(
        MESH_MANIFEST,
        MESH_MANIFEST_SHA256,
        MESH_COMMIT,
        MESH,
    )
    return {
        "observer": {
            "commit": observer_manifest["commit"],
            "manifestSha256": OBSERVER_MANIFEST_SHA256,
        },
        "mesh": {"commit": mesh_manifest["commit"], "manifestSha256": MESH_MANIFEST_SHA256},
    }


def _selected_module_files(manifests: dict[str, dict]) -> dict[str, dict[str, str]]:
    roots = {"agent_observer": OBSERVER.resolve(), "mesh_plus": MESH_SOURCE.resolve()}
    loaded: dict[str, dict[str, str]] = {}
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
            raise TrialFailure("selected_module_path_mismatch")
        relative = str(path.relative_to(root))
        manifest_key = relative if root_name == "agent_observer" else f"src/{relative}"
        manifest = manifests["observer"] if root_name == "agent_observer" else manifests["mesh"]
        actual = sha256(path.read_bytes())
        if manifest.get("files", {}).get(manifest_key) != actual:
            raise TrialFailure("selected_module_manifest_hash_mismatch")
        loaded[name] = {"root": root_name, "path": relative, "sha256": actual}
    for package in roots:
        if not any(item["root"] == package for item in loaded.values()):
            raise TrialFailure("selected_package_not_loaded")
    return dict(sorted(loaded.items()))


def _load_reference():
    spec = importlib.util.spec_from_file_location("joined_read_matched_reference", REFERENCE_PATH)
    if spec is None or spec.loader is None:
        raise TrialFailure("read_reference_unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if module.WINDOW_MS != 72 * 60 * 60 * 1000:
        raise TrialFailure("working_set_window_changed")
    return module


def _pure_native_factory():
    """Compile only the reviewed pure dictionary factory, not its test module."""
    tree = ast.parse(FIXTURE_FACTORY_PATH.read_text(encoding="utf-8"))
    matches = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "native"
    ]
    if len(matches) != 1:
        raise TrialFailure("native_fixture_factory_changed")
    factory = matches[0]
    if len(factory.body) != 1 or not isinstance(factory.body[0], ast.Return) or not isinstance(factory.body[0].value, ast.Dict):
        raise TrialFailure("native_fixture_factory_not_pure_dict")
    namespace = {"__builtins__": {}}
    exec(compile(ast.Module(body=[factory], type_ignores=[]), str(FIXTURE_FACTORY_PATH), "exec"), namespace)
    return namespace["native"]


def build_fixture(output_path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    native = _pure_native_factory()
    fixture_seconds = int(time.time())
    rows: list[dict[str, Any]] = []
    turns: list[dict[str, Any]] = []
    expected: dict[str, dict[str, Any]] = {}
    for index in range(ROWS):
        number = index + 1
        root_number = index + 10_001
        thread_id = f"{number:08x}-1234-4234-8234-{number:012x}"
        root_id = f"{root_number:08x}-5678-4678-8678-{root_number:012x}"
        status = "active" if index == 0 else "idle" if index == 1 else "notLoaded"
        row = native(thread_id)
        row["sessionId"] = root_id
        row["status"] = {"type": status, **({"activeFlags": []} if status == "active" else {})}
        row.pop("name", None)
        if index < LOADED:
            age_seconds = 600
        elif index < LOADED + RECENT_PARKED:
            age_seconds = 3600 * (index - LOADED + 1)
        else:
            age_seconds = 10 * 24 * 3600
        completed = fixture_seconds - age_seconds
        started = completed - 60
        row["createdAt"] = started
        row["updatedAt"] = completed
        if set(row) != {
            "id", "sessionId", "cwd", "source", "threadSource", "ephemeral",
            "status", "createdAt", "updatedAt",
        }:
            raise TrialFailure("native_fixture_shape_changed")
        if thread_id == root_id:
            raise TrialFailure("synthetic_identity_collision")
        rows.append(row)
        turns.append({
            "threadId": thread_id,
            "turn": {
                "itemsView": "notLoaded",
                "items": [],
                "startedAt": started,
                "completedAt": completed,
                "status": "completed",
            },
        })
        expected[thread_id] = {
            "sessionTreeRootId": root_id,
            "nativeStatus": status,
            "runtime": "running" if index < LOADED else "parked",
            "activityClass": (
                "loaded" if index < LOADED
                else "recent" if index < LOADED + RECENT_PARKED
                else "old"
            ),
        }
    value = {"rows": rows, "turns": turns}
    content = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8") + b"\n"
    if any(token in content for token in (b'"name"', b'"title"', b'"prompt"', b'"preview"', b'"tool')):
        raise TrialFailure("fixture_content_field_present")
    fd = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb", closefd=True) as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())
    return expected, {
        "rows": rows,
        "turns": turns,
        "fixtureEpochSeconds": fixture_seconds,
        "sha256": sha256(content),
        "bytes": len(content),
    }


def _expected_server_stats(page_size: int = 100) -> dict[str, Any]:
    collections = GENERATIONS * 2
    pages_per_collection = (ROWS + page_size - 1) // page_size
    return {
        "acceptedConnections": 1 + 2 * collections,
        "methodCounts": {
            "initialize": collections,
            "initialized": collections,
            "thread/list": collections * pages_per_collection,
            "thread/loaded/list": collections,
            "thread/read": collections * (SAVED + 2 * LOADED),
            "thread/turns/list": GENERATIONS * (ROWS + LOADED),
        },
        "threadListPageSizes": [page_size] * (collections * pages_per_collection),
        "uniqueThreadListRows": ROWS,
        "uniqueThreadReadRows": ROWS,
        "uniqueTurnRows": ROWS,
        "hardFail": False,
    }


def _offline_checks() -> dict[str, Any]:
    if ROWS != 500 or LOADED != 2 or SAVED != 498 or RECENT_PARKED != 2 or OLD_PARKED != 496:
        raise TrialFailure("fixture_census_constants_changed")
    if WATCHES_PER_PROFILE_GENERATION * GENERATIONS * len(PROFILE_ORDER[1]) != 24:
        raise TrialFailure("watch_total_changed")
    manifest_pins = _verify_source_manifests()
    helpers = _load_v6_helpers()
    pin_report = helpers.verify_source_pins()
    with tempfile.TemporaryDirectory(prefix="joined-sdk-py314-r2-") as candidate_text:
        candidate = Path(candidate_text)
        candidate_info = candidate.lstat()
        socket_path_bytes = _unix_socket_path_sizes(candidate)
        if (
            candidate_info.st_uid != os.geteuid()
            or stat.S_IMODE(candidate_info.st_mode) != 0o700
            or max(socket_path_bytes.values()) >= UNIX_SOCKET_PATH_LIMIT
        ):
            raise TrialFailure("offline_private_socket_path_or_directory_guard")
    from types import SimpleNamespace

    fake_modules = {
        "agent_observer": SimpleNamespace(__file__=str(OBSERVER / "agent_observer/__init__.py")),
        "mesh_plus": SimpleNamespace(__file__=str(MESH_SOURCE / "mesh_plus/__init__.py")),
    }
    previous_modules = {name: sys.modules.get(name) for name in fake_modules}
    try:
        sys.modules.update(fake_modules)
        selected_paths = _selected_module_files({
            "observer": json.loads(OBSERVER_MANIFEST.read_text(encoding="utf-8")),
            "mesh": json.loads(MESH_MANIFEST.read_text(encoding="utf-8")),
        })
        if len(selected_paths) != 2:
            raise TrialFailure("offline_selected_module_manifest_mapping")
    finally:
        for name, module in previous_modules.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
    source = (OBSERVER / "agent_observer/codex_snapshot.py").read_text(encoding="utf-8")
    if "MAX_SAVED_CLASSIFICATIONS = 1000" not in source or "history_limit: int = 1000" not in source or "live_limit: int = 512" not in source or "timeout: float = 10.0" not in source:
        raise TrialFailure("canonical_source_limits_changed")
    runtime_source = (OBSERVER / "agent_observer/service_runtime.py").read_text(encoding="utf-8")
    if "heartbeat_ms=10000" not in runtime_source:
        raise TrialFailure("service_heartbeat_default_changed")
    runtime_tree = ast.parse(runtime_source)
    runtime_functions = {
        child.name: child
        for cls in runtime_tree.body if isinstance(cls, ast.ClassDef) and cls.name == "Runtime"
        for child in cls.body if isinstance(child, ast.FunctionDef)
    }
    if not {"_complete", "_exit_status", "_stop_worker"}.issubset(runtime_functions):
        raise TrialFailure("runtime_worker_lifecycle_source_changed")
    complete_source = ast.get_source_segment(runtime_source, runtime_functions["_complete"])
    exit_source = ast.get_source_segment(runtime_source, runtime_functions["_exit_status"])
    stop_source = ast.get_source_segment(runtime_source, runtime_functions["_stop_worker"])
    if not (
        complete_source.index("self._exit_status(process)") < complete_source.index("self._stop_worker(worker)")
        < complete_source.index("parse_snapshot(bytes(worker.buffer))")
        < complete_source.index("self.state.accept(")
        and "os.WNOWAIT" in exit_source
        and stop_source.index("os.killpg(") < stop_source.index("process.wait(")
    ):
        raise TrialFailure("runtime_complete_wait_accept_order_changed")
    harness_tree = ast.parse(Path(__file__).read_text(encoding="utf-8"))
    harness_text = Path(__file__).read_text(encoding="utf-8")
    serving_class = next(
        node for node in harness_tree.body
        if isinstance(node, ast.ClassDef) and node.name == "ServingRuntime"
    )
    serving_init = next(
        node for node in serving_class.body
        if isinstance(node, ast.FunctionDef) and node.name == "__init__"
    )
    if "heartbeat_ms" in ast.get_source_segment(harness_text, serving_init):
        raise TrialFailure("serving_runtime_overrides_default_heartbeat")
    gc_mode_mutators = [
        node for node in ast.walk(harness_tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and isinstance(node.func.value, ast.Name)
        and node.func.value.id == "gc"
        and node.func.attr in {"collect", "disable"}
    ]
    if gc_mode_mutators:
        raise TrialFailure("harness_changes_normal_python_gc_mode")
    collect_function = next(
        node for node in harness_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_collect_generation"
    )
    collect_source = ast.get_source_segment(harness_text, collect_function)
    if not (
        collect_source.index("helpers.drain_worker(")
        < collect_source.index("_wait_exit_status_unreaped(")
        < collect_source.index("producer._complete(worker)")
        and "job.deadline - state.clock()" in collect_source
        and "trial_deadline" in collect_source
        and "state.accept(" not in collect_source
    ):
        raise TrialFailure("harness_bypasses_runtime_accept_boundary")
    read_verify_function = next(
        node for node in harness_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_verify_read_outputs"
    )
    read_verify_source = ast.get_source_segment(harness_text, read_verify_function)
    if not all(
        token in read_verify_source for token in (
            "full_view_revisions", "working_view_revisions",
            "working_observation_revisions", "acceptedStateRevision",
            'right["observationRevision"] != left["viewRevision"]',
            'read["historyAccepted"] != clock_join["historyAccepted"]',
            'read["runtimeAccepted"] != clock_join["runtimeAccepted"]',
        )
    ):
        raise TrialFailure("revision_namespace_or_runtime_counter_join_guard_missing")
    runner_function = next(
        node for node in harness_tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_run_pipeline"
    )
    runner_source = ast.get_source_segment(harness_text, runner_function)
    if not all(
        token in runner_source for token in (
            'tempfile.mkdtemp(prefix=f"joined-sdk-{interpreter_name}-r{replicate}-")',
            "socket_path_bytes = _unix_socket_path_sizes(run_dir)",
            "max(socket_path_bytes.values()) >= UNIX_SOCKET_PATH_LIMIT",
            'result["privateRuntimeDirectory"] =',
            'BASE / f"{interpreter_name}-r{replicate}.json"',
            'history_receipt.data["collectionId"] != current_sample',
            'history_receipt.accepted != gen["clockJoin"]["historyAccepted"]',
            'runtime_receipt.accepted != gen["clockJoin"]["runtimeAccepted"]',
            'state.revision != gen["clockJoin"]["acceptedStateRevision"]',
        )
    ):
        raise TrialFailure("accepted_source_counter_sample_stability_guard_missing")
    exit_wait_function = next(
        node for node in harness_tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "_wait_exit_status_unreaped"
    )
    exit_wait_source = ast.get_source_segment(harness_text, exit_wait_function)
    if not all(
        token in exit_wait_source for token in (
            "producer._exit_status(process)", "time.monotonic() < deadline",
            "process.returncode is not None", "time.sleep(",
        )
    ):
        raise TrialFailure("unreaped_worker_exit_observation_guard_missing")
    watch_function = next(
        node for node in harness_tree.body
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "_watch_four"
    )
    watch_source = ast.get_source_segment(harness_text, watch_function)
    if not (
        '"selectedRows": selected_rows' in watch_source
        and '"fullRows": full_rows' in watch_source
        and "list(selected_rows)" not in watch_source
        and "list(full_rows)" not in watch_source
        and 'read.pop("fullRows")' in harness_text
        and 'read.pop("selectedRows")' in harness_text
    ):
        raise TrialFailure("read_oracle_row_copy_or_retention_guard")
    with tempfile.TemporaryDirectory(prefix="joined-sdk-offline-", dir=BASE) as temporary:
        path = Path(temporary) / "fixture.json"
        expected, fixture = build_fixture(path)
        selected_ids = {
            identifier for identifier, metadata in expected.items()
            if metadata["runtime"] == "running" or metadata["activityClass"] == "recent"
        }
        if (
            len(expected) != ROWS
            or len(selected_ids) != LOADED + RECENT_PARKED
            or sum(metadata["runtime"] == "running" for metadata in expected.values()) != LOADED
            or sum(metadata["activityClass"] == "recent" for metadata in expected.values()) != RECENT_PARKED
        ):
            raise TrialFailure("offline_expected_72h_union_census")
        expected_server_stats = _expected_server_stats()
        if (
            expected_server_stats["methodCounts"]["thread/read"] != 3012
            or expected_server_stats["methodCounts"]["thread/turns/list"] != 1506
            or expected_server_stats["threadListPageSizes"] != [100] * 30
        ):
            raise TrialFailure("offline_protocol_census_arithmetic")
        parsed = json.loads(path.read_text(encoding="utf-8"))
        # Offline fixture-server parser check only: no socket, endpoint, process, or worker.
        server_spec = importlib.util.spec_from_file_location("joined_fixture_server_offline", BASE / "fixture_server.py")
        if server_spec is None or server_spec.loader is None:
            raise TrialFailure("fixture_server_unavailable")
        server_module = importlib.util.module_from_spec(server_spec)
        sys.modules[server_spec.name] = server_module
        server_spec.loader.exec_module(server_module)
        rows, order, turns = server_module.row_map_value(parsed)
        if len(rows) != ROWS or len(turns) != ROWS or len(order) != ROWS:
            raise TrialFailure("offline_fixture_parser_census")
        recent_ids = {
            item["threadId"] for item in parsed["turns"]
            if expected[item["threadId"]]["activityClass"] == "recent"
        }
        if len(recent_ids) != RECENT_PARKED or sum(item["activityClass"] == "old" for item in expected.values()) != OLD_PARKED:
            raise TrialFailure("offline_fixture_activity_census")
        if any(turn["itemsView"] != "notLoaded" or turn["items"] != [] for turn in turns.values()):
            raise TrialFailure("offline_turn_fixture_contains_content")
    if any(name == "agent_observer" or name.startswith("agent_observer.") or name == "mesh_plus" or name.startswith("mesh_plus.") for name in sys.modules):
        raise TrialFailure("offline_check_imported_selected_package")
    return {
        "status": "pass",
        "sourceManifests": manifest_pins,
        "selectedModuleManifestMapping": "pass",
        "privateRuntimeDirectoryGuard": {
            "defaultTempRoot": str(Path(tempfile.gettempdir()).resolve()),
            "directoryMode": "0700",
            "directoryUid": os.geteuid(),
            "socketPathBytes": socket_path_bytes,
            "maxSocketPathBytes": max(socket_path_bytes.values()),
            "requiredStrictlyBelowBytes": UNIX_SOCKET_PATH_LIMIT,
        },
        "v6CanonicalRoutePins": pin_report,
        "fixture": {
            "rows": ROWS,
            "loaded": LOADED,
            "saved": SAVED,
            "recentParked": RECENT_PARKED,
            "oldParked": OLD_PARKED,
            "metadataOnlyTurns": ROWS,
            "noPromptTitleToolFields": True,
            "expectedSelectedUnionRows": len(selected_ids),
            "expectedSelectedUnionIdSha256": sha256("\n".join(sorted(selected_ids)).encode("ascii")),
        },
        "expectedProtocolCensus": expected_server_stats,
        "trialPlan": {
            "interpreters": sorted(INTERPRETERS),
            "replicatesPerInterpreter": 2,
            "generationsPerTrial": GENERATIONS,
            "watchAdmissionsPerProfileGeneration": WATCHES_PER_PROFILE_GENERATION,
            "watchRetirementsPerTrial": 24,
            "caseWallTimeoutSeconds": CASE_WALL_TIMEOUT_SECONDS,
            "controlledBurstCadence": True,
            "defaultSchedulerIntervalsMs": {"runtime": 2000, "history": 60000},
            "defaultSchedulerTimeoutMs": WORKER_TIMEOUT_MS,
            "defaultServiceHeartbeatMs": 10000,
            "sourceCaps": {"catalog": 1000, "savedClassifications": 1000, "loaded": 512},
            "canonicalNativeUnionCeiling": 1512,
            "complete2000RowNativeCase": False,
            "normalPythonGcEnabledRequired": True,
            "canonicalRuntimeCompleteLifecyclePreserved": True,
        },
    }


class SelectorBoundaryPause:
    """Pause the serving Runtime only at its ordinary selector boundary."""

    def __init__(self):
        self._condition = threading.Condition()
        self._requested = self._entered = self._released = False

    def request_and_wait(self, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        with self._condition:
            if self._requested or self._entered:
                raise TrialFailure("selector_pause_already_requested")
            self._requested, self._released = True, False
            self._condition.notify_all()
            while not self._entered:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    self._requested, self._released = False, True
                    self._condition.notify_all()
                    raise TrialFailure("runtime_selector_pause_timeout")
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
                    self._requested, self._entered = False, False
                    self._condition.notify_all()
                    raise TrialFailure("runtime_selector_release_timeout")
                self._condition.wait(remaining)
            self._entered = self._requested = self._released = False
            self._condition.notify_all()

    def resume_and_wait(self, timeout: float = 5.0) -> None:
        deadline = time.monotonic() + timeout
        with self._condition:
            if not self._entered:
                raise TrialFailure("runtime_selector_not_held")
            self._released = True
            self._condition.notify_all()
            while self._entered:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TrialFailure("runtime_selector_resume_timeout")
                self._condition.wait(remaining)

    def release_for_cleanup(self) -> None:
        with self._condition:
            self._requested, self._released = False, True
            self._condition.notify_all()


class _SelectorProxy:
    def __init__(self, selector, pause: SelectorBoundaryPause):
        self._selector, self._pause = selector, pause

    def __getattr__(self, name):
        return getattr(self._selector, name)

    def select(self, *args, **kwargs):
        self._pause.at_boundary()
        return self._selector.select(*args, **kwargs)


class ServingRuntime:
    def __init__(self, state, path, Runtime, *, encoded_limit: int):
        self.runtime = Runtime(
            state, path, collect=False, max_clients=16,
            encoded_limit=encoded_limit,
        )
        self._selector = self.runtime.selector
        self.pause = SelectorBoundaryPause()
        self.runtime.selector = _SelectorProxy(self._selector, self.pause)
        self.stop = threading.Event()
        self.errors: list[BaseException] = []
        self.thread = threading.Thread(target=self._run, name="joined-sdk-service")
        self.cleanup: dict[str, Any] | None = None

    def _run(self):
        try:
            self.runtime.run(self.stop)
        except BaseException as error:
            self.errors.append(error)

    def start(self):
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
            self.close()
            raise TrialFailure("service_runtime_start_failed")

    def close(self):
        self.pause.release_for_cleanup()
        self.stop.set()
        self.thread.join(5)
        if self.thread.is_alive():
            raise TrialFailure("service_runtime_cleanup_timeout")
        self.runtime.selector = self._selector
        selector_map = self._selector.get_map()
        self.cleanup = {
            "runtimePeersAfterRun": len(self.runtime.peers),
            "selectorRegistrationsAfterRun": 0 if selector_map is None else len(selector_map),
            "selectorClosed": selector_map is None,
            "runtimeThreadAlive": self.thread.is_alive(),
            "selectorHookRestored": self.runtime.selector is self._selector,
        }
        if self.errors:
            raise TrialFailure("service_runtime_thread_failed")


def _reader_now() -> int:
    return int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)


def _reader_clock() -> dict[str, str]:
    return {
        "bootId": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "timeNamespace": os.readlink("/proc/self/ns/time").replace("[", "").replace("]", ""),
    }


def _frame_header(frame):
    context = getattr(frame, "context", None)
    value = context() if callable(context) else frame
    return value if isinstance(value, dict) else None


def _codex_accepted_counters(header: dict[str, Any]) -> dict[str, int] | None:
    hosts = header.get("mesh", {}).get("hosts", [])
    if not hosts:
        return None
    service = ((hosts[0].get("owner") or {}).get("service") or {})
    for source in service.get("sources", []):
        if source.get("provider") == "codex":
            counters: dict[str, int] = {}
            for component in source.get("components", []):
                name = component.get("name")
                if name in {"history", "runtime"}:
                    value = component.get("accepted")
                    if type(value) is not int or name in counters:
                        return None
                    counters[name] = value
            if set(counters) == {"history", "runtime"}:
                return counters
    return None


def _proof_nonce(header: dict[str, Any], observed_ms: int) -> str | None:
    mesh = header.get("mesh", {})
    hosts = mesh.get("hosts", [])
    if mesh.get("status") != "complete" or not hosts:
        return None
    host = hosts[0]
    if host.get("viewState") != "current":
        return None
    delivery = host.get("delivery") or {}
    if delivery.get("status") != "ready":
        return None
    proof = delivery.get("proof") or {}
    sent, received = proof.get("sentAtMs"), proof.get("receivedAtMs")
    if (
        not proof
        or type(sent) is not int
        or type(received) is not int
        or not sent <= received <= observed_ms
        or received - sent > 2000
    ):
        return None
    nonce = proof.get("nonce")
    return nonce if isinstance(nonce, str) and len(nonce) >= 32 else None


def _working_coverage_current(header: dict[str, Any]) -> bool:
    hosts = header.get("mesh", {}).get("hosts", [])
    if not hosts:
        return False
    metadata = (hosts[0].get("owner") or {}).get("metadata") or {}
    scopes = metadata.get("scopes", [])
    return bool(
        scopes
        and scopes[0].get("coverage", {}).get("status") == "complete"
    )


class ProfileStack:
    def __init__(self, *, variant: str, root: Path, state, Runtime, mesh_api, mesh_transport, mesh_source):
        self.variant = variant
        self.source_id = variant
        self.path = root / f"mesh-{variant}.sock"
        self.handler_count = {"started": 0, "returned": 0, "raised": 0, "active": 0}
        from agent_observer.working_set_policy import DEFAULT_WINDOW_MS
        if variant == "working":
            from agent_observer.mesh_working_set_profile import WorkingSetAgentProfile
            from agent_observer.mesh_working_set_publisher import make_working_set_publisher
            from agent_observer.mesh_working_set_read import PreparedWorkingSetAgentWatch

            self.profile = WorkingSetAgentProfile(DEFAULT_WINDOW_MS)
            self.facade_type = PreparedWorkingSetAgentWatch
            self.publisher = make_working_set_publisher(
                "fixture", variant, root / "service.sock", window_ms=DEFAULT_WINDOW_MS
            )
        else:
            from agent_observer.mesh_profile import AgentProfile
            from agent_observer.mesh_publisher import make_publisher
            from agent_observer.mesh_read import PreparedAgentWatch

            self.profile = AgentProfile()
            self.facade_type = PreparedAgentWatch
            self.publisher = make_publisher("fixture", variant, root / "service.sock")
        self.codec = self.profile.bind("fixture", self.source_id)
        self.bridge = mesh_api.Bridge(self.publisher)

        async def serve(channel):
            self.handler_count["started"] += 1
            self.handler_count["active"] += 1
            try:
                await self.bridge.serve(channel)
            except BaseException:
                self.handler_count["raised"] += 1
                raise
            else:
                self.handler_count["returned"] += 1
            finally:
                self.handler_count["active"] -= 1

        self.serve = serve
        self.mesh_api, self.mesh_transport = mesh_api, mesh_transport
        self.server = None
        self.reader = None
        self.client_refs: list[Any] = []

    async def start(self):
        self.server = await self.mesh_transport.IPCServer(self.path, self.serve).start()
        revision = "sha256:" + hashlib.sha256(f"joined:{self.variant}".encode()).hexdigest()

        async def connect():
            channel = await self.mesh_transport.connect_ipc(self.path)
            client = await self.mesh_api.Client.connect(
                channel,
                host="fixture",
                source=self.source_id,
                profile=self.profile.descriptor.profile_id,
                codec=self.codec.validate_bridge,
            )
            self.client_refs.append(client)
            return client

        async def catalog_check():
            return revision

        endpoint = self.mesh_api.Endpoint("fixture", False, revision, connect, self.codec)
        self.reader = self.mesh_api.Reader(
            "agent", [endpoint], local_host="reader",
            catalog_revision=revision, catalog_check=catalog_check,
            profile=self.profile,
        )

    async def close(self):
        if self.server is not None:
            await self.server.close()
            self.server = None


async def _watch_four(
    stack: ProfileStack,
    *,
    trial: int,
    generation: int,
    expected_history_accepted: int,
    expected_accepted: int,
    reference,
    canonical,
    used_request_ids: set[str],
    used_nonces: set[str],
) -> dict[str, Any]:
    reads: list[dict[str, Any]] = []
    initial_metrics = stack.reader.inspect()
    initial_handlers = dict(stack.handler_count)
    for watch_index in range(WATCHES_PER_PROFILE_GENERATION):
        request_id = hashlib.sha256(
            f"joined-sdk-v1:{trial}:{generation}:{stack.variant}:{watch_index}".encode("ascii")
        ).hexdigest()[:32]
        if request_id in used_request_ids:
            raise TrialFailure("request_id_reused")
        used_request_ids.add(request_id)
        reader_metrics = stack.reader.inspect()
        if reader_metrics["activeConnections"] != 0:
            raise TrialFailure("prior_watch_not_retired")
        stream = stack.reader.watch_admitted(
            request_id=request_id, proof_interval=.1, catalog_interval=5
        )
        facade = stack.facade_type(
            request_id,
            profile=stack.profile,
            **({"window_ms": 72 * 60 * 60 * 1000} if stack.variant == "working" else {}),
        )
        target_header = None
        target_nonce = None
        started = asyncio.get_running_loop().time()
        deadline = started + READ_ADMISSION_TIMEOUT_SECONDS
        try:
            for _ in range(128):
                remaining = deadline - asyncio.get_running_loop().time()
                if remaining <= 0:
                    break
                try:
                    frame = await asyncio.wait_for(anext(stream), timeout=min(5.0, remaining))
                except TimeoutError:
                    continue
                header = _frame_header(frame)
                if header is None:
                    continue
                mesh = header.get("mesh", {})
                if mesh.get("requestId") != request_id:
                    raise TrialFailure("watch_request_id_mismatch")
                facade.accept(frame)
                accepted_counters = _codex_accepted_counters(header)
                if accepted_counters is None or any(
                    accepted_counters[name] < expected
                    for name, expected in (
                        ("history", expected_history_accepted),
                        ("runtime", expected_accepted),
                    )
                ):
                    continue
                if accepted_counters != {
                    "history": expected_history_accepted,
                    "runtime": expected_accepted,
                }:
                    raise TrialFailure("watch_skipped_expected_generation")
                nonce = _proof_nonce(header, _reader_now())
                if nonce is None:
                    continue
                if stack.variant == "working" and not _working_coverage_current(header):
                    continue
                target_header, target_nonce = header, nonce
                break
            if target_header is None or target_nonce is None:
                raise TrialFailure("reader_fresh_complete_admission_timeout")
            if target_nonce in used_nonces:
                raise TrialFailure("proof_nonce_reused")
            used_nonces.add(target_nonce)
            result = facade.read(_reader_now(), _reader_clock())
            if result.context is None:
                raise TrialFailure("facade_current_context_missing")
            if stack.variant == "working":
                full_rows = None
                selected_rows = result.members
            else:
                full_rows = result.sessions
                # This is the full consumer's required selection work, inside
                # its measured read window. Expected-ID comparison is deferred.
                selected_rows = reference.full_consumer_rows({"sessions": full_rows})
            service = ((target_header.get("mesh", {}).get("hosts", [{}])[0].get("owner") or {}).get("service") or {})
            scopes = ((target_header.get("mesh", {}).get("hosts", [{}])[0].get("owner") or {}).get("metadata") or {}).get("scopes", [])
            scope = scopes[0] if scopes else {}
            reads.append({
                "variant": stack.variant,
                "generation": generation,
                "watchIndex": watch_index,
                "requestId": request_id,
                "proofNonceSha256": sha256(target_nonce.encode("ascii")),
                "historyAccepted": accepted_counters["history"],
                "runtimeAccepted": accepted_counters["runtime"],
                "serviceId": service.get("serviceId"),
                "viewRevision": service.get("viewRevision"),
                "observationRevision": service.get("observationRevision"),
                # Retain detached public facade results by reference. The
                # post-window oracle checks and discards these collections.
                "selectedRows": selected_rows,
                "fullRows": full_rows,
                "workingCoverageStatus": (
                    scope.get("coverage", {}).get("status") if stack.variant == "working" else None
                ),
                "workingCoverageMemberCount": (
                    len(scope.get("members", [])) if stack.variant == "working" else None
                ),
                "runtimeReady": True,
                "freshProof": True,
                "facadeContextCurrent": True,
            })
        finally:
            facade.disconnect()
            await stream.aclose()
        retire_deadline = asyncio.get_running_loop().time() + 5.0
        while stack.handler_count["active"]:
            if asyncio.get_running_loop().time() >= retire_deadline:
                raise TrialFailure("bridge_handler_not_retired")
            await asyncio.sleep(.001)
        after = stack.reader.inspect()
        if (
            after["activeConnections"] != 0
            or after["connectionsOpened"] != after["connectionsClosed"]
            or after["cleanupFailures"] != 0
        ):
            raise TrialFailure("reader_watch_cleanup_incomplete")
    final_metrics = stack.reader.inspect()
    opened_delta = final_metrics["connectionsOpened"] - initial_metrics["connectionsOpened"]
    closed_delta = final_metrics["connectionsClosed"] - initial_metrics["connectionsClosed"]
    started_delta = stack.handler_count["started"] - initial_handlers["started"]
    returned_delta = stack.handler_count["returned"] - initial_handlers["returned"]
    if (
        opened_delta != WATCHES_PER_PROFILE_GENERATION
        or closed_delta != WATCHES_PER_PROFILE_GENERATION
        or started_delta != WATCHES_PER_PROFILE_GENERATION
        or returned_delta != WATCHES_PER_PROFILE_GENERATION
        or stack.handler_count["raised"] != initial_handlers["raised"]
        or final_metrics["cleanupFailures"] != initial_metrics["cleanupFailures"]
    ):
        raise TrialFailure("profile_generation_watch_retirements_mismatch")
    return {
        "variant": stack.variant,
        "generation": generation,
        "admissions": len(reads),
        "retirementsVerified": returned_delta,
        "readerConnectionsOpened": opened_delta,
        "readerConnectionsClosed": closed_delta,
        "bridgeHandlersReturned": returned_delta,
        "reads": reads,
    }


def _install_wait4_at_normal_complete_wait(process, wait_records: list[dict[str, Any]]) -> None:
    """Instrument Popen._try_wait; Runtime._complete retains its normal path."""
    if os.name != "posix" or not hasattr(os, "wait4"):
        raise TrialFailure("direct_wait4_unavailable")

    def try_wait(wait_flags):
        pid, status, usage = os.wait4(process.pid, wait_flags)
        if pid == process.pid:
            wait_records.append({
                "pid": pid,
                "exitStatus": os.waitstatus_to_exitcode(status),
                "userCpuNs": int(round(usage.ru_utime * 1_000_000_000)),
                "systemCpuNs": int(round(usage.ru_stime * 1_000_000_000)),
            })
        return pid, status

    # Popen.wait() and its original timeout/lock/status reconciliation stay
    # intact. Only its single-child wait primitive records wait4 rusage.
    process._try_wait = try_wait


def _wait_exit_status_unreaped(producer, process, deadline: float) -> int:
    """Observe the real Runtime WNOWAIT exit before its normal _complete path."""
    while time.monotonic() < deadline:
        status = producer._exit_status(process)
        if status is not None:
            if process.returncode is not None:
                raise TrialFailure("worker_reaped_before_runtime_complete")
            return status
        time.sleep(min(0.01, max(0.0, deadline - time.monotonic())))
    raise TrialFailure("worker_exit_status_timeout")


def _clock_join(state) -> dict[str, Any]:
    source = state.source_meta("codex")
    bindings = state.working_set_clocks.export(source)
    by_component = {item["component"]: item for item in bindings}
    history = state.receipts["codex"]["history"]
    runtime = state.receipts["codex"]["runtime"]
    if (
        history.data is None
        or runtime.data is None
        or history.data["collectionId"] != runtime.data["collectionId"]
        or set(by_component) != {"history", "runtime"}
        or any(item["sampleId"] != history.data["collectionId"] for item in bindings)
        or any(item["originComponent"] != "history" for item in bindings)
    ):
        raise TrialFailure("history_runtime_clock_binding_mismatch")
    if history.health != "current" or runtime.health != "current":
        raise TrialFailure("current_history_runtime_receipt_required")
    return {
        "sampleId": history.data["collectionId"],
        "serviceId": state.service_id,
        "acceptedStateRevision": state.revision,
        "historyAccepted": history.accepted,
        "runtimeAccepted": runtime.accepted,
        "historyHealth": history.health,
        "runtimeHealth": runtime.health,
        "historyRuntimeSameSample": True,
        "historyOriginClockBoundToBoth": True,
        "bindings": [
            {"component": item["component"], "sampleId": item["sampleId"], "originComponent": item["originComponent"]}
            for item in bindings
        ],
    }


def _fixture_stats(path: Path) -> dict[str, Any]:
    info = path.lstat()
    if (
        not stat.S_ISREG(info.st_mode)
        or info.st_uid != os.geteuid()
        or stat.S_IMODE(info.st_mode) != 0o600
        or info.st_size > 64 * 1024
    ):
        raise TrialFailure("fixture_stats_file_untrusted")
    raw = path.read_bytes()
    if len(raw) != info.st_size:
        raise TrialFailure("fixture_stats_file_changed")
    value = json.loads(raw)
    expected = _expected_server_stats()
    if not isinstance(value, dict) or value != expected:
        raise TrialFailure("fixture_server_protocol_census_mismatch")
    return {
        "acceptedConnections": value["acceptedConnections"],
        "methodCounts": value["methodCounts"],
        "threadListPageSizes": value["threadListPageSizes"],
        "uniqueThreadListRows": value["uniqueThreadListRows"],
        "uniqueThreadReadRows": value["uniqueThreadReadRows"],
        "uniqueTurnRows": value["uniqueTurnRows"],
        "hardFail": value["hardFail"],
        "protocolRowCoverageVerified": True,
        "noSyntheticIdentityValuesPersisted": True,
    }


def _cleanup_pending_workers(producer, helpers, expected_argv: list[str]) -> list[dict[str, Any]]:
    cleaned = []
    for worker in tuple(producer.workers.values()):
        process = worker.process
        if process.returncode is None:
            status = producer._exit_status(process)
            if status is None:
                start_ticks = helpers.birth_ticks(process.pid)
                record = helpers.owned_process_record(
                    process, expected_argv, Path(sys.executable),
                    expected_start_ticks=start_ticks,
                )
                if not helpers.verify_process_still_owned(
                    process, record, expected_argv, Path(sys.executable)
                ):
                    raise TrialFailure("incomplete_worker_cleanup_identity_mismatch")
        # Keep the real Runtime group-stop-before-wait ordering. timed_out=True
        # prevents parsing, acceptance, and product-clock refresh on cleanup.
        producer._complete(worker, timed_out=True)
        if process.returncode is None or worker.job.provider in producer.workers:
            raise TrialFailure("incomplete_worker_cleanup_not_reaped")
        cleaned.append({"pid": process.pid, "reaped": True, "stateAccepted": False})
    return cleaned


def _collect_generation(
    producer, serving, state, *, generation: int, helpers, expected_argv: list[str],
    expected_fixture_rows: dict[str, dict[str, Any]], expected_selected_ids: set[str],
    trial_deadline: float,
) -> dict[str, Any]:
    from agent_observer.observation_scheduler import Scheduler
    from agent_observer.service_runtime import _CANONICAL_CLOCK

    producer.scheduler = Scheduler(state.configs)
    if producer.scheduler.timeout != WORKER_TIMEOUT_MS or producer.scheduler.intervals != {"runtime": 2000, "history": 60000}:
        raise TrialFailure("default_scheduler_values_changed")
    component_records = []
    serving.pause.request_and_wait()
    active_worker = None
    active_worker_identity = None
    try:
        for component in ("runtime", "history"):
            if time.monotonic() >= trial_deadline:
                raise TrialFailure("case_wall_timeout")
            jobs = producer.scheduler.start_due(state.clock())
            if len(jobs) != 1 or jobs[0].component != component:
                raise TrialFailure("fresh_default_scheduler_order_mismatch")
            job = jobs[0]
            state.attempt(job.provider, job.component)
            worker = producer._start_worker(job)
            remaining_ms = min(job.deadline - state.clock(), WORKER_TIMEOUT_MS)
            worker_deadline = min(
                trial_deadline, time.monotonic() + max(0, remaining_ms) / 1000
            )
            active_worker = worker
            producer.workers[job.provider] = worker
            process = worker.process
            if worker._clock_provenance is not _CANONICAL_CLOCK:
                raise TrialFailure("canonical_worker_clock_capability_missing")
            if list(process.args) != expected_argv:
                raise TrialFailure("canonical_worker_argv_mismatch")
            start_ticks = helpers.birth_ticks(process.pid)
            worker_identity = helpers.owned_process_record(
                process, expected_argv, Path(sys.executable), expected_start_ticks=start_ticks
            )
            active_worker_identity = worker_identity
            wait_records: list[dict[str, Any]] = []
            _install_wait4_at_normal_complete_wait(process, wait_records)
            drain_timeout = worker_deadline - time.monotonic()
            if remaining_ms <= 0 or drain_timeout <= 0:
                raise TrialFailure("worker_deadline_elapsed_before_drain")
            raw = helpers.drain_worker(process, timeout=drain_timeout)
            observed_exit_status = _wait_exit_status_unreaped(
                producer, process, worker_deadline
            )
            worker.buffer.extend(raw)
            worker.eof = True
            producer._complete(worker)
            active_worker = None
            active_worker_identity = None
            if process.returncode != 0 or len(wait_records) != 1 or wait_records[0]["exitStatus"] != 0:
                raise TrialFailure("canonical_worker_completion_failed")
            component_records.append({
                "component": component,
                "workerIdentity": worker_identity,
                "workerArgvExact": True,
                "clockCapabilityMarkerProved": True,
                "workerOutputBytes": len(raw),
                "workerOutputSha256": sha256(raw),
                "observedExitStatusUnreapedBeforeComplete": observed_exit_status,
                "normalCompleteWaitReapedChild": process.returncode is not None,
                "parentCompleteCalledOnce": True,
                "directWait4AtNormalCompleteWait": wait_records[0],
                "runtimeComplete": component == "runtime",
            })
            del raw, worker, process
        if producer.workers:
            raise TrialFailure("producer_worker_not_retired")
    finally:
        try:
            serving.pause.resume_and_wait()
        finally:
            if active_worker is not None and producer.workers.get(active_worker.job.provider) is active_worker:
                process = active_worker.process
                if process.returncode is None:
                    status = producer._exit_status(process)
                    if status is None and (
                        active_worker_identity is None
                        or not helpers.verify_process_still_owned(
                            process, active_worker_identity, expected_argv, Path(sys.executable)
                        )
                    ):
                        raise TrialFailure("incomplete_worker_ownership_unverified")
                # Preserve the source Runtime's group-stop-before-wait path.
                # timed_out prevents parsing and prevents State.accept here.
                producer._complete(active_worker, timed_out=True)
    snapshot = state.snapshot
    sessions = [] if snapshot is None else snapshot.get("sessions", [])
    if snapshot is None or len(sessions) != ROWS:
        raise TrialFailure("canonical_full_snapshot_row_count_mismatch")
    by_id = {row["identity"]["nativeId"]: row for row in sessions}
    if set(by_id) != set(expected_fixture_rows) or len(by_id) != ROWS:
        raise TrialFailure("canonical_full_snapshot_identity_census_mismatch")
    for identifier, expected in expected_fixture_rows.items():
        row = by_id[identifier]
        if row.get("nativeIds") != {
            "threadId": identifier,
            "sessionTreeRootId": expected["sessionTreeRootId"],
        }:
            raise TrialFailure("canonical_thread_root_identity_join_mismatch")
        if (
            row.get("kind") != "user"
            or row.get("runtime", {}).get("health") != "current"
            or row.get("runtime", {}).get("value") != expected["runtime"]
        ):
            raise TrialFailure("canonical_fixture_runtime_join_mismatch")
    consumer_ids = {
        identifier for identifier, expected in expected_fixture_rows.items()
        if expected["runtime"] == "running" or expected["activityClass"] == "recent"
    }
    if consumer_ids != expected_selected_ids:
        raise TrialFailure("expected_72h_union_fixture_join_mismatch")
    source = snapshot.get("sources", [{}])[0]
    coverage = source.get("coverage", {})
    if (
        coverage.get("saved", {}).get("status") != "complete"
        or coverage.get("runtime", {}).get("status") != "complete"
    ):
        raise TrialFailure("canonical_500_row_coverage_incomplete")
    clock = _clock_join(state)
    return {
        "generation": generation,
        "controlledBurst": True,
        "defaultSchedulerFreshForGeneration": True,
        "defaultSchedulerOrder": [item["component"] for item in component_records],
        "savedCoverage": coverage["saved"]["status"],
        "runtimeCoverage": coverage["runtime"]["status"],
        "rows": len(snapshot["sessions"]),
        "nativeThreadAndSessionRootJoins": len(by_id),
        "completeFixtureIdentityCensus": True,
        "complete72HourUnionExpectedIds": sorted(expected_selected_ids),
        "complete72HourUnionExpectedCount": len(expected_selected_ids),
        "clockJoin": clock,
        "components": component_records,
    }


def _verify_read_outputs(
    generations: list[dict[str, Any]], expected_ids: set[str], fixture_ids: set[str], canonical
) -> dict[str, Any]:
    from agent_observer.active_contract import MAX_FRAME_BYTES
    from agent_observer.working_set_contract import MAX_IDENTITIES, MAX_LEDGER_BYTES
    from agent_observer.working_set_policy import DEFAULT_WINDOW_MS

    comparisons = []
    full_bytes = selected_bytes = 0
    final_ids: set[str] = set()
    for generation in generations:
        grouped = {item["variant"]: item for item in generation["profiles"]}
        if set(grouped) != {"full", "working"}:
            raise TrialFailure("paired_profiles_missing")
        full_reads = grouped["full"]["reads"]
        working_reads = grouped["working"]["reads"]
        if len(full_reads) != 4 or len(working_reads) != 4:
            raise TrialFailure("paired_watch_count_mismatch")
        if len({item["serviceId"] for item in full_reads + working_reads}) != 1:
            raise TrialFailure("paired_service_identity_mismatch")
        clock_join = generation["clockJoin"]
        if {item["serviceId"] for item in full_reads + working_reads} != {
            clock_join["serviceId"]
        }:
            raise TrialFailure("paired_service_state_identity_mismatch")
        full_view_revisions = {item["viewRevision"] for item in full_reads}
        working_view_revisions = {item["viewRevision"] for item in working_reads}
        working_observation_revisions = {
            item["observationRevision"] for item in working_reads
        }
        if len(full_view_revisions) != 1 or full_view_revisions != {
            clock_join["acceptedStateRevision"]
        }:
            raise TrialFailure("full_view_revision_state_join_mismatch")
        if len(working_view_revisions) != 1:
            raise TrialFailure("working_view_revision_unstable")
        if working_observation_revisions != {clock_join["acceptedStateRevision"]}:
            raise TrialFailure("working_observation_revision_state_join_mismatch")
        if any(
            read["historyAccepted"] != clock_join["historyAccepted"]
            or read["runtimeAccepted"] != clock_join["runtimeAccepted"]
            for read in full_reads + working_reads
        ):
            raise TrialFailure("paired_source_accept_counter_mismatch")
        baseline = full_reads[0]
        if baseline["fullRows"] is None or len(baseline["fullRows"]) != ROWS:
            raise TrialFailure("full_facade_row_census_mismatch")
        if {row["identity"]["nativeId"] for row in baseline["fullRows"]} != fixture_ids:
            raise TrialFailure("full_facade_fixture_identity_census_mismatch")
        expected_full_selection = baseline["selectedRows"]
        ids = {row["identity"]["nativeId"] for row in expected_full_selection}
        if ids != expected_ids or len(expected_full_selection) != len(expected_ids):
            raise TrialFailure("full_product_filter_expected_ids_mismatch")
        baseline_digest = sha256(canonical(expected_full_selection).encode("utf-8"))
        full_bytes = len(canonical(baseline["fullRows"]).encode("utf-8"))
        selected_bytes = len(canonical(expected_full_selection).encode("utf-8"))
        for mode in (full_reads, working_reads):
            for read in mode:
                if read["fullRows"] is not None and len(read["fullRows"]) != ROWS:
                    raise TrialFailure("full_facade_changed_row_count")
                if read["fullRows"] is not None and {
                    row["identity"]["nativeId"] for row in read["fullRows"]
                } != fixture_ids:
                    raise TrialFailure("paired_full_fixture_identity_census_mismatch")
                selected = read["selectedRows"]
                if {row["identity"]["nativeId"] for row in selected} != expected_ids:
                    raise TrialFailure("paired_selected_id_join_mismatch")
                if sha256(canonical(selected).encode("utf-8")) != baseline_digest:
                    raise TrialFailure("paired_selected_dto_join_mismatch")
        if any(
            read["workingCoverageStatus"] != "complete"
            or read["workingCoverageMemberCount"] != len(expected_ids)
            for read in working_reads
        ):
            raise TrialFailure("working_set_complete_union_census_mismatch")
        for left, right in zip(full_reads, working_reads, strict=True):
            if (
                left["serviceId"] != right["serviceId"]
                or right["observationRevision"] != left["viewRevision"]
                or left["viewRevision"] != clock_join["acceptedStateRevision"]
            ):
                raise TrialFailure("literal_same_state_join_mismatch")
        final_ids = ids
        comparisons.append({
            "generation": generation["generation"],
            "sameServiceIdAndAcceptedStateRevision": True,
            "workingViewRevisionStableWithinNamespace": True,
            "acceptedHistoryRuntimeCountersAndSampleStable": True,
            "acceptedStateRevision": clock_join["acceptedStateRevision"],
            "workingViewRevision": next(iter(working_view_revisions)),
            "acceptedHistoryCounter": clock_join["historyAccepted"],
            "acceptedRuntimeCounter": clock_join["runtimeAccepted"],
            "historySampleId": clock_join["sampleId"],
            "fullRows": ROWS,
            "selectedRows": len(ids),
            "expectedIdsMatched": True,
            "allEightFacadesSameSelectedDto": True,
            "fullBodyBytes": full_bytes,
            "selectedBodyBytes": selected_bytes,
            "selectedBodyFraction": selected_bytes / full_bytes,
            "workingCoverageComplete": True,
        })
    if not comparisons or any(item["selectedBodyFraction"] > 0.25 for item in comparisons):
        raise TrialFailure("selected_body_exceeds_quarter")
    return {
        "generations": comparisons,
        "sameFinalIdsAllGenerations": final_ids == expected_ids,
        "selectedIds": sorted(final_ids),
        "workingSetWindowMs": DEFAULT_WINDOW_MS,
        "workingSetIdentityLimit": MAX_IDENTITIES,
        "workingSetLedgerBytes": MAX_LEDGER_BYTES,
        "workingSetFrameBytes": MAX_FRAME_BYTES,
        "completeCurrent72HourUnion": True,
        "complete2000RowNativeCase": False,
    }


async def _run_pipeline(replicate: int, interpreter_name: str) -> dict[str, Any]:
    if replicate not in PROFILE_ORDER or interpreter_name not in INTERPRETERS:
        raise TrialFailure("trial_arguments_out_of_bounds")
    helpers = _load_v6_helpers()
    if Path(sys.executable).resolve(strict=True) != helpers.EXPECTED_INTERPRETER_REALPATHS[interpreter_name]:
        raise TrialFailure("interpreter_identity_mismatch")
    if any(name == "agent_observer" or name.startswith("agent_observer.") for name in sys.modules):
        raise TrialFailure("observer_imported_before_source_selection")
    if any(name == "mesh_plus" or name.startswith("mesh_plus.") for name in sys.modules):
        raise TrialFailure("mesh_imported_before_source_selection")
    manifests = _verify_source_manifests()
    helpers.verify_source_pins()
    lock_fd = helpers.acquire_shared_lock()
    run_dir = None
    run_dir_identity = None
    endpoint = binary = config_home = stats_path = stderr_path = rows_path = None
    endpoint_record = endpoint_root_stat = None
    created_endpoint_root = False
    server = producer = state = serving = None
    server_record = server_argv = server_start_ticks = None
    expected_worker_argv = None
    stack_full = stack_working = None
    retain_private = False
    started_wall = time.monotonic()
    trial_deadline = started_wall + CASE_WALL_TIMEOUT_SECONDS
    gc_enabled_at_process_start = gc.isenabled()
    result: dict[str, Any] = {
        "schema": "observer-joined-canonical-sdk-500.v2",
        "status": "failed",
        "source": "b176",
        "sourceCommit": "b176ac06b39daeead4be0a33ff9d781304091fe0",
        "meshCommit": MESH_COMMIT,
        "interpreter": interpreter_name,
        "interpreterExecutable": sys.executable,
        "interpreterVersion": sys.version.split()[0],
        "replicate": replicate,
        "pythonGcEnabledAtTrialEntry": gc_enabled_at_process_start,
        "pythonGcMode": "normal-enabled-no-explicit-collect",
        "profileOrder": list(PROFILE_ORDER[replicate]),
        "rows": ROWS,
        "loadedRows": LOADED,
        "savedRows": SAVED,
        "recentParkedRows": RECENT_PARKED,
        "oldParkedRows": OLD_PARKED,
        "generations": [],
        "cleanup": {},
        "sourcePins": manifests,
    }
    parent_start_ns = None
    parent_end_ns = None
    profile_cpu_ns = {"full": 0, "working": 0}
    fixture_server_rusage = None
    try:
        if not gc_enabled_at_process_start:
            raise TrialFailure("normal_python_gc_disabled")
        stage = "verify_selected_sources"
        selected_paths = (MESH_SOURCE, OBSERVER)
        if any(not path.is_dir() for path in selected_paths):
            raise TrialFailure("selected_source_missing")
        sys.path[0:0] = [str(MESH_SOURCE), str(OBSERVER)]
        from agent_observer.codex_endpoint import inspect_managed_endpoint
        from agent_observer.contract import MAX_SNAPSHOT_BYTES, canonical
        from agent_observer.service_runtime import Runtime
        from agent_observer.service_state import ServiceState
        from agent_observer.working_set_policy import DEFAULT_WINDOW_MS

        mesh_api = importlib.import_module("mesh_plus.api")
        mesh_transport = importlib.import_module("mesh_plus.transport")

        reference = _load_reference()
        result["readWindowMs"] = DEFAULT_WINDOW_MS
        if MAX_SNAPSHOT_BYTES != helpers.MAX_SNAPSHOT_BYTES:
            raise TrialFailure("canonical_snapshot_limit_changed")

        run_dir = Path(tempfile.mkdtemp(prefix=f"joined-sdk-{interpreter_name}-r{replicate}-"))
        run_dir_identity = run_dir.lstat()
        socket_path_bytes = _unix_socket_path_sizes(run_dir)
        if (
            run_dir_identity.st_uid != os.geteuid()
            or not stat.S_ISDIR(run_dir_identity.st_mode)
            or stat.S_IMODE(run_dir_identity.st_mode) != 0o700
            or max(socket_path_bytes.values()) >= UNIX_SOCKET_PATH_LIMIT
        ):
            raise TrialFailure("private_runtime_directory_or_socket_path_guard")
        result["privateRuntimeDirectory"] = {
            "path": str(run_dir),
            "device": run_dir_identity.st_dev,
            "inode": run_dir_identity.st_ino,
            "uid": run_dir_identity.st_uid,
            "mode": stat.S_IMODE(run_dir_identity.st_mode),
            "defaultTempRoot": str(run_dir.parent.resolve()),
            "socketPathBytes": socket_path_bytes,
            "maxSocketPathBytes": max(socket_path_bytes.values()),
            "requiredStrictlyBelowBytes": UNIX_SOCKET_PATH_LIMIT,
        }
        rows_path = run_dir / "fixture-rows.json"
        stats_path = run_dir / "fixture-stats.json"
        stderr_path = run_dir / "fixture-server.stderr"
        expected_rows, fixture = build_fixture(rows_path)
        fixture_ids = set(expected_rows)
        expected_ids = {
            identifier for identifier, metadata in expected_rows.items()
            if metadata["runtime"] == "running" or metadata["activityClass"] == "recent"
        }
        result["fixture"] = {
            "sha256": fixture["sha256"], "bytes": fixture["bytes"],
            "fixtureEpochSeconds": fixture["fixtureEpochSeconds"],
            "rows": ROWS, "loaded": LOADED, "saved": SAVED,
            "recentParked": RECENT_PARKED, "oldParked": OLD_PARKED,
            "contentFreeMetadataOnlyTurns": ROWS,
            "expectedFixtureIdsSha256": sha256("\n".join(sorted(fixture_ids)).encode("ascii")),
            "expectedSelectedIdsSha256": sha256("\n".join(sorted(expected_ids)).encode("ascii")),
        }
        del fixture

        stage = "prepare_private_fake_endpoint"
        (
            config_home, endpoint, binary, binary_digest, venv_config, venv_digest,
            endpoint_root_stat, created_endpoint_root,
        ) = helpers.make_config_home(run_dir)
        if os.path.lexists(endpoint):
            raise TrialFailure("endpoint_target_present")

        stage = "prepare_one_joined_state_and_runtimes"
        state = ServiceState(
            host_scope="fixture", configs={"codex": (str(config_home), "explicit")},
            working_set_window_ms=DEFAULT_WINDOW_MS,
        )
        serving = ServingRuntime(state, run_dir / "service.sock", Runtime, encoded_limit=64 * 1024 * 1024)
        if serving.runtime.heartbeat != 10_000:
            raise TrialFailure("service_heartbeat_default_changed")
        serving.start()
        producer = Runtime(state, run_dir / "producer-unused.sock", collect=True)
        if producer._clock_factory is not producer.worker_factory:
            raise TrialFailure("producer_clock_factory_not_canonical")
        expected_worker_argv = [
            sys.executable, "-I", "-B", str(OBSERVER / "agent_observer/_service_worker.py")
        ]
        result["runtimes"] = {
            "oneSharedWorkingSetEnabledState": True,
            "servingRuntimeCollect": serving.runtime.collect,
            "servingRuntimeHeartbeatMs": serving.runtime.heartbeat,
            "producerRuntimeUsesDefaultCanonicalFactory": True,
            "producerRuntimeUsesDefaultScheduler": True,
            "producerWorkerArgv": expected_worker_argv,
            "workerTimeoutMs": producer.scheduler.timeout,
            "schedulerIntervalsMs": dict(producer.scheduler.intervals),
            "defaultWorkingSetWindowMs": DEFAULT_WINDOW_MS,
        }

        stage = "prepare_full_and_working_mesh_profiles"
        stack_full = ProfileStack(
            variant="full", root=run_dir, state=state, Runtime=Runtime,
            mesh_api=mesh_api, mesh_transport=mesh_transport, mesh_source=MESH_SOURCE,
        )
        stack_working = ProfileStack(
            variant="working", root=run_dir, state=state, Runtime=Runtime,
            mesh_api=mesh_api, mesh_transport=mesh_transport, mesh_source=MESH_SOURCE,
        )
        await stack_full.start()
        await stack_working.start()
        if any(stack.reader.inspect()["activeConnections"] for stack in (stack_full, stack_working)):
            raise TrialFailure("readers_not_idle_before_measurement")
        result["loadedProjectModules"] = _selected_module_files({
            "observer": json.loads(OBSERVER_MANIFEST.read_text(encoding="utf-8")),
            "mesh": json.loads(MESH_MANIFEST.read_text(encoding="utf-8")),
        })

        stage = "start_managed_private_fixture_endpoint"
        server_argv = [
            str(binary), "-I", "-B", str(BASE / "fixture_server.py"),
            "--endpoint", str(endpoint), "--config-home", str(config_home),
            "--rows-file", str(rows_path), "--stats-file", str(stats_path),
        ]
        stderr_fd = os.open(stderr_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | getattr(os, "O_NOFOLLOW", 0), 0o600)
        with os.fdopen(stderr_fd, "wb", closefd=True) as stderr_stream:
            server = subprocess.Popen(
                server_argv, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=stderr_stream, cwd=run_dir, start_new_session=True,
                preexec_fn=helpers.server_file_limit,
            )
        server_start_ticks = helpers.birth_ticks(server.pid)
        server_record = helpers.owned_process_record(
            server, server_argv, binary, expected_start_ticks=server_start_ticks,
        )
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            if helpers.proc_state(server.pid) == "Z":
                raise TrialFailure("fixture_server_exit_before_bind")
            try:
                info = endpoint.lstat()
                if stat.S_ISSOCK(info.st_mode):
                    break
            except FileNotFoundError:
                pass
            time.sleep(.01)
        else:
            raise TrialFailure("fixture_server_bind_timeout")
        if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
            raise TrialFailure("fixture_endpoint_ownership_mismatch")
        inode = helpers.listener_inode(endpoint)
        if not any(os.readlink(fd) == f"socket:[{inode}]" for fd in Path(f"/proc/{server.pid}/fd").iterdir()):
            raise TrialFailure("fixture_listener_fd_unowned")
        endpoint_record = {"device": info.st_dev, "inode": info.st_ino, "listenerInode": inode}
        identity = inspect_managed_endpoint(config_home)
        if (
            identity.pid != server.pid
            or identity.start_ticks != server_record["startTicks"]
            or identity.endpoint != str(endpoint)
            or identity.binary_sha256 != binary_digest
            or identity.listener_inode != inode
            or identity.endpoint_inode != info.st_ino
            or identity.version != "0.0.0"
        ):
            raise TrialFailure("managed_fixture_endpoint_qualification_mismatch")
        result["managedEndpointQualified"] = True
        result["fakeBinarySha256"] = binary_digest
        result["fakeInterpreterConfigSha256"] = venv_digest
        result["endpointInode"] = info.st_ino
        result["fixtureServerIdentity"] = server_record

        # The fixture server's full lifetime CPU is included once as a
        # conservative shared synthetic-input cost. Parent setup above this
        # point and final process/owner cleanup below are outside the timed span.
        generations = []
        used_request_ids: set[str] = set()
        used_nonces: set[str] = set()
        parent_start_ns = time.process_time_ns()
        for generation_index in range(1, GENERATIONS + 1):
            if time.monotonic() >= trial_deadline:
                raise TrialFailure("case_wall_timeout")
            gen = _collect_generation(
                producer, serving, state, generation=generation_index,
                helpers=helpers, expected_argv=expected_worker_argv,
                expected_fixture_rows=expected_rows, expected_selected_ids=expected_ids,
                trial_deadline=trial_deadline,
            )
            gen["profiles"] = []
            # Both readers use this unchanged current accepted history sample.
            current_sample = gen["clockJoin"]["sampleId"]
            for variant in PROFILE_ORDER[replicate]:
                stack = stack_full if variant == "full" else stack_working
                begin = time.process_time_ns()
                profile_result = await _watch_four(
                    stack,
                    trial=replicate,
                    generation=generation_index,
                    expected_history_accepted=gen["clockJoin"]["historyAccepted"],
                    expected_accepted=gen["clockJoin"]["runtimeAccepted"],
                    reference=reference,
                    canonical=canonical,
                    used_request_ids=used_request_ids,
                    used_nonces=used_nonces,
                )
                profile_cpu_ns[variant] += time.process_time_ns() - begin
                history_receipt = state.receipts["codex"]["history"]
                runtime_receipt = state.receipts["codex"]["runtime"]
                if (
                    history_receipt.data is None
                    or runtime_receipt.data is None
                    or history_receipt.data["collectionId"] != current_sample
                    or history_receipt.accepted != gen["clockJoin"]["historyAccepted"]
                    or runtime_receipt.accepted != gen["clockJoin"]["runtimeAccepted"]
                    or state.revision != gen["clockJoin"]["acceptedStateRevision"]
                ):
                    raise TrialFailure("profile_read_changed_accepted_source_join")
                gen["profiles"].append(profile_result)
            generations.append(gen)
        parent_end_ns = time.process_time_ns()

        stage = "post_window_identity_and_body_crosschecks"
        read_join = _verify_read_outputs(generations, expected_ids, fixture_ids, canonical)
        parent_total_ns = parent_end_ns - parent_start_ns
        read_windows_ns = profile_cpu_ns["full"] + profile_cpu_ns["working"]
        if read_windows_ns > parent_total_ns:
            raise TrialFailure("cpu_windows_overlap_parent")
        common_parent_ns = parent_total_ns - read_windows_ns
        worker_cpu_ns = sum(
            item["directWait4AtNormalCompleteWait"]["userCpuNs"]
            + item["directWait4AtNormalCompleteWait"]["systemCpuNs"]
            for gen in generations for component in gen["components"] for item in [component]
        )
        result["cpu"] = {
            "scope": "joined controlled b176 canonical producer + same-State full/working public SDK reads",
            "parentContinuousCpuNs": parent_total_ns,
            "parentFullReadWindowsCpuNs": profile_cpu_ns["full"],
            "parentWorkingReadWindowsCpuNs": profile_cpu_ns["working"],
            "commonParentCpuNs": common_parent_ns,
            "workerDirectWait4CpuNs": worker_cpu_ns,
            "fixtureServerDirectWait4CpuNsAddedOnce": None,
            "observedJoinedPairCpuNs": None,
            "derivedFullCpuNs": None,
            "derivedWorkingCpuNs": None,
            "arithmeticPendingUntilFixtureServerReaped": True,
            "parentCpuIncludesRuntimeThreadMeshReadersAndProductFilter": True,
            "parentCpuHarnessExclusions": [],
            "fixtureServerCpuScope": "full synthetic server process lifetime; conservative setup overhead included once",
            "ownerCleanupIncludedInParentWindow": False,
        }
        result["readJoin"] = read_join
        result["generations"] = generations
        result["workerProcessCount"] = sum(len(gen["components"]) for gen in generations)
        retirement_count = sum(
            profile["retirementsVerified"]
            for gen in generations for profile in gen["profiles"]
        )
        for gen in generations:
            for profile in gen["profiles"]:
                for read in profile["reads"]:
                    full_rows = read.pop("fullRows")
                    selected_rows = read.pop("selectedRows")
                    read["fullRowCount"] = None if full_rows is None else len(full_rows)
                    read["selectedRowCount"] = len(selected_rows)
        result["all24PublicWatchRetirementsVerified"] = (
            result["workerProcessCount"] == 6
            and len(used_request_ids) == 24
            and len(used_nonces) == 24
            and retirement_count == 24
        )
        result["status"] = "functional_and_timing_passed_unreviewed"  # replaced only after review-run gate
    except TrialFailure as error:
        result["failureStage"] = locals().get("stage", "preflight")
        result["failureReason"] = str(error)
    except Exception as error:
        result["failureStage"] = locals().get("stage", "preflight")
        result["failureClass"] = type(error).__name__
        result["failureReason"] = type(error).__name__
    finally:
        cleanup = result.setdefault("cleanup", {})
        for stack in (stack_working, stack_full):
            if stack is not None:
                try:
                    await stack.close()
                    metrics = stack.reader.inspect() if stack.reader is not None else None
                    cleanup[f"{stack.variant}ReaderActiveConnections"] = None if metrics is None else metrics["activeConnections"]
                    cleanup[f"{stack.variant}BridgeHandlersActive"] = stack.handler_count["active"]
                    cleanup[f"{stack.variant}ReaderConnectionsBalanced"] = (
                        metrics is not None
                        and metrics["connectionsOpened"] == metrics["connectionsClosed"]
                        and metrics["cleanupFailures"] == 0
                    )
                except Exception as error:
                    cleanup[f"{stack.variant}CleanupError"] = type(error).__name__
        if serving is not None:
            try:
                serving.close()
                cleanup["serviceRuntime"] = serving.cleanup
            except Exception as error:
                cleanup["serviceRuntimeError"] = type(error).__name__
        if producer is not None:
            try:
                pending_cleanup = _cleanup_pending_workers(
                    producer, helpers, expected_worker_argv or []
                )
                cleanup["producerWorkerProcessesReaped"] = not producer.workers
                result["pendingWorkerCleanup"] = pending_cleanup
            except Exception as error:
                cleanup["producerWorkerProcessesReaped"] = False
                cleanup["producerWorkerCleanupError"] = str(error) if isinstance(error, TrialFailure) else type(error).__name__
                retain_private = True
            try:
                for memo in producer.image_memos.values():
                    memo.close()
                producer.selector.close()
                cleanup["producerResourcesClosed"] = True
            except Exception as error:
                cleanup["producerResourcesClosed"] = False
                cleanup["producerResourceCleanupError"] = type(error).__name__
        if server is not None:
            try:
                pre_reaped_server = None
                if server_record is None and server.returncode is None:
                    pre_reaped_server = helpers.reap_owned_child_if_exited(server)
                    if pre_reaped_server is None:
                        server_start_ticks = helpers.birth_ticks(server.pid)
                        server_record = helpers.owned_process_record(
                            server, server_argv or [], binary,
                            expected_start_ticks=server_start_ticks,
                        )
                if pre_reaped_server is None:
                    server_exit, fixture_server_rusage = helpers.stop_owned_server(
                        server, server_record, server_argv, binary,
                    )
                else:
                    server_exit, fixture_server_rusage = pre_reaped_server
                cleanup["fixtureServerExitStatus"] = server_exit
                cleanup["fixtureServerReaped"] = server.returncode is not None
                if server_exit != 0:
                    raise TrialFailure("fixture_server_shutdown_failed")
                server = None
                cleanup["fixtureServerStderr"] = helpers.stderr_digest(stderr_path)
                if cleanup["fixtureServerStderr"]["bytes"] != 0:
                    raise TrialFailure("fixture_server_stderr_not_empty")
                result["fixtureProtocol"] = _fixture_stats(stats_path)
            except Exception as error:
                cleanup["fixtureServerReaped"] = server is not None and server.returncode is not None
                cleanup["fixtureServerCleanupError"] = str(error) if isinstance(error, TrialFailure) else type(error).__name__
                if not cleanup["fixtureServerReaped"]:
                    retain_private = True
        else:
            cleanup["fixtureServerReaped"] = True
        if fixture_server_rusage is not None:
            fixture_server_cpu_ns = fixture_server_rusage["userCpuNs"] + fixture_server_rusage["systemCpuNs"]
            result["fixtureServerDirectWait4"] = fixture_server_rusage
            if "cpu" in result:
                cpu = result["cpu"]
                cpu["fixtureServerDirectWait4CpuNsAddedOnce"] = fixture_server_cpu_ns
                total_parent_ns = cpu["parentContinuousCpuNs"]
                worker_ns = cpu["workerDirectWait4CpuNs"]
                full_ns = cpu["parentFullReadWindowsCpuNs"]
                working_ns = cpu["parentWorkingReadWindowsCpuNs"]
                common_ns = cpu["commonParentCpuNs"] + worker_ns + fixture_server_cpu_ns
                cpu["observedJoinedPairCpuNs"] = total_parent_ns + worker_ns + fixture_server_cpu_ns
                cpu["commonProducerAndFixtureCpuNs"] = common_ns
                cpu["derivedFullCpuNs"] = common_ns + full_ns
                cpu["derivedWorkingCpuNs"] = common_ns + working_ns
                cpu["arithmeticPendingUntilFixtureServerReaped"] = False
                cpu["claimLimit"] = "one joined controlled fixture; derived variants reuse the same one-time producer and server cost"
        if endpoint is not None:
            if not cleanup.get("fixtureServerReaped", False):
                cleanup["ownedEndpointRemoved"] = False
            elif os.path.lexists(endpoint):
                try:
                    info = endpoint.lstat()
                    if (
                        endpoint_record is None
                        or info.st_dev != endpoint_record["device"]
                        or info.st_ino != endpoint_record["inode"]
                        or info.st_uid != os.geteuid()
                        or not stat.S_ISSOCK(info.st_mode)
                    ):
                        raise TrialFailure("fixture_endpoint_cleanup_identity_mismatch")
                    endpoint.unlink()
                    cleanup["ownedEndpointRemoved"] = True
                except Exception as error:
                    cleanup["ownedEndpointRemoved"] = False
                    cleanup["endpointCleanupError"] = str(error) if isinstance(error, TrialFailure) else type(error).__name__
                    retain_private = True
            else:
                cleanup["ownedEndpointRemoved"] = True
        else:
            cleanup["ownedEndpointRemoved"] = True
        if endpoint is not None and endpoint_root_stat is not None and not os.path.lexists(endpoint):
            cleanup["endpointDirectoryRemoved"] = helpers.cleanup_endpoint_root(
                endpoint, endpoint_root_stat, created_endpoint_root
            )
        else:
            cleanup["endpointDirectoryRemoved"] = not created_endpoint_root
        workers_reaped = producer is None or not producer.workers
        processes_reaped = (server is None or server.returncode is not None) and workers_reaped
        if run_dir is not None and run_dir.exists() and not retain_private and processes_reaped and not os.path.lexists(endpoint):
            try:
                current = run_dir.lstat()
                if (
                    run_dir_identity is None
                    or current.st_dev != run_dir_identity.st_dev
                    or current.st_ino != run_dir_identity.st_ino
                    or current.st_uid != os.geteuid()
                    or not stat.S_ISDIR(current.st_mode)
                ):
                    raise TrialFailure("private_run_directory_identity_mismatch")
                shutil.rmtree(run_dir)
                cleanup["privateRunDirectoryRemoved"] = not run_dir.exists()
            except Exception as error:
                cleanup["privateRunDirectoryRemoved"] = False
                cleanup["privateDirectoryCleanupError"] = str(error) if isinstance(error, TrialFailure) else type(error).__name__
                retain_private = True
        else:
            cleanup["privateRunDirectoryRemoved"] = run_dir is None or not run_dir.exists()
            if run_dir is not None and run_dir.exists():
                cleanup["privateRunDirectoryRetained"] = True
        try:
            import fcntl
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)
            cleanup["sharedLockReleased"] = True
        except OSError as error:
            cleanup["sharedLockReleased"] = False
            cleanup["sharedLockReleaseError"] = type(error).__name__
            result["status"] = "failed"
        if retain_private:
            result["status"] = "failed"
            result.setdefault("failureStage", "cleanup")
            result.setdefault("failureReason", "owned_process_or_endpoint_cleanup_unverified")
        cleanup_keys = (
            "fixtureServerReaped", "ownedEndpointRemoved", "privateRunDirectoryRemoved",
            "sharedLockReleased", "producerResourcesClosed", "producerWorkerProcessesReaped",
        )
        for key in cleanup_keys:
            if cleanup.get(key) is not True:
                result["status"] = "failed"
        if any(key.endswith("Error") for key in cleanup):
            result["status"] = "failed"
        service_runtime_cleanup = cleanup.get("serviceRuntime")
        if service_runtime_cleanup is not None and not (
            service_runtime_cleanup.get("runtimePeersAfterRun") == 0
            and service_runtime_cleanup.get("selectorRegistrationsAfterRun") == 0
            and service_runtime_cleanup.get("selectorClosed") is True
            and service_runtime_cleanup.get("runtimeThreadAlive") is False
            and service_runtime_cleanup.get("selectorHookRestored") is True
        ):
            result["status"] = "failed"
        for name in ("full", "working"):
            if cleanup.get(f"{name}ReaderActiveConnections") not in (None, 0):
                result["status"] = "failed"
            if cleanup.get(f"{name}BridgeHandlersActive") not in (None, 0):
                result["status"] = "failed"
            if cleanup.get(f"{name}ReaderConnectionsBalanced") is False:
                result["status"] = "failed"
        if created_endpoint_root and cleanup.get("endpointDirectoryRemoved") is not True:
            result["status"] = "failed"
        if result["status"] != "failed" and result.get("status") == "functional_and_timing_passed_unreviewed":
            result["status"] = "pass"
        if "failureStage" not in result and result["status"] == "failed":
            result["failureStage"] = "cleanup"
            result["failureReason"] = "cleanup_incomplete"
        if not os.path.lexists(BASE / f"{interpreter_name}-r{replicate}.json"):
            output = BASE / f"{interpreter_name}-r{replicate}.json"
            try:
                output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
                os.chmod(output, 0o600)
            except OSError:
                result["status"] = "failed"
        else:
            result["status"] = "failed"
            result["receiptWriteError"] = "receipt_already_exists"
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline-check", action="store_true")
    parser.add_argument("--run-reviewed-trial", action="store_true")
    parser.add_argument("--interpreter", choices=tuple(INTERPRETERS))
    parser.add_argument("--replicate", type=int, choices=(1, 2))
    args = parser.parse_args()
    try:
        if args.offline_check and not args.run_reviewed_trial:
            print(json.dumps(_offline_checks(), indent=2, sort_keys=True))
            return 0
        if not args.run_reviewed_trial or args.interpreter is None or args.replicate is None:
            raise TrialFailure("explicit_reviewed_trial_arguments_required")
        result = asyncio.run(_run_pipeline(args.replicate, args.interpreter))
        print(json.dumps({key: result[key] for key in ("status", "failureStage", "failureReason", "cpu", "readJoin", "cleanup") if key in result}, indent=2, sort_keys=True))
        return 0 if result.get("status") == "pass" else 1
    except TrialFailure as error:
        print(json.dumps({"status": "failed", "reason": str(error)}, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
