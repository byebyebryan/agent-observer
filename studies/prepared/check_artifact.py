"""Reject stale/extra package files against an isolated committed source tree."""

import argparse
import hashlib
import json
import zipfile
from pathlib import Path

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--wheel", type=Path, required=True)
    args = parser.parse_args()
    expected = {str(path.relative_to(args.source)): path.read_bytes()
                for path in (args.source / "agent_observer").rglob("*")
                if path.is_file() and path.suffix in {".py", ".json"}}
    with zipfile.ZipFile(args.wheel) as bundle:
        actual = {name: bundle.read(name) for name in bundle.namelist()
                  if name.startswith("agent_observer/") and not name.endswith("/")}
    if actual != expected:
        raise ValueError("wheel_source_inventory_or_bytes_mismatch")
    print(json.dumps({"status": "accepted", "packageFiles": len(actual),
                      "sourceFileDigests": {name: hashlib.sha256(body).hexdigest() for name, body in sorted(expected.items())},
                      "wheelSha256": hashlib.sha256(args.wheel.read_bytes()).hexdigest(),
                      "retiredClaudeFiles": len([name for name in actual if "claude" in name])}, indent=2))
