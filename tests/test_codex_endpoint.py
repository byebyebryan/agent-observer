"""Synthetic proc/filesystem metadata; no real shared socket is created."""

import hashlib
import os
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from agent_observer.codex_endpoint import (
    EndpointError,
    inspect_managed_endpoint,
    validate_incarnation,
)
from agent_observer._image_memo import ImageMemo


class EndpointInspectionTest(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        root = Path(self.scratch.name)
        self.home = root / "config"
        control = self.home / "app-server-control/app-server-control.sock"
        control.parent.mkdir(parents=True)
        self.target = (
            Path(f"/tmp/codex-daemon-{os.geteuid()}")
            / hashlib.sha256(str(control).encode()).hexdigest()
        )
        control.symlink_to(self.target)
        self.release = "0.160.0-x86_64-unknown-linux-musl"
        self.executable = (
            self.home / "packages/app-server-daemon/releases" / self.release / "bin/codex"
        )
        self.executable.parent.mkdir(parents=True)
        self.executable.write_bytes(b"synthetic-binary-not-executed")
        self.fingerprint = hashlib.sha256(self.executable.read_bytes()).hexdigest()
        self.proc = root / "proc"
        (self.proc / "net").mkdir(parents=True)
        self.process(123, 456)
        self.listener(314159)
        self.socket_stat = SimpleNamespace(
            st_mode=stat.S_IFSOCK | 0o600, st_uid=os.geteuid(), st_dev=71, st_ino=999999
        )
        original_stat = Path.stat

        def fixture_stat(path, *args, **kwargs):
            if path == self.target:
                return self.socket_stat
            return original_stat(path, *args, **kwargs)

        peer_patch = patch(
            "agent_observer.codex_endpoint._endpoint_peer", return_value=(123, os.geteuid())
        )
        self.peer = peer_patch.start()
        self.addCleanup(peer_patch.stop)
        self.patch = patch.object(Path, "stat", fixture_stat)
        self.patch.start()
        self.addCleanup(self.patch.stop)

    def process(self, pid, start):
        directory = self.proc / str(pid)
        (directory / "fd").mkdir(parents=True)
        (directory / "exe").symlink_to(self.executable)
        (directory / "fd/33").symlink_to("socket:[314159]")
        (directory / "stat").write_text(
            str(pid) + " (synthetic comm) " + " ".join(["0"] * 19 + [str(start), "0"]) + "\n"
        )

    def listener(self, inode):
        (self.proc / "net/unix").write_text(
            "Num RefCount Protocol Flags Type St Inode Path\n"
            + f"00000000: 00000002 00000000 00010000 0001 01 {inode} {self.target}\n"
        )

    def inspect(self, **changes):
        image_args = {'image_cache':changes['image_cache']} if 'image_cache' in changes else {}
        return inspect_managed_endpoint(
            self.home,
            release=self.release,
            binary_sha256=changes.get("binary_sha256", self.fingerprint),
            version="0.160.0",
            proc_root=self.proc,
            **image_args,
        )

    def test_anchored_digest_does_not_replace_birth_or_listener_ownership_checks(self):
        memo = ImageMemo('codex')
        try:
            first = self.inspect(image_cache=memo)
            second = self.inspect(image_cache=memo)
            self.assertEqual(first,second)
            self.assertEqual(len(memo),1)
            stat_path = self.proc/'123/stat'
            stat_path.write_text('123 (synthetic comm) '+ ' '.join(['0']*19+['999','0'])+'\n')
            with self.assertRaisesRegex(EndpointError,'runtime_incarnation_changed'):
                validate_incarnation(first,proc_root=self.proc)
            self.assertEqual(self.inspect(image_cache=memo).start_ticks,999)
            link = self.proc/'123/fd/33'
            link.unlink()
            link.symlink_to('socket:[123456]')
            with self.assertRaisesRegex(EndpointError,'runtime_owner_ambiguous'):
                self.inspect(image_cache=memo)
        finally:
            memo.close()

    def test_exact_listener_owner_and_kernel_vs_filesystem_inode(self):
        identity = self.inspect()
        self.assertEqual((identity.pid, identity.start_ticks), (123, 456))
        self.assertEqual(identity.listener_inode, 314159)
        self.assertEqual(identity.endpoint_inode, 999999)
        self.assertNotEqual(identity.listener_inode, identity.endpoint_inode)
        validate_incarnation(identity, proc_root=self.proc)

    def test_missing_endpoint_does_not_create_or_repair_it(self):
        control = self.home / "app-server-control/app-server-control.sock"
        control.unlink()
        with self.assertRaisesRegex(EndpointError, "^endpoint_unavailable$"):
            self.inspect()
        self.assertFalse(control.exists())

    def test_namespace_and_ownership_mismatch_fail_closed(self):
        control = self.home / "app-server-control/app-server-control.sock"
        control.unlink()
        control.symlink_to("/tmp/synthetic-other-runtime.sock")
        with self.assertRaisesRegex(EndpointError, "^endpoint_namespace_mismatch$"):
            self.inspect()
        control.unlink()
        control.symlink_to(self.target)
        self.socket_stat.st_mode = stat.S_IFSOCK | 0o666
        with self.assertRaisesRegex(EndpointError, "^endpoint_ownership_mismatch$"):
            self.inspect()

    def test_basename_pid_and_filesystem_inode_are_insufficient(self):
        fd = self.proc / "123/fd/33"
        fd.unlink()
        fd.symlink_to(f"socket:[{self.socket_stat.st_ino}]")
        with self.assertRaisesRegex(EndpointError, "^runtime_owner_ambiguous$"):
            self.inspect()

    def test_kernel_peer_selects_identity_independent_of_unrelated_processes(self):
        self.process(124, 457)
        self.assertEqual(123, self.inspect().pid)
        (self.proc / "124/exe").unlink()
        self.assertEqual(123, self.inspect().pid)

    def test_kernel_peer_uid_and_executable_must_match(self):
        self.peer.return_value = (123, os.geteuid() + 1)
        with self.assertRaisesRegex(EndpointError, "^runtime_peer_identity_mismatch$"):
            self.inspect()
        self.peer.return_value = (124, os.geteuid())
        self.process(124, 457)
        (self.proc / "124/exe").unlink()
        (self.proc / "124/exe").symlink_to("/synthetic/unrelated")
        with self.assertRaisesRegex(EndpointError, "^runtime_peer_identity_mismatch$"):
            self.inspect()

    def test_changed_artifact_and_reused_pid_rejected(self):
        with self.assertRaisesRegex(EndpointError, "^runtime_binary_not_accepted$"):
            self.inspect(binary_sha256="0" * 64)
        identity = self.inspect()
        (self.proc / "123/stat").write_text("123 (reused) " + " ".join(["0"] * 19 + ["999", "0"]))
        with self.assertRaisesRegex(EndpointError, "^runtime_incarnation_changed$"):
            validate_incarnation(identity, proc_root=self.proc)

    def test_endpoint_replacement_invalidates_read_from_old_connection(self):
        identity = self.inspect()
        self.socket_stat.st_ino += 1
        with self.assertRaisesRegex(EndpointError, "^endpoint_incarnation_changed$"):
            validate_incarnation(identity, proc_root=self.proc)

    def test_unregistered_owned_image_retains_actual_runtime_identity(self):
        identity = inspect_managed_endpoint(self.home, proc_root=self.proc)
        self.assertEqual(identity.pid, 123)
        self.assertEqual(identity.version, "0.160.0")
        self.assertEqual(identity.binary_sha256, self.fingerprint)
        validate_incarnation(identity, proc_root=self.proc)
