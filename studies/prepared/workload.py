"""Synthetic Agent publications with original receipts; no provider access."""

import copy
import sys
import tempfile
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tests"))
from mesh_native_fixture import CachedPublisher  # noqa: E402
from mesh_plus.api import Bridge, Client, Endpoint, Reader  # noqa: E402
from mesh_plus.evidence import digest  # noqa: E402
from mesh_plus.transport import IPCServer, connect_ipc  # noqa: E402

from agent_observer.mesh_profile import AgentProfile  # noqa: E402

REQUEST = "a" * 32


async def seed(hosts, rows):
    profile = AgentProfile()
    with tempfile.TemporaryDirectory(prefix="agent-prepared-shape-") as directory:
        servers, endpoints = [], []
        try:
            for index in range(hosts):
                host = "fixture" + str(index)
                publisher = CachedPublisher(host)
                frame = publisher.frame
                frame["sources"] = [s for s in frame["sources"] if s["provider"] == "codex"]
                snapshot = frame["snapshot"]
                snapshot["sources"] = [s for s in snapshot["sources"] if s["provider"] == "codex"]
                templates = [r for r in snapshot["sessions"] if r["identity"]["provider"] == "codex"]
                snapshot["sessions"] = []
                for number in range(rows):
                    row = copy.deepcopy(templates[number % len(templates)])
                    identifier = str(uuid.UUID(int=number + 1))
                    row["identity"]["nativeId"] = identifier
                    row["nativeIds"] = {"threadId": identifier, "sessionTreeRootId": identifier}
                    row["title"] = "fixture-" + str(number)
                    row["hasSavedHistory"] = True
                    row["kind"] = "user"
                    if number >= max(1, 8 // hosts):
                        row["runtime"]["value"] = "parked"
                        row["phase"] = None
                        row["blockedReasons"] = []
                    snapshot["sessions"].append(row)
                publisher.codec.inspect_native(frame)
                socket = Path(directory) / (host + ".sock")
                server = await IPCServer(socket, Bridge(publisher).serve).start()
                servers.append(server)
                codec = profile.bind(host, "agent")

                async def connect(path=socket, name=host, binding=codec):
                    return await Client.connect(await connect_ipc(path), host=name, source="agent",
                                                profile=profile.descriptor.profile_id, codec=binding.validate_bridge)

                endpoints.append(Endpoint(host, index == 0, None if index == 0 else "sha256:" + "a" * 64,
                                          connect, codec))
            reader = Reader("agent", endpoints, local_host="fixture0", profile=profile,
                            catalog_revision="sha256:" + "b" * 64)
            response = await reader.snapshot(request_id=REQUEST)
            if any(h["owner"] is None for h in response["mesh"]["hosts"]):
                raise ValueError("fixture_native_admission_failed")
            if reader.inspect()["activeConnections"]:
                raise ValueError("fixture_cleanup")
            response["mesh"]["operation"] = "watch"
            return response
        finally:
            for server in servers:
                await server.close()


def publications(original, count, change):
    frames = []
    for index in range(count):
        frame = copy.deepcopy(original)
        frame["mesh"]["reader"].update(sequence=index + 1, revision=index + 1)
        if change == "native":
            for row in frame["sessions"]:
                row["title"] += "-v" + str(index)
                if row["runtime"]["value"] == "running":
                    phase = ("working", "waiting", "blocked")[index % 3]
                    row["phase"]["value"] = phase
                    row["blockedReasons"] = ["approval"] if phase == "blocked" else []
            for host in frame["mesh"]["hosts"]:
                host["owner"]["service"]["sequence"] += index
                host["owner"]["service"]["viewRevision"] += index
                proof = host["delivery"]["proof"]
                if proof is not None:
                    rows = [r for r in frame["sessions"] if r["identity"]["hostScope"] == host["hostId"]]
                    native = AgentProfile().restore_native(host["owner"], rows)
                    proof["payloadDigest"] = digest(native)
        frames.append(frame)
    return frames


def selected(rows):
    return [(r["identity"]["hostScope"], r["identity"]["nativeId"], r["title"], r["runtime"]["value"],
             r["kind"], r["phase"]["value"] if r["phase"] else None)
            for r in rows if r["runtime"]["value"] == "running"]
