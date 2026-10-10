"""Independent frozen parity, change guards and normalized worker transport."""
import copy
import json
import os
import random
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import claude_transcript_reference as reference
from agent_observer import _claude_file_memo as memo_module
from agent_observer import _claude_history_worker as worker
from agent_observer._claude_file_memo import FileMemo, decode_packet, read_packet, sealed_packet
from agent_observer.claude_saved_identity import saved_ids

SID = '01234567-0123-4567-89ab-0123456789ab'
OTHER = '11234567-0123-4567-89ab-0123456789ab'

def record(**changes):
    value = {'type': 'user', 'sessionId': SID, 'isSidechain': False,
             'timestamp': '2026-10-10T00:00:00Z', 'message': {'role': 'user', 'content': 'PRIVATE SENTINEL'}}
    value.update(changes)
    return json.dumps(value).encode() + b'\n'

class ClaudeMemoTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.project = self.home / 'projects/project'
        self.project.mkdir(parents=True)
        self.path = self.project / (SID + '.jsonl')
        self.path.write_bytes(record())
        self.memo = FileMemo(self.home)

    def read(self, **options):
        return worker.transcript_metadata(self.path, SID, file_memo=self.memo, **options)

    def test_frozen_parser_parity_for_seeded_records_and_head_tail_boundaries(self):
        rng = random.Random(51715)
        records = [record(), record(type='assistant', message={'role': 'assistant', 'content': []}),
            record(isSidechain=True), record(isMeta=True), record(sessionId=OTHER), record(isSidechain=None),
            record(timestamp='bad'), record(message={'role': 'user', 'content': '<command-name>/exit'}),
            record(message=None), b'\n', b'null\n', b'{"type":"meta","padding":"long content"}\n',
            b'{"type":"user","type":"assistant"}\n', b'{oops}\n', b'\xff\n']
        with patch.object(worker, 'MAX_ACTIVITY_BYTES', 256), patch.object(reference, 'MAX_ACTIVITY_BYTES', 256), \
                patch.object(worker, 'MAX_COMPANION_BYTES', 96), patch.object(reference, 'MAX_COMPANION_BYTES', 96):
            for number in range(250):
                data = b''.join(rng.choice(records) for _ in range(rng.randrange(0, 15)))
                if rng.random() < .25:
                    data = data[:-rng.randrange(1, min(10, len(data)) + 1)] if data else data
                self.path.write_bytes(data)
                expected = {'activity': reference.transcript_activity(self.path, SID),
                            'kind': reference.transcript_kind(self.path, SID)}
                with self.subTest(number=number):
                    self.assertEqual(worker.transcript_metadata(self.path, SID), expected)
                    self.assertEqual(self.read(), expected)

    def test_shared_decode_once_and_warm_reuse_without_conversation_clock_renewal(self):
        self.path.write_bytes(record() + record(type='assistant', message={'role': 'assistant', 'content': 'secret'}))
        real = worker.json.loads
        with patch.object(worker.json, 'loads', wraps=real) as decode:
            initial = self.read()
            self.assertEqual(decode.call_count, 2) # head and tail overlap entirely
        with patch.object(worker.json, 'loads', side_effect=AssertionError('unchanged transcript decoded')):
            self.assertEqual(self.read(), initial)
        packet = self.memo.export()
        self.assertNotIn('PRIVATE SENTINEL', json.dumps(packet))
        self.assertNotIn('secret', json.dumps(packet))
        self.assertEqual(packet['entries'][0]['projection']['activity']['at'], initial['activity']['at'])
        self.assertEqual(worker.transcript_metadata(self.path, OTHER, file_memo=self.memo)['kind'], 'unknown')

    def test_append_truncate_atomic_replace_delete_symlink_and_permission_changes_reparse(self):
        initial = self.read()
        with self.path.open('ab') as stream:
            stream.write(record(timestamp='2026-10-10T00:00:01Z'))
        self.assertEqual(self.read()['activity']['at'], initial['activity']['at'] + 1000)
        self.path.write_bytes(record(isSidechain=True))
        self.assertEqual(self.read()['kind'], 'child')
        replacement = self.project / 'new'
        replacement.write_bytes(record())
        replacement.replace(self.path)
        self.assertEqual(self.read()['kind'], 'user')
        os.chmod(self.path, 0o400)
        with patch.object(worker.json, 'loads', wraps=worker.json.loads) as decode:
            self.assertEqual(self.read()['kind'], 'user')
            self.assertGreater(decode.call_count, 0)
        self.path.unlink()
        self.assertEqual(self.read()['kind'], 'unknown')
        replacement.write_bytes(record())
        self.path.symlink_to(replacement)
        self.assertEqual(self.read()['activity']['reason'], 'activity_source_unavailable')
        descriptor = os.open(replacement, os.O_RDONLY)
        self.addCleanup(os.close, descriptor)
        self.assertEqual(self.memo.get(descriptor, 'project', self.path.name, 'projection'), None)

    def test_directory_replacement_and_context_change_invalidate(self):
        initial = self.read()
        old = self.home / 'old-project'
        self.project.rename(old)
        self.project.mkdir()
        self.path.write_bytes(record())
        with patch.object(worker.json, 'loads', wraps=worker.json.loads) as decode:
            self.assertEqual(self.read(), initial)
            self.assertGreater(decode.call_count, 0)
        self.memo.bind_context('a' * 64)
        self.assertFalse(self.memo.entries)
        self.read()
        self.memo.bind_context('a' * 64)
        self.assertTrue(self.memo.entries)
        self.memo.bind_context('b' * 64)
        self.assertFalse(self.memo.entries)
        self.read()
        projects = self.home / 'projects'
        projects.rename(self.home / 'old-projects')
        self.project.mkdir(parents=True)
        self.path.write_bytes(record(isSidechain=True))
        self.assertEqual(self.read()['kind'], 'child')

    def test_positive_saved_identity_is_reused_but_never_conceals_changed_conflict(self):
        self.assertEqual(saved_ids(self.home, file_memo=self.memo), {SID})
        with patch('agent_observer.claude_saved_identity.decode_document', side_effect=AssertionError('reparsed')):
            self.assertEqual(saved_ids(self.home, file_memo=self.memo), {SID})
        self.path.write_bytes(record() + record(sessionId=OTHER))
        self.assertEqual(saved_ids(self.home, file_memo=self.memo), set())
        self.path.write_bytes(record())
        self.assertEqual(saved_ids(self.home, file_memo=self.memo), {SID})
        self.path.unlink()
        self.assertEqual(saved_ids(self.home, file_memo=self.memo), set())

    def test_failed_and_incomplete_metadata_is_not_cached(self):
        for data in (record()[:-1], record() + b'{oops}\n', record(sessionId=OTHER), record(timestamp='bad')):
            self.path.write_bytes(data)
            self.read()
            self.assertFalse(any('projection' in r for r in self.memo.entries.values()))
        self.path.write_bytes(record())
        self.assertEqual(self.read()['kind'], 'user')

    def test_guard_detects_change_during_hit_and_does_not_store_stale_parse(self):
        self.read()
        fd = os.open(self.path, os.O_RDONLY)
        self.addCleanup(os.close, fd)
        before = os.fstat(fd)
        guard = self.memo._guard
        calls = 0
        def changed(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.path.write_bytes(record(isSidechain=True))
            return guard(*args)
        with patch.object(self.memo, '_guard', side_effect=changed):
            self.assertIsNone(self.memo.get(fd, 'project', self.path.name, 'projection'))
        self.memo.put(fd, 'project', self.path.name, 'positive', True, before)
        self.assertFalse(self.memo.entries)

    def test_sealed_read_only_roundtrip_and_strict_content_free_admission(self):
        self.read()
        descriptor = self.memo.descriptor()
        self.addCleanup(os.close, descriptor)
        packet = read_packet(descriptor, self.home)
        self.assertEqual(FileMemo(self.home, packet).export(), self.memo.export())
        with self.assertRaises(OSError):
            os.write(descriptor, b'x')
        wrong = os.open(self.path, os.O_RDONLY)
        self.addCleanup(os.close, wrong)
        with self.assertRaises((ValueError, OSError)):
            read_packet(wrong, self.home)
        bad_packets = []
        for target, key, value in [('root', 'home', '/other'), ('root', 'context', 'bad'),
            ('entry', 'content', 'secret'), ('entry', 'path', ['..', self.path.name]),
            ('entry', 'positive', False), ('projection', 'kind', ['user'])]:
            bad = copy.deepcopy(packet)
            obj = bad if target == 'root' else bad['entries'][0]
            if target == 'projection': obj = obj['projection']
            obj[key] = value
            bad_packets.append(json.dumps(bad).encode())
        bad_packets += [b'{"memoVersion":1,"memoVersion":1}', b'[' * 1100]
        for data in bad_packets:
            with self.assertRaises(ValueError): decode_packet(data, self.home)

    def test_bounds_eviction_cold_start_and_budget_flags(self):
        initial = self.read()
        self.assertEqual(self.read(activity=False)['activity']['reason'], 'activity_scan_limit')
        self.assertEqual(self.read(kind=False)['kind'], 'unknown')
        with patch.object(worker.os, 'open', side_effect=AssertionError('exhausted scan')):
            self.assertEqual(self.read(activity=False, kind=False)['kind'], 'unknown')
        with patch.object(memo_module, 'MAX_ENTRIES', 1):
            path = self.project / (OTHER + '.jsonl')
            path.write_bytes(record(sessionId=OTHER))
            worker.transcript_metadata(path, OTHER, file_memo=self.memo)
            self.assertEqual(len(self.memo.entries), 1)
        self.memo.retain(set())
        self.assertFalse(self.memo.entries)
        self.assertEqual(self.read(), initial)
        with patch.object(memo_module, 'MAX_PACKET', 200):
            self.assertEqual(self.memo.export()['entries'], [])
