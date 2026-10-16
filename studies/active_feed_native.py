#!/usr/bin/env python3
"""Read-only native parity and an owned installed active service/IPC path.

The independent reference script uses only stdlib native RPC. Native bodies and
CLI snapshots stay in memory; the report contains bounded identity/state facts.
No daemon is started, no provider action is permitted, and normal services and
selected launchers are never changed.
"""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import os
import runpy
import subprocess
import tempfile
import time
from pathlib import Path


def require(value, reason):
    if not value:
        raise AssertionError(reason)


def selected(row):
    return (row["identity"]["provider"] == "codex" and row["kind"] in {"unknown", "user"}
            and row["runtime"]["value"] == "running" and row["runtime"]["health"] == "current")


def signature(rows):
    # Hash complete detached bodies in memory. No title, cwd or native body is
    # written to the report; omissions must not weaken the equality assertion.
    facts = list(rows)
    facts.sort(key=lambda row: json.dumps(row["identity"], sort_keys=True))
    return hashlib.sha256(json.dumps(facts, sort_keys=True).encode()).hexdigest()


def protected():
    units = ("agent-observer.service", "mesh-plus-agent.service", "rlcd-agent-dashboard.service",
             "mesh-plus-tmux.service")
    return {"units": {unit: subprocess.check_output([
        "systemctl", "--user", "show", unit, "-p", "ActiveState", "-p", "MainPID",
        "-p", "NRestarts", "-p", "ExecMainStartTimestampMonotonic",
    ], text=True).splitlines() for unit in units}, "links": {
        name: os.path.realpath(Path.home() / ".local/bin" / name)
        for name in ("agent-observer", "mesh-plus")
    }}


def comparison(reference, client, cli, host, *, socket=None, native_before=None):
    before = reference["codex_reference"](client) if native_before is None else native_before
    args = (["service", "snapshot", "--socket", str(socket), "--host-scope", host]
            if socket else ["snapshot", "--provider", "codex", "--host-scope", host])
    frame = json.loads(reference["cli_call"](cli, args))
    snapshot = frame["snapshot"] if socket else frame
    require(snapshot is not None, "native_service_warming")
    after = reference["codex_reference"](client)
    context = snapshot["sources"][0]["runtime"]
    control = Path.home() / ".codex/app-server-control/app-server-control.sock"
    endpoint = str(Path(f"/tmp/codex-daemon-{os.getuid()}")
                   / hashlib.sha256(str(control).encode()).hexdigest())
    require(context is not None and context["topology"] == "native_managed_endpoint"
            and context["pid"] == client.pid and str(context["startTicks"]) == client.start
            and context["binarySha256"] == client.artifact["sha256"]
            and context["version"] == client.artifact["version"]
            and context["bootId"] == Path("/proc/sys/kernel/random/boot_id").read_text().strip()
            and context["endpoint"] == endpoint, "observer_native_incarnation_binding")
    compared = reference["compare"](before, snapshot, after, "codex")
    identity = reference["identity_scope"](snapshot, host, ["codex"])
    require(all(identity[key] for key in ("hostProvenance", "storeScopes", "fullRowReferences")),
            "native_identity_scope")
    issues = [{key: issue[key] for key in ("id", "field", "result") if key in issue}
              for issue in compared["issues"]]
    invalid = [issue for issue in issues if issue["result"] in {
        "mismatch", "missing_cli_row", "cli_only_unproved",
    }]
    if invalid:
        print(json.dumps({"rejectedNativeComparison": invalid, "cached": socket is not None}), flush=True)
        raise AssertionError("native_cli_mismatch")
    return {"cli": str(cli.resolve()), "nativeRuntime": after["runtime"],
            "observerSourceRuntime": context, "independentNativeBinding": True,
            "nativeBeforeSampleAt": before["sampleAt"], "nativeAfterSampleAt": after["sampleAt"],
            "ownerCollectedAt": snapshot["collectedAt"],
            "cachedOwner": None if socket is None else {key: frame[key] for key in (
                "serviceId", "viewRevision", "emittedAt", "emittedBoottimeMs", "sources",
            )},
            "beforeRows": compared["nativeBeforeRows"], "afterRows": compared["nativeAfterRows"],
            "fullRows": compared["cliRows"], "selectedRows": sum(map(selected, snapshot["sessions"])),
            "checks": compared["checks"], "issues": issues, "identityScope": identity,
            "nativeGaps": after["runtimeGaps"], "selectedSignature": signature(
                [row for row in snapshot["sessions"] if selected(row)]),
            "coverage": snapshot["sources"][0]["coverage"]}, frame


async def active_path(socket, host):
    from mesh_plus.api import Bridge, Client, Endpoint, Reader
    from mesh_plus.evidence import clock_domain
    from mesh_plus.transport import IPCServer, boottime_ms, connect_ipc

    from agent_observer.mesh_active_profile import ACTIVE_PROFILE_ID, ActiveAgentProfile
    from agent_observer.mesh_active_read import PreparedActiveAgentWatch
    from agent_observer.mesh_publisher import make_publisher
    from agent_observer.mesh_source import CachedAgentSource

    profile = ActiveAgentProfile()
    publisher = make_publisher(host, "active", str(socket), profile_id=ACTIVE_PROFILE_ID)
    full = CachedAgentSource(host, socket)
    frame = await publisher.native.snapshot()
    ordinary = await full.snapshot()
    # Both operations read one owner generation. Retry if a periodic collection
    # happened between the two cached socket calls.
    for _ in range(5):
        if frame["viewRevision"] == ordinary["viewRevision"]:
            break
        frame = await publisher.native.snapshot()
        ordinary = await full.snapshot()
    require(frame["viewRevision"] == ordinary["viewRevision"], "native_cached_generation_race")
    require(frame["sources"] == ordinary["sources"], "native_cached_receipt_parity")
    expected = [row for row in ordinary["snapshot"]["sessions"] if selected(row)]
    rows = frame["projection"]["sessions"]
    require(signature(rows) == signature(expected), "native_projection_body_parity")
    with tempfile.TemporaryDirectory(prefix="observer-native-mesh-") as directory:
        mesh_socket = Path(directory) / "mesh.sock"
        server = await IPCServer(mesh_socket, Bridge(publisher).serve).start()
        codec = profile.bind(host, "active")

        async def connect():
            return await Client.connect(await connect_ipc(mesh_socket), host=host, source="active",
                                        profile=ACTIVE_PROFILE_ID, codec=codec.validate_bridge)

        reader = Reader("agent", [Endpoint(host, True, None, connect, codec)],
                        local_host=host, profile=profile)
        request = "d" * 32
        facade = PreparedActiveAgentWatch(request, profile=profile)
        stream = reader.watch_admitted(request_id=request)
        try:
            for _ in range(12):
                token = await asyncio.wait_for(anext(stream), 5)
                facade.accept(token)
                result = facade.read(boottime_ms(), clock_domain())
                if result.scopes:
                    break
            require(signature(result.members) == signature(expected), "native_mesh_facade_body_parity")
            summary = {"selectedRows": len(rows), "fullRows": len(ordinary["snapshot"]["sessions"]),
                       "viewRevision": frame["viewRevision"], "sameGenerationFullParity": True,
                       "originalReceiptParity": True, "bodySignature": signature(rows),
                       "coverage": [{key: scope[key] for key in (
                           "provider", "namespace", "contextGeneration", "continuity", "coverage",
                       )} for scope in result.scopes],
                       "wireBytes": {"full": len(json.dumps(ordinary).encode()),
                                     "active": len(json.dumps(frame).encode())}}
        finally:
            facade.disconnect()
            await stream.aclose()
            await server.close()
        require(reader.inspect()["activeConnections"] == 0 and reader.inspect()["cleanupFailures"] == 0,
                "native_reader_cleanup")
        require(publisher.native._active == 0 and full._active == 0, "native_source_cleanup")
        summary["cleanup"] = {"activeConnections": 0, "cleanupFailures": 0, "nativeChannels": 0}
        return summary


def run(args):
    import mesh_plus

    import agent_observer

    require("site-packages" in agent_observer.__file__ and "site-packages" in mesh_plus.__file__,
            "installed_wheels_required")
    reference = runpy.run_path(str(args.reference))
    before_protected = protected()
    client = reference["NativeRPC"](Path.home() / ".codex")  # fails closed; never autostarts
    process = None
    reports = {}
    try:
        reports["baseline"], _ = comparison(reference, client, args.baseline_cli, args.host_scope)
        reports["candidate"], _ = comparison(reference, client, args.candidate_cli, args.host_scope)
        # Bracket the owned service's actual collection, rather than comparing
        # an earlier cached sample to two later observations of changed work.
        service_before = reference["codex_reference"](client)
        with tempfile.TemporaryDirectory(prefix="observer-active-native-") as directory:
            service_socket = Path(directory) / "private/read.sock"
            service_cli = args.candidate_cli.parent / "agent-observer-service"
            process = subprocess.Popen([
                str(service_cli), "serve", "--host-scope", args.host_scope,
                "--socket", str(service_socket), "--provider", "codex", "--codex-home",
                str(Path.home() / ".codex"), "--collection-timeout", "25",
            ], cwd="/tmp", stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, start_new_session=True)
            deadline = time.monotonic() + 55
            while time.monotonic() < deadline:
                require(process.poll() is None, "owned_service_exit")
                if service_socket.exists():
                    try:
                        value = json.loads(reference["cli_call"](args.candidate_cli, [
                            "service", "status", "--socket", str(service_socket),
                            "--host-scope", args.host_scope,
                        ]))
                        if value["snapshot"] is not None and all(
                            receipt["accepted"] > 0 for source in value["sources"]
                            for receipt in source["components"]
                        ):
                            break
                    except (ValueError, OSError):
                        pass
                time.sleep(.1)
            else:
                raise AssertionError("owned_service_not_ready")
            reports["ownedService"], _ = comparison(reference, client, args.candidate_cli,
                                                   args.host_scope, socket=service_socket,
                                                   native_before=service_before)
            reports["activeIPC"] = asyncio.run(active_path(service_socket, args.host_scope))
            process.terminate()
            require(process.wait(timeout=8) == 0, "owned_service_unclean_exit")
            require(not service_socket.exists(), "owned_socket_cleanup")
            process = None
        require(reference["birth"](client.pid)[0] == client.start, "native_incarnation_changed")
        runtime = {name: report["nativeRuntime"] for name, report in reports.items()
                   if "nativeRuntime" in report}
        require(len({(r["pid"], r["startTicks"], r["sha256"]) for r in runtime.values()}) == 1,
                "native_endpoint_parity")
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            process.wait(timeout=8)
        client.close()
    after_protected = protected()
    require(before_protected == after_protected, "normal_roles_changed")
    return {"status": "passed", "hostScope": args.host_scope, "reports": reports,
            "versions": {name: importlib.metadata.version(name) for name in ("agent-observer", "mesh-plus")},
            "modules": {"observer": agent_observer.__file__, "mesh": mesh_plus.__file__},
            "protected": {"before": before_protected, "after": after_protected, "equal": True},
            "providerActions": 0, "normalServiceChanges": 0, "ownedServiceCleanup": True,
            "limits": ["Fresh ordinary native read-only census; session changes may produce labeled sampling races",
                       "Existing daemon endpoint/incarnation held across baseline, candidate and owned service",
                       "Each Observer source context independently matches oracle PID/birth/hash/boot/endpoint/version",
                       "Native field equality is checked only where independent reference establishes a value; unproved counters retained",
                       "No controlled provider transitions or manufactured populated census",
                       "Owned IPC active path; SSH and synthetic lifecycle/capacity gates reported separately"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--baseline-cli", type=Path, required=True)
    parser.add_argument("--candidate-cli", type=Path, required=True)
    parser.add_argument("--host-scope", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"status": result["status"], "hostScope": args.host_scope,
                      "nativeRows": result["reports"]["candidate"]["afterRows"],
                      "selectedRows": result["reports"]["activeIPC"]["selectedRows"],
                      "protectedEqual": result["protected"]["equal"]}))


if __name__ == "__main__":
    main()
