"""Content-free summaries for bounded local Service 4 or Mesh working-set reads."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
import time
import uuid
from pathlib import Path

from agent_observer.service_client import frames
from agent_observer.service_public import ContractError, ReadCache

TICK_SECONDS = 0.1
OUTPUT_SECONDS = 1.0
MAX_DURATION_SECONDS = 60.0
MAX_WINDOW_HOURS = 720
IDENTITY_FIELDS = ("hostScope", "provider", "namespace", "nativeIdKind", "nativeId")


def boottime_ms():
    return int(time.clock_gettime(time.CLOCK_BOOTTIME) * 1000)


def local_clock():
    return {
        "bootId": Path("/proc/sys/kernel/random/boot_id").read_text().strip(),
        "timeNamespace": os.readlink("/proc/self/ns/time").replace("[", "").replace("]", ""),
    }


def select(value, fields):
    return {key: value[key] for key in fields if key in value}


def identity(value):
    return select(value, IDENTITY_FIELDS)


def fact(value):
    return None if value is None else select(value, ("value", "health", "reason"))


def failure_code(error):
    code = getattr(error, "code", None)
    if isinstance(code, str) and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", code):
        return code
    name = type(error).__name__.lower()
    return name if re.fullmatch(r"[a-z][a-z0-9_]{0,127}", name) else "read_failed"


def local_failure_code(error):
    if isinstance(error, ContractError):
        reason = str(error)
        return reason if re.fullmatch(r"[a-z][a-z0-9_]{0,127}", reason) else "service_read_failed"
    name = type(error).__name__.lower()
    return name if re.fullmatch(r"[a-z][a-z0-9_]{0,127}", name) else "read_failed"


def emit(value):
    print(json.dumps(value, sort_keys=True, separators=(",", ":")))


def local_summary(result, *, host, clock, final=False, transport="connected", failure=None):
    snapshot = result["snapshot"]
    data = snapshot or {}
    sources = [
        {
            "provider": source["provider"],
            "namespace": source["namespace"],
            "health": source["sourceHealth"],
            "coverage": {
                name: select(source["coverage"][name], ("status", "reason", "scope"))
                for name in ("runtime", "saved")
            },
        }
        for source in data.get("sources", ())
    ]
    sessions = [
        {
            "identity": identity(row["identity"]),
            "runtime": fact(row.get("runtime")),
            "phase": fact(row.get("phase")),
        }
        for row in data.get("sessions", ())
    ]
    complete = (
        bool(sources)
        and all(
            source["health"] == "current"
            and all(
                source["coverage"][name]["status"] == "complete" for name in ("runtime", "saved")
            )
            for source in sources
        )
        and bool(result["components"])
        and all(item["current"] for item in result["components"])
    )
    state = result["health"]
    if snapshot is not None and state == "current":
        state = "complete-empty" if not sessions and complete else "current"
    if final:
        state, sessions = "revoked", []
    lifecycle = "watching" if not final else "revoked" if failure else "closed"

    return {
        "example": "agent-observer.current-summary.v1",
        "source": {
            "kind": "local-service-watch",
            "hostScope": host,
            "socket": "explicit",
            "serviceProtocol": 4,
            "observationApiVersion": 4,
            "embeddedSnapshotVersion": 6,
        },
        "lifecycle": lifecycle,
        "transport": {"state": transport, "failure": failure},
        "clock": {"kind": "CLOCK_BOOTTIME", **clock},
        "view": {
            "state": state,
            "health": result["health"],
            "reason": result["reason"],
            "sources": sources,
            "components": [
                select(
                    item,
                    (
                        "provider",
                        "namespace",
                        "component",
                        "current",
                        "health",
                        "expiresBoottimeMs",
                    ),
                )
                for item in result["components"]
            ],
            "sessionCount": len(sessions),
            "sessions": sessions,
        },
    }


def validate_duration(value):
    if type(value) not in (int, float) or not 0 < value <= MAX_DURATION_SECONDS:
        raise ValueError("duration_must_be_between_zero_and_60_seconds")


def run_local(*, host, socket_path, duration=5.0, output=emit):
    """Watch an explicit Service 4 socket with a budget started before first read.

    The public transport timeout is max(1, duration), capped at 60 seconds.
    """
    validate_duration(duration)
    clock = local_clock()
    cache = ReadCache(
        host_scope=host,
        uid=os.geteuid(),
        boot_id=clock["bootId"],
        clock_domain="time:[" + clock["timeNamespace"].split(":", 1)[-1].strip("[]") + "]",
    )
    transport_timeout = min(MAX_DURATION_SECONDS, max(1.0, duration))
    stream = frames(
        socket_path, host_scope=host, timeout=transport_timeout, tick_interval=TICK_SECONDS
    )

    def report(result, now, **options):
        output(
            local_summary(
                result,
                host=host,
                clock={**clock, "nowBoottimeMs": now},
                **options,
            )
        )

    deadline = boottime_ms() + int(duration * 1000)
    last_output = None
    failure = None
    transport = "connected"
    code = 0
    baseline = False
    try:
        while True:
            baseline_before_read = baseline
            try:
                frame = next(stream)
            except StopIteration:
                failure, transport, code = "service_stream_ended", "disconnected", 1
                break
            except Exception as error:
                now = boottime_ms()
                reason = local_failure_code(error)
                if (
                    isinstance(error, ContractError)
                    and reason == "service_transport_timeout"
                    and baseline
                    and now >= deadline
                ):
                    break
                failure, transport, code = reason, "disconnected", 1
                break
            now = boottime_ms()
            if now >= deadline and not baseline_before_read:
                failure, code, transport = "service_baseline_unavailable", 1, "closed"
                break
            if frame is not None:
                try:
                    cache.accept(frame, now_ms=now)
                except Exception as error:
                    failure, transport, code = local_failure_code(error), "disconnected", 1
                    break
            result = cache.current(now)
            baseline = baseline or result["snapshot"] is not None
            if last_output is None or now - last_output >= int(OUTPUT_SECONDS * 1000):
                report(result, now)
                last_output = now
            if now >= deadline:
                break
    except KeyboardInterrupt:
        failure, transport = "cancelled", "disconnected"
        raise
    finally:
        try:
            stream.close()
        except Exception as error:
            if failure is None:
                failure, transport, code = local_failure_code(error), "disconnected", 1
        finally:
            cache.invalidate("read_closed" if failure is None else "read_disconnected")
            now = boottime_ms()
            report(
                cache.current(now),
                now,
                final=True,
                transport="closed" if failure is None else transport,
                failure=failure,
            )
    return code


def mesh_state(read):
    if read is None or read.context is None:
        return "warming"
    statuses = [scope["coverage"]["status"] for scope in read.scopes]
    if not statuses:
        return "unavailable"
    if all(status == "complete" for status in statuses):
        return (
            "complete-empty"
            if not read.members and not read.nonmembers and not read.uncertain
            else "complete"
        )
    return next(
        (
            status
            for status in ("unavailable", "warming", "stale", "partial", "unsupported")
            if status in statuses
        ),
        "partial",
    )


def mesh_summary(
    read,
    *,
    source,
    host,
    scope,
    window_ms,
    clock,
    interfaces,
    final=False,
    transport="connected",
    failure=None,
):
    scopes, sessions, uncertain, nonmembers, hosts = [], [], [], [], []
    if read is not None:
        for item in read.scopes:
            scopes.append(
                {
                    "hostScope": item["hostScope"],
                    "serviceId": item["serviceId"],
                    "provider": item["provider"],
                    "namespace": item["namespace"],
                    "contextGeneration": item["contextGeneration"],
                    "continuity": item["continuity"],
                    "coverage": {
                        key: item["coverage"].get(key)
                        for key in ("status", "reason", "expiresAtMs")
                    },
                }
            )
        leases = {
            tuple(item["identity"].get(key) for key in IDENTITY_FIELDS): item
            for item in read.member_leases
        }
        for row in read.members:
            lease = leases.get(tuple(row["identity"].get(key) for key in IDENTITY_FIELDS), {})
            sessions.append(
                {
                    "identity": identity(row["identity"]),
                    "runtime": fact(row.get("runtime")),
                    "phase": fact(row.get("phase")),
                    "membershipLease": {
                        key: lease.get(key)
                        for key in (
                            "activeExpiresAtMs",
                            "recentExpiresAtMs",
                            "membershipExpiresAtMs",
                        )
                    },
                }
            )
        uncertain = [
            {"identity": identity(item["identity"]), "reason": item["reason"]}
            for item in read.uncertain
        ]
        nonmembers = [
            {"identity": identity(item["identity"]), "reason": item["reason"]}
            for item in read.nonmembers
        ]
        if read.context is not None:
            hosts = [
                {
                    "host": item["hostId"],
                    "path": item["delivery"]["path"],
                    "state": item["delivery"]["status"],
                    "viewState": item["viewState"],
                }
                for item in read.context["hosts"]
            ]
    if final:
        sessions, uncertain, nonmembers, scopes, hosts = [], [], [], [], []
    lifecycle = "watching" if not final else "revoked" if failure else "closed"
    return {
        "example": "agent-observer.current-summary.v1",
        "source": {
            "kind": "mesh-working-set-watch",
            "domain": "agent",
            "sourceId": source,
            "scope": scope,
            "hostIds": [host],
            "socket": "explicit",
            "windowMs": window_ms,
            "meshSdkInterface": interfaces.get("sdk"),
            "workingSetReadInterface": interfaces.get("read"),
            "memberLeaseInterface": interfaces.get("memberLease"),
            "scopeLeaseInterface": interfaces.get("scopeLease"),
        },
        "lifecycle": lifecycle,
        "transport": {"state": transport, "hosts": hosts, "failure": failure},
        "clock": None
        if clock is None
        else {
            "bootId": clock["bootId"],
            "timeNamespace": clock["timeNamespace"],
            "nowBoottimeMs": clock["nowBoottimeMs"],
        },
        "view": {
            "state": "revoked" if final else mesh_state(read),
            "memberCount": len(sessions),
            "members": sessions,
            "uncertain": uncertain,
            "nonmembers": nonmembers,
            "scopes": scopes,
        },
    }


async def ticked(stream, *, interval=TICK_SECONDS):
    """Yield quiet ticks while keeping one pending SDK read alive."""
    if not 0 < interval <= 1:
        raise ValueError("tick_interval")
    pending = None
    try:
        while True:
            if pending is None:
                pending = asyncio.create_task(anext(stream))
            done, _ = await asyncio.wait({pending}, timeout=interval)
            if not done:
                yield None
                continue
            try:
                frame = pending.result()
            except StopAsyncIteration:
                return
            pending = None
            yield frame
    finally:
        if pending is not None:
            pending.cancel()
            await asyncio.gather(pending, return_exceptions=True)


async def run_mesh(
    *,
    host,
    source,
    socket_path,
    scope="hosts",
    window_ms=72 * 60 * 60 * 1000,
    duration=5.0,
    output=emit,
):
    """Use one configured, admitted Mesh watch; duration includes setup."""
    validate_duration(duration)
    if scope not in {"local", "hosts"}:
        raise ValueError("mesh_scope")

    deadline = asyncio.get_running_loop().time() + duration
    deadline_timeout = asyncio.timeout_at(deadline)
    clock_domain_fn = boottime_fn = None
    interfaces, reader, guard, stream, events = {}, None, None, None, None
    failure = None
    transport = "connected"
    code = 0
    baseline = False
    last_output = None

    def report(read, *, clock=None, final=False, transport="connected", failure=None):
        output(
            mesh_summary(
                read,
                source=source,
                host=host,
                scope=scope,
                window_ms=window_ms,
                clock=clock,
                interfaces=interfaces,
                final=final,
                transport=transport,
                failure=failure,
            )
        )

    try:
        async with deadline_timeout:
            from mesh_plus.api import SDK_INTERFACE_VERSION, AdmittedResponse, configured_reader
            from mesh_plus.evidence import clock_domain as clock_domain_fn
            from mesh_plus.transport import boottime_ms as boottime_fn

            from agent_observer.mesh_working_set_profile import WorkingSetAgentProfile
            from agent_observer.mesh_working_set_read import (
                WORKING_SET_MEMBER_LEASE_INTERFACE_VERSION,
                WORKING_SET_READ_INTERFACE_VERSION,
                WORKING_SET_SCOPE_LEASE_INTERFACE_VERSION,
                PreparedWorkingSetAgentWatch,
            )

            profile = WorkingSetAgentProfile(window_ms)
            interfaces = {
                "sdk": SDK_INTERFACE_VERSION,
                "read": WORKING_SET_READ_INTERFACE_VERSION,
                "memberLease": WORKING_SET_MEMBER_LEASE_INTERFACE_VERSION,
                "scopeLease": WORKING_SET_SCOPE_LEASE_INTERFACE_VERSION,
            }
            request_id = uuid.uuid4().hex
            reader = await configured_reader(
                "agent",
                source=source,
                socket=socket_path,
                scope=scope,
                hosts=[host] if scope == "hosts" else [],
                local_host=host if scope == "local" else None,
                report_routes=False,
                profile=profile,
            )
            guard = PreparedWorkingSetAgentWatch(
                request_id,
                host_ids=[host] if scope == "hosts" else None,
                window_ms=window_ms,
                profile=profile,
            )
            request = {
                "meshProtocol": 1,
                "requestId": request_id,
                "operation": "watch",
                "profile": profile.descriptor.profile_id,
                "access": "cached",
                "selection": {"mode": scope, "hostIds": [host] if scope == "hosts" else []},
                "extensions": {},
            }
            stream = reader.execute_admitted(request)
            events = ticked(stream)
            async for frame in events:
                now = boottime_fn()
                if frame is not None:
                    if isinstance(frame, dict) and isinstance(frame.get("error"), dict):
                        reason = frame["error"].get("code")
                        failure = (
                            reason
                            if isinstance(reason, str)
                            and re.fullmatch(r"[a-z][a-z0-9_]{0,127}", reason)
                            else "mesh_read_failed"
                        )
                        transport, code = "disconnected", 1
                        break
                    kind = (
                        frame.context()["mesh"].get("kind")
                        if isinstance(frame, AdmittedResponse)
                        else frame.get("mesh", {}).get("kind")
                        if isinstance(frame, dict)
                        else None
                    )
                    guard.accept(frame)
                    baseline = True
                    if kind in {"gap", "resync"}:
                        failure, transport, code = (
                            "mesh_gap" if kind == "gap" else "mesh_resync",
                            "disconnected",
                            1,
                        )
                        break
                clock = clock_domain_fn()
                read = guard.read(now, clock)
                disconnected = read.context is not None and any(
                    host_view["delivery"]["status"] in {"unavailable", "disconnected"}
                    for host_view in read.context["hosts"]
                )
                if disconnected:
                    failure, transport, code = "mesh_delivery_disconnected", "disconnected", 1
                    report(
                        read,
                        clock={**clock, "nowBoottimeMs": now},
                        transport=transport,
                        failure=failure,
                    )
                    break
                if last_output is None or now - last_output >= int(OUTPUT_SECONDS * 1000):
                    report(read, clock={**clock, "nowBoottimeMs": now})
                    last_output = now
            else:
                failure, transport, code = "mesh_stream_ended", "disconnected", 1
    except TimeoutError:
        if deadline_timeout.expired() and not baseline:
            failure, transport, code = "mesh_setup_timeout", "disconnected", 1
        elif not deadline_timeout.expired():
            failure, transport, code = "mesh_operation_timeout", "disconnected", 1
    except asyncio.CancelledError:
        failure, transport = "cancelled", "disconnected"
        raise
    except Exception as error:
        failure, transport, code = failure_code(error), "disconnected", 1
    finally:
        if guard is not None:
            try:
                guard.disconnect()
            except BaseException as error:
                if failure is None:
                    failure, transport, code = failure_code(error), "disconnected", 1
        for iterator in (events, stream):
            if iterator is not None:
                try:
                    await iterator.aclose()
                except BaseException as error:
                    if failure is None:
                        failure, transport, code = failure_code(error), "disconnected", 1
        clock = None
        if clock_domain_fn is not None and boottime_fn is not None:
            try:
                clock = {**clock_domain_fn(), "nowBoottimeMs": boottime_fn()}
            except Exception as error:
                if failure is None:
                    failure, transport, code = failure_code(error), "disconnected", 1
        report(
            None,
            clock=clock,
            final=True,
            transport="closed" if failure is None else transport,
            failure=failure,
        )
    return code


def window_hours(value):
    try:
        hours = int(value)
    except (TypeError, ValueError) as error:
        raise argparse.ArgumentTypeError("window must be an integer number of hours") from error
    if str(hours) != str(value) or not 0 <= hours <= MAX_WINDOW_HOURS:
        raise argparse.ArgumentTypeError("window must be an integer from 0 through 720 hours")
    return hours


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    commands = root.add_subparsers(dest="mode", required=True)
    local = commands.add_parser("local", help="watch an explicit local Service 4 socket")
    local.add_argument("--host-scope", required=True)
    local.add_argument("--socket", type=Path, required=True)
    local.add_argument("--duration", type=float, default=5.0)
    mesh = commands.add_parser("mesh", help="watch an explicit Agent working-set source")
    mesh.add_argument("--host", required=True)
    mesh.add_argument("--source", required=True)
    mesh.add_argument("--socket", type=Path, required=True)
    mesh.add_argument("--scope", choices=("local", "hosts"), default="hosts")
    mesh.add_argument("--window-hours", type=window_hours, default=72)
    mesh.add_argument("--duration", type=float, default=5.0)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        validate_duration(args.duration)
        if args.mode == "local":
            return run_local(host=args.host_scope, socket_path=args.socket, duration=args.duration)
        return asyncio.run(
            run_mesh(
                host=args.host,
                source=args.source,
                socket_path=args.socket,
                scope=args.scope,
                window_ms=args.window_hours * 60 * 60 * 1000,
                duration=args.duration,
            )
        )
    except (ValueError, OSError) as error:
        print(
            json.dumps(
                {"example": "agent-observer.current-summary.v1", "failure": failure_code(error)}
            )
        )
        return 2


if __name__ == "__main__":
    sys.exit(main())
