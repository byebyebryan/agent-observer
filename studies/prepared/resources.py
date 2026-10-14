"""Bounded installed CLI resource windows; no service or provider changes."""

import argparse
import asyncio
import json
import os
import signal
import subprocess
import time
from pathlib import Path

UNITS = ("agent-observer.service", "mesh-plus-agent.service", "rlcd-agent-dashboard.service")


def units():
    result = {}
    for name in UNITS:
        raw = subprocess.check_output(["systemctl", "--user", "show", name, "-p", "MainPID",
            "-p", "NRestarts", "-p", "ActiveState", "-p", "CPUUsageNSec", "-p", "MemoryCurrent"], text=True)
        data = dict(line.split("=", 1) for line in raw.splitlines() if "=" in line)
        result[name] = data
    return result


def tree(pid):
    rows = {}
    pending = [pid]
    while pending:
        current = pending.pop()
        try:
            root = Path(f"/proc/{current}")
            fields = root.joinpath("stat").read_text().rsplit(")", 1)[1].split()
            rows[str(current)] = {"birth": fields[19], "cpuTicks": int(fields[11]) + int(fields[12]),
                                  "rssBytes": int(fields[21]) * os.sysconf("SC_PAGE_SIZE"),
                                  "fds": len(list(root.joinpath("fd").iterdir()))}
            pending.extend(map(int, root.joinpath(f"task/{current}/children").read_text().split()))
        except (OSError, ValueError):
            pass
    return rows


async def main(args):
    windows = []
    cli = str(Path.home() / ".local/bin/agent-observer")
    for label, kinds in (("no_added_reader", ()), ("one_local_prepared", ("local",)),
                         ("one_fleet_prepared", ("fleet",)), ("two_fleet_prepared", ("fleet", "fleet"))):
        processes = []
        samples = []
        try:
            for kind in kinds:
                command = [cli, "mesh", "watch", "--human", "--prepared", "--scope", kind]
                if kind == "local":
                    command.extend(["--local-host", args.host])
                processes.append(await asyncio.create_subprocess_exec(*command, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, start_new_session=True))
            await asyncio.sleep(10)  # startup excluded from steady window
            started, before = time.monotonic(), units()
            while time.monotonic() - started < args.seconds:
                if any(p.returncode is not None for p in processes):
                    raise ValueError("resource_reader_ended")
                samples.append({"atSeconds": round(time.monotonic() - started, 3), "units": units(),
                                "readers": [{"pid": p.pid, "tree": tree(p.pid)} for p in processes]})
                await asyncio.sleep(min(10, max(.01, args.seconds - (time.monotonic() - started))))
            after = units()
            elapsed = time.monotonic() - started
            cpu = {}
            for name, data in before.items():
                end = after[name]
                if (data["MainPID"], data["NRestarts"]) != (end["MainPID"], end["NRestarts"]):
                    raise ValueError("resource_service_incarnation_changed")
                if data["CPUUsageNSec"].isdigit() and end["CPUUsageNSec"].isdigit():
                    cpu[name] = 100 * (int(end["CPUUsageNSec"]) - int(data["CPUUsageNSec"])) / (elapsed * 1e9)
            windows.append({"label": label, "seconds": elapsed, "unitCpuPercentOneCore": cpu,
                            "before": before, "after": after, "samples": samples})
            args.output.write_text(json.dumps({"host": args.host, "windows": windows,
                "limits": ["normal-workload descriptive samples; not causal AB benchmark",
                           "no_added_reader retains existing dashboard/other readers",
                           "owned CLI/descendant snapshots; remote SSH server cost excluded",
                           "startup excluded; original services/provider settings preserved"]}, indent=2) + "\n")
            print(json.dumps({"host": args.host, "label": label, "unitCpuPercentOneCore": cpu}), flush=True)
        finally:
            for process in processes:
                if process.returncode is None:
                    os.killpg(process.pid, signal.SIGINT)
                    try:
                        await asyncio.wait_for(process.wait(), 10)
                    except TimeoutError:
                        os.killpg(process.pid, signal.SIGKILL)
                        await process.wait()
    print(json.dumps({"status": "passed", "host": args.host, "windows": len(windows), "ownedReadersAfter": 0}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", choices=("snap", "starship"), required=True)
    parser.add_argument("--seconds", type=int, choices=range(300, 601), default=300)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(main(parser.parse_args()))
