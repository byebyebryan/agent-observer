"""Pure terminal model tests over bounded synthetic facade records."""

import unittest
from types import SimpleNamespace

from agent_observer.terminal.model import build_report, safe_metadata

NOW = 1_000
NAMESPACE = "sha256:" + "a" * 64


def identity(native_id, *, host="fixture", namespace=NAMESPACE):
    return {
        "hostScope": host,
        "provider": "codex",
        "namespace": namespace,
        "nativeIdKind": "thread_id",
        "nativeId": native_id,
    }


def source(
    source_id="fixture-default",
    *,
    host="fixture",
    home="default",
    mesh="working",
    namespace=NAMESPACE,
):
    return {
        "id": source_id,
        "host": host,
        "home": home,
        "label": home.title(),
        "meshSource": mesh,
        "scope": "local",
        "socket": "/run/user/1000/mesh.sock",
        "namespace": namespace,
        "windowHours": 72,
        "maxIdentities": 1024,
        "maxPayloadMiB": 4,
    }


def row(native_id, *, title="Fixture session", kind="user", host="fixture", workspace=None):
    return {
        "identity": identity(native_id, host=host),
        "title": title,
        "kind": kind,
        "cwd": "/synthetic/workspace",
        "workspace": workspace
        or {"health": "current", "reason": "mapped", "projectKey": "fixture-project"},
        "metadataIssues": [],
        "blockedReasons": [],
        "runtime": {"value": "running", "health": "current", "reason": "native", "observedAt": 900},
        "phase": {"value": "working", "health": "current", "reason": "native", "observedAt": 900},
        "activity": {
            "at": 950,
            "health": "current",
            "reason": "native_timestamp",
            "source": "codex_rpc",
        },
    }


def read(*, rows=(), leases=(), uncertain=(), nonmembers=(), scopes=True, host="fixture"):
    scope_rows = []
    if scopes:
        scope_rows.append(
            {
                "hostScope": host,
                "provider": "codex",
                "namespace": NAMESPACE,
                "serviceId": "synthetic-service",
                "contextGeneration": 1,
                "continuity": 1,
                "coverage": {"status": "complete", "reason": None, "expiresAtMs": 2_000},
            }
        )
    return SimpleNamespace(
        context={
            "hosts": [{"hostId": host, "delivery": {"status": "ready"}, "viewState": "current"}]
        },
        members=list(rows),
        member_leases=list(leases),
        uncertain=list(uncertain),
        nonmembers=list(nonmembers),
        scopes=scope_rows,
    )


def lease(native_id, *, active=1_500, recent=1_700, host="fixture"):
    return {
        "identity": identity(native_id, host=host),
        "activeExpiresAtMs": active,
        "recentExpiresAtMs": recent,
        "membershipExpiresAtMs": 1_700,
    }


def state(
    config=None,
    *,
    current_read=None,
    lifecycle="observing",
    baseline=True,
    reason=None,
    capture=NOW,
):
    config = source() if config is None else config
    return {
        "config": config,
        "lifecycle": lifecycle,
        "reason": reason,
        "baseline": baseline,
        "read": current_read,
        "capture_boottime_ms": capture,
        "last_frame_boottime_ms": capture,
        "clock": {
            "kind": "CLOCK_BOOTTIME",
            "bootId": "fixture-boot",
            "timeNamespace": "time:7",
            "clockDomain": "time:[7]",
        },
    }


def report(states, *, mode="list", filters=None, target=None):
    defaults = {
        "source": (),
        "host": (),
        "home": (),
        "membership": (),
        "runtime": (),
        "phase": (),
        "query": (),
        "includeChildren": False,
        "includeSystem": False,
        "sort": "activity",
        "group": "none",
        "configPath": "/synthetic/terminal.toml",
    }
    defaults.update(filters or {})
    return build_report(
        states,
        now_boottime_ms=NOW,
        generated_at="2026-10-25T12:00:00.000Z",
        clock={
            "kind": "CLOCK_BOOTTIME",
            "bootId": "fixture-boot",
            "timeNamespace": "time:7",
            "clockDomain": "time:[7]",
            "nowBoottimeMs": NOW,
        },
        mode=mode,
        filters=defaults,
        target=target,
    )


class TerminalModelTests(unittest.TestCase):
    def test_membership_stays_separate_from_runtime_and_filters_are_or_within_selector(self):
        rows = [
            row("id-active", title="Renderer review"),
            row("id-recent", title="Release notes"),
            row("id-child", title="Renderer child", kind="child"),
        ]
        leases = [lease(item["identity"]["nativeId"]) for item in rows]
        leases[1]["activeExpiresAtMs"] = None
        read_value = read(rows=rows, leases=leases)
        result = report(
            [state(current_read=read_value)], filters={"query": ("renderer", "release")}
        )
        self.assertEqual(result["totals"]["members"], 3)
        self.assertEqual(result["totals"]["hiddenKinds"], 1)
        self.assertEqual(
            [item["label"] for item in result["sessions"]], ["Renderer review", "Release notes"]
        )
        self.assertEqual([item["membership"] for item in result["sessions"]], ["active", "recent"])
        self.assertEqual(result["sessions"][1]["runtime"]["value"], "running")
        self.assertEqual(result["totals"]["displayedMatches"], 2)

    def test_complete_empty_requires_a_present_complete_scope(self):
        complete = report([state(current_read=read())])
        self.assertEqual(complete["totals"]["state"], "complete-empty")
        self.assertEqual(complete["result"], "complete")

        missing_scope = report([state(current_read=read(scopes=False))])
        self.assertNotEqual(missing_scope["totals"]["state"], "complete-empty")
        self.assertEqual(missing_scope["result"], "degraded")

    def test_failed_sources_never_publish_retained_rows(self):
        source_read = read(rows=[row("id-stale")], leases=[lease("id-stale")])
        degraded = report(
            [
                state(
                    current_read=source_read,
                    lifecycle="failed",
                    baseline=False,
                    reason="mesh_resync",
                )
            ]
        )
        self.assertEqual(degraded["sessions"], [])
        self.assertEqual(degraded["totals"]["members"], 0)
        self.assertEqual(degraded["sources"][0]["health"], "unavailable")

    def test_duplicate_identity_blocks_all_claimant_source_rows(self):
        duplicate = row("same-id")
        unique_in_claimant = row("unique-in-blocked-source")
        source_a = source("route-a", host="fixture", home="default", mesh="working-a")
        source_b = source("route-b", host="fixture", home="work", mesh="working-b")
        source_c = source("route-c", host="healthy", home="default", mesh="working-c")
        source_a_read = read(
            rows=[duplicate, unique_in_claimant],
            leases=[lease("same-id"), lease("unique-in-blocked-source")],
        )
        source_b_read = read(rows=[duplicate], leases=[lease("same-id")])
        source_c_read = read(
            rows=[row("healthy-id", host="healthy")],
            leases=[lease("healthy-id", host="healthy")],
            host="healthy",
        )

        result = report(
            [
                state(source_a, current_read=source_a_read),
                state(source_b, current_read=source_b_read),
                state(source_c, current_read=source_c_read),
            ]
        )
        self.assertEqual(
            [item["identity"]["nativeId"] for item in result["sessions"]], ["healthy-id"]
        )
        self.assertEqual(
            {item["id"]: item["health"] for item in result["sources"]}["route-a"], "blocked"
        )
        self.assertEqual(
            {item["id"]: item["health"] for item in result["sources"]}["route-b"], "blocked"
        )

    def test_unavailable_workspace_does_not_promote_project_key(self):
        unavailable = row(
            "workspace-id",
            workspace={
                "health": "unavailable",
                "reason": "git_metadata_unavailable",
                "projectKey": "unproved-project",
            },
        )
        result = report(
            [state(current_read=read(rows=[unavailable], leases=[lease("workspace-id")]))]
        )
        session = result["sessions"][0]
        self.assertEqual(session["context"], "workspace")
        self.assertIsNone(session["details"]["projectKey"])
        self.assertEqual(session["details"]["workspaceHealth"], "unavailable")
        self.assertEqual(session["details"]["workspaceReason"], "git_metadata_unavailable")

    def test_uncertain_identity_gets_safe_id_label_and_controls_are_visible(self):
        uncertain_identity = identity("uncertain-id")
        value = read(
            uncertain=[{"identity": uncertain_identity, "reason": "membership_unresolved"}]
        )
        result = report([state(current_read=value)])
        self.assertEqual(result["uncertain"][0]["label"], "Codex uncertain-id")
        self.assertEqual(safe_metadata("safe\u202ename"), r"safe\u202Ename")

    def test_show_exact_id_and_ref_have_distinct_complete_not_found_and_unresolved_results(self):
        member = row("show-id")
        source_state = state(current_read=read(rows=[member], leases=[lease("show-id")]))
        found = report([source_state], mode="show", target="show-id")
        self.assertEqual(found["result"], "complete")
        missing = report([source_state], mode="show", target="missing-id")
        self.assertEqual(missing["result"], "not_found")
        unresolved = report(
            [
                state(
                    current_read=read(
                        uncertain=[{"identity": identity("unknown-id"), "reason": "uncertain"}]
                    )
                )
            ],
            mode="show",
            target=identity("unknown-id"),
        )
        self.assertEqual(unresolved["result"], "degraded")


if __name__ == "__main__":
    unittest.main()
