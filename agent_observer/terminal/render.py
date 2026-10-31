"""Dependency-free safe text rendering for finite terminal reports."""

from __future__ import annotations

import os
import re
import unicodedata
from datetime import UTC, datetime
from pathlib import PurePosixPath

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


def icons_enabled(
    mode: str, *, environ=None, isatty: bool = False, encoding: str | None = "utf-8"
) -> bool:
    environ = os.environ if environ is None else environ
    if not isatty or mode == "never" or (mode == "auto" and environ.get("TERM") == "dumb"):
        return False
    if encoding is None:
        return False
    try:
        "◈✓×●○›─".encode(encoding)
    except (UnicodeError, LookupError):
        return False
    return True


def _style(value: str, code: str, enabled: bool) -> str:
    return f"\x1b[{code}m{value}\x1b[0m" if enabled else value


def _cell_style(value: str, field: str, enabled: bool) -> str:
    code = {
        "session": "1",
        "profile": "2",
        "workspace": "2",
        "last_active": "36",
        "id": "2",
    }.get(field)
    if field == "status":
        plain = value.strip()
        status = plain[2:] if plain[:2] in {"● ", "○ ", "! ", "- ", "? ", "× "} else plain
        code = {
            "Working": "32",
            "Ready": "36",
            "Blocked": "33",
            "Inactive": "2",
            "Stale": "33",
            "Unknown": "33",
            "Unavailable": "31",
        }.get(status)
    if not code or not enabled:
        return value
    text = value.rstrip()
    return _style(text, code, True) + value[len(text) :] if text else value


def _health_counts(report: dict) -> str:
    totals = report["totals"]
    complete = totals["completeSources"]
    partial = totals["partialSources"]
    failed = totals["failedSources"]
    return f"{complete} complete, {partial} partial, {failed} unavailable/blocked"


def _source_line(
    source: dict,
    enabled: bool,
    *,
    verbose: bool = False,
    compact: bool = False,
    icons: bool = False,
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
    glyph = (
        "✓"
        if state == "complete"
        else "○"
        if state == "configured"
        else "!"
        if color == "33"
        else "×"
    )
    label = _style(f"{glyph} {state}" if icons else state, color, enabled)
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


def _qualified_fact_state(fact: object) -> str:
    if type(fact) is not dict:
        return "Unknown"
    health = fact.get("health")
    if health == "stale":
        return "Stale"
    if health == "unavailable":
        return "Unavailable"
    return "Unknown"


def _status_text(row: dict) -> str:
    """Conservative human status from current runtime and phase facts only."""
    runtime = row.get("runtime")
    if type(runtime) is not dict or runtime.get("health") != "current":
        return _qualified_fact_state(runtime)
    if runtime.get("value") == "parked":
        return "Inactive"
    if runtime.get("value") != "running":
        return "Unknown"

    phase = row.get("phase")
    if type(phase) is not dict or phase.get("health") != "current":
        return _qualified_fact_state(phase)
    return {
        "working": "Working",
        "waiting": "Ready",
        "blocked": "Blocked",
    }.get(phase.get("value"), "Unknown")


def _status_label(value: str, icons: bool = False) -> str:
    if not icons:
        return value
    glyph = {
        "Working": "●",
        "Ready": "○",
        "Blocked": "!",
        "Inactive": "-",
        "Stale": "?",
        "Unknown": "?",
        "Unavailable": "×",
    }.get(value)
    return f"{glyph} {value}" if glyph else value


def _last_active_text(row: dict, now_ms: int) -> str:
    activity = row.get("activity")
    if type(activity) is not dict:
        return "Unknown"
    if activity.get("health") != "current" or type(activity.get("at")) is not int:
        return _qualified_fact_state(activity)
    text = _activity_text(row, now_ms)
    if text == "clock ahead":
        return "Clock ahead"
    return text.replace("approx. ", "~").removesuffix(" ago")


def _profile_text(row: dict) -> str:
    source = row.get("source")
    if type(source) is not dict:
        return "unknown"
    host, home = source.get("host"), source.get("home")
    if type(host) is not str or not host or type(home) is not str or not home:
        return "unknown"
    return f"{host}/{home}"


def _compact_cwd(value: object) -> str | None:
    if type(value) is not str or not value:
        return None
    path = PurePosixPath(value)
    parts = [part for part in path.parts if part not in {"/", "."}]
    if not parts:
        return "/" if path.is_absolute() else None
    tail = parts[-1]
    if len(parts) == 1:
        return f"/{tail}" if path.is_absolute() else tail
    return f"…/{tail}"


def _workspace_text(row: dict) -> str:
    """Use only already-projected current repo metadata or reported cwd."""
    details = row.get("details")
    if type(details) is not dict:
        return "unknown"
    repository = details.get("repo")
    if (
        details.get("workspaceHealth") == "current"
        and type(repository) is dict
        and type(repository.get("root")) is str
        and repository["root"]
    ):
        leaf = PurePosixPath(repository["root"]).name
        if leaf:
            return leaf
    return _compact_cwd(details.get("cwd")) or "unknown"


def _session_title(row: dict) -> str:
    label = row.get("label")
    return label if type(label) is str and label else f"Codex {row['identity']['nativeId']}"


def _main_values(row: dict, now_ms: int) -> list[str]:
    return [
        _status_text(row),
        _last_active_text(row, now_ms),
        _session_title(row),
        _profile_text(row),
        _workspace_text(row),
    ]


def _rows(report: dict) -> list[dict]:
    rows = [*report["sessions"], *report["uncertain"], *report["nonmembers"]]
    return sort_rows(rows, report["filters"]["sort"], report["filters"]["group"])


def _overview_header(report: dict, enabled: bool, icons: bool) -> list[str]:
    totals = report["totals"]
    count = totals["members"]
    counts = [_style(f"{count} session{'s' if count != 1 else ''}", "1", enabled)]
    if totals["uncertain"]:
        counts.append(_style(f"{totals['uncertain']} uncertain", "33", enabled))
    if totals["nonmembers"]:
        counts.append(_style(f"{totals['nonmembers']} known nonmembers", "2", enabled))
    brand = "◈ Agent Observer" if icons else "Agent Observer"
    lines = [_style(brand, "1;36", enabled) + "   " + " · ".join(counts)]
    coverage = [f"{totals['completeSources']}/{totals['selectedSources']} sources complete"]
    if totals["partialSources"]:
        coverage.append(f"{totals['partialSources']} partial/stale/warming")
    if totals["failedSources"]:
        coverage.append(f"{totals['failedSources']} unavailable/blocked")
    code = "31" if totals["failedSources"] else "33" if totals["partialSources"] else "32"
    glyph = "×" if totals["failedSources"] else "!" if totals["partialSources"] else "✓"
    lines.append(
        (_style(glyph + " ", code, enabled) if icons else "")
        + _style("Coverage: ", "2", enabled)
        + _style("; ".join(coverage), code, enabled)
    )
    complete = [
        f"{source['host']}/{source['label']}"
        for source in report["sources"]
        if source["health"] == "complete"
    ]
    if complete:
        lines.append(
            _style("Sources: ", "2", enabled) + _style(" · ".join(complete), "36", enabled)
        )
    lines.extend(
        _source_line(source, enabled, compact=True, icons=icons)
        for source in report["sources"]
        if source["health"] != "complete"
    )
    selectors = []
    for name in ("membership", "runtime", "phase", "query"):
        if report["filters"][name]:
            selectors.append(f"{name}=" + ", ".join(report["filters"][name]))
    if selectors:
        lines.append(_style("Filters: ", "2", enabled) + "; ".join(selectors))
    if totals["hiddenKinds"]:
        lines.append(_style(f"Hidden: {totals['hiddenKinds']} child/system sessions", "2", enabled))
    return lines


_MAIN_HEADERS = ("Status", "Last active", "Session", "Profile", "Workspace")
_MAIN_FIELDS = ("status", "last_active", "session", "profile", "workspace")
_MIN_COLUMN_WIDTHS = (13, 11, 10, 16, 12)


def _main_column_widths(
    rows: list[dict], now_ms: int, width: int | None, icons: bool
) -> list[int] | None:
    prepared = [_main_values(row, now_ms) for row in rows]
    for values in prepared:
        values[0] = _status_label(values[0], icons)
    widths = [
        max(minimum, _cells(header), *(_cells(values[index]) for values in prepared))
        for index, (minimum, header) in enumerate(
            zip(_MIN_COLUMN_WIDTHS, _MAIN_HEADERS, strict=True)
        )
    ]
    if width is None:
        return widths
    spare = width - sum(widths) - 2 * (len(widths) - 1)
    if spare < 0:
        return None
    # Keep an ordinary row on one line when it fits. Otherwise use the
    # status/title + context layout rather than splitting identifiers down
    # narrow metadata columns. Any spare width belongs to the title.
    widths[2] += spare
    return widths


def _main_table_header(enabled: bool, widths: list[int]) -> str:
    header = "  ".join(
        value.ljust(size) for value, size in zip(_MAIN_HEADERS, widths, strict=True)
    ).rstrip()
    return _style(header, "1;2", enabled)


def _main_table_row(
    row: dict, now_ms: int, enabled: bool, widths: list[int], icons: bool
) -> list[str]:
    values = _main_values(row, now_ms)
    values[0] = _status_label(values[0], icons)
    cells = [
        _finish([value], size).splitlines()
        for value, size in zip(values, widths, strict=True)
    ]
    output = []
    for line_index in range(max(map(len, cells))):
        parts = []
        for index, (cell, size) in enumerate(zip(cells, widths, strict=True)):
            value = cell[line_index] if line_index < len(cell) else ""
            padded = value + " " * max(0, size - _cells(value))
            parts.append(_cell_style(padded, _MAIN_FIELDS[index], enabled))
        output.append("  ".join(parts).rstrip())
    return output


def _compact_main_row(
    row: dict, now_ms: int, enabled: bool, width: int, icons: bool
) -> list[str]:
    status, activity, title, profile, workspace = _main_values(row, now_ms)
    status = _status_label(status, icons)
    first = (
        _cell_style(status, "status", enabled)
        + "  "
        + _cell_style(activity, "last_active", enabled)
        + "  "
        + _cell_style(title, "session", enabled)
    )
    second = "  " + _cell_style(f"{profile} · {workspace}", "profile", enabled)
    return _finish([first, second], width).splitlines()


def _overview_table(
    rows: list[dict], now_ms: int, enabled: bool, group: str, width: int | None, icons: bool
) -> list[str]:
    if not rows:
        return []
    widths = _main_column_widths(rows, now_ms, width, icons)
    output = [_main_table_header(enabled, widths)] if widths is not None else []
    if widths is None:
        output.extend(_finish(["STATUS · LAST ACTIVE · SESSION / PROFILE · WORKSPACE"], width).splitlines())
    previous_group = None
    for row in rows:
        source = row["source"]
        if group == "host-home":
            selected_group = (source["host"], source["home"])
            if selected_group != previous_group:
                output.append(_style(f"[{selected_group[0]}/{selected_group[1]}]", "1;36", enabled))
                previous_group = selected_group
        if widths is None:
            output.extend(_compact_main_row(row, now_ms, enabled, width or 80, icons))
        else:
            output.extend(_main_table_row(row, now_ms, enabled, widths, icons))
    return output


def _session_table(
    rows: list[dict], now_ms: int, enabled: bool, group: str, width: int | None, icons: bool
) -> list[str]:
    if not rows:
        return []
    widths = _main_column_widths(rows, now_ms, width, icons)
    output = [_main_table_header(enabled, widths)] if widths is not None else []
    if widths is None:
        output.extend(_finish(["STATUS · LAST ACTIVE · SESSION / PROFILE · WORKSPACE"], width).splitlines())
    previous_group = None
    for row in rows:
        source = row["source"]
        if group == "host-home":
            selected_group = (source["host"], source["home"])
            if selected_group != previous_group:
                output.append(f"[{selected_group[0]}/{selected_group[1]}]")
                previous_group = selected_group
        if widths is None:
            output.extend(_compact_main_row(row, now_ms, enabled, width or 80, icons))
        else:
            output.extend(_main_table_row(row, now_ms, enabled, widths, icons))
        evidence = "  id: " + _cell_style(row["identity"]["nativeId"], "id", enabled)
        output.extend(_finish([evidence], width).splitlines() if width is not None else [evidence])
        if row.get("context"):
            context = "  context: " + _cell_style(row["context"], "profile", enabled)
            output.extend(_finish([context], width).splitlines() if width is not None else [context])
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
    icons: bool = False,
    width: int | None = None,
    command: str = "agent-observer sessions",
) -> str:
    """Render one report as safe ordinary terminal text without truncation."""
    lines = []
    totals = report["totals"]
    if report.get("error"):
        lines.append(
            _style(
                ("! " if icons else "")
                + f"Report {report['result']}: {report['error']['code']} - {report['error']['message']}",
                "33",
                color,
            )
        )
    if mode == "sources":
        lines.append(
            _style(
                f"Sources: {totals['selectedSources']} selected; {_health_counts(report)}",
                "1;36",
                color,
            )
        )
        lines.extend(
            _source_line(source, color, verbose=True, icons=icons) for source in report["sources"]
        )
        return _finish(lines, width)

    if mode == "show":
        if report["result"] == "not_found":
            lines.append("Exact identity was not in the fully observed selected projection.")
        elif report["error"] and report["error"].get("code") == "target_unresolved":
            lines.append("Exact identity membership is unresolved; selected coverage is degraded.")
        rows = _rows(report)
        lines.extend(
            _source_line(source, color, verbose=True, icons=icons) for source in report["sources"]
        )
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
                details = _details(row, report)
                details[0] = _style(details[0], "1;36", color)
                lines.extend(details)
        return _finish(lines, width)

    lines.extend(_overview_header(report, color, icons))
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
    lines.extend(table(rows, _wall_now_ms(report), color, report["filters"]["group"], width, icons))
    if mode == "overview":
        lines.append("")
        if totals["displayedMatches"] > totals["shown"]:
            lines.append(
                _style(
                    f"Showing {totals['shown']} of {totals['displayedMatches']} matches.",
                    "2",
                    color,
                )
            )
        elif rows and totals["displayedMatches"] != totals["members"] + totals["uncertain"]:
            lines.append(f"{totals['displayedMatches']} matches in the selected sources.")
        lines.append(
            (_style("› ", "36", color) if icons else "")
            + _style("All rows, context and full IDs: ", "2", color)
            + _style(f"{command} list", "36", color)
        )
        if rows:
            lines.append(_style("~ approximate activity age", "2", color))
    return _finish(lines, width)
