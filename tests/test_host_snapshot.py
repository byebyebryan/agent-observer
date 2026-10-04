"""Common consumer-boundary fixtures; independent of native acceptance."""

import copy
import unittest

from agent_observer.host_snapshot import compose

ID = "01234567-0123-4567-89ab-0123456789ab"


def provider_snapshot(provider="codex", namespace="config-a", *, healthy=True):
    return {
        "schemaVersion": 1,
        "provider": provider,
        "namespace": namespace,
        "host": {"authority": "snap"},
        "sourceHealth": "current" if healthy else "unavailable",
        "coverage": {"saved": {"complete": False, "reason": "history_limit"}},
        "errors": [] if healthy else [{"code": "endpoint_unavailable"}],
        "sessions": [
            {
                "identity": {
                    "hostScope": "snap",
                    "provider": provider,
                    "namespace": namespace,
                    "nativeIdKind": "thread" if provider == "codex" else "session",
                    "nativeId": ID,
                },
                "work": {
                    "value": "working",
                    "health": "current",
                    "observedAt": 100,
                    "source": "synthetic",
                },
                "presence": {
                    "value": "present",
                    "health": "current",
                    "observedAt": 200,
                },
                "attachment": {
                    "value": "unknown",
                    "health": "unsupported",
                    "observedAt": None,
                },
            }
        ]
        if healthy
        else [],
    }


class HostCompositionTest(unittest.TestCase):
    def test_provider_failure_preserves_other_provider_evidence(self):
        good = provider_snapshot()
        bad = provider_snapshot("claude", healthy=False)
        result = compose(host_scope="snap", provider_snapshots=[good, bad])
        self.assertEqual(result["sourceHealth"], "partial")
        self.assertEqual(result["sessions"][0]["work"]["value"], "working")
        self.assertEqual(result["sessions"][0]["work"]["observedAt"], 100)
        self.assertEqual(result["sources"][1]["errors"], [{"code": "endpoint_unavailable"}])
        self.assertFalse(result["sources"][0]["coverage"]["saved"]["complete"])

    def test_healthy_empty_provider_remains_partial_when_another_provider_fails(self):
        good = provider_snapshot("claude")
        good["sessions"] = []
        bad = provider_snapshot("codex", healthy=False)
        result = compose(host_scope="snap", provider_snapshots=[good, bad])
        self.assertEqual("partial", result["sourceHealth"])
        self.assertEqual("current", result["sources"][0]["sourceHealth"])
        self.assertEqual("unavailable", result["sources"][1]["sourceHealth"])
        self.assertEqual([], result["sessions"])

    def test_equal_native_ids_in_different_providers_do_not_collapse(self):
        result = compose(
            host_scope="snap",
            provider_snapshots=[
                provider_snapshot(),
                provider_snapshot("claude", "config-b"),
            ],
        )
        self.assertEqual(len(result["sessions"]), 2)
        self.assertEqual(result["errors"], [])

    def test_duplicate_identity_is_ambiguous_and_keeps_original_age(self):
        native = provider_snapshot()
        native["sessions"].append(copy.deepcopy(native["sessions"][0]))
        original = copy.deepcopy(native)
        result = compose(host_scope="snap", provider_snapshots=[native])
        self.assertEqual(len(result["sessions"]), 2)
        self.assertEqual(result["errors"][0]["code"], "duplicate_native_identity")
        for row in result["sessions"]:
            self.assertEqual(row["work"]["value"], "unknown")
            self.assertEqual(row["work"]["lastKnownValue"], "working")
            self.assertEqual(row["work"]["observedAt"], 100)
        self.assertEqual(native, original)

    def test_host_and_row_namespace_mismatch_fail_closed(self):
        native = provider_snapshot()
        with self.assertRaisesRegex(ValueError, "source_provenance_mismatch"):
            compose(host_scope="starship", provider_snapshots=[native])
        native["sessions"][0]["identity"]["namespace"] = "other"
        with self.assertRaisesRegex(ValueError, "session_provenance_mismatch"):
            compose(host_scope="snap", provider_snapshots=[native])

    def test_unavailable_empty_sources_are_not_healthy_empty_inventory(self):
        result = compose(host_scope="snap", provider_snapshots=[provider_snapshot(healthy=False)])
        self.assertEqual(result["sourceHealth"], "unavailable")
        self.assertEqual(result["sessions"], [])


if __name__ == "__main__":
    unittest.main()
