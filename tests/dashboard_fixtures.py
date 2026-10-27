"""Owned cached-service fixtures for dashboard qualification, never native providers.

Run in a separate process so consumer measurements exclude these producers.
Only invented labels and paths are emitted. The long synthetic leases exercise
consumer lifetime/resource ownership, not native classification accuracy.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import json
import math
import os
import signal
import sys
import time
from contextlib import ExitStack
from pathlib import Path
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_service_runtime import Running, scoped_snapshot

from agent_observer.service_state import ServiceState


def _write_json_atomic(path: Path, value: dict) -> None:
    staging = path.with_suffix(path.suffix + ".tmp")
    staging.write_text(json.dumps(value) + "\n", encoding="utf-8")
    staging.chmod(0o600)
    staging.replace(path)


def fixture_state(host: str, count: int, *, ttl_ms=36_000_000):
    """Create one initial admitted synthetic runtime census and fixed activity."""
    state = ServiceState(
        host_scope=host,
        configs={"codex": ("/fixture/codex", "explicit")},
        uid=os.geteuid(),
        working_set_window_ms=0,
    )
    sample = scoped_snapshot()
    sample["host"]["authority"] = host
    sample["collectedAt"] = int(time.time() * 1000)
    sample["sources"][0]["capabilities"]["activity"] = True
    template = sample["sessions"][0]
    sample["sessions"] = []
    for index in range(count):
        value = copy.deepcopy(template)
        native_id = str(UUID(int=50_000 + index))
        value["identity"].update(hostScope=host, nativeId=native_id)
        value["nativeIds"].update(threadId=native_id, sessionTreeRootId=native_id)
        value["title"] = f"Fixture session {index + 1}"
        value["activity"].update(
            at=sample["collectedAt"] - 1000,
            health="current",
            source="codex_rpc",
            reason="native_timestamp",
        )
        sample["sessions"].append(value)
    sampled = state.clock()
    state.attempt("codex", "runtime")
    assert state.accept(
        "codex",
        "runtime",
        sample,
        sampled_ms=sampled,
        ttl_ms=ttl_ms,
        runtime_ttl_ms=ttl_ms,
        accepted_boottime_ms=state.clock(),
    )
    return state, sample


async def serve(directory: Path, *, sources=3, count=100, outage_after=None, outage_duration=0):
    from mesh_plus.api import Bridge
    from mesh_plus.transport import IPCServer

    from agent_observer.mesh_working_set_publisher import make_working_set_publisher

    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    assert directory.stat().st_uid == os.getuid() and directory.stat().st_mode & 0o077 == 0
    stops = asyncio.Event()
    loop = asyncio.get_running_loop()
    for signum in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(signum, stops.set)
    servers, declarations, live_channels, handlers = [], [], [], []
    outage_task = None

    def tracked_handler(publisher, channels):
        async def handle(channel):
            channels.add(channel)
            try:
                await Bridge(publisher).serve(channel)
            finally:
                channels.discard(channel)

        return handle

    with ExitStack() as stack:
        try:
            for index in range(sources):
                host = f"fixture-{index + 1}"
                state, sample = fixture_state(host, count)
                native = stack.enter_context(Running(state=state))
                source_id = "agent_working_set"
                socket = directory / f"mesh-{index + 1}.sock"
                publisher = make_working_set_publisher(host, source_id, native.path, window_ms=0)
                channels = set()
                handler = tracked_handler(publisher, channels)
                server = await IPCServer(socket, handler).start()
                servers.append(server)
                live_channels.append(channels)
                handlers.append(handler)
                declarations.append(
                    {
                        "id": host,
                        "host": host,
                        "home": "default",
                        "label": "Default",
                        "mesh_source": source_id,
                        "scope": "local",
                        "socket": str(socket),
                        "namespace": sample["sources"][0]["namespace"],
                        "window_hours": 0,
                        "max_identities": max(1024, count),
                        "max_payload_mib": 4,
                    }
                )
            lines = [
                "version = 1",
                "default_sources = " + json.dumps([s["id"] for s in declarations]),
            ]
            for source in declarations:
                lines.extend(["", "[[sources]]"])
                lines.extend(f"{key} = {json.dumps(value)}" for key, value in source.items())
            config = directory / "terminal.toml"
            config.write_text("\n".join(lines) + "\n")
            config.chmod(0o600)
            ready = {
                "pid": os.getpid(),
                "sources": sources,
                "identitiesPerSource": count,
                "config": str(config),
                "synthetic": True,
                "nativeProviderCalls": 0,
                "fixtureStartedAtMonotonic": time.monotonic(),
                "outageConfigured": outage_after is not None,
                "outageAfterSeconds": outage_after,
                "outageDurationSeconds": outage_duration if outage_after is not None else None,
            }
            _write_json_atomic(directory / "ready.json", ready)
            print(json.dumps(ready), flush=True)

            async def outage():
                await asyncio.sleep(outage_after)
                outage_started_at = time.monotonic()
                proof = {
                    "source": declarations[0]["id"],
                    "stage": "unavailable",
                    "outageStartedAtMonotonic": outage_started_at,
                    "listenerRestoredAtMonotonic": None,
                }
                _write_json_atomic(directory / "outage.json", proof)
                await asyncio.gather(*(c.close() for c in tuple(live_channels[0])))
                await servers[0].close()
                await asyncio.sleep(outage_duration)
                servers[0] = await IPCServer(directory / "mesh-1.sock", handlers[0]).start()
                proof["stage"] = "listener-restored"
                proof["listenerRestoredAtMonotonic"] = time.monotonic()
                _write_json_atomic(directory / "outage.json", proof)

            if outage_after is not None:
                outage_task = asyncio.create_task(outage())
            await stops.wait()
        finally:
            if outage_task is not None:
                outage_task.cancel()
                await asyncio.gather(outage_task, return_exceptions=True)
            await asyncio.gather(
                *(c.close() for channels in live_channels for c in tuple(channels))
            )
            await asyncio.gather(*(server.close() for server in servers))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    parser.add_argument("--sources", type=int, default=3, choices=range(1, 9))
    parser.add_argument("--count", type=int, default=100, choices=range(0, 4097))
    parser.add_argument(
        "--outage-after", type=float, help="drop only fixture-1 after this many seconds"
    )
    parser.add_argument(
        "--outage-duration", type=float, default=600, help="owned fixture listener outage duration"
    )
    args = parser.parse_args()
    if args.outage_after is not None and (
        not math.isfinite(args.outage_after)
        or not math.isfinite(args.outage_duration)
        or args.outage_after < 0
        or args.outage_duration <= 0
    ):
        parser.error("use a nonnegative outage start and positive duration")
    asyncio.run(
        serve(
            args.directory,
            sources=args.sources,
            count=args.count,
            outage_after=args.outage_after,
            outage_duration=args.outage_duration,
        )
    )
