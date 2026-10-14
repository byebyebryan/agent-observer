"""Complete Agent consumer cost; fresh-process CPU and separate allocation."""

import argparse
import asyncio
import gc
import hashlib
import json
import resource
import sys
import time
import tracemalloc
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from mesh_plus.api import ReadGuard, reconstructed, validate_response  # noqa: E402
from mesh_plus.transport import boottime_ms  # noqa: E402
from workload import REQUEST, publications, seed, selected  # noqa: E402

import agent_observer  # noqa: E402
from agent_observer.mesh_profile import AgentProfile  # noqa: E402
from agent_observer.mesh_read import PreparedAgentWatch  # noqa: E402

OWNER = Path(agent_observer.__file__).parent


async def measure(args):
    original = await seed(args.hosts, args.rows)
    frames = publications(original, args.publications, args.change)
    expected = [selected(frame["sessions"]) for frame in frames]
    profile = AgentProfile()
    clock = original["mesh"]["reader"]["clock"]
    validate_response(frames[-1], profile=profile)

    def constructor():
        return (ReadGuard("agent", REQUEST, profile=profile) if args.mode == "legacy"
                else PreparedAgentWatch(REQUEST, profile=profile))

    def query(guard, *, fixed=False):
        now = original["mesh"]["reader"]["encodedAtMs"] if fixed else boottime_ms()
        if args.mode == "legacy":
            rows = guard.current(now, clock)
            context = guard.view["mesh"]
            # The accepted first consumer reconstructs all saved rows each tick.
            # Include that cost, as well as caller-owned current results.
            snapshots = [reconstructed(guard.view, host, profile=profile)["snapshot"]
                         for host in context["hosts"] if host["owner"] is not None]
        else:
            read = guard.read(now, clock)
            rows, context = read.sessions, read.context
            snapshots = [{**h["owner"]["metadata"], "sessions": [r for r in rows
                          if r["identity"]["hostScope"] == h["hostId"]]}
                         for h in context["hosts"] if h["owner"] is not None]
        # Exercise both source context and active selection, without serial/UI.
        if len(snapshots) != args.hosts:
            raise ValueError("context_oracle")
        if len(rows) != args.hosts * args.rows:
            raise ValueError("full_inventory_or_original_lease_expired")
        return selected(rows)

    def lifetime(*, fixed=False):
        guard = constructor()
        admit_ns, read_ns = 0, 0
        try:
            for frame, expected_rows in zip(frames, expected, strict=True):
                at = time.process_time_ns()
                guard.accept(frame)
                admit_ns += time.process_time_ns() - at
                at = time.process_time_ns()
                for _ in range(args.reads):
                    if query(guard, fixed=fixed) != expected_rows:
                        raise ValueError("active_row_oracle_or_original_lease_expired")
                read_ns += time.process_time_ns() - at
        finally:
            guard.disconnect()
        return admit_ns, read_ns

    # Require full packaged-profile admission for every changed publication.
    # Counting runs before timing; never patch the decision CPU path.
    from mesh_plus.view import profile_validator
    validator = profile_validator("agent", profile.descriptor.profile_id)
    validate = type(validator).validate
    calls = 0

    def counted(instance, *values, **kwargs):
        nonlocal calls
        calls += instance is validator
        return validate(instance, *values, **kwargs)

    with patch.object(type(validator), "validate", counted):
        lifetime(fixed=True)
    if calls != len(frames):
        raise ValueError("full_schema_admission_count")
    report = {"mode": args.mode, "hosts": args.hosts, "rowsPerHost": args.rows,
              "reads": args.reads, "publications": args.publications, "change": args.change,
              "scope": "complete guard/context/active-selection lifetime; synthetic cached frames; no native acquisition/carrier/device",
              "harnessSha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "workloadSha256": hashlib.sha256(Path(__file__).with_name("workload.py").read_bytes()).hexdigest(),
              "python": sys.version, "cleanup": True, "preflightSchemaAdmissions": calls,
              "ownerModule": str(OWNER),
              "ownerRuntimeDigests": {name: hashlib.sha256((OWNER / name).read_bytes()).hexdigest()
                                      for name in ("mesh_profile.py", "mesh_preparation.py", "mesh_read.py")},
              "expectedActiveOracleSha256": hashlib.sha256(json.dumps(expected).encode()).hexdigest()}
    if args.memory:
        gc.collect()
        tracemalloc.start()
        guard = constructor()
        checkpoints = []
        for index, frame in enumerate(frames):
            guard.accept(frame)
            if query(guard, fixed=True) != expected[index]:
                raise ValueError("allocation_oracle")
            if index in {0, len(frames) // 4, len(frames) // 2, len(frames) - 1}:
                gc.collect()
                retained, peak = tracemalloc.get_traced_memory()
                checkpoints.append({"publication": index + 1, "retainedTracedBytes": retained,
                                    "peakTracedBytes": peak})
        guard.disconnect()
        del guard
        gc.collect()
        retained, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()
        report.update(retiredTracedBytes=retained, peakTracedBytes=peak,
                      checkpoints=checkpoints,
                      maxRssKiB=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      memoryScope="guard/context/query only; prebuilt inputs excluded; fixed admission time; not real-time freshness")
    else:
        started = time.process_time_ns()
        admit, read = lifetime()
        report.update(cpuNs=time.process_time_ns() - started, admissionCpuNs=admit, readCpuNs=read)
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("legacy", "prepared"), required=True)
    parser.add_argument("--hosts", type=int, choices=(1, 2), required=True)
    parser.add_argument("--rows", type=int, choices=(0, 8, 250, 500, 1000), required=True)
    parser.add_argument("--reads", type=int, choices=(1, 3, 4, 16), required=True)
    parser.add_argument("--change", choices=("envelope", "native"), required=True)
    parser.add_argument("--publications", type=int, choices=range(2, 1001), default=4)
    parser.add_argument("--memory", action="store_true")
    asyncio.run(measure(parser.parse_args()))
