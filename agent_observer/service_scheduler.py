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
        self.active = {}
        self.generation = {p: 0 for p in providers}
        self.dirty = {(p, c): 0 for p in providers for c in self.intervals}
        self.due = {key: 0 for key in self.dirty}
        self.last = {key: -debounce_ms for key in self.dirty}
        self.failures = {key: 0 for key in self.dirty}

    def hint(self, provider, component, now):
        key = provider, component
        self.dirty[key] += 1
        self.due[key] = min(self.due[key], max(now, self.last[key] + self.debounce))

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
            jobs.append(job)
        return jobs

    def finish(self, job, now, *, success):
        if self.active.get(job.provider) != job:
            return False
        del self.active[job.provider]
        key = job.provider, job.component
        self.failures[key] = 0 if success else min(6, self.failures[key] + 1)
        interval = self.intervals[job.component] * max(1, 2 ** self.failures[key])
        self.due[key] = now + min(interval, 300000)
        if self.dirty[key] != job.dirty:
            self.due[key] = max(now, self.last[key] + self.debounce)
        return job.generation == self.generation[job.provider]

    def expired(self, now):
        return [job for job in self.active.values() if now >= job.deadline]
