#!/usr/bin/env python3
"""Serialize installed producer-cost ABBA trials under the shared CPU lock.

Example (run only after both installed artifacts are frozen and Mesh is ready):
  python studies/active_feed_series.py \
    --baseline-python /home/bryan/code/agent-observer/.local/cpu-prepared-20261015/installed/bin/python \
    --candidate-python /home/bryan/code/agent-observer/.local/active-feed-20261016/installed/bin/python \
    --fixture tests/fixtures/service-v4/view.json --output-dir /tmp/active-feed-series

The child reports measured acceptance and cached-read CPU only. Fixture building,
warm-up, semantic hashing and transport are outside those CPU windows. This is
not a whole application, Mesh, native runtime or live-service comparison.
"""

from __future__ import annotations

import argparse
import datetime
import fcntl
import json
import os
import signal
import statistics
import subprocess
import time
from pathlib import Path

LOCK_PATH = Path("/home/bryan/.cache/agent-active-feed-cpu.lock")
ROWS = (100, 500, 2000)
ACTIVE = 10
SIGNATURES = ("selectedSignature", "originalLeasesSignature", "fullMembershipSignature")
CPU_STAGES = ("generation", "cachedFrame", "encoding", "parseSelection",
              "cachedReadTotal", "measuredTotal")


def arguments():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--baseline-python", type=Path, required=True,
                        help="exact installed a6 interpreter; its prefix is checked against child ownerRoot")
    parser.add_argument("--candidate-python", type=Path, required=True,
                        help="exact frozen candidate interpreter; never an editable source checkout")
    parser.add_argument("--fixture", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True, help="new directory; existing paths are rejected")
    parser.add_argument("--benchmark", type=Path, default=Path(__file__).with_name("active_feed_cost.py"))
    parser.add_argument("--generations", type=int, default=6)
    parser.add_argument("--reads", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=600, help="seconds per child, including unmeasured fixture work")
    args = parser.parse_args()
    if not 1 <= args.generations <= 1000 or not 1 <= args.reads <= 100 or args.timeout < 1:
        parser.error("generations must be 1..1000, reads 1..100 and timeout positive")
    # Do not resolve the interpreter symlink: its containing venv is the chosen
    # artifact prefix even when bin/python ultimately points to /usr/bin/python.
    for name in ("baseline_python", "candidate_python", "fixture", "benchmark", "output_dir"):
        setattr(args, name, Path(os.path.abspath(getattr(args, name).expanduser())))
    for name in ("baseline_python", "candidate_python"):
        path = getattr(args, name)
        if not path.is_file() or not os.access(path, os.X_OK):
            parser.error(name.replace("_", "-") + " must name an executable installed interpreter")
    if not args.fixture.is_file() or not args.benchmark.is_file():
        parser.error("fixture and benchmark must be existing files")
    if args.output_dir.exists():
        parser.error("output directory must not exist")
    return args


def stamp():
    return {"utc": datetime.datetime.now(datetime.UTC).isoformat(),
            "monotonicNs": time.monotonic_ns(), "loadAverage": list(os.getloadavg())}


def write_json(path, value):
    pending = path.with_name(path.name + ".tmp")
    pending.write_text(json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    pending.replace(path)


def stop_child(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def one_child(args, output, *, order, rows, comparison, arm, occurrence, python, mode, order_records):
    name = f"{order:02d}-rows{rows}-{comparison}-{arm}{occurrence}"
    stdout_path, stderr_path = output / (name + ".stdout.txt"), output / (name + ".stderr.txt")
    result_path, record_path = output / (name + ".json"), output / (name + ".record.json")
    command = [str(python), "-I", "-B", str(args.benchmark), "--fixture", str(args.fixture),
               "--mode", mode, "--rows", str(rows), "--active", str(ACTIVE),
               "--generations", str(args.generations), "--reads", str(args.reads)]
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("PYTHONHOME", None)
    record = {"order": order, "rows": rows, "comparison": comparison, "arm": arm,
              "occurrence": occurrence, "mode": mode, "python": str(python), "command": command,
              "cwd": "/tmp", "environment": {"PYTHONPATH": None, "PYTHONHOME": None, "isolated": True},
              "stdout": stdout_path.name, "stderr": stderr_path.name, "result": result_path.name,
              "status": "running", "start": stamp()}
    order_records.append(record)
    write_json(record_path, record)
    process = None
    try:
        with stdout_path.open("wb") as stdout, stderr_path.open("wb") as stderr:
            process = subprocess.Popen(command, cwd="/tmp", env=environment, stdout=stdout, stderr=stderr,
                                       start_new_session=True)
            record["pid"] = process.pid
            try:
                record["returncode"] = process.wait(timeout=args.timeout)
            except BaseException:
                # The series lock remains held until the child has been reaped,
                # including timeout and Ctrl-C paths.
                stop_child(process)
                record["returncode"] = process.returncode
                raise
        if record["returncode"] != 0:
            raise ValueError("benchmark_child_failed")
        result = json.loads(stdout_path.read_text(encoding="utf-8"))
        write_json(result_path, result)
        if (result.get("mode") != mode or result.get("rows") != rows or result.get("active") != ACTIVE
                or result.get("generations") != args.generations or result.get("readsPerGeneration") != args.reads
                or result.get("completeReads") != args.generations * args.reads
                or not all(result.get(key) is True for key in
                           ("selectedBodyParity", "originalLeasesPreserved", "fullMembershipDecisionParity"))
                or result.get("limits", {}).get("capacityPassed") is not True
                or any(not isinstance(result.get(key), str) or len(result[key]) != 64 for key in SIGNATURES)):
            raise ValueError("benchmark_child_contract")
        owner_root = Path(result["ownerRoot"]).resolve()
        if not owner_root.is_relative_to(python.parent.parent.resolve()):
            raise ValueError("benchmark_owner_root_not_installed_prefix")
        record.update(status="complete", ownerRoot=str(owner_root), ownerVersion=result.get("ownerVersion"),
                      signatures={key: result[key] for key in SIGNATURES})
        return record, result
    except BaseException as error:
        if process is not None:
            stop_child(process)
        record.update(status="failed", error=type(error).__name__, reason=str(error))
        raise
    finally:
        record["end"] = stamp()
        record["wallNs"] = record["end"]["monotonicNs"] - record["start"]["monotonicNs"]
        write_json(record_path, record)


def median_arm(results, generations, reads):
    cpu = {stage: statistics.median(result["cpuNs"][stage] for result in results) for stage in CPU_STAGES}
    return {"runs": len(results), "cpuNsMedian": cpu,
            "generationCpuNsPerGenerationMedian": cpu["generation"] / generations,
            "cachedReadCpuNsPerReadMedian": cpu["cachedReadTotal"] / (generations * reads),
            "wireBytesMedian": statistics.median(result["bytes"]["cachedReadsTotal"] for result in results),
            "wireBytesPerReadMeanMedian": statistics.median(
                result["bytes"]["cachedReadsTotal"] / (generations * reads) for result in results),
            "wireBytesPerReadMin": min(result["bytes"]["perReadMin"] for result in results),
            "wireBytesPerReadMax": max(result["bytes"]["perReadMax"] for result in results),
            "projectorGenerations": [result["cachedProjectorGenerations"] for result in results]}


def comparison_summary(results, generations, reads):
    baseline, candidate = (median_arm([result for arm, result in results if arm == name], generations, reads)
                           for name in ("A", "B"))
    before, after = baseline["cpuNsMedian"], candidate["cpuNsMedian"]
    return {"baseline": baseline, "candidate": candidate,
            "generationAddedCpuNsMedian": after["generation"] - before["generation"],
            "cachedReadChangeCpuNsMedian": after["cachedReadTotal"] - before["cachedReadTotal"],
            "measuredProducerPathChangeCpuNsMedian": after["measuredTotal"] - before["measuredTotal"],
            "cpuChangePercent": {stage: 100 * (after[stage] - before[stage]) / before[stage]
                                 for stage in ("generation", "cachedReadTotal", "measuredTotal")}}


def series(args):
    requested = stamp()
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Never unlink this file: Mesh and every series must lock the same inode.
    with LOCK_PATH.open("a+") as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        acquired = stamp()
        try:
            args.output_dir.mkdir(parents=True, exist_ok=False)
            report = {
                "status": "running", "kind": "serial controlled installed producer cost; no whole-app/live claim",
                "lock": str(LOCK_PATH), "lockRequested": requested, "lockAcquired": acquired,
                "lockWaitWallNs": acquired["monotonicNs"] - requested["monotonicNs"],
                "start": acquired, "baselinePython": str(args.baseline_python),
                "candidatePython": str(args.candidate_python), "benchmark": str(args.benchmark),
                "fixture": str(args.fixture), "rows": list(ROWS), "active": ACTIVE,
                "generations": args.generations, "readsPerGeneration": args.reads,
                "order": [], "aggregates": {},
                "measurementBounds": {
                    "cpuWindows": ["ServiceState acceptance/generation", "cached status creation",
                                   "frame encoding", "strict parse and selection"],
                    "unmeasuredCpu": ["fixture construction", "warmup", "semantic hashing", "series orchestration"],
                    "notIncluded": ["Mesh", "transport", "RLCD", "native collection", "normal services"],
                    "wallTime": "includes unmeasured work; not a CPU or end-to-end application metric",
                    "memory": "not measured; no profiler or tracemalloc",
                    "changeSign": "positive means candidate cost increased; negative means decreased",
                },
            }
            target = args.output_dir / "series.json"
            write_json(target, report)
            signatures, owners = {}, {}
            try:
                for rows in ROWS:
                    report["aggregates"][str(rows)] = {}
                    for comparison, candidate_mode in (("full-pair", "full"), ("active-pair", "active")):
                        results = []
                        for arm, occurrence in (("A", 1), ("B", 1), ("B", 2), ("A", 2)):
                            python = args.baseline_python if arm == "A" else args.candidate_python
                            mode = "full" if arm == "A" else candidate_mode
                            record, result = one_child(
                                args, args.output_dir, order=len(report["order"]) + 1, rows=rows,
                                comparison=comparison, arm=arm, occurrence=occurrence, python=python, mode=mode,
                                order_records=report["order"])
                            actual = {key: result[key] for key in SIGNATURES}
                            if rows in signatures and signatures[rows] != actual:
                                raise ValueError("semantic_signature_mismatch")
                            signatures[rows] = actual
                            owner = (result["ownerRoot"], result.get("ownerVersion"))
                            if str(python) in owners and owners[str(python)] != owner:
                                raise ValueError("installed_owner_changed_during_series")
                            owners[str(python)] = owner
                            results.append((arm, result))
                            write_json(target, report)
                        report["aggregates"][str(rows)][comparison] = comparison_summary(
                            results, args.generations, args.reads)
                        write_json(target, report)
                    report["aggregates"][str(rows)]["signatures"] = signatures[rows]
                    report["aggregates"][str(rows)]["allThreeSignaturesEqual"] = True
                report.update(status="complete", allThreeSignaturesEqual=True, children=len(report["order"]))
            except BaseException as error:
                report.update(status="failed", error=type(error).__name__, reason=str(error))
                raise
            finally:
                report["end"] = stamp()
                report["wallNs"] = report["end"]["monotonicNs"] - acquired["monotonicNs"]
                write_json(target, report)
            return {"status": report["status"], "series": str(target), "children": len(report["order"]),
                    "allThreeSignaturesEqual": True, "aggregates": report["aggregates"]}
        finally:
            fcntl.flock(lock.fileno(), fcntl.LOCK_UN)


def main():
    args = arguments()
    try:
        result = series(args)
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(json.dumps({"status": "failed", "error": type(error).__name__, "reason": str(error)}))
        return 2
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
