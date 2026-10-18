"""Recreate the synthetic input from immutable test fixtures, without providers."""
import argparse
import json
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("candidate_root", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--uid", type=int, default=1000)
    args = parser.parse_args()
    sys.path[:0] = [str(args.candidate_root), str(args.candidate_root / "tests")]
    from test_service_state import provider_snapshot

    from agent_observer.contract import store_namespace

    seed = provider_snapshot("codex")
    seed["host"]["uid"] = args.uid
    namespace = store_namespace("codex", "/fixture/codex", "explicit", args.uid)
    seed["sources"][0]["namespace"] = namespace
    for row in seed["sessions"]:
        row["identity"]["namespace"] = namespace
    args.output.write_text(json.dumps(seed, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
