from __future__ import annotations

from contextlib import contextmanager
from typing import Callable, Iterator


EXCLUSION_LABELS = (
    "fixture_sample_copy",
    "full_oracle_construction",
    "post_read_hash_checks",
    "native_reconstruction_crosschecks",
    "report_only_records",
)


class TrialCpuExclusions:
    """Subtract main-thread CPU only for named harness-only blocks."""

    def __init__(
        self,
        *,
        process_clock_ns: Callable[[], int],
        thread_clock_ns: Callable[[], int],
        thread_id: Callable[[], int],
    ) -> None:
        self._process_clock_ns = process_clock_ns
        self._thread_clock_ns = thread_clock_ns
        self._thread_id = thread_id
        self._owner_thread_id = thread_id()
        self._window_active = False
        self._window_process_start_ns: int | None = None
        self._window_process_end_ns: int | None = None
        self._depth = 0
        self._outer_label: str | None = None
        self._outer_thread_start_ns: int | None = None
        self._excluded_ns = {label: 0 for label in EXCLUSION_LABELS}
        self._block_counts = {label: 0 for label in EXCLUSION_LABELS}

    def _assert_owner_thread(self) -> None:
        if self._thread_id() != self._owner_thread_id:
            raise RuntimeError("cpu_exclusion_thread_mismatch")

    @property
    def window_active(self) -> bool:
        return self._window_active

    def start_window(self) -> None:
        self._assert_owner_thread()
        if self._window_active or self._depth:
            raise RuntimeError("cpu_window_already_active")
        self._window_process_start_ns = self._process_clock_ns()
        self._window_process_end_ns = None
        self._window_active = True

    @contextmanager
    def exclude(self, label: str) -> Iterator[None]:
        self._assert_owner_thread()
        if label not in self._excluded_ns:
            raise ValueError("cpu_exclusion_label_unknown")
        if not self._window_active:
            yield
            return

        if self._depth:
            # Nested harness bookkeeping stays owned by the outer label. It is
            # counted once and cannot double-subtract an overlapping interval.
            self._depth += 1
            try:
                yield
            finally:
                self._assert_owner_thread()
                self._depth -= 1
            return

        self._depth = 1
        self._outer_label = label
        self._outer_thread_start_ns = self._thread_clock_ns()
        try:
            yield
        finally:
            self._assert_owner_thread()
            end_ns = self._thread_clock_ns()
            start_ns = self._outer_thread_start_ns
            outer_label = self._outer_label
            if (start_ns is None or outer_label is None or end_ns < start_ns):
                raise RuntimeError("cpu_exclusion_clock_invalid")
            self._excluded_ns[outer_label] += end_ns - start_ns
            self._block_counts[outer_label] += 1
            self._depth = 0
            self._outer_label = None
            self._outer_thread_start_ns = None

    def stop_window(self) -> dict[str, object]:
        self._assert_owner_thread()
        if not self._window_active:
            raise RuntimeError("cpu_window_not_active")
        if self._depth:
            raise RuntimeError("cpu_exclusion_block_open")
        end_ns = self._process_clock_ns()
        start_ns = self._window_process_start_ns
        if start_ns is None or end_ns < start_ns:
            raise RuntimeError("cpu_window_clock_invalid")
        self._window_process_end_ns = end_ns
        self._window_active = False
        raw_ns = end_ns - start_ns
        excluded_ns = sum(self._excluded_ns.values())
        adjusted_ns = raw_ns - excluded_ns
        if adjusted_ns < 0:
            raise RuntimeError("cpu_exclusions_exceed_raw_process_cpu")
        return {
            "clock": "time.process_time_ns with named main-thread time.thread_time_ns exclusions",
            "windowStartThreadId": self._owner_thread_id,
            "rawProcessCpuNs": raw_ns,
            "excludedMainThreadCpuNsByLabel": dict(self._excluded_ns),
            "excludedBlockCountsByLabel": dict(self._block_counts),
            "excludedMainThreadCpuNs": excluded_ns,
            "adjustedProcessCpuNs": adjusted_ns,
            "otherThreadCpuDuringExclusionsIncluded": True,
            "exclusionNestedIntervalsCountedOnce": True,
        }

    def run_excluded(self, label: str, function: Callable, *args, **kwargs):
        with self.exclude(label):
            return function(*args, **kwargs)


def full_consumer_filter(reference, sessions):
    """Required consumer filtering stays in the measured product path."""
    return reference.full_consumer_rows({"sessions": sessions})
