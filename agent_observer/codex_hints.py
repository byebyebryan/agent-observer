"""Passive initialized native peer; finite metadata signals, no action RPCs."""

from collections import OrderedDict
import hashlib
import select
import time

from .codex_endpoint import inspect_managed_endpoint, validate_incarnation
from .codex_transport import PassiveClient

METHODS = frozenset({"thread/started", "thread/status/changed", "thread/name/updated"})
MAX_CONTEXTS = 4096


def native_id(value):
    return isinstance(value, str) and 1 <= len(value) <= 256 and all(32 <= ord(c) < 127 for c in value)


class Changes:
    def __init__(self):
        self.seen = OrderedDict()

    def components(self, value):
        if not isinstance(value, dict) or "id" in value or not isinstance(value.get("method"), str) or value["method"] not in METHODS:
            return ()
        method, params = value["method"], value.get("params")
        if not isinstance(params, dict):
            return ()
        if method == "thread/started":
            thread = params.get("thread")
            if not isinstance(thread, dict):
                return ()
            identifier = thread.get("id")
            fingerprint = "started"
        elif method == "thread/status/changed":
            identifier = params.get("threadId")
            status = params.get("status")
            if not isinstance(status, dict) or not isinstance(status.get("type"), str) or status["type"] not in {"active", "idle", "notLoaded", "systemError"}:
                return ()
            flags = status.get("activeFlags", [])
            if not isinstance(flags, list) or len(flags) > 8 or any(not isinstance(f, str) or len(f) > 64 for f in flags):
                return ()
            # Known native wait flags matter even when the status stays active.
            fingerprint = (status["type"], tuple(sorted(f for f in flags if f in {"waitingOnApproval", "waitingOnUserInput"})))
        else:
            identifier = params.get("threadId")
            name = params.get("threadName")
            if name is not None and (not isinstance(name, str) or len(name) > 4096):
                return ()
            fingerprint = hashlib.sha256((name or "").encode()).hexdigest()
        if not native_id(identifier):
            return ()
        key = identifier, method
        unchanged = key in self.seen and self.seen[key] == fingerprint
        self.seen[key] = fingerprint
        self.seen.move_to_end(key)
        while len(self.seen) > MAX_CONTEXTS:
            self.seen.popitem(last=False)
        return () if unchanged else ("runtime", "history")


def run(home, emitter):
    identity = inspect_managed_endpoint(home)
    with PassiveClient.connect(identity.endpoint, expected_uid=identity.uid,
                               expected_pid=identity.pid, timeout=2) as client:
        initialized = client.initialize()
        if not isinstance(initialized, dict) or initialized.get("codexHome") != str(home):
            raise ValueError("endpoint_namespace_mismatch")
        validate_incarnation(identity)
        for component in ("runtime", "history"):
            emitter.hint(component, "source_ready")
        changes = Changes()
        checked = time.monotonic()
        while True:
            emitter.flush()
            now = time.monotonic()
            if now - checked >= 1:
                validate_incarnation(identity)
                checked = now
            if not client.buffer and not select.select([client.connection], [], [], 0.2)[0]:
                continue
            # Bound each burst; unknown methods/content are discarded in memory.
            for _ in range(64):
                for component in changes.components(client.notification()):
                    emitter.hint(component)
                if not client.buffer and not select.select([client.connection], [], [], 0)[0]:
                    break
            emitter.flush()
            time.sleep(0.01)
