"""Synthetic proof-bound public facade checks; no I/O/native acceptance."""

import copy
import unittest
from unittest.mock import patch

from test_service_state import provider_snapshot

from agent_observer.contract import ContractError, identity_key
from agent_observer.service_state import ServiceState
from agent_observer.sync_native import parse_message

try:
    from mesh_plus.protocol import ProtocolError
    from mesh_plus.sync.cache import OwnedSyncCache, ResyncRequired, ViewRef, source_binding
    from mesh_plus.sync.canonical import canonical
    from mesh_plus.sync.reconstruction import PublicIndexRef

    from agent_observer.mesh_sync_profile import AgentSyncProfile
    from agent_observer.mesh_sync_read import PreparedAgentSyncRead
except ModuleNotFoundError as error:
    if error.name != "mesh_plus" and not error.name.startswith("mesh_plus."):
        raise
    HAS_SYNC = False
else:
    HAS_SYNC = True


@unittest.skipUnless(HAS_SYNC, "optional Mesh sync interface is unavailable")
class MeshSyncReadTest(unittest.TestCase):
    def setUp(self):
        self.now = 15000
        self.caches = []
        self.owners = []

    def tearDown(self):
        for cache in self.caches:
            cache.close()
            self.assertEqual(cache.ledger.used, 0)
            self.assertEqual(cache.ledger.reserved, 0)
        for owner in self.owners:
            if owner._sync_cache is not None:
                owner._sync_cache.close()

    def fixture(self, count=1):
        value = provider_snapshot("codex")
        first = value["sessions"][0]
        value["sessions"] = []
        for index in range(count):
            row = copy.deepcopy(first)
            row["identity"]["nativeId"] = row["nativeIds"]["threadId"] = (
                f"00000000-0000-4000-8000-{index + 1:012d}"
            )
            value["sessions"].append(row)
        return value

    def owner(self, value=None):
        value = self.fixture() if value is None else value
        source = value["sources"][0]
        owner = ServiceState(
            host_scope="fixture",
            configs={"codex": (source["configHome"], source["configHomeKind"])},
            uid=1000,
            clock=lambda: self.now,
            boot_id="00000000-0000-4000-8000-000000000001",
            clock_domain="time:[123]",
        )
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        self.owners.append(owner)
        return owner

    def cache(self, view="full", *, source="agents", profile=None):
        profile = profile or AgentSyncProfile(profile_schema_digest="a" * 64, view=view)
        reader_time = [100000]
        clock = {"bootId": "reader-boot", "timeNamespace": "time:2"}
        binding = source_binding("fixture", source, profile.descriptor)
        request = {
            "readerEpoch": "r" * 32,
            "channelEpoch": "c" * 32,
            "bridgeId": "b" * 32,
            "hosts": ["fixture"],
            "route": "fixed",
        }
        cache = OwnedSyncCache(
            profile, binding, request_binding=request, _now_ms=lambda: reader_time[0], _clock=clock
        )
        self.caches.append(cache)
        return cache, reader_time, clock, binding, request

    def confirm(self, parts, owner, candidate, *, tag=None):
        cache, reader_time, clock, binding, request = parts
        # Test-owned transport setup only. Admission/facade never use this
        # private challenge operation or inspect private cache state.
        challenge = cache._proof_request(candidate)
        head = parse_message(
            owner.sync_head(cache.profile.view, challenge), cache.profile.view, "fixture"
        )
        if tag is not None:
            head["tag"] = tag
        bridge_time = head["ownerClock"]["boottimeMs"] + 10
        proof = {
            "protocol": "mesh.state-sync/1",
            "kind": "proof",
            "descriptor": cache.descriptor.wire(),
            "sourceBinding": binding,
            "sourceTag": candidate.tag.wire(),
            "requestBinding": request,
            "challenge": challenge,
            "bridgeId": request["bridgeId"],
            "bridgeClock": {
                "bootId": head["ownerClock"]["bootId"],
                "timeNamespace": head["ownerClock"]["clockDomain"]
                .replace("[", "")
                .replace("]", ""),
                "boottimeMs": bridge_time,
            },
            "head": head,
            "remaining": [
                [
                    key,
                    max(0, value["expiresBoottimeMs"] - bridge_time)
                    if value["health"] in {"current", "partial"}
                    else 0,
                ]
                for key, value in head["originalReceipts"]
            ],
        }
        reader_time[0] += 20
        return cache.confirm(candidate, canonical(proof), clock)

    def prepared(self, owner, view="full", *, raw=None):
        parts = self.cache(view)
        candidate = parts[0].admit_baseline(owner.sync_baseline(view) if raw is None else raw)
        confirmed = self.confirm(
            parts, owner, candidate, tag=None if raw is None else candidate.tag.native.wire()
        )
        facade = PreparedAgentSyncRead(parts[0].profile, "fixture", "agents")
        facade.accept(confirmed)
        return facade, parts, confirmed

    def advance(self, facade, parts, owner, *, baseline=False):
        cache = parts[0]
        if baseline:
            candidate = cache.admit_baseline(owner.sync_baseline(cache.profile.view))
        else:
            target = owner.sync_current_tag(cache.profile.view)
            response = owner.sync_changes(cache.profile.view, facade._tag.native.wire(), target)
            self.assertIsInstance(response, tuple)
            for raw in response[:-1]:
                candidate = cache.stage(raw)
        confirmed = self.confirm(parts, owner, candidate)
        facade.accept(confirmed)
        return confirmed

    def test_accept_is_constant_and_context_precedes_all_public_read_access(self):
        owner = self.owner()
        facade, parts, view = self.prepared(owner)
        events = []
        context, lookup = ViewRef.context, ViewRef.lookup

        def before(ref, now, clock):
            events.append("context")
            return context(ref, now, clock)

        def after(ref, space, key):
            self.assertEqual(events[0], "context")
            events.append(space)
            return lookup(ref, space, key)

        with (
            patch.object(ViewRef, "context", side_effect=AssertionError("accept context")),
            patch.object(
                ViewRef,
                "lookup",
                side_effect=AssertionError("accept table"),
            ),
            patch.object(ViewRef, "index", side_effect=AssertionError("accept index")),
            patch.object(
                ViewRef,
                "export_committed",
                side_effect=AssertionError("implicit export"),
            ),
        ):
            facade.accept(view)
        key = identity_key(owner.snapshot["sessions"][0]["identity"])
        with (
            patch.object(ViewRef, "context", before),
            patch.object(ViewRef, "lookup", after),
            patch.object(
                ViewRef,
                "export_committed",
                side_effect=AssertionError("implicit export"),
            ),
        ):
            result = facade.current(parts[1][0], parts[2], keys=[key])
        self.assertEqual(len(result.sessions), 1)
        self.assertTrue(result.field_authority[key]["runtime"])
        self.assertEqual(result.tag, view.tag)
        result.sessions[0]["title"] = "mutated caller copy"
        result.context["host"] = "changed"
        again = facade.current(parts[1][0], parts[2], keys=[key])
        self.assertNotEqual(again.sessions[0]["title"], result.sessions[0]["title"])
        self.assertEqual(again.context["host"], "fixture")

    def test_keyed_cost_is_independent_of_roster_and_never_uses_order_or_export(self):
        counts = []
        for count in (1, 128):
            owner = self.owner(self.fixture(count))
            facade, parts, view = self.prepared(owner)
            key = identity_key(owner.snapshot["sessions"][0]["identity"])
            calls, lookup = [], ViewRef.lookup

            def counted(ref, space, item, calls=calls, lookup=lookup):
                calls.append((space, item))
                return lookup(ref, space, item)

            with (
                patch.object(
                    PublicIndexRef, "iter_keys", side_effect=AssertionError("keyed order scan")
                ),
                patch.object(
                    ViewRef,
                    "lookup",
                    counted,
                ),
                patch.object(
                    ViewRef, "export_committed", side_effect=AssertionError("implicit export")
                ),
            ):
                result = facade.current(parts[1][0], parts[2], keys=[key])
            self.assertEqual(len(result.sessions), 1)
            self.assertEqual(sum(space == "bodies" for space, _ in calls), 1)
            self.assertEqual([item for space, item in calls if space == "records"], [list(key)])
            counts.append(len(calls))
        self.assertEqual(counts[0], counts[1])

    def test_full_all_rows_use_public_order_and_snapshot_is_explicit_diagnostic(self):
        owner = self.owner(self.fixture(3))
        facade, parts, view = self.prepared(owner)
        result = facade.current(parts[1][0], parts[2])
        self.assertEqual(
            [r["identity"] for r in result.sessions],
            [r["identity"] for r in owner.snapshot["sessions"]],
        )
        diagnostic = facade.snapshot()
        self.assertEqual(diagnostic, owner.snapshot)
        deadline = max(r["expiresMs"] for r in result.context["receipts"])
        stale = facade.current(deadline, parts[2])
        self.assertEqual(len(stale.sessions), 3)
        self.assertTrue(all(not flags["runtime"] for flags in stale.field_authority.values()))
        self.assertTrue(all(row["runtime"]["value"] == "unknown" for row in stale.sessions))
        self.assertEqual(facade.snapshot(), diagnostic)

    def test_history_expiry_masks_fields_without_revoking_runtime_active_membership(self):
        value = self.fixture()
        row = value["sessions"][0]
        row["activity"].update(
            at=1700000010000, source="codex_rpc", health="current", reason="native_activity"
        )
        row["workspace"] = {
            "health": "current",
            "reason": "local_metadata",
            "root": "/fixture",
            "rootKey": "fixture",
            "relativePath": "project",
            "projectKey": None,
            "repo": None,
        }
        value["sources"][0]["capabilities"]["activity"] = True
        owner = self.owner(value)
        owner.accept(
            "codex", "history", value, sampled_ms=self.now, ttl_ms=1000, runtime_ttl_ms=10000
        )
        runtime = self.fixture()
        owner.accept("codex", "runtime", runtime, sampled_ms=self.now, ttl_ms=10000)
        for view in ("full", "active"):
            facade, parts, _ = self.prepared(owner, view)
            key = identity_key(value["sessions"][0]["identity"])
            result = facade.current(parts[1][0], parts[2], keys=[key])
            self.assertEqual(result.sessions[0]["activity"]["at"], 1700000010000)
            self.assertIsNotNone(result.sessions[0]["workspace"])
            history = next(r for r in result.context["receipts"] if r["key"][-1] == "history")
            expired = facade.current(history["expiresMs"], parts[2], keys=[key])
            self.assertEqual(len(expired.sessions), 1)
            self.assertEqual(expired.sessions[0]["runtime"]["value"], "running")
            self.assertTrue(expired.field_authority[key]["runtime"])
            self.assertFalse(expired.field_authority[key]["activity"])
            self.assertIsNone(expired.sessions[0]["activity"]["at"])
            self.assertIsNone(expired.sessions[0]["workspace"])

    def test_complete_empty_scope_expires_independently_of_rows(self):
        owner = self.owner(self.fixture(0))
        facade, parts, _ = self.prepared(owner, "active")
        result = facade.current(parts[1][0], parts[2], keys=())
        self.assertEqual(result.sessions, [])
        self.assertTrue(result.scopes[0]["currentComplete"])
        runtime = next(r for r in result.context["receipts"] if r["key"][-1] == "runtime")
        result = facade.current(runtime["expiresMs"], parts[2], keys=())
        self.assertFalse(result.scopes[0]["currentComplete"])
        self.assertEqual(result.scopes[0]["coverage"]["status"], "stale")
        self.assertIsNotNone(result.context)

    def test_retained_context_ref_never_rebinds_to_newer_same_key_receipt(self):
        value = self.fixture(2)
        owner = self.owner(value)
        facade, parts, _ = self.prepared(owner)
        retained = identity_key(value["sessions"][1]["identity"])
        value["sessions"] = value["sessions"][:1]
        value["sources"][0]["coverage"]["runtime"].update(status="partial", reason="bounded_census")
        self.now += 1
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        self.advance(facade, parts, owner)
        result = facade.current(parts[1][0], parts[2], keys=[retained])
        self.assertEqual(len(result.sessions), 1)
        self.assertFalse(result.field_authority[retained]["runtime"])
        self.assertEqual(result.sessions[0]["runtime"]["value"], "unknown")
        self.assertFalse(result.scopes[0]["currentComplete"])
        self.assertTrue(
            next(r for r in result.context["receipts"] if r["key"][-1] == "runtime")["current"]
        )

    def test_negative_horizon_attenuates_translated_deadline_and_preserves_context(self):
        from test_mesh_sync_profile import restamp

        value = self.fixture()
        owner = self.owner(value)
        owner.sync_baseline("active")
        value["sessions"][0]["kind"] = "child"
        self.now += 1
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        baseline = parse_message(owner.sync_baseline("active"), "active", "fixture")
        negative = next(
            fact for key, fact in baseline["tables"]["scopes"] if key[2] == "nonmembers"
        )
        negative["horizonBoottimeMs"] = self.now + 2000
        raw = canonical(restamp(baseline)) + b"\n"
        facade, parts, _ = self.prepared(owner, "active", raw=raw)
        key = identity_key(negative["identity"])
        result = facade.current(parts[1][0], parts[2], keys=[key])
        self.assertEqual(result.nonmembers, [negative])
        self.assertEqual(facade.current(parts[1][0], parts[2]).nonmembers, [negative])
        support = negative["supports"][0]
        translated = next(
            r for r in result.context["receipts"] if r["key"][-1] == support["component"]
        )
        deadline = translated["expiresMs"] - (
            support["expiresBoottimeMs"] - negative["horizonBoottimeMs"]
        )
        self.assertNotEqual(deadline, negative["horizonBoottimeMs"])
        self.assertTrue(facade.current(deadline - 1, parts[2], keys=[key]).nonmembers)
        expired = facade.current(deadline, parts[2], keys=[key])
        self.assertEqual(expired.nonmembers, [])
        self.assertEqual(expired.uncertain, [])
        self.assertEqual(expired.exception_context[0].fact, negative)
        self.assertFalse(expired.exception_context[0].current)

    def test_partial_reconnect_uncertainty_and_missed_negative_never_retire_prior_context(self):
        value = self.fixture()
        owner = self.owner(value)
        facade, parts, _ = self.prepared(owner, "active")
        key = identity_key(value["sessions"][0]["identity"])
        presentation = facade.current(parts[1][0], parts[2], keys=[key]).sessions[0]
        facade.disconnect()
        parts[0].disconnect()
        value["sessions"][0]["kind"] = "child"
        self.now += 1
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        value["sessions"] = []
        value["sources"][0]["coverage"]["runtime"].update(status="partial", reason="bounded_census")
        self.now += 1
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        self.advance(facade, parts, owner, baseline=True)
        result = facade.current(parts[1][0], parts[2], keys=[key])
        self.assertEqual(result.sessions, [])
        self.assertEqual(result.nonmembers, [])
        self.assertEqual(len(result.uncertain), 1)
        self.assertFalse(result.exception_context[0].current)
        self.assertFalse(result.scopes[0]["currentComplete"])
        whole = facade.current(parts[1][0], parts[2])
        self.assertEqual(whole.uncertain, result.uncertain)
        self.assertEqual(whole.exception_context, result.exception_context)
        self.assertEqual(presentation["runtime"]["value"], "running")
        # A longer partial outage may miss the bounded negative/uncertain
        # exception entirely. Its absence still cannot settle prior context.
        self.now += 10001
        owner.expire(self.now)
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        self.advance(facade, parts, owner, baseline=True)
        missed = facade.current(parts[1][0], parts[2], keys=[key])
        self.assertEqual(missed.nonmembers, [])
        self.assertEqual(missed.uncertain, [])
        self.assertEqual(missed.exception_context, ())
        self.assertFalse(missed.scopes[0]["currentComplete"])
        # The facade owns no UI history and invents no timeout for this prior row.
        facade.disconnect()
        self.assertIsNone(facade.current(parts[1][0], parts[2], keys=[key]).context)
        self.assertEqual(identity_key(presentation["identity"]), key)

    def test_since_reads_only_explicit_changed_keys_and_returns_recovery_without_export(self):
        owner = self.owner(self.fixture(16))
        facade, parts, view = self.prepared(owner)
        original = view.tag
        value = self.fixture(16)
        value["sessions"][0]["title"] = "changed content"
        self.now += 1
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        self.advance(facade, parts, owner)
        with (
            patch.object(
                ViewRef, "export_committed", side_effect=AssertionError("implicit export")
            ),
            patch.object(
                PublicIndexRef,
                "iter_keys",
                side_effect=AssertionError("delta roster scan"),
            ),
        ):
            result = facade.current(parts[1][0], parts[2], since=original)
            self.assertEqual([r["title"] for r in result.sessions], ["changed content"])
            self.assertTrue(
                any(space == "receipts" for space, _key, _removed in result.changes.keys)
            )
            previous = result.tag
            owner.attempt("codex", "runtime")
            self.advance(facade, parts, owner)
            diagnostic = facade.current(parts[1][0], parts[2], since=previous)
            self.assertEqual(diagnostic.sessions, [])
            self.assertTrue(
                any(space == "receipts" for space, _key, _removed in diagnostic.changes.keys)
            )
            recovery = facade.current(parts[1][0], parts[2], since=original)
            self.assertIsInstance(recovery.changes, ResyncRequired)
            self.assertEqual(recovery.sessions, [])
            key = identity_key(value["sessions"][1]["identity"])
            keyed = facade.current(parts[1][0], parts[2], keys=[key], since=original)
            self.assertEqual(len(keyed.sessions), 1)

    def test_clock_errors_wrong_bindings_disconnect_and_key_limits_fail_closed(self):
        owner = self.owner()
        facade, parts, view = self.prepared(owner)
        facade.current(parts[1][0] + 10, parts[2], keys=())
        with self.assertRaisesRegex(ProtocolError, "agent_sync_read_clock"):
            facade.current(parts[1][0] + 9, parts[2], keys=())
        self.assertIsNone(facade.snapshot())
        parts[1][0] += 10
        for host, source, profile in (
            ("foreign", "agents", parts[0].profile),
            ("fixture", "other", parts[0].profile),
            ("fixture", "agents", AgentSyncProfile(profile_schema_digest="b" * 64)),
            ("fixture", "agents", AgentSyncProfile(profile_schema_digest="a" * 64, view="active")),
        ):
            wrong = PreparedAgentSyncRead(profile, host, source)
            with self.assertRaises(ProtocolError):
                wrong.accept(view)
            self.assertIsNone(wrong.snapshot())
        for mutate in (
            lambda c: c.update(host="foreign"),
            lambda c: c.update(source="other"),
            lambda c: c.update(profile="other"),
            lambda c: c["nativeBinding"].update(selector={}),
            lambda c: c["ownerClock"].update(ownerEpoch="different"),
            lambda c: c["receipts"][0].update(valueHash="f" * 64),
            lambda c: c["receipts"][0].update(accepted=999),
        ):
            facade.accept(view)
            context = view.context(parts[1][0], parts[2])
            mutate(context)
            with (
                patch.object(ViewRef, "context", return_value=context),
                self.assertRaises(ProtocolError),
            ):
                facade.current(parts[1][0], parts[2], keys=())
            self.assertIsNone(facade.snapshot())
        facade.accept(view)
        with self.assertRaisesRegex(ProtocolError, "sync_reader_clock"):
            facade.current(parts[1][0], {**parts[2], "bootId": "different"}, keys=())
        self.assertIsNone(facade.snapshot())
        key = identity_key(owner.snapshot["sessions"][0]["identity"])
        for keys in ([key] * 4097, [key, key], [key[:4]], [["foreign", *key[1:]]]):
            facade.accept(view)
            with self.assertRaises((ProtocolError, ContractError)):
                facade.current(parts[1][0], parts[2], keys=keys)
            self.assertIsNone(facade.snapshot())
        facade.accept(view)
        parts[0].disconnect()
        with self.assertRaises(ProtocolError):
            facade.current(parts[1][0], parts[2], keys=())
        self.assertIsNone(facade.snapshot())

    def test_whole_active_exceptions_and_export_use_declared_public_index(self):
        owner = self.owner()
        facade, parts, _ = self.prepared(owner, "active")
        self.assertEqual(len(facade.current(parts[1][0], parts[2]).sessions), 1)
        self.assertEqual(facade.snapshot(), owner.sync_active_projection)

    def test_whole_scope_index_finds_exclusions_beyond_first_32_rows(self):
        value = self.fixture(40)
        owner = self.owner(value)
        owner.sync_baseline("active")
        excluded = identity_key(value["sessions"][-1]["identity"])
        value["sessions"][-1]["kind"] = "child"
        self.now += 1
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        facade, parts, _ = self.prepared(owner, "active")
        result = facade.current(parts[1][0], parts[2])
        self.assertEqual(len(result.sessions), 39)
        self.assertEqual([identity_key(fact["identity"]) for fact in result.nonmembers], [excluded])
        self.assertEqual(facade.snapshot(), owner.sync_active_projection)
