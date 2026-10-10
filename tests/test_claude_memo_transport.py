"""Actual owned processes prove private memo replies never bypass admission."""
import copy
import os
import stat
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from test_service_state import provider_snapshot
from test_service_contract import fixture
from agent_observer._claude_file_memo import FileMemo
from agent_observer.contract import canonical, store_namespace
from agent_observer.service_runtime import Runtime, Worker
from agent_observer.service_state import ServiceState

class ClaudeMemoTransportTest(unittest.TestCase):
    def setUp(self):
        self.value = provider_snapshot('claude')
        self.value['host']['uid'] = os.geteuid()
        self.source = self.value['sources'][0]
        self.source['namespace'] = store_namespace('claude', self.source['configHome'],
            self.source['configHomeKind'], os.geteuid())
        for row in self.value['sessions']:
            row['identity']['namespace'] = self.source['namespace']
        self.home = self.source['configHome']
        self.now = 15000
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = ServiceState(host_scope='fixture', configs={'claude': (self.home, self.source['configHomeKind'])},
            uid=os.geteuid(), clock=lambda: self.now, boot_id=fixture()['bootId'], clock_domain=fixture()['clockDomain'])
        self.runtime = Runtime(self.state, Path(self.temp.name) / 'read.sock')
        self.addCleanup(self.runtime.selector.close)
        self.addCleanup(self.runtime.image_memos['claude'].close)
        self.state.attempt('claude', 'runtime')
        self.state.accept('claude', 'runtime', self.value, sampled_ms=self.now, ttl_ms=60000)
        self.packet = FileMemo(self.home).export()
        self.packet.update(scope=[[1, 2, os.geteuid(), stat.S_IFDIR | 0o700]] * 2, context='a' * 64,
            entries=[{'path': ['project', '01234567-0123-4567-89ab-0123456789ab.jsonl'],
                      'project': [1, 3, os.geteuid(), stat.S_IFDIR | 0o700],
                      'file': [1, 4, 100, 123, 123, os.geteuid(), stat.S_IFREG | 0o600], 'positive': True}])

    def complete(self, envelope, *, stale=False, timed_out=False):
        job = self.runtime.scheduler.start_due(self.now)[0]
        self.state.attempt('claude', job.component)
        process = subprocess.Popen([sys.executable, '-I', '-B', '-c', 'pass'], stdout=subprocess.PIPE,
                                   stderr=subprocess.DEVNULL, start_new_session=True)
        process.wait(timeout=2)
        process._observer_claude_envelope = True
        worker = Worker(job, process)
        worker.buffer.extend(canonical(envelope).encode())
        self.runtime.workers['claude'] = worker
        if stale: self.runtime.scheduler.invalidate('claude')
        self.runtime._complete(worker, timed_out=timed_out)

    def test_valid_reply_retains_metadata_after_normal_snapshot_admission(self):
        phase = copy.deepcopy(self.value['sessions'][0]['phase'])
        self.complete({'snapshot': self.value, 'claudeMemo': self.packet})
        self.assertEqual(len(self.runtime.claude_memo.entries), 1)
        self.assertEqual(self.state.snapshot['sessions'][0]['phase'], phase)
        self.assertNotIn('claudeMemo', self.state.snapshot)

    def test_invalid_private_payload_rejects_receipt_and_clears_memo(self):
        self.runtime.claude_memo = FileMemo(self.home, self.packet)
        bad = copy.deepcopy(self.packet)
        bad['entries'][0]['content'] = 'unpermitted'
        accepted = self.state.receipts['claude']['runtime'].accepted
        self.complete({'snapshot': self.value, 'claudeMemo': bad})
        self.assertEqual(self.state.receipts['claude']['runtime'].accepted, accepted)
        self.assertFalse(self.runtime.claude_memo.entries)
        self.assertEqual(self.state.snapshot['sessions'][0]['runtime']['value'], 'unknown')

    def test_changed_generation_or_timeout_cannot_reuse_memo(self):
        self.runtime.claude_memo = FileMemo(self.home, self.packet)
        self.complete({'snapshot': self.value, 'claudeMemo': self.packet}, stale=True)
        self.assertFalse(self.runtime.claude_memo.entries)
        self.runtime.scheduler.due['claude', 'runtime'] = self.now
        self.runtime.scheduler.due['claude', 'history'] = self.now + 10000
        self.runtime.claude_memo = FileMemo(self.home, self.packet)
        self.complete({'snapshot': self.value, 'claudeMemo': self.packet}, timed_out=True)
        self.assertFalse(self.runtime.claude_memo.entries)

    def test_context_change_accepts_snapshot_but_discards_old_memo(self):
        value = copy.deepcopy(self.value)
        value['sources'][0]['runtime']['binarySha256'] = 'b' * 64
        self.complete({'snapshot': value, 'claudeMemo': self.packet})
        self.assertFalse(self.runtime.claude_memo.entries)

    @unittest.skipUnless(callable(getattr(os, "memfd_create", None)), "Python lacks Linux memfd support")
    def test_real_worker_accepts_sealed_input_and_emits_only_normalized_envelope(self):
        job = self.runtime.scheduler.start_due(self.now)[0]
        process = self.runtime._spawn(job)
        try:
            output = process.stdout.read()
            process.wait(timeout=5)
            self.assertEqual(process.returncode, 0)
            import json
            envelope = json.loads(output)
            self.assertEqual(set(envelope), {'snapshot', 'claudeMemo'})
            self.assertEqual(envelope['claudeMemo']['entries'], [])
            self.assertEqual(envelope['snapshot']['sources'][0]['provider'], 'claude')
        finally:
            self.runtime._stop_worker(Worker(job, process))
            self.runtime._close_memo_channel(process)
            process.stdout.close()

    def test_worker_without_memfd_uses_normal_snapshot_without_memo(self):
        job = self.runtime.scheduler.start_due(self.now)[0]
        with patch.object(os, 'memfd_create', None, create=True):
            process = self.runtime._spawn(job)
        try:
            output = process.stdout.read()
            process.wait(timeout=5)
            self.assertEqual(process.returncode, 0)
            import json
            snapshot = json.loads(output)
            self.assertNotIn('claudeMemo', snapshot)
            self.assertEqual(snapshot['sources'][0]['provider'], 'claude')
            self.assertFalse(process._observer_claude_envelope)
        finally:
            self.runtime._stop_worker(Worker(job, process))
            self.runtime._close_memo_channel(process)
            process.stdout.close()
