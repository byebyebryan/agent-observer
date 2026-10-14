"""Compare the installed rollback tuple with the complete prepared tuple."""

import argparse
import json
import statistics
import subprocess
import tempfile
from pathlib import Path


def run(args):
    source = Path(__file__).parent
    measure = (source / "measure.py").read_text()
    # Keep the decision harness frozen. Older packages lack the optional module;
    # only import/diagnostic compatibility belongs in this separate driver.
    measure = measure.replace(
        "from agent_observer.mesh_read import PreparedAgentWatch  # noqa: E402\n", "")
    measure = measure.replace("    def constructor():\n",
        '    def constructor():\n        if args.mode == "prepared":\n'
        "            from agent_observer.mesh_read import PreparedAgentWatch\n")
    measure = measure.replace('"mesh_read.py")},',
                              '"mesh_read.py") if (OWNER / name).exists()},')
    workload = (source / "workload.py").read_text().replace(
        "ROOT = Path(__file__).resolve().parents[2]",
        f"ROOT = Path({json.dumps(str(source.resolve().parents[1]))})")
    trials = []
    with tempfile.TemporaryDirectory(prefix="agent-deployed-comparison-") as directory:
        root = Path(directory)
        (root / "measure.py").write_text(measure)
        (root / "workload.py").write_text(workload)
        for block, order in enumerate((("legacy", "prepared", "prepared", "legacy"),
                                        ("prepared", "legacy", "legacy", "prepared"))):
            for position, mode in enumerate(order):
                python = args.legacy_python if mode == "legacy" else args.prepared_python
                result = subprocess.run([str(python), "-I", "-B", str(root / "measure.py"),
                    "--mode", mode, "--hosts", "2", "--rows", "250", "--reads", "3",
                    "--change", "native"], capture_output=True, text=True, timeout=120)
                if result.returncode:
                    raise RuntimeError(f"measurement_failed: {result.stderr}")
                trial = json.loads(result.stdout)
                trial.update(block=block, position=position)
                trials.append(trial)
                args.output.write_text(json.dumps({"trials": trials}, indent=2) + "\n")
    for field in ("expectedActiveOracleSha256", "harnessSha256", "workloadSha256"):
        if len({trial[field] for trial in trials}) != 1:
            raise ValueError(f"cross_process_{field}")
    blocks = []
    for block in (0, 1):
        totals = {mode: {key: statistics.mean(t[key] for t in trials
                    if t["block"] == block and t["mode"] == mode)
                    for key in ("cpuNs", "readCpuNs", "admissionCpuNs")}
                  for mode in ("legacy", "prepared")}
        blocks.append({"block": block, "totals": totals,
            "cpuReductionPercent": 100 * (1 - totals["prepared"]["cpuNs"] / totals["legacy"]["cpuNs"]),
            "readReductionPercent": 100 * (1 - totals["prepared"]["readCpuNs"] / totals["legacy"]["readCpuNs"])})
    report = {"scope": "complete deployed tuple comparison; not preparation-only attribution",
              "trials": trials, "blocks": blocks,
              "medianCpuReductionPercent": statistics.median(b["cpuReductionPercent"] for b in blocks),
              "medianReadReductionPercent": statistics.median(b["readReductionPercent"] for b in blocks)}
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in ("trials", "blocks")}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--legacy-python", type=Path, required=True)
    parser.add_argument("--prepared-python", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    run(parser.parse_args())
