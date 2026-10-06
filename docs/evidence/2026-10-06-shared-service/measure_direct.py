"""Bounded passive CLI timing; persist aggregate metadata only, never raw rows."""

import json
import resource
import subprocess
import sys
import time
from collections import Counter


PREFIX = "/home/bryan/.local/share/agent-observer/0.3.0a2-98ce1f9203f97c13"


def main():
    host = sys.argv[1]
    if host not in {"snap", "starship"}:
        raise SystemExit("expected snap or starship")
    cases = [("codex",)] if host == "starship" else [
        ("codex",), ("claude",), ("codex", "claude"),
    ]
    results = []
    for providers in cases:
        for index in range(3 if len(providers) == 1 else 2):
            args = [PREFIX + "/bin/agent-observer", "snapshot", "--host-scope", host]
            for provider in providers:
                args.extend(("--provider", provider))
            before = resource.getrusage(resource.RUSAGE_CHILDREN)
            started = time.perf_counter()
            process = subprocess.run(args, capture_output=True, timeout=45, check=True)
            elapsed = time.perf_counter() - started
            after = resource.getrusage(resource.RUSAGE_CHILDREN)
            value = json.loads(process.stdout)
            results.append({
                "providers": list(providers), "sample": index + 1,
                "elapsedSeconds": round(elapsed, 4),
                "childCpuSeconds": round(
                    (after.ru_utime + after.ru_stime) - (before.ru_utime + before.ru_stime), 4,
                ),
                "serializedBytes": len(process.stdout), "rows": len(value["sessions"]),
                "observedRuntimeCounts": dict(Counter(row["runtime"]["value"] for row in value["sessions"])),
                "sources": [{
                    "provider": source["provider"], "sourceHealth": source["sourceHealth"],
                    "coverage": source["coverage"], "errors": source["errors"],
                    "runtimeBinarySha256": source["runtime"]["binarySha256"] if source["runtime"] else None,
                } for source in value["sources"]],
            })
    print(json.dumps({
        "host": host, "candidatePrefix": PREFIX,
        "measurement": "existing direct CLI; separate process each call; OS cache state uncontrolled",
        "passiveReadsOnly": True, "serviceImplemented": False,
        "independentNativeInventoryAudit": False, "samples": results,
    }, indent=2))


if __name__ == "__main__":
    main()
