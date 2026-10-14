# RLCD: optional prepared Agent read adoption

Producer acceptance: [R0–R5 ledger](evidence/2026-10-14-prepared-reads/REPORT.md).
This is a request for an independently owned client adoption pass. Observer has
not modified RLCD source, bundle, firmware, USB transport or application service.

## Accepted input and boundary

Use the exact [Observer 0.7.0a2](../artifacts/observer-0.7.0a2.json) and
[Mesh 0.1.0a18](../artifacts/mesh-0.1.0a18.json) wheel pair. Hashes:

- Observer: `d4a37999bcf5652d877572230746d9d0c3c306362b4c174b29cd642414f5768d`.
- Mesh: `035f0a54a06581e702ad79cce93ecf56f3d5dcf8d28535b533c0098e97ae2098`.

Both hosts archive these bytes under
`~/.local/share/agent-observer/0.7.0a2-d4a37999bcf5652d-mesh-a18-prepared/artifact/`.
The package pair is independently installed/native-tested; hosted wheel
publication is separate. Archive checksums take precedence over package names.
Observation remains API 4 / read 6 / Service 4 / explicit Agent profile v3,
SDK 1 plus optional preparation/read interface 1. No wire migration is needed.
Collectors and resident publishers retain a1/a17. Ordinary CLI defaults remain
legacy; `mesh watch --human --prepared` exercises the optional path.

The [local interface](prepared-agent-read-interface.md) owns no network task,
timer, reconnect, device clock, membership policy, ordering or notification.
Mesh owns full admission, proof, expiry and delivery. Observer owns deterministic
Agent rules and the small retained-header/current-row facade.

## Suggested change to Fleet

Replace ReadGuard with the explicit owner helper, retaining the same configured
Reader, AgentProfile, request, host scope, authority and route-reporting policy:

```python
from agent_observer.mesh_profile import AgentProfile
from agent_observer.mesh_read import PreparedAgentWatch
from mesh_plus.evidence import clock_domain
from mesh_plus.transport import boottime_ms

profile = AgentProfile()
watch = PreparedAgentWatch(request_id, host_ids=hosts, profile=profile)
try:
    async for frame in stream:
        watch.accept(frame)
        # The device/render timer can also read the same admitted watch.
        read = watch.read(boottime_ms(), clock_domain())
        # read.sessions: owned current rows, including parked/child/system rows.
        # read.context: original Mesh header/source context, or None.
finally:
    watch.disconnect()
    await stream.aclose()
```

Methods are synchronous and caller-serialized. The example illustrates the
seam, not an application supervisor. Preserve the client's existing bounded
reconnect/serial worker ownership, including cancellation and cleanup failures.
EOF/framing/liveness/output failure must disconnect. Reconnect and changed
installed profile/compiler semantics require a new helper. Explicit preparation
failure cannot fall back to an unchecked or legacy positive view.

`read.context` contains the original header's host delivery, owner metadata,
coverage and receipts. It excludes row bodies and is retained evidence, not
current authority or a wire response. Derive positive rows only from
`read.sessions`. Do not reconstruct/export all history per one-second request.
`watch.snapshot()` remains an explicit lossless raw export when needed; use it
at a deliberate boundary, not every device tick. Frame receipt/sample times do
not change on heartbeat or read. A gap discards context until valid resync;
clock/admission/compiler failure or disconnect retires it.

## Preserve accepted client behavior

Continue full host/provider/namespace/native-kind/native-ID identity; native title
and project label policy; running-only membership; confirmed child/system/parked
exclusion; unknown-kind running inclusion; source-sampled conversation age;
oldest activity first within the client's urgency bands; membership/capacity and
overflow separation. The helper does not implement these product policies.

Maintain current/partial/offline behavior, healthy siblings, retained labels
without stale positive phase/age/alerts, nonce-bound source-to-device lifetime,
expiry anchored to request send and ACK distinct from source freshness. Source
context does not supply a device clock bridge or prove completeness on omission.
Keep serial busy/absent/reset recovery and application service supervision.

## Required client acceptance

1. Use exact installed wheels in an isolated candidate dashboard bundle. Confirm
   no checkout or historical fallback imports. Keep the current accepted bundle
   and a1/a17 reader tuple for rollback.
2. Compare complete Fleet/projection outputs with the previous implementation
   over complete, partial, expired, gap/resync, missing-host and reconnect inputs.
   Check counts, membership, ordering, age, duplicate labels, system/child removal
   and healthy siblings. Raw export and source context are not positive authority.
3. Measure complete application CPU at actual publication/read cadence, including
   admission, source projection/exports, serial and worker supervision. Measure
   steady/peak memory separately. Producer microbenchmarks do not establish the
   application's savings or physical behavior.
4. Accept immutable bundle/device behavior and scoped service rollback separately.
   Preserve the independent 349 daemon and ordinary provider/Observer services.

The Agent benchmark at two hosts / 500 rows / three reads per replacement saves
about **36% total consumer CPU and 86% repeated-read CPU**. Prepared 500-row traced
allocation peaks are about **35% higher**, with lower steady retained bytes in
that sample; 1,000 small-inventory replacements plateau. Single-read lifetime
savings are only about 10%. These bound expectations, not an application promise.

Installed prepared fleet CLI watches still use roughly **12–16% of one core**
in five-minute normal-workflow windows. The unchanged RLCD application uses
roughly **19–22%**. Reader/carrier/admission pipeline and remote source costs are
outside the consumer benchmark; measure the complete application before claiming
the daily CPU issue is closed. Hosted Mesh a18/Observer a2 distribution remains
separate from the exact locally archived and accepted bytes.

Bring a producer/SDK defect back as a separate checkpoint with normalized input
shape, original receipt/clock/delivery facts and exact artifacts. Avoid frontend
workarounds that renew leases, treat omission as parked, or access private guard
internals. Rich occurrence notifications, attachment/actions, exact phase age
and new providers remain outside this handoff.
