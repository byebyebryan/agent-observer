"""Serial owner-only a7/compact ABBA diagnostic; no producer acceptance."""

import argparse
import fcntl
import hashlib
import json
import os
import statistics
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--observer", type=Path, required=True)
    parser.add_argument("--legacy-python", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--rows", type=int, choices=(100, 500, 2000), required=True)
    parser.add_argument("--workload", choices=("timestamp", "all-bodies"), required=True)
    parser.add_argument("--lock", type=Path,
                        default=Path("/home/bryan/.cache/agent-active-feed-cpu.lock"))
    args = parser.parse_args()
    observer, python = args.observer.resolve(), args.legacy_python.absolute()
    bench = observer / "tests/bench_sync_producer.py"
    bench_hash = hashlib.sha256(bench.read_bytes()).hexdigest()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    runs = []
    print("Waiting for the shared CPU advisory lock", flush=True)
    with args.lock.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        print("Shared CPU advisory lock acquired", flush=True)
        for label, mode in (("a1", "legacy"), ("b1", "sync"), ("b2", "sync"), ("a2", "legacy")):
            env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
            env.pop("PYTHONPATH", None)
            flags = ["-I", "-B"] if mode == "legacy" else ["-B"]
            if mode == "sync":
                env["PYTHONPATH"] = str(observer)
            argv = [str(python), *flags, str(bench), "--rows", str(args.rows), "--mode", mode,
                    "--workload", args.workload, "--sync-serialization", "compact"]
            result = subprocess.run(argv, env=env, cwd=observer, capture_output=True, text=True)
            (args.output_dir / (label + ".stdout")).write_text(result.stdout)
            (args.output_dir / (label + ".stderr")).write_text(result.stderr)
            result.check_returncode()
            value = json.loads(result.stdout)
            assert value["cyclicGcEnabled"]
            for filename, digest in value["sourceHashesStart"].items():
                assert value["sourceHashes"][filename] == digest
            for filename, digest in value["sourceHashes"].items():
                assert hashlib.sha256(Path(filename).read_bytes()).hexdigest() == digest
            assert value["version"] == "0.7.0a7"
            assert hashlib.sha256(bench.read_bytes()).hexdigest() == bench_hash
            runs.append({"label": label, "argv": argv, "result": value})
            print(label, value["medianCpuNs"] / 1e6, "ms", flush=True)
    assert all(run["result"]["signatures"] == runs[0]["result"]["signatures"] for run in runs)
    assert runs[1]["result"]["sourceHashes"] == runs[2]["result"]["sourceHashes"]
    old = [v for run in (runs[0], runs[3]) for v in run["result"]["cpuNs"]]
    new = [v for run in (runs[1], runs[2]) for v in run["result"]["cpuNs"]]
    components = {name: sum(sum(run["result"][name]) for run in (runs[1], runs[2]))
                  for name in ("commonCpuNs", "syncCpuNs", "oracleCpuNs")}
    assert sum(components.values()) == sum(new)
    summary = {
        "scope": "synthetic owner generation plus semantic oracle only; not installed candidate or end-to-end acceptance",
        "rows": args.rows, "workload": args.workload, "serialization": "compact",
        "generationsPerRun": 6, "sharedLock": str(args.lock), "cyclicGcEnabled": True,
        "benchmarkSha256": bench_hash, "allSignaturesEqual": True,
        "oldMedianTotalCpuNs": statistics.median(old), "newMedianTotalCpuNs": statistics.median(new),
        "medianIncreasePercent": 100 * (statistics.median(new) / statistics.median(old) - 1),
        "oldTotalCpuNs": sum(old), "newComponentsTotalCpuNs": components, "newTotalCpuNs": sum(new),
        "sumIncreasePercent": 100 * (sum(new) / sum(old) - 1),
        "hard25PercentSourceScreen": (sum(new) <= 1.25 * sum(old) and
                                     statistics.median(new) <= 1.25 * statistics.median(old)),
        "runs": runs,
        "exclusions": "Cold setup reported separately; no delivered baseline/recovery, publisher, Reader/facade, IPC/SSH, aggregate32/64MiB/RSS, fully dense nine-field fixture or installed candidate acceptance.",
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    print(json.dumps({key: summary[key] for key in (
        "rows", "workload", "medianIncreasePercent", "sumIncreasePercent", "hard25PercentSourceScreen"
    )}), flush=True)


if __name__ == "__main__":
    main()
