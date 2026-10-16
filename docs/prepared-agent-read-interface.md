# Optional prepared Agent read interface 2

Observer 0.7.0a6 adds explicit selection and owned Mesh admission, requiring
Mesh 0.1.0a22 or newer with admission 1, selection 1 and preparation 1.
`agent_observer.mesh_read.READ_INTERFACE_VERSION` is 2. API 4, read wire 6,
Service 4, Agent profile v3 and SDK 1 retain their meanings. Independent producer
acceptance and performance bounds belong to the accompanying evidence receipt;
consumer adoption and production selection remain separate.

`PreparedAgentWatch` accepts either strict ordinary watch JSON or the opaque
`AdmittedResponse` replacements from `reader.execute_admitted(request)` /
`reader.watch_admitted(...)`. Pass the **same AgentProfile instance** to the
reader and helper. Mesh binds the owned admission to that instance and its
callbacks, checks watch ordering/scope afresh and retains immutable bytes.
Exported dictionaries cannot change the admitted value. Ordinary mutable inputs
still receive complete admission every time. Observer's optional
`AgentCodec.admit_bridge(payload) -> NativeState` combines native binding and
inspection into one complete Service 4 validation. Mesh independently checks
native round-trip, capacity, host, clock, digest, nonce, receipts and proof.
The standalone codec callbacks remain strict; the combined callback is not a
proof validator or a trusted-input switch.

Replacement context now comes from the supported Mesh `context()` header export.
It never reconstructs raw session bodies. Heartbeats retain the original header.

## Explicit current selection

Pass an immutable `AgentSelection` as `PreparedAgentWatch(..., selection=...)`.
Each optional field is a `frozenset` of accepted contract values. `None` accepts
all values, and an empty set accepts none. The four fields are `providers`,
`kinds`, `runtime_values` and `runtime_healths`. Selection compares admitted
facts directly and adds no native classifications, work phases or defaults.

```python
from agent_observer.mesh_profile import AgentProfile
from agent_observer.mesh_read import AgentSelection, PreparedAgentWatch

profile = AgentProfile()
selection = AgentSelection(
    providers=frozenset({"codex"}),
    kinds=frozenset({"user", "unknown"}),
    runtime_values=frozenset({"running"}),
    runtime_healths=frozenset({"current"}),
)
watch = PreparedAgentWatch(request_id, profile=profile, selection=selection)
# Configure the reader with profile=profile, then consume its execute_admitted
# iterator. Control/terminal frames remain ordinary dictionaries.
watch.accept(frame)
read = watch.read(now_ms, reader_clock)
```

This example's selection belongs to its caller. No provider filter, kind filter,
row limit, ranking, failure/retry presentation, identity hash, age rendering or
device policy is implicit in the helper. Default `selection=None` preserves all
current rows and returns `summaries=None`.

For a selected helper, `read.sessions` contains full owned native records matching
the explicit filters. `read.summaries` is a tuple of frozen `AgentRecordSummary`
values for **every current record**, including records rejected by the filters:

| Field | Meaning |
| --- | --- |
| `identity` | Full tuple in host/provider/namespace/native-kind/native-ID order |
| `kind` | Original admitted user/child/system/unknown kind |
| `runtime_value` | Original running/parked/unknown observation |
| `runtime_health` | Original runtime observation health |

Consumers can use positive child/system/current-parked facts to retire exact
identities even beyond their display prefix. Missing or rejected selection is
not itself a retirement fact. Unknown-kind running rows remain available when
requested. Summary and body authority expire together under Mesh's original
per-row component/delivery checks. Partial-host retention, gap/resync, reconnect
and stale/unavailable behavior match the complete current read. Source-sampled
`activity.at`, failure outcomes and latest-turn/retry metadata remain unchanged
in selected bodies.

Mesh compiles selection once per generation, on its first selected read. Warm
reads decode selected bodies and small summaries without decoding rejected full
records. `snapshot()` remains a complete lossless raw export regardless of
selection. All outputs are detached; `AgentWatchRead` and summaries are frozen
DTOs, while context/session dictionaries remain independently owned mutable JSON.
Failures revoke context and the whole helper, with no fallback.

## Preparation and lifecycle inherited from interface 1

Accepted local interface, 2026-10-14 UTC. Observer 0.7.0a2/Mesh a18 passes
source, immutable package, native read and reader-only selection gates in the
[acceptance ledger](evidence/2026-10-14-prepared-reads/REPORT.md). The
[RLCD handoff](rlcd-prepared-read-handoff.md) retains independent client adoption.
This additive local Python interface preserves API 4, Service 4, Agent profile
v3 and Mesh SDK 1. It is not a wire response, collector or transport owner.

`agent_observer.mesh_preparation.AgentPreparation(profile=AgentProfile())`
implements Mesh preparation interface 1. Its frozen descriptor binds the exact
selected profile and a reviewed static-rule implementation identifier. For each
immutable admitted record, in original order, it returns the full identity,
requirements and eligibility matching AgentProfile:

- Requirements are all originally current/partial native receipts for that
  record's provider/namespace, or `None` if absent. Grouping receipt lookup may
  avoid repeated scans but cannot change the required set.
- A saved record is eligible. A runtime-only record requires current runtime
  health and a required runtime receipt. Eligibility never filters kind or
  runtime disposition; clients retain their own selection policy.
- Mesh alone intersects original native/projected receipts, delivery and expiry
  to grant current rows. Receipt missing/expiry behavior matches legacy exactly.

Compilation uses admitted immutable facts only. No callback state, clocks, I/O,
provider invocation, actions or global policy participates. Owners retire and
replace guards before changing installed profile/compiler semantics. Descriptor
identity reports provenance; it does not attest package bytes.

`agent_observer.mesh_read.PreparedAgentWatch(request_id, *, host_ids=None,
profile=None, preparation=None)` explicitly constructs Mesh PreparedReadGuard.
Supported methods are synchronous and caller-serialized:

| Method | Result and ownership |
| --- | --- |
| `accept(frame)` | Strict raw or owned Mesh watch admission, then a context-only export on a replacement. Return the supplied value. Any failure retires the whole helper. |
| `read(now_ms, clock)` | Fresh `AgentWatchRead(context, sessions, summaries)`. Bodies and optional summaries follow the guard's current expiry/delivery checks. Context is a defensive copy of original Mesh header metadata; it is retained evidence, not authority. |
| `snapshot()` | A fresh lossless raw Mesh export or `None`, with the SDK's retained-evidence semantics. No automatic export occurs during a timer read. |
| `disconnect()` | Retire the guard and discard retained context immediately. |

`AgentWatchRead` is a frozen DTO with independently owned mutable JSON outputs.
Its `context` is the original Mesh header or `None`, **not** a complete or
validatable wire response. Host owner metadata/service fields preserve source
coverage, sample times and original receipts; `sessions` carries the independently
current rows. No source-to-device clock conversion, status renaming, label policy,
membership retirement, TTL decision or filtering is added.

| Input or lifecycle | Result |
| --- | --- |
| Before baseline | No context or current rows |
| Valid replacement, including partial/unavailable hosts | Replace context once; current rows retain each admitted host's own delivery/lease outcome |
| Heartbeat | Keep original context/receipt/sample times; do not export or prepare again |
| Lease expiry during silence | Current rows expire through Mesh; original context remains separately marked retained evidence |
| Gap | Discard context and positives until valid resync |
| Base/terminal error, malformed frame or compiler error | Discard context and positives; retire the helper |
| Invalid clock/BOOTTIME on read | Discard context and positives; propagate the bounded SDK error |
| EOF, framing/liveness failure, cancellation or output failure | Transport caller calls disconnect in finally and closes its owned iterator |
| Reconnect or changed installed semantics | Construct a fresh helper/guard; no repair or implicit legacy fallback |

The optional module requires the exported prepared SDK capability and preparation
interface 1. Its imports are explicit; core, local service, ordinary help and
legacy snapshot APIs remain usable independently. It owns no tasks, timers,
subscription, reconnect or network connection. Polling does not use this helper.

The first CLI adoption is explicit `mesh watch --human --prepared`. Ordinary
watch/poll/raw paths keep their existing behavior. Unsupported preparation yields
a bounded dependency/capability error; an explicit request cannot fall back.
Performance acceptance may justify a separate future default-selection decision.
