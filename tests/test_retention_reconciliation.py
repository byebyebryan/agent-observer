"""Behavioral parity with a11 full scans and a quiet-tick work regression."""

import copy
import random
import unittest
from unittest.mock import patch
from uuid import UUID

from agent_observer.contract import ContractError, identity_key, validate_snapshot
from agent_observer.service_state import ServiceState
from test_runtime_only_retention import missing, unsaved
from test_service_contract import fixture
from test_service_state import provider_snapshot


class FullScanReference(ServiceState):
    # Frozen a11 oracle from 37ccc53; compatibility code exists only in tests.
    def _retire_runtime_only(self, now):
        changed = False
        for provider, receipts in self.receipts.items():
            runtime = receipts["runtime"]
            saved = {identity_key(row["identity"]) for receipt in receipts.values()
                     if receipt.data for row in receipt.data["sessions"]
                     if row["hasSavedHistory"]}
            current = {identity_key(row["identity"])
                       for row in (runtime.data or {}).get("sessions", [])
                       if "retained_after_gap" not in row["metadataIssues"]}
            if not runtime.current():
                current.clear()
            retention = self.retention[provider]
            protected = saved | current
            for receipt in receipts.values():
                if receipt.data is None:
                    continue
                rows = receipt.data["sessions"]
                receipt.data["sessions"] = [row for row in rows
                    if identity_key(row["identity"]) in protected
                    or not retention.expired(row, now)]
                changed = changed or len(rows) != len(receipt.data["sessions"])
            retention.prune(runtime.data["sessions"] if runtime.data else [])
        return changed



class RetentionReconciliationTest(unittest.TestCase):
    def setUp(self):
        self.now = 15000
        frame = fixture()
        self.kwargs = dict(host_scope="fixture", uid=1000,
            configs={s["provider"]: (s["configHome"], s["configHomeKind"])
                     for s in frame["snapshot"]["sources"]},
            clock=lambda: self.now, boot_id=frame["bootId"], clock_domain=frame["clockDomain"])
        self.state = self.make_state(ServiceState)
        self.reference = self.make_state(FullScanReference)

    def make_state(self, cls):
        state = cls(**self.kwargs)
        state.wall_clock = lambda: 1700000000000 + self.now
        state.collection_id = lambda: "11111111-1111-1111-1111-111111111111"
        state.native_hostname = "fixture-native"
        return state

    def compare(self):
        self.assertEqual(self.state.snapshot, self.reference.snapshot)
        self.assertEqual(self.state.revision, self.reference.revision)
        self.assertEqual(self.state.contexts, self.reference.contexts)
        self.assertEqual(self.state.context_samples, self.reference.context_samples)
        self.assertEqual(self.state.generations, self.reference.generations)
        for provider in self.kwargs["configs"]:
            self.assertEqual(self.state.source_meta(provider), self.reference.source_meta(provider))
            self.assertEqual(self.state.retention[provider].deadlines,
                             self.reference.retention[provider].deadlines)
            for component in ("runtime", "history"):
                self.assertEqual(self.state.receipts[provider][component].data,
                                 self.reference.receipts[provider][component].data)

    def accept(self, value, *, component="runtime", sampled=None, ttl=1000, runtime_ttl=1000):
        provider = value["sources"][0]["provider"]
        results = []
        for state in (self.state, self.reference):
            state.attempt(provider, component)
            results.append(state.accept(provider, component, value,
                sampled_ms=self.now if sampled is None else sampled, ttl_ms=ttl,
                runtime_ttl_ms=runtime_ttl))
        self.assertEqual(*results)
        self.compare()

    def test_saved_idle_ticks_do_not_repeat_roster_identity_validation(self):
        for provider in ("codex", "claude"):
            self.accept(provider_snapshot(provider), component="history", ttl=10000, runtime_ttl=10000)
        before = copy.deepcopy(self.state.snapshot)
        # Guard the measured expensive operation, not a particular cache design.
        with patch("agent_observer.observation_engine.identity_key",
                   side_effect=AssertionError("quiet tick revalidates the roster")):
            for _ in range(2000):
                self.now += 1
                self.assertFalse(self.state.expire())
        self.assertEqual(self.state.snapshot, before)
        self.reference.expire()
        self.compare()

    def test_future_unsaved_deadline_is_quiet_until_exact_retirement(self):
        original = unsaved()
        self.accept(original, ttl=100)
        self.now += 20
        self.accept(missing(original), ttl=10000)
        with patch("agent_observer.observation_engine.identity_key",
                   side_effect=AssertionError("future deadline scans the roster")):
            for _ in range(79):
                self.now += 1
                self.assertFalse(self.state.expire())
        self.reference.expire()
        self.compare()
        self.assertEqual(len(self.state.snapshot["sessions"]), 1)
        self.now += 1
        self.assertEqual(self.state.expire(), self.reference.expire())
        self.compare()
        self.assertEqual(self.state.snapshot["sessions"], [])

    def test_rejected_identity_cannot_bypass_admission_or_invalidate_owned_data(self):
        self.accept(provider_snapshot("codex"))
        invalid = provider_snapshot("codex")
        invalid["sessions"][0]["identity"]["nativeId"] = "not-a-thread-id"
        for state in (self.state, self.reference):
            with self.assertRaises(ContractError):
                state.accept("codex", "runtime", invalid, sampled_ms=self.now, ttl_ms=1000)
        self.compare()
        with patch("agent_observer.observation_engine.identity_key",
                   side_effect=AssertionError("rejected input dirtied unchanged data")):
            self.assertFalse(self.state.expire())

    def test_seeded_mixed_provider_replacements_failures_and_expiry_match_full_scans(self):
        for seed in range(10):
            with self.subTest(seed=seed):
                self.now = 15000
                self.state = self.make_state(ServiceState)
                self.reference = self.make_state(FullScanReference)
                randomizer = random.Random(seed)
                epochs = {"codex": 1, "claude": 1}
                for step in range(120):
                    self.now += randomizer.choice((0, 1, 3, 10, 30, 101))
                    provider = randomizer.choice(("codex", "claude"))
                    component = randomizer.choice(("runtime", "history"))
                    operation = randomizer.randrange(10)
                    if operation < 6:
                        value = provider_snapshot(provider)
                        prototype = copy.deepcopy(value["sessions"][0])
                        value["sessions"] = []
                        for index in range(3):
                            if randomizer.randrange(3) == 0:
                                continue
                            row = copy.deepcopy(prototype)
                            row["identity"]["nativeId"] = str(UUID(int=100 + index))
                            row["nativeIds"]["threadId" if provider == "codex" else "sessionId"] = row["identity"]["nativeId"]
                            row["title"] = f"Fixture {index} {step}"
                            row["hasSavedHistory"] = bool(randomizer.randrange(2))
                            row["inventory"] = "saved" if row["hasSavedHistory"] else "live"
                            if randomizer.randrange(4) == 0:
                                row["metadataIssues"] += ["retained_after_gap"]
                            row["activity"] = {
                                "at": 1700000000000 + self.now, "health": "current",
                                "reason": "native_conversation_event",
                                "source": "codex_turn_metadata" if provider == "codex" else "claude_transcript_message"}
                            value["sessions"].append(row)
                        for dimension in ("runtime", "saved"):
                            value["sources"][0]["coverage"][dimension].update(
                                status=randomizer.choice(("complete", "partial", "unavailable")),
                                reason="fixture_trace")
                        if provider == "codex":
                            if randomizer.randrange(7) == 0:
                                epochs[provider] += 1
                            value["sources"][0]["runtime"] = {
                                "version": "diagnostic", "binarySha256": "a" * 64,
                                "topology": "native_managed_endpoint", "bootId": self.state.boot_id,
                                "pid": 123, "startTicks": epochs[provider], "endpoint": "/fixture/endpoint"}
                        self.accept(validate_snapshot(value), component=component,
                            sampled=self.now - randomizer.choice((0, 0, 1, 10, 100)),
                            ttl=randomizer.choice((1, 10, 100, 10000)),
                            runtime_ttl=randomizer.choice((1, 10, 100)))
                    elif operation == 6:
                        for state in (self.state, self.reference):
                            state.fail(provider, component, "fixture_failure")
                    elif operation == 7:
                        self.assertEqual(self.state.expire(), self.reference.expire())
                    elif operation == 8:
                        for state in (self.state, self.reference):
                            state.frame("heartbeat", step + 1)
                    else:
                        for state in (self.state, self.reference):
                            state.attempt(provider, component)
                    self.compare()


if __name__ == "__main__":
    unittest.main()
