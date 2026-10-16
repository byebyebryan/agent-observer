"""Optional prepared watch; retained source context is separate from authority.

No I/O, timers, reconnection or display policy. Callers serialize methods and
disconnect on EOF, framing/liveness failure, cancellation or output failure.
"""

import copy
from dataclasses import dataclass

from mesh_plus import api as mesh_api
from mesh_plus.api import PreparedReadGuard
from mesh_plus.protocol import check

from .mesh_preparation import AgentPreparation
from .mesh_profile import AgentProfile
from .mesh_selection import AgentClassifier, AgentRecordSummary, AgentSelection

READ_INTERFACE_VERSION = 2


@dataclass(frozen=True)
class AgentWatchRead:
    context: dict | None
    sessions: list
    summaries: tuple[AgentRecordSummary, ...] | None = None


class PreparedAgentWatch:
    def __init__(self, request_id, *, host_ids=None, profile=None, preparation=None, selection=None):
        check(getattr(mesh_api, "ADMISSION_INTERFACE_VERSION", None) == 1
              and getattr(mesh_api, "SELECTION_INTERFACE_VERSION", None) == 1
              and callable(getattr(PreparedReadGuard, "context", None)), "mesh_prepared_read_incompatible")
        check(selection is None or type(selection) is AgentSelection, "agent_selection")
        profile = AgentProfile() if profile is None else profile
        preparation = AgentPreparation(profile) if preparation is None else preparation
        self._guard = PreparedReadGuard("agent", request_id, host_ids=host_ids,
                                        profile=profile, preparation=preparation)
        self._selection = None if selection is None else self._guard.select(AgentClassifier(selection))
        self._context = None

    def accept(self, frame):
        try:
            self._guard.accept(frame)
            # Owned admitted replacements are opaque SDK values; controls keep
            # their ordinary JSON shape. Context exports never decode row bodies.
            if not isinstance(frame, dict) or frame.get("mesh", {}).get("kind") != "heartbeat":
                snapshot = self._guard.context()
                self._context = None if snapshot is None else snapshot["mesh"]
        except BaseException:
            self.disconnect()
            raise
        return frame

    def read(self, now_ms, clock):
        try:
            summaries = None
            if self._selection is None:
                rows = self._guard.current(now_ms, clock)
            else:
                rows, raw = self._selection.current(now_ms, clock)
                summaries = tuple(AgentRecordSummary(tuple(s["identity"]), s["kind"],
                                                    s["runtimeValue"], s["runtimeHealth"]) for s in raw)
            return AgentWatchRead(copy.deepcopy(self._context), rows, summaries)
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
