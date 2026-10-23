"""Pure projected-field expiry; copying never renews source evidence."""

import copy

from . import timing
from .contract import ContractError


def _stale_fact(fact, reason):
    value = copy.deepcopy(fact)
    if value is None:
        return None
    if value["value"] != "unknown":
        value["lastKnownValue"] = value["value"]
    value.update(value="unknown", health="stale", reason=reason)
    return value


def mask_fields(row, supports, current):
    """Detached body with only individually supported fields current.

    ``current`` is an owner-boottime or admitted Mesh-translated predicate.
    It never uses encoding time as native evidence.
    """
    result = copy.deepcopy(row)
    for name in ("runtime", "phase", "outcome"):
        fact = result[name]
        if (not current(supports.get(name)) and fact is not None
                and (fact["value"] != "unknown" or fact["health"] == "current")):
            result[name] = _stale_fact(result[name], "active_support_expired")
    if result["phase"] is None or result["phase"]["value"] != "blocked":
        result["blockedReasons"] = []
    if (not current(supports.get("activity"))
            and result["activity"]["health"] == "current"):
        activity = result["activity"]
        if activity["at"] is not None:
            activity["lastKnownAt"] = activity["at"]
        activity.update(at=None, health="stale", reason="active_support_expired")
    if not current(supports.get("workspace")):
        result["workspace"] = None
    for name in ("lastUpdated", "latestTurn"):
        if not current(supports.get(name)) and result[name]["health"] == "current":
            result[name] = timing.stale(result[name], name, "active_support_expired")
    return result


def _unique_supports(values):
    result = {}
    for value in values:
        if value is not None:
            key = value["provider"], value["namespace"], value["component"]
            previous = result.get(key)
            if previous is not None and previous != value:
                raise ContractError("active_conflicting_support")
            result[key] = copy.deepcopy(value)
    return [result[key] for key in sorted(result)]

