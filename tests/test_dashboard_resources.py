"""Qualification profiles and controlled outage evidence for the dashboard probe."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check-dashboard-resources"
LOADER = importlib.machinery.SourceFileLoader("dashboard_resource_check", str(SCRIPT))
SPEC = importlib.util.spec_from_loader(LOADER.name, LOADER)
resource_check = importlib.util.module_from_spec(SPEC)
sys.modules[LOADER.name] = resource_check
LOADER.exec_module(resource_check)


def arguments(**overrides):
    values = {
        "profile": "diagnostic",
        "warmup": None,
        "duration": None,
        "cpu_percent": None,
        "rss_mib": None,
        "ui": False,
        "config": Path("/tmp/terminal.toml"),
        "outage_source": None,
        "outage_proof": None,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def fixture_sources(directory: Path, count: int, *, outcomes: int) -> tuple:
    return tuple(
        SimpleNamespace(
            id=f"fixture-{index}",
            host=f"fixture-{index}",
            home="default",
            mesh_source="agent_working_set",
            scope="local",
            socket=directory / f"mesh-{index}.sock",
            namespace=f"fixture-namespace-{index}",
            max_identities=max(1024, outcomes),
            max_payload_mib=4,
            window_hours=0,
        )
        for index in range(1, count + 1)
    )


def write_fixture_metadata(directory: Path, *, sources=3, outcomes=100, outage=False):
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    config = directory / "terminal.toml"
    config.write_text("fixture configuration\n", encoding="utf-8")
    config.chmod(0o600)
    ready = {
        "pid": os.getpid(),
        "sources": sources,
        "identitiesPerSource": outcomes,
        "config": str(config),
        "synthetic": True,
        "nativeProviderCalls": 0,
        "fixtureStartedAtMonotonic": 10.0,
        "outageConfigured": outage,
        "outageAfterSeconds": 150.0 if outage else None,
        "outageDurationSeconds": 600.0 if outage else None,
    }
    (directory / "ready.json").write_text(json.dumps(ready) + "\n", encoding="utf-8")
    (directory / "ready.json").chmod(0o600)
    return config


def complete_snapshot(*, epoch=1, attempts=1, total=100):
    return {
        "health": "complete",
        "baseline": True,
        "epoch": epoch,
        "attempts": attempts,
        "stage": "observing",
        "members": total,
        "uncertain": 0,
        "nonmembers": 0,
        "total": total,
    }


class ResourceProfileTests(unittest.TestCase):
    def test_qualification_geometry_cannot_substitute_tiny_guidance_for_full_ui(self):
        normal = resource_check.resolve_profile(arguments(profile="normal", ui=True))
        resource_check.validate_terminal_geometry(normal, (120, 40))
        for size in ((80, 24), (40, 10), (120, 30)):
            with self.subTest(size=size), self.assertRaises(resource_check.QualificationSetupError):
                resource_check.validate_terminal_geometry(normal, size)
        diagnostic = resource_check.resolve_profile(arguments(ui=True))
        resource_check.validate_terminal_geometry(diagnostic, (40, 10))

    def test_diagnostic_can_be_short_but_never_uses_accepted_status(self):
        policy = resource_check.resolve_profile(
            arguments(warmup=0.0, duration=2.0, cpu_percent=50.0, rss_mib=512.0)
        )
        self.assertEqual(policy.name, "diagnostic")
        self.assertEqual(policy.duration_seconds, 2.0)
        self.assertEqual(resource_check._profile_status(policy, set()), "diagnostic_pass")

    def test_qualification_profiles_reject_short_windows_and_custom_thresholds(self):
        rejected = (
            arguments(profile="normal", ui=True, warmup=119, duration=1800),
            arguments(profile="normal", ui=True, warmup=120, duration=1799),
            arguments(profile="normal", ui=True, cpu_percent=4.9),
            arguments(profile="normal", ui=True, rss_mib=193),
            arguments(profile="soak", ui=True, duration=28799),
            arguments(profile="capacity", ui=True, rss_mib=769),
            arguments(profile="capacity", ui=True, cpu_percent=5),
        )
        for value in rejected:
            with (
                self.subTest(value=value),
                self.assertRaises(resource_check.QualificationSetupError),
            ):
                resource_check.resolve_profile(value)

    def test_profile_defaults_pin_normal_soak_and_capacity_budgets(self):
        normal = resource_check.resolve_profile(arguments(profile="normal", ui=True))
        soak = resource_check.resolve_profile(arguments(profile="soak", ui=True))
        capacity = resource_check.resolve_profile(arguments(profile="capacity", ui=True))
        self.assertEqual((normal.warmup_seconds, normal.duration_seconds), (120, 1800))
        self.assertEqual((normal.cpu_percent_limit, normal.rss_mib_limit), (5, 192))
        self.assertEqual((soak.duration_seconds, soak.rss_mib_limit), (28_800, 192))
        self.assertEqual((capacity.expected_sources, capacity.outcomes_per_source), (8, 1024))
        self.assertIsNone(capacity.cpu_percent_limit)
        self.assertEqual(capacity.rss_mib_limit, 768)

    def test_non_ui_and_empty_fixture_cannot_qualify(self):
        with self.assertRaisesRegex(
            resource_check.QualificationSetupError, "qualification_requires_real_ui"
        ):
            resource_check.resolve_profile(arguments(profile="normal"))

        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config = write_fixture_metadata(directory, outcomes=0)
            value = arguments(profile="normal", ui=True, config=config)
            with self.assertRaisesRegex(
                resource_check.QualificationSetupError,
                "qualification_fixture_workload_mismatch",
            ):
                resource_check.validate_qualification_setup(
                    value, fixture_sources(directory, 3, outcomes=100)
                )

    def test_qualification_requires_exact_source_roster_and_outage_setup(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config = write_fixture_metadata(directory)
            value = arguments(profile="normal", ui=True, config=config)
            with self.assertRaisesRegex(
                resource_check.QualificationSetupError,
                "qualification_fixture_source_selection_mismatch",
            ):
                resource_check.validate_qualification_setup(
                    value, fixture_sources(directory, 2, outcomes=100)
                )

            soak_config = write_fixture_metadata(directory / "soak", outage=False)
            soak = arguments(
                profile="soak",
                ui=True,
                config=soak_config,
                outage_source="fixture-1",
                outage_proof=soak_config.parent / "outage.json",
            )
            with self.assertRaisesRegex(
                resource_check.QualificationSetupError, "fixture_outage_not_configured"
            ):
                resource_check.validate_qualification_setup(
                    soak, fixture_sources(soak_config.parent, 3, outcomes=100)
                )

    def test_soak_requires_ten_minute_fixture_outage(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config = write_fixture_metadata(directory, outage=True)
            value = arguments(
                profile="soak",
                ui=True,
                config=config,
                outage_source="fixture-1",
                outage_proof=directory / "outage.json",
            )
            sources = fixture_sources(directory, 3, outcomes=100)
            resource_check.validate_qualification_setup(value, sources)
            ready_path = directory / "ready.json"
            ready = json.loads(ready_path.read_text())
            ready["outageDurationSeconds"] = 599
            ready_path.write_text(json.dumps(ready) + "\n")
            with self.assertRaisesRegex(
                resource_check.QualificationSetupError, "qualification_outage_too_short"
            ):
                resource_check.validate_qualification_setup(value, sources)

    def test_zero_and_wrong_per_source_outcomes_fail_at_complete_coverage(self):
        policy = resource_check.resolve_profile(arguments(profile="normal", ui=True))
        self.assertFalse(resource_check.outcome_count_valid(policy, complete_snapshot(total=0)))
        self.assertFalse(resource_check.outcome_count_valid(policy, complete_snapshot(total=99)))
        self.assertTrue(resource_check.outcome_count_valid(policy, complete_snapshot(total=100)))

    def test_ui_resource_run_uses_cli_default_color_and_icon_policy(self):
        presentation = resource_check.ui_presentation_options(
            environ={"TERM": "xterm-256color", "NO_COLOR": "1"}, encoding="utf-8"
        )
        self.assertTrue(presentation["noColor"])
        self.assertTrue(presentation["icons"])
        self.assertTrue(presentation["noColorEnvironmentPresent"])
        ascii_only = resource_check.ui_presentation_options(
            environ={"TERM": "xterm-256color"}, encoding="ascii"
        )
        self.assertFalse(ascii_only["noColor"])
        self.assertFalse(ascii_only["icons"])


class ControlledOutageTests(unittest.TestCase):
    def setUp(self):
        self.tracker = resource_check.ControlledOutageTracker(
            "fixture-1", ("fixture-1", "fixture-2", "fixture-3")
        )
        self.initial = {
            "fixture-1": complete_snapshot(),
            "fixture-2": complete_snapshot(),
            "fixture-3": complete_snapshot(),
        }
        self.start_proof = {
            "source": "fixture-1",
            "stage": "unavailable",
            "outageStartedAtMonotonic": 10.0,
            "listenerRestoredAtMonotonic": None,
        }
        self.restored_proof = {
            **self.start_proof,
            "stage": "listener-restored",
            "listenerRestoredAtMonotonic": 20.0,
        }
        self.tracker.observe(9.0, self.initial, None)
        self.tracker.observe(10.05, self.initial, self.start_proof)

    def _target_down(self, snapshots=None):
        snapshots = {key: dict(value) for key, value in (snapshots or self.initial).items()}
        snapshots["fixture-1"].update(
            health="unavailable", baseline=False, epoch=2, stage="revoked", total=0
        )
        return snapshots

    def _target_recovering(self, snapshots=None):
        snapshots = {key: dict(value) for key, value in (snapshots or self.initial).items()}
        snapshots["fixture-1"].update(
            health="warming", baseline=False, epoch=3, attempts=2, stage="connecting", total=0
        )
        return snapshots

    def test_named_outage_requires_fresh_epoch_and_accepts_valid_recovery(self):
        target_down = self._target_down()
        self.tracker.observe(10.2, target_down, self.start_proof)
        self.assertTrue(self.tracker.partial_allowed(15, target_down))
        sample_at = 10.7
        while sample_at < 20:
            self.tracker.observe(sample_at, target_down, self.start_proof)
            sample_at += 0.5
        self.tracker.observe(20.1, self._target_recovering(), self.restored_proof)
        recovered = {key: dict(value) for key, value in self.initial.items()}
        recovered["fixture-1"].update(epoch=3, attempts=2)
        self.tracker.observe(20.3, recovered, self.restored_proof)
        self.assertFalse(self.tracker.partial_allowed(21, recovered))
        self.assertEqual(self.tracker.failures(measurement_started=8, measurement_ended=30), [])

    def test_wrong_source_cannot_satisfy_fault_and_healthy_siblings_are_required(self):
        wrong = {**self.start_proof, "source": "fixture-2"}
        self.tracker.observe(10.2, self._target_down(), wrong)
        failures = self.tracker.failures(measurement_started=8, measurement_ended=30)
        self.assertIn("outage_proof_wrong_source", failures)

        tracker = resource_check.ControlledOutageTracker(
            "fixture-1", ("fixture-1", "fixture-2", "fixture-3")
        )
        tracker.observe(9.0, self.initial, None)
        sibling_loss = self._target_down()
        sibling_loss["fixture-2"].update(health="unavailable", baseline=False, epoch=2)
        tracker.observe(10.2, sibling_loss, self.start_proof)
        failures = tracker.failures(measurement_started=8, measurement_ended=30)
        self.assertIn("healthy_sibling_coverage_lost", failures)
        self.assertFalse(tracker.partial_allowed(10.2, sibling_loss))

    def test_old_epoch_or_false_baseline_does_not_count_as_recovery(self):
        self.tracker.observe(10.2, self._target_down(), self.start_proof)
        self.tracker.observe(20.1, self._target_recovering(), self.restored_proof)
        stale = {key: dict(value) for key, value in self.initial.items()}
        stale["fixture-1"].update(epoch=2, attempts=1)
        self.tracker.observe(20.3, stale, self.restored_proof)
        failures = self.tracker.failures(measurement_started=8, measurement_ended=30)
        self.assertIn("outage_fresh_recovery_not_observed", failures)

        false_baseline = {key: dict(value) for key, value in self.initial.items()}
        false_baseline["fixture-1"].update(epoch=3, attempts=2, baseline=False)
        self.tracker.observe(20.4, false_baseline, self.restored_proof)
        failures = self.tracker.failures(measurement_started=8, measurement_ended=30)
        self.assertIn("outage_fresh_recovery_not_observed", failures)

    def test_loss_and_recovery_must_match_proof_window_and_bounds(self):
        self.tracker.observe(16.0, self._target_down(), self.start_proof)
        failures = self.tracker.failures(measurement_started=8, measurement_ended=30)
        self.assertIn("outage_loss_detection_too_slow", failures)

        self.tracker.observe(20.1, self._target_recovering(), self.restored_proof)
        self.tracker.observe(58.0, self._target_recovering(), self.restored_proof)
        failures = self.tracker.failures(measurement_started=8, measurement_ended=60)
        self.assertIn("outage_recovery_too_slow", failures)

    def test_other_feed_loss_does_not_substitute_for_named_source(self):
        sibling_loss = {key: dict(value) for key, value in self.initial.items()}
        sibling_loss["fixture-2"].update(
            health="unavailable", baseline=False, epoch=2, stage="revoked", total=0
        )
        self.tracker.observe(10.2, sibling_loss, self.start_proof)
        failures = self.tracker.failures(measurement_started=8, measurement_ended=30)
        self.assertIn("outage_loss_not_observed", failures)

    def test_single_source_outage_cannot_be_claimed_as_isolation(self):
        with self.assertRaisesRegex(
            resource_check.QualificationSetupError,
            "outage_requires_selected_source_and_sibling",
        ):
            resource_check.ControlledOutageTracker("fixture-1", ("fixture-1",))

    def test_outage_proof_retains_start_time_and_requires_the_named_source(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "outage.json"
            started = {
                "source": "fixture-1",
                "stage": "unavailable",
                "outageStartedAtMonotonic": 10.0,
                "listenerRestoredAtMonotonic": None,
            }
            path.write_text(json.dumps(started) + "\n", encoding="utf-8")
            path.chmod(0o600)
            self.assertEqual(resource_check.load_outage_proof(path, "fixture-1"), started)
            restored = {
                **started,
                "stage": "listener-restored",
                "listenerRestoredAtMonotonic": 20.0,
            }
            path.write_text(json.dumps(restored) + "\n", encoding="utf-8")
            loaded = resource_check.load_outage_proof(path, "fixture-1")
            self.assertEqual(loaded["outageStartedAtMonotonic"], 10.0)
            self.assertEqual(loaded["listenerRestoredAtMonotonic"], 20.0)
            with self.assertRaisesRegex(
                resource_check.QualificationSetupError,
                "outage_proof_invalid_or_wrong_source",
            ):
                resource_check.load_outage_proof(path, "fixture-2")


class ProvenanceTests(unittest.TestCase):
    def test_product_tree_digest_changes_with_output_code_and_ignores_bytecode(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "terminal" / "dashboard_output.py"
            output.parent.mkdir()
            output.write_text("value = 1\n", encoding="utf-8")
            stylesheet = output.parent / "dashboard.tcss"
            stylesheet.write_text("Screen {}\n", encoding="utf-8")
            cache = output.parent / "__pycache__"
            cache.mkdir()
            (cache / "ignored.pyc").write_bytes(b"one")
            before = resource_check._digest_named_files(
                resource_check._iter_source_files(root, {".py", ".json", ".tcss"})
            )
            output.write_text("value = 2\n", encoding="utf-8")
            (cache / "ignored.pyc").write_bytes(b"two")
            after = resource_check._digest_named_files(
                resource_check._iter_source_files(root, {".py", ".json", ".tcss"})
            )
        self.assertNotEqual(before["sha256"], after["sha256"])
        self.assertEqual(before["fileCount"], 2)

    def test_installed_dependency_file_bytes_are_hashed_and_cache_files_excluded(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            module = root / "dependency" / "module.py"
            module.parent.mkdir()
            module.write_text("value = 1\n", encoding="utf-8")
            cache = module.parent / "__pycache__"
            cache.mkdir()
            cached = cache / "module.cpython-311.pyc"
            cached.write_bytes(b"ignored")

            class Distribution:
                metadata = {"Name": "fixture-dependency"}
                version = "1.0"
                files = (Path("dependency/module.py"), Path("dependency/__pycache__/module.pyc"))

                @staticmethod
                def locate_file(relative):
                    return root / relative

            before = resource_check._installed_distribution_provenance([Distribution()])
            module.write_text("value = 2\n", encoding="utf-8")
            cached.write_bytes(b"different ignored bytes")
            after = resource_check._installed_distribution_provenance([Distribution()])
        self.assertNotEqual(before["sha256"], after["sha256"])
        self.assertEqual(before["fileCount"], 1)


if __name__ == "__main__":
    unittest.main()
