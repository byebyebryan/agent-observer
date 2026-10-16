"""The byte owner backend preserves the reference domain semantics."""

import copy
import gc
import sys
import unittest
from unittest.mock import patch

import test_sync_state as reference

from agent_observer.active_contract import FACT_SUPPORT
from agent_observer.contract import SESSION, ContractError, validate_shape
from agent_observer.observation_support import SUPPORT_FIELDS
from agent_observer.sync_commitment import BudgetExceeded, canonical
from agent_observer.sync_contract import split_record
from agent_observer.sync_encoded_state import (
    _OBS_BYTES,
    MAX_ROW_BYTES,
    EncodedTableStage,
    encode_row_content,
    row_content_bound,
)
from agent_observer.sync_state import OwnerSyncCache, _Stage


def _maximum_shape(spec):
    if "anyOf" in spec:
        values = [_maximum_shape(child) for child in spec["anyOf"]]
        return max(values, key=lambda value: len(canonical(value)))
    if "enum" in spec:
        return max(spec["enum"], key=lambda value: len(canonical(value)))
    kind = spec["type"]
    if type(kind) is list:
        return max((_maximum_shape(dict(spec, type=value)) for value in kind),
                   key=lambda value: len(canonical(value)))
    if kind == "null":
        return None
    if kind == "boolean":
        return False
    if kind == "integer":
        return spec["maximum"]
    if kind == "string":
        length, pattern = spec["maxLength"], spec.get("pattern", "")
        if "[0-9a-f]{8}" in pattern:
            return reference.BOOT
        if "sha256" in pattern:
            return "sha256:" + "f" * 64
        if pattern:
            return "a" * length
        return "🙂" * length
    if kind == "array":
        return [_maximum_shape(spec["items"]) for _ in range(spec["maxItems"])]
    return {key: _maximum_shape(child) for key, child in spec["properties"].items()}


class SyncEncodedStateTest(reference.SyncStateTest):
    def setUp(self):
        super().setUp()
        self.state._sync_cache = OwnerSyncCache(self.state, backend="encoded")

    def test_same_owner_reference_has_identical_roots_and_exported_values(self):
        self.accept(component="history")
        self.accept()
        encoded = self.state._sync_cache
        frozen = OwnerSyncCache(self.state)
        for view in ("full", "active"):
            left, right = encoded.ensure(view).current, frozen.ensure(view).current
            self.assertEqual(left.tag, right.tag)
            self.assertEqual(encoded.baseline(view), frozen.baseline(view))
            self.assertEqual(encoded.export_committed(view), frozen.export_committed(view))
            slot = next(left.tables["records"].items())[1]
            original = left.tables["bodies"].get(slot["body"])
            changed = copy.deepcopy(original)
            changed["title"] = "detached caller mutation"
            self.assertEqual(left.tables["bodies"].get(slot["body"]), original)
            self.assertNotEqual(changed, original)
        frozen.close()

    def test_invalid_backend_is_explicit(self):
        with self.assertRaises(ContractError):
            OwnerSyncCache(self.state, backend="unknown")

    def test_warm_observation_update_shares_existing_canonical_key_buffers(self):
        self.accept()
        self.baseline("full")
        cache = self.state._sync_cache
        current = cache.views["full"].current
        before = dict(current.tables["observations"].encoded_items())
        value = reference.provider_snapshot("codex")
        for row in value["sessions"]:
            row["runtime"]["observedAt"] += 1000
            if row["phase"] is not None:
                row["phase"]["observedAt"] += 1000
        self.accept(value)
        original_keys = {key: key for key in before}
        changed = False
        for key, observed in cache.views["full"].current.tables["observations"].encoded_items():
            if key in original_keys:
                self.assertIs(key, original_keys[key])
                changed |= before[key] != observed
        self.assertTrue(changed)

    def test_internal_canonical_buffers_share_encoded_cap_with_output(self):
        self.accept()
        cache = self.state._sync_cache
        slot = cache.ensure("full")
        internal = cache.encoded_ownership.used
        self.assertGreater(internal, 0)
        self.assertEqual(cache.owned_encoded_bytes(), internal)
        before = slot.current.tag
        with patch("agent_observer.sync_state.ENCODED_LIMIT", internal), \
                patch("agent_observer.sync_encoded.EncodedMap.encoded_items",
                      side_effect=AssertionError("walked before reservation")):
            with self.assertRaises(ContractError):
                cache.baseline("full")
        self.assertEqual(slot.current.tag, before)
        self.assertIsNone(slot.baseline)
        self.assertEqual(cache.encoded_ownership.used, internal)

    def test_finite_row_and_context_support_bounds_cover_maximum_shape(self):
        row, support = _maximum_shape(SESSION), _maximum_shape(FACT_SUPPORT)
        validate_shape(row, SESSION)
        validate_shape(support, FACT_SUPPORT)
        content, observations = split_record(row)
        self.assertLessEqual(len(canonical(row)), MAX_ROW_BYTES)
        self.assertLessEqual(len(canonical(content)), MAX_ROW_BYTES)
        self.assertLessEqual(len(canonical(content)), row_content_bound(content))
        value = {"fields": observations,
                 "supports": {name: ["context", support] for name in SUPPORT_FIELDS}}
        self.assertLessEqual(len(canonical(value)), _OBS_BYTES)

    def test_row_encoding_workspace_survives_return_and_preflights_before_copy(self):
        stage = _Stage(self.state._sync_cache)
        content, _ = split_record(reference.provider_snapshot("codex")["sessions"][0])
        encoded_bound = min(MAX_ROW_BYTES, row_content_bound(content)) * 6
        try:
            with patch("agent_observer.sync_state.ENCODED_LIMIT", encoded_bound - 1), \
                    patch("agent_observer.sync_encoded_state.json.dumps", side_effect=AssertionError("allocated")):
                with self.assertRaises(ContractError):
                    encode_row_content(stage, content)
            value = encode_row_content(stage, content)
            self.assertEqual(value, canonical(content))
            self.assertGreaterEqual(self.state._sync_cache.encoded_staged, encoded_bound)
            # An unchanged row buffer has no pending-map owner, yet remains
            # covered through subsequent work and the end of publication.
            stage.row()
            self.assertGreaterEqual(self.state._sync_cache.encoded_staged, len(value))
        finally:
            stage.close()
        self.assertEqual(self.state._sync_cache.encoded_staged, 0)

    def test_failed_stage_constructor_has_no_unraisable_destructor_error(self):
        cache = self.state._sync_cache
        stage = _Stage(cache)
        failures = []
        try:
            with patch.object(cache.account, "reserve", side_effect=BudgetExceeded("fixture")), \
                    patch.object(sys, "unraisablehook", failures.append):
                with self.assertRaises(BudgetExceeded):
                    EncodedTableStage("records", stage)
                gc.collect()
            self.assertEqual(failures, [])
        finally:
            stage.close()


if __name__ == "__main__":
    unittest.main()
