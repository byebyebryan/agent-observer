"""Source-only material admission; no installed/proof/native acceptance claim."""

import copy
import hashlib
import unittest
import weakref
from contextlib import contextmanager
from unittest.mock import patch

from test_service_state import provider_snapshot

from agent_observer import timing
from agent_observer.contract import ContractError, identity_key, validate_record
from agent_observer.service_state import ServiceState
from agent_observer.sync_commitment import body_id, frame, value_hash
from agent_observer.sync_commitment import field_token as native_field_token
from agent_observer.sync_contract import admit_record as native_admit_record
from agent_observer.sync_contract import join_record, split_record
from agent_observer.sync_native import parse_message

try:
    from mesh_plus.protocol import ProtocolError
    from mesh_plus.sync.cache import OwnedSyncCache, ViewRef, source_binding
    from mesh_plus.sync.canonical import Atom, canonical
    from mesh_plus.sync.commitment import ABSENT, MerkleMap, binding_digest, native_root
    from mesh_plus.sync.context import ObjectRef
    from mesh_plus.sync.model import NativeTag
    from mesh_plus.sync.reconstruction import (
        BudgetRef,
        Operation,
        PublicOperation,
        PublicStateRef,
        ReconstructionStore,
    )

    from agent_observer.mesh_sync_profile import (
        ACTIVE_PROFILE_ID,
        FULL_PROFILE_ID,
        AgentSyncProfile,
        _observation_rule,
        _row_rule,
    )
except ModuleNotFoundError as error:
    if error.name != "mesh_plus" and not error.name.startswith("mesh_plus."):
        raise
    HAS_MESH_SYNC = False
else:
    HAS_MESH_SYNC = True


def restamp(message):
    """Forge a correctly committed synthetic native state, not a bad hash."""
    maps = {name: MerkleMap.baseline(name, entries)
            for name, entries in message["tables"].items()}
    binding = binding_digest(message["nativeBinding"], native=True).hex()
    generation = message["tag"][1]
    root = native_root(message["nativeBinding"], generation, maps).hex()
    message["tag"] = [binding, generation, root]
    message["cursor"] = [message["nativeBinding"]["ownerEpoch"], generation, root]
    return message


def stage(store, message):
    if message["kind"] == "baseline":
        return store.stage_baseline(message["nativeBinding"], NativeTag.parse(message["tag"]),
                                    tuple(message["cursor"]), message["tables"])
    operations = []
    for space, values in message["operations"].items():
        for item in values:
            op, key, expected = item[:3]
            value = Atom.own(item[3]) if op == "put" else None
            operations.append(Operation(space, op, Atom.own(key), expected, value))
    return store.stage_delta(NativeTag.parse(message["baseTag"]),
                             NativeTag.parse(message["resultTag"]),
                             tuple(message["resultCursor"]), operations)


def observation_transaction(baseline, observations):
    """Independent synthetic full-state oracle for a facet-only transaction."""
    target = copy.deepcopy(baseline)
    operations = {name: [] for name in baseline["tables"]}
    for entry in target["tables"]["observations"]:
        key, old = entry
        replacement = observations.get(canonical(key))
        if replacement is not None:
            operations["observations"].append(["put", copy.deepcopy(key),
                                                value_hash("observations", old), replacement])
            entry[1] = replacement
    target["tag"][1] += 1
    target = restamp(target)
    message = {"kind": "transaction", "descriptor": baseline["descriptor"],
               "nativeBindingDigest": baseline["tag"][0], "baseTag": baseline["tag"],
               "resultTag": target["tag"], "baseCursor": baseline["cursor"],
               "resultCursor": target["cursor"], "operations": operations}
    message["transactionId"] = hashlib.sha256(
        b"mesh-sync-transaction\0" + frame(canonical(message))).hexdigest()
    return message, target


@unittest.skipUnless(HAS_MESH_SYNC, "optional Mesh sync interface is unavailable")
class MeshSyncProfileTest(unittest.TestCase):
    def setUp(self):
        self.now = 15000
        self.stores = []
        self.caches = []

    def tearDown(self):
        for cache in self.caches:
            cache.close()
            self.assertEqual(cache.ledger.used, 0)
            self.assertEqual(cache.ledger.reserved, 0)
        for store in self.stores:
            store.close()

    def fixture(self, count=1):
        value = provider_snapshot("codex")
        first = value["sessions"][0]
        value["sessions"] = []
        for i in range(count):
            row = copy.deepcopy(first)
            row["identity"]["nativeId"] = row["nativeIds"]["threadId"] = (
                f"00000000-0000-4000-8000-{i + 1:012d}")
            value["sessions"].append(row)
        return value

    def owner(self, value=None):
        value = self.fixture() if value is None else value
        source = value["sources"][0]
        owner = ServiceState(
            host_scope="fixture", configs={"codex": (source["configHome"], source["configHomeKind"])},
            uid=1000, clock=lambda: self.now,
            boot_id="00000000-0000-4000-8000-000000000001", clock_domain="time:[123]",
        )
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        return owner

    def store(self, view="full"):
        profile = AgentSyncProfile(profile_schema_digest="a" * 64, view=view)
        store = ReconstructionStore(profile, host="fixture")
        self.stores.append(store)
        return store

    def baseline(self, owner, view="full"):
        return parse_message(owner.sync_baseline(view), view, "fixture")

    def changes(self, owner, view, base):
        target = owner.sync_current_tag(view)
        response = owner.sync_changes(view, base, target)
        self.assertIsInstance(response, tuple)
        messages = [parse_message(raw, view, "fixture") for raw in response]
        self.assertEqual(messages[-1]["kind"], "control")
        self.assertEqual(messages[-1]["status"], "complete")
        return [m for m in messages if m["kind"] == "transaction"]

    def owned_cache(self, view="full"):
        profile = AgentSyncProfile(profile_schema_digest="a" * 64, view=view)
        reader_time = [100000]
        clock = {"bootId": "reader-boot", "timeNamespace": "time:2"}
        binding = source_binding("fixture", "agents", profile.descriptor)
        request = {"readerEpoch": "r" * 32, "channelEpoch": "c" * 32,
                   "bridgeId": "b" * 32, "hosts": ["fixture"], "route": "fixed"}
        cache = OwnedSyncCache(profile, binding, request_binding=request,
                               _now_ms=lambda: reader_time[0], _clock=clock)
        self.caches.append(cache)
        return cache, reader_time, clock, binding, request

    def proof(self, cache, candidate, owner, view, binding, request):
        # The sole private call is test-owned proof-transport challenge setup,
        # matching Mesh's own cache tests. All state/head bytes come from the
        # native public source, never private cache roots or tables.
        challenge = cache._proof_request(candidate)
        head = parse_message(owner.sync_head(view, challenge), view, "fixture")
        bridge_time = head["ownerClock"]["boottimeMs"] + 10
        return {"protocol": "mesh.state-sync/1", "kind": "proof",
                "descriptor": cache.descriptor.wire(), "sourceBinding": binding,
                "sourceTag": candidate.tag.wire(), "requestBinding": request,
                "challenge": challenge, "bridgeId": request["bridgeId"],
                "bridgeClock": {"bootId": head["ownerClock"]["bootId"],
                                "timeNamespace": head["ownerClock"]["clockDomain"].replace("[", "").replace("]", ""),
                                "boottimeMs": bridge_time}, "head": head,
                "remaining": [[key, max(0, value["expiresBoottimeMs"] - bridge_time)
                               if value["health"] in {"current", "partial"} else 0]
                              for key, value in head["originalReceipts"]]}

    def confirm(self, cache, reader_time, clock, proof, candidate):
        reader_time[0] += 20
        return cache.confirm(candidate, canonical(proof), clock)

    def test_exact_owner_baseline_both_views_and_explicit_descriptor(self):
        owner = self.owner(self.fixture(3))
        for view, profile_id in (("full", FULL_PROFILE_ID), ("active", ACTIVE_PROFILE_ID)):
            message = self.baseline(owner, view)
            store = self.store(view)
            with patch("agent_observer.mesh_sync_profile.admit_record", wraps=native_admit_record) as validate:
                result = stage(store, message)
            self.assertEqual(result.tag.wire(), message["tag"])
            self.assertEqual(validate.call_count, 3)
            self.assertEqual(store.descriptor.profile_id, profile_id)
            self.assertEqual(len(store.descriptor.indexes), 8)
            profile = AgentSyncProfile(profile_schema_digest="a" * 64, view=view,
                                       native=message["descriptor"])
            self.assertEqual(profile.descriptor, store.descriptor)

    def test_baseline_detaches_one_body_at_a_time_under_pre_copy_reservation(self):
        owner = self.owner(self.fixture(12))
        for view in ("full", "active"):
            active, peak, count = [0], [0], [0]
            reservations, body_refs = [], set()
            materialize, reserve, lookup = ObjectRef.materialize, BudgetRef.reserve, PublicStateRef.lookup

            class Lifetime:
                pass

            def retired(active=active):
                active[0] -= 1

            def admitted(body, *args, active=active, peak=peak, count=count,
                         retired=retired, Lifetime=Lifetime):
                result = native_admit_record(body, *args)
                active[0] += 1
                peak[0] = max(peak[0], active[0])
                count[0] += 1
                # Added after independent admission, solely to observe the
                # detached input's lifetime; the immutable native body stays
                # untouched and the marker is absent from row/token outputs.
                marker = Lifetime()
                weakref.finalize(marker, retired)
                body["test_lifetime"] = marker
                return result

            def looked_up(ref, space, key, lookup=lookup, body_refs=body_refs):
                value = lookup(ref, space, key)
                if space == "bodies" and value is not ABSENT:
                    body_refs.add(id(value))
                return value

            @contextmanager
            def reserved(budget, amount, reserve=reserve, reservations=reservations):
                with reserve(budget, amount):
                    reservations.append(amount)
                    try:
                        yield
                    finally:
                        reservations.pop()

            def copied(ref, body_refs=body_refs, reservations=reservations,
                       active=active, materialize=materialize):
                if id(ref) in body_refs:
                    body_refs.remove(id(ref))
                    self.assertTrue(reservations)
                    self.assertGreaterEqual(reservations[-1], 4096 + 4 * ref.materialization_bytes)
                    self.assertEqual(active[0], 0, "previous detached body survives into the next row")
                return materialize(ref)

            with (patch.object(PublicStateRef, "lookup", looked_up),
                  patch.object(BudgetRef, "reserve", reserved),
                  patch.object(ObjectRef, "materialize", copied),
                  patch("agent_observer.mesh_sync_profile.admit_record", admitted)):
                stage(self.store(view), self.baseline(owner, view))
            self.assertEqual((count[0], peak[0], active[0]), (12, 1, 0))

    def test_same_digest_body_put_reuses_admission_without_body_copy(self):
        owner = self.owner()
        message = self.baseline(owner)
        store = self.store()
        stage(store, message)
        store.advance_material()
        tx, _ = observation_transaction(message, {})
        digest, body = message["tables"]["bodies"][0]
        tx["operations"]["bodies"] = [["put", digest, value_hash("bodies", body), body]]
        unsigned = {k: v for k, v in tx.items() if k != "transactionId"}
        tx["transactionId"] = hashlib.sha256(
            b"mesh-sync-transaction\0" + frame(canonical(unsigned))).hexdigest()
        lookup, value = PublicStateRef.lookup, PublicOperation.value

        def no_body_lookup(ref, space, key):
            self.assertNotEqual(space, "bodies")
            return lookup(ref, space, key)

        def no_body_value(op):
            self.assertNotEqual(op.space, "bodies")
            return value.fget(op)

        with (patch.object(PublicStateRef, "lookup", no_body_lookup),
              patch.object(PublicOperation, "value", property(no_body_value)),
              patch("agent_observer.mesh_sync_profile.admit_record", side_effect=AssertionError("readmit"))):
            stage(store, tx)

    def test_body_reservation_rejection_precedes_detached_copy(self):
        owner, store = self.owner(), self.store()
        lookup, materialize, reserve = PublicStateRef.lookup, ObjectRef.materialize, BudgetRef.reserve
        requested, copied = [False], [False]
        body_refs = set()

        def looked_up(ref, space, key):
            value = lookup(ref, space, key)
            if space == "bodies" and value is not ABSENT:
                requested[0] = True
                body_refs.add(id(value))
            return value

        @contextmanager
        def rejected(budget, amount):
            if requested[0]:
                raise ProtocolError("test_pre_copy_capacity")
            with reserve(budget, amount):
                yield

        def detached(ref):
            if id(ref) in body_refs:
                copied[0] = True
            return materialize(ref)

        with (patch.object(PublicStateRef, "lookup", looked_up),
              patch.object(BudgetRef, "reserve", rejected),
              patch.object(ObjectRef, "materialize", detached)):
            with self.assertRaisesRegex(ProtocolError, "test_pre_copy_capacity"):
                stage(store, self.baseline(owner))
        self.assertTrue(requested[0])
        self.assertFalse(copied[0])
        self.assertIsNone(store.candidate)
        # Mesh may retain bounded, charged decoder memo entries after rejected
        # admission. Closing the store must retire those and all reservations.
        store.close()
        self.assertEqual(store.ledger.used, 0)
        self.assertEqual(store.ledger.reserved, 0)

    def test_warming_empty_baselines_are_material_only(self):
        owner = ServiceState(host_scope="fixture", configs={"codex": ("/fixture/codex", "explicit")},
                             uid=1000, clock=lambda: self.now,
                             boot_id="00000000-0000-4000-8000-000000000001", clock_domain="time:[123]")
        for view in ("full", "active"):
            message = self.baseline(owner, view)
            result = stage(self.store(view), message)
            self.assertEqual(result.tag.wire(), message["tag"])

    def test_public_order_index_matches_native_order_through_runtime_transition(self):
        value = self.fixture(4)
        value["sessions"][2].update(phase=None, blockedReasons=[])
        value["sessions"][2]["runtime"]["value"] = "parked"
        owner = self.owner(value)
        stores, tags, expected, captured = {}, {}, {}, {}
        for view in ("full", "active"):
            seen = []

            class Probe(AgentSyncProfile):
                def stage_delta(self, ctx, seen=seen):
                    # Explicit metered output in this independent test probe;
                    # production sparse admission never iterates this index.
                    seen.append(list(ctx.before.index("order").iter_keys()))
                    return super().stage_delta(ctx)

            store = ReconstructionStore(Probe(profile_schema_digest="a" * 64, view=view), host="fixture")
            self.stores.append(store)
            baseline = self.baseline(owner, view)
            rows = (owner.snapshot if view == "full" else owner.active_projection)["sessions"]
            expected[view] = [[int(row["runtime"]["value"] != "running") if view == "full" else 0,
                               list(identity_key(row["identity"]))] for row in rows]
            stage(store, baseline)
            store.advance_material()
            stores[view], tags[view], captured[view] = store, baseline["tag"], seen
        value["sessions"][0].update(phase=None, blockedReasons=[])
        value["sessions"][0]["runtime"]["value"] = "parked"
        self.now += 1
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        for view, store in stores.items():
            message, = self.changes(owner, view, tags[view])
            stage(store, message)
            store.advance_material()
            self.assertEqual(captured[view].pop(), expected[view])
            rows = (owner.snapshot if view == "full" else owner.active_projection)["sessions"]
            expected[view] = [[int(row["runtime"]["value"] != "running") if view == "full" else 0,
                               list(identity_key(row["identity"]))] for row in rows]
            tags[view] = message["resultTag"]
        owner.attempt("codex", "runtime")
        for view, store in stores.items():
            message, = self.changes(owner, view, tags[view])
            stage(store, message)
            self.assertEqual(captured[view].pop(), expected[view])

    def test_sparse_body_and_observation_change_validates_one_joined_row(self):
        value = self.fixture(8)
        owner = self.owner(value)
        store = self.store()
        baseline = self.baseline(owner)
        stage(store, baseline)
        store.advance_material()
        self.now += 1
        value["sessions"][0]["title"] = "changed synthetic title"
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        messages = self.changes(owner, "full", baseline["tag"])
        self.assertEqual(len(messages), 1)
        with patch("agent_observer.mesh_sync_profile.admit_record", wraps=native_admit_record) as validate:
            with patch("agent_observer.sync_contract.validate_record", wraps=validate_record) as schema:
                with patch("agent_observer.mesh_sync_profile.field_token", wraps=native_field_token) as token:
                    result = stage(store, messages[0])
        self.assertEqual(validate.call_count, 1)
        self.assertEqual(schema.call_count, 1)
        self.assertEqual(token.call_count, 9)
        self.assertEqual(result.tag.wire(), messages[0]["resultTag"])

    def test_receipt_diagnostics_do_not_revisit_rows(self):
        work = []
        for count in (1, 32):
            owner = self.owner(self.fixture(count))
            store = self.store()
            baseline = self.baseline(owner)
            stage(store, baseline)
            store.advance_material()
            owner.attempt("codex", "runtime")
            messages = self.changes(owner, "full", baseline["tag"])
            self.assertEqual(len(messages), 1)
            self.assertFalse(messages[0]["operations"]["records"])
            with patch("agent_observer.mesh_sync_profile.admit_record", wraps=native_admit_record) as validate:
                with patch("agent_observer.mesh_sync_profile.field_token", wraps=native_field_token) as token:
                    stage(store, messages[0])
            self.assertEqual(validate.call_count, 0)
            self.assertEqual(token.call_count, 0)
            work.append(store.last_work["callbackLookups"])
        self.assertEqual(work[0], work[1])

    def test_native_n_row_timestamp_refresh_never_reads_or_validates_stable_bodies(self):
        count = 32
        for view in ("full", "active"):
            value = self.fixture(count)
            owner = self.owner(value)
            store = self.store(view)
            baseline = self.baseline(owner, view)
            stage(store, baseline)
            store.advance_material()
            for i, row in enumerate(value["sessions"]):
                row["runtime"]["observedAt"] += 100 + i
                row["phase"]["observedAt"] = row["runtime"]["observedAt"]
            self.now += 1
            owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
            messages = self.changes(owner, view, baseline["tag"])
            self.assertEqual(len(messages), 1)
            self.assertFalse(messages[0]["operations"]["bodies"])
            self.assertEqual(len(messages[0]["operations"]["observations"]), count)
            lookup = PublicStateRef.lookup

            def no_body_lookup(ref, space, key, lookup=lookup):
                self.assertNotEqual(space, "bodies", "unchanged stable body lookup")
                return lookup(ref, space, key)

            with patch.object(PublicStateRef, "lookup", no_body_lookup):
                with patch("agent_observer.mesh_sync_profile.admit_record", side_effect=AssertionError("body admission/join/extraction")):
                    with patch("agent_observer.sync_contract.validate_record", side_effect=AssertionError("body validation")):
                        with patch("agent_observer.mesh_sync_profile.field_token", side_effect=AssertionError("body token hash")):
                            result = stage(store, messages[0])
            self.assertEqual(result.tag.wire(), messages[0]["resultTag"])
            # Explicit linear test oracle joins original content with the new
            # native facets, independently of the compact admission rule.
            after = self.baseline(owner, view)
            self.assertEqual(baseline["tables"]["bodies"], after["tables"]["bodies"])
            bodies = dict(baseline["tables"]["bodies"])
            facets = {canonical(key): observation for key, observation in after["tables"]["observations"]}
            metadata = dict(after["tables"]["metadata"])
            sources = metadata["snapshot"]["sources"] if view == "full" else metadata["validationSources"]
            expected = {row["identity"]["nativeId"]: row["runtime"]["observedAt"] for row in value["sessions"]}
            for identity, slot in after["tables"]["records"]:
                row = join_record(bodies[slot["body"]], facets[canonical([identity, slot["birth"]])]["fields"])
                validate_record(row, "fixture", sources)
                self.assertEqual(row["runtime"]["observedAt"], expected[identity[4]])

    def test_compact_facet_rule_matches_independent_full_semantics(self):
        base = self.fixture()["sessions"][0]
        source = self.fixture()["sources"][0]
        source["capabilities"]["timing"] = {"lastUpdated": True, "latestTurn": True}
        variants = [copy.deepcopy(base)]
        null_activity = copy.deepcopy(base)
        null_activity["activity"]["lastKnownAt"] = None
        variants.append(null_activity)
        known = copy.deepcopy(base)
        known["activity"].update(at=1000, source=base["runtime"]["source"], health="current")
        known["outcome"].update(value="completed", observedAt=1000, source=base["runtime"]["source"],
                                health="current", clock="native")
        known["lastUpdated"] = {"at": 1000, "timestampPrecisionMs": 1, "observedAt": 3000,
                                "source": base["runtime"]["source"], "health": "current",
                                "reason": "native_fixture", "receipt": None}
        known["latestTurn"] = {"value": {"id": "turn-1", "status": "completed", "startedAt": 1000,
                                         "completedAt": 2000, "durationMs": 1000, "timestampPrecisionMs": 1},
                               "observedAt": 3000, "source": base["runtime"]["source"],
                               "health": "current", "reason": "native_fixture", "receipt": None}
        variants.append(known)
        stale = copy.deepcopy(known)
        stale["activity"].update(at=None, lastKnownAt=1000, health="stale")
        for name in ("lastUpdated", "latestTurn"):
            stale[name] = timing.stale(stale[name], name, "fixture_expired")
        variants.append(stale)
        parked = copy.deepcopy(base)
        parked["runtime"]["value"] = "parked"
        parked.update(phase=None, blockedReasons=[], hasSavedHistory=True)
        variants.append(parked)
        unknown_phase = copy.deepcopy(base)
        unknown_phase["phase"].update(value="unknown", health="unavailable", source=None,
                                       observedAt=None, clock=None)
        unknown_phase["blockedReasons"] = []
        variants.append(unknown_phase)
        cases = 0
        for row in variants:
            validate_record(row, "fixture", [source])
            content, original = split_record(row)
            rule = _row_rule(row)
            changes = []
            for name in original:
                for health in ("current", "stale", "unavailable", "unsupported"):
                    fields = copy.deepcopy(original)
                    fields[name]["health"] = health
                    changes.append(fields)
                if "observedAt" in original[name]:
                    for observed in (None, 0, 999):
                        fields = copy.deepcopy(original)
                        fields[name]["observedAt"] = observed
                        changes.append(fields)
            for name in ("lastUpdated", "latestTurn"):
                fields = copy.deepcopy(original)
                fields[name]["receipt"] = {"component": "runtime", "sampledBoottimeMs": 10,
                                             "observedBoottimeMs": 9, "contextGeneration": 0}
                changes.append(fields)
            for fields in changes:
                try:
                    validate_record(join_record(content, fields), "fixture", [source])
                    expected = True
                except ContractError:
                    expected = False
                try:
                    _observation_rule(fields, rule, source)
                    actual = True
                except (ContractError, ProtocolError):
                    actual = False
                self.assertEqual(actual, expected, (row["runtime"]["value"], fields))
                cases += 1
        self.assertGreater(cases, 200)

    def test_forged_observation_only_facet_fails_without_body_fallback(self):
        owner = self.owner()
        baseline = self.baseline(owner)
        ref, observation = baseline["tables"]["observations"][0]
        # Observation DTO has explicit fields/supports; the native content is
        # unchanged and still positively running.
        forged = copy.deepcopy(observation)
        forged["fields"]["runtime"]["health"] = "stale"
        message, _ = observation_transaction(baseline, {canonical(ref): forged})
        store = self.store()
        stage(store, baseline)
        store.advance_material()
        with patch("agent_observer.mesh_sync_profile.admit_record", side_effect=AssertionError("body fallback")):
            with self.assertRaisesRegex(ProtocolError, "missing_evidence_provenance"):
                stage(store, message)

    def test_observation_ref_cannot_abandon_an_unchanged_current_cell(self):
        owner = self.owner()
        baseline = self.baseline(owner)
        ref, observation = baseline["tables"]["observations"][0]
        forged = copy.deepcopy(observation)
        current_field = next(name for name, support in forged["supports"].items()
                             if support is not None and support[0] == "cohort")
        forged["supports"][current_field] = None
        message, _ = observation_transaction(baseline, {canonical(ref): forged})
        store = self.store()
        stage(store, baseline)
        store.advance_material()
        with patch("agent_observer.mesh_sync_profile.admit_record", side_effect=AssertionError("body fallback")):
            with self.assertRaisesRegex(ProtocolError, "agent_sync_unreferenced_membership"):
                stage(store, message)

    def test_partial_subset_retains_old_context_without_membership_renewal(self):
        value = self.fixture(2)
        owner = self.owner(value)
        for view in ("full", "active"):
            store = self.store(view)
            baseline = self.baseline(owner, view)
            stage(store, baseline)
            store.advance_material()
            subset = copy.deepcopy(value)
            subset["sessions"] = subset["sessions"][:1]
            subset["sources"][0]["coverage"]["runtime"].update(status="partial", reason="bounded_census")
            self.now += 1
            owner.accept("codex", "runtime", subset, sampled_ms=self.now, ttl_ms=10000)
            messages = self.changes(owner, view, baseline["tag"])
            for message in messages:
                stage(store, message)
            self.assertEqual(store.candidate.tag.wire(), messages[-1]["resultTag"])
            if view == "full":
                current = self.baseline(owner, view)
                refs = [v["supports"] for _, v in current["tables"]["observations"]]
                self.assertTrue(any(any(ref and ref[0] == "context" for ref in fields.values()) for fields in refs))

    def test_active_ledger_exact_cap_tracks_receipt_digit_width_without_row_walk(self):
        value = self.fixture(2)
        owner = self.owner(value)
        for _ in range(8):
            self.now += 1
            owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        before_bytes = len(canonical(owner.active_projection["scopes"]))
        baseline = self.baseline(owner, "active")
        store = self.store("active")
        with patch("agent_observer.mesh_sync_profile.MAX_LEDGER_BYTES", before_bytes):
            stage(store, baseline)
        store.advance_material()
        self.now += 1
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        after_bytes = len(canonical(owner.active_projection["scopes"]))
        self.assertGreater(after_bytes, before_bytes)
        messages = self.changes(owner, "active", baseline["tag"])
        self.assertEqual(len(messages), 1)
        with patch("agent_observer.mesh_sync_profile.MAX_LEDGER_BYTES", after_bytes - 1):
            with self.assertRaisesRegex(ProtocolError, "agent_sync_ledger_capacity"):
                stage(store, messages[0])
        self.assertEqual(store.current.tag.wire(), baseline["tag"])
        with patch("agent_observer.mesh_sync_profile.MAX_LEDGER_BYTES", after_bytes):
            with patch("agent_observer.mesh_sync_profile.admit_record", wraps=native_admit_record) as validate:
                stage(store, messages[0])
        self.assertEqual(validate.call_count, 0)

    def test_record_removal_prunes_indexes_and_reinsertion_has_new_birth(self):
        value = self.fixture()
        owner = self.owner(value)
        for view in ("full", "active"):
            store = self.store(view)
            baseline = self.baseline(owner, view)
            stage(store, baseline)
            store.advance_material()
            empty = copy.deepcopy(value)
            empty["sessions"] = []
            self.now += 1
            owner.accept("codex", "runtime", empty, sampled_ms=self.now, ttl_ms=10000)
            removed = self.changes(owner, view, baseline["tag"])
            for message in removed:
                stage(store, message)
            store.advance_material()
            base = removed[-1]["resultTag"]
            self.now += 1
            owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
            inserted = self.changes(owner, view, base)
            for message in inserted:
                stage(store, message)
            result = self.baseline(owner, view)
            self.assertNotEqual(result["tables"]["records"][0][1]["birth"],
                                baseline["tables"]["records"][0][1]["birth"])

    def test_active_negative_becomes_uncertain_after_unrelated_partial_receipt(self):
        value = self.fixture()
        owner = self.owner(value)
        store = self.store("active")
        baseline = self.baseline(owner, "active")
        stage(store, baseline)
        store.advance_material()
        value["sessions"][0]["kind"] = "child"
        self.now += 1
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        negative = self.changes(owner, "active", baseline["tag"])
        for message in negative:
            stage(store, message)
        store.advance_material()
        self.assertEqual(len(owner.active_projection["scopes"][0]["nonmembers"]), 1)
        value["sessions"] = []
        value["sources"][0]["coverage"]["runtime"].update(status="partial", reason="bounded_census")
        self.now += 1
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        for message in self.changes(owner, "active", negative[-1]["resultTag"]):
            stage(store, message)
        scope = owner.active_projection["scopes"][0]
        self.assertEqual(scope["nonmembers"], [])
        self.assertEqual(len(scope["uncertain"]), 1)

    def test_expired_complete_census_is_context_and_does_not_block_material_update(self):
        for view in ("full", "active"):
            owner = self.owner()
            store = self.store(view)
            baseline = self.baseline(owner, view)
            stage(store, baseline)
            store.advance_material()
            self.now += 10001
            owner.expire(self.now)
            messages = self.changes(owner, view, baseline["tag"])
            for message in messages:
                stage(store, message)
            self.assertEqual(store.candidate.tag.wire(), messages[-1]["resultTag"])

    def test_profile_rejects_generation_jump_even_if_generic_engine_accepts_it(self):
        owner = self.owner()
        store = self.store()
        baseline = self.baseline(owner)
        stage(store, baseline)
        store.advance_material()
        owner.attempt("codex", "runtime")
        message = self.changes(owner, "full", baseline["tag"])[0]
        message["resultTag"][1] += 1
        message["resultCursor"][1] += 1
        with self.assertRaisesRegex(ProtocolError, "agent_sync_transaction_generation"):
            stage(store, message)

    def test_forged_birth_or_alias_identity_and_orphan_observation_fail(self):
        message = self.baseline(self.owner(self.fixture(2)))
        for mutate in (
            lambda m: m["tables"]["records"][0][1]["birth"].__setitem__(0, "00000000-0000-4000-8000-000000000099"),
            lambda m: m["tables"]["records"][1][1].update(alias=m["tables"]["records"][0][1]["alias"]),
            lambda m: m["tables"]["observations"][0][0][1].__setitem__(1, 0),
            lambda m: m["tables"]["records"][0][1].update(scope=["codex", "sha256:" + "a" * 64]),
        ):
            forged = copy.deepcopy(message)
            mutate(forged)
            with self.assertRaises((ProtocolError, ContractError)):
                stage(self.store(), restamp(forged))

    def test_orphan_stable_body_rejected_even_with_correct_body_and_native_roots(self):
        message = self.baseline(self.owner())
        orphan = copy.deepcopy(message["tables"]["bodies"][0][1])
        orphan["identity"]["nativeId"] = orphan["nativeIds"]["threadId"] = "00000000-0000-4000-8000-000000000099"
        profile = self.store().profile
        digest = body_id(profile.descriptor.native_descriptor_digest, orphan)
        message["tables"]["bodies"].append([digest, orphan])
        with self.assertRaisesRegex(ProtocolError, "(agent_)?sync_(dangling_record|orphan_body)"):
            stage(self.store(), restamp(message))

    def test_wrong_field_token_missing_cell_and_unreferenced_cell_rejected(self):
        original = self.baseline(self.owner())
        forged = copy.deepcopy(original)
        forged["tables"]["memberships"][0][1] = "f" * 64
        with self.assertRaisesRegex(ProtocolError, "agent_sync_member_token"):
            stage(self.store(), restamp(forged))
        forged = copy.deepcopy(original)
        forged["tables"]["memberships"].pop()
        with self.assertRaisesRegex(ProtocolError, "agent_sync_member_token"):
            stage(self.store(), restamp(forged))
        forged = copy.deepcopy(original)
        cell = forged["tables"]["memberships"][0]
        field = cell[0][3]
        for _, observation in forged["tables"]["observations"]:
            if observation["supports"][field] is not None:
                observation["supports"][field] = None
        with self.assertRaisesRegex(ProtocolError, "agent_sync_unreferenced_membership"):
            stage(self.store(), restamp(forged))

    def test_retained_context_cannot_name_another_incarnation_or_future_accept(self):
        value = self.fixture(2)
        owner = self.owner(value)
        self.now += 1
        value["sessions"] = value["sessions"][:1]
        value["sources"][0]["coverage"]["runtime"].update(status="partial", reason="bounded_census")
        owner.accept("codex", "runtime", value, sampled_ms=self.now, ttl_ms=10000)
        original = self.baseline(owner)
        for name, replacement in (("serviceId", "00000000-0000-4000-8000-000000000099"), ("accepted", 100)):
            forged = copy.deepcopy(original)
            changed = False
            for _, observation in forged["tables"]["observations"]:
                for ref in observation["supports"].values():
                    if ref is not None and ref[0] == "context":
                        ref[1][name] = replacement
                        changed = True
            self.assertTrue(changed)
            with self.assertRaises((ProtocolError, ContractError)):
                stage(self.store(), restamp(forged))

    def test_active_members_require_matching_scope_and_complete_coverage_support(self):
        original = self.baseline(self.owner(), "active")
        for mutate in (
            lambda m: m["tables"]["scopes"].__setitem__(slice(None), [e for e in m["tables"]["scopes"] if len(e[0]) == 3]),
            lambda m: next(v for k, v in m["tables"]["scopes"] if len(k) == 3)["coverage"].update(supports=[]),
            lambda m: next(v for k, v in m["tables"]["scopes"] if len(k) == 4)["fields"].update(runtime=None),
        ):
            forged = copy.deepcopy(original)
            mutate(forged)
            with self.assertRaises((ProtocolError, ContractError)):
                stage(self.store("active"), restamp(forged))

    def test_boolean_order_and_malformed_coverage_reason_are_not_equal_wire_values(self):
        message = self.baseline(self.owner())
        message["tables"]["records"][0][1]["order"][0] = False
        with self.assertRaisesRegex(ProtocolError, "agent_sync_order_key"):
            stage(self.store(), restamp(message))
        message = self.baseline(self.owner(), "active")
        next(v for k, v in message["tables"]["scopes"] if len(k) == 3)["coverage"]["reason"] = True
        with self.assertRaises(ContractError):
            stage(self.store("active"), restamp(message))

    def test_descriptor_construction_is_explicit(self):
        profile = self.store().profile
        with self.assertRaisesRegex(ProtocolError, "agent_sync_export_view"):
            profile.export_committed(None)
        with self.assertRaises(ProtocolError):
            AgentSyncProfile(profile_schema_digest="bad")
        native = copy.deepcopy(self.baseline(self.owner())["descriptor"])
        native["view"] = "active"
        with self.assertRaises(ProtocolError):
            AgentSyncProfile(profile_schema_digest="a" * 64, native=native)

    def test_owned_confirmation_uses_strict_bounded_head_and_detached_exact_full_export(self):
        owner = self.owner(self.fixture(3))
        expected = copy.deepcopy(owner.snapshot)
        cache, reader_time, clock, binding, request = self.owned_cache()
        candidate = cache.admit_baseline(owner.sync_baseline("full"))
        with self.assertRaisesRegex(ProtocolError, "sync_unconfirmed"):
            cache.acquire()
        proof = self.proof(cache, candidate, owner, "full", binding, request)
        lookup = ViewRef.lookup

        def no_bodies(view, space, key):
            self.assertNotIn(space, {"records", "bodies", "observations", "memberships", "scopes"})
            return lookup(view, space, key)

        with patch.object(ViewRef, "lookup", no_bodies):
            with patch("agent_observer.mesh_sync_profile.admit_record", side_effect=AssertionError("head body work")):
                view = self.confirm(cache, reader_time, clock, proof, candidate)
        context = view.context(reader_time[0], clock)
        runtime = next(r for r in context["receipts"] if r["key"][2] == "runtime")
        self.assertTrue(runtime["current"])
        original = dict((tuple(k), v) for k, v in proof["head"]["originalReceipts"])[tuple(runtime["key"])]
        self.assertEqual(runtime["valueHash"], value_hash("receipts", original))
        exported = view.export_committed()
        self.assertEqual(exported, expected)
        exported["sessions"][0]["title"] = "caller mutation"
        exported["sources"].clear()
        self.assertEqual(view.export_committed(), expected)

    def test_owned_head_reconfirmation_does_not_renew_original_expiry(self):
        owner = self.owner()
        cache, reader_time, clock, binding, request = self.owned_cache()
        candidate = cache.admit_baseline(owner.sync_baseline("full"))
        first = self.confirm(cache, reader_time, clock,
                             self.proof(cache, candidate, owner, "full", binding, request), candidate)
        expiry = next(r["expiresMs"] for r in first.context(reader_time[0], clock)["receipts"]
                      if r["key"][2] == "runtime")
        self.now += 1000
        reader_time[0] = 101000
        second = self.confirm(cache, reader_time, clock,
                              self.proof(cache, candidate, owner, "full", binding, request), candidate)
        runtime = next(r for r in second.context(reader_time[0], clock)["receipts"]
                       if r["key"][2] == "runtime")
        self.assertEqual(runtime["expiresMs"], expiry)
        self.assertFalse(next(r for r in second.context(expiry, clock)["receipts"]
                              if r["key"][2] == "runtime")["current"])
        self.assertEqual(second.export_committed(), owner.snapshot)

    def test_owned_expired_head_confirms_context_without_current_receipts(self):
        owner = self.owner()
        expected = copy.deepcopy(owner.snapshot)
        cache, reader_time, clock, binding, request = self.owned_cache()
        candidate = cache.admit_baseline(owner.sync_baseline("full"))
        self.now += 10001  # Head is a cached read; deliberately no expire/publish.
        proof = self.proof(cache, candidate, owner, "full", binding, request)
        view = self.confirm(cache, reader_time, clock, proof, candidate)
        self.assertTrue(all(not r["current"] for r in view.context(reader_time[0], clock)["receipts"]))
        self.assertEqual(view.export_committed(), expected)

    def test_owned_head_schema_receipt_cohort_and_clock_corruption_fail_closed(self):
        for mutate in (
            lambda p: p["head"].update(extra="forbidden"),
            lambda p: p["head"]["ownerClock"].update(boottimeMs=14999),
            lambda p: p["head"]["ownerClock"].update(clockDomain="time:[999]"),
            lambda p: p["head"]["originalReceipts"][0][1].update(accepted=999),
            lambda p: p["head"]["cohortHeads"][0][1]["seal"].__setitem__(1, "f" * 64),
        ):
            owner = self.owner()
            cache, reader_time, clock, binding, request = self.owned_cache()
            candidate = cache.admit_baseline(owner.sync_baseline("full"))
            proof = self.proof(cache, candidate, owner, "full", binding, request)
            mutate(proof)
            with self.assertRaises((ProtocolError, ContractError)):
                self.confirm(cache, reader_time, clock, proof, candidate)
            with self.assertRaisesRegex(ProtocolError, "sync_unconfirmed"):
                cache.acquire()

    def test_owned_disconnect_revokes_public_context_lookup_iterator_and_export(self):
        owner = self.owner()
        cache, reader_time, clock, binding, request = self.owned_cache()
        candidate = cache.admit_baseline(owner.sync_baseline("full"))
        view = self.confirm(cache, reader_time, clock,
                            self.proof(cache, candidate, owner, "full", binding, request), candidate)
        iterator = view.index("order").iter_keys()
        record = view.lookup("records", self.baseline(owner)["tables"]["records"][0][0])
        with self.assertRaisesRegex(ProtocolError, "sync_reader_clock"):
            view.context(reader_time[0] - 1, clock)
        cache.disconnect()
        for operation in (lambda: view.context(reader_time[0], clock), view.export_committed,
                          lambda: next(iterator), record.materialize):
            with self.assertRaisesRegex(ProtocolError, "sync_view_retired"):
                operation()

    def test_owned_active_confirmation_and_explicit_export_use_public_scope_index(self):
        owner = self.owner(self.fixture(2))
        cache, reader_time, clock, binding, request = self.owned_cache("active")
        candidate = cache.admit_baseline(owner.sync_baseline("active"))
        view = self.confirm(cache, reader_time, clock,
                            self.proof(cache, candidate, owner, "active", binding, request), candidate)
        self.assertEqual(view.export_committed(), owner.active_projection)


if __name__ == "__main__":
    unittest.main()
