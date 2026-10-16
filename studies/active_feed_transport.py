#!/usr/bin/env python3
"""Installed active-feed lifecycle qualification over owned local IPC.

The explicit Service 4 fixture is synthetic input to public ServiceState APIs.
Collection is disabled. This script never adds a checkout to sys.path, imports
tests, changes normal selections, or invokes a provider. --development labels an
explicit source screen; omit it only with separately installed exact wheels.
Fixed SSH has its own Mesh qualification harness and is not exercised here.
"""

from __future__ import annotations

import argparse
import asyncio
import copy
import hashlib
import importlib.metadata
import json
import os
import secrets
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path


def require(value, reason):
    if not value:
        raise AssertionError(reason)


def arguments():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", type=Path, required=True,
                        help="explicit frozen synthetic Service 4 view")
    parser.add_argument("--development", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


async def qualify(args):
    import mesh_plus
    from mesh_plus.api import Bridge, CachedPublisher, Client, Endpoint, Reader
    from mesh_plus.transport import IPCServer, boottime_ms, connect_ipc

    import agent_observer
    from agent_observer.active_contract import SELECTOR_DIGEST
    from agent_observer.contract import identity_key, store_namespace, validate_snapshot
    from agent_observer.mesh_active_profile import ACTIVE_PROFILE_ID, ActiveAgentProfile
    from agent_observer.mesh_active_read import PreparedActiveAgentWatch
    from agent_observer.mesh_active_source import CachedActiveAgentSource
    from agent_observer.service_contract import validate_frame
    from agent_observer.service_runtime import Runtime
    from agent_observer.service_state import ServiceState

    modules = {"observer": str(Path(agent_observer.__file__).resolve()),
               "mesh": str(Path(mesh_plus.__file__).resolve())}
    if not args.development:
        require(all("site-packages" in Path(path).parts for path in modules.values()),
                "exact_installed_wheels_required")
    frozen = validate_frame(json.loads(args.fixture.read_text(encoding="utf-8")))
    base = copy.deepcopy(frozen["snapshot"])
    source = next(s for s in base["sources"] if s["provider"] == "codex")
    template = next(r for r in base["sessions"] if r["identity"]["provider"] == "codex")
    host = frozen["hostScope"]
    require(host == "fixture", "explicit_synthetic_fixture_scope_required")
    namespace = store_namespace("codex", source["configHome"], source["configHomeKind"], os.geteuid())
    source["namespace"] = namespace
    source["capabilities"].update(runtime=["running", "parked"], activity=True,
                                  timing={"lastUpdated": True, "latestTurn": True})
    source.update(errors=[], limitations=["synthetic_controlled_fixture"])
    base["host"]["uid"] = os.geteuid()
    base["sources"] = [source]
    base["errors"], base["limitations"] = [], ["synthetic_controlled_fixture"]

    def native(values=("running", "running", "parked"), *, partial=False):
        """One new bounded daemon census, never a retained provider payload."""
        sample, wall = boottime_ms(), time.time_ns() // 1_000_000
        value = copy.deepcopy(base)
        value.update(collectionId=str(uuid.uuid4()), collectedAt=wall, sessions=[],
                     sourceHealth="partial" if partial else "current")
        owner = value["sources"][0]
        owner["sourceHealth"] = value["sourceHealth"]
        for dimension in ("runtime", "saved"):
            owner["coverage"][dimension].update(status="partial" if partial else "complete",
                                                reason="synthetic_partial" if partial else "native_snapshot")
        for number, runtime in enumerate(values):
            row = copy.deepcopy(template)
            identifier = str(uuid.UUID(int=number + 1))
            row["identity"].update(namespace=namespace, nativeId=identifier)
            row["nativeIds"] = {"threadId": identifier, "sessionTreeRootId": identifier}
            row.update(title="synthetic-agent-" + str(number), kind="unknown", cwd="/fixture/project",
                       cwdSource="codex_rpc", inventory="saved", hasSavedHistory=True,
                       metadataIssues=[], blockedReasons=[])
            row["runtime"] = {"value": runtime, "health": "current", "source": "codex_rpc",
                              "reason": "native_not_loaded" if runtime == "parked" else "native_snapshot",
                              "observedAt": wall, "clock": "sample"}
            row["phase"] = None if runtime == "parked" else {
                "value": "waiting", "health": "current", "source": "codex_rpc",
                "reason": "native_snapshot", "observedAt": wall, "clock": "sample",
            }
            row["activity"] = {"at": wall - 1000, "source": "codex_turn_metadata", "health": "current",
                               "reason": "native_conversation_event"}
            row["outcome"] = {"value": "completed", "health": "current", "source": "codex_turn_metadata",
                              "reason": "latest_terminal_turn", "observedAt": wall - 1000, "clock": "native"}
            row["workspace"] = {"health": "current", "reason": "synthetic_metadata", "root": None,
                                "rootKey": None, "relativePath": None, "projectKey": None, "repo": None}
            origin = {"component": "history", "sampledBoottimeMs": sample,
                      "observedBoottimeMs": sample, "contextGeneration": 0}
            row["lastUpdated"] = {
                "at": wall - 1000, "timestampPrecisionMs": 1000, "observedAt": wall,
                "source": "codex_thread_metadata", "health": "current", "reason": "native_thread_update",
                "receipt": copy.deepcopy(origin),
            }
            row["latestTurn"] = {
                "value": {"id": "synthetic-turn-" + str(number), "status": "completed",
                          "startedAt": wall - 10000, "completedAt": wall - 1000,
                          "durationMs": 9000, "timestampPrecisionMs": 1000},
                "observedAt": wall, "source": "codex_turn_metadata", "health": "current",
                "reason": "native_latest_turn", "receipt": copy.deepcopy(origin),
            }
            value["sessions"].append(row)
        return validate_snapshot(value), sample

    class SerializedState(ServiceState):
        """Serialize fixture submissions with the hosting thread's frame reads."""

        def __init__(self):
            self.serial = threading.RLock()
            super().__init__(host_scope=host,
                             configs={"codex": (source["configHome"], source["configHomeKind"])})
            self.native_hostname = base["host"]["nativeHostname"]

        def expire(self, *args, **kwargs):
            with self.serial:
                return super().expire(*args, **kwargs)

        def frame(self, *args, **kwargs):
            with self.serial:
                return super().frame(*args, **kwargs)

        def active_frame(self, *args, **kwargs):
            with self.serial:
                return super().active_frame(*args, **kwargs)

        def submit(self, values=("running", "running", "parked"), *, partial=False,
                   history_ttl=60000, runtime_ttl=60000):
            with self.serial:
                value, sample = native(values, partial=partial)
                self.attempt("codex", "history")
                require(self.accept("codex", "history", value, sampled_ms=sample,
                                    ttl_ms=history_ttl, runtime_ttl_ms=runtime_ttl), "synthetic_sample_rejected")
                return self.revision

    class Owner:
        def __init__(self, state, path):
            self.state, self.path = state, path
            self.runtime = Runtime(state, path, collect=False, heartbeat_ms=100, io_timeout_ms=2000)
            self.stop_event, self.errors = threading.Event(), []
            self.thread = threading.Thread(target=self.serve, name="owned-active-service")
            self.started = False

        def serve(self):
            try:
                self.runtime.run(self.stop_event)
            except BaseException as error:
                self.errors.append(type(error).__name__)

        async def start(self):
            self.thread.start()
            self.started = True
            async with asyncio.timeout(5):
                while not self.path.exists() and not self.errors:
                    await asyncio.sleep(.01)
            require(self.path.exists() and not self.errors, "owned_service_start")

        async def stop(self):
            if self.started:
                self.stop_event.set()
                await asyncio.to_thread(self.thread.join, 4)
                self.started = False
            require(not self.thread.is_alive() and not self.errors, "owned_service_stop")
            require(not self.path.exists() and not self.runtime.peers, "owned_native_socket_cleanup")
            require(self.runtime.counts["workerStarts"] == 0, "provider_worker_started")

    class NativeSource(CachedActiveAgentSource):
        def __init__(self, path):
            super().__init__(host, path, timeout=2)
            self.snapshot_reads = 0

        async def snapshot(self):
            self.snapshot_reads += 1
            return await super().snapshot()

    class Pipeline:
        async def __aenter__(self):
            self.directory = tempfile.TemporaryDirectory(prefix="ao-active-transport-")
            self.root = Path(self.directory.name)
            self.owner = Owner(self.state, self.root / "private/read.sock")
            self.owners = [self.owner]
            self.clients, self.readers = [], []
            self.server = None
            try:
                await self.owner.start()
                self.profile = ActiveAgentProfile()
                self.native = NativeSource(self.owner.path)
                self.publisher = CachedPublisher("agent", host, "active", self.native, profile=self.profile)
                self.socket = self.root / "mesh.sock"
                self.server = await IPCServer(self.socket, Bridge(
                    self.publisher, heartbeat_interval=.1,
                ).serve).start()
                self.reader = self.make_reader()
                return self
            except BaseException:
                await self.__aexit__(None, None, None)
                raise

        def __init__(self, state):
            self.state = state

        def make_reader(self, *, remote=False):
            async def connect():
                client = await Client.connect(await connect_ipc(self.socket), host=host, source="active",
                                              profile=ACTIVE_PROFILE_ID, codec=self.publisher.validate)
                self.clients.append(client)
                return client

            async def catalog():
                return "sha256:" + "b" * 64

            reader = Reader("agent", [Endpoint(
                host, not remote, "sha256:" + "a" * 64 if remote else None,
                connect, self.profile.bind(host, "active"),
            )], local_host="synthetic-reader" if remote else host, profile=self.profile,
                            catalog_revision="sha256:" + "b" * 64 if remote else None,
                            catalog_check=catalog if remote else None)
            self.readers.append(reader)
            return reader

        async def restart(self, state):
            await self.owner.stop()
            self.owner = Owner(state, self.owner.path)
            self.owners.append(self.owner)
            await self.owner.start()

        async def __aexit__(self, *_args):
            failures = []
            try:
                if self.server is not None:
                    try:
                        await self.server.close()
                    except BaseException as error:
                        failures.append(error)
                for owner in reversed(self.owners):
                    try:
                        await owner.stop()
                    except BaseException as error:
                        failures.append(error)
                if failures:
                    raise failures[0]
                require(all(client.channel.closed for client in self.clients), "mesh_channel_cleanup")
                require(all(reader.inspect()["activeConnections"] == 0 and
                            reader.inspect()["cleanupFailures"] == 0 for reader in self.readers),
                        "reader_cleanup")
                require(self.server is None or not self.server.tasks, "publisher_task_cleanup")
                require(not (self.root / "mesh.sock").exists(), "mesh_socket_cleanup")
                self.cleanup = {"serviceThreads": 0, "nativePeers": 0, "meshConnections": 0,
                                "publisherTasks": 0, "sockets": 0, "providerWorkers": 0,
                                "readerMetrics": [reader.inspect() for reader in self.readers]}
            finally:
                self.directory.cleanup()

    class Watch:
        def __init__(self, pipeline, *, reader=None):
            self.pipeline = pipeline
            self.reader = pipeline.reader if reader is None else reader
            self.request_id = secrets.token_hex(16)
            self.facade = PreparedActiveAgentWatch(self.request_id, profile=pipeline.profile)
            self.stream = self.reader.watch_admitted(request_id=self.request_id, proof_interval=.1)
            self.clock, self.snapshot = None, None
            self.frames = 0

        async def __aenter__(self):
            return self

        async def until(self, predicate):
            async with asyncio.timeout(8):
                while True:
                    self.facade.accept(await anext(self.stream))
                    self.frames += 1
                    self.snapshot = self.facade.snapshot()
                    if self.snapshot is not None:
                        self.clock = self.snapshot["mesh"]["reader"]["clock"]
                    if self.clock is None:
                        continue
                    result = self.facade.read(boottime_ms(), self.clock)
                    if predicate(result, self.snapshot):
                        return result

        async def __aexit__(self, *_args):
            self.facade.disconnect()
            await self.stream.aclose()
            if self.clock is not None:
                require(self.facade.read(boottime_ms(), self.clock).context is None,
                        "facade_disconnect_retained_authority")

    def complete(read):
        return bool(read.scopes) and all(scope["coverage"]["status"] == "complete" for scope in read.scopes)

    def current_revision(snapshot):
        if snapshot is None:
            return None
        owner = snapshot["mesh"]["hosts"][0]["owner"]
        return None if owner is None else owner["service"]["viewRevision"]

    def context_example(previous, read):
        """Explicit harness policy: only current membership facts retire context."""
        result = copy.deepcopy(previous)
        positives = {identity_key(row["identity"]): row for row in read.members}
        for scope in read.scopes:
            if scope["coverage"]["status"] == "complete":
                covered = scope["hostScope"], scope["provider"], scope["namespace"]
                result = {key: row for key, row in result.items()
                          if key[:3] != covered or key in positives}
        for entry in read.nonmembers:
            result.pop(identity_key(entry["identity"]), None)
        result.update(copy.deepcopy(positives))
        return result

    reports, cleanups = [], []
    state = SerializedState()
    state.submit(history_ttl=10000)
    generations = state.active_projector.generations
    pipeline = Pipeline(state)
    async with pipeline:
        async with Watch(pipeline) as watch:
            read = await watch.until(lambda result, _snapshot: len(result.members) == 2 and complete(result))
            require(all(row["lastUpdated"]["health"] == "current" and row["workspace"] is not None
                        for row in read.members), "history_fields_not_current")
            host_view = read.context["hosts"][0]
            deadlines = {r["component"]: r["expiresAtMs"] for r in host_view["receipts"]}
            require(deadlines["history"] < deadlines["runtime"], "independent_deadlines_missing")
            expired = watch.facade.read(deadlines["history"], watch.clock)
            require({identity_key(row["identity"]) for row in expired.members}
                    == {identity_key(row["identity"]) for row in read.members}, "field_expiry_retired_member")
            require(all(row["lastUpdated"]["health"] != "current" and row["workspace"] is None
                        for row in expired.members), "expired_history_fields_promoted")
            require(all(row["runtime"]["value"] == "running" and row["runtime"]["health"] == "current"
                        for row in expired.members), "field_expiry_revoked_unrelated_runtime")
            positive_expired = watch.facade.read(deadlines["runtime"], watch.clock)
            prior_context = {identity_key(row["identity"]): row for row in read.members}
            require(not positive_expired.members and not complete(positive_expired)
                    and context_example(prior_context, positive_expired) == prior_context,
                    "positive_expiry_retired_presentation_context")
        remote = pipeline.make_reader(remote=True)
        before = pipeline.native.snapshot_reads
        proofs = []
        for _ in range(2):
            snapshot = await remote.snapshot()
            owner = snapshot["mesh"]["hosts"][0]
            require(owner["delivery"]["status"] == "ready" and owner["delivery"]["proof"] is not None,
                    "fresh_proof_not_ready")
            require(owner["owner"]["service"]["selectorDigest"] == SELECTOR_DIGEST,
                    "proof_selector_binding")
            proofs.append(owner["delivery"]["proof"])
        require(proofs[0]["nonce"] != proofs[1]["nonce"] and pipeline.native.snapshot_reads >= before + 2,
                "proof_did_not_acquire_fresh_cached_reply")
        require(state.active_projector.generations == generations, "proof_reprojected_generation")
        reports.append({"case": "populated-independent-field-expiry-and-proofs", "members": 2,
                        "historyFieldsRevokedIndependently": True, "freshFullProofs": 2,
                        "positiveExpiryRetainsExternalContext": True,
                        "proofCarrier": "owned IPC with remote proof policy", "cacheGenerations": generations})
    cleanups.append(pipeline.cleanup)

    state = SerializedState()
    state.submit(("running",), runtime_ttl=1500)
    pipeline = Pipeline(state)
    async with pipeline:
        async with Watch(pipeline) as watch:
            read = await watch.until(lambda result, _snapshot: len(result.members) == 1 and complete(result))
            prior = copy.deepcopy(read.members[0])
            horizon = watch.snapshot["mesh"]["hosts"][0]["owner"]["metadata"]["scopes"][0]["members"][0][
                "fieldSupports"]["runtime"]["expiresBoottimeMs"]
        revision = state.submit(("parked",), partial=True)
        # An independent watcher sees the exact negative; the simulated
        # presentation consumer deliberately misses this bounded replacement.
        async with Watch(pipeline) as negative_watch:
            negative = await negative_watch.until(lambda result, snapshot:
                current_revision(snapshot) == revision and bool(result.nonmembers))
            require(not complete(negative) and negative.nonmembers[0]["reason"] == "parked",
                    "partial_exact_negative_missing")
            require(identity_key(negative.nonmembers[0]["identity"]) == identity_key(prior["identity"]),
                    "negative_identity_mismatch")
        await asyncio.sleep(max(0, (horizon - boottime_ms() + 20) / 1000))
        revision = state.submit((), partial=True)
        async with Watch(pipeline) as resumed:
            partial = await resumed.until(lambda result, snapshot:
                current_revision(snapshot) == revision and bool(result.scopes))
            require(not complete(partial) and not partial.members and not partial.nonmembers and not partial.uncertain,
                    "missed_negative_became_absence_authority")
            # The facade does not own UI history. This explicit context example
            # retires only for exact negative or fresh complete scope authority.
            prior_context = {identity_key(prior["identity"]): prior}
            retained_context = context_example(prior_context, partial)
            require(retained_context == prior_context, "presentation_context_hidden_by_bookkeeping")
            revision = state.submit(())
            empty = await resumed.until(lambda result, snapshot:
                current_revision(snapshot) == revision and complete(result) and not result.members)
            retained_context = context_example(retained_context, empty)
            require(not retained_context, "complete_empty_failed_reconciliation")
            expiry = max(r["expiresAtMs"] or 0 for r in empty.context["hosts"][0]["receipts"])
            require(not complete(resumed.facade.read(expiry, resumed.clock)),
                    "complete_empty_authority_outlived_receipts")
        reports.append({"case": "partial-missed-negative-and-complete-empty", "exactPartialNegative": True,
                        "negativeMissedThenAgedOut": True, "partialOmissionHasNoRetirementAuthority": True,
                        "externalPriorContextRetained": True, "completeEmptyReconciles": True,
                        "completeEmptyAuthorityExpires": True})
    cleanups.append(pipeline.cleanup)

    state = SerializedState()
    state.submit()
    pipeline = Pipeline(state)
    async with pipeline:
        async with Watch(pipeline) as watch:
            await watch.until(lambda result, _snapshot: len(result.members) == 2 and complete(result))
            old_service = state.service_id
            await pipeline.owner.stop()
            lost = await watch.until(lambda result, _snapshot:
                not result.members and not result.nonmembers and not complete(result))
            require(not complete(lost), "native_disconnect_concealed")
            replacement = SerializedState()
            replacement.submit()
            require(replacement.service_id != old_service, "new_owner_incarnation_missing")
            await pipeline.restart(replacement)
            recovered = await watch.until(lambda result, snapshot:
                len(result.members) == 2 and complete(result) and snapshot is not None
                and snapshot["mesh"]["hosts"][0]["owner"]["service"]["serviceId"] == replacement.service_id)
            require(all(scope["serviceId"] == replacement.service_id for scope in recovered.scopes),
                    "old_incarnation_authority_retained")
        reports.append({"case": "native-source-disconnect-and-reconnect", "authorityRevoked": True,
                        "newIncarnationRecovered": True, "membersAfterRecovery": 2})
    cleanups.append(pipeline.cleanup)

    versions = {}
    for name in ("agent-observer", "mesh-plus"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = "source-only"
    return {
        "status": "passed", "kind": "synthetic installed transport lifecycle; no native census or rollout proof",
        "development": args.development, "modules": modules, "versions": versions,
        "moduleVersions": {"agent-observer": getattr(agent_observer, "__version__", None),
                           "mesh-plus": getattr(mesh_plus, "__version__", None)},
        "python": sys.version.split()[0], "fixtureSha256": hashlib.sha256(args.fixture.read_bytes()).hexdigest(),
        "profile": ACTIVE_PROFILE_ID, "selectorDigest": SELECTOR_DIGEST, "reports": reports,
        "cleanup": cleanups, "providerActions": 0, "normalSelectionsChanged": False,
        "limits": ["Synthetic accepted samples; collect=False; owned private IPC only",
                   "Remote proof policy over IPC is not SSH/cross-host proof",
                   "Fixed SSH is qualified separately by the Mesh owner harness",
                   "No performance, real provider classification, device or production acceptance"],
    }


def main():
    args = arguments()
    result = json.dumps(asyncio.run(qualify(args)), sort_keys=True, separators=(",", ":")) + "\n"
    if args.output:
        args.output.write_text(result, encoding="utf-8")
    print(result, end="")


if __name__ == "__main__":
    main()
