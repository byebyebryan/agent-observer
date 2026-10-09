"""Deterministic fair jobs, source generations and debounce; no provider imports."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Job:
    provider: str
    component: str
    started: int
    deadline: int
    generation: int
    dirty: int


class Scheduler:
    def __init__(self, providers, *, intervals=None, timeout_ms=10000, debounce_ms=500):
        self.intervals = intervals or {"runtime": 2000, "history": 60000}
        if set(self.intervals) != {"runtime", "history"} or any(type(v) is not int or not 1000 <= v <= 3600000 for v in self.intervals.values()) or not 1000 <= timeout_ms <= 30000:
            raise ValueError("service_schedule_invalid")
        self.timeout = timeout_ms
        self.debounce = debounce_ms
        self.minimum_gap = {"runtime": max(1000, debounce_ms), "history": max(10000, debounce_ms)}
        self.active = {}
        self.generation = {p: 0 for p in providers}
        self.dirty = {(p, c): 0 for p in providers for c in self.intervals}
        self.hint_due = {key: None for key in self.dirty}
        self.due = {key: 0 for key in self.dirty}
        self.last = {key: -self.minimum_gap[key[1]] for key in self.dirty}
        self.failures = {key: 0 for key in self.dirty}
        self.retry_not_before = {key: 0 for key in self.dirty}

    def hint(self, provider, component, now):
        key = provider, component
        if key not in self.dirty:
            raise ValueError("service_hint_scope")
        # A bit, not a count: a burst owns one trailing read per component.
        self.dirty[key] = 1
        # Anchor the settling window to the first unconsumed hint. Subsequent
        # hints cannot postpone reconciliation indefinitely, and a periodic
        # read which is already due remains entitled to run sooner.
        if self.hint_due[key] is None:
            self.hint_due[key] = now + self.debounce
        self.due[key] = min(self.due[key], max(self.hint_due[key], self.last[key] + self.minimum_gap[component],
                                              self.retry_not_before[key]))

    def invalidate(self, provider):
        self.generation[provider] += 1

    def start_due(self, now):
        jobs = []
        for provider in self.generation:
            if provider in self.active:
                continue
            candidates = [(due, component) for (p, component), due in self.due.items() if p == provider and due <= now]
            if not candidates:
                continue
            _, component = min(candidates, key=lambda x: (x[0], x[1] != "runtime"))
            key = provider, component
            job = Job(provider, component, now, now + self.timeout, self.generation[provider], self.dirty[key])
            self.active[provider] = job
            self.last[key] = now
            self.dirty[key] = 0
            self.hint_due[key] = None
            jobs.append(job)
        return jobs

    def finish(self, job, now, *, success):
        if self.active.get(job.provider) != job:
            return False
        del self.active[job.provider]
        key = job.provider, job.component
        self.failures[key] = 0 if success else min(6, self.failures[key] + 1)
        base_interval = self.intervals[job.component]
        interval = base_interval * max(1, 2 ** self.failures[key])
        # Cap additional retry backoff, never a caller's slower base cadence.
        self.due[key] = now + max(base_interval, min(interval, 300000))
        self.retry_not_before[key] = 0 if success else self.due[key]
        if success and self.dirty[key]:
            self.due[key] = max(now, self.hint_due[key], self.last[key] + self.minimum_gap[job.component])
        return job.generation == self.generation[job.provider]

    def expired(self, now):
        return [job for job in self.active.values() if now >= job.deadline]
