"""Executable provisional Claude snapshot with independently verified artifact.

Reads installed bytes and private metadata only. This module never invokes
Claude, its roster or a supervisor. It is a study boundary, not a public API.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import socket
import stat
import time
import unicodedata
import uuid
from pathlib import Path

from .activity import unavailable
from .claude_history import SDK_VERSION as CLAUDE_HISTORY_SDK_VERSION
from .claude_history import collect_saved_history
from .claude_metadata import snapshot
from .claude_saved_identity import saved_ids
from .native_artifacts import inspect_installed
from .observation_model import bounded_native_title

_SCOPE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,255}\Z", re.ASCII)
_UUID = re.compile(r"[0-9a-fA-F]{8}(?:-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}\Z", re.ASCII)
# Separate native BG work/completion and held-approval cases passed; general
# questions, worker requests, failure and cancellation have their own gates.
ACCEPTED_WORK_VALUES = frozenset({"working", "settled", "needs_input"})
ACCEPTED_WAIT_REASONS = frozenset({"approval"})


class CollectionError(ValueError):
    """Finite failure code, without inspected native contents."""


def _verify_artifact(path: Path, *, timeout: float = 3.0, cache=None):
    try:
        return inspect_installed(path, "claude", timeout=timeout, cache=cache)
    except ValueError as exc:
        raise CollectionError(str(exc)) from None


def _namespace(config_home: Path, config_home_kind: str = "explicit"):
    try:
        values = [str(config_home), config_home_kind] + [
            os.readlink(f"/proc/self/ns/{name}") for name in ("user", "mnt", "pid")
        ]
        boot_id = Path("/proc/sys/kernel/random/boot_id").read_text().strip()
    except OSError:
        raise CollectionError("namespace_provenance_unavailable") from None
    if not _UUID.fullmatch(boot_id):
        raise CollectionError("namespace_provenance_unavailable")
    return "sha256:" + hashlib.sha256("\x00".join(values).encode()).hexdigest(), boot_id


def collect_claude(
    config_home: Path,
    *,
    host_scope: str,
    executable: Path = Path("/opt/claude-code/bin/claude"),
    include_history: bool = True,
    image_cache=None,
    owned_worker_group: bool = False,
    config_home_kind: str | None = None,
):
    if (
        type(include_history) is not bool
        or type(owned_worker_group) is not bool
        or config_home_kind is not None and (
            not isinstance(config_home_kind, str) or config_home_kind not in {"default", "explicit"}
        )
        or not isinstance(config_home, Path)
        or not config_home.is_absolute()
        or len(str(config_home)) > 4096
        or any(unicodedata.category(c).startswith("C") for c in str(config_home))
        or not isinstance(host_scope, str)
        or not _SCOPE.fullmatch(host_scope)
        or not isinstance(executable, Path)
        or not executable.is_absolute()
    ):
        raise CollectionError("invalid_collection_scope")
    started = time.monotonic()
    config_home_kind = config_home_kind or (
        "default"
        if config_home == Path.home() / ".claude" and "CLAUDE_CONFIG_DIR" not in os.environ
        else "explicit"
    )
    result = {
        "schemaVersion": 1,
        "collectionId": str(uuid.uuid4()),
        "collectedAt": time.time_ns() // 1_000_000,
        "host": {
            "authority": host_scope,
            "authoritySource": "caller",
            "nativeHostname": socket.gethostname(),
            "uid": os.geteuid(),
        },
        "provider": "claude",
        "configHome": str(config_home),
        "configHomeKind": config_home_kind,
        "sessions": [],
        "coverage": {"saved": {"complete": False, "reason": "not_observed"}},
        "limitations": [
            "study_contract",
            "private_required_contract",
            "one_configured_namespace",
            "no_watch",
            "saved_history_metadata_only",
            "current_client_not_observed",
        ],
        "errors": [],
        "sourceHealth": "unavailable",
    }
    try:
        if config_home.resolve(strict=True) != config_home:
            raise CollectionError("unsupported_namespace")
        root_stat = config_home.stat()
        if not stat.S_ISDIR(root_stat.st_mode) or root_stat.st_uid != os.geteuid():
            raise CollectionError("config_ownership_mismatch")
        namespace, boot_id = _namespace(config_home, config_home_kind)
        result["namespace"] = namespace
        installed_issue = None
        # Direct reads share only within this collection. Owned service workers
        # may supply a bounded descriptor-anchored memo; all current guards stay.
        image_cache = {} if image_cache is None else image_cache
        try:
            artifact_identity = _verify_artifact(executable, cache=image_cache)
        except (CollectionError, OSError) as error:
            artifact_identity = None
            installed_issue = str(error) if isinstance(error, CollectionError) else "runtime_artifact_unavailable"
        result["runtime"] = {
            "version": artifact_identity.artifact.version,
            "versionEvidence": "verified_installed_executable_sha256",
            "binarySha256": artifact_identity.artifact.sha256,
            "bootId": boot_id,
            "topology": "private_session_registry_and_job_store",
        } if artifact_identity is not None else None
        native = snapshot(
            config_home,
            host_scope=host_scope,
            namespace=namespace,
            runtime_version=artifact_identity.artifact.version if artifact_identity is not None else "unknown",
            binary_sha256=artifact_identity.artifact.sha256 if artifact_identity is not None else None,
            image_cache=image_cache,
        )
        result["sessions"] = native["observations"]
        result["parkedSupported"] = native.get("parkedSupported") is True
        for row in result["sessions"]:
            accepted_wait_reasons = ACCEPTED_WAIT_REASONS | (
                {"question", "user_input"} if "input_wait" in row.get("phaseCapabilities", []) else set()
            )
            row["presenceKind"] = "os_worker"
            row["inventory"] = (
                "live"
                if row["presence"].get("value") == "present"
                else "retained_job"
                if row.get("job", {}).get("retained") is True
                else "registry"
            )
            if row["work"].get("value") not in ACCEPTED_WORK_VALUES | {"unknown"} or (
                row["work"].get("value") == "needs_input"
                and row.get("waitReason") not in accepted_wait_reasons
            ):
                row["work"] = {
                    "value": "unknown",
                    "observedAt": None,
                    "source": None,
                    "health": "unsupported",
                    "reason": "unsupported",
                }
                row["waitReason"] = "unknown"
        result["coverage"].update(native["coverage"])
        result["coverage"]["work"] = {
            "supportedValues": sorted(ACCEPTED_WORK_VALUES),
            "supportedWaitReasons": sorted(ACCEPTED_WAIT_REASONS | (
                {"question", "user_input"} if any("input_wait" in row.get("phaseCapabilities", [])
                                    for row in result["sessions"]) else set()
            )),
            "pendingValues": ["error", "interrupted"],
            "pendingWaitReasons": ["user_input", "worker_request", "sandbox_request"],
        }
        result["coverage"]["clientBinding"] = {
            "supported": False,
            "reason": "source_not_established",
        }
        result["errors"] = native["errors"]
        if installed_issue is not None:
            result["errors"].append({"code": installed_issue})
        result["limitations"] = list(dict.fromkeys(result["limitations"] + native["limitations"]))
        if artifact_identity is not None:
            try:
                current_artifact = executable.lstat()
                unchanged = stat.S_ISREG(current_artifact.st_mode) and (
                    current_artifact.st_dev, current_artifact.st_ino
                ) == artifact_identity.stamp
            except OSError:
                unchanged = False
            if not unchanged:
                # The installed CLI is not the executable of surviving workers.
                # Each worker was checked against its own kernel image/birth.
                result["runtime"] = None
                result["errors"].append({"code": "installed_image_changed"})
        complete = native["supported"] and all(
            native["coverage"][name] == "complete" for name in ("sessionRegistry", "jobStore")
        )
        result["sourceHealth"] = (
            "current"
            if complete and not result["errors"]
            else "partial"
            if native["supported"]
            and any(
                native["coverage"][name] in {"complete", "partial"}
                for name in ("sessionRegistry", "jobStore")
            )
            else "unavailable"
        )
    except (CollectionError, OSError) as exc:
        result["errors"] = [
            {"code": str(exc) if isinstance(exc, CollectionError) else "source_unavailable"}
        ]
        if result["sessions"]:
            result["sourceHealth"] = "stale"
            for row in result["sessions"]:
                for dimension in ("work", "presence", "attachment", "runtimeDisposition"):
                    evidence = row.get(dimension)
                    if isinstance(evidence, dict) and evidence.get("health") == "current":
                        if evidence.get("value") != "unknown":
                            evidence["lastKnownValue"] = evidence["value"]
                        evidence.update(value="unknown", health="stale", reason="observation_gap")

    # Saved history has its own failure and coverage boundary. A missing SDK,
    # oversized history tree, or failed metadata scan must not stale live
    # registry/job evidence above.
    identities = saved_ids(config_home, {r["identity"]["nativeId"] for r in result["sessions"]})
    for row in result["sessions"]:
        row["savedIdentity"] = row["identity"]["nativeId"] in identities
    if not include_history:
        history = {"rows": [], "coverage": {"complete": False, "reason": "not_observed"}, "errors": []}
    elif "namespace" in result:
        try:
            history = collect_saved_history(config_home, owned_worker_group=True) if owned_worker_group else collect_saved_history(config_home)
        except Exception:
            history = {
                "rows": [],
                "coverage": {"complete": False, "reason": "source_failed"},
                "errors": [{"code": "history_source_failed"}],
            }
    else:
        history = {
            "rows": [],
            "coverage": {"complete": False, "reason": "source_failed"},
            "errors": [{"code": "history_source_failed"}],
        }

    saved_coverage = history.get("coverage")
    if isinstance(saved_coverage, dict):
        result["coverage"]["saved"] = saved_coverage
    census = history.get("census") or {}
    for key, reason in (("sdk_omitted_ids", "history_sdk_candidates_omitted"),
                        ("unresolved_ids", "history_candidates_unresolved"),
                        ("resolved_companion_ids", "history_duplicate_companions"),
                        ("malformed_filename_ids", "history_invalid_filename_candidates")):
        if census.get(key, 0):
            result["limitations"].append(reason)
    for history_error in history.get("errors", []):
        if isinstance(history_error, dict) and isinstance(history_error.get("code"), str):
            if history_error not in result["errors"]:
                result["errors"].append(history_error)

    history_rows = history.get("rows", [])
    if isinstance(history_rows, list):
        live_by_id: dict[str, dict] = {}
        ambiguous_live_ids: set[str] = set()
        for row in result["sessions"]:
            native_ids = row.get("nativeIds", {})
            session_id = native_ids.get("sessionId") if isinstance(native_ids, dict) else None
            identity = row.get("identity", {})
            if (
                isinstance(session_id, str)
                and isinstance(identity, dict)
                and identity.get("nativeIdKind") == "session"
                and isinstance(identity.get("nativeId"), str)
                and identity["nativeId"].lower() == session_id.lower()
                and _UUID.fullmatch(session_id)
            ):
                normalized_id = session_id.lower()
                if normalized_id in live_by_id:
                    ambiguous_live_ids.add(normalized_id)
                    live_by_id.pop(normalized_id, None)
                elif normalized_id not in ambiguous_live_ids:
                    live_by_id[normalized_id] = row

        for history_row in history_rows:
            if not isinstance(history_row, dict):
                continue
            session_id = history_row.get("session_id")
            if not isinstance(session_id, str) or not _UUID.fullmatch(session_id):
                continue
            session_id = session_id.lower()
            if session_id in ambiguous_live_ids:
                if {"code": "history_ambiguous"} not in result["errors"]:
                    result["errors"].append({"code": "history_ambiguous"})
                continue

            native = live_by_id.get(session_id)
            history_metadata = {
                "source": "claude_sdk",
                "sdkVersion": CLAUDE_HISTORY_SDK_VERSION,
                "createdAt": history_row.get("created_at"),
                "fileModifiedAt": history_row.get("last_modified"),
            }
            if native is not None:
                native["history"] = history_metadata
                native["threadKind"] = history_row.get("kind", "unknown")
                native["activity"] = history_row.get(
                    "activity", unavailable("activity_clock_unavailable")
                )
                fallback_title = "Claude " + session_id
                custom_title = history_row.get("custom_title")
                if native.get("title") == fallback_title and isinstance(custom_title, str):
                    native["title"] = bounded_native_title(custom_title, fallback_title)
                continue

            custom_title = history_row.get("custom_title")
            title = bounded_native_title(custom_title, "Claude " + session_id)
            cwd = history_row.get("cwd")
            result["sessions"].append(
                {
                    "identity": {
                        "hostScope": host_scope,
                        "provider": "claude",
                        "namespace": result["namespace"],
                        "nativeIdKind": "session",
                        "nativeId": session_id,
                    },
                    "work": {
                        "value": "unknown",
                        "observedAt": None,
                        "source": None,
                        "health": "unavailable",
                        "reason": "unobserved",
                    },
                    "presence": {
                        "value": "unknown",
                        "observedAt": None,
                        "source": None,
                        "health": "unavailable",
                        "reason": "unobserved",
                    },
                    "attachment": {
                        "value": "unknown",
                        "observedAt": None,
                        "source": None,
                        "health": "unsupported",
                        "reason": "unsupported",
                    },
                    "nativeIds": {"sessionId": session_id, "jobId": None},
                    "title": title,
                    "sessionKind": "unknown",
                    "nativeStatus": {"value": "unknown", "observedAt": None},
                    "job": None,
                    "waitReason": "unknown",
                    "cwd": cwd,
                    "cwdSource": "claude_history" if isinstance(cwd, str) else None,
                    "metadataIssues": [],
                    "history": history_metadata,
                    "activity": history_row.get(
                        "activity", unavailable("activity_clock_unavailable")
                    ),
                    "inventory": "saved",
                    "threadKind": history_row.get("kind", "unknown"),
                }
            )
    result["durationMs"] = round((time.monotonic() - started) * 1000, 3)
    # History and runtime are independent observations. A failed runtime
    # fingerprint cannot stale newly read, identity-checked saved metadata.
    # Each live fact retains its own failed/stale health and action guard.
    if history_rows and result["sourceHealth"] in {"unavailable", "stale"}:
        result["sourceHealth"] = "partial"
    result["activitySupported"] = True
    for row in result["sessions"]:
        row.setdefault("activity", unavailable("conversation_metadata_not_persisted"))
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host-scope", required=True)
    parser.add_argument(
        "--claude-home",
        type=Path,
        default=Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude"))),
    )
    args = parser.parse_args()
    try:
        value = collect_claude(args.claude_home, host_scope=args.host_scope)
    except CollectionError as exc:
        parser.error(str(exc))
    print(json.dumps(value, ensure_ascii=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
