"""Canonical-worker-only bracket capability; controlled pipes, no provider."""

import io
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import test_working_set_capture as capture_fixture

from agent_observer.contract import canonical
from agent_observer.service_runtime import Runtime, Worker


class WorkingSetWorkerProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.fixture = capture_fixture.WorkingSetCaptureTest()
        self.fixture.setUp()
        self.state = self.fixture.state
        self.runtimes = []

    def tearDown(self):
        for runtime in self.runtimes:
            runtime.selector.close()
            for memo in runtime.image_memos.values():
                memo.close()

    def runtime(self, factory=None, cls=Runtime):
        runtime = cls(self.state, "/unused/read.sock", collect=False, worker_factory=factory)
        runtime.scheduler.finish = Mock()
        self.runtimes.append(runtime)
        return runtime

    def sample(self, *, number=11, running=False):
        value = self.fixture.sample(number)
        row = value["sessions"][0]
        row["activity"].update(at=value["collectedAt"] - 1000, health="current",
                               source="codex_rpc", reason="native_timestamp")
        value["sources"][0]["capabilities"]["activity"] = True
        if not running:
            row["runtime"]["value"] = "parked"
            row["phase"], row["blockedReasons"] = None, []
        return value

    @staticmethod
    def job(component="runtime", started=14000):
        return SimpleNamespace(provider="codex", component=component, started=started, generation=0)

    @staticmethod
    def process():
        return SimpleNamespace(stdin=io.BytesIO(), stdout=io.BytesIO())

    def complete(self, runtime, worker, value):
        self.state.attempt("codex", worker.job.component)
        worker.buffer.extend(canonical(value).encode())
        runtime.workers["codex"] = worker
        with (patch.object(runtime, "_exit_status", return_value=0),
              patch.object(runtime, "_stop_worker"),
              patch.object(runtime, "_take_image_memo")):
            runtime._complete(worker)
        self.assertTrue(runtime.scheduler.finish.call_args.kwargs["success"])
        self.assertEqual(self.state.receipts["codex"][worker.job.component].health, "current")

    def test_injected_manual_return_cannot_grant_clock(self):
        # This unchanged _complete path also runs on the before revision. It
        # isolates the original semantic bug rather than a missing new helper.
        process = self.process()
        runtime = self.runtime(lambda _job: process)
        worker = Worker(self.job(), process)
        self.complete(runtime, worker, self.sample())
        self.assertEqual(self.state.working_set_clocks.export(self.state.source_meta("codex")), [])
        self.assertIsNone(self.state.working_set_clocks.ceiling)
        frame = self.state.working_set_frame("status", 1)
        self.assertEqual(frame["projection"]["sessions"], [])
        self.assertEqual(frame["projection"]["scopes"][0]["coverage"]["status"], "partial")

    def canonical_worker(self, runtime, job):
        # Mock only Popen, leaving the exact installed _spawn method and its
        # request path in place. This is capability wiring, not native proof.
        with patch("agent_observer.service_runtime.subprocess.Popen", return_value=self.process()):
            return runtime._start_worker(job)

    def test_default_canonical_path_installs_exact_bracket_and_history_mirror(self):
        for component, expected in (("runtime", 1), ("history", 2)):
            with self.subTest(component=component):
                self.setUp()
                runtime = self.runtime()
                worker = self.canonical_worker(runtime, self.job(component))
                self.assertIsNotNone(worker._clock_provenance)
                value = self.sample()
                self.complete(runtime, worker, value)
                clocks = self.state.working_set_clocks.export(self.state.source_meta("codex"))
                self.assertEqual(len(clocks), expected)
                for clock in clocks:
                    self.assertEqual(clock["sampleId"], value["collectionId"])
                    self.assertEqual(clock["originComponent"], component)
                    self.assertEqual((clock["sampledBoottimeMs"], clock["wallMs"], clock["acceptedBoottimeMs"]),
                                     (14000, value["collectedAt"], 15000))
                self.assertEqual(len(self.state.working_set_frame("status", 1)["projection"]["sessions"]), 1)
                self.tearDown()

    def test_injected_replaced_and_subclass_factories_keep_only_active_authority(self):
        class AlternateRuntime(Runtime):
            def _spawn(self, _job):
                return WorkingSetWorkerProvenanceTest.process()

        for variant in ("injected", "replaced", "subclass"):
            with self.subTest(variant=variant):
                self.setUp()
                runtime = self.runtime((lambda _job: self.process()) if variant == "injected" else None,
                                       AlternateRuntime if variant == "subclass" else Runtime)
                if variant == "replaced":
                    runtime.worker_factory = lambda _job: self.process()
                worker = runtime._start_worker(self.job())
                self.assertIsNone(worker._clock_provenance)
                self.complete(runtime, worker, self.sample(running=True))
                self.assertEqual(self.state.working_set_clocks.export(self.state.source_meta("codex")), [])
                scope = self.state.working_set_frame("status", 1)["projection"]["scopes"][0]
                self.assertIsNotNone(scope["members"][0]["active"])
                self.assertIsNone(scope["members"][0]["recent"])
                self.assertEqual(scope["coverage"]["status"], "complete")
                self.tearDown()

    def test_injected_new_acceptance_cannot_borrow_previous_canonical_clock(self):
        runtime = self.runtime()
        first = self.canonical_worker(runtime, self.job())
        self.complete(runtime, first, self.sample())
        ceiling = self.state.working_set_clocks.ceiling
        self.fixture.now = 16000
        runtime.worker_factory = lambda _job: self.process()
        second = runtime._start_worker(self.job(started=15000))
        self.complete(runtime, second, self.sample(number=12))
        self.assertEqual(self.state.working_set_clocks.ceiling, ceiling)
        self.assertEqual(self.state.working_set_clocks.export(self.state.source_meta("codex")), [])
        scope = self.state.working_set_frame("status", 1)["projection"]["scopes"][0]
        self.assertEqual(scope["members"], [])
        self.assertEqual(len(scope["uncertain"]), 1)
        self.assertEqual(scope["coverage"]["status"], "partial")

    def test_superseded_canonical_input_still_cannot_install_a_bracket(self):
        runtime = self.runtime()
        first = self.canonical_worker(runtime, self.job())
        self.complete(runtime, first, self.sample())
        before = self.state.working_set_clocks.export(self.state.source_meta("codex"))
        second = self.canonical_worker(runtime, self.job(started=13000))
        self.assertIsNotNone(second._clock_provenance)
        self.complete(runtime, second, self.sample(number=12))
        self.assertEqual(self.state.working_set_clocks.export(self.state.source_meta("codex")), before)


if __name__ == "__main__":
    unittest.main()
