"""Pure SDK 1 decomposition for the unreleased working-set profile candidate."""

import ast
import copy
import inspect
import unittest
from pathlib import Path
from types import MappingProxyType
from unittest.mock import patch

import test_service_contract as service_contract_fixture
import test_working_set_projection as projection_fixture
from mesh_test_support import require_working_set_sdk

from agent_observer.contract import ContractError, identity_key
from agent_observer.working_set_policy import DEFAULT_WINDOW_MS, MAX_WINDOW_MS

if require_working_set_sdk():
    from mesh_plus.api import NativeState, PreparationState, PreparedRule
    from mesh_plus.api import descriptor as mesh_descriptor

    from agent_observer.mesh_working_set_profile import (
        NATIVE_PROTOCOL,
        WORKING_SET_PROFILE_ID,
        WorkingSetAgentCodec,
        WorkingSetAgentPreparation,
        WorkingSetAgentProfile,
        _members,
        _prepare_rules,
        _record_eligible,
        restore_working_set_native,
    )
    from agent_observer.mesh_working_set_publisher import make_working_set_publisher


def _freeze(value):
    if type(value) is dict:
        return MappingProxyType({key: _freeze(child) for key, child in value.items()})
    if type(value) in {list, tuple}:
        return tuple(_freeze(child) for child in value)
    return value


class MeshWorkingSetProfileTest(unittest.TestCase):
    host = "fixture"
    source = "local"
    window = 10000

    def setUp(self):
        self.codec = WorkingSetAgentCodec(self.host, self.source, self.window)

    @staticmethod
    def frame(*, runtime="parked", recent=True, kind=None):
        service_fixture = service_contract_fixture.fixture()
        service_fixture["clockDomain"] = "time:[123]"
        fixture = projection_fixture.WorkingSetProjectionTest()
        with patch.object(projection_fixture, "fixture", return_value=service_fixture):
            fixture.setUp()
        at = projection_fixture.WALL - 5000 if recent else None
        value = fixture.sample(runtime=runtime, at=at)
        if kind is not None:
            value["sessions"][0]["kind"] = kind
        return fixture.accept(value)

    def test_native_split_restore_and_member_rules_cover_active_recent_parked_unknown(self):
        cases = (
            self.frame(runtime="running", recent=False),
            self.frame(runtime="parked"),
            self.frame(runtime="unknown"),
            self.frame(runtime="parked", kind="unknown"),
        )
        for frame in cases:
            before = copy.deepcopy(frame)
            state = self.codec.inspect_native(frame)
            self.assertIsInstance(state, NativeState)
            self.assertEqual(state.owner["protocol"], NATIVE_PROTOCOL)
            self.assertEqual(state.owner["version"], 1)
            self.assertEqual(
                state.owner["metadata"],
                {key: value for key, value in frame["projection"].items() if key != "sessions"},
            )
            self.assertEqual(state.owner["service"], {
                key: value for key, value in frame.items() if key != "projection"
            })
            self.assertEqual(state.records, tuple(frame["projection"]["sessions"]))
            self.assertEqual(
                restore_working_set_native(state.owner, state.records), frame
            )
            members = _members(state.owner)
            self.assertTrue(_record_eligible(state.records[0], members))
            self.assertEqual(frame, before)

    def test_generic_preparation_indexes_metadata_once_and_retains_only_rules(self):
        for frame in (
            self.frame(runtime="running", recent=False),
            self.frame(runtime="parked"),
            self.frame(runtime="unknown"),
            self.frame(runtime="parked", kind="unknown"),
        ):
            state = self.codec.inspect_native(frame)
            prep_state = PreparationState(
                _freeze(state.owner),
                _freeze(state.records),
                _freeze(state.clock),
                state.publisher,
                state.emitted_ms,
                _freeze(state.receipts),
            )
            with patch(
                "agent_observer.mesh_working_set_profile._members", wraps=_members
            ) as index:
                rules = _prepare_rules(prep_state)
            self.assertEqual(index.call_count, 1)
            self.assertEqual(len(rules), len(state.records))
            self.assertIs(type(rules[0]), PreparedRule)
            self.assertTrue(rules[0].eligible)
            self.assertIsNotNone(rules[0].required)
            self.assertEqual(
                rules[0].identity,
                identity_key(dict(state.records[0]["identity"])),
            )

            rejected = copy.deepcopy(state.records[0])
            rejected["kind"] = "system"
            self.assertFalse(_record_eligible(rejected, _members(state.owner)))
            rejected = copy.deepcopy(state.records[0])
            rejected["identity"]["hostScope"] = "other"
            self.assertFalse(_record_eligible(rejected, _members(state.owner)))

            # Rules contain only copied scalar identity/receipt keys, not the
            # caller's row or metadata mappings.
            original_required = rules[0].required
            state.records[0]["identity"]["nativeId"] += "-mutated"
            self.assertEqual(rules[0].required, original_required)

    def test_receipts_clock_and_publisher_keep_original_native_meanings(self):
        frame = self.frame(runtime="parked")
        state = self.codec.inspect_native(frame)
        expected_receipts = tuple(
            {
                "sourceId": source["provider"] + ":" + source["namespace"],
                "component": component["name"],
                "accepted": component["accepted"],
                "health": component["health"],
                "expiry": component["expiresBoottimeMs"],
            }
            for source in frame["sources"]
            for component in source["components"]
        )
        self.assertEqual(state.receipts, expected_receipts)
        self.assertEqual(state.publisher, frame["serviceId"])
        self.assertEqual(state.emitted_ms, frame["emittedBoottimeMs"])
        self.assertEqual(
            state.clock,
            {"bootId": frame["bootId"], "timeNamespace": frame["clockDomain"].replace("[", "").replace("]", "")},
        )

    def test_null_projection_downgrades_current_receipts_and_restores_exactly(self):
        frame = self.frame(runtime="parked")
        frame["projection"] = None
        original = copy.deepcopy(frame)
        state = self.codec.inspect_native(frame)
        self.assertIsNone(state.owner["metadata"])
        self.assertEqual(state.records, ())
        self.assertEqual(state.owner["service"], {
            key: value for key, value in frame.items() if key != "projection"
        })
        self.assertEqual(restore_working_set_native(state.owner, state.records), frame)
        for receipt, component in zip(
            state.receipts, frame["sources"][0]["components"], strict=True
        ):
            self.assertEqual(receipt["accepted"], component["accepted"])
            self.assertEqual(receipt["expiry"], component["expiresBoottimeMs"])
            self.assertEqual(
                receipt["health"],
                "stale" if component["health"] in {"current", "partial"} else component["health"],
            )
            self.assertNotIn(receipt["health"], {"current", "partial"})
        self.assertEqual(frame, original)
        with self.assertRaisesRegex(ContractError, "records_without_metadata"):
            restore_working_set_native(state.owner, ({"unexpected": True},))

    def test_bridge_binds_exact_host_source_and_selected_window(self):
        frame = self.frame(runtime="parked")
        payload = {"hostId": self.host, "sourceId": self.source, "ownerFrame": frame}
        self.codec.validate_bridge(payload)
        self.assertEqual(self.codec.admit_bridge(payload), self.codec.inspect_native(frame))
        for bad in (
            {**payload, "hostId": "other"},
            {**payload, "sourceId": "other"},
        ):
            with self.subTest(binding=bad), self.assertRaisesRegex(
                ContractError, "bridge_source_binding"
            ):
                self.codec.admit_bridge(bad)
        with self.assertRaisesRegex(ContractError, "working_set_host"):
            WorkingSetAgentCodec("other", self.source, self.window).inspect_native(frame)
        with self.assertRaisesRegex(ContractError, "working_set_selector_mismatch"):
            WorkingSetAgentCodec(self.host, self.source, self.window + 1).inspect_native(frame)

    def test_exact_integer_window_and_immutable_codec_contract(self):
        default = WorkingSetAgentCodec(self.host, self.source)
        self.assertEqual(default.window_ms, DEFAULT_WINDOW_MS)
        self.assertEqual(
            WorkingSetAgentCodec(self.host, self.source, MAX_WINDOW_MS).window_ms,
            MAX_WINDOW_MS,
        )
        for window in (True, 72.0, -1, MAX_WINDOW_MS + 1):
            with self.subTest(window=window), self.assertRaises(ContractError):
                WorkingSetAgentCodec(self.host, self.source, window)
        with self.assertRaises(ContractError):
            WorkingSetAgentCodec(self.host, self.source, self.window, "other-profile")
        with self.assertRaises(ContractError):
            WorkingSetAgentCodec("bad host", self.source, self.window)
        with self.assertRaises(ContractError):
            WorkingSetAgentCodec(self.host, "BadSource", self.window)
        with self.assertRaises((AttributeError, TypeError)):
            self.codec.window_ms = 0

    def test_sdk_profile_registration_is_checked_only_through_public_descriptor(self):
        try:
            descriptor = mesh_descriptor("agent", profile_id=WORKING_SET_PROFILE_ID)
        except ValueError:
            with self.assertRaises(ValueError):
                WorkingSetAgentProfile()
            with self.assertRaises(ValueError):
                WorkingSetAgentPreparation()
            with patch(
                "agent_observer.mesh_working_set_source.CachedWorkingSetAgentSource"
            ) as source:
                with self.assertRaises(ValueError):
                    make_working_set_publisher("fixture", "local", "/unused", window_ms=10000)
                source.assert_not_called()
        else:
            self.assertEqual(descriptor.profile_id, WORKING_SET_PROFILE_ID)
            profile = WorkingSetAgentProfile()
            preparation = WorkingSetAgentPreparation(profile)
            self.assertEqual(profile.descriptor, descriptor)
            self.assertEqual(preparation.descriptor.profile, descriptor)
            with (
                patch(
                    "agent_observer.mesh_working_set_source.CachedWorkingSetAgentSource"
                ) as source,
                patch("mesh_plus.api.CachedPublisher") as publisher,
            ):
                result = make_working_set_publisher(
                    "fixture", "local", "/unused", window_ms=10000
                )
                source.assert_called_once_with("fixture", "/unused", window_ms=10000)
                publisher.assert_called_once()
                self.assertIs(result, publisher.return_value)
        with self.assertRaises(ContractError):
            WorkingSetAgentProfile(window_ms=True)

    def test_profile_module_has_no_direct_provider_or_io_dependencies(self):
        source = Path(inspect.getsourcefile(WorkingSetAgentCodec)).read_text()
        tree = ast.parse(source)
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module is not None:
                imports.append(node.module)
        forbidden = {
            "os",
            "pathlib",
            "socket",
            "subprocess",
            "selectors",
            "requests",
            "urllib",
            "agent_observer.service_state",
            "agent_observer.service_runtime",
            "agent_observer.providers",
        }
        self.assertFalse(forbidden.intersection(imports), imports)


if __name__ == "__main__":
    unittest.main()
