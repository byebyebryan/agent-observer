"""First-party transport against the actual controlled local publisher."""

import os
import unittest

from test_service_runtime import Running, source_worker

from agent_observer.contract import ContractError
from agent_observer.service_client import frames


class ServiceClientTest(unittest.TestCase):
    def test_explicit_cold_status_and_host_rejection(self):
        with Running() as server:
            frame = next(frames(server.path, host_scope="fixture", operation="status"))
            self.assertEqual(frame["uid"], os.geteuid())
            self.assertEqual(frame["state"], "warming")
            with self.assertRaises(ContractError):
                next(frames(server.path, host_scope="another", operation="snapshot"))

    def test_watch_parses_multiple_views_and_closes_its_peer(self):
        with Running(collect=True, factory=source_worker) as server:
            stream = frames(server.path, host_scope="fixture")
            try:
                values = [next(stream) for _ in range(4)]
            finally:
                stream.close()
            self.assertEqual([v["sequence"] for v in values], [1, 2, 3, 4])
            self.assertTrue(any(v["snapshot"] is not None for v in values))
            self.assertEqual(server.runtime.counts["workerStarts"], 2)

    def test_service_absence_never_falls_back_or_creates_endpoint(self):
        with Running() as server:
            missing = server.path.with_name("missing.sock")
            with self.assertRaises(FileNotFoundError):
                next(frames(missing, host_scope="fixture", operation="status"))
            self.assertFalse(missing.exists())
            self.assertEqual(server.runtime.counts["workerStarts"], 0)
