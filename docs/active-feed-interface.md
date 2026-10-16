# Opt-in active Agent feed interface 1

This G1 implementation follows the [agreed active-feed plan](active-feed-proposal.md).
The [a7/a23 producer receipt](evidence/2026-10-16-active-feed/REPORT.md) accepts
the exact immutable package with bounded installed/native, fixed-SSH and
controlled performance evidence, including added generation cost and limits.
This document does not select a service, publisher, reader or downstream bundle.
RLCD owns its later consumer and operational gates. The existing full API 4,
Service 4 and Agent profile v3 remain available with their original semantics.

The owner service caches one fixed projection per published observation
generation before consumer IPC or Mesh transport. Status and proof calls read
that cache; no subscriber performs native collection or filters a full inventory.
The local service and projection engine remain Mesh-free. Original independent
component leases, conversation activity and timing receipts remain unchanged.

## Native contract and fixed selector

`agent_observer.active_contract` supplies the pure, bounded native contract:

| Export | Meaning |
| --- | --- |
| `ACTIVE_FEED_PROTOCOL = 1` | Distinct `activeFeedProtocol` wire family |
| `SELECTOR`, `SELECTOR_DIGEST` | Exact fixed descriptor and canonical SHA-256 binding |
| `interface()` | Detached contract metadata and limits |
| `schema_document("request" | "frame")` | Detached native schema |
| `validate_request(value)`, `validate_frame(value, *, expected_host=None, expected_uid=None)` | Strict structural and semantic admission; return the supplied value |
| `parse_request(data)`, `parse_frame(data, *, expected_host=None, expected_uid=None)` | Bounded one-line JSON decoding followed by strict admission |
| `support_matches(support, source, service_id, now_ms=None)` | Exact original native receipt comparison; optional owner BOOTTIME expiry check |
| `StreamGuard(*, expected_host=None, expected_uid=None)` | `accept(value)` / `parse(data)` with service, host, clock, sequence, revision and gap/resync checks |

The packaged [request schema](../agent_observer/contracts/active-request.schema.json)
and [frame schema](../agent_observer/contracts/active-frame.schema.json) define all
required properties and finite limits. The exports can be inspected without a
running service, Mesh installation, provider import or native acquisition:

```sh
agent-observer service active-api
agent-observer service active-schema --kind request
agent-observer service active-schema --kind frame
```

Every request has exactly `activeFeedProtocol`, `operation`, `hostScope`,
`selector` and `selectorDigest`. Operations are `status`, `snapshot` and `watch`.
There is no arbitrary caller predicate or request-time selector:

```json
{
  "version": 1,
  "providers": ["codex"],
  "kinds": ["unknown", "user"],
  "runtimeValues": ["running"],
  "runtimeHealths": ["current"]
}
```

Its digest is
`sha256:73d08f0217e03cea283820e18abed0b06cd5e4c52428e431bab5da1d760ff9d6`.
Descriptor order, scalar types and values must match exactly. The first source
is explicitly configured for this selector; there is no implicit full-feed
fallback when its endpoint/profile is unsupported.

The root frame retains the Service 4 metadata properties `serviceId`, `bootId`,
`uid`, `hostScope`, `sequence`, `viewRevision`, `kind`, `state`, `emittedAt`,
`emittedBoottimeMs`, `clock`, `clockDomain`, `reason` and `sources`. It uses
`activeFeedProtocol: 1`, `selector`, `selectorDigest` and `projection` instead
of `serviceProtocol` and `snapshot`. Configured source/component metadata keeps
its original shape. This family admits only the configured Codex source.

`projection` is `null` during warming and on heartbeat/gap/error controls.
A view or resync requires a projection. Otherwise its exact shape is
`{"scopes": [...], "sessions": [...]}`. `sessions` contains only selected,
unchanged API 4 session bodies. No full source roster is nested elsewhere.
Each projected scope has:

| Property | Content |
| --- | --- |
| `provider`, `namespace`, `contextGeneration`, `continuity` | Exact source scope and positive continuity token |
| `coverage` | `status`, bounded `reason` and original `supports`; statuses are complete, partial, warming, stale, unavailable or unsupported |
| `members` | Exact identity plus `fieldSupports`, one-to-one with selected bodies |
| `uncertain` | Exact identity, reason, nullable `priorSupport` / `support`, and original `horizonBoottimeMs`; informational context |
| `nonmembers` | Exact identity, `parked` / `excluded_kind` reason, parked/child/system value, original supports and prior-positive retention horizon |

Every identity uses host/provider/namespace/native-kind/native-ID. Scope and body
identities must agree, duplicates are rejected, and member metadata cannot exist
without its body. A complete-empty scope still carries explicit coverage support.

## Original evidence and membership

`FactSupport` contains exactly `serviceId`, `provider`, `namespace`,
`contextGeneration`, `component`, `accepted`, `sampledBoottimeMs` and
`expiresBoottimeMs`. Components are runtime or history. `fieldSupports` has
exactly runtime, phase, kind, savedIdentity, activity, outcome, workspace,
lastUpdated and latestTurn, each a support reference or `null`.

Transient engine metadata captures support when the actual field value is
accepted and follows that value through reconciliation. It does not infer
support from the latest healthy component. A current reference must exactly
match the source's service/context/accepted/sample/expiry tuple with current or
partial native receipt health. A newer receipt at the same component key cannot
renew an older field or decision. Old references can remain informational;
there is no historical receipt bank or extra per-identity receipt slot. Mesh's
existing maximum of 32 receipts per host remains in force.

Running membership requires current runtime support and support for a known
selected kind. An unresolved kind may remain explicitly unknown; a known kind
whose support failed becomes uncertainty. Phase and outcome are separate:
loaded idle/waiting, blocked and errored sessions remain running while the
runtime predicate remains current. Loaded-list absence does not prove parked.
A parked decision requires the positive saved-thread `notLoaded` observation
and its own saved identity support. An excluded-kind decision requires the
actual native child/system classification support.

Complete coverage requires the current complete `daemon_threads` loaded-and-saved
census, no unresolved native statuses, and a decidable selected/nonselected
result for every census identity. Its support union includes that runtime census
and the actual classification/identity dependencies used. Any unresolved input,
missing support or lost entry/byte/census capacity makes coverage partial.
The inactive census identity set is not sent to consumers. Fresh complete
coverage permits absence reconciliation only within that exact covered scope.

The producer ledger has separate hard bounds of 4,096 tracked identities and
1 MiB canonical metadata, including internal references and order/continuity
bookkeeping. Body/frame capacity is separate: requests and envelope overhead
are each at most 16 KiB; frames are at most 8 MiB plus 16 KiB. These are ceilings,
not a promise that every maximum-sized combination fits. Overflow explicitly
fails the affected scope and changes continuity; no truncated selected set is
advertised as complete. Healthy sibling scopes retain their own authority.

| Lifetime | Expiry or loss means |
| --- | --- |
| Positive member and individual field facts | Revoke only those unsupported facts; no positive parked assertion |
| Positive nonmember or complete-absence authority | Stop using it for new reconciliation; a valid earlier retirement is not reversed |
| Consumer presentation context | Existing policy remains external; this interface introduces no finite time-to-hide |

The ledger tracks only recent positively emitted members. Its unresolved-prior
horizon comes from the original positive support; uncertainty, emission and
unrelated receipt renewal do not extend it. A nonmember's ledger retention
horizon and its currently usable negative lease are distinct. Ledger expiry,
pruning, overflow and omission never retire consumer context by themselves.
After a partial reconnect or a missed expired negative, prior rows can remain
uncertain until later complete authority or a current exact decision settles
them. Exact eventual retirement through arbitrary partial outages is not
promised. A prior-identity query, deltas, digest-only proof and new presentation
timeout are outside this pass.

## Optional Mesh profile, source and publisher

These modules require the separately reviewed packaged Mesh active profile.
An older Mesh lacking it fails explicitly. They own no native provider adapter.

`agent_observer.mesh_active_profile.ActiveAgentProfile()` uses
`ACTIVE_PROFILE_ID = "agent-observer.mesh-active.v1"` and native protocol
`agent-observer.active-feed` version 1. Its descriptor binds the packaged profile
schema digest and native frame ceiling. `bind(host, source)` returns frozen
`ActiveAgentCodec`; `validate_bridge(payload)`, `inspect_native(frame)` and
`admit_bridge(payload)` remain strict for arbitrary mutable input. Combined
admission performs one native validation and returns `NativeState`; Mesh still
independently validates envelope, capacity, lossless roundtrip, digest, source,
clock, request, nonce and translated receipts.

The profile's public SDK callbacks are `validate_response`, `restore_native`,
`record_host`, `record_identity`, `record_receipts` and `record_eligible`.
`NativeState.records` contains selected API 4 bodies only. Its owner is
`{protocol, version, metadata, service}`: `metadata` is projection without
sessions, and `service` is the native header without projection. Restoration is
lossless for this new DTO. Root component receipts retain original acceptance,
health and expiry; a null projection exports no positive native receipt health.
The publisher incarnation is the owner service ID. The codec requires the
original `time:[digits]` clock domain.

`ActiveAgentPreparation(profile=...)` implements preparation interface 1 with a
frozen profile/implementation descriptor. It compiles immutable admitted facts
once per replacement. Generic row requirements conservatively union exact
current body-field dependencies, after exact original references have been
checked; only then are they reduced to source/component keys. Preparation is
independent of caller clocks and UI selection policy.

`agent_observer.mesh_active_source.CachedActiveAgentSource(host, path, *,
timeout=15.0)` supplies async `snapshot()` and async-generator `watch()`.
Snapshot requests cached status; watch yields `CachedPublication(frame,
serviceId, {"viewRevision": ...})`. It inherits the checked full source's socket
ownership, local clock, ordering, receipt-watermark, incarnation, timeout,
capacity and operation-owned cleanup checks, with the fixed active request and
active stream guard. Construction acquires nothing. It never starts or repairs
an owner or provider.

The lazy factory is
`agent_observer.mesh_publisher.make_publisher(host, source, socket, *,
profile_id=FULL_PROFILE_ID)`. The default remains full profile v3. Explicit
active configuration can retain Mesh's three-argument factory interface:

```python
from functools import partial
from agent_observer.mesh_active_profile import ACTIVE_PROFILE_ID
from agent_observer.mesh_publisher import make_publisher

active_factory = partial(make_publisher, profile_id=ACTIVE_PROFILE_ID)
publisher = active_factory(host, configured_active_source, owner_socket)
```

The active source is separately configured and hello-bound to its profile.
The fixed selector is inside the digest-covered native DTO. Fresh nonce proofs
call the cached active endpoint after nonce validation and carry a full projected
reply. Full inventory, full profile v3 and independent Tmux configuration keep
their existing routes.

## Public prepared active read facade

`agent_observer.mesh_active_read.ACTIVE_READ_INTERFACE_VERSION` is 1.
`PreparedActiveAgentWatch(request_id, *, host_ids=None, profile=None,
preparation=None)` is synchronous and caller-serialized. Pass the same
`ActiveAgentProfile` instance to the Mesh reader and helper when using opaque
`AdmittedResponse` values from `watch_admitted` / `execute_admitted`.

| Method | Result and ownership |
| --- | --- |
| `accept(frame)` | Admit strict raw or opaque owned watch input. On each replacement, call public guard `snapshot()` once and privately retain selected bodies plus admitted metadata. Return supplied input. Heartbeats do not renew or re-export facts. |
| `read(now_ms, clock)` | Detached `ActiveAgentRead(context, members, uncertain, nonmembers, scopes)` using exact reader clock and monotonic query time |
| `snapshot()` | Detached retained raw projected Mesh replacement, or `None`; informational after lease expiry |
| `disconnect()` | Revoke the helper and discard owned cache; reconnection needs a new helper |

`ActiveAgentRead` is a frozen wrapper. Its JSON dictionaries/lists are detached,
mutable caller-owned exports. `sessions` aliases `members` on that result.
`context` is the original Mesh header, never current authority. `uncertain`
contains compact informational decisions. `nonmembers` contains only currently
supported exact positive exclusions. `scopes` contains `hostScope`, `serviceId`,
provider, namespace, contextGeneration, continuity and query-time coverage;
nested member lists are absent from this scope export.

Every read calls public `guard.current(now_ms, clock)` first, then `context()`,
including zero-body generations. Each claim separately requires exact native
support, matching service/source/context/selector/continuity, ready delivery,
matching accepted counter and current/partial translated host receipt with
`expiresAtMs > now_ms`. Remote expiry uses Mesh's translated deadline, never
subtraction of remote absolute clocks. Raw retained headers grant no authority.

The facade keeps the public snapshot body so it can mask fields independently
with their original support. Generic preparation may expire an entire body when
one history dependency expires; valid running/kind support can still retain
membership while activity, workspace or timing becomes last-known. Invalid
runtime or selected-kind support removes the row from current members without
declaring it parked. Complete-empty coverage expires through its own dependency
union even if another receipt or header remains healthy; its exported status
becomes stale. These rules apply before any consumer sorting or display cap.

Gap revokes the generation until a proved resync. Disconnect, malformed input,
clock regression, invalid binding or failed admission clears the helper. The
caller must disconnect in `finally` on EOF, framing/liveness failure,
cancellation and output failure and close its owned iterator. The facade owns
no timer, I/O, reconnect, presentation history or expiry-to-retirement policy.

## Adoption and evidence boundary

The active endpoint requires the new service/collector artifact with actual-value
support and census provenance. A reader/publisher-only upgrade against the old
service cannot provide this interface. Later adoption must qualify and select
the service, publisher, Mesh package and consumer as an explicit tuple, retain
the full-feed rollback tuple, and independently prove source/native parity,
IPC/fixed-SSH proofs, original leases, full membership reconciliation, controlled
cost, cleanup and affected service behavior. The current full-feed selections
are unchanged by source acceptance. No package installation, managed role
change, provider/session action or production rollout is authorized by this
interface document.
