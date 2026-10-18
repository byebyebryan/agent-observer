"""Public cached acquisition over disposable native UNIX sockets, no SDK role."""

import asyncio
import contextlib
import copy
import json
import os
import tempfile
import time
import unittest
from pathlib import Path

from test_active_service_delivery import local_uid
from test_working_set_contract import fixture

from agent_observer.contract import ContractError, canonical
from agent_observer.mesh_working_set_source import CachedWorkingSetAgentSource
from agent_observer.working_set_contract import selector, selector_digest, validate_frame


def native_frame():
    value = local_uid(fixture(recent=True, window=259200000))
    value.update(
        kind="status",
        bootId=Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        clockDomain=os.readlink("/proc/self/ns/time"),
    )
    now = int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)
    value["emittedBoottimeMs"] = now
    lower, upper = now - 100, now - 90

    def visit(item):
        if isinstance(item, dict):
            if "sampledBoottimeMs" in item:
                item["sampledBoottimeMs"] = lower
            if "expiresBoottimeMs" in item:
                item["expiresBoottimeMs"] = now + 20000
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)

    visit(value)
    scope = value["projection"]["scopes"][0]
    clock = scope["clocks"][0]
    clock["acceptedBoottimeMs"] = upper
    value["clockCeiling"] = clock["wallMs"] - lower + 1
    branch = scope["members"][0]["recent"]
    branch["lowerBoottimeMs"] = branch["activityAt"] + 259200000 - value["clockCeiling"]
    branch["upperBoottimeMs"] = upper + 259200000 - (clock["wallMs"] - branch["activityAt"]) + 1
    return validate_frame(value)


class WorkingSetSourceTest(unittest.IsolatedAsyncioTestCase):
    async def run_source(self, responses, check):
        requests, tasks = [], set()

        async def handle(reader, writer):
            task = asyncio.current_task()
            tasks.add(task)
            try:
                requests.append(json.loads(await reader.readline()))
                reply = responses[min(len(requests) - 1, len(responses) - 1)]
                writer.write((canonical(reply) + "\n").encode())
                await writer.drain()
                await reader.read()
            except (ConnectionError, asyncio.CancelledError):
                pass
            finally:
                writer.close()
                with contextlib.suppress(ConnectionError):
                    await writer.wait_closed()
                tasks.discard(task)

        with tempfile.TemporaryDirectory(prefix="observer-working-set-source-") as directory:
            path = Path(directory) / "read.sock"
            server = await asyncio.start_unix_server(handle, path=path)
            path.chmod(0o600)
            source = CachedWorkingSetAgentSource("fixture", path)
            try:
                await check(source, requests)
                self.assertEqual(source._active, 0)
                self.assertEqual(source._pending_reads, 0)
            finally:
                server.close()
                await server.wait_closed()
                for task in list(tasks):
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

    async def test_snapshot_exact_policy_detached_request_and_socket_cleanup(self):
        value = native_frame()

        async def check(source, requests):
            result = await source.snapshot()
            self.assertEqual(result, value)
            self.assertEqual(requests[0]["workingSetProtocol"], 1)
            self.assertNotIn("serviceProtocol", requests[0])
            self.assertEqual(requests[0]["selector"], value["selector"])
            requests[0]["selector"]["recent"]["windowMs"] = 0
            self.assertEqual(source._make_request("status")["selector"], value["selector"])
            with self.assertRaises(AttributeError):
                source.window_ms = 0

        await self.run_source([value], check)

    async def test_across_status_operations_clock_ceiling_cannot_regress(self):
        first = native_frame()
        first["clockCeiling"] += 2000
        first["projection"]["scopes"][0]["members"][0]["recent"]["lowerBoottimeMs"] -= 2000
        second = copy.deepcopy(first)
        second["viewRevision"] += 1
        second["clockCeiling"] -= 1000
        second["projection"]["scopes"][0]["members"][0]["recent"]["lowerBoottimeMs"] += 1000
        validate_frame(first)
        validate_frame(second)

        async def check(source, _requests):
            await source.snapshot()
            with self.assertRaisesRegex(ContractError, "working_set_acquisition_clock_regression"):
                await source.snapshot()
            self.assertEqual(source._clock_watermark, (first["clockCeiling"], 0))

        await self.run_source([first, second], check)

    async def test_wrong_policy_fails_without_another_family_request(self):
        value = native_frame()
        value["selector"] = selector(0)
        value["selectorDigest"] = selector_digest(value["selector"])
        value["projection"]["scopes"][0]["members"][0]["recent"] = None
        validate_frame(value)

        async def check(source, requests):
            with self.assertRaises(ContractError):
                await source.snapshot()
            self.assertEqual(len(requests), 1)
            self.assertIn("workingSetProtocol", requests[0])

        await self.run_source([value], check)
