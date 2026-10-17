"""Synthetic patch graph census and semantic digest; no RSS or CPU claim."""

import argparse
import dataclasses
import gc
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace


def graph_bytes(*roots):
    pending, seen, total = list(roots), set(), 0
    while pending:
        value = pending.pop()
        if id(value) in seen:
            continue
        seen.add(id(value))
        total += sys.getsizeof(value)
        if type(value) is dict:
            pending.extend(value)
            pending.extend(value.values())
        elif type(value) in (tuple, list):
            pending.extend(value)
        elif dataclasses.is_dataclass(value):
            pending.extend(getattr(value, field.name) for field in dataclasses.fields(value))
    return total


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("observer", "mesh", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    observer, mesh = args.observer.resolve(), args.mesh.resolve()
    sys.path[:0] = [str(mesh / "src"), str(observer)]
    gc.disable()
    from agent_observer import mesh_sync_profile as patch_module
    from agent_observer.observation_support import SUPPORT_FIELDS
    from mesh_plus.sync.canonical import canonical
    from mesh_plus.sync.commitment import ABSENT

    _Patch = patch_module._Patch
    marker_for = getattr(patch_module, "_marker", canonical)

    class Meter:
        used = 0

        def charge(self, amount):
            self.used += amount

    outcomes = []
    for rows in (100, 500, 2000):
        budget = Meter()
        empty = SimpleNamespace(get=lambda _key: ABSENT)
        patch = _Patch(SimpleNamespace(budget=budget, index=lambda _name: empty))
        for number in range(rows):
            identity = ["fixture", "codex", "default", "thread", str(number)]
            ref = [identity, ["owner", 1]]
            patch.put("aliases", number + 1, ref)
            patch.put("row_rules", ref, 42)
            patch.put("order", [0, [part.encode().decode() for part in identity]], ref)
            marker = marker_for(ref)
            for field in SUPPORT_FIELDS:
                patch.token(ref, field, f"{number:064x}", marker)
            patch.put("scope_stats", ["codex", "default"], {"records": number + 1})
        result = patch.result(())
        digest = hashlib.sha256()
        for item in result.writes:
            digest.update(canonical(["write", item.index, item.key, item.value]))
        for item in result.removes:
            digest.update(canonical(["remove", item.index, item.key]))
        for item in result.field_tokens:
            digest.update(canonical(["token", item.record_ref, item.field, item.token]))
        live = graph_bytes(patch.values, patch.tokens, result)
        assert budget.used >= live
        outcomes.append(dict(rows=rows, emittedWrites=len(result.writes),
                             emittedTokens=len(result.field_tokens), tokenMarkers=len(patch.tokens),
                             uniqueLiveGraphBytes=live, chargedBytes=budget.used,
                             semanticSha256=digest.hexdigest()))
        patch = result = None
    loaded = {}
    for module in tuple(sys.modules.values()):
        filename = getattr(module, "__file__", None)
        if filename and Path(filename).suffix == ".py" and getattr(module, "__name__", None) != "__main__":
            path = Path(filename).resolve()
            for label, directory in (("mesh", mesh), ("observer", observer)):
                if path.is_relative_to(directory):
                    loaded[label + "/" + str(path.relative_to(directory))] = hashlib.sha256(path.read_bytes()).hexdigest()
                    break
    assert not gc.isenabled()
    report = dict(python=sys.version.split()[0], gcDisabled=True, outcomes=outcomes,
                  loadedInputs=loaded, scope="Unique test-owned builder/result graph only. Traversal/oracle/import/input fixtures excluded; no inclusive physical heap/RSS/CPU or authority claim.")
    with args.output.open("x") as stream:
        json.dump(report, stream, indent=2, sort_keys=True)
        stream.write("\n")
    print(json.dumps(outcomes))


if __name__ == "__main__":
    main()
