# Read delivery hardening and publication

Date: 2026-10-09. The user authorizes this regular goal loop following the
[accepted Mesh integration](evidence/2026-10-09-mesh-integration/REPORT.md).
Commit independently reviewable checkpoints. Preserve API 2, snapshot/watch 4,
Service 2 and the frozen Mesh Agent profile.

## R0 — baseline and publication

Review source divergence and accepted artifact manifests. Publish the exact
archived Observer a12 and Mesh a4 wheels/manifests as GitHub prereleases; never
rebuild or overwrite those accepted bytes. Verify downloaded assets and a clean
core/Mesh installation. Publishing Mesh's already accepted dependency is in
scope; new networking development and shared-authority deployment are not.
The existing a11 collector, a16 writer and a4 bridge remain selected.

## R1 — sustained costs

Measure ordinary Snap/Starship operation with zero added readers, one local
watch, one fleet watch and two fleet watches. Each steady window is ten minutes,
with startup/warmup separate. Report actual simultaneous fleet workload, native
activity and attribution limits instead of calling an active host idle.
Authenticate managed process incarnations and walk only owned reader trees.
Measure CPU, RSS/PSS, process/FD counts and cleanup. Include collector helpers
and owned SSH clients; remote SSH bridge costs require separately authenticated
attribution and must otherwise remain explicitly excluded. No strict RSS target.
Do not implement pooling or change transport contracts based on short samples.

## R2 — pure local read cache

Add a provider-independent consumer helper for validated local Service 2 frames
and injected BOOTTIME/clock context. Reuse the public StreamGuard; do not query
providers, import collectors/Mesh, reconnect, deliver alerts or infer lifecycle.
Expose a qualified current projection, original last-known view, independent
component deadlines, next expiry and explicit invalidation/reset. Positive facts
expire during silence. Heartbeats do not replace view receipts. Runtime expiry
must not discard independently valid saved metadata, and liveness refresh must
not renew old work-state evidence. Preserve original activity clocks and rows.

Conformance covers warming versus empty, partial coverage, delayed frames,
independent runtime/history/provider expiry, unchanged-value receipt renewal,
gap/status/resync, EOF/error, changed incarnation/scope, reconnect, full identity,
filter reset and original age. Reject invalid input conservatively. The earlier
[study](state-push-execution-plan.md) is not the production helper.

## R3 — human watch

Add explicit local `service watch --human`. Keep existing default machine
commands and filtered service-watch semantics. Human output updates age and
expiry without a new frame, reports warming/partial/stale/disconnected states,
and preserves urgency ordering and confirmed-child filtering.

Mesh human watch uses Mesh's ReadGuard/current selector and reader clock;
Observer does not implement remote proof, clock conversion or reconnect.
Raw Mesh envelopes remain lossless. Timer renders are presentation only and do
not count as protocol frames or create synthetic wire events. EOF/cancellation/
output failure closes owned transport and invalidates positives.

## R4 — package, native acceptance and reader selection

Run source/conformance/controlled socket checks and `./scripts/check`. Build a
new immutable Observer reader candidate only when production bytes change;
independently test installed imports and interfaces away from the checkout.
Compare installed direct/cached/Mesh reads with the independent native oracle
on both hosts, within accepted provider scopes and sampling races.

Select the reader only after acceptance, preserving the a11 collector, a16
writer and existing a4 bridge prefix/process. Extend the managed reader gate
if needed to represent separate reader and bridge prefixes. Verify scoped
rollback/reselection, protected configuration and installed/live identity.
Publish changed accepted bytes separately from the a12 baseline. Update the
client handoff with cache examples, conformance obligations and measured costs.

## Scope and stopping rules

Notifications/native occurrence replay, devices/frontends, attachment/actions,
provider policy, ordinary provider restarts, physical suspend, legacy history
compatibility, broker/pooling and networking implementation stay separate.
Keep detected provider limitations explicit. A producer defect opens a focused
Observer checkpoint; it does not authorize downstream changes. A required
incompatible contract change or unrelated deployment drift blocks that delivery
step while independent work continues. Keep prior artifacts and evidence.
