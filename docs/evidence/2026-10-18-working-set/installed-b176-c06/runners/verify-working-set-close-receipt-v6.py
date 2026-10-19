from __future__ import annotations

import json
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RECEIPT = ROOT / "working-set-fixed-ssh-close-receipt-v6.json"
EXPECTED_UID = 1000
EXPECTED_OBSERVER_WHEEL = "30a4e30b2fdc1f2bb7c6ee8b6cbf2fe16fdf32fbb7b95932b0d8e5c68eef9e5e"
EXPECTED_MESH_WHEEL = "287d98c9d16f492a3df43a391b2036f98760c805480a74a7f93b3fcd2d8cf14a"


class ReceiptError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


def require(condition, code):
    if not condition:
        raise ReceiptError(code)


def lexists(path):
    try:
        Path(path).lstat()
        return True
    except FileNotFoundError:
        return False


def proc_start_ticks(pid):
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
    except FileNotFoundError:
        return None
    tail = raw[raw.rfind(")") + 2 :].split()
    if len(tail) <= 19:
        return None
    return int(tail[19])


def main():
    try:
        root_stat = ROOT.stat(follow_symlinks=False)
        require(root_stat.st_uid == EXPECTED_UID and root_stat.st_mode & 0o077 == 0, "private_root_policy")
        receipt_deadline = time.monotonic() + 2.0
        while not lexists(RECEIPT) and time.monotonic() < receipt_deadline:
            time.sleep(0.025)
        require(lexists(RECEIPT), "close_receipt_missing")
        receipt_stat = RECEIPT.stat(follow_symlinks=False)
        require(receipt_stat.st_uid == EXPECTED_UID and receipt_stat.st_mode & 0o777 == 0o600, "receipt_policy")
        require(RECEIPT.is_file() and not RECEIPT.is_symlink(), "receipt_file_shape")
        value = json.loads(RECEIPT.read_text())
        require(value.get("schema") == "agent-observer.working-set-fixed-ssh-close-receipt.v6", "receipt_schema")
        require(value.get("status") == "cleanup_complete", "runtime_cleanup_incomplete")
        terminal = value.get("bridgeRunTerminal")
        require(isinstance(terminal, dict), "bridge_terminal_missing")
        signal_exit = (
            value.get("exitPath") == "owned_transport_signal_unwind"
            and value.get("caughtSignal") in {"SIGTERM", "SIGHUP"}
            and value.get("bridgeExitCode") == 1
            and value.get("reasonCode") == "owned_transport_signal"
            and value.get("meshStderrErrorTokens") == []
        )
        eof_exit = (
            value.get("exitPath") == "bridge_returned"
            and value.get("caughtSignal") is None
            and value.get("bridgeExitCode") == 1
            and value.get("reasonCode") == "bridge_returned_nonzero"
            and terminal.get("expectedTransportTerminal") is True
            and terminal.get("type") in {"EOFError", "BrokenPipeError",
                                         "ConnectionResetError", "ConnectionAbortedError"}
            and terminal.get("code") is None
            and value.get("meshStderrErrorTokens") == ["bridge_failed"]
            and value.get("meshStderrLineCount") == 1
        )
        clean_exit = (
            value.get("exitPath") == "bridge_returned"
            and value.get("bridgeExitCode") == 0
            and terminal.get("type") is None
            and value.get("meshStderrErrorTokens") == []
        )
        require(signal_exit or eof_exit or clean_exit, "bridge_terminal_unclassified")
        bridge_class = ("owned_terminated_nonzero" if signal_exit else
                        "transport_eof_nonzero" if eof_exit else "normal_cli_exit")
        require(value.get("windowMs") == 259200000, "working_set_window_mismatch")
        require(value.get("readyEmitted") is True, "ready_not_emitted")
        require(value.get("runtimeCollectFalse") is True, "runtime_collection_not_disabled")
        require(value.get("gcDisabledBeforeProjectImports") is True, "remote_gc_not_disabled_before_imports")
        require(value.get("runtimeThreadStopped") is True, "runtime_thread_not_stopped")
        require(value.get("runtimePeerCount") == 0, "runtime_peer_cleanup_incomplete")
        require(value.get("runtimeSelectorClosed") is True, "runtime_selector_not_closed")
        require(value.get("runtimeSocketAbsent") is True, "runtime_socket_not_absent")
        require(value.get("privateConfigAbsent") is True, "private_config_not_absent")
        require(value.get("sourceCleanupComplete") is True, "source_cleanup_incomplete")
        require(value.get("runtimeWorkerCount") == 0 and value.get("runtimeWorkerStarts") == 0, "synthetic_runtime_started_worker")
        require(value.get("sourceRowCount") == 4 and value.get("expectedSelectedCount") == 2, "fixture_selection_shape")

        process = value.get("process")
        require(isinstance(process, dict), "process_identity_missing")
        pid, birth = process.get("pid"), process.get("startTicks")
        require(type(pid) is int and pid > 0 and type(birth) is int and birth > 0, "process_birth_missing")
        require(process.get("uid") == EXPECTED_UID, "process_uid_mismatch")
        require(process.get("pythonVersion") == "3.14.8", "process_python_version_mismatch")
        require(process.get("pythonEntrypointMatchesPrivateVenv") is True, "process_venv_entrypoint_mismatch")
        require(process.get("resolvedExecutableSha256") == "375532f83be620283ab780c14ca6bcc5907dc379d2b621de0c5d0a112cf5458b", "process_executable_hash_mismatch")
        current_birth = proc_start_ticks(pid)
        process_deadline = time.monotonic() + 2.0
        while current_birth == birth and time.monotonic() < process_deadline:
            time.sleep(0.025)
            current_birth = proc_start_ticks(pid)
        process_same_incarnation_alive = current_birth == birth

        socket_path = value.get("runtimeSocketPath")
        config_path = value.get("privateConfigPath")
        require(isinstance(socket_path, str) and Path(socket_path).is_absolute(), "runtime_socket_path_missing")
        require(isinstance(config_path, str) and Path(config_path).is_absolute(), "private_config_path_missing")
        socket = Path(socket_path)
        config = Path(config_path)
        runtime_dir = socket.parents[1] if len(socket.parents) > 1 else Path("/")
        require(socket.name == "read.sock" and socket.parent.name == "private" and runtime_dir.parent == Path("/tmp") and runtime_dir.name.startswith("ao-service-test-"), "runtime_socket_path_scope")
        require(config.name == "sources.toml" and config.parent.parent == Path("/tmp") and config.parent.name.startswith("ao-ws-bridge-config-"), "private_config_path_scope")
        runtime_paths_absent = not lexists(socket) and not lexists(socket.parent) and not lexists(runtime_dir)
        config_paths_absent = not lexists(config) and not lexists(config.parent)

        loaded_initial = value.get("loadedModulesInitial")
        loaded_final = value.get("loadedModulesFinal")
        expected_wheels = {"agent_observer": EXPECTED_OBSERVER_WHEEL, "mesh_plus": EXPECTED_MESH_WHEEL}
        for loaded in (loaded_initial, loaded_final):
            require(isinstance(loaded, dict) and loaded.get("installedModuleBytesExact") is True, "installed_module_bytes_unproved")
            require(loaded.get("wheelSha256") == expected_wheels, "installed_wheel_hash_mismatch")
            require(type(loaded.get("observerModuleCount")) is int and loaded["observerModuleCount"] > 0, "observer_module_count_missing")
            require(type(loaded.get("meshModuleCount")) is int and loaded["meshModuleCount"] > 0, "mesh_module_count_missing")
        require(value.get("moduleBytesExactAtInitialAndFinalChecks") is True, "loaded_modules_not_rechecked_after_bridge")
        require(loaded_initial.get("wheelSha256") == loaded_final.get("wheelSha256"), "loaded_wheel_hash_changed")
        require(not process_same_incarnation_alive, "remote_fixture_process_still_alive")
        require(runtime_paths_absent and config_paths_absent, "remote_fixture_paths_remain")

        result = {
            "schema": "agent-observer.working-set-fixed-ssh-close-check.v6",
            "status": "pass",
            "reasonCode": "none",
            "exitPath": value["exitPath"],
            "caughtSignal": value.get("caughtSignal"),
            "remoteProcess": {"pid": pid, "startTicks": birth, "uid": process["uid"],
                              "pythonVersion": process["pythonVersion"],
                              "executableSha256": process["resolvedExecutableSha256"],
                              "sameIncarnationStillAlive": False},
            "runtime": {"collectFalse": True, "threadStopped": True, "peerCount": 0,
                        "selectorClosed": True, "socketPathsAbsent": True,
                        "workerStarts": 0, "workerCount": 0, "sourceCleanupComplete": True},
            "privateConfigAbsent": True,
            "bridgeClassification": bridge_class,
            "bridgeRunTerminal": terminal,
            "bridgeExitCode": value["bridgeExitCode"],
            "gracefulEofPass": clean_exit,
            "normalCliExitPass": clean_exit,
            "gcDisabledBeforeProjectImports": True,
            "loadedModulesInitial": {k: loaded_initial.get(k) for k in ("observerModuleCount", "meshModuleCount", "installedModuleBytesExact", "wheelSha256")},
            "loadedModulesFinal": {k: loaded_final.get(k) for k in ("observerModuleCount", "meshModuleCount", "installedModuleBytesExact", "wheelSha256")},
            "loadedModules": {k: loaded_final.get(k) for k in ("observerModuleCount", "meshModuleCount", "installedModuleBytesExact", "wheelSha256")},
        }
        print(json.dumps(result, sort_keys=True, separators=(",", ":")))
        return 0
    except ReceiptError as error:
        print(json.dumps({"schema": "agent-observer.working-set-fixed-ssh-close-check.v6",
                          "status": "failed", "reasonCode": error.code}, sort_keys=True, separators=(",", ":")))
        return 1
    except BaseException:
        print(json.dumps({"schema": "agent-observer.working-set-fixed-ssh-close-check.v6",
                          "status": "failed", "reasonCode": "receipt_validation_failed"}, sort_keys=True, separators=(",", ":")))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
