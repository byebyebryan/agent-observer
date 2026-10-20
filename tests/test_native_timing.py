"""Production normalization, receipt ownership, replacement and clock limits."""

import copy
import unittest

from test_service_state import provider_snapshot

from agent_observer import timing
from agent_observer.contract import ContractError, validate_snapshot
from agent_observer.read_cache import ReadCache
from agent_observer.service_contract import validate_frame
from agent_observer.service_state import ServiceState


def turn(*, identifier="native-turn", status="inProgress", start=10, end=None, duration=None):
    return {"data": [{"id": identifier, "status": status, "startedAt": start,
                      "completedAt": end, "durationMs": duration, "itemsView": "notLoaded", "items": []}]}


class NativeTimingTest(unittest.TestCase):
    def test_native_units_duration_and_nullable_identity(self):
        record = timing.codex_turn(turn(identifier=None, status="completed", end=11, duration=1251), observed_at=12000)
        self.assertEqual(record["value"], {"id": None, "status": "completed", "startedAt": 10000,
                                         "completedAt": 11000, "durationMs": 1251, "timestampPrecisionMs": 1000})
        self.assertIsNone(record["receipt"])

    def test_all_terminal_and_unknown_statuses(self):
        for native, normalized in (("completed", "completed"), ("failed", "failed"), ("interrupted", "cancelled"), ("future", "unknown")):
            with self.subTest(status=native):
                self.assertEqual(timing.codex_turn(turn(status=native, end=11), observed_at=12000)["value"]["status"], normalized)

    def test_known_empty_and_missing_clocks_are_current_metadata(self):
        self.assertEqual(timing.codex_turn({"data": []}, observed_at=12000)["health"], "current")
        record = timing.codex_turn(turn(start=None), observed_at=12000)
        self.assertIsNone(record["value"]["startedAt"])
        self.assertEqual(record["health"], "current")
        self.assertIsNone(record["value"]["timestampPrecisionMs"])

    def test_bad_timing_is_rejected_without_including_payload(self):
        cases = [turn(start=True), turn(start=-1), turn(end=9), turn(end=11),
                 turn(duration=123), turn(identifier="bad\n"), turn(status="completed", duration=True),
                 turn(status="completed", duration=-1), turn(start=4_000_000_001)]
        content = turn()
        content["data"][0]["items"] = [{"private": "secret"}]
        cases.append(content)
        for value in cases:
            with self.subTest(value=value):
                record = timing.codex_turn(value, observed_at=12000)
                self.assertEqual(record["health"], "unavailable")
                self.assertIsNone(record["value"])
                self.assertNotIn("secret", str(record))

    def test_update_is_separate_and_invalid_bool_is_not_clock(self):
        self.assertEqual(timing.codex_updated({"updatedAt": 20}, observed_at=21000)["at"], 20000)
        self.assertEqual(timing.codex_updated({}, observed_at=21000)["health"], "current")
        self.assertEqual(timing.codex_updated({"updatedAt": True}, observed_at=21000)["health"], "unavailable")

    def test_unsaved_clock_is_not_last_known_or_current(self):
        native = {"lastUpdated": timing.codex_updated({"updatedAt": 20}, observed_at=21000),
                  "timingObservedBoottimeMs": {"lastUpdated": 110}}
        result = timing.project(native, "lastUpdated", saved=False,
                                origin={"component": "runtime", "sampledBoottimeMs": 100})
        self.assertEqual(result["health"], "unsupported")
        self.assertIsNone(result["at"])
        self.assertNotIn("lastKnownAt", timing.stale(result, "lastUpdated", "expired"))

    def test_source_wall_baseline_ticks_by_boottime_only(self):
        record = timing.codex_updated({"updatedAt": 20}, observed_at=21000)
        record["receipt"] = {"component": "runtime", "sampledBoottimeMs": 100,
                             "observedBoottimeMs": 110, "contextGeneration": 1}
        self.assertEqual(timing.age_ms(record, record["at"], now_boottime_ms=2110), 3000)
        self.assertIsNone(timing.age_ms(record, 22000, now_boottime_ms=2110))
        self.assertIsNone(timing.age_ms(record, record["at"], now_boottime_ms=109))
        self.assertEqual(record["at"], 20000)

    def test_non_atomic_join_suppresses_false_ongoing_timer(self):
        row = provider_snapshot("codex")["sessions"][0]
        row["runtime"].update(value="running", health="current")
        row["phase"].update(value="working", health="current", observedAt=12000)
        row["latestTurn"] = timing.codex_turn(turn(), observed_at=13000)
        self.assertEqual(timing.ongoing_turn_age_ms(row), 3000)
        row["phase"]["value"] = "blocked"
        self.assertEqual(timing.ongoing_turn_age_ms(row), 3000)
        row["phase"]["value"] = "waiting"
        self.assertIsNone(timing.ongoing_turn_age_ms(row))
        row["phase"]["value"] = "working"
        row["latestTurn"] = timing.codex_turn(turn(status="completed", end=11), observed_at=13000)
        self.assertIsNone(timing.ongoing_turn_age_ms(row))
        row["latestTurn"] = timing.codex_turn(turn(start=14), observed_at=15000)
        self.assertIsNone(timing.ongoing_turn_age_ms(row))


class TimingLeaseTest(unittest.TestCase):
    def setUp(self):
        self.now = 15000
        self.value = provider_snapshot("codex")
        self.value["sessions"] = [self.value["sessions"][0]]
        self.value["sessions"][0]["hasSavedHistory"] = True
        source = self.value["sources"][0]
        self.state = ServiceState(host_scope="fixture", configs={"codex": (source["configHome"], source["configHomeKind"])},
                                  uid=1000, clock=lambda: self.now,
                                  boot_id="11111111-1111-1111-1111-111111111111", clock_domain="time:[123]")

    def sample(self, component, *, payload=None, updated=12, ttl=10000, runtime_ttl=None, sample=None):
        value = copy.deepcopy(self.value)
        sample = self.now if sample is None else sample
        row = value["sessions"][0]
        row["lastUpdated"] = timing.codex_updated({"updatedAt": updated}, observed_at=20000)
        row["latestTurn"] = timing.codex_turn(turn() if payload is None else payload, observed_at=20000)
        for name in ("lastUpdated", "latestTurn"):
            row[name]["receipt"] = {"component": component, "sampledBoottimeMs": sample,
                                    "observedBoottimeMs": self.now, "contextGeneration": 0}
        value["sources"][0]["capabilities"]["timing"] = {"lastUpdated": True, "latestTurn": True}
        self.state.attempt("codex", component)
        self.state.accept("codex", component, value, sampled_ms=sample, ttl_ms=ttl, runtime_ttl_ms=runtime_ttl)
        return self.state.snapshot["sessions"][0]

    def test_history_coupling_publishes_once_keeps_real_origin(self):
        before = self.state.revision
        row = self.sample("history", ttl=10000, runtime_ttl=1000)
        self.assertEqual(self.state.revision, before + 1)
        self.assertEqual(row["latestTurn"]["receipt"]["component"], "history")
        self.now += 1001
        frame = self.state.frame("view", 1)
        row = frame["snapshot"]["sessions"][0]
        self.assertEqual(row["runtime"]["value"], "unknown")
        self.assertEqual(row["latestTurn"]["health"], "current")
        self.assertIsNone(timing.ongoing_turn_age_ms(row))

    def test_new_missing_and_expired_turn_never_restore_old_completion(self):
        self.sample("history", payload=turn(status="completed", end=11))
        self.now += 100
        row = self.sample("runtime", payload=turn(identifier="new", start=None), ttl=1000)
        self.assertEqual(row["latestTurn"]["value"]["id"], "new")
        self.assertIsNone(row["latestTurn"]["value"]["startedAt"])
        self.now += 1001
        row = self.state.frame("view", 1)["snapshot"]["sessions"][0]
        self.assertIsNone(row["latestTurn"]["value"])
        self.assertEqual(row["latestTurn"]["lastKnownValue"]["id"], "new")

    def test_new_known_empty_and_failed_reads_supersede_old_terminal(self):
        for payload in ({"data": []}, {"data": "bad"}):
            self.setUp()
            self.sample("history", payload=turn(status="completed", end=11))
            self.now += 100
            row = self.sample("runtime", payload=payload, ttl=1000)
            self.assertIsNone(row["latestTurn"]["value"])
            self.now += 1001
            row = self.state.frame("view", 1)["snapshot"]["sessions"][0]
            self.assertIsNone(row["latestTurn"]["value"])
            self.assertNotIn("lastKnownValue", row["latestTurn"])

    def test_older_event_clock_from_newer_sample_wins(self):
        self.sample("history", updated=17)
        self.now += 100
        row = self.sample("runtime", updated=12)
        self.assertEqual(row["lastUpdated"]["at"], 12000)

    def test_cache_uses_each_timing_origin_and_heartbeat_cannot_extend(self):
        self.sample("history", ttl=10000, runtime_ttl=1000)
        frame = self.state.frame("view", 1)
        cache = ReadCache(host_scope="fixture", uid=1000, boot_id=self.state.boot_id, clock_domain=self.state.clock_domain)
        cache.accept(frame, now_ms=self.now)
        self.now += 1001
        row = cache.current(self.now)["snapshot"]["sessions"][0]
        self.assertEqual(row["latestTurn"]["health"], "current")
        self.assertEqual(row["runtime"]["value"], "unknown")
        cache.accept(self.state.frame("heartbeat", 2), now_ms=self.now)
        self.now += 9000
        row = cache.current(self.now)["snapshot"]["sessions"][0]
        self.assertEqual(row["latestTurn"]["health"], "stale")
        self.assertEqual(row["latestTurn"]["receipt"], frame["snapshot"]["sessions"][0]["latestTurn"]["receipt"])

    def test_partial_missing_row_cannot_borrow_new_sample(self):
        self.sample("runtime")
        original = copy.deepcopy(self.state.snapshot["sessions"][0]["latestTurn"])
        self.now += 100
        value = copy.deepcopy(self.value)
        value["sessions"] = []
        value["sources"][0]["coverage"]["runtime"].update(status="partial", reason="bounded_census")
        self.state.attempt("codex", "runtime")
        self.state.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        row = self.state.frame("view", 1)["snapshot"]["sessions"][0]
        self.assertEqual(row["latestTurn"]["health"], "stale")
        self.assertEqual(row["latestTurn"]["receipt"], original["receipt"])

    def test_service_rejects_receipt_tampering_and_direct_current_timing(self):
        self.sample("runtime")
        good = self.state.frame("view", 1)
        mutations = [lambda r: r.update(receipt=None),
                     lambda r: r["receipt"].update(sampledBoottimeMs=self.now - 1),
                     lambda r: r["receipt"].update(contextGeneration=99),
                     lambda r: r["receipt"].update(observedBoottimeMs=self.now + 1)]
        for mutate in mutations:
            value = copy.deepcopy(good)
            mutate(value["snapshot"]["sessions"][0]["latestTurn"])
            with self.assertRaises(ContractError):
                validate_frame(value)

    def test_bad_worker_binding_leaves_accepted_state_unchanged(self):
        self.sample("runtime")
        before = copy.deepcopy(self.state.snapshot)
        value = copy.deepcopy(self.value)
        value["sessions"][0]["latestTurn"]["receipt"] = {"component": "history", "sampledBoottimeMs": self.now,
                                                       "observedBoottimeMs": self.now, "contextGeneration": 0}
        value["sessions"][0]["latestTurn"]["observedAt"] = 20000
        with self.assertRaises(ContractError):
            self.state.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        self.assertEqual(self.state.snapshot, before)

    def test_equal_observation_conflict_is_ambiguous(self):
        self.sample("runtime", updated=12)
        row = self.sample("history", updated=13)
        # Coupling replaces the runtime receipt with this exact history job;
        # independently tied records remain subject to the pure conflict rule.
        one, two = copy.deepcopy(row["lastUpdated"]), copy.deepcopy(row["lastUpdated"])
        two["at"] += 1000
        self.assertEqual(timing.select([(one, 25000), (two, 35000)], "lastUpdated")["health"], "ambiguous")

    def test_contract_rejects_wrong_precision_stale_values_and_extra_payload(self):
        self.sample("runtime")
        good = self.state.snapshot
        mutations = [lambda r: r["lastUpdated"].update(timestampPrecisionMs=None),
                     lambda r: r["latestTurn"].update(health="stale"),
                     lambda r: r["latestTurn"]["value"].update(completedAt=20000),
                     lambda r: r["latestTurn"]["value"].update(items=[])]
        for mutate in mutations:
            value = copy.deepcopy(good)
            mutate(value["sessions"][0])
            with self.assertRaises(ContractError):
                validate_snapshot(value)
