"""Pure terminal model tests over bounded synthetic facade records."""

import unittest
from types import SimpleNamespace

from agent_observer.terminal.model import build_report, safe_metadata
from agent_observer.terminal.output import json_document

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
        or {
            "health": "current",
            "reason": "mapped",
            "projectKey": "fixture-project",
            "repo": None,
        },
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
        "fieldExpiresAtMs": {"workspace": 2_000},
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


def report(states, *, mode="list", filters=None, target=None, include_repository=False):
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
        include_repository=include_repository,
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
                "repo": {
                    "root": "/synthetic/stale-root",
                    "commonDir": "/synthetic/stale-root/.git",
                    "relativePath": "src",
                },
            },
        )
        result = report(
            [state(current_read=read(rows=[unavailable], leases=[lease("workspace-id")]))],
            include_repository=True,
        )
        session = result["sessions"][0]
        self.assertEqual(session["context"], "workspace")
        self.assertIsNone(session["details"]["projectKey"])
        self.assertEqual(session["details"]["workspaceHealth"], "unavailable")
        self.assertEqual(session["details"]["workspaceReason"], "git_metadata_unavailable")
        self.assertIsNone(session["details"]["repo"])
        self.assertNotIn("stale-root", json_document(session))

    def test_repository_enrichment_is_opt_in_and_sanitizes_current_workspace(self):
        current = row("repo-id")
        current["cwd"] = "/synthetic/worktrees/topic/src"
        current["workspace"] = {
            "health": "current",
            "reason": "mapped",
            "root": "/synthetic/worktrees/topic",
            "rootKey": "workspace-topic",
            "relativePath": "src",
            "projectKey": "fixture-project",
            "repo": {
                "root": "/synthetic/worktrees/topic\x1b",
                "commonDir": "/synthetic/repos/shared/.git\x01",
                "relativePath": "src\x1b",
            },
        }
        current_state = state(
            current_read=read(rows=[current], leases=[lease("repo-id")])
        )

        finite = report([current_state])
        finite_false = report([current_state], include_repository=False)
        dashboard = report([current_state], include_repository=True)
        finite_session = finite["sessions"][0]
        dashboard_session = dashboard["sessions"][0]
        self.assertEqual(finite, finite_false)
        self.assertEqual(json_document(finite), json_document(finite_false))
        self.assertNotIn("repo", finite_session["details"])
        self.assertEqual(
            dashboard_session["details"]["repo"],
            {
                "root": r"/synthetic/worktrees/topic\u001B",
                "commonDir": r"/synthetic/repos/shared/.git\u0001",
                "relativePath": r"src\u001B",
            },
        )

        expired_lease = lease("repo-id")
        expired_lease["fieldExpiresAtMs"]["workspace"] = NOW
        expired = report(
            [
                state(
                    current_read=read(rows=[current], leases=[expired_lease])
                )
            ],
            include_repository=True,
        )["sessions"][0]
        self.assertIsNone(expired["details"]["repo"])
        self.assertEqual(expired["details"]["workspaceHealth"], "unavailable")
        self.assertEqual(
            expired["details"]["workspaceReason"], "workspace_support_expired"
        )
        self.assertIsNone(expired["details"]["projectKey"])
        self.assertEqual(expired["context"], "src")

        no_repo = row("no-repo")
        no_repo["workspace"]["repo"] = None
        no_repo_report = report(
            [state(current_read=read(rows=[no_repo], leases=[lease("no-repo")]))],
            include_repository=True,
        )
        self.assertIsNone(no_repo_report["sessions"][0]["details"]["repo"])
        self.assertEqual(no_repo_report["sessions"][0]["details"]["workspaceHealth"], "current")

        missing = row("missing-workspace")
        missing["workspace"] = None
        missing.pop("cwd")
        missing_report = report(
            [
                state(
                    current_read=read(
                        rows=[missing], leases=[lease("missing-workspace")]
                    )
                )
            ],
            include_repository=True,
        )
        missing_session = missing_report["sessions"][0]
        self.assertIsNone(missing_session["details"]["repo"])
        self.assertIsNone(missing_session["details"]["workspaceHealth"])
        self.assertIsNone(missing_session["details"]["cwd"])

    def test_repository_search_uses_only_current_cached_fields_and_keeps_filters(self):
        first = row("worktree-one", title="Alpha task")
        first["cwd"] = "/synthetic/cwd/alpha"
        first["workspace"] = {
            "health": "current",
            "reason": "mapped",
            "projectKey": "alpha-project",
            "repo": {
                "root": "/synthetic/worktrees/feature-one",
                "commonDir": "/synthetic/repositories/shared.git",
                "relativePath": "modules/alpha",
            },
        }
        second = row("worktree-two", title="Beta task")
        second["cwd"] = "/synthetic/cwd/beta"
        second["workspace"] = {
            "health": "current",
            "reason": "mapped",
            "projectKey": "beta-project",
            "repo": {
                "root": "/synthetic/worktrees/feature-two",
                "commonDir": "/synthetic/repositories/shared.git",
                "relativePath": "tools/beta",
            },
        }
        second_lease = lease("worktree-two")
        second_lease["activeExpiresAtMs"] = None
        current = state(
            current_read=read(
                rows=[first, second],
                leases=[lease("worktree-one"), second_lease],
            )
        )

        def matching_ids(query, *, extra_filters=None, include_repository=True):
            filters = {"query": query}
            filters.update(extra_filters or {})
            result = report(
                [current], filters=filters, include_repository=include_repository
            )
            return [item["identity"]["nativeId"] for item in result["sessions"]]

        # Root, common directory, and relative path are all searchable. Full
        # shared-directory matching returns both linked worktrees independently.
        self.assertEqual(matching_ids(("FEATURE-ONE",)), ["worktree-one"])
        self.assertEqual(
            matching_ids(("repositories/shared",)), ["worktree-one", "worktree-two"]
        )
        self.assertEqual(matching_ids(("tools/beta",)), ["worktree-two"])

        # Search terms remain OR-ed, while other filter dimensions still narrow
        # the matching identities. Regex punctuation remains literal text.
        self.assertEqual(
            matching_ids(("feature-one", "Beta task")),
            ["worktree-one", "worktree-two"],
        )
        self.assertEqual(
            matching_ids(
                ("feature-one", "Beta task"),
                extra_filters={"membership": ("recent",)},
            ),
            ["worktree-two"],
        )
        self.assertEqual(matching_ids(("feature-one|Beta task",)), [])

        # The finite CLI keeps its existing search fields and JSON contract.
        self.assertEqual(
            matching_ids(("feature-one",), include_repository=False), []
        )

        stale = row("stale-repository", title="Expired task")
        stale["cwd"] = "/synthetic/reported-cwd"
        stale["workspace"] = {
            "health": "current",
            "reason": "mapped",
            "projectKey": "still-project-context",
            "repo": {
                "root": "/synthetic/worktrees/expired-root",
                "commonDir": "/synthetic/repositories/expired-shared.git",
                "relativePath": "expired/path",
            },
        }
        expired_lease = lease("stale-repository")
        expired_lease["fieldExpiresAtMs"]["workspace"] = NOW
        expired_state = state(
            current_read=read(rows=[stale], leases=[expired_lease])
        )

        def expired_matches(query):
            return report(
                [expired_state],
                filters={"query": (query,)},
                include_repository=True,
            )["sessions"]

        self.assertEqual(expired_matches("expired-root"), [])
        # Repo expiry does not disable independently admitted label or cwd text.
        self.assertEqual(len(expired_matches("Expired task")), 1)
        self.assertEqual(len(expired_matches("reported-cwd")), 1)

        stale_workspace = row("unavailable-repository")
        stale_workspace["workspace"] = {
            "health": "unavailable",
            "reason": "workspace_unavailable",
            "projectKey": "stale-project",
            "repo": {
                "root": "/synthetic/worktrees/unavailable-root",
                "commonDir": "/synthetic/repositories/unavailable.git",
                "relativePath": "unavailable/path",
            },
        }
        unavailable = report(
            [
                state(
                    current_read=read(
                        rows=[stale_workspace],
                        leases=[lease("unavailable-repository")],
                    )
                )
            ],
            filters={"query": ("unavailable-root",)},
            include_repository=True,
        )
        self.assertEqual(unavailable["sessions"], [])

        missing_lease = row("missing-repository-lease")
        missing_lease["workspace"]["repo"] = {
            "root": "/synthetic/worktrees/unleased-root",
            "commonDir": "/synthetic/repositories/unleased.git",
            "relativePath": "unleased/path",
        }
        no_workspace_lease = lease("missing-repository-lease")
        no_workspace_lease["fieldExpiresAtMs"].pop("workspace")
        missing_lease_report = report(
            [
                state(
                    current_read=read(
                        rows=[missing_lease], leases=[no_workspace_lease]
                    )
                )
            ],
            filters={"query": ("unleased-root",)},
            include_repository=True,
        )
        self.assertEqual(missing_lease_report["sessions"], [])

        no_repository = row("no-repository", title="No repository task")
        no_repository["workspace"]["repo"] = None
        no_repository_state = state(
            current_read=read(
                rows=[no_repository], leases=[lease("no-repository")]
            )
        )
        project_match = report(
            [no_repository_state],
            filters={"query": ("fixture-project",)},
            include_repository=True,
        )
        self.assertEqual(len(project_match["sessions"]), 1)
        for placeholder in ("none", "unavailable"):
            self.assertEqual(
                report(
                    [no_repository_state],
                    filters={"query": (placeholder,)},
                    include_repository=True,
                )["sessions"],
                [],
            )

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
