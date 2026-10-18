"""Bounded facade-policy gap probe; no SDK registration, guard injection or IO."""
import copy
import gc
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
OBS = ROOT / "observer-c6a238f"
MESH = ROOT / "mesh-bea0289" / "src"
sys.path[:0] = [str(OBS / "tests"), str(OBS), str(MESH)]
gc.disable()
import test_mesh_working_set_profile as pf
import test_mesh_working_set_read as rf
from agent_observer.mesh_working_set_read import _WorkingSetSelection
from agent_observer.working_set_contract import validate_frame

base = pf.MeshWorkingSetProfileTest.frame(runtime="parked")
high = copy.deepcopy(base)
high["clockCeiling"] += 4000
high["projection"]["scopes"][0]["members"][0]["recent"]["lowerBoottimeMs"] -= 4000
low = copy.deepcopy(base)
low["sequence"] += 1
low["viewRevision"] += 1
validate_frame(high)
validate_frame(low)
hi, lo = rf.context(high), rf.context(low)
now = high["projection"]["scopes"][0]["members"][0]["recent"]["lowerBoottimeMs"] + rf.OFFSET + 1

control = _WorkingSetSelection(10000)
control.retain(copy.deepcopy(hi))
try:
    control.retain(copy.deepcopy(lo))
except ValueError as exc:
    control_outcome = str(exc)
else:
    control_outcome = "accepted"

policy = _WorkingSetSelection(10000)
policy.retain(copy.deepcopy(hi))
before = policy.evaluate(hi, now)
prior_clock = copy.deepcopy(policy.clocks)
policy.retain(None)  # Exact branch called when public guard snapshot is None on gap.
after_gap_clock = copy.deepcopy(policy.clocks)
policy.retain(copy.deepcopy(lo))
after = policy.evaluate(lo, now)

time_policy = _WorkingSetSelection(10000)
time_policy.retain(copy.deepcopy(hi))
time_policy.evaluate(hi, now)
time_policy.retain(None)
time_policy.retain(copy.deepcopy(hi))
try:
    time_policy.evaluate(hi, now - 1)
except ValueError as exc:
    time_outcome = str(exc)
else:
    time_outcome = "accepted earlier now after gap"

loaded = {}
for name, module in tuple(sys.modules.items()):
    filename = getattr(module, "__file__", None)
    if filename is None:
        continue
    path = pathlib.Path(filename).resolve()
    for label, folder in (("observer", OBS), ("mesh", MESH)):
        if path.suffix == ".py" and path.is_relative_to(folder):
            loaded[name] = {"repo": label, "path": str(path.relative_to(folder)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            break
result = {
    "scope": "Isolated Observer policy helper using individually strict-native-admitted synthetic frames and direct translated headers; no actual SDK guard/Reader admission, proof, transport or runtime",
    "gcDisabled": not gc.isenabled(),
    "sameNativeClockIncarnation": all(high[k] == low[k] for k in ("serviceId", "bootId", "clockDomain")),
    "activityTimestampUnchanged": high["projection"]["sessions"][0]["activity"]["at"] == low["projection"]["sessions"][0]["activity"]["at"],
    "controlWithoutGap": control_outcome,
    "highCeiling": high["clockCeiling"], "lowCeiling": low["clockCeiling"],
    "priorClockWatermarks": len(prior_clock), "afterGapClockWatermarks": len(after_gap_clock),
    "beforeGapExpiredMembers": len(before.members),
    "afterGapRegressedCeilingMembers": len(after.members),
    "beforeGapCoverage": before.scopes[0]["coverage"]["status"],
    "afterGapCoverage": after.scopes[0]["coverage"]["status"],
    "sameReaderTimeNow": now,
    "readerTimeAfterGap": time_outcome,
    "loadedProjectModules": loaded,
}
print(json.dumps(result, indent=2, sort_keys=True))
