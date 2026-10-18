"""Unreleased working-set native candidate; pure strict replacement admission.

SDK/profile registration and schema freeze are separate owning gates. Frozen
active/full protocols and their API4 row schema are unchanged.
"""

from __future__ import annotations

import copy
import hashlib

from .active_contract import (
    FACT_SUPPORT,
    FIELD_SUPPORTS,
    MAX_FRAME_BYTES,
    MAX_IDENTITIES,
    MAX_LEDGER_BYTES,
    MAX_OVERHEAD_BYTES,
    MAX_REQUEST_BYTES,
    NULL_SUPPORT,
    POSITIVE_INTEGER,
    UNCERTAIN,
    _current_support,
    _identity,
    _sources,
    _support_scope,
    _support_set,
)
from .bounded_json import decode_document
from .contract import (
    CODE,
    DIGEST,
    IDENTITY,
    INTEGER,
    LATEST_TURN,
    MAX_NODES,
    SESSION,
    TIME,
    UUID,
    ContractError,
    _validate_record_semantics,
    array,
    canonical,
    choice,
    identity_key,
    obj,
    text,
    validate_shape,
)
from .service_contract import FRAME as SERVICE_FRAME
from .service_contract import SOURCE
from .working_set_policy import DEFAULT_WINDOW_MS, MAX_WINDOW_MS

WORKING_SET_PROTOCOL = 1
OPERATIONS = ("status", "snapshot", "watch")
MAX_SAFE_INTEGER = 2**53 - 1
SIGNED = {"type": "integer", "minimum": -MAX_SAFE_INTEGER, "maximum": MAX_SAFE_INTEGER}
OPTIONAL_SIGNED = {"anyOf": [SIGNED, {"type": "null"}]}
CLOCK_REF = obj(component=choice("runtime", "history"), accepted=POSITIVE_INTEGER)
OPTIONAL_CLOCK = {"anyOf": [CLOCK_REF, {"type": "null"}]}
CLOCK_SAMPLE = obj(
    component=choice("runtime", "history"),
    accepted=POSITIVE_INTEGER,
    sampleId=text(36, pattern=UUID),
    originComponent=choice("runtime", "history"),
    sampledBoottimeMs=INTEGER,
    wallMs={**INTEGER, "maximum": 4_000_000_000_000},
    acceptedBoottimeMs=INTEGER,
)
SELECTOR_SCHEMA = obj(
    version={"const": 1},
    providers={**array(choice("codex"), 1), "const": ["codex"]},
    kinds={**array(choice("unknown", "user"), 2), "const": ["unknown", "user"]},
    active=obj(
        runtimeValues={**array(choice("running"), 1), "const": ["running"]},
        runtimeHealths={**array(choice("current"), 1), "const": ["current"]},
    ),
    recent=obj(
        field={"const": "activity.at"},
        windowMs={**INTEGER, "maximum": MAX_WINDOW_MS},
        boundary={"const": "exclusive"},
        unknown={"const": "unresolved"},
    ),
)
ACTIVE_BRANCH = obj(supports=array(FACT_SUPPORT, 2))
RECENT_BRANCH = obj(
    supports=array(FACT_SUPPORT, 2),
    activityAt={**INTEGER, "maximum": 4_000_000_000_000},
    clock=CLOCK_REF,
    lowerBoottimeMs=SIGNED,
    upperBoottimeMs=SIGNED,
)
MEMBER = obj(
    identity=IDENTITY,
    fieldSupports=FIELD_SUPPORTS,
    active={"anyOf": [ACTIVE_BRANCH, {"type": "null"}]},
    recent={"anyOf": [RECENT_BRANCH, {"type": "null"}]},
)
NO_ACTIVITY = obj(
    field={"const": "latestTurn"},
    latestTurn=LATEST_TURN,
    activity=obj(
        at={"const": None},
        source={"const": None},
        health={"const": "unavailable"},
        reason={"const": "no_conversation_activity"},
    ),
)
NEGATIVE_RECENT = obj(
    kind=choice("window_disabled", "outside_window", "no_activity"),
    support=NULL_SUPPORT,
    clock=OPTIONAL_CLOCK,
    activityAt=TIME,
    lowerBoottimeMs=OPTIONAL_SIGNED,
    upperBoottimeMs=OPTIONAL_SIGNED,
    absence={"anyOf": [NO_ACTIVITY, {"type": "null"}]},
)
NONMEMBER = obj(
    identity=IDENTITY,
    reason=choice("excluded_kind", "outside_window", "no_activity"),
    value=choice("child", "system", "parked"),
    supports=array(FACT_SUPPORT, 2),
    recent={"anyOf": [NEGATIVE_RECENT, {"type": "null"}]},
    horizonBoottimeMs=INTEGER,
)
SCOPE = obj(
    provider=choice("codex"),
    namespace=text(71, pattern=DIGEST),
    contextGeneration=INTEGER,
    continuity=POSITIVE_INTEGER,
    clocks=array(CLOCK_SAMPLE, 2),
    coverage=obj(
        status=choice("complete", "partial", "warming", "stale", "unavailable", "unsupported"),
        reason=text(128, pattern=CODE),
        supports=array(FACT_SUPPORT, 2),
    ),
    members=array(MEMBER, MAX_IDENTITIES),
    uncertain=array(UNCERTAIN, MAX_IDENTITIES),
    nonmembers=array(NONMEMBER, MAX_IDENTITIES),
)
PROJECTION = obj(scopes=array(SCOPE, 1), sessions=array(SESSION, MAX_IDENTITIES))
REQUEST = obj(
    workingSetProtocol={"const": WORKING_SET_PROTOCOL},
    operation=choice(*OPERATIONS),
    hostScope=copy.deepcopy(SERVICE_FRAME["properties"]["hostScope"]),
    selector=SELECTOR_SCHEMA,
    selectorDigest=text(71, pattern=DIGEST),
)
FRAME = copy.deepcopy(SERVICE_FRAME)
FRAME["properties"].pop("serviceProtocol")
FRAME["properties"].pop("snapshot")
FRAME["properties"].update(
    workingSetProtocol={"const": WORKING_SET_PROTOCOL},
    selector=SELECTOR_SCHEMA,
    selectorDigest=text(71, pattern=DIGEST),
    observationRevision=INTEGER,
    clockCeiling=OPTIONAL_SIGNED,
    clockGeneration=INTEGER,
    projection={"anyOf": [PROJECTION, {"type": "null"}]},
    sources=array(SOURCE, 1),
)
FRAME["required"] = list(FRAME["properties"])


def selector(window_ms=DEFAULT_WINDOW_MS):
    if type(window_ms) is not int or not 0 <= window_ms <= MAX_WINDOW_MS:
        raise ContractError("working_set_window_invalid")
    return {
        "version": 1,
        "providers": ["codex"],
        "kinds": ["unknown", "user"],
        "active": {"runtimeValues": ["running"], "runtimeHealths": ["current"]},
        "recent": {
            "field": "activity.at",
            "windowMs": window_ms,
            "boundary": "exclusive",
            "unknown": "unresolved",
        },
    }


def selector_digest(value):
    return "sha256:" + hashlib.sha256(canonical(value).encode()).hexdigest()


def interface(window_ms=DEFAULT_WINDOW_MS):
    policy = selector(window_ms)
    return {
        "workingSetProtocol": WORKING_SET_PROTOCOL,
        "stability": "unreleased-candidate",
        "observationApiVersion": 4,
        "hostLocal": True,
        "operations": list(OPERATIONS),
        "selector": policy,
        "selectorDigest": selector_digest(policy),
        "nativeEventReplay": False,
        "durableReplay": False,
        "limits": {
            "requestBytes": MAX_REQUEST_BYTES,
            "frameBytes": MAX_FRAME_BYTES,
            "envelopeBytes": MAX_OVERHEAD_BYTES,
            "ledgerBytes": MAX_LEDGER_BYTES,
            "identities": MAX_IDENTITIES,
        },
    }


def _policy(value, expected_window_ms=None):
    if expected_window_ms is not None:
        selector(expected_window_ms)
    window = value["selector"]["recent"]["windowMs"]
    if (
        canonical(value["selector"]) != canonical(selector(window))
        or value["selectorDigest"] != selector_digest(value["selector"])
        or expected_window_ms is not None
        and window != expected_window_ms
    ):
        raise ContractError("working_set_selector_mismatch")
    return window


def validate_request(value, *, expected_window_ms=None):
    validate_shape(value, REQUEST)
    _policy(value, expected_window_ms)
    if len(canonical(value).encode()) + 1 > MAX_REQUEST_BYTES:
        raise ContractError("working_set_request_limit")
    return value


def _clocks(scope, source, value):
    result, samples = {}, {}
    receipts = {r["name"]: r for r in source["components"]}
    for clock in scope["clocks"]:
        component = clock["component"]
        receipt = receipts[component]
        if (
            any(key[0] == component for key in result)
            or receipt["health"] not in {"current", "partial"}
            or clock["accepted"] != receipt["accepted"]
            or clock["sampledBoottimeMs"] != receipt["sampledBoottimeMs"]
            or not clock["sampledBoottimeMs"]
            <= clock["acceptedBoottimeMs"]
            <= value["emittedBoottimeMs"]
            or value["clockCeiling"] is None
            or value["clockCeiling"] < clock["wallMs"] - clock["sampledBoottimeMs"] + 1
        ):
            raise ContractError("working_set_clock_binding")
        original = tuple(
            clock[k]
            for k in (
                "sampleId",
                "originComponent",
                "sampledBoottimeMs",
                "wallMs",
                "acceptedBoottimeMs",
            )
        )
        prior = samples.get(clock["sampleId"])
        if prior is not None and prior != original:
            raise ContractError("working_set_mirrored_clock")
        samples[clock["sampleId"]] = original
        result[component, clock["accepted"]] = clock
    return result


def _bounds(at, ref, clock_ref, clocks, value, window):
    clock = clocks.get((clock_ref["component"], clock_ref["accepted"]))
    if (
        window == 0
        or clock is None
        or value["clockCeiling"] is None
        or (ref["component"], ref["accepted"]) != (clock_ref["component"], clock_ref["accepted"])
        or ref["sampledBoottimeMs"] != clock["sampledBoottimeMs"]
        or at > clock["wallMs"]
    ):
        raise ContractError("working_set_recent_clock")
    lower = at + window - value["clockCeiling"]
    upper = clock["acceptedBoottimeMs"] + window - (clock["wallMs"] - at) + 1
    if not (-MAX_SAFE_INTEGER <= lower <= upper <= MAX_SAFE_INTEGER):
        raise ContractError("working_set_cutoff_range")
    return lower, upper


def _required(refs, expected, source, scope, value):
    _support_set(refs, source, scope, value)
    if canonical(refs) != canonical(sorted(expected, key=lambda r: r["component"])):
        raise ContractError("working_set_branch_support")


def _member(row, metadata, source, scope, value, clocks, window):
    fields = metadata["fieldSupports"]
    for ref in fields.values():
        if ref is not None:
            _current_support(ref, source, scope, value)
    for name in ("runtime", "phase", "outcome", "activity", "lastUpdated", "latestTurn"):
        fact = row[name]
        if fact is not None and fact["health"] == "current" and fields[name] is None:
            raise ContractError("working_set_field_support")
    if row["kind"] not in {"unknown", "user"} or (
        row["kind"] != "unknown" and fields["kind"] is None
    ):
        raise ContractError("working_set_member_kind")
    if (
        row["workspace"] is not None
        and row["workspace"]["health"] == "current"
        and fields["workspace"] is None
    ):
        raise ContractError("working_set_field_support")
    if fields["workspace"] is not None and fields["workspace"]["component"] != "history":
        raise ContractError("working_set_workspace_support")
    if (
        row["phase"] is not None
        and row["phase"]["value"] != "unknown"
        and fields["phase"] != fields["runtime"]
    ):
        raise ContractError("working_set_phase_support")
    for name in ("lastUpdated", "latestTurn"):
        if row[name]["health"] != "current":
            continue
        binding, ref = row[name]["receipt"], fields[name]
        if (
            binding is None
            or any(
                binding[k] != ref[k]
                for k in (
                    "component",
                    "sampledBoottimeMs",
                    "contextGeneration",
                )
            )
            or not ref["sampledBoottimeMs"]
            <= binding["observedBoottimeMs"]
            <= value["emittedBoottimeMs"]
            or binding["observedBoottimeMs"] >= ref["expiresBoottimeMs"]
        ):
            raise ContractError("working_set_timing_support")
    kind = [] if row["kind"] == "unknown" else [fields["kind"]]
    active, recent = metadata["active"], metadata["recent"]
    if active is not None:
        runtime = fields["runtime"]
        if (
            runtime is None
            or runtime["component"] != "runtime"
            or row["runtime"]["value"] != "running"
            or row["runtime"]["health"] != "current"
        ):
            raise ContractError("working_set_active_branch")
        expected = {canonical(ref): ref for ref in [runtime, *kind]}
        _required(active["supports"], list(expected.values()), source, scope, value)
    if recent is not None:
        ref = fields["activity"]
        if (
            ref is None
            or row["activity"]["health"] != "current"
            or recent["activityAt"] != row["activity"]["at"]
        ):
            raise ContractError("working_set_recent_branch")
        expected = {canonical(r): r for r in [ref, *kind]}
        _required(recent["supports"], list(expected.values()), source, scope, value)
        bounds = _bounds(recent["activityAt"], ref, recent["clock"], clocks, value, window)
        if (
            bounds != (recent["lowerBoottimeMs"], recent["upperBoottimeMs"])
            or value["emittedBoottimeMs"] >= bounds[0]
        ):
            raise ContractError("working_set_recent_cutoff")
    if active is None and recent is None:
        raise ContractError("working_set_positive_missing")


def _nonmember(entry, source, scope, value, clocks, window):
    refs = entry["supports"]
    _support_set(refs, source, scope, value)
    if not refs:
        raise ContractError("working_set_negative_support")
    recent = entry["recent"]
    if entry["reason"] == "excluded_kind":
        if entry["value"] not in {"child", "system"} or recent is not None:
            raise ContractError("working_set_negative_kind")
        return
    if (
        entry["value"] != "parked"
        or not any(ref["component"] == "runtime" for ref in refs)
        or recent is None
    ):
        raise ContractError("working_set_negative_active")
    if recent["kind"] == "window_disabled":
        if (
            window != 0
            or entry["reason"] != "outside_window"
            or any(
                recent[k] is not None
                for k in (
                    "support",
                    "clock",
                    "activityAt",
                    "lowerBoottimeMs",
                    "upperBoottimeMs",
                    "absence",
                )
            )
        ):
            raise ContractError("working_set_negative_disabled")
        return
    ref = recent["support"]
    if ref is None or ref not in refs or recent["clock"] is None:
        raise ContractError("working_set_negative_recent")
    if recent["kind"] == "no_activity":
        clock = clocks.get((recent["clock"]["component"], recent["clock"]["accepted"]))
        if (
            entry["reason"] != "no_activity"
            or clock is None
            or ref["component"] != recent["clock"]["component"]
            or ref["accepted"] != recent["clock"]["accepted"]
            or ref["sampledBoottimeMs"] != clock["sampledBoottimeMs"]
            or any(
                recent[k] is not None for k in ("activityAt", "lowerBoottimeMs", "upperBoottimeMs")
            )
        ):
            raise ContractError("working_set_negative_absence")
        absence = recent["absence"]
        turn = None if absence is None else absence["latestTurn"]
        binding = None if turn is None else turn["receipt"]
        if (
            turn is None
            or turn["value"] is not None
            or turn["health"] != "current"
            or turn["reason"] != "no_native_turn"
            or turn["source"] is None
            or turn["observedAt"] is None
            or "lastKnownValue" in turn
            or binding is None
            or any(
                binding[k] != ref[k]
                for k in (
                    "component",
                    "sampledBoottimeMs",
                    "contextGeneration",
                )
            )
            or not ref["sampledBoottimeMs"]
            <= binding["observedBoottimeMs"]
            <= clock["acceptedBoottimeMs"]
            or binding["observedBoottimeMs"] >= ref["expiresBoottimeMs"]
        ):
            raise ContractError("working_set_negative_absence_binding")
    else:
        if (
            entry["reason"] != "outside_window"
            or recent["activityAt"] is None
            or recent["absence"] is not None
        ):
            raise ContractError("working_set_negative_recent")
        bounds = _bounds(recent["activityAt"], ref, recent["clock"], clocks, value, window)
        if (
            bounds != (recent["lowerBoottimeMs"], recent["upperBoottimeMs"])
            or value["emittedBoottimeMs"] < bounds[1]
        ):
            raise ContractError("working_set_negative_cutoff")


def validate_frame(value, *, expected_host=None, expected_uid=None, expected_window_ms=None):
    validate_shape(value, FRAME)
    window = _policy(value, expected_window_ms)
    if value["sequence"] < 1 or value["emittedAt"] is None:
        raise ContractError("working_set_sequence")
    if expected_host is not None and value["hostScope"] != expected_host:
        raise ContractError("working_set_host")
    if expected_uid is not None and value["uid"] != expected_uid:
        raise ContractError("working_set_uid")
    sources, projection = _sources(value), value["projection"]
    if value["kind"] in {"view", "resync"} and projection is None:
        raise ContractError("working_set_view_missing")
    if (
        value["kind"] in {"heartbeat", "gap", "error"} or value["state"] == "warming"
    ) and projection is not None:
        raise ContractError("working_set_view_unexpected")
    if projection is not None:
        scopes, members = {}, {}
        for scope in projection["scopes"]:
            key = scope["provider"], scope["namespace"]
            source = sources.get(scope["provider"])
            if (
                key in scopes
                or source is None
                or key[1] != source["namespace"]
                or scope["contextGeneration"] != source["contextGeneration"]
            ):
                raise ContractError("working_set_scope")
            clocks = _clocks(scope, source, value)
            scopes[key] = scope, source, clocks
            coverage = scope["coverage"]
            _support_set(
                coverage["supports"], source, scope, value, runtime=coverage["status"] == "complete"
            )
            runtime = next(r for r in source["components"] if r["name"] == "runtime")
            if coverage["status"] == "complete" and (
                scope["uncertain"] or runtime["health"] != "current"
            ):
                raise ContractError("working_set_complete_unresolved")
            seen = set()
            for name in ("members", "uncertain", "nonmembers"):
                for entry in scope[name]:
                    identity = _identity(entry["identity"], scope, value)
                    if identity in seen:
                        raise ContractError("working_set_duplicate_identity")
                    seen.add(identity)
                    if name == "members":
                        members[identity] = entry
                    elif name == "uncertain":
                        for field in ("priorSupport", "support"):
                            if entry[field] is not None:
                                _support_scope(entry[field], scope, value)
                        if (
                            entry["priorSupport"] is not None
                            and entry["horizonBoottimeMs"]
                            > entry["priorSupport"]["expiresBoottimeMs"]
                        ):
                            raise ContractError("working_set_uncertain_horizon")
                    else:
                        _nonmember(entry, source, scope, value, clocks, window)
            if len(seen) > MAX_IDENTITIES:
                raise ContractError("working_set_identity_limit")
        if set(scopes) != {(s["provider"], s["namespace"]) for s in sources.values()}:
            raise ContractError("working_set_scopes_missing")
        if len(canonical(projection["scopes"]).encode()) > MAX_LEDGER_BYTES:
            raise ContractError("working_set_ledger_limit")
        rows = set()
        for row in projection["sessions"]:
            identity = identity_key(row["identity"])
            if identity in rows or identity not in members:
                raise ContractError("working_set_member_body")
            rows.add(identity)
            key = row["identity"]["provider"], row["identity"]["namespace"]
            if key not in scopes:
                raise ContractError("working_set_scope")
            scope, source, clocks = scopes[key]
            # The projected frame intentionally carries receipt metadata, not
            # full-inventory capabilities. Field support is validated below.
            _validate_record_semantics(row, value["hostScope"], scopes, check_capabilities=False)
            _member(row, members[identity], source, scope, value, clocks, window)
        if rows != members.keys():
            raise ContractError("working_set_member_body")
    if len(canonical({**value, "projection": None}).encode()) + 1 > MAX_OVERHEAD_BYTES:
        raise ContractError("working_set_overhead_limit")
    if len(canonical(value).encode()) + 1 > MAX_FRAME_BYTES:
        raise ContractError("working_set_frame_limit")
    return value


def schema_document(kind):
    if kind not in {"request", "frame"}:
        raise ContractError("working_set_schema_kind")
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$id": f"urn:agent-observer:working-set-{kind}:{WORKING_SET_PROTOCOL}",
        **copy.deepcopy(REQUEST if kind == "request" else FRAME),
    }


def parse_request(data, **expected):
    return validate_request(
        decode_document(
            data, max_bytes=MAX_REQUEST_BYTES, max_nodes=128, max_depth=8, line_framed=True
        ),
        **expected,
    )


def parse_frame(data, **expected):
    return validate_frame(
        decode_document(
            data,
            max_bytes=MAX_FRAME_BYTES,
            max_nodes=MAX_NODES + 4096,
            max_depth=36,
            line_framed=True,
        ),
        **expected,
    )


class StreamGuard:
    """One native stream, including clock authority across scope retirement.

    A reconnect needs a new guard and independent baseline/proof. Neither a
    gap nor a provider context change can reset the incarnation's ceiling.
    Validation failures leave stream state unchanged.
    """

    def __init__(self, *, expected_host=None, expected_uid=None, expected_window_ms=None):
        self.expected_host, self.expected_uid = expected_host, expected_uid
        self.expected_window_ms = expected_window_ms
        self.service_id, self.binding = None, None
        self.sequence = self.revision = self.observation_revision = self.emitted = 0
        self.ceiling, self.clock_generation = None, 0
        self.gapped, self.material = False, None
        self.contexts = {}

    def parse(self, data):
        return self.accept(
            decode_document(
                data,
                max_bytes=MAX_FRAME_BYTES,
                max_nodes=MAX_NODES + 4096,
                max_depth=36,
                line_framed=True,
            )
        )

    def accept(self, value):
        validate_frame(
            value,
            expected_host=self.expected_host,
            expected_uid=self.expected_uid,
            expected_window_ms=self.expected_window_ms,
        )
        if self.service_id is None and value["kind"] not in {"status", "view", "error"}:
            raise ContractError("working_set_initial_frame")
        binding = (
            value["hostScope"],
            value["uid"],
            value["bootId"],
            value["clockDomain"],
            value["selectorDigest"],
            tuple(
                sorted(
                    (s["provider"], s["namespace"], s["configHome"], s["configHomeKind"])
                    for s in value["sources"]
                )
            ),
        )
        if self.binding is not None and binding != self.binding:
            raise ContractError("working_set_stream_scope_changed")
        if self.service_id is not None and value["serviceId"] != self.service_id:
            raise ContractError("working_set_stream_incarnation")
        if (
            value["sequence"] != self.sequence + 1
            or value["viewRevision"] < self.revision
            or value["observationRevision"] < self.observation_revision
            or value["emittedBoottimeMs"] < self.emitted
        ):
            raise ContractError("working_set_stream_order")
        ceiling = value["clockCeiling"]
        if (
            self.ceiling is not None
            and (ceiling is None or ceiling < self.ceiling)
            or value["clockGeneration"] < self.clock_generation
        ):
            raise ContractError("working_set_stream_clock_regression")
        if self.gapped and value["kind"] not in {"resync", "error", "status"}:
            raise ContractError("working_set_resync_required")
        contexts = dict(self.contexts)
        projection = value["projection"]
        material = self.material
        if projection is not None:
            candidate = canonical(
                {
                    "projection": projection,
                    "clockCeiling": ceiling,
                    "clockGeneration": value["clockGeneration"],
                }
            )
            if (
                material is not None
                and value["viewRevision"] == self.revision
                and candidate != material
            ):
                raise ContractError("working_set_revision_reused")
            material = candidate
            for scope in projection["scopes"]:
                key = scope["provider"], scope["namespace"]
                context = scope["contextGeneration"], scope["continuity"]
                prior = contexts.get(key)
                if prior is not None and (context[0] < prior[0] or context[1] < prior[1]):
                    raise ContractError("working_set_scope_regression")
                contexts[key] = context
        self.service_id, self.binding = value["serviceId"], binding
        self.sequence, self.revision = value["sequence"], value["viewRevision"]
        self.observation_revision, self.emitted = (
            value["observationRevision"],
            value["emittedBoottimeMs"],
        )
        self.ceiling, self.clock_generation = ceiling, value["clockGeneration"]
        self.contexts, self.material = contexts, material
        self.gapped = value["kind"] == "gap" or (self.gapped and value["kind"] == "status")
        return value
