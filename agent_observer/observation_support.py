"""Transient provenance for cached projections, separate from frozen row bytes."""

from __future__ import annotations

from collections.abc import Mapping

SUPPORT_FIELDS = ("runtime", "phase", "kind", "savedIdentity", "activity", "outcome",
                  "workspace", "lastUpdated", "latestTurn")
_SUPPORT_KEYS = frozenset({"serviceId", "provider", "namespace", "contextGeneration",
                           "component", "accepted", "sampledBoottimeMs", "expiresBoottimeMs"})


def empty_support():
    return dict.fromkeys(SUPPORT_FIELDS)


def fact_support(service_id, source, component, receipt):
    """Name one accepted sample; retaining this token never renews that sample."""
    if (service_id is None or receipt.accepted < 1
            or receipt.sampledBoottimeMs is None or receipt.expiresBoottimeMs is None):
        return None
    return {
        "serviceId": service_id, "provider": source["provider"],
        "namespace": source["namespace"], "contextGeneration": source["contextGeneration"],
        "component": component, "accepted": receipt.accepted,
        "sampledBoottimeMs": receipt.sampledBoottimeMs,
        "expiresBoottimeMs": receipt.expiresBoottimeMs,
    }


def support_matches(support, source, *, service_id, now_ms=None):
    """Require the exact current receipt, never a newer sample under its key."""
    if (not isinstance(support, Mapping) or set(support) != _SUPPORT_KEYS
            or not isinstance(source, Mapping) or not isinstance(service_id, str)
            or now_ms is not None and (type(now_ms) is not int or now_ms < 0)):
        return False
    if (not all(isinstance(support[name], str) and support[name]
                for name in ("serviceId", "provider", "namespace", "component"))
            or support["component"] not in {"runtime", "history"}
            or any(type(support[name]) is not int for name in
                   ("contextGeneration", "accepted", "sampledBoottimeMs", "expiresBoottimeMs"))
            or support["contextGeneration"] < 0 or support["accepted"] < 1
            or not 0 <= support["sampledBoottimeMs"] < support["expiresBoottimeMs"]):
        return False
    if (support["serviceId"] != service_id or type(source.get("contextGeneration")) is not int
            or any(support[name] != source.get(name)
                   for name in ("provider", "namespace", "contextGeneration"))):
        return False
    components = source.get("components")
    if not isinstance(components, (list, tuple)):
        return False
    matching = [r for r in components if isinstance(r, Mapping)
                and r.get("name") == support["component"]]
    receipt = matching[0] if len(matching) == 1 else None
    return (receipt is not None and receipt.get("health") in ("current", "partial")
            and all(type(receipt.get(name)) is int and support[name] == receipt[name] for name in
                    ("accepted", "sampledBoottimeMs", "expiresBoottimeMs"))
            and (now_ms is None or support["sampledBoottimeMs"] <= now_ms
                 < support["expiresBoottimeMs"]))
