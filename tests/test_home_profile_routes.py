"""Two named homes through existing local service and public Mesh routes.

All observations are fixture data accepted by ServiceState. This test starts
only disposable Observer/Bridge sockets and never invokes a native provider.
"""

import asyncio
import hashlib
import os
import tempfile
import threading
import time
import unittest
from pathlib import Path

from mesh_plus.api import Bridge, Client, Endpoint, Reader
from mesh_plus.transport import IPCServer, connect_ipc
from test_service_runtime import scoped_snapshot

from agent_observer.contract import ContractError, identity_key, store_namespace
from agent_observer.home_profiles import load_home_profiles
from agent_observer.mesh_working_set_profile import WorkingSetAgentProfile
from agent_observer.mesh_working_set_publisher import make_working_set_publisher
from agent_observer.mesh_working_set_read import PreparedWorkingSetAgentWatch
from agent_observer.service_runtime import Runtime
from agent_observer.service_state import ServiceState


HOST = "snap"
THREAD_ID = "00000000-0000-4000-8000-000000000123"


def _toml(default_home, work_home):
    return (
        'version = 1\nhost = "snap"\n\n'
        '[profiles.default]\nlabel = "Default"\n'
        f'codex_home = "{default_home}"\n\n'
        '[profiles.work]\nlabel = "Work"\n'
        f'codex_home = "{work_home}"\n'
    )


def _service_state(route, *, home=None):
    """Build one complete current state with a caller-selected store path."""
    uid = os.geteuid()
    configured_home = route.codex_home if home is None else str(home)
    namespace = store_namespace("codex", configured_home, "explicit", uid)
    state = ServiceState(
        host_scope=route.host,
        configs={"codex": (configured_home, "explicit")},
        uid=uid,
        working_set_window_ms=route.window_ms,
    )
    sample = scoped_snapshot()
    wall = time.time_ns() // 1_000_000
    sample["collectedAt"] = wall
    sample["host"].update(authority=route.host, uid=uid)
    sample["sources"] = [sample["sources"][0]]
    sample["sources"][0].update(
        configHome=configured_home,
        configHomeKind="explicit",
        namespace=namespace,
    )
    sample["sources"][0]["capabilities"]["activity"] = True
    sample["sessions"] = [sample["sessions"][0]]
    row = sample["sessions"][0]
    row["identity"].update(
        hostScope=route.host,
        namespace=namespace,
        nativeId=THREAD_ID,
    )
    row["nativeIds"].update(threadId=THREAD_ID, sessionTreeRootId=THREAD_ID)
    row["runtime"]["value"] = "running"
    row["activity"].update(
        at=wall - 5_000,
        source="codex_rpc",
        health="current",
        reason="native_timestamp",
    )
    sampled = state.clock()
    state.attempt("codex", "runtime")
    accepted = state.accept(
        "codex",
        "runtime",
        sample,
        sampled_ms=sampled,
        ttl_ms=120_000,
        accepted_boottime_ms=state.clock(),
    )
    if accepted is not True:
        raise AssertionError("fixture_acceptance_required")
    return state, namespace


class RuntimeAtPath:
    """An owned collect=False service used only by this disposable test."""

    def __init__(self, state, path):
        self.path = Path(path)
        self.runtime = Runtime(state, self.path, collect=False)
        self.stop = threading.Event()
        self.errors = []
        self.thread = threading.Thread(target=self._run, name="home-profile-service")

    def _run(self):
        try:
            self.runtime.run(self.stop)
        except BaseException as error:
            self.errors.append(error)

    def __enter__(self):
        self.thread.start()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if self.errors:
                self.__exit__()
                raise AssertionError(self.errors)
            try:
                if self.path.stat().st_mode & 0o777 == 0o600:
                    return self
            except OSError:
                pass
            time.sleep(0.01)
        self.__exit__()
        raise AssertionError("service_socket_not_ready")

    def __exit__(self, *_args):
        self.stop.set()
        self.thread.join(4)
        if self.thread.is_alive():
            raise AssertionError("service_thread_not_stopped")
        if self.path.exists():
            raise AssertionError("service_socket_leaked")
        if self.errors:
            raise AssertionError(self.errors)


def _reader_clock():
    return {
        "bootId": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "timeNamespace": os.readlink("/proc/self/ns/time").replace("[", "").replace("]", ""),
    }


def _reader_now():
    return int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)


class HomeProfileRoutesTest(unittest.IsolatedAsyncioTestCase):
    async def _open_public_route(self, route):
        profile = WorkingSetAgentProfile(route.window_ms)
        publisher = make_working_set_publisher(
            route.host,
            route.mesh_source,
            route.collector_socket,
            window_ms=route.window_ms,
        )
        route.publisher_runtime_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        server = await IPCServer(route.publisher_socket, Bridge(publisher).serve).start()
        codec = profile.bind(route.host, route.mesh_source)
        revision = "sha256:" + hashlib.sha256(route.mesh_source.encode()).hexdigest()

        async def connect():
            channel = await connect_ipc(route.publisher_socket)
            return await Client.connect(
                channel,
                host=route.host,
                source=route.mesh_source,
                profile=profile.descriptor.profile_id,
                codec=codec.validate_bridge,
            )

        async def catalog_check():
            return revision

        reader = Reader(
            "agent",
            [Endpoint(route.host, False, revision, connect, codec)],
            local_host="profile-reader",
            profile=profile,
            catalog_revision=revision,
            catalog_check=catalog_check,
        )
        request_id = "2" * 32 if route.profile_id == "work" else "1" * 32
        facade = PreparedWorkingSetAgentWatch(
            request_id,
            profile=profile,
            window_ms=route.window_ms,
        )
        stream = reader.watch_admitted(request_id=request_id, proof_interval=0.1)
        return {
            "publisher": publisher,
            "server": server,
            "reader": reader,
            "facade": facade,
            "stream": stream,
        }

    async def _read_complete(self, route_reader):
        for _ in range(40):
            frame = await asyncio.wait_for(anext(route_reader["stream"]), timeout=3)
            route_reader["facade"].accept(frame)
            result = route_reader["facade"].read(_reader_now(), _reader_clock())
            snapshot = route_reader["facade"].snapshot()
            if snapshot is None or result.context is None or not result.scopes:
                continue
            host = snapshot["mesh"]["hosts"][0]
            if (
                host["delivery"]["status"] == "ready"
                and host["delivery"]["proof"] is not None
                and result.scopes[0]["coverage"]["status"] == "complete"
            ):
                self.assertEqual(len(result.members), 1)
                self.assertEqual(result.uncertain, [])
                self.assertEqual(result.nonmembers, [])
                return snapshot, result
        self.fail("public_reader_did_not_reach_complete_proven_view")

    async def asyncTearDown(self):
        # Per-test teardown actions are registered only for routes successfully
        # opened; this is a final guard against leaving an IPC handler alive.
        routes = getattr(self, "_open_routes", [])
        for route_reader in reversed(routes):
            route_reader["facade"].disconnect()
            await route_reader["stream"].aclose()
            if not route_reader["server"].closed:
                await route_reader["server"].close()

    async def test_two_same_host_routes_keep_identical_thread_ids_distinct(self):
        with tempfile.TemporaryDirectory(prefix="home-route-") as directory:
            root = Path(directory)
            runtime_dir = root / "xdg"
            runtime_dir.mkdir(mode=0o700)
            default_home, work_home = root / "codex-default", root / "codex-work"
            config = root / "profiles.toml"
            config.write_text(_toml(default_home, work_home), encoding="utf-8")
            config.chmod(0o600)
            manifest = load_home_profiles(
                config,
                uid=os.getuid(),
                runtime_dir=runtime_dir,
            )
            routes = manifest.routes
            self.assertEqual([route.host for route in routes], [HOST, HOST])
            self.assertNotEqual(routes[0].mesh_source, routes[1].mesh_source)
            self.assertNotEqual(routes[0].collector_socket, routes[1].collector_socket)
            self.assertNotEqual(routes[0].publisher_socket, routes[1].publisher_socket)

            states = [_service_state(route) for route in routes]
            self.assertEqual(states[0][1], routes[0].namespace)
            self.assertEqual(states[1][1], routes[1].namespace)
            shared_runtime = [
                RuntimeAtPath(state, route.collector_socket)
                for route, (state, _namespace) in zip(routes, states, strict=True)
            ]
            public = []
            self._open_routes = public
            try:
                with shared_runtime[0], shared_runtime[1]:
                    for route in routes:
                        public.append(await self._open_public_route(route))
                    observations = [await self._read_complete(item) for item in public]
                    rows = [observation[1].members[0] for observation in observations]
                    keys = [identity_key(row["identity"]) for row in rows]

                    self.assertEqual(rows[0]["identity"]["hostScope"], HOST)
                    self.assertEqual(rows[1]["identity"]["hostScope"], HOST)
                    self.assertEqual(rows[0]["identity"]["nativeId"], THREAD_ID)
                    self.assertEqual(rows[1]["identity"]["nativeId"], THREAD_ID)
                    self.assertEqual(rows[0]["identity"]["namespace"], routes[0].namespace)
                    self.assertEqual(rows[1]["identity"]["namespace"], routes[1].namespace)
                    self.assertNotEqual(rows[0]["identity"]["namespace"], rows[1]["identity"]["namespace"])
                    self.assertNotEqual(keys[0], keys[1])
                    for route_reader, route in zip(public, routes, strict=True):
                        self.assertEqual(route_reader["reader"].inspect()["activeConnections"], 1)
                        self.assertEqual(route_reader["reader"].endpoints[0].host, HOST)
                        self.assertEqual(route_reader["reader"].endpoints[0].codec.source, route.mesh_source)

                    # Expiring one read facade affects only its own guard and
                    # original leases; the sibling still returns its admitted row.
                    first_snapshot = observations[0][0]
                    first_host = first_snapshot["mesh"]["hosts"][0]
                    deadlines = [
                        receipt["expiresAtMs"]
                        for receipt in first_host["receipts"]
                        if type(receipt["expiresAtMs"]) is int
                    ]
                    self.assertTrue(deadlines)
                    expired = public[0]["facade"].read(max(deadlines) + 1, _reader_clock())
                    self.assertEqual(expired.members, [])
                    self.assertNotEqual(expired.scopes[0]["coverage"]["status"], "complete")
                    sibling = public[1]["facade"].read(_reader_now(), _reader_clock())
                    self.assertEqual(len(sibling.members), 1)
                    self.assertEqual(sibling.scopes[0]["coverage"]["status"], "complete")

                    public[0]["facade"].disconnect()
                    self.assertIsNone(public[0]["facade"].read(_reader_now(), _reader_clock()).context)
                    sibling_after_close = public[1]["facade"].read(_reader_now(), _reader_clock())
                    self.assertEqual(len(sibling_after_close.members), 1)
            finally:
                for route_reader in reversed(public):
                    route_reader["facade"].disconnect()
                    await route_reader["stream"].aclose()
                    await route_reader["server"].close()
                self._open_routes = []

            self.assertFalse(default_home.exists())
            self.assertFalse(work_home.exists())

    def test_public_codec_rejects_wrong_source_but_expected_home_is_not_bound(self):
        with tempfile.TemporaryDirectory(prefix="home-binding-") as directory:
            root = Path(directory)
            runtime_dir = root / "xdg"
            runtime_dir.mkdir(mode=0o700)
            default_home, work_home, wrong_home = (
                root / "default",
                root / "work",
                root / "wrong-home",
            )
            config = root / "profiles.toml"
            config.write_text(_toml(default_home, work_home), encoding="utf-8")
            config.chmod(0o600)
            manifest = load_home_profiles(
                config,
                uid=os.getuid(),
                runtime_dir=runtime_dir,
            )
            default, work = manifest.routes
            profile = WorkingSetAgentProfile(default.window_ms)
            codec = profile.bind(default.host, default.mesh_source)
            state, wrong_namespace = _service_state(default, home=wrong_home)
            frame = state.working_set_frame("status", 1)

            with self.assertRaisesRegex(ContractError, "bridge_source_binding"):
                codec.validate_bridge(
                    {
                        "hostId": default.host,
                        "sourceId": work.mesh_source,
                        "ownerFrame": frame,
                    }
                )

            # This remains an explicit integration gap: the frozen Mesh codec
            # binds host/source/window, while the current factory does not also
            # bind the configured store namespace to the selected home route.
            self.assertNotEqual(wrong_namespace, default.namespace)
            codec.validate_bridge(
                {
                    "hostId": default.host,
                    "sourceId": default.mesh_source,
                    "ownerFrame": frame,
                }
            )
            self.assertEqual(frame["sources"][0]["namespace"], wrong_namespace)
            self.assertNotEqual(frame["sources"][0]["namespace"], default.namespace)


if __name__ == "__main__":
    unittest.main()
