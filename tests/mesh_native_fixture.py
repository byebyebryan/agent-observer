"""Owned cached-native scenarios for optional SDK tests; no provider collection."""

import asyncio
import copy
import json
import os
from pathlib import Path

from mesh_plus.api import Publication
from mesh_plus.evidence import clock_domain, digest
from mesh_plus.transport import boottime_ms

from agent_observer.mesh_profile import AgentProfile
from agent_observer.public import store_namespace
from agent_observer.service_public import validate_frame


def native_frame(host="fixture"):
    path = Path(__file__).parent / "fixtures/service-v4/view.json"
    frame = json.loads(path.read_text())
    clock = clock_domain()
    shift = boottime_ms() - 100 - frame["emittedBoottimeMs"]
    frame.update(hostScope=host, uid=os.getuid(), bootId=clock["bootId"],
                 clockDomain="time:[" + clock["timeNamespace"].split(":")[1] + "]",
                 emittedBoottimeMs=frame["emittedBoottimeMs"] + shift)
    namespaces = {}
    for source in frame["sources"]:
        source["namespace"] = store_namespace(source["provider"], source["configHome"],
                                              source["configHomeKind"], os.getuid())
        namespaces[source["provider"]] = source["namespace"]
        for component in source["components"]:
            for key in ("sampledBoottimeMs", "expiresBoottimeMs", "lastAttemptBoottimeMs"):
                if type(component.get(key)) is int:
                    component[key] += shift
            component["expiresBoottimeMs"] = frame["emittedBoottimeMs"] + 30000
    snapshot = frame["snapshot"]
    snapshot["host"].update(authority=host, uid=os.getuid())
    for source in snapshot["sources"]:
        source["namespace"] = namespaces[source["provider"]]
    for row in snapshot["sessions"]:
        row["identity"].update(hostScope=host, namespace=namespaces[row["identity"]["provider"]])
    return validate_frame(frame)


class CachedPublisher:
    capabilities = ("snapshot", "proof", "subscribe")

    def __init__(self, host="fixture"):
        self.host, self.source = host, "agent"
        self.state_profile = AgentProfile()
        self.profile = self.state_profile.descriptor.profile_id
        self.codec = self.state_profile.bind(host, self.source)
        self.validate = self.codec.validate_bridge
        self.frame = native_frame(host)
        self.bridge_id = "00000000-0000-0000-0000-000000000099"
        self.sequence, self.watchers, self.proof_reads = 0, 0, 0
        self.alter = None
        self.wait_snapshot = None
        self.snapshot_started = asyncio.Event()
        self.changes = asyncio.Queue()

    def wrap(self, nonce=None):
        self.sequence += 1
        state = self.codec.inspect_native(self.frame)
        now = boottime_ms()
        remaining = []
        if nonce is not None:
            remaining = [{"sourceId": r["sourceId"], "component": r["component"],
                          "accepted": r["accepted"], "health": r["health"],
                          "remainingMs": max(0, r["expiry"] - now) if r["health"] in {"current", "partial"} else 0}
                         for r in state.receipts]
        result = {"meshProtocol": 1, "kind": "proof" if nonce else "candidate", "nonce": nonce,
                  "bridgeId": self.bridge_id, "sequence": self.sequence, "sourceId": self.source,
                  "hostId": self.host, "clock": state.clock, "encodedAtMs": now,
                  "ownerFrame": copy.deepcopy(self.frame), "ownerDigest": digest(self.frame),
                  "remaining": remaining, "error": None}
        if self.alter is not None:
            self.alter(result)
        return result

    async def snapshot(self, parameters):
        assert parameters == {}
        self.snapshot_started.set()
        if self.wait_snapshot is not None:
            await self.wait_snapshot.wait()
        return self.wrap()

    async def proof(self, parameters):
        self.proof_reads += 1
        return self.wrap(parameters["nonce"])

    async def watch(self):
        self.watchers += 1
        try:
            while True:
                yield Publication(self.wrap(), self.frame["serviceId"], {"viewRevision": self.frame["viewRevision"]})
                await self.changes.get()
        finally:
            self.watchers -= 1
