"""Serial ordinary-host ABBA publisher/prepared-CLI windows, cached data only."""

import argparse
import json
import os
import runpy
import signal
import subprocess
import tempfile
import time
from pathlib import Path


def stop(process):
    if process.poll() is None:
        os.killpg(process.pid, signal.SIGINT)
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait(timeout=5)


def run(args):
    helpers = runpy.run_path(str(args.resource_helper))
    counters, tree = helpers["counters"], helpers["tree"]
    results = []
    with tempfile.TemporaryDirectory(prefix="agent-a20-cost-") as directory:
        root = Path(directory)
        config = root / "sources.toml"
        config.write_text(f'version=1\nhost={json.dumps(args.host)}\n[sources.agent]\n'
            f'domain="agent"\nsocket={json.dumps(str(args.service_socket))}\n')
        config.chmod(0o600)
        for position, variant in enumerate(("baseline", "candidate", "candidate", "baseline")):
            publisher_prefix = args.baseline_publisher if variant == "baseline" else args.candidate
            cli = args.baseline_cli if variant == "baseline" else args.candidate / "bin/agent-observer"
            endpoint = root / (str(position) + ".sock")
            publisher = subprocess.Popen([str(publisher_prefix / "bin/mesh-plus"), "serve",
                "--source", "agent", "--config", str(config), "--socket", str(endpoint)],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            reader = None
            try:
                until = time.monotonic() + 10
                while not endpoint.exists():
                    if publisher.poll() is not None or time.monotonic() >= until:
                        raise ValueError("publisher_startup")
                    time.sleep(.05)
                snapshot = json.loads(subprocess.check_output([str(cli), "mesh", "snapshot",
                    "--scope", "local", "--local-host", args.host, "--socket", str(endpoint)], timeout=30))
                if snapshot["mesh"]["status"] != "complete":
                    raise ValueError("snapshot_not_complete")
                reader = subprocess.Popen([str(cli), "mesh", "watch", "--human", "--prepared",
                    "--scope", "local", "--local-host", args.host, "--socket", str(endpoint)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
                roots = {"publisher": (publisher.pid, counters(publisher.pid)["birth"]),
                         "reader": (reader.pid, counters(reader.pid)["birth"])}
                time.sleep(10)
                before = {role: tree(*identity) for role, identity in roots.items()}
                start = time.monotonic()
                samples = []
                while time.monotonic() - start < args.seconds:
                    if publisher.poll() is not None or reader.poll() is not None:
                        raise ValueError("owned_process_ended")
                    samples.append({role: tree(*identity) for role, identity in roots.items()})
                    time.sleep(1)
                after = {role: tree(*identity) for role, identity in roots.items()}
                elapsed = time.monotonic() - start
                final = json.loads(subprocess.check_output([str(cli), "mesh", "snapshot",
                    "--scope", "local", "--local-host", args.host, "--socket", str(endpoint)], timeout=30))
                if final["mesh"]["status"] != "complete":
                    raise ValueError("ending_snapshot_not_complete")
                report = {"variant": variant, "position": position, "seconds": elapsed,
                    "rowsBefore": len(snapshot["sessions"]), "rowsAfter": len(final["sessions"]),
                    "roots": roots, "roles": {role: {
                        "cpuPercentOneCore": 100 * (after[role]["ticks"] - before[role]["ticks"]) /
                            (os.sysconf("SC_CLK_TCK") * elapsed),
                        "peak": {key: max(s[role][key] for s in samples)
                            for key in ("rssBytes", "pssBytes", "fds", "processes")},
                        "pssComplete": after[role]["pssComplete"]} for role in roots}}
                results.append(report)
                args.output.write_text(json.dumps({"host": args.host, "windows": results,
                    "scope": "complete owned local publisher/prepared human CLI; ordinary cached Service 4",
                    "limits": ["ABBA serial; ordinary source/load changes are uncontrolled",
                               "startup excluded; collection and remote/server cost excluded",
                               "frame/render counts not collected; original cadence/leases unchanged",
                               "no source/device/application CPU saving claim"]}, indent=2) + "\n")
                print(json.dumps({"host": args.host, "position": position, "variant": variant,
                    "cpu": {role: value["cpuPercentOneCore"] for role, value in report["roles"].items()}}), flush=True)
            finally:
                if reader is not None:
                    stop(reader)
                stop(publisher)
    print(json.dumps({"status": "passed", "ownedProcessesAfter": 0, "host": args.host}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=("snap", "starship"), required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--baseline-publisher", type=Path, required=True)
    parser.add_argument("--baseline-cli", type=Path, required=True)
    parser.add_argument("--service-socket", type=Path, required=True)
    parser.add_argument("--resource-helper", type=Path, required=True)
    parser.add_argument("--seconds", type=int, choices=range(120, 601), default=120)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
