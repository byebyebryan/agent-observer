"""Recompute saved component comparisons and verify imported immutable blobs."""

import argparse
import hashlib
import json
import statistics
import subprocess
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("observer_git", type=Path)
    parser.add_argument("directory", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    base = args.directory
    refs = {"a7": "7807160384ba39b4d438c5c7f1b5f316c3608dcd", "candidate": "c6a238f"}
    blob_hashes = {}
    verified = {}
    for path in sorted([*base.glob("abba-*.json"), *base.glob("disabled-*.json"),
                        *base.glob("read4-*.json"), *base.glob("pilot-*.json")]):
        data = json.loads(path.read_bytes())
        variant = data["variant"]
        ref = refs["a7" if variant.startswith("a7") else "candidate"]
        assert data["gcEnabled"] is False
        loaded = data.get("loaded", data.get("loadedModules"))
        for module in loaded.values():
            key = ref, module["path"]
            if key not in blob_hashes:
                blob = subprocess.check_output([
                    "git", "-C", str(args.observer_git), "show", ref + ":" + module["path"],
                ])
                blob_hashes[key] = hashlib.sha256(blob).hexdigest()
            assert module["sha256"] == blob_hashes[key], (path.name, key)
        verified[path.name] = {"loaded": len(loaded), "commit": ref}
    summary = {"owner": {}, "read4": {}, "verified": verified,
               "scope": "saved synthetic source component only; no native/SDK/RSS/producer acceptance"}
    for version in ("314", "311"):
        for rows in (100, 500, 2000):
            owner = [json.loads(p.read_bytes()) for p in base.glob(f"abba-{rows}-*-{version}.json")]
            disabled = [json.loads(p.read_bytes()) for p in base.glob(f"disabled-{rows}-*-{version}.json")]
            assert len(owner) == 4 and len(disabled) == 2
            assert len({d["fixtureDigest"] for d in owner + disabled}) == 1
            for key in ("fullDigest", "activeDigest", "selectedDigest"):
                assert len({d["checks"][key] for d in owner + disabled}) == 1
            old = statistics.median(d["totalSixGenerationCpuMs"] for d in owner if d["variant"] == "a7")
            new = statistics.median(d["totalSixGenerationCpuMs"] for d in owner if d["variant"] == "candidate")
            off = statistics.median(d["totalSixGenerationCpuMs"] for d in disabled)
            summary["owner"][f"{version}/{rows}"] = {
                "a7TotalMs": old, "currentDisabledTotalMs": off, "currentEnabledTotalMs": new,
                "enabledMinusDisabledMs": new - off, "netUpgradePercent": (new / old - 1) * 100,
                "fixtureWithin25PercentOwnerCeiling": new <= old * 1.25,
            }
            read = [json.loads(p.read_bytes()) for p in base.glob(f"read4-{rows}-*-{version}.json")]
            assert len(read) == 5
            for key in ("sourceInputDigest", "fullDigest", "activeDigest", "selectedDigest"):
                assert len({d[key] for d in read}) == 1
            assert all(d["measuredReads"] == 24 and d["measuredGenerations"] == 6 for d in read)
            a7 = [d for d in read if d["variant"] == "a7-full"]
            working = [d for d in read if d["variant"] == "candidate-working"]
            current_full = next(d for d in read if d["variant"] == "candidate-full")
            for data in working:
                assert data["workingDigest"] == data["selectedDigest"]
                assert data["workingCoverage"] == "complete"
            old_cpu = statistics.median(d["combinedCpuTotalMs"] for d in a7)
            new_cpu = statistics.median(d["combinedCpuTotalMs"] for d in working)
            old_bytes = statistics.median(d["totalSerializedFrameBytes"] for d in a7)
            new_bytes = statistics.median(d["totalSerializedFrameBytes"] for d in working)
            fraction = max(s / f for d in working for s, f in zip(
                d["selectedRowsBytesPerGeneration"], d["fullBodyBytesPerGeneration"], strict=True,
            ))
            summary["read4"][f"{version}/{rows}"] = {
                "a7CombinedMs": old_cpu, "candidateCombinedMs": new_cpu,
                "cpuSavingPercent": (1 - new_cpu / old_cpu) * 100,
                "a7SerializedBytes": old_bytes, "candidateSerializedBytes": new_bytes,
                "serializedByteSavingPercent": (1 - new_bytes / old_bytes) * 100,
                "selectedBodyFraction": fraction,
                "fixtureMeets30PercentCpu50PercentByteTargets": (
                    fraction <= 0.25 and new_cpu <= old_cpu * 0.7 and new_bytes <= old_bytes * 0.5
                ), "singleCurrentFullCombinedMs": current_full["combinedCpuTotalMs"],
            }
    args.output.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
