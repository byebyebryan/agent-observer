"""Strict opt-in replacement grammar, union proof and clock continuity."""

import copy
import json
import unittest
from pathlib import Path
from unittest.mock import patch

from projection_fixture import fixture as active_fixture
from projection_fixture import support

from agent_observer.contract import ContractError, canonical, validate_snapshot
from agent_observer.working_set_contract import (
    MAX_SAFE_INTEGER,
    MAX_WORKING_SET_NODES,
    StreamGuard,
    interface,
    parse_frame,
    parse_request,
    selector,
    selector_digest,
    validate_frame,
    validate_request,
)
from agent_observer.working_set_supports import (
    compact_scope,
    resolve_coverage,
    resolve_member,
    resolve_nonmember,
    resolve_uncertain,
)


def expand_scope(scope):
    result = {
        key: value
        for key, value in scope.items()
        if key != "supportTable"
    }
    result["coverage"] = resolve_coverage(scope, scope["coverage"])
    result["members"] = [resolve_member(scope, entry) for entry in scope["members"]]
    result["uncertain"] = [resolve_uncertain(scope, entry) for entry in scope["uncertain"]]
    result["nonmembers"] = [resolve_nonmember(scope, entry) for entry in scope["nonmembers"]]
    return result


def fixture(*, recent=False, active=True, window=10000):
    value = active_fixture()
    value.pop("activeFeedProtocol")
    policy = selector(window)
    value.update(
        workingSetProtocol=1,
        selector=policy,
        selectorDigest=selector_digest(policy),
        observationRevision=value["viewRevision"],
        clockCeiling=None,
        clockGeneration=0,
    )
    scope = value["projection"]["scopes"][0]
    scope["clocks"] = []
    member = scope["members"][0]
    member.update(active={"supports": [support(value)]} if active else None, recent=None)
    if recent:
        row = value["projection"]["sessions"][0]
        row["activity"].update(
            at=1700000019000, health="current", source="codex_rpc", reason="native_timestamp"
        )
        member["fieldSupports"]["activity"] = support(value)
        value["clockCeiling"] = 1700000020000 - 10000 + 1
        scope["clocks"] = [
            {
                "component": "runtime",
                "accepted": 1,
                "sampleId": "00000000-0000-0000-0000-000000000011",
                "originComponent": "history",
                "sampledBoottimeMs": 10000,
                "wallMs": 1700000020000,
                "acceptedBoottimeMs": 10001,
            }
        ]
        member["recent"] = {
            "supports": [support(value)],
            "activityAt": 1700000019000,
            "clock": {"component": "runtime", "accepted": 1},
            "lowerBoottimeMs": 18999,
            "upperBoottimeMs": 19002,
        }
        if not active:
            row["runtime"]["value"] = "parked"
            row["phase"] = None
            row["blockedReasons"] = []
            member["fieldSupports"]["phase"] = None
    scope = value["projection"]["scopes"][0]
    value["projection"]["scopes"][0] = compact_scope(scope)
    return value


def outside(value):
    scope = expand_scope(value["projection"]["scopes"][0])
    member = scope["members"].pop()
    value["projection"]["sessions"].clear()
    proof = member["recent"]
    scope["nonmembers"] = [
        {
            "identity": member["identity"],
            "reason": "outside_window",
            "value": "parked",
            "supports": [support(value)],
            "recent": {
                "kind": "outside_window",
                "support": support(value),
                "clock": proof["clock"],
                "activityAt": proof["activityAt"],
                "lowerBoottimeMs": proof["lowerBoottimeMs"],
                "upperBoottimeMs": proof["upperBoottimeMs"],
                "absence": None,
            },
            "horizonBoottimeMs": 20000,
        }
    ]
    value["projection"]["scopes"][0] = compact_scope(scope)
    return value["projection"]["scopes"][0]["nonmembers"][0]


class WorkingSetContractTest(unittest.TestCase):
    def test_compact_table_does_not_expand_existing_parser_node_budget(self):
        self.assertEqual(MAX_WORKING_SET_NODES, 2_004_096)

    def test_closed_policy_exact_types_and_bound_request(self):
        for window in (0, 259200000, 2592000000):
            policy = selector(window)
            request = {
                "workingSetProtocol": 1,
                "operation": "watch",
                "hostScope": "fixture",
                "selector": policy,
                "selectorDigest": selector_digest(policy),
            }
            self.assertEqual(
                parse_request((canonical(request) + "\n").encode(), expected_window_ms=window),
                request,
            )
            for mutate in (
                lambda v: v["selector"]["recent"].update(windowMs=True),
                lambda v: v["selector"].update(version=1.0),
                lambda v: v["selector"].update(kinds=["user"]),
                lambda v: v.update(selectorDigest="sha256:" + "0" * 64),
                lambda v: v.update(predicate="all"),
            ):
                bad = copy.deepcopy(request)
                mutate(bad)
                with self.subTest(window=window, bad=bad), self.assertRaises(ContractError):
                    validate_request(bad)
            with self.assertRaises(ContractError):
                validate_request(request, expected_window_ms=window + 1)
        for window in (True, -1, 2592000001, 72.0):
            with self.assertRaises(ContractError):
                selector(window)
        public = interface()
        public["selector"]["providers"].clear()
        self.assertEqual(interface()["selector"]["providers"], ["codex"])

    def test_active_recent_or_both_and_actual_parked_body(self):
        for recent, active in ((False, True), (True, False), (True, True)):
            value = fixture(recent=recent, active=active)
            wire = (canonical(value) + "\n").encode()
            self.assertEqual(
                parse_frame(
                    wire, expected_host="fixture", expected_uid=1000, expected_window_ms=10000
                ),
                value,
            )
        bad = fixture(active=False)
        with self.assertRaisesRegex(ContractError, "positive_missing"):
            validate_frame(bad)

    def test_recent_requires_exact_receipt_clock_sample_and_conservative_bound(self):
        for mutate in (
            lambda v: v.update(clockCeiling=None),
            lambda v: v.update(clockCeiling=v["clockCeiling"] - 1),
            lambda v: v["projection"]["scopes"][0]["clocks"].append(
                copy.deepcopy(v["projection"]["scopes"][0]["clocks"][0])
            ),
            lambda v: v["projection"]["scopes"][0]["clocks"][0].update(accepted=2),
            lambda v: v["projection"]["scopes"][0]["clocks"][0].update(acceptedBoottimeMs=16000),
            lambda v: v["projection"]["scopes"][0]["members"][0]["recent"].update(
                lowerBoottimeMs=19000
            ),
            lambda v: v["projection"]["scopes"][0]["members"][0]["recent"]["clock"].update(
                component="history"
            ),
            lambda v: v["projection"]["scopes"][0]["members"][0]["recent"].update(supports=[]),
            lambda v: v.update(emittedBoottimeMs=18999),
        ):
            bad = fixture(recent=True)
            mutate(bad)
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                validate_frame(bad)
        value = fixture(recent=True)
        value["clockCeiling"] += 100
        value["projection"]["scopes"][0]["members"][0]["recent"]["lowerBoottimeMs"] -= 100
        validate_frame(value)

    def test_expired_recent_can_leave_independent_active_branch_and_complete_scope(self):
        value = fixture(recent=True)
        value["emittedBoottimeMs"] = 19000
        member = value["projection"]["scopes"][0]["members"][0]
        member["recent"] = None
        validate_frame(value)
        member["active"] = None
        with self.assertRaisesRegex(ContractError, "positive_missing"):
            validate_frame(value)

    def test_outside_window_cannot_use_positive_or_early_boundary(self):
        value = fixture(recent=True, active=False)
        entry = outside(value)
        value["emittedBoottimeMs"] = 19002
        validate_frame(value)
        for mutate in (
            lambda v, e: v.update(emittedBoottimeMs=19001),
            lambda v, e: e.update(value="child"),
            lambda v, e: e.update(supports=[]),
            lambda v, e: e["recent"].update(upperBoottimeMs=19001),
                lambda v, e: v["projection"]["scopes"][0]["supportTable"][
                    e["recent"]["support"]
                ].update(component="history"),
        ):
            bad = copy.deepcopy(value)
            mutate(bad, bad["projection"]["scopes"][0]["nonmembers"][0])
            with self.subTest(bad=bad), self.assertRaises(ContractError):
                validate_frame(bad)
        self.assertEqual(entry["recent"]["upperBoottimeMs"], 19002)

    def test_signed_cutoffs_cannot_escape_safe_range(self):
        value = fixture(recent=True)
        value["clockCeiling"] = -MAX_SAFE_INTEGER
        value["projection"]["scopes"][0]["clocks"].clear()
        with self.assertRaises(ContractError):
            validate_frame(value)

    def test_no_activity_carries_typed_original_absence_and_timing_binding(self):
        value = fixture(recent=True, active=False)
        entry = outside(value)
        recent = entry["recent"]
        entry["reason"] = "no_activity"
        recent.update(
            kind="no_activity",
            activityAt=None,
            lowerBoottimeMs=None,
            upperBoottimeMs=None,
            absence={
                "field": "latestTurn",
                "activity": {
                    "at": None,
                    "source": None,
                    "health": "unavailable",
                    "reason": "no_conversation_activity",
                },
                "latestTurn": {
                    "value": None,
                    "observedAt": 1700000020000,
                    "source": "codex_rpc",
                    "health": "current",
                    "reason": "no_native_turn",
                    "receipt": {
                        "component": "runtime",
                        "sampledBoottimeMs": 10000,
                        "observedBoottimeMs": 10001,
                        "contextGeneration": 1,
                    },
                },
            },
        )
        validate_frame(value)
        for mutate in (
            lambda r: r.update(absence=None),
            lambda r: r["absence"].update(field="activity"),
            lambda r: r["absence"]["activity"].update(reason="metadata_unavailable"),
            lambda r: r["absence"]["latestTurn"].update(reason="native_turn_content_rejected"),
            lambda r: r["absence"]["latestTurn"].update(source=None),
            lambda r: r["absence"]["latestTurn"].update(health="stale"),
            lambda r: r["absence"]["latestTurn"]["receipt"].update(component="history"),
            lambda r: r["absence"]["latestTurn"]["receipt"].update(observedBoottimeMs=10002),
        ):
            bad = copy.deepcopy(value)
            mutate(bad["projection"]["scopes"][0]["nonmembers"][0]["recent"])
            with self.subTest(mutate=mutate), self.assertRaises(ContractError):
                validate_frame(bad)

    def test_unknown_context_never_proves_complete_and_keeps_prior_horizon(self):
        value = fixture()
        scope = expand_scope(value["projection"]["scopes"][0])
        row = value["projection"]["sessions"].pop()
        scope["members"].clear()
        scope["uncertain"] = [
            {
                "identity": row["identity"],
                "reason": "activity_unresolved",
                "priorSupport": support(value),
                "support": None,
                "horizonBoottimeMs": 20000,
            }
        ]
        value["projection"]["scopes"][0] = compact_scope(scope)
        with self.assertRaisesRegex(ContractError, "complete_unresolved"):
            validate_frame(value)
        scope = expand_scope(value["projection"]["scopes"][0])
        scope["coverage"].update(status="partial", supports=[])
        value["projection"]["scopes"][0] = compact_scope(scope)
        validate_frame(value)
        value["projection"]["scopes"][0]["uncertain"][0]["horizonBoottimeMs"] = 20001
        with self.assertRaisesRegex(ContractError, "uncertain_horizon"):
            validate_frame(value)

    def test_body_semantics_and_original_full_capability_validation_remain_strict(self):
        for mutate in (
            lambda r: r.update(cwd="relative"),
            lambda r: r["nativeIds"].update(threadId="00000000-0000-0000-0000-000000000099"),
            lambda r: r.update(blockedReasons=[]),
            lambda r: r["phase"].update(observedAt=1),
            lambda r: r.update(prompt="forbidden"),
        ):
            value = fixture()
            mutate(value["projection"]["sessions"][0])
            with self.assertRaises(ContractError):
                validate_frame(value)
        path = Path(__file__).parent / "fixtures/service-v4/view.json"
        snapshot = json.loads(path.read_text())["snapshot"]
        row = snapshot["sessions"][0]
        row["lastUpdated"].update(
            at=1700000010000,
            timestampPrecisionMs=1000,
            observedAt=1700000020000,
            source="codex_rpc",
            health="current",
        )
        with self.assertRaisesRegex(ContractError, "timing_capability_missing"):
            validate_snapshot(snapshot)

    def test_control_correspondence_and_frame_budgets(self):
        for kind in ("status", "heartbeat", "gap", "error"):
            value = {**fixture(), "kind": kind, "projection": None}
            validate_frame(value)
        for mutate in (
            lambda v: v.update(kind="heartbeat"),
            lambda v: v.update(projection=None),
            lambda v: v["projection"]["sessions"].clear(),
            lambda v: v["projection"]["scopes"][0]["members"].clear(),
            lambda v: v["projection"]["sessions"][0]["identity"].update(hostScope="elsewhere"),
        ):
            value = fixture()
            mutate(value)
            with self.assertRaises(ContractError):
                validate_frame(value)
        for limit in ("MAX_LEDGER_BYTES", "MAX_OVERHEAD_BYTES", "MAX_FRAME_BYTES"):
            with patch("agent_observer.working_set_contract." + limit, 100):
                with self.assertRaises(ContractError):
                    validate_frame(fixture())
        wire = (canonical(fixture()) + "\n").encode()
        for malformed in (wire[:-1], wire + wire):
            with self.assertRaises(ValueError):
                parse_frame(malformed)

    def test_stream_keeps_ceiling_and_both_revisions_across_context_and_gaps(self):
        value = fixture(recent=True)
        guard = StreamGuard(expected_window_ms=10000)
        guard.accept(value)
        for change in (
            {"clockCeiling": value["clockCeiling"] - 1, "projection": None, "kind": "heartbeat"},
            {"clockCeiling": None, "projection": None, "kind": "heartbeat"},
            {"observationRevision": 0},
            {"viewRevision": 0},
            {"emittedBoottimeMs": 14999},
            {"serviceId": "00000000-0000-0000-0000-000000000099"},
        ):
            bad = {**value, "sequence": 2, **change}
            with self.subTest(change=change), self.assertRaises(ContractError):
                guard.accept(bad)
        changed = copy.deepcopy(value)
        changed["sequence"] = 2
        changed["projection"]["sessions"][0]["title"] = "different"
        with self.assertRaisesRegex(ContractError, "revision_reused"):
            guard.accept(changed)
        guard.accept({**value, "sequence": 2, "kind": "gap", "projection": None})
        with self.assertRaisesRegex(ContractError, "resync_required"):
            guard.accept({**value, "sequence": 3, "kind": "heartbeat", "projection": None})
        guard.accept({**value, "sequence": 3, "kind": "resync"})
        stepped = {
            **value,
            "sequence": 4,
            "viewRevision": 2,
            "clockGeneration": 1,
            "kind": "heartbeat",
            "projection": None,
        }
        guard.accept(stepped)
        with self.assertRaisesRegex(ContractError, "clock_regression"):
            guard.accept({**stepped, "sequence": 5, "clockGeneration": 0})
