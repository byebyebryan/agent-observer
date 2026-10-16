"""Owner sync generations checked against detached native exports and hash replay."""

import copy
import gc
import hashlib
import json
import unittest
from unittest.mock import patch

from test_service_state import provider_snapshot

from agent_observer.contract import ContractError, identity_key
from agent_observer.service_state import ServiceState
from agent_observer.sync_commitment import (
    BudgetExceeded,
    body_id,
    canonical,
    descriptor_digest,
    freeze,
    native_root,
    thaw,
)
from agent_observer.sync_contract import field_tokens
from agent_observer.sync_native import parse_message
from agent_observer.sync_state import SPACES, OwnerSyncCache

BOOT = "00000000-0000-4000-8000-000000000002"


def _frame(value):
    return len(value).to_bytes(8, "big") + value


def _root(space, rows):
    """Independent full Patricia rebuild, without PersistentMap internals."""
    space = _frame(space.encode())
    leaves = []
    for key, value in rows.items():
        key_hash = hashlib.sha256(b"mesh-sync-key\0" + space + _frame(key)).digest()
        value_hash = hashlib.sha256(b"mesh-sync-value\0" + space + _frame(canonical(value))).digest()
        leaf = hashlib.sha256(b"mesh-sync-leaf\0" + space + key_hash + _frame(key) + value_hash).digest()
        leaves.append((int.from_bytes(key_hash, "big"), leaf))
    leaves.sort()

    def build(items):
        if len(items) == 1:
            return items[0][1]
        bit = 256 - (items[0][0] ^ items[-1][0]).bit_length()
        prefix_size = (bit + 7) // 8
        prefix = ((items[0][0] >> (256 - bit)) << (prefix_size * 8 - bit)).to_bytes(prefix_size, "big")
        boundary = next(i for i, (key, _) in enumerate(items) if key & (1 << (255 - bit)))
        return hashlib.sha256(b"mesh-sync-branch\0" + space + bit.to_bytes(2, "big") + _frame(prefix)
                              + build(items[:boundary]) + build(items[boundary:])).digest()

    return (build(leaves) if leaves else hashlib.sha256(b"mesh-sync-empty\0" + space).digest()).hex()


class Replay:
    def __init__(self, baseline):
        self.binding = baseline["nativeBinding"]
        self.tables = {s: {canonical(k): v for k, v in baseline["tables"][s]} for s in SPACES}
        self.tag = baseline["tag"]

    def apply(self, transaction):
        assert transaction["baseTag"] == self.tag
        for space, operations in transaction["operations"].items():
            for operation in operations:
                kind, key, expected, *replacement = operation
                key = canonical(key)
                prior = self.tables[space].get(key)
                digest = None if prior is None else hashlib.sha256(
                    b"mesh-sync-value\0" + _frame(space.encode()) + _frame(canonical(prior))).hexdigest()
                assert digest == expected, (space, kind)
                if kind == "put":
                    self.tables[space][key] = replacement[0]
                else:
                    del self.tables[space][key]
        self.tag = transaction["resultTag"]

    def check(self, test):
        summary = [[s, _root(s, self.tables[s]), len(self.tables[s])] for s in sorted(SPACES)]
        test.assertEqual(native_root(self.binding, self.tag[1], summary, expected_spaces=SPACES), self.tag[2])


class SyncStateTest(unittest.TestCase):
    def setUp(self):
        self.now = 15000
        self.state = ServiceState(
            host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")},
            uid=1000, clock=lambda: self.now, boot_id=BOOT, clock_domain="time:[123]",
        )
        # Keep an independent frozen-tree oracle while production sync uses
        # canonical-byte tables. The subclass runs every case on that backend.
        self.state._sync_cache = OwnerSyncCache(self.state, backend="frozen")

    def accept(self, value=None, component="runtime"):
        self.now += 1
        self.state.attempt("codex", component)
        self.state.accept("codex", component, value or provider_snapshot("codex"),
                          sampled_ms=self.now, ttl_ms=5000)

    def baseline(self, view):
        return parse_message(self.state.sync_baseline(view), view, "fixture")

    def test_warming_binds_configured_empty_scope_without_authority(self):
        for view in ("full", "active"):
            frame = self.baseline(view)
            Replay(frame).check(self)
            self.assertEqual(frame["tables"]["records"], [])
            self.assertEqual(frame["tables"]["cohorts"], [])
            if view == "active":
                self.assertEqual(len(frame["nativeBinding"]["scopeContinuity"]), 1)
            self.assertIsNone(self.state._sync_cache.export_committed(view))

    def test_replay_all_roots_and_exact_exports_across_reobservations(self):
        self.accept(component="history")
        self.accept()
        views = {view: Replay(self.baseline(view)) for view in ("full", "active")}
        for index in range(6):
            value = provider_snapshot("codex")
            # Include genuine per-row clock changes, not just receipt changes.
            for row in value["sessions"]:
                row["runtime"]["observedAt"] += index
                if row["phase"] is not None:
                    row["phase"]["observedAt"] += index
            self.accept(value)
            for view, replay in views.items():
                target = self.state.sync_current_tag(view)
                messages = self.state.sync_changes(view, replay.tag, target)
                self.assertIsInstance(messages, tuple)
                for raw in messages[:-1]:
                    replay.apply(parse_message(raw, view, "fixture"))
                replay.check(self)
                expected = self.state.snapshot if view == "full" else self.state.active_projection
                self.assertEqual(self.state._sync_cache.export_committed(view), expected)
                terminal = parse_message(messages[-1], view, "fixture")
                self.assertEqual(terminal["tag"], list(target))

    def test_owner_hashes_match_strict_public_body_and_all_field_tokens(self):
        value = provider_snapshot("codex")
        value["sessions"][0].update(title='é漢字🙂 "quoted" \\slash', cwd="/fixture/é漢字")
        self.accept(value)
        for view in ("full", "active"):
            frame = self.baseline(view)
            current = self.state._sync_cache.views[view].current
            descriptor = descriptor_digest(frame["descriptor"])
            for identity, slot in current.tables["records"].items():
                content = thaw(current.tables["bodies"].get(slot["body"]))
                self.assertEqual(slot["body"], body_id(descriptor, content))
                tokens = field_tokens(descriptor, thaw(identity), thaw(slot["birth"]), content)
                observations = current.tables["observations"].get([identity, slot["birth"]])
                for name, ref in observations["supports"].items():
                    if ref is not None and ref[0] == "cohort":
                        self.assertEqual(current.tables["memberships"].get(
                            [ref[1], identity, slot["birth"], name]), tokens[name])

    def test_body_metadata_change_reuses_exact_unchanged_field_memberships(self):
        from agent_observer.sync_state import _owned_hash

        self.accept(component="history")
        before = self.baseline("full")
        cache = self.state._sync_cache
        previous = cache.views["full"].current
        membership_root = previous.tables["memberships"].root
        body_root = previous.tables["bodies"].root
        value = provider_snapshot("codex")
        value["sessions"][0]["title"] = "new admitted display title"
        with patch("agent_observer.sync_state._owned_hash", wraps=_owned_hash) as hashing:
            self.accept(value, component="history")
        current = cache.views["full"].current
        self.assertNotEqual(current.tables["bodies"].root, body_root)
        self.assertEqual(current.tables["memberships"].root, membership_root)
        self.assertFalse(any(call.args[1] == b"mesh-sync-field\0" for call in hashing.call_args_list))
        replay = Replay(before)
        for raw in self.state.sync_changes("full", replay.tag, current.tag)[:-1]:
            replay.apply(parse_message(raw, "full", "fixture"))
        replay.check(self)
        self.assertEqual(cache.export_committed("full"), self.state.snapshot)

    def test_partial_subset_never_rebinds_retained_support(self):
        self.accept()
        before = self.baseline("full")
        identity = list(identity_key(self.state.snapshot["sessions"][0]["identity"]))
        prior = self.state._sync_cache.views["full"].current
        slot = prior.tables["records"].get(identity)
        original = copy.deepcopy(self.state.projection_support[tuple(identity)]["runtime"])
        value = provider_snapshot("codex")
        value["sessions"] = [r for r in value["sessions"] if identity_key(r["identity"]) != tuple(identity)]
        value["sources"][0]["coverage"]["runtime"].update(status="partial", reason="live_limit")
        self.accept(value)
        current = self.state._sync_cache.views["full"].current
        observed = current.tables["observations"].get([identity, slot["birth"]])
        self.assertEqual(thaw(observed["supports"]["runtime"]), ["context", original])
        self.assertFalse(any(list(k[1]) == identity for k, _ in current.tables["memberships"].items()))
        replay = Replay(before)
        for raw in self.state.sync_changes("full", replay.tag, current.tag)[:-1]:
            replay.apply(parse_message(raw, "full", "fixture"))
        replay.check(self)

    def test_heads_and_cached_baseline_do_not_normalize_or_expire(self):
        self.assertEqual(json.loads(self.state.sync_head("full", {"nonce": "cold"}))["status"], "baseline_required")
        self.accept()
        raw = self.state.sync_baseline("full")
        counts = dict(self.state._sync_cache.counts)
        self.now += 10000
        with patch.object(self.state, "expire", side_effect=AssertionError("query expiry")), \
                patch.object(self.state, "publish", side_effect=AssertionError("query publication")):
            self.assertIs(self.state.sync_baseline("full"), raw)
            head = parse_message(self.state.sync_head("full", {"nonce": "fresh"}), "full", "fixture")
        self.assertTrue(all(ms == 0 for _, ms in head["attenuation"]))
        self.assertEqual(self.state._sync_cache.counts["normalizations"], counts["normalizations"])

    def test_head_outputs_have_bounded_ownership_and_preflight_before_receipt_reads(self):
        self.accept()
        self.baseline("full")
        cache = self.state._sync_cache
        for index in range(40):
            self.state.sync_head("full", {"nonce": str(index)})
        self.assertEqual(len(cache.query_buffers), 16)
        self.assertEqual(cache.encoded_staged, 0)
        frame = next(iter(cache.query_buffers.values())).data
        pin = cache.pin_buffers((frame,))
        self.assertNotIn(id(frame), cache.query_buffers)
        self.assertIs(cache.account._held[id(frame)].value, frame)
        pin.release()
        self.assertNotIn(id(frame), cache.account._held)
        occupied = cache.account.limit - cache.account.snapshot()["used"] - 8191
        with cache.account.reserve(occupied, kind="stage"), \
                patch.object(type(cache.views["full"].current.tables["receipts"]), "items",
                             side_effect=AssertionError("receipt parse before heap credit")):
            with self.assertRaises(BudgetExceeded):
                self.state.sync_head("full", {"nonce": "pressure"})
        self.assertEqual(cache.encoded_staged, 0)

    def test_rejected_transaction_revokes_host_and_does_not_publish_staged_root(self):
        self.accept()
        self.baseline("full")
        old = self.state.sync_current_tag("full")
        self.state.sync_reserver = lambda size: False
        self.state.attempt("codex", "runtime")
        self.assertIsNone(self.state.sync_current_tag("full"))
        # With no encoding credit even a recovery control cannot be allocated.
        with self.assertRaises(ContractError):
            self.state.sync_head("full", {"nonce": "failed"})
        self.state.sync_reserver = None
        frame = json.loads(self.state.sync_head("full", {"nonce": "failed"}))
        self.assertEqual(frame["status"], "baseline_required")
        self.assertNotEqual(frame["tag"], list(old))
        self.state.sync_reserver = None
        self.accept()
        self.assertIsNotNone(self.state.sync_current_tag("full"))

    def test_attempt_diagnostics_are_bounded_and_history_promotion_is_atomic(self):
        self.accept()
        for view in ("full", "active"):
            self.baseline(view)
        cache = self.state._sync_cache
        before = {view: slot.current for view, slot in cache.views.items()}
        normalized = cache.counts["normalizations"]
        self.state.attempt("codex", "history")
        self.assertEqual(cache.counts["normalizations"], normalized)
        for view, old in before.items():
            current = cache.views[view].current
            self.assertIs(old.tables["records"], current.tables["records"])
            self.assertIs(old.tables["memberships"], current.tables["memberships"])
            self.assertEqual(current.tables["metadata"].get("service")["sources"][0]["components"][1]["inFlight"], True)
        publications = cache.counts["publications"]
        self.now += 1
        self.state.accept("codex", "history", provider_snapshot("codex"), sampled_ms=self.now, ttl_ms=5000)
        self.assertEqual(cache.counts["publications"], publications + 2)  # one atomic commit per enabled view

    def test_capacity_rebuild_preserves_births_generation_and_requires_explicit_baseline(self):
        self.accept()
        before = self.baseline("full")
        cache = self.state._sync_cache
        prior = cache.views["full"].current
        births = {tuple(key): (thaw(slot["birth"]), slot["alias"])
                  for key, slot in prior.tables["records"].items()}
        original, calls = cache._publish_staged, []

        def capacity_once(slot, stage, generation, **kwargs):
            calls.append(generation)
            if len(calls) == 1:
                raise BudgetExceeded("synthetic_stage_pressure")
            return original(slot, stage, generation, **kwargs)

        with patch.object(cache, "_publish_staged", side_effect=capacity_once):
            self.now += 1
            self.state.accept("codex", "runtime", provider_snapshot("codex"), sampled_ms=self.now, ttl_ms=5000)
        current = cache.views["full"].current
        self.assertEqual(calls, [before["tag"][1] + 1] * 2)
        self.assertEqual(current.generation, calls[0])
        self.assertEqual({tuple(key): (thaw(slot["birth"]), slot["alias"])
                          for key, slot in current.tables["records"].items()}, births)
        self.assertIsNone(cache.views["full"].previous)
        self.assertIsNone(cache.views["full"].seed)
        response = self.state.sync_changes("full", before["tag"], current.tag)
        self.assertEqual(json.loads(response)["status"], "baseline_required")
        Replay(self.baseline("full")).check(self)
        self.assertEqual(cache.export_committed("full"), self.state.snapshot)
        self.assertEqual(cache.counts["recoveries"], 1)

    def test_failed_rebuild_retains_bounded_births_but_prunes_actual_active_removals(self):
        value = provider_snapshot("codex")
        self.accept(value)
        self.baseline("active")
        cache = self.state._sync_cache
        slot = cache.views["active"]
        identity, prior = next(slot.current.tables["records"].items())
        birth, alias = thaw(prior["birth"]), prior["alias"]
        with patch.object(cache, "_publish_staged", side_effect=BudgetExceeded("synthetic_stage_pressure")) as stage:
            self.now += 1
            self.state.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=5000)
            self.assertEqual(stage.call_count, 2)
            self.assertIsNotNone(slot.seed)
            self.assertIsNone(slot.current)
            with self.assertRaises(ContractError):
                self.state.sync_baseline("active")
            self.state.attempt("codex", "runtime")
            self.assertEqual(stage.call_count, 2)  # no query or diagnostic rebuild
            parked = copy.deepcopy(value)
            for row in parked["sessions"]:
                row.update(phase=None, blockedReasons=[])
                row["runtime"]["value"] = "parked"
            self.now += 1
            self.state.accept("codex", "runtime", parked, sampled_ms=self.now, ttl_ms=5000)
            self.assertEqual(stage.call_count, 3)
            self.assertNotIn(freeze(identity), slot.seed.rows)
        self.now += 1
        self.state.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=5000)
        replacement = slot.current.tables["records"].get(identity)
        self.assertNotEqual(thaw(replacement["birth"]), birth)
        self.assertGreater(replacement["alias"], alias)
        self.assertIsNone(slot.seed)
        cache.close()
        gc.collect()
        self.assertEqual(cache.account.snapshot()["used"], cache.account.snapshot()["base"])

    def test_capacity_retry_does_not_consume_unpublished_aliases_twice(self):
        value = provider_snapshot("codex")
        value["sessions"] = value["sessions"][:1]
        self.accept(value)
        self.baseline("full")
        cache = self.state._sync_cache
        slot = cache.views["full"]
        slot.alias = 2**64 - 2
        new = copy.deepcopy(value["sessions"][0])
        native_id = "00000000-0000-4000-8000-000000000099"
        new["identity"]["nativeId"] = new["nativeIds"]["threadId"] = native_id
        value["sessions"].append(new)
        original, calls = cache._publish_staged, []

        def capacity_once(view, stage, generation, **kwargs):
            calls.append(generation)
            if len(calls) == 1:
                view.alias += 1  # an unpublished new slot allocated before pressure
                raise BudgetExceeded("synthetic_stage_pressure")
            return original(view, stage, generation, **kwargs)

        with patch.object(cache, "_publish_staged", side_effect=capacity_once):
            self.now += 1
            self.state.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=5000)
        self.assertIsNotNone(slot.current)
        self.assertEqual(slot.current.tables["records"].get(identity_key(new["identity"]))["alias"], 2**64 - 1)

    def test_new_native_binding_discards_an_unusable_failed_birth_seed(self):
        value = provider_snapshot("codex")
        self.accept(value)
        before = self.baseline("full")
        cache = self.state._sync_cache
        with patch.object(cache, "_publish_staged", side_effect=BudgetExceeded("synthetic_stage_pressure")):
            self.now += 1
            self.state.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=5000)
        slot = cache.views["full"]
        slot.seed.continuous = False
        value["sources"][0]["runtime"]["pid"] += 1
        value["sources"][0]["runtime"]["startTicks"] += 1
        self.now += 1
        self.state.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=5000)
        self.assertIsNotNone(slot.current)
        self.assertIsNone(slot.seed)
        self.assertNotEqual(slot.current.tag[0], before["tag"][0])
        Replay(self.baseline("full")).check(self)

    def test_owner_close_releases_roots_encoded_and_outer_leases(self):
        self.accept()
        self.baseline("full")
        cache = self.state._sync_cache
        self.accept()
        self.assertGreater(cache.account.snapshot()["byKind"]["external"], 0)
        cache.close()
        gc.collect()
        snapshot = cache.account.snapshot()
        self.assertEqual(snapshot["used"], snapshot["base"])

    def test_encoded_outputs_count_under_both_independent_caps(self):
        self.accept()
        cache = self.state._sync_owner()
        cache.ensure("full")
        before = cache.account.snapshot()["used"]
        baseline = self.state.sync_baseline("full")
        # Physical output bytes consume both the encoded cap and the heap cap;
        # their small owner/lease overhead also consumes the heap cap.
        self.assertGreater(len(baseline), 8192)
        increase = cache.account.snapshot()["used"] - before
        self.assertGreaterEqual(increase, len(baseline))
        self.assertLess(increase, len(baseline) + 4096)
        self.assertEqual(cache.encoded_staged, 0)
        persistent_stage = cache.account.snapshot()["byKind"]["stage"]
        with patch("agent_observer.sync_state.ENCODED_LIMIT", 1):
            self.state.attempt("codex", "runtime")
        self.assertIsNone(cache.current_tag("full"))
        self.assertEqual(cache.encoded_staged, 0)
        self.assertEqual(cache.account.snapshot()["byKind"]["stage"], persistent_stage)
        self.assertEqual(cache.retained_buffers(), ())

    def test_baseline_heap_failure_precedes_the_full_export_walk(self):
        self.accept()
        cache = self.state._sync_owner()
        current = cache.ensure("full").current
        before = current.tag
        occupied = cache.account.limit - cache.account.snapshot()["used"] - 8191
        with cache.account.reserve(occupied, kind="stage"):
            with patch.object(type(current.tables["records"]), "encoded_items",
                              side_effect=AssertionError("walked before heap credit")):
                with self.assertRaises(BudgetExceeded):
                    cache.baseline("full")
        self.assertEqual(cache.current_tag("full"), before)
        self.assertIsNone(cache.views["full"].baseline)
        self.assertEqual(cache.encoded_staged, 0)

    def test_optional_change_frame_quota_preserves_paid_state_and_requires_baseline(self):
        self.accept()
        before = self.baseline("full")
        cache = self.state._sync_cache
        reserve = cache.account.reserve

        def reject_frame(size, *, kind="external"):
            if kind == "encoded":
                raise BudgetExceeded("fixture_output_quota")
            return reserve(size, kind=kind)

        with patch.object(cache.account, "reserve", side_effect=reject_frame), \
                patch("agent_observer.sync_state._encode_parts",
                      side_effect=AssertionError("frame constructed before credit")):
            self.accept()
        current = cache.views["full"].current
        self.assertIsNotNone(current)
        self.assertIsNone(cache.views["full"].failed)
        self.assertGreater(cache.counts["baseline_fallbacks"], 0)
        self.assertEqual(cache.encoded_staged, 0)
        response = self.state.sync_changes("full", before["tag"], current.tag)
        self.assertEqual(json.loads(response)["status"], "baseline_required")
        Replay(self.baseline("full")).check(self)
        self.assertEqual(cache.export_committed("full"), self.state.snapshot)

    def test_journal_exact_chain_is_bounded_and_transaction_hash_is_independent(self):
        self.accept()
        first = self.baseline("full")
        for _ in range(4):
            self.accept()
        cache = self.state._sync_cache
        slot = cache.views["full"]
        self.assertEqual(len(slot.journal), 4)
        self.assertEqual(json.loads(self.state.sync_changes("full", first["tag"], slot.current.tag))["status"],
                         "baseline_required")
        for item in slot.journal:
            message = json.loads(item.data)
            transaction_id = message.pop("transactionId")
            expected = hashlib.sha256(b"mesh-sync-transaction\0" + _frame(canonical(message))).hexdigest()
            self.assertEqual(transaction_id, expected)
            self.assertEqual(message["resultTag"][1], message["baseTag"][1] + 1)
        target = slot.previous.tag
        result = self.state.sync_changes("full", target, target)
        self.assertEqual(len(result), 1)
        self.assertEqual(json.loads(result[0])["tag"], list(target))

    def test_tiny_budget_fails_closed_without_changing_legacy_source(self):
        self.accept()
        original = copy.deepcopy(self.state.snapshot)
        with self.assertRaises((ContractError, ValueError)):
            self.state._sync_cache = OwnerSyncCache(self.state, decoded_limit=8192)
            self.state.sync_baseline("full")
        self.assertIsNone(self.state.sync_current_tag("full"))
        self.assertEqual(self.state.snapshot, original)


if __name__ == "__main__":
    unittest.main()
