"""Serial fresh-process ABBA comparisons; preserve all trials and failures."""

import argparse
import json
import statistics
import subprocess
from pathlib import Path


def run(args):
    trials, summaries = [], []
    # Normal device cadence is ~3 reads/replacement. Bound the enlarged case;
    # broad generic topology/transport qualification already belongs to Mesh.
    cells = [(1, 0, 3, "native"), (1, 8, 1, "native"), (1, 8, 4, "native"),
             (1, 8, 16, "native"), (1, 500, 1, "native"), (1, 500, 3, "native"),
             (2, 250, 1, "native"), (2, 250, 3, "native"), (2, 250, 4, "native"),
             (2, 250, 16, "native"), (2, 250, 3, "envelope"), (1, 1000, 3, "native")]
    args.output.mkdir(parents=True, exist_ok=True)
    for hosts, rows, reads, change in cells:
        block_results = []
        for block, ordering in enumerate((("legacy", "prepared", "prepared", "legacy"),
                                          ("prepared", "legacy", "legacy", "prepared"))):
            paired = {"legacy": [], "prepared": []}
            for position, mode in enumerate(ordering):
                command = [str(args.python), "-I", "-B", str(Path(__file__).with_name("measure.py")),
                           "--mode", mode, "--hosts", str(hosts), "--rows", str(rows),
                           "--reads", str(reads), "--change", change]
                completed = subprocess.run(command, capture_output=True, text=True, timeout=120)
                if completed.returncode:
                    (args.output / "failure.json").write_text(json.dumps({"command": command,
                        "returncode": completed.returncode, "stderr": completed.stderr}, indent=2) + "\n")
                    raise RuntimeError("measurement_failed")
                result = json.loads(completed.stdout)
                result.update(block=block, position=position)
                paired[mode].append(result)
                trials.append(result)
                (args.output / "timing-cases.json").write_text(json.dumps(trials, indent=2) + "\n")
            if len({r["expectedActiveOracleSha256"] for values in paired.values() for r in values}) != 1:
                raise ValueError("cross_process_oracle")
            totals = {mode: {key: statistics.mean(r[key] for r in values)
                             for key in ("cpuNs", "readCpuNs", "admissionCpuNs")}
                      for mode, values in paired.items()}
            block_results.append({"block": block, "totals": totals,
                                  "cpuReductionPercent": 100 * (1 - totals["prepared"]["cpuNs"] / totals["legacy"]["cpuNs"]),
                                  "readReductionPercent": 100 * (1 - totals["prepared"]["readCpuNs"] / totals["legacy"]["readCpuNs"])})
        summary = {"hosts": hosts, "rowsPerHost": rows, "reads": reads, "change": change,
                   "blocks": block_results,
                   "medianCpuReductionPercent": statistics.median(b["cpuReductionPercent"] for b in block_results),
                   "medianReadReductionPercent": statistics.median(b["readReductionPercent"] for b in block_results)}
        summaries.append(summary)
        (args.output / "timing-summary.json").write_text(json.dumps(summaries, indent=2) + "\n")
        print(json.dumps({k: v for k, v in summary.items() if k != "blocks"}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
