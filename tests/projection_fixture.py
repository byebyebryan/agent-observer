"""Historical projection-shaped supplied data for current working-set tests."""
import copy
import json
import os
from pathlib import Path

from test_service_state import provider_snapshot as _provider_snapshot

from agent_observer.contract import store_namespace
from agent_observer.sync_projection_schema import SELECTOR, SELECTOR_DIGEST

ROOT = Path(__file__).resolve().parent.parent

def support(value, component="runtime"):
    source = value["sources"][0]
    receipt = next(c for c in source["components"] if c["name"] == component)
    return {
        "serviceId": value["serviceId"], "provider": source["provider"],
        "namespace": source["namespace"], "contextGeneration": source["contextGeneration"],
        "component": component, **{key: receipt[key] for key in (
            "accepted", "sampledBoottimeMs", "expiresBoottimeMs",
        )},
    }


def fixture():
    value = json.loads((ROOT / "tests/fixtures/service-v4/view.json").read_text())
    row = value.pop("snapshot")["sessions"][0]
    value.pop("serviceProtocol")
    value["sources"] = value["sources"][:1]
    value.update(activeFeedProtocol=1, selector=copy.deepcopy(SELECTOR), selectorDigest=SELECTOR_DIGEST)
    runtime = support(value)
    fields = dict.fromkeys((
        "runtime", "phase", "kind", "savedIdentity", "activity", "outcome", "workspace",
        "lastUpdated", "latestTurn",
    ))
    fields.update(runtime=copy.deepcopy(runtime), phase=copy.deepcopy(runtime), kind=copy.deepcopy(runtime))
    source = value["sources"][0]
    value["projection"] = {
        "scopes": [{
            "provider": "codex", "namespace": source["namespace"],
            "contextGeneration": source["contextGeneration"], "continuity": 1,
            "coverage": {"status": "complete", "reason": "daemon_threads_complete", "supports": [runtime]},
            "members": [{"identity": copy.deepcopy(row["identity"]), "fieldSupports": fields}],
            "uncertain": [], "nonmembers": [],
        }],
        "sessions": [row],
    }
    return value


def uncertain(value):
    scope = value["projection"]["scopes"][0]
    row = value["projection"]["sessions"].pop()
    scope["members"].clear()
    scope["coverage"].update(status="partial", reason="native_status_unresolved")
    prior = support(value)
    prior.update(accepted=1, sampledBoottimeMs=1000, expiresBoottimeMs=14000)
    entry = {
        "identity": row["identity"], "reason": "native_status_unresolved",
        "priorSupport": prior, "support": support(value), "horizonBoottimeMs": 14000,
    }
    scope["uncertain"].append(entry)
    return entry


def provider_snapshot(provider):
    value = _provider_snapshot(provider)
    value["sessions"] = value["sessions"][:1]
    return value


def local_uid(value):
    """Keep strict fixtures usable through the current user's protected socket."""
    value["uid"] = os.geteuid()
    namespaces = {
        source["namespace"]: store_namespace(source["provider"], source["configHome"],
                                             source["configHomeKind"], os.geteuid())
        for source in value["sources"]
    }
    def visit(item):
        if isinstance(item, dict):
            if "namespace" in item:
                item["namespace"] = namespaces.get(item["namespace"], item["namespace"])
            if "uid" in item:
                item["uid"] = os.geteuid()
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
    visit(value)
    return value

