"""Optional prepared watch; retained source context is separate from authority.

No I/O, timers, reconnection or display policy. Callers serialize methods and
disconnect on EOF, framing/liveness failure, cancellation or output failure.
"""

import copy
from dataclasses import dataclass

from mesh_plus.api import PreparedReadGuard

from .mesh_preparation import AgentPreparation
from .mesh_profile import AgentProfile

READ_INTERFACE_VERSION = 1


@dataclass(frozen=True)
class AgentWatchRead:
    context: dict | None
    sessions: list


class PreparedAgentWatch:
    def __init__(self, request_id, *, host_ids=None, profile=None, preparation=None):
        profile = AgentProfile() if profile is None else profile
        preparation = AgentPreparation(profile) if preparation is None else preparation
        self._guard = PreparedReadGuard("agent", request_id, host_ids=host_ids,
                                        profile=profile, preparation=preparation)
        self._context = None

    def accept(self, frame):
        try:
            self._guard.accept(frame)
            if "mesh" not in frame or frame["mesh"]["kind"] in {"gap", "error"}:
                self._context = None
            elif frame["mesh"]["kind"] != "heartbeat":
                snapshot = self._guard.snapshot()
                self._context = None if snapshot is None else snapshot["mesh"]
        except BaseException:
            self.disconnect()
            raise
        return frame

    def read(self, now_ms, clock):
        try:
            rows = self._guard.current(now_ms, clock)
            return AgentWatchRead(copy.deepcopy(self._context), rows)
        except BaseException:
            self.disconnect()
            raise

    def snapshot(self):
        try:
            return self._guard.snapshot()
        except BaseException:
            self.disconnect()
            raise

    def disconnect(self):
        self._context = None
        self._guard.disconnect()
