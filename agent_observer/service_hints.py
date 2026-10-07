"""Private bounded hint port; wakeups never supply observations or renew leases."""

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import uuid

from .bounded_json import decode_document
from .contract import canonical

MAX_LINE = 512
MAX_BUFFER = 2048
REASONS = frozenset({"native_event", "source_ready", "source_lost", "watch_rearmed"})


def message(epoch, component, reason):
    return (canonical({"epoch": epoch, "component": component, "reason": reason}) + "\n").encode()


def parse_message(data, epoch):
    value = decode_document(data, max_bytes=MAX_LINE)
    if not isinstance(value, dict) or set(value) != {"epoch", "component", "reason"}:
        raise ValueError("service_hint_message")
    if any(not isinstance(v, str) for v in value.values()):
        raise ValueError("service_hint_message")
    if value["epoch"] != epoch:
        raise ValueError("service_hint_epoch")
    if value["component"] not in {"runtime", "history"} or value["reason"] not in REASONS:
        raise ValueError("service_hint_message")
    return value


@dataclass
class Source:
    provider: str
    epoch: str
    process: object
    buffer: bytearray = field(default_factory=bytearray)


class Hints:
    def __init__(self, configs, selector, scheduler, stop_process, *, factory=None, diagnostics=None):
        self.configs, self.selector, self.scheduler = configs, selector, scheduler
        self.stop_process = stop_process
        self.factory = factory or self._spawn
        self.sources = {}
        self.due = {p: 0 for p in configs}
        self.failures = {p: 0 for p in configs}
        self.counts = {p: {"starts": 0, "runtime": 0, "history": 0, "losses": 0,
                           "rejected": 0, "ready": False,
                           "lastRuntimeHintBoottimeMs": None,
                           "lastHistoryHintBoottimeMs": None} for p in configs}
        self.diagnostics = Path(diagnostics) if diagnostics else None
        self.last_diagnostic = -1000
        self.changed = True
        self.diagnostic_parent = None
        if self.diagnostics:
            path = self.diagnostics
            if not path.is_absolute() or path.parent.resolve() != path.parent:
                raise ValueError("service_hint_diagnostics_scope")
            info = path.parent.stat()
            if info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o700:
                raise ValueError("service_hint_diagnostics_scope")
            self.diagnostic_parent = info.st_dev, info.st_ino
            if path.exists() or path.is_symlink():
                info = path.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
                    raise ValueError("service_hint_diagnostics_scope")

    def _increment(self, provider, key):
        self.counts[provider][key] = min(1_000_000_000, self.counts[provider][key] + 1)
        self.changed = True

    @staticmethod
    def _spawn(provider, config, epoch):
        payload = {"provider": provider, "configHome": config[0], "epoch": epoch,
                   "parentPid": os.getpid()}
        process = subprocess.Popen(
            [sys.executable, "-I", "-B", str(Path(__file__).with_name("_hint_worker.py"))],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            process.stdin.write((canonical(payload) + "\n").encode())
            process.stdin.close()
        except BaseException:
            process.kill()
            process.wait(timeout=2)
            process.stdout.close()
            raise
        return process

    def tick(self, now):
        for provider in self.configs:
            if provider in self.sources or now < self.due[provider]:
                continue
            process = None
            try:
                epoch = str(uuid.uuid4())
                process = self.factory(provider, self.configs[provider], epoch)
                os.set_blocking(process.stdout.fileno(), False)
                source = Source(provider, epoch, process)
                self.selector.register(process.stdout, 1, ("hint", source))
                self.sources[provider] = source
                self._increment(provider, "starts")
            except (ValueError, OSError):
                if process is not None:
                    self.stop_process(process)
                    process.stdout.close()
                self._lost(provider, now)
        self._diagnostic(now)

    def _lost(self, provider, now):
        reconcile = self.counts[provider]["ready"]
        self._increment(provider, "losses")
        self.counts[provider]["ready"] = False
        self.failures[provider] = min(4, self.failures[provider] + 1)
        self.due[provider] = now + min(60000, 5000 * 2 ** (self.failures[provider] - 1))
        # Feed loss is a budgeted wakeup, never contrary presence evidence.
        if reconcile:
            for component in ("runtime", "history"):
                self.scheduler.hint(provider, component, now)

    def drop(self, source, now, *, rejected=False):
        if self.sources.get(source.provider) is not source:
            return
        self.selector.unregister(source.process.stdout)
        self.stop_process(source.process)
        source.process.stdout.close()
        del self.sources[source.provider]
        if rejected:
            self._increment(source.provider, "rejected")
        self._lost(source.provider, now)

    def read(self, source, now):
        if self.sources.get(source.provider) is not source:
            return
        data = os.read(source.process.stdout.fileno(), MAX_BUFFER - len(source.buffer))
        if not data:
            self.drop(source, now)
            return
        source.buffer.extend(data)
        try:
            if len(source.buffer) > MAX_BUFFER:
                raise ValueError("service_hint_limit")
            pending = set()
            while b"\n" in source.buffer:
                raw, _, tail = source.buffer.partition(b"\n")
                source.buffer[:] = tail
                value = parse_message(bytes(raw), source.epoch)
                if value["reason"] == "source_lost":
                    self.drop(source, now)
                    return
                if value["reason"] == "source_ready":
                    self.counts[source.provider]["ready"] = True
                    self.failures[source.provider] = 0
                    self.changed = True
                pending.add(value["component"])
            if len(source.buffer) > MAX_LINE:
                raise ValueError("service_hint_limit")
            for component in pending:
                self.scheduler.hint(source.provider, component, now)
                self._increment(source.provider, component)
                self.counts[source.provider]["last" + component.title() + "HintBoottimeMs"] = now
        except (ValueError, TypeError, OSError):
            self.drop(source, now, rejected=True)

    def _diagnostic(self, now):
        if not self.diagnostics or not self.changed or now - self.last_diagnostic < 1000:
            return
        # Bounded operator diagnostics stay outside strict public frames. A
        # replaced/foreign path is never followed or overwritten.
        path = self.diagnostics
        try:
            parent = path.parent.lstat()
            if (not stat.S_ISDIR(parent.st_mode) or (parent.st_dev, parent.st_ino) != self.diagnostic_parent
                    or parent.st_uid != os.geteuid() or stat.S_IMODE(parent.st_mode) != 0o700):
                raise ValueError("service_hint_diagnostics_scope")
            if path.exists() or path.is_symlink():
                info = path.lstat()
                if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or stat.S_IMODE(info.st_mode) != 0o600:
                    raise ValueError("service_hint_diagnostics_scope")
            with tempfile.TemporaryDirectory(prefix=".hints-", dir=path.parent) as directory:
                temporary = Path(directory) / "diagnostic"
                temporary.write_text(json.dumps({"diagnosticVersion": 1, "providers": self.counts}) + "\n")
                temporary.chmod(0o600)
                os.replace(temporary, path)
        except (ValueError, OSError):
            # Losing optional diagnostics cannot take collection/IPC down.
            self.diagnostics = None
            return
        self.changed = False
        self.last_diagnostic = now

    def close(self):
        for source in list(self.sources.values()):
            self.selector.unregister(source.process.stdout)
            self.stop_process(source.process)
            source.process.stdout.close()
        self.sources.clear()
