"""Metadata clocks, independent of liveness, creation and presentation policy."""

MAX_TIME_MS = 4_000_000_000_000


def unavailable(reason, health="unavailable"):
    return {"at": None, "source": None, "health": health, "reason": reason}


def codex_activity(payload, *, completion_only=False):
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        return unavailable("activity_metadata_invalid")
    turns = payload["data"]
    if not turns:
        return unavailable("no_conversation_activity")
    if len(turns) != 1 or not isinstance(turns[0], dict):
        return unavailable("activity_metadata_invalid")
    turn = turns[0]
    if turn.get("itemsView") != "notLoaded" or turn.get("items") != []:
        return unavailable("activity_content_rejected")
    start, end = turn.get("startedAt"), turn.get("completedAt")
    def valid(value):
        return type(value) is int and 0 <= value <= MAX_TIME_MS // 1000
    if (
        (start is not None and not valid(start))
        or (end is not None and not valid(end))
        or (start is None and end is None)
        or (start is None and not completion_only)
        or (start is not None and end is not None and end < start)
    ):
        return unavailable("activity_clock_unavailable")
    return {
        "at": (end if end is not None else start) * 1000,
        "source": "codex_turn_metadata",
        "health": "current",
        "reason": "native_conversation_event",
    }


def ordering(row):
    activity = row.get("activity", {})
    at = activity.get("at") if activity.get("health") == "current" else None
    return (at is None, -(at or 0), row["identity"]["nativeId"])
