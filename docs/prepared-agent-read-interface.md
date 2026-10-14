# Optional prepared Agent read interface 1

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
| `accept(frame)` | Full Mesh watch admission, then one raw export to retain source context on a replacement. Return the supplied frame, matching the SDK pattern. Any failure retires the whole helper. |
| `read(now_ms, clock)` | Fresh `AgentWatchRead(context, sessions)`. Sessions come only from the guard's current expiry/delivery checks. Context is a defensive copy of original Mesh header metadata, without session bodies; it is retained evidence, not authority. |
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
