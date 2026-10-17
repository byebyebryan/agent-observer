"""Independent exact framing vectors and bounded persistent-map mutations."""

import gc
import hashlib
import itertools
import json
import random
import sys
import tracemalloc
import types
import unittest
import weakref
from collections.abc import Mapping
from types import MappingProxyType
from unittest.mock import patch

from agent_observer import sync_commitment as sync


def reference_canonical(value):
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode()


def reference_frame(value):
    return len(value).to_bytes(8, "big") + value


def reference_root(space, entries):
    """Deliberately independent full-sort oracle, never the production path."""
    raw_space = space.encode()
    rows = []
    for key, value in entries:
        key_bytes = reference_canonical(key)
        key_hash = hashlib.sha256(
            b"mesh-sync-key\0" + reference_frame(raw_space) + reference_frame(key_bytes)
        ).digest()
        value_hash = hashlib.sha256(
            b"mesh-sync-value\0"
            + reference_frame(raw_space)
            + reference_frame(reference_canonical(value))
        ).digest()
        leaf = hashlib.sha256(
            b"mesh-sync-leaf\0"
            + reference_frame(raw_space)
            + key_hash
            + reference_frame(key_bytes)
            + value_hash
        ).digest()
        rows.append((key_hash, leaf))
    rows.sort()

    def commit(items):
        if len(items) == 1:
            return items[0][1]
        first, last = int.from_bytes(items[0][0], "big"), int.from_bytes(items[-1][0], "big")
        split = 256 - (first ^ last).bit_length()
        prefix_size = (split + 7) // 8
        prefix = ((first >> (256 - split)) << (prefix_size * 8 - split)).to_bytes(
            prefix_size, "big"
        )
        boundary = next(
            index
            for index, (key_hash, _) in enumerate(items)
            if (int.from_bytes(key_hash, "big") >> (255 - split)) & 1
        )
        return hashlib.sha256(
            b"mesh-sync-branch\0"
            + reference_frame(raw_space)
            + split.to_bytes(2, "big")
            + reference_frame(prefix)
            + commit(items[:boundary])
            + commit(items[boundary:])
        ).digest()

    return (
        commit(rows)
        if rows
        else hashlib.sha256(b"mesh-sync-empty\0" + reference_frame(raw_space)).digest()
    ).hex()


class CanonicalTest(unittest.TestCase):
    def test_repeated_json_helpers_retire_scratch_with_cyclic_gc_disabled(self):
        enabled = gc.isenabled()
        gc.collect()
        gc.disable()
        tracemalloc.start()
        try:
            for index in range(200):
                value = {"nested": [index, None, {"text": "é" * 32}]}
                frozen = sync.freeze(value)
                self.assertEqual(sync.thaw(sync.freeze_reusing(value, frozen)), value)
                sync.canonical(frozen)
            del value, frozen
            retained, _peak = tracemalloc.get_traced_memory()
            self.assertLess(retained, 64 * 1024)
        finally:
            tracemalloc.stop()
            if enabled:
                gc.enable()

    def test_freeze_reusing_shares_only_unchanged_prior_paths(self):
        prior = sync.freeze(
            {
                "identity": ["host", "provider", "namespace", "thread", "id"],
                "runtime": {"value": "running", "source": "native"},
                "lastUpdated": {"at": 100, "source": "native"},
            }
        )
        incoming = sync.thaw(prior)
        incoming["lastUpdated"]["at"] = 101
        result = sync.freeze_reusing(incoming, prior)
        self.assertIsNot(result, prior)
        self.assertIs(result["identity"], prior["identity"])
        self.assertIs(result["runtime"], prior["runtime"])
        self.assertIsNot(result["lastUpdated"], prior["lastUpdated"])
        self.assertEqual(prior["lastUpdated"]["at"], 100)
        incoming["runtime"]["value"] = "mutated"
        incoming["identity"].append("mutated")
        self.assertEqual(result["runtime"]["value"], "running")
        self.assertEqual(len(result["identity"]), 5)
        self.assertIs(sync.freeze_reusing(sync.thaw(prior), prior), prior)
        # Key iteration order is not a different canonical object value.
        self.assertIs(
            sync.freeze_reusing(dict(reversed(list(sync.thaw(prior).items()))), prior), prior
        )

    def test_freeze_reusing_obeys_typed_json_and_validates_all_inputs(self):
        for value, earlier in (
            (True, 1),
            (1, True),
            (None, {}),
            ({}, []),
            ([], {}),
            ({"missing": None}, {}),
            ({}, {"missing": None}),
            ("é", "e\u0301"),
            ([1, 2], [2, 1]),
        ):
            with self.subTest(value=value, earlier=earlier):
                old = sync.freeze(earlier)
                result = sync.freeze_reusing(value, old)
                self.assertEqual(sync.canonical(result), sync.canonical(value))
                self.assertNotEqual(sync.canonical(result), sync.canonical(old))
        old = sync.freeze([1, {"x": [True, None]}])
        self.assertIs(sync.freeze_reusing((1, {"x": (True, None)}), old), old)
        mutable_prior = {"x": [1]}
        result = sync.freeze_reusing({"x": [1]}, mutable_prior)
        mutable_prior["x"].append(2)
        self.assertEqual(sync.thaw(result), {"x": [1]})
        cycle = []
        cycle.append(cycle)
        for invalid in (cycle, {"x": cycle}, {"x": 1.0}, {"x": "\ud800"}, {1: "key"}):
            with self.assertRaises(ValueError):
                sync.freeze_reusing(invalid, old)
        with self.assertRaises(ValueError):
            sync.freeze_reusing({}, cycle)
        self.assertEqual(sync.thaw(sync.freeze_reusing({"x": [1]}, sync.ABSENT)), {"x": [1]})

    def test_unicode_short_escapes_scalar_order_and_absence_are_exact(self):
        value = {"z": None, "é": "é\n", "a": True}
        self.assertEqual(
            sync.canonical(value).hex(),
            "7b2261223a747275652c227a223a6e756c6c2c22c3a9223a22c3a95c6e227d",
        )
        self.assertEqual(
            sync.canonical("\b\f\n\r\t\0\x1f/é"), b'"\\b\\f\\n\\r\\t\\u0000\\u001f/\xc3\xa9"'
        )
        self.assertNotEqual(sync.canonical({}), sync.canonical({"optional": None}))
        self.assertNotEqual(sync.canonical(True), sync.canonical(1))
        self.assertNotEqual(sync.canonical("é"), sync.canonical("e\u0301"))
        self.assertEqual(
            sync.canonical({"\U00010000": 1, "\ue000": 2}), '{"\ue000":2,"\U00010000":1}'.encode()
        )

    def test_mapping_freeze_reuses_minted_subvalues_and_owns_mutable_inputs(self):
        original = {"nested": [1, {"x": "value"}]}
        proxy = MappingProxyType(original)
        frozen = sync.freeze(proxy)
        self.assertIs(sync.freeze(frozen), frozen)
        nested = sync.freeze(["identity", 1])
        parent = sync.freeze((nested, nested))
        self.assertIs(parent[0], nested)
        self.assertIs(parent[1], nested)
        original["nested"][1]["x"] = "changed"
        self.assertEqual(sync.thaw(frozen), {"nested": [1, {"x": "value"}]})
        with self.assertRaises(TypeError):
            frozen["new"] = 2
        with self.assertRaises(AttributeError):
            parent.extra = []
        detached = sync.thaw(frozen)
        detached["nested"].append(3)
        self.assertEqual(len(frozen["nested"]), 2)

    def test_strict_json_rejects_unsupported_types_cycles_duplicates_and_surrogates(self):
        cycle = []
        cycle.append(cycle)

        class DuplicateMapping(Mapping):
            def __iter__(self):
                return iter(("same", "same"))

            def __len__(self):
                return 2

            def __getitem__(self, key):
                return 1

        for value in (
            1.0,
            float("nan"),
            float("inf"),
            b"bytes",
            {1: "key"},
            "\ud800",
            cycle,
            DuplicateMapping(),
        ):
            with self.subTest(value=type(value).__name__), self.assertRaises(ValueError):
                sync.canonical(value)
        for raw in (
            b'{"a":1,"a":2}',
            b"1.0",
            b"1e0",
            b"NaN",
            b"Infinity",
            b"-0",
            b'"\\ud800"',
            b'"\xff"',
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                sync.parse(raw)
        self.assertEqual(sync.thaw(sync.parse(b' { "a": 1 } ')), {"a": 1})
        with self.assertRaisesRegex(ValueError, "noncanonical"):
            sync.parse(b' { "a": 1 } ', require_canonical=True)
        self.assertEqual(sync.canonical(sync.parse(b'{"a":1}', require_canonical=True)), b'{"a":1}')

    def test_exact_binary_framing_and_u64_boundaries(self):
        self.assertEqual(sync.frame(b"abc"), b"\0\0\0\0\0\0\0\x03abc")
        self.assertEqual(sync.unframe(sync.frame(b"")), b"")
        self.assertEqual(sync.u64(sync.U64_MAX), b"\xff" * 8)
        for value in (-1, True, sync.U64_MAX + 1):
            with self.assertRaises(ValueError):
                sync.u64(value)
        for value in (b"", b"\0" * 7, b"\0" * 8 + b"extra", b"\xff" * 8):
            with self.assertRaises(ValueError):
                sync.unframe(value)


class ExactVectorsTest(unittest.TestCase):
    def test_all_twenty_pinned_appendix_hash_vectors(self):
        a = sync.PersistentMap("records", (("a", {"body": "A"}),))
        b = sync.PersistentMap("records", (("b", {"body": "B"}),))
        ab = a.put("b", {"body": "B"}, expected=None)
        ba = b.put("a", {"body": "A"}, expected=None)
        binding = {"contract": "fixture", "host": "h", "owner": "o", "view": "full"}
        source = {"host": "h", "profile": "proposal", "source": "s"}
        summary = [["records", ab.root, ab.count]]
        native = sync.native_root(binding, 2, summary)
        receipt1 = sync.PersistentMap("receipts", (("r", {"accepted": 1}),))
        receipt2 = receipt1.put("r", {"accepted": 2})
        identity = ["h", "codex", "ns", "thread", "id"]
        cohort1 = sync.PersistentMap(
            "cohort-members", (((identity, ("o", 1), "runtime"), "11" * 32),)
        )
        cohort2 = sync.PersistentMap(
            "cohort-members", (((identity, ("o", 2), "runtime"), "11" * 32),)
        )
        actual = {
            "empty": sync.empty_root("records"),
            "K(a)": sync.key_hash("records", "a"),
            "K(b)": sync.key_hash("records", "b"),
            "L(a,A)": a.root,
            "L(b,B)": b.root,
            "root(a,b)": ab.root,
            "root(b,a)": ba.root,
            "replace": ab.put("a", {"body": "A2"}).root,
            "delete": ab.remove("b").root,
            "NativeRoot": native,
            "owner=o2": sync.native_root({**binding, "owner": "o2"}, 2, summary),
            "SourceRoot": sync.source_root(source, native),
            "source=s2": sync.source_root({**source, "source": "s2"}, native),
            "non-byte": a.put("c", {"body": "C"}).root,
            "receipt1 map": receipt1.root,
            "receipt2 map": receipt2.root,
            "receipt1 all": sync.native_root(
                binding, 2, [["receipts", receipt1.root, 1], *summary]
            ),
            "receipt2 all": sync.native_root(
                binding, 2, [["receipts", receipt2.root, 1], *summary]
            ),
            "cohort1": cohort1.root,
            "cohort2": cohort2.root,
        }
        expected = {
            "empty": "eeb50b54d1d8075c3a13e3c3d8fbe7c51995bad9129f80e4de7e1b6ce3d6c587",
            "K(a)": "ce82c5b724b7c17d4d8ceb7c1b6e5c50115c60572ae3a6863eb2466a3a2e0c9c",
            "K(b)": "13d1c83070beb5be53fc138e46af5044b5968fcd458a302c42aaf6eeeeab31cd",
            "L(a,A)": "e6656cee7d68057ea405fe79d91dfca8d73242361a402ce86c7ec8df3fb895ac",
            "L(b,B)": "ba716d28870d9878937cb24f5b2f1bf6a946c1f01018b87eb7fcfad4b70588b3",
            "root(a,b)": "d9d6043d34003e0962032d529fd5ee197a02fe7818b7e91f01563826c914034f",
            "root(b,a)": "d9d6043d34003e0962032d529fd5ee197a02fe7818b7e91f01563826c914034f",
            "replace": "60c4c18888def3635a595751bf82e9160a019f4a7ce19a620a5c2b5f60f40419",
            "delete": "e6656cee7d68057ea405fe79d91dfca8d73242361a402ce86c7ec8df3fb895ac",
            "NativeRoot": "5b7ca726bb1e93e425752f9d2c742c80131b1fab11fb57f8940c815b84f3eb0f",
            "owner=o2": "e3f480295ecf19e68520ffbdd1e3f937c6cac9c0d0eeb88f9df26f164f81954d",
            "SourceRoot": "8ad9669a41a79d9df2d397a1233418ac739bd5d8d8a3b83ae1393e68b863882a",
            "source=s2": "71dfd4b47c9316613ab4f5d5fda282fb939bfdd96a85bf3de3f238b368d80d77",
            "non-byte": "28143b1ae65c68223f645cb7d988eb6b1e79fba5d9e9705055a3908e190ff560",
            "receipt1 map": "3ef6dffb3d5d4fa791ad6e1c04553d1e9d0233e155d3a41aae2f6ebbcd0d1aee",
            "receipt2 map": "bd2704bfd2239abdb8903145e17879db02e29e4fc00131b45123b422795a4235",
            "receipt1 all": "2485b2dceba1daadcc49da715c99346ebd6466083dbe0603dde3e2b7edc6f43a",
            "receipt2 all": "2e3531e0db82dc02bb9ef0e34d020c8b91b0a7f07c4df6f387686efb6b8d0642",
            "cohort1": "f7e17cab2df897006e1a7d89363c6b433c29f81273619eb0e8b729440df2e814",
            "cohort2": "e11a69eecb1dbba9d8bec87ff55c5562a0cb579c3259ab306fd03e9c8ab95941",
        }
        self.assertEqual(len(actual), 20)
        self.assertEqual(actual, expected)

    def test_descriptor_body_field_and_binding_tags_are_independently_framed(self):
        descriptor = {"schema": 1, "view": "full", "unicode": "é"}
        raw_descriptor = hashlib.sha256(reference_canonical(descriptor)).digest()
        desc = raw_descriptor.hex()
        content = {"kind": "user", "runtime": {"value": "running"}}
        identity, birth = ["h", "codex", "ns", "thread", "id"], ["owner", sync.U64_MAX]
        value = {"value": "running", "optional": None}
        expected_body = hashlib.sha256(
            b"mesh-sync-body\0"
            + reference_frame(raw_descriptor)
            + reference_frame(reference_canonical(content))
        ).hexdigest()
        expected_token = hashlib.sha256(
            b"mesh-sync-field\0"
            + reference_frame(raw_descriptor)
            + reference_frame(reference_canonical(identity))
            + reference_frame(reference_canonical(birth))
            + reference_frame(b"runtime")
            + reference_frame(reference_canonical(value))
        ).hexdigest()
        self.assertEqual(sync.descriptor_digest(descriptor), desc)
        self.assertEqual(sync.body_id(desc, content), expected_body)
        self.assertEqual(sync.field_token(desc, identity, birth, "runtime", value), expected_token)
        self.assertNotEqual(
            sync.field_token(desc, identity, ["owner", 1], "runtime", value), expected_token
        )
        binding = {"context": None, "owner": "one"}
        self.assertEqual(
            sync.native_binding_digest(binding),
            hashlib.sha256(
                b"mesh-sync-native-binding\0" + reference_frame(reference_canonical(binding))
            ).hexdigest(),
        )
        self.assertEqual(
            sync.source_binding_digest(binding),
            hashlib.sha256(
                b"mesh-sync-source-binding\0" + reference_frame(reference_canonical(binding))
            ).hexdigest(),
        )
        with self.assertRaises(ValueError):
            sync.body_id("sha256:" + desc, content)
        with self.assertRaises(ValueError):
            sync.field_token(desc, identity, ["owner", True], "runtime", value)


class PersistentMapTest(unittest.TestCase):
    def test_patch_rebuilds_union_once_for_all_changed_leaves(self):
        for count in (100, 500, 2000):
            with self.subTest(count=count):
                entries = [(str(index), {"n": index}) for index in range(count)]
                tree = sync.PersistentMap("records", entries)
                operations = [
                    ("put", key, sync.value_hash("records", value), {"n": -value["n"] - 1})
                    for key, value in entries
                ]
                with (
                    patch.object(
                        sync.PersistentMap, "items", side_effect=AssertionError("full export")
                    ),
                    patch.object(
                        sync.PersistentMap,
                        "encoded_items",
                        side_effect=AssertionError("full export"),
                    ),
                    patch.object(
                        sync.PersistentMap, "_find", side_effect=AssertionError("per-key search")
                    ),
                ):
                    updated = tree.patch(reversed(operations))
                expected = [(key, {"n": -value["n"] - 1}) for key, value in entries]
                self.assertEqual(updated.root, reference_root("records", expected))
                self.assertEqual(tree.root, reference_root("records", entries))
                self.assertEqual(updated.last_update.created_nodes, 2 * count - 1)
                self.assertEqual(updated.last_update.hashes, 4 * count - 1)
                self.assertEqual(updated.last_update.visits, 4 * count - 2)
                self.assertEqual(updated.last_update.enumerated_keys, count)
                self.assertEqual(updated.account.snapshot()["byKind"]["stage"], 0)

    def test_patch_sparse_changes_preserve_untouched_subtrees(self):
        tree = sync.PersistentMap("records", ((str(index), index) for index in range(2000)))
        entries = list(tree.items())
        # One affected path; every sibling object remains the identical subtree.
        key, old = entries[531]
        updated = tree.patch([("put", key, sync.value_hash("records", old), -1)])
        before, after = tree._node, updated._node
        digest = bytes.fromhex(sync.key_hash("records", key))
        while isinstance(before, sync._Branch):
            if sync._bit(digest, before.split):
                self.assertIs(before.left, after.left)
                before, after = before.right, after.right
            else:
                self.assertIs(before.right, after.right)
                before, after = before.left, after.left
        self.assertLess(updated.last_update.created_nodes, 30)
        self.assertLess(updated.last_update.visits, 60)
        self.assertEqual(updated.last_update.enumerated_keys, 1)
        self.assertEqual(tree.get(key), old)

    def test_patch_changed_path_union_counts_for_sparse_cluster(self):
        tree = sync.PersistentMap("records", ((str(index), index) for index in range(500)))
        keys = [str(index) for index in range(10, 30)]
        union = set()
        for key in keys:
            digest = bytes.fromhex(sync.key_hash("records", key))
            node = tree._node
            while node is not None:
                union.add(id(node))
                if isinstance(node, sync._Leaf):
                    break
                node = node.right if sync._bit(digest, node.split) else node.left
        changed = tree.patch([("put", key, tree.get_hash(key), -1) for key in keys])
        self.assertEqual(changed.last_update.created_nodes, len(union))
        self.assertEqual(changed.last_update.visits, 2 * len(union))
        self.assertLess(len(union), len(keys) * 10)

    def test_patch_mixed_insert_delete_collapse_nonbyte_and_typed_keys(self):
        tree = sync.PersistentMap(
            "records",
            (("a", {"body": "A"}), ("c", {"body": "C"}), (None, None), (True, "bool"), (1, "int")),
        )
        updated = tree.patch(
            [
                ("remove", "a", sync.value_hash("records", {"body": "A"})),
                ("put", "c", sync.value_hash("records", {"body": "C"}), {"body": "C2"}),
                ("put", ["new", None], None, {"mutable": [1]}),
                ("remove", True, sync.value_hash("records", "bool")),
                ("put", {}, None, None),
            ]
        )
        expected = [
            ("c", {"body": "C2"}),
            (None, None),
            (1, "int"),
            (["new", None], {"mutable": [1]}),
            ({}, None),
        ]
        self.assertEqual(updated.root, reference_root("records", expected))
        self.assertEqual(updated.count, 5)
        removed = updated.patch([("remove", key, updated.get_hash(key)) for key, _ in expected])
        self.assertEqual(removed.root, sync.empty_root("records"))
        self.assertEqual(removed.count, 0)
        self.assertEqual(removed.last_update.created_nodes, 0)

    def test_patch_checks_all_expected_before_creating_nodes_and_rejects_duplicates(self):
        tree = sync.PersistentMap("records", (("a", 1), ("b", 2)))
        original = tree.root
        rejected = [
            [("put", "a", tree.get_hash("a"), 3), ("remove", "b", "0" * 64)],
            [("put", "a", None, 3)],
            [("remove", "missing", "0" * 64)],
            [("put", "missing", "0" * 64, 3)],
            [("remove", "b", None)],
            [("put", "a", sync.ANY, 3)],
            [("remove", "a")],
            [("unknown", "a", None)],
            [("put", [1, None], None, 3), ("put", (1, None), None, 4)],
            [("remove", "a", tree.get_hash("a")), ("put", "a", tree.get_hash("a"), 3)],
        ]
        for operations in rejected:
            with (
                self.subTest(operations=operations),
                patch.object(
                    sync.PersistentMap,
                    "_entry",
                    side_effect=AssertionError("node before admission"),
                ),
                self.assertRaises(sync.CommitmentError),
            ):
                tree.patch(operations)
            self.assertEqual(tree.root, original)
            self.assertEqual(tree.get("a"), 1)
        for operations in (None, 1, "", b"", {}):
            with self.assertRaisesRegex(ValueError, "patch_operations"):
                tree.patch(operations)
        with patch.object(sync, "_key_digest", return_value=b"x" * 32):
            colliding = sync.PersistentMap("collision", (("a", 1),))
            with self.assertRaisesRegex(ValueError, "collision"):
                colliding.patch([("put", "b", None, 2)])
            with self.assertRaisesRegex(ValueError, "collision"):
                sync.PersistentMap("collision").patch(
                    [("put", "a", None, 1), ("put", "b", None, 2)]
                )

    def test_patch_noops_empty_inputs_and_mutable_inputs_are_safe(self):
        tree = sync.PersistentMap("records", ((["key"], {"nested": [1]}),))
        same = tree.patch([("put", ["key"], tree.get_hash(["key"]), {"nested": [1]})])
        self.assertIs(same._node, tree._node)
        self.assertFalse(same.last_update.changed)
        self.assertEqual(same.last_update.created_nodes, 0)
        self.assertIs(tree.patch([])._node, tree._node)
        key, value = ["new"], {"nested": [1]}
        inserted = tree.patch([("put", key, None, value)])
        key.append("changed")
        value["nested"].append(2)
        self.assertEqual(sync.thaw(inserted.get(["new"])), {"nested": [1]})
        frozen = sync.freeze({"first": 1, "second": 2})
        with patch.object(
            sync._FrozenObject,
            "__getitem__",
            side_effect=AssertionError("quadratic Mapping fallback"),
        ):
            self.assertEqual(list(frozen.items()), [("first", 1), ("second", 2)])
            self.assertEqual(list(frozen.values()), [1, 2])

    def test_patch_handles_full_256_bit_boundary_and_compressed_replacement(self):
        def digest(space, raw):
            number = json.loads(raw)
            return (0 if number == 0 else 1 << (256 - number)).to_bytes(32, "big")

        with patch.object(sync, "_key_digest", side_effect=digest):
            tree = sync.PersistentMap("boundary", ((number, number) for number in range(257)))
            changed = tree.patch(
                [("put", number, tree.get_hash(number), -number - 1) for number in (0, 1, 128, 256)]
            )
            self.assertEqual(changed.get(0), -1)
            self.assertEqual(changed.get(128), -129)
            removed = changed.patch(
                [("remove", number, changed.get_hash(number)) for number in range(257)]
            )
            self.assertEqual(removed.count, 0)
            self.assertEqual(removed.root, sync.empty_root("boundary"))
            self.assertEqual(tree.get(0), 0)

    def test_randomized_batches_match_independent_full_oracle(self):
        rng, model, tree = random.Random(841), {}, sync.PersistentMap("patch-random")
        prior = []
        for generation in range(40):
            keys = rng.sample(range(80), rng.randrange(1, 21))
            operations = []
            prior.append((tree, tree.root))
            for number in keys:
                key = str(number)
                if key in model and rng.randrange(3) == 0:
                    operations.append(
                        ("remove", key, sync.value_hash("patch-random", model.pop(key)))
                    )
                else:
                    expected = sync.value_hash("patch-random", model[key]) if key in model else None
                    model[key] = {"generation": generation}
                    operations.append(("put", key, expected, model[key]))
            tree = tree.patch(operations)
            self.assertEqual(tree.root, reference_root("patch-random", model.items()))
            self.assertEqual(tree.count, len(model))
        for old, root in prior:
            self.assertEqual(old.root, root)

    def test_bulk_initial_build_creates_each_node_and_hash_once(self):
        entries = [(str(index), {"n": index}) for index in range(500)]
        with patch.object(
            sync.PersistentMap, "_find", side_effect=AssertionError("point insertion")
        ):
            tree = sync.PersistentMap("records", reversed(entries))
        self.assertEqual(tree.root, reference_root("records", entries))
        self.assertEqual(tree.last_update.created_nodes, 999)
        self.assertEqual(tree.last_update.hashes, 2000)
        self.assertEqual(tree.last_update.visits, 0)
        self.assertEqual(tree.last_update.enumerated_keys, 500)
        self.assertEqual(tree.account.snapshot()["byKind"]["stage"], 0)

    def test_insert_order_full_oracle_and_delete_collapses_unique_shape(self):
        entries = [(str(index), {"n": index}) for index in range(6)]
        expected = reference_root("records", entries)
        for order in itertools.permutations(entries):
            self.assertEqual(sync.PersistentMap("records", order).root, expected)
        original = sync.PersistentMap("records", entries)
        for key, _ in reversed(entries):
            previous = original
            original = original.remove(key)
            entries = [(k, v) for k, v in entries if k != key]
            self.assertEqual(original.root, reference_root("records", entries))
            self.assertEqual(previous.count, original.count + 1)
            self.assertEqual(original.node_count, 2 * original.count - 1 if original.count else 0)

    def test_non_byte_prefix_padding_and_full_256_ancestor_boundary(self):
        nonbyte = sync.PersistentMap("records", (("a", {"body": "A"}), ("c", {"body": "C"})))
        self.assertEqual(nonbyte._node.split, 2)
        self.assertEqual(nonbyte._node.prefix, b"\xc0")

        def digest(space, raw):
            number = json.loads(raw)
            return (0 if number == 0 else 1 << (256 - number)).to_bytes(32, "big")

        with patch.object(sync, "_key_digest", side_effect=digest):
            tree = sync.PersistentMap("boundary", ((number, number) for number in range(257)))
            updated = tree.put(0, "changed")
            self.assertEqual(updated.last_update.path_visits, 256)
            self.assertEqual(updated.last_update.leaf_visits, 1)
            self.assertEqual(updated.last_update.visits, 257)
            self.assertEqual(updated.last_update.created_nodes, 257)
            self.assertEqual(tree.get(0), 0)
            self.assertEqual(updated.get(0), "changed")
            removed = updated.remove(0)
            self.assertEqual(removed.count, 256)
            self.assertLessEqual(removed.last_update.path_visits, 256)

    def test_expected_hash_absence_duplicates_collision_and_prior_roots(self):
        tree = sync.PersistentMap("records", (("a", {"v": 1}),))
        root = tree.root
        updated = tree.put("a", {"v": 2}, expected=sync.value_hash("records", {"v": 1}))
        self.assertEqual(tree.root, root)
        self.assertEqual(sync.thaw(tree.get("a")), {"v": 1})
        self.assertEqual(sync.thaw(updated.get("a")), {"v": 2})
        self.assertIs(tree.get("absent"), sync.ABSENT)
        self.assertEqual(tree.get("absent", "default"), "default")
        for action in (
            lambda: tree.put("a", 1, expected=None),
            lambda: tree.put("a", 1, expected="0" * 64),
            lambda: tree.remove("a", expected="0" * 64),
            lambda: tree.remove("a", expected=None),
            lambda: tree.remove("absent"),
            lambda: sync.PersistentMap("records", (("a", 1), ("a", 1))),
        ):
            with self.assertRaises(ValueError):
                action()
        with patch.object(sync, "_key_digest", return_value=b"x" * 32):
            colliding = sync.PersistentMap("records", (("a", 1),))
            for action in (
                lambda: colliding.put("b", 2),
                lambda: colliding.get("b"),
                lambda: colliding.remove("b"),
                lambda: sync.PersistentMap("records", (("a", 1), ("b", 2))),
            ):
                with self.assertRaisesRegex(ValueError, "collision"):
                    action()

    def test_typed_keys_and_present_null_remain_distinct_from_absence(self):
        entries = ((None, "null"), (True, "boolean"), (1, "integer"), ([], "array"), ({}, "object"))
        tree = sync.PersistentMap("typed", entries)
        self.assertEqual(tree.count, 5)
        for key, expected in entries:
            self.assertEqual(tree.get(key), expected)
        null = sync.PersistentMap("typed", MappingProxyType({"key": None}))
        self.assertIsNone(null.get("key"))
        self.assertIs(null.get("missing"), sync.ABSENT)
        removed = null.remove("key", expected=sync.value_hash("typed", None))
        self.assertEqual(removed.count, 0)
        with self.assertRaisesRegex(ValueError, "duplicate"):
            sync.PersistentMap("typed", (([1, None], 1), ((1, None), 2)))

    def test_sparse_counts_at_100_500_2000_do_not_export_or_rebuild(self):
        for count in (100, 500, 2000):
            with self.subTest(count=count):
                entries = [("id-" + str(index), {"n": index}) for index in range(count)]
                tree = sync.PersistentMap("records", entries)
                self.assertEqual(tree.last_update.enumerated_keys, count)
                original = tree.root
                with (
                    patch.object(
                        sync.PersistentMap, "items", side_effect=AssertionError("full export")
                    ),
                    patch.object(
                        sync.PersistentMap,
                        "encoded_items",
                        side_effect=AssertionError("full export"),
                    ),
                ):
                    updated = tree.put("id-5", {"n": -5})
                    removed = updated.remove("id-6")
                for changed in (updated, removed):
                    stats = changed.last_update
                    self.assertLessEqual(stats.visits, 257)
                    self.assertLess(stats.visits, count // 2)
                    self.assertLessEqual(stats.hashes, stats.path_visits + 3)
                    self.assertLessEqual(stats.created_nodes, stats.path_visits + 1)
                    self.assertEqual(stats.enumerated_keys, 0)
                expected = [
                    (key, {"n": -5} if key == "id-5" else value)
                    for key, value in entries
                    if key != "id-6"
                ]
                self.assertEqual(removed.root, reference_root("records", expected))
                self.assertEqual(tree.root, original)
                self.assertEqual(tree.count, count)
                self.assertEqual(removed.count, count - 1)

    def test_encoded_size_cached_bytes_and_explicit_export_meter(self):
        tree = sync.PersistentMap("records", (("é", {"n": 1}), (("nested", 2), [None, True])))
        meter = sync.VisitMeter()
        pairs = list(tree.encoded_items(meter=meter))
        encoded = b"[" + b",".join(b"[" + key + b"," + value + b"]" for key, value in pairs) + b"]"
        self.assertEqual(tree.encoded_size, len(encoded))
        self.assertEqual(meter.iterations, tree.count)
        self.assertEqual(meter.visits, tree.node_count)
        self.assertEqual(sync.PersistentMap("empty").encoded_size, 2)
        self.assertEqual(tree.meter.iterations, 0)
        self.assertEqual(len(list(tree.items())), 2)
        self.assertEqual(tree.meter.iterations, 2)
        self.assertTrue(tree.check_summary(tree.root, tree.count))
        for root, count in (("0" * 64, tree.count), (tree.root, tree.count + 1), (tree.root, True)):
            with self.assertRaises(ValueError):
                tree.check_summary(root, count)

    def test_lookup_returns_cached_hash_in_one_metered_traversal(self):
        tree = sync.PersistentMap("records", (("key", {"nested": [1, None]}),))
        meter = sync.VisitMeter()
        with patch.object(sync, "_value_digest", side_effect=AssertionError("rehashed value")):
            value, digest = tree.lookup("key", meter=meter)
            self.assertEqual(tree.get_hash("key"), digest)
        self.assertEqual(sync.thaw(value), {"nested": [1, None]})
        self.assertEqual(digest, sync.value_hash("records", {"nested": [1, None]}))
        self.assertEqual(meter.lookups, 1)
        self.assertEqual(meter.visits, 1)
        self.assertEqual(meter.hashes, 1)
        self.assertIs(tree.lookup("missing"), sync.ABSENT)

    def test_lookup_entry_and_encoded_bytes_share_owned_immutable_storage(self):
        key = sync.freeze(["identity", 1])
        tree = sync.PersistentMap("records", ((key, {"nested": [1, None]}),))
        with patch.object(sync, "_value_digest", side_effect=AssertionError("rehashed value")):
            owned_key, owned_value, digest, key_bytes, value_bytes = tree.lookup_entry(key)
            encoded = tree.lookup_encoded(key)
        self.assertIs(owned_key, key)
        self.assertIs(owned_value, tree.get(key))
        self.assertIs(encoded[0], key_bytes)
        self.assertIs(encoded[1], value_bytes)
        self.assertEqual(digest, sync.value_hash("records", owned_value))
        self.assertEqual(
            (key_bytes, value_bytes), (sync.canonical(key), sync.canonical(owned_value))
        )
        self.assertIs(tree.lookup_entry("missing"), sync.ABSENT)
        self.assertIs(tree.lookup_encoded("missing"), sync.ABSENT)

    def test_equal_value_noop_does_not_rehash_or_allocate_entry_nodes(self):
        tree = sync.PersistentMap("records", (("key", {"n": 1}),))
        with patch.object(
            sync, "_value_digest", side_effect=AssertionError("rehashed unchanged value")
        ):
            same = tree.put("key", MappingProxyType({"n": 1}))
        self.assertEqual(same.root, tree.root)
        self.assertFalse(same.last_update.changed)
        self.assertEqual(same.last_update.created_nodes, 0)
        self.assertEqual(same.last_update.hashes, 1)

    def test_randomized_sparse_mutations_match_independent_full_tree(self):
        rng, model = random.Random(731), {}
        tree = sync.PersistentMap("random")
        previous = []
        for step in range(120):
            key = str(rng.randrange(40))
            previous.append((tree, tree.root))
            if key in model and rng.randrange(3) == 0:
                tree = tree.remove(key, expected=sync.value_hash("random", model.pop(key)))
            else:
                model[key] = {"step": step, "maybe": None}
                tree = tree.put(key, model[key])
            self.assertEqual(tree.root, reference_root("random", model.items()))
        for old, root in previous:
            self.assertEqual(old.root, root)

    def test_native_summary_requires_sorted_complete_registry_and_u64_generation(self):
        empty = sync.PersistentMap("empty")
        summary = [["empty", empty.root, 0]]
        self.assertNotEqual(
            sync.native_root({}, 0, summary), sync.native_root({}, sync.U64_MAX, summary)
        )
        for values in (
            [["empty", "0" * 64, 0]],
            [["empty", empty.root, 1]],
            [["z", sync.empty_root("z"), 0], *summary],
            [*summary, *summary],
        ):
            with self.assertRaises(ValueError):
                sync.native_root({}, 0, values)
        with self.assertRaises(ValueError):
            sync.native_root({}, 0, summary, expected_spaces=("empty", "missing"))
        with self.assertRaises(ValueError):
            sync.native_root({}, sync.U64_MAX + 1, summary)


class AllocationTest(unittest.TestCase):
    def test_released_reservation_does_not_keep_account_alive(self):
        account = sync.AllocationAccount()
        reference = weakref.ref(account)
        lease = account.reserve(4096)
        lease.release()
        del account
        self.assertIsNone(reference())
        lease.release()

    def test_immutable_buffer_aliases_share_heap_until_the_last_delivery_pin(self):
        account = sync.AllocationAccount()
        body = bytes(bytearray(b"native-buffer" * 1000))
        copied = bytes(bytearray(body))
        self.assertIsNot(body, copied)
        owner = account.retain_bytes(body, size=128)
        first = account.snapshot()
        peer = account.retain_bytes(body, body, size=128, kind="queue")
        self.assertEqual(account.snapshot()["objects"], first["objects"])
        self.assertLess(account.snapshot()["used"] - first["used"], len(body))
        distinct = account.retain_bytes(copied)
        self.assertEqual(account.snapshot()["objects"], first["objects"] + 1)
        owner.release()
        distinct.release()
        self.assertEqual(account.snapshot()["objects"], 1)
        self.assertGreaterEqual(account.snapshot()["used"], sys.getsizeof(body))
        peer.release()
        peer.release()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_constructor_buffer_credit_transfers_atomically_and_rejection_keeps_credit(self):
        account = sync.AllocationAccount(limit=65536)
        credit = account.reserve(20000, kind="encoded")
        body = bytes(bytearray(b"b" * 8192))
        lease = account.retain_bytes(body, size=128, credit=credit)
        self.assertEqual(credit._size, 0)
        credit.release()
        self.assertLess(account.snapshot()["used"], 20000 + account.snapshot()["base"])
        foreign = sync.AllocationAccount()
        other_credit = foreign.reserve(2000)
        before = account.snapshot()
        with self.assertRaisesRegex(ValueError, "allocation_credit"):
            account.retain_bytes(body, credit=other_credit)
        self.assertEqual(account.snapshot()["used"], before["used"])
        self.assertEqual(other_credit._size, 2000)
        with self.assertRaisesRegex(ValueError, "allocation_bytes"):
            account.retain_bytes(bytearray(body))
        other_credit.release()
        lease.release()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_bufferless_credit_still_charges_metadata_and_rejects_atomically(self):
        account = sync.AllocationAccount(limit=65536)
        credit = account.reserve(16000, kind="encoded")
        before = account.snapshot()
        with self.assertRaises(sync.BudgetExceeded):
            account.retain_bytes(size=account.limit, kind="queue", credit=credit)
        self.assertEqual(credit._size, 16000)
        self.assertEqual(account.snapshot(), before)
        lease = account.retain_bytes(size=4000, kind="queue", credit=credit)
        self.assertEqual(credit._size, 0)
        report = account.snapshot()
        self.assertEqual(report["objects"], 0)
        self.assertEqual(report["byKind"]["queue"], 4000)
        self.assertEqual(report["byKind"]["encoded"], 0)
        # Empty immutable payloads still retain both lease bookkeeping roots.
        self.assertEqual((report["leases"], report["allocations"]), (2, 2))
        self.assertGreater(report["used"], report["base"] + 4000)
        lease.release()
        credit.release()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])
        with self.assertRaisesRegex(ValueError, "allocation_credit"):
            account.retain_bytes(size=1, credit=credit)

    def test_budgeted_arena_priors_share_paths_and_reject_unowned_or_mutable_priors(self):
        account = sync.AllocationAccount()
        with account.json_arena() as arena:
            (old,) = arena.retain_json({"stable": [1, {"native": True}], "updated": {"at": 1}})
            incoming = sync.thaw(old)
            incoming["updated"]["at"] = 2
            (new,) = arena.retain_json(incoming, priors=(old,))
            self.assertIs(new["stable"], old["stable"])
            self.assertIsNot(new["updated"], old["updated"])
            self.assertEqual(new["updated"]["at"], 2)
            (same,) = arena.retain_json(sync.thaw(new), priors=(new,))
            self.assertIs(same, new)
            before = account.snapshot()["used"]
            for priors in (
                (),
                [old],
                (old, old),
                ({"mutable": []},),
                (sync.freeze({"unowned": 1}),),
            ):
                with self.assertRaisesRegex(ValueError, "arena_priors"):
                    arena.retain_json(incoming, priors=priors)
                self.assertEqual(account.snapshot()["used"], before)
            incoming["stable"].append("external mutation")
            self.assertEqual(len(new["stable"]), 2)
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_near_cap_analysis_rejects_before_frozen_construction_with_bounded_real_peak(self):
        account = sync.AllocationAccount(limit=65536)
        arena = account.json_arena()
        arena.retain_json({"retained": 1})
        incoming = {"native-field-" + str(index): index for index in range(1000)}
        before = account.snapshot()
        tracemalloc.start()
        try:
            with patch.object(
                sync,
                "_materialize_plan",
                side_effect=AssertionError("unfunded frozen construction"),
            ):
                with self.assertRaises(sync.BudgetExceeded):
                    arena.retain_json(incoming)
            _, peak = tracemalloc.get_traced_memory()
        finally:
            tracemalloc.stop()
        # Inputs predate tracing; this measures actual construction/analysis
        # allocations, not just a post-claim ledger or a size prediction.
        self.assertLessEqual(peak, account.limit - before["used"])
        self.assertEqual(account.snapshot()["used"], before["used"])
        self.assertEqual(account.snapshot()["objects"], before["objects"])
        self.assertEqual(len(arena._claims), 1)
        arena.close()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_arena_atomic_credit_equals_independently_measured_fresh_containers(self):
        account = sync.AllocationAccount()
        events = []
        original = sync.AllocationAccount._acquire

        def observe(current, size, kind, unique, **kwargs):
            credit = kwargs.get("credit")
            if credit is not None:
                pending = [value for value, _, _ in unique.values()]
                seen, actual = set(), 0
                while pending:
                    value = pending.pop()
                    if id(value) in seen or id(value) in current._held:
                        continue
                    seen.add(id(value))
                    if isinstance(value, sync._FrozenObject):
                        actual += sys.getsizeof(value) + sys.getsizeof(value._items)
                    elif isinstance(value, sync._FrozenArray):
                        actual += sys.getsizeof(value)
                    pending.extend(sync._owned_children(value))
                self.assertEqual(credit._size - kwargs["credit_keep"], actual + size)
                events.append(actual)
            result = original(current, size, kind, unique, **kwargs)
            if credit is not None:
                self.assertEqual(credit._size, kwargs["credit_keep"])
            return result

        with patch.object(sync.AllocationAccount, "_acquire", new=observe):
            with account.json_arena() as arena:
                (old,) = arena.retain_json({"native": [1, 2], "changed": {"at": 1}})
                arena.retain_json({"native": [1, 2], "changed": {"at": 2}}, priors=(old,))
        self.assertEqual(len(events), 2)
        self.assertGreater(events[0], events[1])
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_budgeted_arena_failed_adoption_reclaims_credit_and_keeps_prior_claims(self):
        account = sync.AllocationAccount()
        arena = account.json_arena()
        (old,) = arena.retain_json({"stable": [1, 2], "changed": {"at": 1}})
        before = account.snapshot()
        original = sync._IdentityIndex.growth_bound
        original_materialize = sync._materialize_plan
        materialized, caught = set(), None

        def reject_adoption(index, markers):
            if sys._getframe(1).f_locals.get("credit") is not None:
                return account.limit
            return original(index, markers)

        def observe_materialization(plan):
            result = original_materialize(plan)
            if (
                type(result) in (sync._FrozenObject, sync._FrozenArray)
                and id(result) not in account._held
            ):
                materialized.add(id(result))
            return result

        with (
            patch.object(sync._IdentityIndex, "growth_bound", new=reject_adoption),
            patch.object(sync, "_materialize_plan", new=observe_materialization),
        ):
            try:
                arena.retain_json({"stable": [1, 2], "changed": {"at": 2}}, priors=(old,))
            except sync.BudgetExceeded as error:
                caught = error
            else:
                self.fail("over-budget adoption accepted")
        self.assertTrue(materialized)
        # Retain the exception itself: its traceback must not become an
        # uncharged owner of the rejected frozen graph or scratch dictionaries.
        self.assertIsNotNone(caught.__traceback__)
        gc.collect()
        retained_frozen = {
            id(value)
            for value in gc.get_objects()
            if type(value) in (sync._FrozenObject, sync._FrozenArray)
        }
        self.assertFalse(materialized & retained_frozen)
        self.assertEqual(account.snapshot()["used"], before["used"])
        self.assertEqual(account.snapshot()["objects"], before["objects"])
        self.assertEqual(account._held[id(old)].refs, 1)
        self.assertEqual(len(arena._claims), 1)
        arena.close()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_arena_acquire_dictionary_scratch_fits_prepaid_envelope(self):
        account = sync.AllocationAccount()
        measured = []
        original = sync._IdentityIndex.growth_bound

        def inspect_scratch(index, markers):
            local = sys._getframe(1).f_locals
            if local.get("credit") is not None:
                json_ids, pending = set(), [value for value, _, _ in local["unique"].values()]
                while pending:
                    value = pending.pop()
                    if id(value) not in json_ids:
                        json_ids.add(id(value))
                        pending.extend(sync._owned_children(value))
                roots = [
                    local[name]
                    for name in ("unique", "planned", "pending", "increments", "new_encodings")
                ]
                seen, pending, actual = set(json_ids), roots, 0
                while pending:
                    value = pending.pop()
                    if id(value) in seen or isinstance(
                        value,
                        (
                            type,
                            types.ModuleType,
                            types.FunctionType,
                            types.BuiltinFunctionType,
                            types.CodeType,
                        ),
                    ):
                        continue
                    seen.add(id(value))
                    actual += sys.getsizeof(value)
                    pending.extend(gc.get_referents(value))
                self.assertLessEqual(actual, local["credit_keep"])
                measured.append(actual)
            return original(index, markers)

        with patch.object(sync._IdentityIndex, "growth_bound", new=inspect_scratch):
            with account.json_arena() as arena:
                arena.retain_json(
                    {"native": [{"number": n, "flag": bool(n % 2)} for n in range(50)]}
                )
        self.assertEqual(len(measured), 1)
        self.assertGreater(measured[0], 1000)
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_json_arena_owns_detached_roots_and_hands_off_shared_graphs_to_map(self):
        account = sync.AllocationAccount()
        base = account.snapshot()["used"]
        original_key, original_value = ["identity", 1], {"fact": [1, None]}
        arena = account.json_arena()
        key, value = arena.retain_json(original_key, original_value)
        self.assertEqual(account._held[id(value)].refs, 1)
        original_key.append("changed")
        original_value["fact"].append(2)
        tree = sync.PersistentMap("records", ((key, value),), account=account)
        self.assertEqual(account._held[id(value)].refs, 2)
        arena.close()
        arena.close()
        self.assertEqual(account._held[id(value)].refs, 1)
        self.assertEqual(sync.thaw(tree.get(["identity", 1])), {"fact": [1, None]})
        with self.assertRaises(ValueError):
            arena.retain_json("closed")
        del tree
        gc.collect()
        self.assertEqual(account.snapshot()["used"], base)

    def test_json_arena_rejections_preserve_prior_claims_and_eager_capacity(self):
        account = sync.AllocationAccount(limit=60000)
        with account.json_arena() as arena:
            (first,) = arena.retain_json({"first": 1})
            before = account.snapshot()
            cycle = []
            cycle.append(cycle)
            for invalid in (cycle, object()):
                with self.assertRaises(ValueError):
                    arena.retain_json("valid", invalid)
                self.assertEqual(account.snapshot()["used"], before["used"])
            with self.assertRaises(sync.BudgetExceeded):
                arena.retain_json("oversized" * 20000)
            self.assertEqual(account.snapshot()["used"], before["used"])
            self.assertEqual(account._held[id(first)].refs, 1)
            self.assertEqual(len(arena._claims), 1)
            with self.assertRaises(ValueError):
                arena.retain_json()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_json_arena_graph_is_fully_charged_without_row_leases_or_wrappers(self):
        account = sync.AllocationAccount()
        arena = account.json_arena()
        shared = sync.freeze({"shared": ["native", None]})
        for index in range(300):
            arena.retain_json(["identity", index], shared)
        self.assertEqual(account._held[id(shared)].refs, 300)
        report = account.snapshot()
        self.assertEqual(report["leases"], 1)
        self.assertEqual(report["allocations"], 301)
        self.assertEqual(len(arena._claims), 300)
        self.assertTrue(all(type(claim) is tuple for claim in arena._claims))
        seen, pending, actual = set(), [arena], 0
        while pending:
            value = pending.pop()
            if id(value) in seen or isinstance(
                value,
                (
                    type,
                    types.ModuleType,
                    types.FunctionType,
                    types.BuiltinFunctionType,
                    types.CodeType,
                ),
            ):
                continue
            seen.add(id(value))
            actual += sys.getsizeof(value)
            pending.extend(gc.get_referents(value))
        self.assertGreaterEqual(report["used"], actual)
        del arena
        gc.collect()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_patch_budget_rejection_reclaims_provisional_nodes_without_changing_root(self):
        account = sync.AllocationAccount(limit=100000)
        tree = sync.PersistentMap("records", (("a", "original"), ("b", 2)), account=account)
        before, root = account.snapshot(), tree.root
        try:
            tree.patch(
                [
                    ("put", "a", tree.get_hash("a"), {"replacement": [1]}),
                    ("put", "b", tree.get_hash("b"), "oversized" * 20000),
                ]
            )
            self.fail("over-budget patch accepted")
        except sync.BudgetExceeded:
            pass
        gc.collect()
        after = account.snapshot()
        self.assertEqual(tree.root, root)
        self.assertEqual(tree.get("a"), "original")
        self.assertEqual(tree.get("b"), 2)
        self.assertEqual(after["objects"], before["objects"])
        self.assertEqual(after["allocations"], before["allocations"])
        for kind in ("nodes", "containers", "value_bytes", "stage"):
            self.assertEqual(after["byKind"][kind], before["byKind"][kind])
        # A dict that grew during staging may retain real capacity; it stays
        # charged until the last owner disappears, rather than being hidden.
        self.assertEqual(
            after["used"] - before["used"], after["registryBytes"] - before["registryBytes"]
        )
        del tree
        gc.collect()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_index_growth_is_reserved_before_insertion_and_actual_capacity_is_charged(self):
        # Deliberately defeat the shard distribution. Capacity accounting must
        # still cover a large single shard and its sparse replacement churn.
        with patch.object(sync._IdentityIndex, "_bucket", return_value=0):
            account = sync.AllocationAccount()
            tree = sync.PersistentMap(
                "records", ((str(index), index) for index in range(300)), account=account
            )
            for index in range(40):
                tree = tree.put(str(index), {"generation": index})
                report = account.snapshot()
                actual = (
                    sys.getsizeof(account._held)
                    + sys.getsizeof(account._held._shards)
                    + sum(map(sys.getsizeof, account._held._shards))
                )
                self.assertEqual(report["registryBytes"], actual)
                self.assertEqual(report["registryReserved"], actual - report["registryBase"])
            before, root = account.snapshot(), tree.root
            with patch.object(sync._IdentityIndex, "growth_bound", return_value=account.limit):
                with self.assertRaises(sync.BudgetExceeded):
                    tree.put("new key", ["new allocation"])
            self.assertEqual(account.snapshot()["used"], before["used"])
            self.assertEqual(account.snapshot()["registryBytes"], before["registryBytes"])
            self.assertEqual(tree.root, root)
            del tree
            gc.collect()
            self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_string_canonical_atoms_share_across_spaces_without_hash_domain_reuse(self):
        account = sync.AllocationAccount()
        base = account.snapshot()["used"]
        token = "18" * 32
        global_map = sync.PersistentMap("memberships", ((["global"], token),), account=account)
        grouped_map = sync.PersistentMap("cohort-members", ((["group"], token),), account=account)
        global_pair = global_map.lookup_encoded(["global"])
        grouped_pair = grouped_map.lookup_encoded(["group"])
        self.assertIs(global_pair[1], grouped_pair[1])
        self.assertNotEqual(global_map.get_hash(["global"]), grouped_map.get_hash(["group"]))
        del global_map
        gc.collect()
        self.assertEqual(grouped_map.get(["group"]), token)
        self.assertIn(id(token), account._held)
        del grouped_map
        gc.collect()
        self.assertEqual(account.snapshot()["used"], base)

    def test_large_shared_reference_counters_charge_transitions_and_reclaim(self):
        account = sync.AllocationAccount()
        value = sync.freeze({"reused": ["fact", 1]})
        leases = [account.retain_json(value) for _ in range(260)]
        self.assertEqual(account._held[id(value)].refs, 260)
        large = account.snapshot()
        del leases[256:]
        self.assertEqual(account._held[id(value)].refs, 256)
        self.assertLess(account.snapshot()["used"], large["used"])
        del leases
        gc.collect()
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_retained_object_graph_fits_ledger_without_per_node_sidecars(self):
        account = sync.AllocationAccount()
        shared = sync.freeze(["host", "codex", "namespace", "thread", "id"])
        tree = sync.PersistentMap(
            "records", (([shared, index], {"n": index}) for index in range(100)), account=account
        )
        seen, pending, actual = set(), [tree], 0
        while pending:
            value = pending.pop()
            if id(value) in seen or isinstance(
                value,
                (
                    type,
                    types.ModuleType,
                    types.FunctionType,
                    types.BuiltinFunctionType,
                    types.CodeType,
                ),
            ):
                continue
            seen.add(id(value))
            actual += sys.getsizeof(value)
            pending.extend(gc.get_referents(value))
        report = account.snapshot()
        self.assertGreaterEqual(report["used"], actual)
        self.assertEqual(report["leases"], 1)  # Map only; leaves/branches own themselves.
        self.assertEqual(report["allocations"], tree.node_count + 1)
        self.assertEqual(report["used"], sum(report["byKind"].values()))

    def test_json_retention_reuses_shared_graph_and_owns_mutable_input(self):
        account = sync.AllocationAccount()
        base = account.snapshot()["used"]
        frozen = sync.freeze({"binding": ["owner", 1]})
        lease = account.retain_json(frozen)
        first = account.snapshot()
        second = account.retain_json(frozen, 120)
        self.assertEqual(account.snapshot()["objects"], first["objects"])
        self.assertEqual(account._held[id(frozen)].refs, 2)
        original = {"mutable": [1]}
        third = account.retain_json(original)
        original["mutable"].append(2)
        self.assertIn(
            {"mutable": [1]},
            [
                sync.thaw(held.value)
                for held in account._held.values()
                if isinstance(held.value, Mapping)
            ],
        )
        del lease, second, third
        gc.collect()
        self.assertEqual(account.snapshot()["used"], base)

    def test_reservation_resize_is_atomic_and_uses_one_sidecar(self):
        account = sync.AllocationAccount(limit=50000)
        lease = account.reserve(1000, kind="stage")
        before = account.snapshot()
        lease.resize(2000)
        self.assertEqual(account.snapshot()["used"], before["used"] + 1000)
        self.assertEqual(account.snapshot()["leases"], before["leases"])
        with self.assertRaises(sync.BudgetExceeded):
            lease.resize(50000)
        self.assertEqual(account.snapshot()["byKind"]["stage"], 2000)
        lease.resize(0)
        lease.release()
        with self.assertRaises(ValueError):
            lease.resize(1)
        self.assertEqual(account.snapshot()["used"], account.snapshot()["base"])

    def test_registry_capacity_remains_reserved_after_sparse_reclamation(self):
        account = sync.AllocationAccount()
        tree = sync.PersistentMap(
            "records", ((str(index), index) for index in range(100)), account=account
        )
        previous = account.snapshot()
        for index in range(99):
            tree = tree.remove(str(index))
        current = account.snapshot()
        self.assertLess(current["objects"], previous["objects"])
        self.assertEqual(
            current["registryReserved"], current["registryBytes"] - current["registryBase"]
        )
        self.assertGreaterEqual(current["registrySlots"], previous["registrySlots"])
        self.assertEqual(current["used"], sum(current["byKind"].values()))
        del tree
        gc.collect()
        self.assertEqual(account.snapshot()["registryReserved"], 0)
        self.assertEqual(account.snapshot()["registryBytes"], account.snapshot()["registryBase"])

    def test_shared_frozen_allocations_and_paths_are_charged_once_then_reclaimed(self):
        account = sync.AllocationAccount()
        base = account.snapshot()["used"]
        identity = sync.freeze(("h", "codex", "ns", "thread", "id"))
        birth = sync.freeze(("owner", 1))
        value = sync.freeze({"shared": ["content", None]})
        first = sync.PersistentMap(
            "full", (((identity, birth, "runtime"), value),), account=account
        )
        shared_refs = account._held[id(value)].refs
        second = sync.PersistentMap(
            "active", (((identity, birth, "runtime"), value),), account=account
        )
        self.assertEqual(account._held[id(value)].refs, shared_refs + 1)
        self.assertEqual(account._held[id(identity)].refs, 2)
        before = account.snapshot()
        third = first.put((identity, birth, "phase"), "token")
        self.assertEqual(account._held[id(identity)].refs, 3)
        self.assertGreater(account.snapshot()["used"], before["used"])
        self.assertLess(third.last_update.created_nodes, 4)
        del first, second, third
        gc.collect()
        after = account.snapshot()
        self.assertEqual(after["used"], base)
        self.assertEqual(after["objects"], 0)
        self.assertEqual(after["leases"], 0)
        self.assertEqual(after["created"], after["reclaimed"])

    def test_external_buffer_reservations_are_bounded_idempotent_and_reclaim(self):
        account = sync.AllocationAccount(limit=50000)
        with self.assertRaises(AttributeError):
            account.limit = 999999
        base = account.snapshot()["used"]
        lease = account.reserve(2000, kind="encoded")
        self.assertEqual(account.snapshot()["byKind"]["encoded"], 2000)
        alias = lease
        self.assertIs(alias, lease)
        lease.release()
        alias.release()
        self.assertEqual(account.snapshot()["used"], base)
        with account.reserve(1000, kind="queue"):
            self.assertEqual(account.snapshot()["byKind"]["queue"], 1000)
        self.assertEqual(account.snapshot()["used"], base)
        before = account.snapshot()["used"]
        with self.assertRaises(sync.BudgetExceeded):
            account.reserve(50000, kind="stage")
        self.assertEqual(account.snapshot()["used"], before)

    def test_budget_rejection_does_not_change_prior_root_or_leak_provisional_allocations(self):
        account = sync.AllocationAccount(limit=50000)
        tree = sync.PersistentMap("records", (("key", "original"),), account=account)
        before, root = account.snapshot()["used"], tree.root
        try:
            tree.put("key", "oversized" * 20000)
            self.fail("over-budget mutation accepted")
        except sync.BudgetExceeded:
            pass
        gc.collect()
        self.assertEqual(tree.root, root)
        self.assertEqual(tree.get("key"), "original")
        self.assertEqual(account.snapshot()["used"], before)


if __name__ == "__main__":
    unittest.main()
