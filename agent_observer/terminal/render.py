"""Dependency-free safe text rendering for finite terminal reports."""

from __future__ import annotations

import os
import re
import unicodedata
from datetime import UTC, datetime

from .model import sort_rows

_SGR = re.compile(r"\x1b\[[0-9;]*m")


def _cells(value: str) -> int:
    return sum(
        0
        if unicodedata.combining(char)
        else 2
        if unicodedata.east_asian_width(char) in {"W", "F"}
        else 1
        for char in _SGR.sub("", value)
    )


def _word_parts(word: str, width: int) -> list[str]:
    parts, current, cells, active = [], "", 0, ""
    for token in re.findall(r"\x1b\[[0-9;]*m|[^\x1b]", word):
        if _SGR.fullmatch(token):
            current += token
            active = "" if token == "\x1b[0m" else token
            continue
        size = _cells(token)
        if cells + size > width and cells:
            parts.append(current + ("\x1b[0m" if active else ""))
            current, cells = active, 0
        current += token
        cells += size
    if current:
        parts.append(current)
    return parts


def _finish(lines: list[str], width: int | None) -> str:
    if width is None:
        return "\n".join(lines)
    width = max(4, width)
    output = []
    for line in lines:
        if _cells(line) <= width:
            output.append(line)
            continue
        indent = line[: len(line) - len(line.lstrip())]
        indent = indent[: max(0, width - 4)]
        prefix = indent
        available = max(2, width - _cells(indent) - 2)
        current = prefix
        for word in line.split():
            for part in _word_parts(word, available):
                separator = " " if current != prefix else ""
                if _cells(current + separator + part) > width:
                    output.append(current)
                    prefix = indent + "  "
                    current, separator = prefix, ""
                current += separator + part
        if current != prefix:
            output.append(current)
    return "\n".join(output)


def color_enabled(mode: str, *, environ=None, isatty: bool = False) -> bool:
    environ = os.environ if environ is None else environ
    if environ.get("NO_COLOR"):
        return False
    if not isatty or mode == "never":
        return False
    if mode == "always":
        return True
    return environ.get("TERM", "") != "dumb"


def _style(value: str, code: str, enabled: bool) -> str:
    return f"\x1b[{code}m{value}\x1b[0m" if enabled else value


def _health_counts(report: dict) -> str:
    totals = report["totals"]
    complete = totals["completeSources"]
    partial = totals["partialSources"]
    failed = totals["failedSources"]
    return f"{complete} complete, {partial} partial, {failed} unavailable/blocked"


def _source_line(
    source: dict, enabled: bool, *, verbose: bool = False, compact: bool = False
) -> str:
    state = source["health"]
    color = (
        "32"
        if state == "complete"
        else "36"
        if state == "configured"
        else "33"
        if state in {"partial", "stale", "warming"}
        else "31"
    )
    label = _style(state, color, enabled)
    route = f"{source['host']}/{source['label']}"
    text = f"{route}: {label}" if compact else f"{route} [{source['id']}]: {label}"
    if not verbose:
        if state == "complete":
            return text
        explanations = {
            "namespace_mismatch": "configured home does not match the observed namespace",
            "identity_conflict": "sources claim the same exact identity",
            "source_identity_capacity": "configured reader capacity exceeded",
            "source_payload_capacity": "configured reader capacity exceeded",
            "mesh_resync": "delivery reset; current facts revoked",
            "mesh_gap": "delivery gap; current facts revoked",
            "mesh_delivery_disconnected": "connection lost; current facts revoked",
            "source_unavailable": "cached source is unavailable",
            "source_not_configured": "Mesh source is not configured on that host",
            "transport_failure": "host transport is unavailable",
            "deadline_timeout": "read deadline elapsed before a baseline",
            "clock_discontinuity": "activity evidence crossed a clock change",
            "clock_bracket_overlap": "activity age is not proved at the window boundary",
            "census_support_unproved": "session census evidence is not current",
            "census_identity_unprojected": "some census identities lack membership evidence",
            "working_set_membership_unresolved": "membership evidence is incomplete or expired",
        }
        reasons = [source.get("deliveryError"), source.get("reason"), *source.get("reasons", ())]
        explanation = next((explanations[code] for code in reasons if code in explanations), None)
        if explanation is None:
            explanation = (
                "waiting for an admitted baseline"
                if state == "warming"
                else "coverage is incomplete; see sessions sources"
                if state in {"partial", "stale"}
                else "read unavailable; see sessions sources"
            )
        return text + "; " + explanation
    if source.get("scopes"):
        detail = ", ".join(
            f"{scope.get('provider')} coverage={scope['coverage']['status']}"
            for scope in source["scopes"]
        )
        text += f"; {detail}"
    elif source["health"] == "warming":
        text += "; waiting for an admitted baseline"
    else:
        text += "; no current scope coverage"
    reasons = list(source.get("reasons", ()))
    if source.get("reason") and source["reason"] not in reasons:
        reasons.append(source["reason"])
    if reasons:
        text += "; reason=" + ",".join(reasons)
    elif source["health"] == "configured":
        text += "; no connection opened"
    if verbose:
        text += (
            f"; namespace expected={source['expectedNamespace']} "
            f"observed={source.get('observedNamespace') or 'unknown'}"
        )
    return text


def _wall_now_ms(report: dict) -> int:
    try:
        value = datetime.fromisoformat(report["generatedAt"].replace("Z", "+00:00"))
        return int(value.astimezone(UTC).timestamp() * 1000)
    except (ValueError, TypeError, OverflowError):
        return 0


def _wall_time(ms) -> str:
    if type(ms) is not int:
        return "unknown"
    try:
        return (
            datetime.fromtimestamp(ms / 1000, UTC)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
    except (OverflowError, OSError, ValueError):
        return "invalid timestamp"


def _activity_text(session: dict, now_ms: int) -> str:
    activity = session.get("activity", {})
    if activity.get("health") != "current" or type(activity.get("at")) is not int:
        health = activity.get("health", "unavailable")
        return f"unknown ({health})"
    delta = now_ms - activity["at"]
    if delta < 0:
        return "clock ahead"
    if delta < 60_000:
        quantity, unit = max(1, delta // 1000), "s"
    elif delta < 3_600_000:
        quantity, unit = delta // 60_000, "m"
    elif delta < 86_400_000:
        quantity, unit = delta // 3_600_000, "h"
    else:
        quantity, unit = delta // 86_400_000, "d"
    return f"approx. {quantity}{unit} ago"


def _runtime_text(session: dict) -> str:
    fact = session.get("runtime", {})
    if fact.get("health") == "current" and fact.get("value") in {"running", "parked"}:
        return fact["value"]
    return f"unknown ({fact.get('health', 'unavailable')})"


def _phase_text(session: dict) -> str:
    fact = session.get("phase", {})
    if fact.get("health") == "not_applicable":
        return "-"
    if fact.get("health") == "current" and fact.get("value") in {"working", "blocked", "waiting"}:
        return fact["value"]
    return f"unknown ({fact.get('health', 'unavailable')})"


def _rows(report: dict) -> list[dict]:
    rows = [*report["sessions"], *report["uncertain"], *report["nonmembers"]]
    return sort_rows(rows, report["filters"]["sort"], report["filters"]["group"])


def _overview_header(report: dict, enabled: bool) -> list[str]:
    totals = report["totals"]
    count = totals["members"]
    counts = [f"{count} session{'s' if count != 1 else ''}"]
    if totals["uncertain"]:
        counts.append(f"{totals['uncertain']} uncertain")
    if totals["nonmembers"]:
        counts.append(f"{totals['nonmembers']} known nonmembers")
    lines = [_style("Agent Observer", "1", enabled) + "   " + " · ".join(counts)]
    coverage = [f"{totals['completeSources']}/{totals['selectedSources']} sources complete"]
    if totals["partialSources"]:
        coverage.append(f"{totals['partialSources']} partial/stale/warming")
    if totals["failedSources"]:
        coverage.append(f"{totals['failedSources']} unavailable/blocked")
    lines.append("Coverage: " + "; ".join(coverage))
    complete = [
        f"{source['host']}/{source['label']}"
        for source in report["sources"]
        if source["health"] == "complete"
    ]
    if complete:
        lines.append("Sources: " + ", ".join(complete))
    lines.extend(
        _source_line(source, enabled, compact=True)
        for source in report["sources"]
        if source["health"] != "complete"
    )
    selectors = []
    for name in ("membership", "runtime", "phase", "query"):
        if report["filters"][name]:
            selectors.append(f"{name}=" + ", ".join(report["filters"][name]))
    if selectors:
        lines.append("Filters: " + "; ".join(selectors))
    if totals["hiddenKinds"]:
        lines.append(f"Hidden: {totals['hiddenKinds']} child/system sessions")
    return lines


def _overview_values(row: dict, now_ms: int, context: bool) -> tuple[list[str], list[str]]:
    member = row["membership"] in {"active", "recent"}
    runtime = _runtime_text(row) if member else "unknown"
    phase = _phase_text(row) if member else "unknown"
    activity = _activity_text(row, now_ms) if member else "unknown"
    notes = []
    for name, value in (("runtime", runtime), ("phase", phase), ("activity", activity)):
        if member and value.startswith("unknown ("):
            notes.append(f"{name}: {value}")
    values = [row.get("label") or f"Codex {row['identity']['nativeId']}"]
    if context:
        values.append(row.get("context") or "-")
    values.extend(
        (
            f"{row['source']['host']}/{row['source']['label']}",
            row["membership"],
            "unknown" if runtime.startswith("unknown (") else runtime,
            "unknown" if phase.startswith("unknown (") else phase,
            "unknown"
            if activity.startswith("unknown (")
            else activity.replace("approx. ", "~").removesuffix(" ago"),
        )
    )
    if not member and row.get("reason"):
        notes.append(f"membership: {row['reason']}")
    return values, notes


def _overview_table(
    rows: list[dict], now_ms: int, enabled: bool, group: str, width: int | None
) -> list[str]:
    if not rows:
        return []
    context = any(row.get("context") for row in rows) and (width is None or width >= 110)
    headers = [
        "SESSION",
        *(["CONTEXT"] if context else []),
        "HOST/HOME",
        "MEMBER",
        "RUNTIME",
        "PHASE",
        "ACTIVITY",
    ]
    prepared = [_overview_values(row, now_ms, context) for row in rows]
    widths = [
        max(_cells(header), *(_cells(values[index]) for values, _ in prepared))
        for index, header in enumerate(headers)
    ]
    flexible = {0: (12, 30), 1: (10, 22), 2: (10, 24)} if context else {0: (12, 30), 1: (10, 24)}
    if width is not None:
        for index, (_, preferred) in flexible.items():
            widths[index] = min(widths[index], preferred)
        while sum(widths) + 2 * (len(headers) - 1) > width:
            choices = [index for index, (minimum, _) in flexible.items() if widths[index] > minimum]
            if not choices:
                break
            index = max(choices, key=lambda item: widths[item] - flexible[item][0])
            widths[index] -= 1
    compact = width is not None and (width < 72 or sum(widths) + 2 * (len(headers) - 1) > width)
    output = []
    if not compact:
        heading = "  ".join(
            value.ljust(size) for value, size in zip(headers, widths, strict=True)
        ).rstrip()
        output.extend((_style(heading, "2", enabled), "  ".join("-" * size for size in widths)))
    previous_group = None
    for row, (values, notes) in zip(rows, prepared, strict=True):
        source = row["source"]
        if group == "host-home":
            selected_group = (source["host"], source["home"], source["label"])
            if selected_group != previous_group:
                output.append(f"[{selected_group[0]}/{selected_group[2]}]")
                previous_group = selected_group
        if compact:
            if output:
                output.append("")
            output.append(_style(values[0], "1", enabled))
            output.append("  " + " · ".join(values[1:]))
        else:
            cells = [
                _finish([value], size).splitlines()
                for value, size in zip(values, widths, strict=True)
            ]
            for line_index in range(max(map(len, cells))):
                parts = []
                for index, (cell, size) in enumerate(zip(cells, widths, strict=True)):
                    value = cell[line_index] if line_index < len(cell) else ""
                    padded = value + " " * (size - _cells(value))
                    if index == len(headers) - 2:
                        code = {
                            "working": "32",
                            "blocked": "33",
                            "waiting": "36",
                            "unknown": "33",
                        }.get(value)
                        if code:
                            padded = _style(padded, code, enabled)
                    parts.append(padded)
                output.append("  ".join(parts).rstrip())
        if notes:
            output.append("  " + "; ".join(notes))
    return output


def _session_table(
    rows: list[dict], now_ms: int, enabled: bool, group: str, width: int | None
) -> list[str]:
    if not rows:
        return []
    values = [
        (
            row.get("label", ""),
            f"{row['source']['host']}/{row['source']['label']}",
            row["membership"],
            _runtime_text(row) if row["membership"] in {"active", "recent"} else "unknown",
            _phase_text(row) if row["membership"] in {"active", "recent"} else "unknown",
            _activity_text(row, now_ms) if row["membership"] in {"active", "recent"} else "unknown",
            row["identity"]["nativeId"],
        )
        for row in rows
    ]
    headers = ("SESSION", "HOST/HOME", "MEMBERSHIP", "RUNTIME", "PHASE", "ACTIVITY", "ID")
    widths = [
        max(_cells(headers[index]), *(_cells(value[index]) for value in values))
        for index in range(len(headers))
    ]
    if width is not None and sum(widths) + 2 * (len(headers) - 1) > width:
        output = []
        previous_group = None
        for row in rows:
            source = row["source"]
            if group == "host-home":
                selected_group = (source["host"], source["home"], source["label"])
                if selected_group != previous_group:
                    output.append(f"[{selected_group[0]}/{selected_group[2]}]")
                    previous_group = selected_group
            membership = row["membership"]
            runtime = _runtime_text(row) if membership in {"active", "recent"} else "unknown"
            phase = _phase_text(row) if membership in {"active", "recent"} else "unknown"
            activity = (
                _activity_text(row, now_ms) if membership in {"active", "recent"} else "unknown"
            )
            color = "32" if membership == "active" else "36" if membership == "recent" else "33"
            output.append(
                f"- {_style(membership, color, enabled)} / {runtime} / {phase} / {activity}"
            )
            label = row.get("label") or f"Codex {row['identity']['nativeId']}"
            output.append("  " + label)
            output.append(f"  host/home: {source['host']}/{source['label']}")
            if row.get("context"):
                output.append("  context: " + row["context"])
            output.append("  id: " + row["identity"]["nativeId"])
        return output
    output = ["  ".join(headers[index].ljust(widths[index]) for index in range(len(headers)))]
    output.append("  ".join("-" * width for width in widths))
    previous_group = None
    for row, value in zip(rows, values, strict=True):
        if group == "host-home":
            selected_group = (row["source"]["host"], row["source"]["home"], row["source"]["label"])
            if selected_group != previous_group:
                output.append(f"[{selected_group[0]}/{selected_group[2]}]")
                previous_group = selected_group
        colored = list(value)
        padded = [
            colored[index] + " " * (widths[index] - _cells(colored[index]))
            for index in range(len(colored))
        ]
        padded[2] = _style(
            padded[2],
            "32" if colored[2] == "active" else "36" if colored[2] == "recent" else "33",
            enabled,
        )
        output.append("  ".join(padded))
        if row.get("context"):
            output.append("  context: " + row["context"])
    return output


def _details(row: dict, report: dict) -> list[str]:
    ident = row["identity"]
    source = row["source"]
    output = [
        f"{row.get('label', 'Codex ' + ident['nativeId'])}",
        f"Source: {source['id']} ({source['host']}/{source['label']}; home={source['home']}; Mesh={source['meshSource']})",
        f"Membership: {row['membership']}",
        "Identity: "
        + "/".join(
            ident[key] for key in ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId")
        ),
    ]
    for name in ("runtime", "phase"):
        fact = row.get(name, {})
        output.append(
            f"{name.title()}: {fact.get('value') or 'unknown'} ({fact.get('health')}; reason={fact.get('reason') or 'none'})"
        )
        if fact.get("observedAt") is not None:
            output.append(
                f"  observed at: {_wall_time(fact['observedAt'])} ({fact['observedAt']} ms)"
            )
        if fact.get("lastKnownValue") is not None:
            output.append(f"  last known: {fact['lastKnownValue']} (not current) ")
    activity = row.get("activity", {})
    at = activity.get("at") if activity.get("at") is not None else activity.get("lastKnownAt")
    activity_qualification = (
        _activity_text(row, _wall_now_ms(report))
        if activity.get("health") == "current" and activity.get("at") is not None
        else "not current"
    )
    output.append(
        f"Activity: {_wall_time(at)} ({at if at is not None else 'unknown'} ms; "
        f"{activity.get('health')}; {activity_qualification}; reason={activity.get('reason') or 'none'})"
    )
    if row.get("context"):
        output.append(f"Context: {row['context']}")
    details = row.get("details", {})
    if details.get("cwd"):
        output.append(f"Path: {details['cwd']}")
    if details.get("projectKey"):
        output.append(f"Project key: {details['projectKey']}")
    if details.get("workspaceHealth"):
        output.append(
            f"Workspace metadata: {details['workspaceHealth']} "
            f"(reason={details.get('workspaceReason') or 'none'})"
        )
    if details.get("metadataIssues"):
        output.append("Metadata issues: " + ", ".join(details["metadataIssues"]))
    if details.get("blockedReasons"):
        output.append("Blocked evidence: " + ", ".join(details["blockedReasons"]))
    branches = row.get("membershipBranches", {})
    output.append(
        "Membership leases (receiving CLOCK_BOOTTIME): "
        + ", ".join(
            f"{key}={branches.get(key) or 'unavailable'}"
            for key in (
                "activeExpiresAtBoottimeMs",
                "recentExpiresAtBoottimeMs",
                "membershipExpiresAtBoottimeMs",
            )
        )
    )
    expiries = details.get("fieldExpiresAtBoottimeMs", {})
    if expiries:
        output.append(
            "Field leases (receiving CLOCK_BOOTTIME): "
            + ", ".join(
                f"{name}={expiries[name] if expiries[name] is not None else 'unavailable'}"
                for name in sorted(expiries)
            )
        )
    output.append(
        f"Receiving clock: {report['clock']['bootId']} {report['clock']['timeNamespace']} "
        f"now={report['clock']['nowBoottimeMs']}"
    )
    source_info = next((item for item in report["sources"] if item["id"] == source["id"]), None)
    if source_info:
        output.append(
            f"Source health: {source_info['health']}; reasons={', '.join(source_info['reasons']) or 'none'}"
        )
        for scope in source_info["scopes"]:
            output.append(
                f"Scope: {scope['host']}/{scope['provider']}/{scope['namespace']} "
                f"coverage={scope['coverage']['status']} reason={scope['coverage']['reason'] or 'none'} "
                f"expires={scope['coverage']['expiresAtBoottimeMs'] or 'unknown'}"
            )
    return output


def render(
    report: dict,
    *,
    mode: str = "overview",
    color: bool = False,
    width: int | None = None,
    command: str = "agent-observer sessions",
) -> str:
    """Render one report as safe ordinary terminal text without truncation."""
    lines = []
    totals = report["totals"]
    if report.get("error"):
        lines.append(
            f"Report {report['result']}: {report['error']['code']} - {report['error']['message']}"
        )
    if mode == "sources":
        lines.append(f"Sources: {totals['selectedSources']} selected; {_health_counts(report)}")
        lines.extend(_source_line(source, color, verbose=True) for source in report["sources"])
        return _finish(lines, width)

    if mode == "show":
        if report["result"] == "not_found":
            lines.append("Exact identity was not in the fully observed selected projection.")
        elif report["error"] and report["error"].get("code") == "target_unresolved":
            lines.append("Exact identity membership is unresolved; selected coverage is degraded.")
        rows = _rows(report)
        lines.extend(_source_line(source, color, verbose=True) for source in report["sources"])
        if rows:
            row = rows[0]
            if row.get("membership") in {"uncertain", "nonmember"}:
                lines.extend(
                    (
                        row.get("label", f"Codex {row['identity']['nativeId']}"),
                        f"Membership: {row['membership']}",
                        f"Reason: {row['reason']}",
                        f"Source: {row['source']['host']}/{row['source']['label']} ({row['source']['id']})",
                    )
                )
                lines.append(
                    "Identity: "
                    + "/".join(
                        row["identity"][key]
                        for key in (
                            "hostScope",
                            "provider",
                            "namespace",
                            "nativeIdKind",
                            "nativeId",
                        )
                    )
                )
            else:
                lines.extend(_details(row, report))
        return _finish(lines, width)

    lines.extend(_overview_header(report, color))
    if mode == "list":
        lines.append(f"Matches: {totals['displayedMatches']}")
    lines.append("")
    if totals["state"] == "complete-empty":
        lines.append("No qualifying members in complete current coverage.")
    elif totals["members"] == 0 and totals["nonmembers"]:
        lines.append(f"0 qualifying members; {totals['nonmembers']} known nonmembers.")
    elif totals["displayedMatches"] == 0:
        lines.append("0 matches; source health and unfiltered counts are shown above.")
    rows = _rows(report)
    table = _overview_table if mode == "overview" else _session_table
    lines.extend(table(rows, _wall_now_ms(report), color, report["filters"]["group"], width))
    if mode == "overview":
        lines.append("")
        if totals["displayedMatches"] > totals["shown"]:
            lines.append(f"Showing {totals['shown']} of {totals['displayedMatches']} matches.")
        elif rows and totals["displayedMatches"] != totals["members"] + totals["uncertain"]:
            lines.append(f"{totals['displayedMatches']} matches in the selected sources.")
        lines.append(f"All rows, context and full IDs: {command} list")
        if rows:
            lines.append("~ approximate activity age; membership, runtime and phase are separate.")
    return _finish(lines, width)
