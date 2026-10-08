"""Passive exact-reference reads for the separately gated Codex write client.

No discovery display cap, private store fallback, provider startup or actions.
"""

import os
import socket
import time
import uuid
from pathlib import Path

from .activity import codex_activity, codex_outcome, unavailable
from .codex_endpoint import inspect_managed_endpoint, validate_incarnation
from .codex_metadata import MetadataError, live_thread_metadata
from .codex_snapshot import _namespace
from .codex_transport import PassiveClient, TransportError
from .collection import compose_snapshot


def _readable_saved_history(summary, turns):
    """Positive stored-history proof, independent of nonempty turns or clocks.

    A non-ephemeral summary may still be an unmaterialized blank context.
    The exact metadata-only history RPC must also succeed with bounded items.
    Neither the unstable native path nor a local file is an observation input.
    """
    if summary.get("ephemeral") is not False or not isinstance(turns, dict):
        return False
    data = turns.get("data")
    return isinstance(data, list) and len(data) <= 1 and all(
        isinstance(turn, dict) and turn.get("itemsView") == "notLoaded" and turn.get("items") == []
        for turn in data
    )


def collect_exact(config_home, *, host_scope, thread_id):
    home = Path(config_home)
    peer = inspect_managed_endpoint(home, timeout=3)
    namespace, boot = _namespace(home, peer.pid)
    with PassiveClient.connect(peer.endpoint, expected_uid=peer.uid, expected_pid=peer.pid, timeout=5) as client:
        initialized = client.initialize()
        if not isinstance(initialized, dict) or initialized.get("codexHome") != str(home):
            raise MetadataError("runtime_namespace_mismatch")
        response = client.read_thread(thread_id)
        if not isinstance(response, dict):
            raise MetadataError("invalid_thread_metadata")
        payload = response.get("thread")
        row = live_thread_metadata(payload, host_scope=host_scope, namespace=namespace,
                                   runtime_version=peer.version, observed_at=time.time_ns() // 1_000_000)
        if row["identity"]["nativeId"] != thread_id:
            raise MetadataError("native_identity_mapping_conflict")
        row["savedIdentity"] = False
        try:
            turns = client.latest_turn(thread_id)
            row["savedIdentity"] = _readable_saved_history(payload, turns)
            row["activity"] = codex_activity(turns, completion_only=True)
            row["outcome"] = codex_outcome(turns, completion_only=True)
        except TransportError:
            row["activity"] = unavailable("native_turn_read_unavailable")
        if row["runtimeDisposition"]["value"] == "parked" and not row["savedIdentity"]:
            row["runtimeDisposition"].update(value="unknown", health="unavailable", reason="saved_identity_unavailable")
        validate_incarnation(peer)
    source = {
        "provider": "codex", "configHome": str(home), "configHomeKind": "explicit",
        "namespace": namespace, "host": {"authority": host_scope, "uid": os.geteuid(), "nativeHostname": socket.gethostname()},
        "collectionId": str(uuid.uuid4()), "sessions": [row], "sourceHealth": "partial", "errors": [],
        "runtime": {"version": peer.version, "binarySha256": peer.binary_sha256,
                    "topology": "native_managed_endpoint", "bootId": boot, "pid": peer.pid,
                    "startTicks": peer.start_ticks, "endpoint": peer.endpoint},
        "discovery": {"catalogMode": "exact_reference", "sourceKinds": [],
                      "catalogRows": 0, "runtimeRows": 1, "parkedRows": 1,
                      "pages": 0, "nativeMessageBytes": 2 * 1024 * 1024, "historyClocks": True},
        "coverage": {"saved": {"complete": False, "reason": "exact_reference"},
                     "daemon": {"complete": False, "reason": "exact_reference"},
                     "work": {"supported": True}},
        "activitySupported": row["activity"]["health"] == "current", "limitations": ["exact_reference_only"],
    }
    return compose_snapshot(host_scope=host_scope, provider_snapshots=[source])
