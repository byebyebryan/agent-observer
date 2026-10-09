"""Owned passive feed helper; emits only a finite private scheduling signal."""

import ctypes
import os
from pathlib import Path
import signal
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


class Emitter:
    def __init__(self, epoch):
        self.epoch = epoch
        self.pending = {}
        self.last = -1
        os.set_blocking(sys.stdout.fileno(), False)

    def hint(self, component, reason="native_event"):
        from agent_observer.service_hints import REASONS
        if component not in {"runtime", "history"} or reason not in REASONS:
            raise ValueError("service_hint_message")
        self.pending[component] = reason

    def flush(self):
        from agent_observer.service_hints import message
        now = time.monotonic()
        if now - self.last < 0.2:
            return
        for component, reason in list(self.pending.items()):
            data = message(self.epoch, component, reason)
            try:
                written = os.write(sys.stdout.fileno(), data)
            except BlockingIOError:
                return
            if written != len(data):
                raise ValueError("service_hint_pipe")
            del self.pending[component]
        self.last = now


def main():
    from agent_observer.bounded_json import decode_document
    from agent_observer.adapters import adapter_for
    signal.signal(signal.SIGALRM, lambda *_args: os._exit(2))
    signal.setitimer(signal.ITIMER_REAL, 2)
    request = decode_document(sys.stdin.buffer.read(4097), max_bytes=4096)
    if not isinstance(request, dict) or set(request) != {"provider", "configHome", "epoch", "parentPid"}:
        raise ValueError("service_hint_request")
    if request["provider"] not in {"codex", "claude"} or not isinstance(request["epoch"], str) or len(request["epoch"]) != 36:
        raise ValueError("service_hint_request")
    adapter = adapter_for(request["provider"])
    home = Path(request["configHome"])
    if not home.is_absolute() or os.getpgrp() != os.getpid() or os.getsid(0) != os.getpid():
        raise ValueError("service_hint_ownership")
    # No nested native launcher is used. The feed must also die when a killed
    # publisher cannot execute its normal owned-helper shutdown.
    if type(request["parentPid"]) is not int or request["parentPid"] != os.getppid():
        raise ValueError("service_hint_parent")
    if ctypes.CDLL(None, use_errno=True).prctl(1, signal.SIGKILL, 0, 0, 0) != 0 or request["parentPid"] != os.getppid():
        raise ValueError("service_hint_parent")
    signal.setitimer(signal.ITIMER_REAL, 0)
    emitter = Emitter(request["epoch"])
    adapter.listen(home, emitter)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        raise SystemExit(2) from None
