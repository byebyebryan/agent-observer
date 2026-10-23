"""Artifact identity must reject before installation or any provider invocation."""

import hashlib
import json
import runpy
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
HELPER = runpy.run_path(str(ROOT / "scripts/candidate-artifact"))


class CandidateArtifactTest(unittest.TestCase):
    def test_read_only_manifest_requires_exact_entrypoints_and_withdrawal(self):
        good = json.loads((ROOT / "artifacts/observer-0.7.0a8.json").read_text())
        good.update(manifestVersion=6, retiredCapabilities=["write", "active-feed"],
                    entrypoints=["agent-observer", "agent-observer-service"])
        good.pop("write")
        good.pop("activeFeed")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(good))
            self.assertEqual(HELPER["document"](path), good)
            for extra in ({"write": {"schema": 2}}, {"activeFeed": {}},
                          {"retiredCapabilities": ["write"]},
                          {"entrypoints": ["agent-observer", "agent-observer-write", "agent-observer-service"]}):
                with self.subTest(extra=extra), self.assertRaises(ValueError):
                    path.write_text(json.dumps({**good, **extra}))
                    HELPER["document"](path)

    def active_manifest(self):
        manifest = HELPER["document"](ROOT / "artifacts/observer-0.7.0a6.json")
        schemas = {name: ROOT / f"agent_observer/contracts/active-{name}.schema.json"
                   for name in ("request", "frame")}
        request = json.loads(schemas["request"].read_bytes())
        manifest["activeFeed"] = {
            "protocol": 1, "schemas": {"request": 1, "frame": 1},
            "schemaSha256": {name: hashlib.sha256(path.read_bytes()).hexdigest()
                             for name, path in schemas.items()},
            "selectorDigest": request["properties"]["selectorDigest"]["const"],
        }
        return manifest

    def test_read_only_pair_metadata_rejects_malformed_provenance(self):
        good = json.loads((ROOT / 'artifacts/observer-0.7.0a9.json').read_text())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'manifest.json'
            path.write_text(json.dumps(good))
            self.assertEqual(HELPER['document'](path)['pairedMesh'], good['pairedMesh'])
            for change in ({'wheelSha256': True}, {'sourceRevision': None},
                           {'wheel': '../outside.whl'}, {'version': 'unbound'}):
                changed = {**good, 'pairedMesh': {**good['pairedMesh'], **change}}
                path.write_text(json.dumps(changed))
                with self.subTest(change=change), self.assertRaises(ValueError):
                    HELPER['document'](path)

    def fake_installation(self, directory, *, active=True):
        """Exact-byte in-process verification fixture; never installs or spawns."""
        prefix = Path(directory).resolve() / "candidate"
        site = prefix / "lib/site-packages"
        schemas = site / "agent_observer/contracts"
        schemas.mkdir(parents=True)
        manifest = self.active_manifest() if active else HELPER["document"](ROOT / "artifacts/observer-0.7.0a6.json")
        for name in ("request", "frame"):
            (schemas / f"active-{name}.schema.json").write_bytes(
                (ROOT / f"agent_observer/contracts/active-{name}.schema.json").read_bytes())
        (prefix / "bin").mkdir()
        python = prefix / "bin/python"
        python.write_text("fixture interpreter; never executed\n")
        python.chmod(0o700)
        for name in manifest["entrypoints"]:
            executable = prefix / "bin" / name
            executable.write_text("#!" + str(python) + "\n")
            executable.chmod(0o700)
        wheel = Path(directory) / manifest["wheel"]
        with zipfile.ZipFile(wheel, "w") as archive:
            for path in schemas.iterdir():
                archive.write(path, str(path.relative_to(site)))
        manifest["wheelSha256"] = hashlib.sha256(wheel.read_bytes()).hexdigest()
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            if "-c" in argv:
                return json.dumps({"version": manifest["version"], "site": str(site),
                                   "module": str(site / "agent_observer/contract.py"), "sdk": None,
                                   "bundledExecutable": False, "retiredNativeModules": False}).encode()
            if argv[1:] == ["--version"]:
                return (Path(argv[0]).name + " " + manifest["version"]).encode()
            command = argv[1:]
            if command == ["api"]:
                value = {"apiVersion": 4, "schemas": manifest["schemas"]}
            elif command[:1] == ["schema"]:
                version = 2 if Path(argv[0]).name == "agent-observer-write" else 6
                value = {"properties": {"schemaVersion": {"const": version}}}
            elif command == ["service", "api"]:
                value = {"serviceProtocol": 4, "observationApiVersion": 4, "embeddedSnapshotVersion": 6}
            elif command[:2] == ["service", "schema"]:
                value = {"properties": {"serviceProtocol": {"const": 4}}}
            elif command == ["service", "active-api"]:
                if not active:
                    self.fail("old manifest invoked active declarations")
                request = json.loads((schemas / "active-request.schema.json").read_bytes())
                value = {"activeFeedProtocol": 1, "observationApiVersion": 4,
                         "selector": request["properties"]["selector"]["const"],
                         "selectorDigest": manifest["activeFeed"]["selectorDigest"]}
            elif command[:2] == ["service", "active-schema"]:
                if not active:
                    self.fail("old manifest invoked active schema")
                value = json.loads((schemas / f"active-{command[-1]}.schema.json").read_bytes())
            else:
                self.fail("unexpected verification command: " + repr(argv))
            return json.dumps(value).encode()

        return prefix, site, wheel, manifest, calls, run

    def test_active_extension_is_optional_and_every_retained_manifest_still_parses(self):
        for path in (ROOT / "artifacts").glob("observer-*.json"):
            with self.subTest(path=path.name):
                manifest = HELPER["document"](path)
                self.assertEqual(manifest, json.loads(path.read_bytes()))
                if "activeFeed" not in manifest:
                    self.assertIsNone(HELPER["active_feed_manifest"](manifest))
        manifest = self.active_manifest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(manifest))
            self.assertEqual(HELPER["document"](path), manifest)

    def test_active_extension_rejects_unknown_missing_malformed_and_boolean_fields(self):
        good = self.active_manifest()
        bad_values = [None, {}, [], {**good["activeFeed"], "unknown": 1}]
        for key, value in (
            ("protocol", True), ("protocol", 2),
            ("schemas", {"request": 1}), ("schemas", {"request": True, "frame": 1}),
            ("schemas", {"request": 1, "frame": 1, "snapshot": 1}),
            ("schemaSha256", {"request": "a" * 64, "frame": "sha256:" + "b" * 64}),
            ("schemaSha256", {"request": "A" * 64, "frame": "b" * 64}),
            ("schemaSha256", {"request": None, "frame": "b" * 64}),
            ("selectorDigest", "a" * 64), ("selectorDigest", "sha256:" + "A" * 64),
        ):
            bad_values.append({**good["activeFeed"], key: value})
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            for active in bad_values:
                with self.subTest(active=active):
                    path.write_text(json.dumps({**good, "activeFeed": active}))
                    with self.assertRaisesRegex(ValueError, "active_feed_manifest_invalid"):
                        HELPER["document"](path)
            old = HELPER["document"](ROOT / "artifacts/observer-0.6.0a2.json")
            path.write_text(json.dumps({**old, "activeFeed": good["activeFeed"]}))
            with self.assertRaisesRegex(ValueError, "active_feed_manifest_invalid"):
                HELPER["document"](path)

    def test_active_installed_verification_checks_exact_schema_bytes_cli_and_selector(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix, site, wheel, manifest, calls, run = self.fake_installation(directory)
            with patch.dict(HELPER["verify"].__globals__, run=run):
                receipt = HELPER["verify"](prefix, wheel, manifest, "core")
            self.assertIs(receipt["activeFeedVerified"], True)
            self.assertEqual([argv[1:] for argv in calls if argv[1:3] in
                              (["service", "active-api"], ["service", "active-schema"])],
                             [["service", "active-api"], ["service", "active-schema", "--kind", "request"],
                              ["service", "active-schema", "--kind", "frame"]])
            self.assertEqual(receipt["providerInvocations"], 0)

    def test_active_manifest_hash_mismatch_rejects_even_exact_installed_wheel_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix, site, wheel, manifest, calls, run = self.fake_installation(directory)
            manifest["activeFeed"]["schemaSha256"]["request"] = "f" * 64
            with patch.dict(HELPER["verify"].__globals__, run=run):
                with self.assertRaisesRegex(ValueError, "active_feed_schema_bytes_mismatch"):
                    HELPER["verify"](prefix, wheel, manifest, "core")

    def test_malformed_active_extension_rejects_before_installation(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix = Path(directory) / "never-created"
            manifest = self.active_manifest()
            manifest["activeFeed"]["protocol"] = True
            with patch.dict(HELPER["install"].__globals__,
                            run=lambda *a, **k: self.fail("spawned"),
                            wheel_check=lambda *a, **k: self.fail("read wheel before rejecting manifest")):
                with self.assertRaisesRegex(ValueError, "active_feed_manifest_invalid"):
                    HELPER["install"](prefix, Path(directory) / "missing.whl", manifest, "core")
            self.assertFalse(prefix.exists())

    def test_old_installed_verification_keeps_receipt_shape_and_skips_active_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            prefix, site, wheel, manifest, calls, run = self.fake_installation(directory, active=False)
            with patch.dict(HELPER["verify"].__globals__, run=run):
                receipt = HELPER["verify"](prefix, wheel, manifest, "core")
            self.assertNotIn("activeFeedVerified", receipt)

    def test_active_installed_cli_mismatches_reject_before_acceptance(self):
        mutations = (
            lambda command, value: value.update(activeFeedProtocol=True) if command == "active-api" else None,
            lambda command, value: value.update(observationApiVersion=3) if command == "active-api" else None,
            lambda command, value: value.update(selectorDigest="sha256:" + "0" * 64) if command == "active-api" else None,
            lambda command, value: value["selector"].update(version=2) if command == "active-api" else None,
            lambda command, value: value.update(description="different CLI bytes") if command == "active-schema" else None,
        )
        for number, mutate in enumerate(mutations):
            with self.subTest(case=number), tempfile.TemporaryDirectory() as directory:
                prefix, site, wheel, manifest, calls, original = self.fake_installation(directory)

                def run(argv, *, original=original, mutate=mutate, **kwargs):
                    value = json.loads(original(argv, **kwargs))
                    mutate(argv[2], value)
                    return json.dumps(value).encode()

                with patch.dict(HELPER["verify_active_feed"].__globals__, run=run):
                    with self.assertRaisesRegex(ValueError, "active_feed_(api|selector|schema)_mismatch"):
                        HELPER["verify_active_feed"](prefix, site, manifest["activeFeed"], 4)

    def test_active_raw_schema_digest_and_selector_bindings_are_mandatory(self):
        for mutation in ("bytes", "selector", "schema_version", "boolean_protocol", "symlink"):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                prefix, site, wheel, manifest, calls, run = self.fake_installation(directory)
                path = site / "agent_observer/contracts/active-frame.schema.json"
                if mutation == "bytes":
                    path.write_bytes(path.read_bytes() + b" ")
                elif mutation == "symlink":
                    target = path.with_suffix(".target")
                    path.rename(target)
                    path.symlink_to(target)
                else:
                    value = json.loads(path.read_bytes())
                    if mutation == "selector":
                        value["properties"]["selector"]["const"]["version"] = 2
                    elif mutation == "schema_version":
                        value["$id"] = "urn:agent-observer:active-frame:2"
                    else:
                        value["properties"]["activeFeedProtocol"]["const"] = True
                    path.write_text(json.dumps(value))
                    manifest["activeFeed"]["schemaSha256"]["frame"] = hashlib.sha256(path.read_bytes()).hexdigest()
                with patch.dict(HELPER["verify_active_feed"].__globals__, run=run):
                    with self.assertRaisesRegex(ValueError, "active_feed_schema(_bytes)?_mismatch"):
                        HELPER["verify_active_feed"](prefix, site, manifest["activeFeed"], 4)

    def test_timing_manifest_keeps_independent_writer_and_requires_new_tuple(self):
        manifest = HELPER["document"](ROOT / "artifacts/observer-0.5.0a20.json")
        manifest.update(manifestVersion=4, apiVersion=3, schemas={"snapshot": 5, "watch": 5},
                        service={"protocol": 3, "schemas": {"request": 3, "frame": 3}})
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "manifest.json"
            path.write_text(json.dumps(manifest))
            self.assertEqual(HELPER["document"](path)["write"], {"schema": 2})
            manifest["apiVersion"] = 2
            path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError, "manifest_invalid"):
                HELPER["document"](path)
    def test_service_manifest_is_a_separate_versioned_extension(self):
        manifest = HELPER["document"](ROOT / "artifacts/observer-0.3.0a2.json")
        manifest.update(manifestVersion=2, entrypoints=["agent-observer", "agent-observer-write", "agent-observer-service"], service={"protocol": 1, "schemas": {"request": 1, "frame": 1}})
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "manifest.json"
            path.write_text(json.dumps(manifest))
            self.assertEqual(HELPER["document"](path)["service"]["protocol"], 1)
            manifest["schemas"]["service"] = 1
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                HELPER["document"](path)

    def test_breaking_manifest_declares_read_service_and_writer_separately(self):
        manifest = HELPER["document"](ROOT / "artifacts/observer-0.3.0a2.json")
        manifest.update(manifestVersion=3, apiVersion=2,
                        entrypoints=["agent-observer", "agent-observer-write", "agent-observer-service"],
                        schemas={"snapshot": 4, "watch": 4}, write={"schema": 2},
                        service={"protocol": 2, "schemas": {"request": 2, "frame": 2}})
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "manifest.json"
            path.write_text(json.dumps(manifest))
            self.assertEqual(HELPER["document"](path)["apiVersion"], 2)
            manifest["service"]["protocol"] = 1
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                HELPER["document"](path)

    def test_rejected_wheel_has_no_install_effect(self):
        with tempfile.TemporaryDirectory() as root:
            wheel = Path(root) / "invalid.whl"
            wheel.write_bytes(b"invalid")
            prefix = Path(root) / "candidate"
            manifest = {"wheel": wheel.name, "wheelSha256": "f" * 64}
            with patch.dict(
                HELPER["install"].__globals__, run=lambda *a, **k: self.fail("spawned")
            ):
                with self.assertRaisesRegex(ValueError, "wheel_mismatch"):
                    HELPER["install"](prefix, wheel, manifest, "core")
            self.assertFalse(prefix.exists())

    def test_accepted_manifest_has_exact_source_and_interfaces(self):
        manifest = HELPER["document"](ROOT / "artifacts/observer-0.2.0a3.json")
        self.assertEqual(["agent-observer", "agent-observer-write"], manifest["entrypoints"])
        self.assertEqual(2, manifest["schemas"]["snapshot"])
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "manifest.json"
            manifest["sourceRevision"] = "moving-branch"
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                HELPER["document"](path)

    def test_zip_traversal_rejected_before_extracting(self):
        import zipfile

        with tempfile.TemporaryDirectory() as root:
            wheel = Path(root) / "candidate.whl"
            with zipfile.ZipFile(wheel, "w") as archive:
                archive.writestr("../outside", "untrusted")
            manifest = {
                "wheel": wheel.name,
                "wheelSha256": hashlib.sha256(wheel.read_bytes()).hexdigest(),
            }
            with self.assertRaisesRegex(ValueError, "wheel_path_invalid"):
                HELPER["wheel_check"](wheel, manifest)

    def test_v3_candidate_receipt_requires_matching_read_and_watch_versions(self):
        manifest = HELPER["document"](ROOT / "artifacts/observer-0.2.0a11.json")
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "manifest.json"
            manifest["schemas"] = {"snapshot": 3, "watch": 3, "write": 1}
            manifest["apiVersion"] = 1
            path.write_text(json.dumps(manifest))
            self.assertEqual(HELPER["document"](path)["schemas"]["snapshot"], 3)
            manifest["schemas"]["watch"] = 2
            path.write_text(json.dumps(manifest))
            with self.assertRaises(ValueError):
                HELPER["document"](path)

    def test_failed_install_removes_only_owned_new_prefix(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            prefix = root / "candidate"
            unrelated = root / "user-file"
            unrelated.write_text("preserve")
            functions = HELPER["install"].__globals__
            with patch.dict(
                functions,
                wheel_check=lambda *a: None,
                run=lambda *a, **k: (_ for _ in ()).throw(ValueError("failed")),
            ):
                with self.assertRaises(ValueError):
                    HELPER["install"](prefix, root / "wheel", {}, "core")
            self.assertFalse(prefix.exists())
            self.assertEqual("preserve", unrelated.read_text())
