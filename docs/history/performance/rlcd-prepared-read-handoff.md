# RLCD: optional prepared Agent read adoption

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Producer acceptance: [R0–R5 ledger](../../evidence/2026-10-14-prepared-reads/REPORT.md).
The independently owned RLCD adoption pass now implements this seam. Its source,
bundle, firmware, USB and application-service acceptance remain in the device
repository; the producer checkpoint remains frozen throughout client work.

The [2026-10-15 CPU delivery plan](cpu-reduction-execution-plan.md) now sequences
the existing CPU source corrections through an independent producer gate before
client adoption. [C0–C2 are accepted](../../evidence/2026-10-15-cpu-delivery/REPORT.md);
the a5/a20 pair below is the accepted input. C3–C4 adopt prepared reads from
the previous wire-2/failure-refinement application, sync the reviewed source to
**Starship**, verify/flash/read back RLCD `94:A9:90:F3:43:74`, and accept real
feed/expiry and paired rollback. Selected client source is `19323e6`, bundle
`807eab96b48825ae`, Observer a5/Mesh a20. This document retains the seam and
required gates as the reference for later consumers; it is no longer pending
RLCD implementation.

The [independent client acceptance](https://github.com/byebyebryan/esp32-rlcd/blob/358d265/docs/evidence/2026-10-15-prepared-reads/REPORT.md)
also completes the warmed cost and publication gate: 12.76% of one core in the
selected Starship service versus 20.99% before, with essentially flat memory.
These are descriptive ordinary-workload windows; matched controlled application
cost/output and separate endpoint costs are reported in that receipt.

## Accepted input and boundary

The [CPU delivery checkpoint](../../evidence/2026-10-15-cpu-delivery/REPORT.md) accepts the exact
[Observer 0.7.0a5](../../../artifacts/observer-0.7.0a5.json) and
[Mesh 0.1.0a20](../../../artifacts/mesh-0.1.0a20.json) wheel pair. The earlier a2/a18
helper acceptance remains separate historical evidence. Hashes:

- Observer: `25cd5663560c973b55fc322b9504e287f5a2a6706ef1c377100c6bf900752ee5`.
- Mesh: `e02306b2323ddd845fec2c1ee82dd25b429878edefcee4cf8ac2b552535fc200`.

Both hosts archive these bytes under
`~/.local/share/agent-observer/0.7.0a5-25cd5663560c973b-cpu/artifact/`.
The package pair is independently installed/native-tested; hosted wheel
publication is separate. Archive checksums take precedence over package names.
Observation remains API 4 / read 6 / Service 4 / explicit Agent profile v3,
SDK 1 plus optional preparation/read interface 1. No wire migration is needed.
Collectors retain core-only a3; resident Agent publishers select a5/a20. Ordinary CLI defaults remain
legacy; `mesh watch --human --prepared` exercises the optional path.

The [local interface](../../prepared-agent-read-interface.md) owns no network task,
timer, reconnect, device clock, membership policy, ordering or notification.
Mesh owns full admission, proof, expiry and delivery. Observer owns deterministic
Agent rules and the small retained-header/current-row facade.

## Implemented seam in Fleet

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

## Client acceptance requirements

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

Historical installed prepared fleet CLI watches used roughly **12–16% of one
core**, and the old RLCD application used roughly **19–22%** in five-minute
normal-workflow windows. The client pass independently compares old/new
application and dependency tuples, plus installed service CPU and memory.
Reader/carrier/admission pipeline and remote source costs remain distinct from
the consumer benchmark. Hosted wheel distribution remains separate from the
exact locally archived and accepted bytes.

Bring a producer/SDK defect back as a separate checkpoint with normalized input
shape, original receipt/clock/delivery facts and exact artifacts. Avoid frontend
workarounds that renew leases, treat omission as parked, or access private guard
internals. Rich occurrence notifications, attachment/actions, exact phase age
and new providers remain outside this handoff.

The a20 source/publisher correction separates watch receipt histories from
serialized snapshot/proof acquisitions. Original expiry, identity and the
prepared local interface remain unchanged. Recreate guards/processes when
adopting the installed pair. Mixed local CPU results are not a general SDK
speedup; accept the complete RLCD application independently. Its former
a1/a17 dependency environment and bundle were preserved by Observer rollout and
are retained for the independently exercised client rollback.
