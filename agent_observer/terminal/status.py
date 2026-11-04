"""Shared conservative session status labels for finite and dashboard views."""

from __future__ import annotations


def qualified_fact_state(fact: object) -> str:
    if type(fact) is not dict:
        return "Unknown"
    health = fact.get("health")
    if health == "stale":
        return "Stale"
    if health == "unavailable":
        return "Unavailable"
    return "Unknown"


def status_text(row: dict) -> str:
    """Return a human label from current runtime and phase facts only."""
    runtime = row.get("runtime")
    if type(runtime) is not dict or runtime.get("health") != "current":
        return qualified_fact_state(runtime)
    if runtime.get("value") == "parked":
        return "Inactive"
    if runtime.get("value") != "running":
        return "Unknown"

    phase = row.get("phase")
    if type(phase) is not dict or phase.get("health") != "current":
        return qualified_fact_state(phase)
    return {
        "working": "Working",
        "waiting": "Ready",
        "blocked": "Blocked",
    }.get(phase.get("value"), "Unknown")
