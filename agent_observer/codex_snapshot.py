"""Executable, provisional host-local Codex snapshot study.

No provider is invoked or started. The output reports source facts and pending
semantic coverage explicitly; public consumers use the separate v2 projection.
Exact artifact/capability gates and independently proved saved-store reads remain
enforced below.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import sqlite3
import time
import unicodedata
import uuid
from pathlib import Path

from .activity import codex_activity, codex_outcome, ordering, unavailable
from .codex_endpoint import (
    EndpointError,
    inspect_managed_endpoint,
    validate_incarnation,
)
from .codex_metadata import MetadataError, live_thread_metadata, saved_thread_metadata
from .codex_saved import collect_saved
from .codex_transport import PassiveClient, TransportError
from .native_artifacts import CODEX, registered

VERSION = CODEX.version
RELEASE = VERSION + "-x86_64-unknown-linux-musl"
BINARY_SHA256 = CODEX.sha256
# Native 0.160.0 managed-runtime proof: 33 RPC observations overlapped a
# verified running disposable tool; all were active with an empty flags list.
# The same native series supplied idle before/after successful completion.
# A separate native on-request/workspace-write client held an approval with
# waitingOnApproval; operator denial returned it to idle without a write.
# Other waiting/error semantics have separate gates below.
WORK_STATE_ACCEPTED = True
ACCEPTED_WORK_VALUES = frozenset({"working", "settled", "needs_input"})
ACCEPTED_WAIT_FLAGS = frozenset({"waitingOnApproval"})
_UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z", re.ASCII)
_SCOPE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,255}\Z", re.ASCII)


class SnapshotError(ValueError):
    """Finite source/coverage error, never raw native data."""


def _page(value, *, loaded=False):
    if not isinstance(value, dict) or not isinstance(value.get("data"), list):
        raise SnapshotError("invalid_inventory_page")
    cursor = value.get("nextCursor")
    if cursor is not None and (not isinstance(cursor, str) or not 0 < len(cursor) <= 4096):
        raise SnapshotError("invalid_inventory_cursor")
    if len(value["data"]) > 10000:
        raise SnapshotError("inventory_page_limit")
    if loaded and any(
        not isinstance(item, str) or not _UUID.fullmatch(item) for item in value["data"]
    ):
        raise SnapshotError("invalid_loaded_identity")
    return value["data"], cursor


def _clock():
    return int(time.time() * 1000)


def _namespace(config_home, pid):
    values = [str(config_home)]
    try:
        for name in ("user", "mnt", "pid"):
            values.append(os.readlink(Path("/proc") / str(pid) / "ns" / name))
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        raise SnapshotError("namespace_provenance_unavailable") from None
    if not _UUID.fullmatch(boot_id):
        raise SnapshotError("namespace_provenance_unavailable")
    return "sha256:" + hashlib.sha256("\x00".join(values).encode()).hexdigest(), boot_id


def collect_codex(
    config_home: Path,
    *,
    host_scope: str,
    history_limit: int = 100,
    live_limit: int = 512,
    timeout: float = 10.0,
):
    if (
        not isinstance(config_home, Path)
        or not config_home.is_absolute()
        or len(str(config_home)) > 4096
        or any(unicodedata.category(char).startswith("C") for char in str(config_home))
        or not isinstance(host_scope, str)
        or not _SCOPE.fullmatch(host_scope)
        or type(history_limit) is not int
        or not 1 <= history_limit <= 1000
        or type(live_limit) is not int
        or not 1 <= live_limit <= 2048
        or type(timeout) not in (int, float)
        or not 1 <= timeout <= 30
    ):
        raise SnapshotError("invalid_collection_scope")
    started = time.monotonic()
    deadline = started + timeout
    result = {
        "schemaVersion": 1,
        "collectionId": str(uuid.uuid4()),
        "collectedAt": _clock(),
        "host": {
            "authority": host_scope,
            "authoritySource": "caller",
            "nativeHostname": socket.gethostname(),
            "uid": os.geteuid(),
        },
        "provider": "codex",
        "activitySupported": False,
        "configHome": str(config_home),
        "sessions": [],
        "coverage": {
            "saved": {"complete": False, "reason": "not_observed"},
            "loaded": {"complete": False, "reason": "not_observed"},
            "work": {
                "supported": False,
                "reason": "not_observed",
                "supportedValues": [],
                "supportedWaitFlags": [],
                "pendingValues": ["interrupted", "error"],
                "pendingWaitFlags": ["waitingOnUserInput"],
            },
            "workerPresence": {"supported": False, "reason": "not_observed"},
            "clientBinding": {"supported": False, "reason": "source_not_established"},
        },
        "limitations": [
            "study_contract",
            "one_configured_namespace",
            "no_watch",
            "loaded_thread_is_not_worker_or_client_presence",
        ],
        "errors": [],
        "sourceHealth": "unavailable",
    }
    rows = {}
    runtime_rows_read = False

    def remaining():
        value = deadline - time.monotonic()
        if value <= 0:
            raise SnapshotError("collection_timeout")
        return min(5.0, value)

    def runtime_info(identity):
        namespace, boot_id = _namespace(config_home, identity.pid)
        result["namespace"] = namespace
        result["runtime"] = {
            "version": identity.version,
            "versionEvidence": "verified_executable_sha256"
            if registered("codex", identity.binary_sha256) else "unaccepted_release_path_and_sha256",
            "binarySha256": identity.binary_sha256,
            "pid": identity.pid,
            "startTicks": identity.start_ticks,
            "bootId": boot_id,
            "topology": "native_managed_endpoint",
            "endpoint": identity.endpoint,
        }

    try:
        identity = inspect_managed_endpoint(
            config_home,
            timeout=min(3.0, remaining()),
        )
        runtime_info(identity)
        profile = registered("codex", identity.binary_sha256)
        work_supported = WORK_STATE_ACCEPTED and profile is not None and "managed_work" in profile.capabilities
        wait_flags = ACCEPTED_WAIT_FLAGS if profile is not None and "managed_approval" in profile.capabilities else frozenset()
        if profile is not None and "managed_question" in profile.capabilities:
            wait_flags |= {"waitingOnUserInput"}
        result["activitySupported"] = profile is not None and "managed_activity" in profile.capabilities
        result["coverage"]["work"].update(
            supported=work_supported,
            reason="native_proof" if work_supported else "native_transition_proof_pending",
            supportedValues=sorted(ACCEPTED_WORK_VALUES) if work_supported else [],
            supportedWaitFlags=sorted(wait_flags),
            pendingWaitFlags=sorted({"waitingOnUserInput"} - wait_flags),
        )
        scope = {
            "host_scope": host_scope,
            "namespace": result["namespace"],
            "runtime_version": identity.version,
        }
        with PassiveClient.connect(
            identity.endpoint,
            expected_uid=identity.uid,
            expected_pid=identity.pid,
            timeout=remaining(),
        ) as client:
            initialized = client.initialize()
            if not isinstance(initialized, dict) or initialized.get("codexHome") != str(
                config_home
            ):
                raise SnapshotError("runtime_namespace_mismatch")
            # Read loaded inventory independently and before display-limited history.
            loaded = []
            cursor = None
            cursors = set()
            for _ in range(64):
                client.timeout = remaining()
                data, following = _page(client.loaded_threads(cursor=cursor), loaded=True)
                loaded.extend(item.lower() for item in data)
                if len(set(loaded)) != len(loaded):
                    raise SnapshotError("loaded_identity_ambiguous")
                if len(loaded) > live_limit:
                    loaded = loaded[:live_limit]
                    result["coverage"]["loaded"] = {
                        "complete": False,
                        "reason": "live_limit",
                    }
                    break
                if following is None:
                    result["coverage"]["loaded"] = {
                        "complete": True,
                        "reason": "native_snapshot",
                    }
                    break
                if following in cursors:
                    raise SnapshotError("inventory_cursor_cycle")
                cursors.add(following)
                cursor = following
            else:
                raise SnapshotError("inventory_page_limit")
            for identifier in loaded:
                try:
                    client.timeout = remaining()
                    response = client.read_thread(identifier)
                    if not isinstance(response, dict) or not isinstance(response.get("thread"), dict):
                        raise MetadataError("loaded_row_metadata_unavailable")
                    returned_id = response["thread"].get("id")
                    if isinstance(returned_id, str) and _UUID.fullmatch(returned_id) and returned_id.lower() != identifier:
                        raise SnapshotError("loaded_read_identity_conflict")
                    row = live_thread_metadata(response["thread"], **scope, observed_at=_clock())
                except (TransportError, MetadataError) as error:
                    issue = {"code": str(error)}
                    if issue not in result["errors"]:
                        result["errors"].append(issue)
                    result["coverage"]["loaded"] = {"complete": False, "reason": "loaded_row_unavailable"}
                    continue
                row["presenceKind"] = "server_thread_loaded"
                if (
                    not work_supported
                    or row["work"]["value"] not in ACCEPTED_WORK_VALUES
                    or (
                        row["work"]["value"] == "needs_input"
                        and not set(row["nativeState"]["activeFlags"]).issubset(wait_flags)
                    )
                ):
                    row["work"] = {
                        "value": "unknown",
                        "observedAt": None,
                        "source": None,
                        "health": "unsupported",
                        "reason": "unsupported",
                    }
                    row["waitReason"] = "unknown"
                rows[identifier] = row
            runtime_rows_read = True
            cursor = None
            cursors = set()
            saved_count = 0
            saved_ids = set()
            catalog_limit = 1000
            for _ in range(64):
                client.timeout = remaining()
                data, following = _page(
                    client.list_threads(cursor=cursor, limit=min(100, catalog_limit - saved_count))
                )
                if len(data) > catalog_limit - saved_count:
                    data = data[: catalog_limit - saved_count]
                    following = following or "display_limit"
                for payload in data:
                    row = saved_thread_metadata(payload, **scope)
                    identifier = row["identity"]["nativeId"]
                    if identifier in saved_ids:
                        raise SnapshotError("saved_identity_ambiguous")
                    saved_ids.add(identifier)
                    existing = rows.get(identifier)
                    if existing and existing["nativeIds"] != row["nativeIds"]:
                        raise SnapshotError("native_identity_mapping_conflict")
                    rows.setdefault(identifier, row)
                saved_count += len(data)
                if following is None:
                    result["coverage"]["saved"] = {
                        "complete": True,
                        "reason": "native_snapshot",
                    }
                    break
                if saved_count >= catalog_limit:
                    result["coverage"]["saved"] = {
                        "complete": False,
                        "reason": "catalog_limit",
                    }
                    break
                if following in cursors:
                    raise SnapshotError("inventory_cursor_cycle")
                cursors.add(following)
                cursor = following
            else:
                raise SnapshotError("inventory_page_limit")
            # Fetch a bounded metadata-only clock before applying the display
            # cap. Neither thread recency nor file modification substitutes for
            # conversation completion. A clock failure cannot erase live facts.
            for identifier, row in rows.items():
                try:
                    client.timeout = remaining()
                    turn_metadata = client.latest_turn(identifier) if result["activitySupported"] else None
                    row["activity"] = codex_activity(
                        turn_metadata,
                        completion_only=profile is not None and "completion_only_activity" in profile.capabilities,
                    ) if result["activitySupported"] else unavailable("activity_source_unproved", "unsupported")
                    if profile is not None and "managed_outcome" in profile.capabilities:
                        row["outcome"] = codex_outcome(
                            turn_metadata, completion_only="completion_only_activity" in profile.capabilities,
                        )
                except (TransportError, SnapshotError) as error:
                    row["activity"] = unavailable(str(error))
            selected = sorted((rows[identifier] for identifier in saved_ids), key=ordering)[
                :history_limit
            ]
            selected_ids = {row["identity"]["nativeId"] for row in selected} | set(loaded)
            if len(saved_ids) > history_limit:
                result["coverage"]["saved"] = {"complete": False, "reason": "history_limit"}
            rows = {
                identifier: row for identifier, row in rows.items() if identifier in selected_ids
            }
            validate_incarnation(identity)
            result["ignoredMessages"] = client.ignored_messages
            result["sourceHealth"] = "partial" if result["errors"] else "current"
    except (EndpointError, TransportError, MetadataError, SnapshotError) as error:
        if isinstance(error, EndpointError) and error.identity is not None:
            try:
                runtime_info(error.identity)
            except SnapshotError:
                pass
        result["errors"].append({"code": str(error)})
        # History is an independent dimension. A malformed/capped/failed
        # history read cannot erase successfully read live facts while the
        # owning runtime incarnation is still verified. Identity conflicts
        # and failed incarnation checks invalidate them.
        preserve_runtime = runtime_rows_read and str(error) not in {
            "native_identity_mapping_conflict",
            "saved_identity_ambiguous",
            "loaded_read_identity_conflict",
            "runtime_incarnation_changed",
            "runtime_incarnation_unavailable",
            "endpoint_incarnation_changed",
        }
        if preserve_runtime:
            try:
                validate_incarnation(identity)
            except EndpointError:
                preserve_runtime = False
        if not preserve_runtime:
            for row in rows.values():
                for dimension in ("work", "presence", "attachment"):
                    evidence = row[dimension]
                    if evidence["value"] != "unknown":
                        evidence["lastKnownValue"] = evidence["value"]
                    evidence.update(value="unknown", health="stale", reason="observation_gap")
            result["coverage"]["loaded"] = {"complete": False, "reason": "source_failed"}
        result["sourceHealth"] = (
            "partial" if preserve_runtime else "stale" if rows else "unavailable"
        )
        result["coverage"]["saved"] = {"complete": False, "reason": "source_failed"}
    if result["coverage"]["saved"].get("reason") == "source_failed":
        # This is the current metadata store, not a spawned legacy backend.
        # Its exact migration/schema/identity proof is independent of the peer.
        try:
            namespace = result.setdefault("namespace", "sha256:" + hashlib.sha256(
                (str(config_home) + "\0saved_metadata\0" + str(os.geteuid())).encode()
            ).hexdigest())
            saved = collect_saved(config_home, host_scope=host_scope, namespace=namespace,
                                  history_limit=history_limit)
            for row in saved["sessions"]:
                identifier = row["identity"]["nativeId"]
                existing = rows.get(identifier)
                if existing and existing["nativeIds"] != row["nativeIds"]:
                    existing["metadataIssues"].append("saved_identity_conflict")
                    continue
                if existing:
                    existing["activity"] = row["activity"]
                else:
                    rows[identifier] = row
            result["coverage"]["saved"] = saved["coverage"]
            result["activitySupported"] = saved["activitySupported"]
            result["errors"].extend({"code": issue} for issue in saved["issues"])
            if rows:
                result["sourceHealth"] = "partial"
        except (ValueError, OSError, sqlite3.Error):
            result["errors"].append({"code": "saved_metadata_unavailable"})
    result["sessions"] = list(rows.values())
    result["collectedAt"] = _clock()
    result["durationMs"] = round((time.monotonic() - started) * 1000, 3)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-scope", required=True)
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))),
    )
    parser.add_argument("--history-limit", type=int, default=100)
    parser.add_argument("--live-limit", type=int, default=512)
    arguments = parser.parse_args()
    try:
        value = collect_codex(
            arguments.codex_home,
            host_scope=arguments.host_scope,
            history_limit=arguments.history_limit,
            live_limit=arguments.live_limit,
        )
    except SnapshotError:
        print('{"schemaVersion":1,"error":"invalid_collection_scope"}')
        return 2
    print(json.dumps(value, ensure_ascii=True, separators=(",", ":"), allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
