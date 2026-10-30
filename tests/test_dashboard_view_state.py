"""Strict saved-view schema, private storage and isolated lifecycle tests."""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
import textwrap
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_observer.terminal.dashboard_view import (
    APP_DIRECTORY,
    GROUPS,
    MAX_PINS,
    MAX_STATE_BYTES,
    SORTS,
    STATE_FILENAME,
    SavedView,
    SavedViewController,
    SavedViewError,
    decode_saved_view,
    encode_saved_view,
    load_view_bytes,
    order_pinned_rows,
    save_view_bytes,
    select_state_root,
    toggle_pin,
)


def reference(native_id: str) -> dict[str, str]:
    return {
        "hostScope": "host-one",
        "provider": "codex",
        "namespace": "namespace-one",
        "nativeIdKind": "thread",
        "nativeId": native_id,
    }


def row(native_id: str, label: str | None = None) -> dict:
    return {
        "identity": reference(native_id),
        "label": label or native_id,
    }


def state_file(root: Path) -> Path:
    return root / APP_DIRECTORY / STATE_FILENAME


def write_test_helper(path: Path, body: str) -> Path:
    path.write_text(
        "import json, os, pathlib, sys, time\n"
        "operation, root = sys.argv[1:]\n"
        + textwrap.dedent(body),
        encoding="utf-8",
    )
    path.chmod(0o700)
    return path


class SavedViewSchemaTests(unittest.TestCase):
    def test_round_trip_has_only_version_pins_sort_and_group(self):
        view = SavedView.from_references(
            [reference("first"), reference("second")], sort="label", group="host-home"
        )
        payload = encode_saved_view(view)
        document = json.loads(payload)
        self.assertEqual(set(document), {"version", "pins", "sort", "group"})
        self.assertEqual(document["version"], 1)
        self.assertEqual(decode_saved_view(payload), view)
        self.assertEqual(view.references, (reference("first"), reference("second")))
        self.assertIn(view.sort, SORTS)
        self.assertIn(view.group, GROUPS)

    def test_rejects_unknown_fields_duplicate_refs_invalid_types_and_versions(self):
        base = json.loads(encode_saved_view(SavedView.from_references([reference("one")])))
        cases = (
            {**base, "extra": 1},
            {**base, "version": True},
            {**base, "version": 2},
            {**base, "pins": [dict(reference("one"), extra="field")]},
            {**base, "pins": [reference("one"), reference("one")]},
            {**base, "pins": "not-a-list"},
            {**base, "sort": "recent"},
            {**base, "group": []},
        )
        for document in cases:
            with self.subTest(document=document):
                with self.assertRaises(SavedViewError):
                    decode_saved_view(json.dumps(document).encode())

    def test_rejects_duplicate_json_keys_and_bad_identity_shapes(self):
        duplicate_key = b'{"version":1,"pins":[],"pins":[],"sort":"activity","group":"none"}'
        with self.assertRaises(SavedViewError):
            decode_saved_view(duplicate_key)
        for pin in (
            {"hostScope": "partial"},
            {**reference("one"), "nativeId": 2},
            {**reference("one"), "nativeId": ""},
        ):
            document = {"version": 1, "pins": [pin], "sort": "activity", "group": "none"}
            with self.subTest(pin=pin), self.assertRaises(SavedViewError):
                decode_saved_view(json.dumps(document).encode())

    def test_pin_count_and_encoded_byte_limit_are_inclusive(self):
        pins = [reference(f"thread-{index}") for index in range(MAX_PINS)]
        view = SavedView.from_references(pins)
        self.assertEqual(len(view.pins), MAX_PINS)
        with self.assertRaises(SavedViewError):
            SavedView.from_references([*pins, reference("overflow")])

        base = reference("x")
        one = encode_saved_view(SavedView.from_references([base]))
        exact = dict(base)
        exact["nativeId"] += "x" * (MAX_STATE_BYTES - len(one))
        at_limit = SavedView.from_references([exact])
        self.assertEqual(len(encode_saved_view(at_limit)), MAX_STATE_BYTES)
        with self.assertRaises(SavedViewError):
            SavedView.from_references([{**exact, "nativeId": exact["nativeId"] + "x"}])
        with self.assertRaises(SavedViewError):
            decode_saved_view(encode_saved_view(at_limit) + b" ")

    def test_toggle_appends_and_removes_without_mutating(self):
        original = SavedView.from_references([reference("one")], sort="host")
        appended = toggle_pin(original, reference("two"))
        removed = toggle_pin(appended, reference("one"))
        self.assertEqual(original.references, (reference("one"),))
        self.assertEqual(appended.references, (reference("one"), reference("two")))
        self.assertEqual(removed.references, (reference("two"),))
        self.assertEqual(removed.sort, "host")


class PinnedOrderTests(unittest.TestCase):
    def test_exact_pins_precede_rows_in_first_pinned_order_and_remainder_is_stable(self):
        original = [row("ordinary-a"), row("pin-b"), row("ordinary-b"), row("pin-a")]
        view = SavedView.from_references([reference("pin-a"), reference("pin-b")])
        ordered = order_pinned_rows(original, view)
        self.assertEqual([item["identity"]["nativeId"] for item in ordered], [
            "pin-a", "pin-b", "ordinary-a", "ordinary-b"
        ])
        self.assertEqual(original[0]["identity"]["nativeId"], "ordinary-a")
        self.assertEqual(ordered[0], original[3])

    def test_unmatched_and_malformed_rows_remain_in_original_remainder(self):
        original = [row("ordinary"), {"identity": {"nativeId": "bad"}}, row("pinned")]
        view = SavedView.from_references([reference("pinned"), reference("missing")])
        ordered = order_pinned_rows(original, view)
        self.assertEqual(ordered, [original[2], original[0], original[1]])
        self.assertEqual(original, [row("ordinary"), {"identity": {"nativeId": "bad"}}, row("pinned")])

    def test_duplicate_rows_for_one_pinned_identity_stay_adjacent_and_appear_once(self):
        first, duplicate, other = row("pin"), row("pin", "second source"), row("other")
        result = order_pinned_rows([other, first, duplicate], SavedView.from_references([reference("pin")]))
        self.assertEqual(result, [first, duplicate, other])
        self.assertEqual(len(result), 3)

    def test_pins_preserve_the_public_projection_order_for_every_sort_and_group(self):
        from test_terminal_model import lease, read, report, source, state
        from test_terminal_model import row as session

        states = []
        references = []
        for host, labels in (("north", ("Zulu", "Alpha")), ("south", ("Bravo", "Echo"))):
            rows = [session(f"{host}-{i}", title=label, host=host) for i, label in enumerate(labels)]
            for i, item in enumerate(rows):
                item["activity"]["at"] = 950 + i
            route = source(host, host=host)
            states.append(state(route, current_read=read(
                rows=rows, leases=[lease(item["identity"]["nativeId"], host=host) for item in rows], host=host
            )))
            references.append(rows[0]["identity"])
        for sort in SORTS:
            for group in GROUPS:
                with self.subTest(sort=sort, group=group):
                    projected = report(states, filters={"sort": sort, "group": group})["sessions"]
                    before = json.dumps(projected, sort_keys=True)
                    view = SavedView.from_references(reversed(references), sort=sort, group=group)
                    result = order_pinned_rows(projected, view)
                    self.assertEqual([item["identity"] for item in result[:2]], list(reversed(references)))
                    self.assertEqual(result[2:], [item for item in projected if item["identity"] not in references])
                    self.assertEqual(json.dumps(projected, sort_keys=True), before)


class SavedViewPathAndFileTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="observer-dashboard-view-")
        self.root = Path(self.temp.name) / "state"
        self.root.mkdir(mode=0o700)
        self.root.chmod(0o700)

    def tearDown(self):
        self.temp.cleanup()

    def test_root_resolution_uses_absolute_xdg_or_home_fallback(self):
        self.assertEqual(
            select_state_root(environ={"XDG_STATE_HOME": str(self.root)}, home=Path("/unused")),
            self.root,
        )
        self.assertEqual(
            select_state_root(environ={}, home=Path("/home/example")),
            Path("/home/example/.local/state"),
        )
        for value in ("relative/state", "/tmp/../state"):
            with self.subTest(value=value), self.assertRaises(SavedViewError):
                select_state_root(environ={"XDG_STATE_HOME": value})

    def test_missing_state_root_or_file_never_creates_startup_state(self):
        self.assertIsNone(load_view_bytes(self.root))
        self.assertFalse((self.root / APP_DIRECTORY).exists())
        missing_root = self.root / "missing"
        with self.assertRaises(SavedViewError):
            load_view_bytes(missing_root)
        self.assertFalse(missing_root.exists())

    def test_deliberate_save_creates_only_private_appdir_and_atomic_state_file(self):
        payload = encode_saved_view(SavedView.from_references([reference("saved")]))
        save_view_bytes(self.root, payload)
        appdir = self.root / APP_DIRECTORY
        path = state_file(self.root)
        self.assertEqual(appdir.stat().st_mode & 0o777, 0o700)
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(load_view_bytes(self.root), payload)
        self.assertEqual(decode_saved_view(path.read_bytes()).references, (reference("saved"),))
        self.assertEqual(list(appdir.glob("*.tmp")), [])

    def test_root_and_application_directory_symlinks_or_unsafe_modes_are_rejected(self):
        target = Path(self.temp.name) / "target"
        target.mkdir(mode=0o700)
        target.chmod(0o700)
        root_link = Path(self.temp.name) / "state-link"
        root_link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(SavedViewError):
            load_view_bytes(root_link)

        self.root.chmod(0o722)
        with self.assertRaises(SavedViewError):
            save_view_bytes(self.root, encode_saved_view(SavedView()))
        self.assertFalse((self.root / APP_DIRECTORY).exists())
        self.root.chmod(0o700)

        (self.root / APP_DIRECTORY).symlink_to(target, target_is_directory=True)
        with self.assertRaises(SavedViewError):
            save_view_bytes(self.root, encode_saved_view(SavedView()))
        self.assertEqual(list(target.iterdir()), [])

    def test_existing_owned_application_directory_keeps_safe_permissions(self):
        appdir = self.root / APP_DIRECTORY
        appdir.mkdir(mode=0o755)
        appdir.chmod(0o755)
        payload = encode_saved_view(SavedView.from_references([reference("saved")]))
        save_view_bytes(self.root, payload)
        self.assertEqual(load_view_bytes(self.root), payload)
        self.assertEqual(appdir.stat().st_mode & 0o777, 0o755)
        self.assertEqual(state_file(self.root).stat().st_mode & 0o777, 0o600)
        appdir.chmod(0o777)
        with self.assertRaises(SavedViewError):
            save_view_bytes(self.root, encode_saved_view(SavedView()))
        self.assertEqual(state_file(self.root).read_bytes(), payload)

    def test_unsafe_existing_files_are_preserved_on_load_and_save(self):
        payload = encode_saved_view(SavedView.from_references([reference("new")]))
        appdir = self.root / APP_DIRECTORY
        appdir.mkdir(mode=0o700)
        appdir.chmod(0o700)
        path = state_file(self.root)
        external = Path(self.temp.name) / "outside.json"
        external.write_bytes(b"preserve-me")
        path.symlink_to(external)
        with self.assertRaises(SavedViewError):
            load_view_bytes(self.root)
        with self.assertRaises(SavedViewError):
            save_view_bytes(self.root, payload)
        self.assertTrue(path.is_symlink())
        self.assertEqual(external.read_bytes(), b"preserve-me")

    def test_corrupt_unsupported_nonregular_oversize_and_public_files_are_preserved(self):
        appdir = self.root / APP_DIRECTORY
        appdir.mkdir(mode=0o700)
        appdir.chmod(0o700)
        path = state_file(self.root)
        new_payload = encode_saved_view(SavedView.from_references([reference("replacement")]))
        bad_payloads = (
            b"not json",
            b'{"version":2,"pins":[],"sort":"activity","group":"none"}',
            b'{"version":1,"pins":[],"sort":"activity","group":"none","extra":true}',
        )
        for payload in bad_payloads:
            with self.subTest(payload=payload):
                path.write_bytes(payload)
                path.chmod(0o600)
                with self.assertRaises(SavedViewError):
                    load_view_bytes(self.root)
                with self.assertRaises(SavedViewError):
                    save_view_bytes(self.root, new_payload)
                self.assertEqual(path.read_bytes(), payload)

        path.unlink()
        os.mkfifo(path, 0o600)
        with self.assertRaises(SavedViewError):
            load_view_bytes(self.root)
        with self.assertRaises(SavedViewError):
            save_view_bytes(self.root, new_payload)
        path.unlink()

        oversized = b"{" + b" " * MAX_STATE_BYTES
        path.write_bytes(oversized)
        path.chmod(0o600)
        with self.assertRaises(SavedViewError):
            load_view_bytes(self.root)
        with self.assertRaises(SavedViewError):
            save_view_bytes(self.root, new_payload)
        self.assertEqual(path.read_bytes(), oversized)

        path.write_bytes(encode_saved_view(SavedView()))
        path.chmod(0o644)
        public_bytes = path.read_bytes()
        with self.assertRaises(SavedViewError):
            save_view_bytes(self.root, new_payload)
        self.assertEqual(path.read_bytes(), public_bytes)

    def test_atomic_replace_failure_preserves_old_file_and_removes_normal_staging_file(self):
        old = encode_saved_view(SavedView.from_references([reference("old")]))
        new = encode_saved_view(SavedView.from_references([reference("new")]))
        save_view_bytes(self.root, old)
        for operation in ("write", "replace"):
            with self.subTest(operation=operation):
                with patch(f"agent_observer.terminal.dashboard_view.os.{operation}", side_effect=OSError("injected")):
                    with self.assertRaises(SavedViewError):
                        save_view_bytes(self.root, new)
                self.assertEqual(state_file(self.root).read_bytes(), old)
                self.assertEqual(list((self.root / APP_DIRECTORY).glob("*.tmp")), [])


class SavedViewControllerTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="observer-dashboard-view-controller-")
        self.root = Path(self.temp.name) / "state"
        self.root.mkdir(mode=0o700)
        self.root.chmod(0o700)

    def tearDown(self):
        self.temp.cleanup()

    async def test_real_helper_load_and_save_are_private_and_leave_no_startup_file(self):
        controller = SavedViewController(self.root)
        self.assertEqual(await controller.load(), SavedView())
        self.assertTrue(controller.persistence_enabled)
        self.assertFalse((self.root / APP_DIRECTORY).exists())
        selected = toggle_pin(controller.view, reference("saved"))
        controller.submit(selected)
        await controller.close()
        self.assertEqual(decode_saved_view(state_file(self.root).read_bytes()), selected)
        self.assertEqual(controller.persisted_view, selected)
        self.assertTrue(controller.changed.is_set())
        self.assertEqual(state_file(self.root).stat().st_mode & 0o777, 0o600)

    async def test_latest_accepted_snapshot_coalesces_behind_one_active_child(self):
        helper = write_test_helper(
            Path(self.temp.name) / "recording_helper.py",
            """
            if operation == "load":
                sys.stdout.buffer.write(b"MISSING\\n")
            else:
                payload = sys.stdin.buffer.read()
                calls = pathlib.Path(root) / "helper-calls.jsonl"
                with calls.open("ab") as stream:
                    stream.write(payload + b"\\n")
                if json.loads(payload)["pins"][0]["nativeId"] == "first":
                    time.sleep(0.12)
                sys.stdout.buffer.write(b"OK\\n")
            """,
        )
        controller = SavedViewController(
            self.root, helper_path=helper, save_timeout=1, shutdown_drain=1
        )
        await controller.load()
        first = SavedView.from_references([reference("first")])
        second = SavedView.from_references([reference("second")])
        newest = SavedView.from_references([reference("newest")])
        controller.submit(first)
        calls = self.root / "helper-calls.jsonl"
        deadline = asyncio.get_running_loop().time() + 1
        while not calls.exists() and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.005)
        self.assertTrue(calls.exists())
        controller.submit(second)
        controller.submit(newest)
        await controller.close()
        documents = [json.loads(line) for line in calls.read_bytes().splitlines()]
        self.assertEqual(
            [document["pins"][0]["nativeId"] for document in documents],
            ["first", "newest"],
        )

    async def test_independent_concurrent_writers_leave_one_complete_last_save_wins_view(self):
        first = SavedViewController(self.root)
        second = SavedViewController(self.root)
        await asyncio.gather(first.load(), second.load())
        view_a = SavedView.from_references([reference("writer-a")], sort="label")
        view_b = SavedView.from_references([reference("writer-b")], group="host-home")
        first.submit(view_a)
        second.submit(view_b)
        await asyncio.gather(first.close(), second.close())
        final = decode_saved_view(state_file(self.root).read_bytes())
        self.assertIn(final, (view_a, view_b))

        later = SavedViewController(self.root)
        await later.load()
        view_c = SavedView.from_references([reference("writer-c")], sort="host")
        later.submit(view_c)
        await later.close()
        self.assertEqual(decode_saved_view(state_file(self.root).read_bytes()), view_c)

    async def test_blocked_load_and_save_are_killed_reaped_and_do_not_block_event_loop(self):
        helper = write_test_helper(
            Path(self.temp.name) / "blocked_helper.py",
            """
            pathlib.Path(root, "helper-pid").write_text(str(os.getpid()))
            if operation == "load":
                time.sleep(60)
            else:
                sys.stdin.buffer.read()
                time.sleep(60)
            """,
        )
        ticks = 0
        running = True

        async def tick():
            nonlocal ticks
            while running:
                ticks += 1
                await asyncio.sleep(0.002)

        ticker = asyncio.create_task(tick())
        controller = SavedViewController(
            self.root,
            helper_path=helper,
            load_timeout=0.05,
            save_timeout=0.05,
            shutdown_drain=0.5,
            reap_timeout=0.2,
        )
        started = time.monotonic()
        self.assertEqual(await controller.load(), SavedView())
        self.assertLess(time.monotonic() - started, 1.0)
        self.assertFalse(controller.persistence_enabled)
        self.assertEqual(controller.warning, "saved_view_load_timeout")
        load_pid_file = self.root / "helper-pid"
        if load_pid_file.exists():
            load_pid = int(load_pid_file.read_text())
            with self.assertRaises(ProcessLookupError):
                os.kill(load_pid, 0)
        await controller.close()
        self.assertGreater(ticks, 0)
        self.assertIsNone(controller._process)
        self.assertTrue(controller._save_task is None or controller._save_task.done())

        helper = write_test_helper(
            Path(self.temp.name) / "blocked_save_helper.py",
            """
            if operation == "load":
                sys.stdout.buffer.write(b"MISSING\\n")
            else:
                pathlib.Path(root, "helper-pid").write_text(str(os.getpid()))
                sys.stdin.buffer.read()
                time.sleep(60)
            """,
        )
        load_pid_file.unlink(missing_ok=True)
        save_controller = SavedViewController(
            self.root,
            helper_path=helper,
            save_timeout=0.05,
            shutdown_drain=0.5,
            reap_timeout=0.2,
        )
        await save_controller.load()
        # A stale receipt from the load case cannot prove the save child ran.
        (self.root / "helper-pid").unlink(missing_ok=True)
        save_controller.submit(SavedView.from_references([reference("unsaved")]))
        await save_controller.close()
        self.assertEqual(save_controller.warning, "saved_view_save_timeout")
        self.assertTrue(load_pid_file.exists())
        save_pid = int((self.root / "helper-pid").read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(save_pid, 0)
        self.assertIsNone(save_controller._process)
        running = False
        await ticker

    async def test_unexpected_finished_save_task_failure_is_observed_on_close(self):
        controller = SavedViewController(self.root)
        await controller.load()
        accepted = SavedView.from_references([reference("unsaved")])
        with patch.object(controller, "_invoke", side_effect=RuntimeError("controlled fault")):
            controller.submit(accepted)
            await asyncio.sleep(0)
            await controller.close()
        self.assertEqual(controller.view, accepted)
        self.assertEqual(controller.cleanup_error, "saved_view_internal_failure")
        self.assertFalse(controller.persistence_enabled)

    async def test_shutdown_deadline_kills_and_joins_active_save_child(self):
        helper = write_test_helper(
            Path(self.temp.name) / "slow_save_helper.py",
            """
            if operation == "load":
                sys.stdout.buffer.write(b"MISSING\\n")
            else:
                pathlib.Path(root, "helper-pid").write_text(str(os.getpid()))
                sys.stdin.buffer.read()
                time.sleep(60)
            """,
        )
        controller = SavedViewController(
            self.root,
            helper_path=helper,
            save_timeout=5,
            shutdown_drain=0.05,
            reap_timeout=0.2,
        )
        await controller.load()
        controller.submit(SavedView.from_references([reference("pending")]))
        deadline = asyncio.get_running_loop().time() + 1
        pid_file = self.root / "helper-pid"
        while not pid_file.exists() and asyncio.get_running_loop().time() < deadline:
            await asyncio.sleep(0.005)
        await controller.close()
        self.assertEqual(controller.warning, "saved_view_shutdown_timeout")
        pid = int(pid_file.read_text())
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)
        self.assertIsNone(controller._process)
        self.assertTrue(controller._save_task.done())

    async def test_operation_deadline_includes_slow_child_creation_and_reaps_late_handle(self):
        helper = write_test_helper(
            Path(self.temp.name) / "late_spawn_helper.py",
            """
            time.sleep(60)
            """,
        )
        controller = SavedViewController(
            self.root,
            helper_path=helper,
            load_timeout=0.02,
            reap_timeout=0.25,
        )
        create_process = asyncio.create_subprocess_exec
        created = []

        async def delayed_create(*args, **kwargs):
            await asyncio.sleep(0.06)
            process = await create_process(*args, **kwargs)
            created.append(process)
            await asyncio.sleep(0.02)
            return process

        with patch(
            "agent_observer.terminal.dashboard_view.asyncio.create_subprocess_exec",
            side_effect=delayed_create,
        ):
            await controller.load()
        self.assertEqual(controller.warning, "saved_view_load_timeout")
        self.assertEqual(len(created), 1)
        self.assertIsNotNone(created[0].returncode)
        with self.assertRaises(ProcessLookupError):
            os.kill(created[0].pid, 0)
        self.assertIsNone(controller._process)
        self.assertIsNone(controller.cleanup_error)

    async def test_constructor_rejects_nonfinite_timeouts_and_relative_roots_are_session_only(self):
        for timeout in (float("nan"), float("inf"), 0):
            with self.subTest(timeout=timeout), self.assertRaises(ValueError):
                SavedViewController(self.root, load_timeout=timeout)
        controller = SavedViewController.from_environment(
            environ={"XDG_STATE_HOME": "relative"}
        )
        self.assertIsNone(controller.state_root)
        self.assertFalse(controller.persistence_enabled)
        self.assertEqual(controller.warning, "saved_view_state_root_unsafe")
        self.assertEqual(await controller.load(), SavedView())


if __name__ == "__main__":
    unittest.main()
