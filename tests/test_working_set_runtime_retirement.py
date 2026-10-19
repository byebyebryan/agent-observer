"""Terminal Runtime callbacks must not keep a closed owner alive."""

import gc
import tempfile
import threading
import unittest
import weakref
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

from test_service_state import provider_snapshot

from agent_observer.service_runtime import Runtime
from agent_observer.service_state import ServiceState


@contextmanager
def gc_disabled():
    was_enabled = gc.isenabled()
    gc.disable()
    try:
        yield
    finally:
        if was_enabled:
            gc.enable()


def seeded_state():
    value = provider_snapshot("codex")
    configs = {
        source["provider"]: (source["configHome"], source["configHomeKind"])
        for source in value["sources"]
    }
    state = ServiceState(
        host_scope="fixture",
        configs=configs,
        uid=value["host"]["uid"],
        clock=lambda: 15000,
        working_set_window_ms=259200000,
    )
    state.attempt("codex", "runtime")
    if not state.accept("codex", "runtime", value, sampled_ms=15000, ttl_ms=60000):
        raise AssertionError("synthetic_snapshot_rejected")
    return state


def stop_immediately():
    stop = threading.Event()
    stop.set()
    return stop


class ExternalFactory:
    def spawn(self, _job):
        raise AssertionError("collect_false_called_worker_factory")


class SiblingReservers:
    def reserve_sync(self, _amount):
        return True

    def reserve_working_set(self, _amount):
        return True


class StopAfterSiblingReplacement:
    def __init__(self, state, sibling):
        self.state = state
        self.sibling = sibling
        self.replaced = False

    def is_set(self):
        if not self.replaced:
            self.state.sync_reserver = self.sibling.reserve_sync
            self.state.working_set_reserver = self.sibling.reserve_working_set
            self.replaced = True
        return True


class WorkingSetRuntimeRetirementTests(unittest.TestCase):
    def runtime(self, state, directory, *, worker_factory=None):
        return Runtime(
            state,
            Path(directory) / "read.sock",
            collect=False,
            worker_factory=worker_factory,
        )

    def assert_self_callbacks_retired(self, runtime):
        for name in (
            "worker_factory",
            "_clock_factory",
            "_sync_reserver",
            "_working_set_reserver",
        ):
            callback = getattr(runtime, name)
            if getattr(callback, "__self__", None) is runtime:
                self.fail(f"{name} still points back to terminal Runtime")

    def test_closed_runtime_dies_while_caller_owned_state_buffers_remain(self):
        with gc_disabled(), tempfile.TemporaryDirectory(prefix="ws-runtime-retire-") as directory:
            state = seeded_state()
            runtime = self.runtime(state, directory)
            socket_path = runtime.path
            stop = stop_immediately()
            runtime.run(stop)

            self.assertFalse(socket_path.exists())
            self.assertIsNone(state.sync_reserver)
            self.assertIsNone(state.working_set_reserver)
            self.assertEqual(runtime.peers, set())
            self.assertEqual(runtime.workers, {})
            self.assertEqual(runtime.counts["workerStarts"], 0)
            self.assertEqual(runtime.bodies, {})

            buffer_ids = tuple(id(buffer) for buffer in state.working_set_retained_buffers())
            buffer_lengths = tuple(len(buffer) for buffer in state.working_set_retained_buffers())
            self.assertEqual(len(buffer_lengths), 2)
            self.assertEqual(runtime.encoded_bytes(), sum(buffer_lengths))
            runtime_ref, state_ref = weakref.ref(runtime), weakref.ref(state)

            del runtime
            self.assertIsNone(runtime_ref())
            self.assertIs(state_ref(), state)
            self.assertEqual(
                tuple(id(buffer) for buffer in state.working_set_retained_buffers()),
                buffer_ids,
            )
            self.assertEqual(
                tuple(len(buffer) for buffer in state.working_set_retained_buffers()),
                buffer_lengths,
            )

            del state
            self.assertIsNone(state_ref())

    def test_sibling_reserver_replacements_and_injected_factory_survive_close(self):
        with gc_disabled(), tempfile.TemporaryDirectory(prefix="ws-runtime-sibling-") as directory:
            state = seeded_state()
            sibling = SiblingReservers()
            factory_owner = ExternalFactory()
            injected_factory = factory_owner.spawn
            runtime = self.runtime(state, directory, worker_factory=injected_factory)
            stop = StopAfterSiblingReplacement(state, sibling)
            runtime.run(stop)

            self.assertTrue(stop.replaced)
            self.assertIs(state.sync_reserver.__self__, sibling)
            self.assertIs(state.working_set_reserver.__self__, sibling)
            self.assertIs(runtime.worker_factory, injected_factory)
            self.assertIsNone(runtime._clock_factory)
            self.assertIsNone(runtime._sync_reserver)
            self.assertIsNone(runtime._working_set_reserver)
            runtime_ref = weakref.ref(runtime)

            del runtime
            self.assertIsNone(runtime_ref())
            self.assertIs(state.sync_reserver.__self__, sibling)
            self.assertIs(state.working_set_reserver.__self__, sibling)

    def test_owned_callbacks_retire_even_when_late_cleanup_raises(self):
        with gc_disabled(), tempfile.TemporaryDirectory(prefix="ws-runtime-cleanup-error-") as directory:
            state = seeded_state()
            factory_owner = ExternalFactory()
            injected_factory = factory_owner.spawn
            runtime = self.runtime(state, directory, worker_factory=injected_factory)
            runtime_ref = weakref.ref(runtime)
            with patch.object(runtime.selector, "close", side_effect=RuntimeError("close_probe")):
                with self.assertRaisesRegex(RuntimeError, "close_probe"):
                    runtime.run(stop_immediately())

            self.assertIsNone(state.sync_reserver)
            self.assertIsNone(state.working_set_reserver)
            self.assertIs(runtime.worker_factory, injected_factory)
            self.assertIsNone(runtime._clock_factory)
            self.assertIsNone(runtime._sync_reserver)
            self.assertIsNone(runtime._working_set_reserver)
            runtime.selector.close()

            del runtime
            self.assertIsNone(runtime_ref())

    def test_failed_endpoint_startup_still_retires_runtime_callbacks(self):
        with gc_disabled(), tempfile.TemporaryDirectory(prefix="ws-runtime-endpoint-error-") as directory:
            public_parent = Path(directory) / "public"
            public_parent.mkdir()
            public_parent.chmod(0o755)
            state = seeded_state()
            runtime = Runtime(state, public_parent / "read.sock", collect=False)
            runtime_ref = weakref.ref(runtime)

            with self.assertRaisesRegex(ValueError, "service_socket_directory"):
                runtime.run(stop_immediately())

            self.assertIsNone(state.sync_reserver)
            self.assertIsNone(state.working_set_reserver)
            self.assert_self_callbacks_retired(runtime)
            del runtime
            self.assertIsNone(runtime_ref())


if __name__ == "__main__":
    unittest.main()
