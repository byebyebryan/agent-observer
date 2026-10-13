"""Bounded native timing semantics; clocks and lease decisions are caller inputs."""

from __future__ import annotations

import copy
import unicodedata

MAX_TIME = 4_000_000_000_000


def unknown(name, reason="timing_source_unproved", health="unsupported", *, observed_at=None):
    result = {"observedAt": observed_at, "source": None, "health": health,
              "reason": reason, "receipt": None}
    result.update({"at": None, "timestampPrecisionMs": None} if name == "lastUpdated" else {"value": None})
    return result


def _seconds(value):
    return value is None or type(value) is int and 0 <= value <= MAX_TIME // 1000


def codex_updated(payload, *, observed_at):
    result = unknown("lastUpdated", "native_update_clock_missing", "current", observed_at=observed_at)
    result["source"] = "codex_thread_metadata"
    at = payload.get("updatedAt")
    if not _seconds(at):
        result.update(health="unavailable", reason="native_update_clock_invalid")
    elif at is not None:
        result.update(at=at * 1000, timestampPrecisionMs=1000, reason="native_thread_update")
    return result


def codex_turn(payload, *, observed_at):
    result = unknown("latestTurn", "native_turn_metadata_invalid", "unavailable", observed_at=observed_at)
    result["source"] = "codex_turn_metadata"
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return result
    turns = payload["data"]
    if not turns:
        result.update(health="current", reason="no_native_turn")
        return result
    if len(turns) != 1 or not isinstance(turns[0], dict):
        return result
    turn = turns[0]
    if turn.get("itemsView") != "notLoaded" or turn.get("items") != []:
        result["reason"] = "native_turn_content_rejected"
        return result
    identifier = turn.get("id")
    start, end, duration = turn.get("startedAt"), turn.get("completedAt"), turn.get("durationMs")
    status = {"inProgress": "in_progress", "completed": "completed", "failed": "failed",
              "interrupted": "cancelled"}.get(turn.get("status")) if isinstance(turn.get("status"), str) else None
    if (identifier is not None and (not isinstance(identifier, str) or not 0 < len(identifier) <= 512
                                   or any(unicodedata.category(c).startswith("C") for c in identifier))
            or not _seconds(start) or not _seconds(end)
            or duration is not None and (type(duration) is not int or not 0 <= duration <= MAX_TIME)
            or start is not None and end is not None and end < start
            or status == "in_progress" and (end is not None or duration is not None)):
        return result
    result.update(health="current", reason="native_latest_turn" if status else "native_turn_status_unknown",
                  value={"id": identifier, "status": status or "unknown",
                         "startedAt": None if start is None else start * 1000,
                         "completedAt": None if end is None else end * 1000,
                         "durationMs": duration,
                         "timestampPrecisionMs": 1000 if start is not None or end is not None else None})
    return result


def stale(record, name, reason):
    result = copy.deepcopy(record)
    key, known = ("at", "lastKnownAt") if name == "lastUpdated" else ("value", "lastKnownValue")
    if result["health"] == "current" and result[key] is not None:
        result[known] = result[key]
        if name == "lastUpdated":
            result["lastKnownTimestampPrecisionMs"] = result["timestampPrecisionMs"]
    result[key] = None
    if name == "lastUpdated":
        result["timestampPrecisionMs"] = None
    # Failed/unsupported input never becomes last-known native metadata.
    if result["health"] == "current" or result["health"] == "stale":
        result.update(health="stale", reason=reason)
    return result


def project(native, name, *, saved, origin=None):
    record = copy.deepcopy(native.get(name, unknown(name)))
    if not saved:
        record = unknown(name, observed_at=record["observedAt"])
    boot = native.get("timingObservedBoottimeMs", {}).get(name)
    if origin is not None and type(boot) is int and boot >= origin["sampledBoottimeMs"]:
        record["receipt"] = {**origin, "observedBoottimeMs": boot, "contextGeneration": 0}
    return record


def select(candidates, name):
    """Choose the latest observation, even failed/empty/expired; never event time."""
    def order(item):
        record, _ = item
        receipt = record["receipt"]
        return (-1, -1) if receipt is None else (receipt["sampledBoottimeMs"], receipt["observedBoottimeMs"])
    newest = max(map(order, candidates))
    tied = [item for item in candidates if order(item) == newest]
    # Ignore attribution only for equality of otherwise identical evidence.
    signatures = [{k: v for k, v in record.items() if k != "receipt"} for record, _ in tied]
    if any(value != signatures[0] for value in signatures[1:]):
        return unknown(name, "timing_observation_conflict", "ambiguous")
    return copy.deepcopy(min(tied, key=lambda item: item[1] if item[1] is not None else -1)[0])


def age_ms(record, at, *, now_boottime_ms=None):
    """Source-wall baseline, optionally advanced within its admitted local clock.

    Callers must first validate/expire the enclosing local service frame. Remote
    carriers require their own accepted clock bridge and cannot supply local
    BOOTTIME here. This helper never grants a lease or compares device wall time.
    """
    if record["health"] != "current" or at is None or record["observedAt"] is None:
        return None
    base = record["observedAt"] - at
    if base < 0:
        return None
    if now_boottime_ms is None:
        return base
    receipt = record["receipt"]
    if receipt is None or type(now_boottime_ms) is not int or now_boottime_ms < receipt["observedBoottimeMs"]:
        return None
    return base + now_boottime_ms - receipt["observedBoottimeMs"]


def ongoing_turn_age_ms(row, *, now_boottime_ms=None):
    """A sampled joined timer, not phase entry or a continuity claim."""
    record, phase = row["latestTurn"], row["phase"]
    turn = record["value"]
    if (row["runtime"]["health"] != "current" or row["runtime"]["value"] != "running"
            or phase is None or phase["health"] != "current" or phase["value"] not in {"working", "blocked"}
            or record["health"] != "current" or turn is None or turn["status"] != "in_progress"
            or turn["startedAt"] is None or phase["observedAt"] is None
            or turn["startedAt"] > phase["observedAt"] + (turn["timestampPrecisionMs"] or 1) - 1):
        return None
    return age_ms(record, turn["startedAt"], now_boottime_ms=now_boottime_ms)
