from __future__ import annotations

import contextlib
import gc
import hashlib
import importlib.util
import io
import json
import os
import signal
import sys
import sysconfig
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = ROOT.parent
TESTS = ROOT / "bootstrap" / "fixtures" / "tests"
SOURCE = "working_set_fixture"
HOST = "fixture"
WINDOW_MS = 72 * 60 * 60 * 1000
KNOWN_CODES = {
    "bridge_failed", "source_config_policy", "source_config_capacity", "source_config_shape",
    "source_not_configured", "source_descriptor_shape", "source_binding", "unsupported_capability",
    "unsupported_contract", "scope_mismatch", "source_unavailable", "request_deadline",
    "delivery_timing", "ipc_directory_policy", "ipc_socket_policy", "publisher_restart",
    "reader_clock_scope", "working_set_policy_binding", "working_set_preparation_binding",
}
SAFE_EXCEPTION_TYPES = {
    "EOFError", "BrokenPipeError", "ConnectionResetError", "ConnectionAbortedError", "TimeoutError",
    "SystemExit", "KeyboardInterrupt", "OSError", "RuntimeError", "ValueError", "TypeError",
    "AttributeError", "ImportError", "ProtocolError", "AssertionError",
}


class CappedTextSink(io.TextIOBase):
    def __init__(self, limit=32768):
        self.limit = limit
        self.parts = []
        self.size = 0
        self.truncated = False

    def write(self, value):
        text = str(value)
        remaining = self.limit - self.size
        if remaining > 0:
            kept = text[:remaining]
            self.parts.append(kept)
            self.size += len(kept)
        if len(text) > max(remaining, 0):
            self.truncated = True
        return len(text)

    def getvalue(self):
        return "".join(self.parts)


def safe_exception(error):
    name = type(error).__name__
    code = getattr(error, "code", None)
    return (name if name in SAFE_EXCEPTION_TYPES else "other",
            code if isinstance(code, str) and code in KNOWN_CODES else None)


def known_mesh_stderr_tokens(text):
    found = set()
    for line in text.splitlines():
        try:
            value = json.loads(line)
        except (ValueError, TypeError):
            continue
        token = value.get("error") if isinstance(value, dict) else None
        if isinstance(token, str):
            found.add(token if token in KNOWN_CODES else "other")
    return sorted(found)
RECEIPT = ROOT / "working-set-fixed-ssh-close-receipt-v8.json"


class OwnedTransportSignal(BaseException):
    def __init__(self, signum):
        self.signum = signum
        super().__init__(signum)


def stop_on_owned_transport_signal(signum, _frame):
    raise OwnedTransportSignal(signum)


def digest_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def process_start_ticks(pid):
    raw = Path(f"/proc/{pid}/stat").read_text()
    tail = raw[raw.rfind(")") + 2 :].split()
    if len(tail) <= 19:
        raise RuntimeError("process_stat_unavailable")
    return int(tail[19])


def loaded_module_wheel_check():
    purelib = Path(sysconfig.get_paths()["purelib"]).resolve()
    expected_prefix = (PACKAGE_ROOT / "venv-314").resolve()
    if expected_prefix not in purelib.parents:
        raise RuntimeError("private_site_packages_mismatch")
    wheels = {
        "agent_observer": ROOT / "wheels" / "agent_observer-0.7.0a7-py3-none-any.whl",
        "mesh_plus": ROOT / "wheels" / "mesh_plus-0.1.0a23-py3-none-any.whl",
    }
    wheel_sha = {}
    entries = {}
    for package, wheel in wheels.items():
        wheel_sha[package] = digest_file(wheel)
        with zipfile.ZipFile(wheel) as archive:
            entries[package] = {
                name[len(package) + 1 :]: archive.read(name)
                for name in archive.namelist()
                if name.startswith(package + "/") and not name.endswith("/")
            }
    loaded = {}
    for name, module in tuple(sys.modules.items()):
        if not name.startswith(("agent_observer", "mesh_plus")):
            continue
        origin = getattr(module, "__file__", None)
        if origin is None:
            continue
        path = Path(origin).resolve()
        if not path.is_relative_to(purelib):
            raise RuntimeError("loaded_package_outside_private_venv")
        package = "agent_observer" if name.startswith("agent_observer") else "mesh_plus"
        if path.suffix == ".pyc":
            try:
                path = Path(importlib.util.source_from_cache(str(path)))
            except (ValueError, NotImplementedError):
                raise RuntimeError("loaded_bytecode_origin_unknown") from None
        relative = path.relative_to(purelib).as_posix().split("/", 1)[1]
        expected = entries[package].get(relative)
        if expected is None or digest_file(path) != hashlib.sha256(expected).hexdigest():
            raise RuntimeError("loaded_module_bytes_mismatch")
        loaded[name] = True
    if not any(name == "agent_observer" for name in loaded):
        raise RuntimeError("observer_package_not_loaded")
    if not any(name == "mesh_plus" for name in loaded):
        raise RuntimeError("mesh_package_not_loaded")
    return {
        "observerModuleCount": sum(name.startswith("agent_observer") for name in loaded),
        "meshModuleCount": sum(name.startswith("mesh_plus") for name in loaded),
        "installedModuleBytesExact": True,
        "wheelSha256": wheel_sha,
    }


def selector_is_closed(selector):
    try:
        return selector.get_map() is None
    except ValueError:
        return True


def write_close_receipt(value):
    if RECEIPT.exists() or RECEIPT.is_symlink():
        raise RuntimeError("close_receipt_already_exists")
    temporary = ROOT / f".working-set-fixed-ssh-close-receipt-v8.{os.getpid()}.tmp"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW
    descriptor = os.open(temporary, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        with os.fdopen(descriptor, "wb", closefd=True) as stream:
            descriptor = -1
            stream.write((json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode())
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, RECEIPT)
        directory = os.open(ROOT, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        node = RECEIPT.stat(follow_symlinks=False)
        if node.st_uid != os.getuid() or node.st_mode & 0o777 != 0o600:
            raise RuntimeError("close_receipt_policy")
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass


def marker(event, **fields):
    payload = {"schema": "agent-observer.working-set-stdio-fixture.v8", "event": event, **fields}
    line = b"AO_WORKING_SET_FIXTURE " + json.dumps(payload, sort_keys=True, separators=(",", ":")).encode() + b"\n"
    os.write(2, line)


def main():
    gc.disable()
    gc_disabled_before_project_imports = not gc.isenabled()
    if RECEIPT.exists() or RECEIPT.is_symlink():
        raise SystemExit(2)
    old_handlers = {}
    caught_signal = None
    signal_names = (signal.SIGTERM, signal.SIGHUP)

    native = None
    config_dir = None
    config_path = None
    state = None
    sample = None
    expected = {}
    module_check = {"installedModuleBytesExact": False, "observerModuleCount": 0, "meshModuleCount": 0}
    code = 1
    exit_path = "setup_failed"
    reason_code = "fixture_setup_failed"
    ready_emitted = False
    bridge_exit_code = None
    exception_type = None
    exception_code = None
    stderr_capture = CappedTextSink()
    bridge_run_terminal = {"type": None, "code": None, "expectedTransportTerminal": False}
    runtime_path = None
    process_identity = {
        "pid": os.getpid(),
        "uid": os.getuid(),
        "processGroup": os.getpgrp(),
        "sessionId": os.getsid(0),
        "startTicks": None,
        "pythonVersion": ".".join(map(str, sys.version_info[:3])),
        "pythonEntrypoint": os.path.abspath(sys.executable),
        "pythonEntrypointMatchesPrivateVenv": False,
        "resolvedExecutableSha256": None,
    }
    try:
        for selected in signal_names:
            old_handlers[selected] = signal.signal(selected, stop_on_owned_transport_signal)
        os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
        os.environ["PYTHONNOUSERSITE"] = "1"
        sys.dont_write_bytecode = True
        expected_python = PACKAGE_ROOT / "venv-314" / "bin" / "python"
        process_identity["pythonEntrypointMatchesPrivateVenv"] = (
            Path(os.path.abspath(sys.executable)) == expected_python
            and Path(os.path.abspath(sys.prefix)) == PACKAGE_ROOT / "venv-314"
            and tuple(sys.version_info[:3]) == (3, 14, 8)
        )
        process_identity["resolvedExecutableSha256"] = digest_file(Path(sys.executable).resolve())
        process_identity["startTicks"] = process_start_ticks(os.getpid())
        if not process_identity["pythonEntrypointMatchesPrivateVenv"]:
            raise RuntimeError("private_interpreter_mismatch")

        if gc.isenabled() or not gc_disabled_before_project_imports:
            raise RuntimeError("gc_not_disabled_before_project_imports")
        sys.path.insert(0, str(TESTS))
        import mesh_plus.cli as mesh_cli

        # Observe only finite terminal error metadata. Always re-raise into
        # the unchanged CLI; no transport, result or exit behavior is altered.
        original_mesh_run = mesh_cli.run
        async def observe_mesh_run(*args, **kwargs):
            try:
                return await original_mesh_run(*args, **kwargs)
            except BaseException as terminal:
                name, code = safe_exception(terminal)
                bridge_run_terminal.update(
                    type=name, code=code,
                    expectedTransportTerminal=(
                        type(terminal) in {EOFError, BrokenPipeError, ConnectionResetError,
                                           ConnectionAbortedError, OwnedTransportSignal}
                    ),
                )
                raise
        mesh_cli.run = observe_mesh_run
        from agent_observer.mesh_working_set_publisher import make_working_set_publisher
        from test_service_runtime import Running
        from working_set_synthetic_fixture import HOST as FIXTURE_HOST
        from working_set_synthetic_fixture import SOURCE as FIXTURE_SOURCE
        from working_set_synthetic_fixture import WINDOW_MS, build_fixture

        if FIXTURE_HOST != HOST or FIXTURE_SOURCE != SOURCE or WINDOW_MS != 259_200_000:
            raise RuntimeError("fixture_binding_mismatch")
        state, sample, expected = build_fixture()
        native = Running(state=state, collect=False)
        runtime_path = native.path
        with native:
            if native.runtime.collect is not False:
                raise RuntimeError("fixture_collection_not_disabled")
            config_dir = tempfile.TemporaryDirectory(prefix="ao-ws-bridge-config-")
            config_path = Path(config_dir.name) / "sources.toml"
            config = (
                "version = 1\n"
                f'host = "{HOST}"\n\n'
                f"[sources.{SOURCE}]\n"
                'domain = "agent"\n'
                f'socket = "{runtime_path}"\n'
            ).encode()
            fd = os.open(config_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_CLOEXEC, 0o600)
            with os.fdopen(fd, "wb") as stream:
                stream.write(config)
                stream.flush()
                os.fsync(stream.fileno())
            os.chmod(config_path, 0o600)
            if config_path.stat().st_uid != os.getuid() or config_path.stat().st_mode & 0o077:
                raise RuntimeError("fixture_config_permissions")

            module_check = loaded_module_wheel_check()
            if not module_check["installedModuleBytesExact"]:
                raise RuntimeError("installed_module_pin_failure")

            def publisher_factory(host, source, socket_path):
                nonlocal ready_emitted
                if (host, source, Path(socket_path)) != (HOST, SOURCE, runtime_path):
                    raise RuntimeError("fixture_publisher_binding_mismatch")
                publisher = make_working_set_publisher(host, source, socket_path)
                if publisher.state_profile.window_ms != WINDOW_MS:
                    raise RuntimeError("fixture_profile_window_mismatch")
                if not ready_emitted:
                    marker(
                        "READY",
                        host=HOST,
                        source=SOURCE,
                        runtimeCollect=False,
                        gcDisabledBeforeProjectImports=gc_disabled_before_project_imports,
                        runtimeSocketReady=runtime_path.exists(),
                        configMode="0600",
                        windowMs=WINDOW_MS,
                        sourceRows=len(sample["sessions"]),
                        expectedSelectedCount=len(expected),
                        expectedIdentityHashes=sorted(expected),
                        sourceSampleWallMs=sample["collectedAt"],
                        pythonVersion=process_identity["pythonVersion"],
                        pythonEntrypointMatchesPrivateVenv=process_identity["pythonEntrypointMatchesPrivateVenv"],
                        processId=process_identity["pid"],
                        processStartTicks=process_identity["startTicks"],
                        processUid=process_identity["uid"],
                        processExecutableSha256=process_identity["resolvedExecutableSha256"],
                        loadedModuleCounts={
                            "observer": module_check["observerModuleCount"],
                            "mesh": module_check["meshModuleCount"],
                        },
                        loadedModuleBytesExact=module_check["installedModuleBytesExact"],
                        wheelSha256=module_check["wheelSha256"],
                    )
                    ready_emitted = True
                return publisher

            sys.argv = [
                "mesh-plus",
                "bridge",
                "--source",
                SOURCE,
                "--config",
                str(config_path),
                "--stdio",
            ]
            try:
                with contextlib.redirect_stderr(stderr_capture):
                    code = int(mesh_cli.main(publisher_factories={"agent": publisher_factory}) or 0)
            finally:
                mesh_cli.run = original_mesh_run
            bridge_exit_code = code
        exit_path = "bridge_returned"
        reason_code = "bridge_returned_zero" if code == 0 else "bridge_returned_nonzero"
    except OwnedTransportSignal as stopped:
        caught_signal = signal.Signals(stopped.signum).name
        code = 1
        bridge_exit_code = 1
        exception_type = "owned_transport_signal"
        exit_path = "owned_transport_signal_unwind"
        reason_code = "owned_transport_signal"
    except EOFError as error:
        code = 1
        bridge_exit_code = 1
        exception_type, exception_code = safe_exception(error)
        exit_path = "owned_transport_eof_unwind"
        reason_code = "owned_transport_eof"
    except BaseException as error:
        code = 1
        bridge_exit_code = 1
        exception_type, exception_code = safe_exception(error)
        exit_path = "fixture_exception"
        reason_code = "fixture_setup_or_bridge_failed"
    finally:
        for selected in old_handlers:
            signal.signal(selected, signal.SIG_IGN)
        if config_dir is not None:
            config_dir.cleanup()
        if native is not None and native.thread.ident is None:
            native.runtime.selector.close()
            native.directory.cleanup()

    final_module_check = {"installedModuleBytesExact": False, "observerModuleCount": 0, "meshModuleCount": 0, "wheelSha256": {}}
    try:
        final_module_check = loaded_module_wheel_check()
    except BaseException:
        final_module_check = {"installedModuleBytesExact": False, "observerModuleCount": 0, "meshModuleCount": 0, "wheelSha256": {}}
    module_bytes_exact = (
        module_check.get("installedModuleBytesExact") is True
        and final_module_check.get("installedModuleBytesExact") is True
        and module_check.get("wheelSha256") == final_module_check.get("wheelSha256")
    )
    thread_stopped = native is None or not native.thread.is_alive()
    peer_count = 0 if native is None else len(native.runtime.peers)
    worker_count = 0 if native is None else len(native.runtime.workers)
    worker_starts = 0 if native is None else native.runtime.counts.get("workerStarts", 0)
    selector_closed = False if native is None else selector_is_closed(native.runtime.selector)
    socket_absent = runtime_path is None or not runtime_path.exists()
    config_absent = config_dir is None or not Path(config_dir.name).exists()
    source_cleanup = (
        native is not None
        and native.runtime.collect is False
        and worker_starts == 0
        and worker_count == 0
    )
    cleanup_complete = bool(thread_stopped and peer_count == 0 and selector_closed and socket_absent and config_absent and source_cleanup and module_bytes_exact)
    bridge_status = "passed" if bridge_exit_code == 0 else "failed"
    stderr_text = stderr_capture.getvalue()
    stderr_tokens = known_mesh_stderr_tokens(stderr_text)
    receipt = {
        "schema": "agent-observer.working-set-fixed-ssh-close-receipt.v8",
        "status": "cleanup_complete" if cleanup_complete else "cleanup_incomplete",
        "bridgeStatus": bridge_status,
        "bridgeExitCode": bridge_exit_code,
        "bridgeRunTerminal": bridge_run_terminal.copy(),
        "exitPath": exit_path,
        "reasonCode": reason_code,
        "exceptionType": exception_type,
        "exceptionCode": exception_code,
        "meshStderrErrorTokens": stderr_tokens,
        "meshStderrLineCount": len(stderr_text.splitlines()),
        "meshStderrTruncated": stderr_capture.truncated,
        "caughtSignal": caught_signal,
        "readyEmitted": ready_emitted,
        "windowMs": WINDOW_MS,
        "runtimeCollectFalse": native is not None and native.runtime.collect is False,
        "gcDisabledBeforeProjectImports": gc_disabled_before_project_imports,
        "runtimeThreadStopped": thread_stopped,
        "runtimePeerCount": peer_count,
        "runtimeWorkerCount": worker_count,
        "runtimeWorkerStarts": worker_starts,
        "runtimeSelectorClosed": selector_closed,
        "runtimeSocketAbsent": socket_absent,
        "privateConfigAbsent": config_absent,
        "sourceCleanupComplete": source_cleanup,
        "process": process_identity,
        "loadedModulesInitial": module_check,
        "loadedModulesFinal": final_module_check,
        "loadedModules": final_module_check,
        "moduleBytesExactAtInitialAndFinalChecks": module_bytes_exact,
        "expectedSelectedCount": len(expected),
        "sourceRowCount": 0 if sample is None else len(sample["sessions"]),
        "runtimeSocketPath": None if runtime_path is None else str(runtime_path),
        "privateConfigPath": None if config_path is None else str(config_path),
        "exitCode": code,
    }
    try:
        write_close_receipt(receipt)
    except BaseException:
        reason_code = "close_receipt_write_failed"
        receipt["status"] = "incomplete"
        receipt["reasonCode"] = reason_code
    marker(
        "CLOSED",
        status=receipt["status"],
        bridgeStatus=receipt["bridgeStatus"],
        bridgeExitCode=receipt["bridgeExitCode"],
        reasonCode=receipt["reasonCode"],
        exitPath=receipt["exitPath"],
        exceptionType=receipt["exceptionType"],
        exceptionCode=receipt["exceptionCode"],
        meshStderrErrorTokens=receipt["meshStderrErrorTokens"],
        loadedModulesInitial=receipt["loadedModulesInitial"],
        loadedModulesFinal=receipt["loadedModulesFinal"],
        caughtSignal=receipt["caughtSignal"],
        gcDisabledBeforeProjectImports=receipt["gcDisabledBeforeProjectImports"],
        runtimeThreadStopped=receipt["runtimeThreadStopped"],
        runtimePeerCount=receipt["runtimePeerCount"],
        runtimeSelectorClosed=receipt["runtimeSelectorClosed"],
        runtimeSocketAbsent=receipt["runtimeSocketAbsent"],
        privateConfigAbsent=receipt["privateConfigAbsent"],
        sourceCleanupComplete=receipt["sourceCleanupComplete"],
    )
    return 0 if receipt["status"] == "cleanup_complete" and receipt["bridgeStatus"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
