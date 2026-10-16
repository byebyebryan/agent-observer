"""Fixed Agent compose/admission/selection workload; synthetic data only."""

import argparse
import asyncio
import hashlib
import importlib.metadata
import json
import sys
import time
from pathlib import Path


def summary(row):
    identity = row["identity"]
    return (tuple(identity[k] for k in ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId")),
            row["kind"], row["runtime"]["value"], row["runtime"]["health"])


def selected(value):
    identity, kind, runtime, health = value
    return identity[1] == "codex" and kind in {"user", "unknown"} and runtime == "running" and health == "current"


async def run(args):
    if args.owner_root:
        sys.path.insert(0, str(args.owner_root))
    if args.mesh_root:
        sys.path.insert(0, str(args.mesh_root / "src"))
    root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(root / "studies/prepared"))
    from workload import REQUEST, seed

    from mesh_plus import reader as reader_module, view
    from mesh_plus.api import Endpoint, Reader
    from mesh_plus.evidence import digest
    from mesh_plus.reader import PublicationState

    from agent_observer import contract
    from agent_observer.mesh_profile import AgentProfile
    from agent_observer.mesh_read import PreparedAgentWatch

    original = await seed(2, args.rows // 2)
    profile = AgentProfile()
    endpoints = [Endpoint(h["hostId"], i == 0, None if i == 0 else "sha256:" + "a" * 64,
                          None, profile.bind(h["hostId"], "agent")) for i, h in enumerate(original["mesh"]["hosts"])]
    reader = Reader("agent", endpoints, local_host=endpoints[0].host,
                    catalog_revision="sha256:" + "b" * 64, profile=profile)
    outcomes = {h["hostId"]: (h, [r for r in original["sessions"] if r["identity"]["hostScope"] == h["hostId"]])
                for h in original["mesh"]["hosts"]}
    # Include a running unknown kind and positive kind exclusions in every size.
    for host, rows in outcomes.values():
        rows[0]["kind"] = "unknown"
        rows[1]["kind"] = "child"
        rows[2]["kind"] = "system"
        if host["delivery"]["proof"] is not None:
            host["delivery"]["proof"]["payloadDigest"] = digest(profile.restore_native(host["owner"], rows))

    counts = {"aggregateAdmissions": 0, "snapshotValidations": 0}
    validate = view._validated_response
    native = contract.validate_snapshot
    def admission(*a, **kw):
        counts["aggregateAdmissions"] += 1
        return validate(*a, **kw)
    def snapshot(*a, **kw):
        counts["snapshotValidations"] += 1
        return native(*a, **kw)
    view._validated_response = reader_module._validated_response = admission
    for module in tuple(sys.modules.values()):
        if module is not None and getattr(module, "__name__", "").startswith("agent_observer"):
            for name, value in tuple(vars(module).items()):
                if value is native:
                    setattr(module, name, snapshot)

    selection = None
    if args.mode == "selected":
        from agent_observer.mesh_selection import AgentSelection
        selection = AgentSelection(providers=frozenset({"codex"}), kinds=frozenset({"user", "unknown"}),
                                   runtime_values=frozenset({"running"}), runtime_healths=frozenset({"current"}))
    compose = reader.compose_admitted if args.owned else reader.compose

    def workload():
        guard = PreparedAgentWatch(REQUEST, profile=profile, **({"selection": selection} if selection else {}))
        state, signature, spans = PublicationState(), hashlib.sha256(), {k: 0 for k in ("compose", "accept", "read", "oracle")}
        selected_count, summary_count = 0, 0
        try:
            for generation in range(args.generations):
                for host, rows in outcomes.values():
                    rows[0]["title"] = "synthetic generation " + str(generation)
                    host["owner"]["service"]["sequence"] += 1
                    host["owner"]["service"]["viewRevision"] += 1
                    if host["delivery"]["proof"] is not None:
                        host["delivery"]["proof"]["payloadDigest"] = digest(profile.restore_native(host["owner"], rows))
                start = time.thread_time_ns()
                frame = compose(endpoints, outcomes, REQUEST, "watch", state=state)
                spans["compose"] += time.thread_time_ns() - start
                start = time.thread_time_ns()
                guard.accept(frame)
                spans["accept"] += time.thread_time_ns() - start
                header = frame.context() if args.owned else frame
                clock, now = header["mesh"]["reader"]["clock"], header["mesh"]["reader"]["encodedAtMs"]
                for _ in range(args.reads):
                    start = time.thread_time_ns()
                    result = guard.read(now, clock)
                    if args.mode == "selected":
                        summaries = [(s.identity, s.kind, s.runtime_value, s.runtime_health) for s in result.summaries]
                        rows = result.sessions
                    else:
                        summaries = list(map(summary, result.sessions))
                        rows = [r for r, s in zip(result.sessions, summaries) if selected(s)]
                    spans["read"] += time.thread_time_ns() - start
                    start = time.thread_time_ns()
                    signature.update(json.dumps({"rows": rows, "summaries": summaries}, sort_keys=True).encode())
                    spans["oracle"] += time.thread_time_ns() - start
                    selected_count += len(rows)
                    summary_count += len(summaries)
        finally:
            guard.disconnect()
        assert guard.snapshot() is None and reader.inspect()["activeConnections"] == 0
        return {"semanticSignature": signature.hexdigest(), "selectedRows": selected_count,
                "currentSummaries": summary_count, "threadCpuNs": spans, "cleanup": True}

    workload()  # Exclude fixture construction and one warm-up.
    for key in counts:
        counts[key] = 0
    start = time.process_time_ns()
    result = workload()
    result.update(cpuNs=time.process_time_ns() - start, counts=counts, rows=args.rows,
                  generations=args.generations, readsPerGeneration=args.reads, mode=args.mode,
                  owned=args.owned, python=sys.version,
                  observer=importlib.metadata.version("agent-observer"), mesh=importlib.metadata.version("mesh-plus"),
                  observerModule=sys.modules["agent_observer.mesh_read"].__file__, meshModule=view.__file__,
                  limits=["fixed synthetic compose/admission/preparation/read work; no live service percent",
                          "setup/warm-up excluded; full-body row/summary semantic oracle included",
                          "provider, publisher, SSH, device and RLCD application excluded"])
    args.output.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner-root", type=Path)
    parser.add_argument("--mesh-root", type=Path)
    parser.add_argument("--rows", type=int, choices=(100, 500), default=500)
    parser.add_argument("--mode", choices=("full", "selected"), default="full")
    parser.add_argument("--owned", action="store_true")
    parser.add_argument("--generations", type=int, default=15)
    parser.add_argument("--reads", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    asyncio.run(run(parser.parse_args()))
