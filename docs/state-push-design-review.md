# State push design review

Date: 2026-10-09. Reviews the narrowed [design](state-push-design.md) against
existing core/service/read source, an independent example consumer, installed
CLI/native streams and primary watch/patch references. Native occurrence-event
and desktop-notification integration are deferred by the user.

## Verdict

The existing complete-view Service 2 design fits the current discovery/monitoring
requirements. No new event vocabulary, transport, delta journal or wire version
is needed. Read-client work can bind the accepted API 2/snapshot 4/Service 2
today, preserving source scope, sampling, explicit uncertainty and local expiry.
This checkpoint refines documentation and validation; it changes no production
provider, core, service or read-client implementation.

The useful following work is reusable read-cache ergonomics/conformance and
consumer-specific projections, not a native-notification pipeline. Those remain
separate implementation gates. The 349 handoff is a client request and does not
make desktop notification transport part of shared observation.

## Source audit and resolutions

| Issue | Actual source / evidence | Decision |
| --- | --- | --- |
| Poll-to-push may duplicate collection per subscriber | Service worker scheduling is independent of read peers; controlled socket tests check cached readers start no extra jobs | Keep one host-local service collector/fan-out; clients never query providers |
| Push and pull might use different classifiers | Both wrap the same `ObservationEngine` projection; `ServiceState` supplies envelopes | Retain the shared engine; different receipt instants are not semantic disagreement |
| Revision mistaken for meaningful phase event | Engine publishes new revisions after accepted receipts even for unchanged values | Treat revisions as view ordering; compare values/health separately from evidence renewal |
| Full view mistaken for full native census | Rows include bounds/source coverage; Claude runtime explicitly partial | Complete replacement view under declared bounds, never universal native completeness |
| Initial/reconnect state causes alert burst | First complete view is current inventory, not new session creation or replay | Baseline-only on initial/resync/recovery; no inferred native notifications |
| Removal mistaken for session end | Accepted finite retention omits disappeared unsaved memory; selection also omits rows | Observation omission only; no parked/stopped/deleted event |
| Heartbeats keep a stale cache current | Heartbeat has no snapshot; core expiry and client receipt checks are independent | Cached-view expiry timers remain tied to that view, not heartbeat arrival |
| Idle reader never checks expiry | Validation on receipt cannot govern later UI display | Run local timers and silence deadline; source-specific conservative invalidation |
| One stale provider invalidates everything | Runtime/history receipts and sources are independent | Keep other source's still-current facts; retain qualified stale values separately |
| CLI filters masquerade as inventory | `service watch` calls `listing`; default child exclusion is presentation | Inspect all rows with `--include-children` or raw transport; retain filter context and reset baseline on policy changes |
| Array order becomes identity | CLI urgency/activity sorting and provider reclassification can reorder rows | Use the full identity tuple; no index-keyed deltas |
| Healthy subscriber needs every projection | Runtime coalesces obsolete views with gap/resync, bounded output and encoding | Current-view convergence is sufficient; no all-native-transition promise |
| Compact boards receive general metadata directly | Ordinary full views measured about 148 KiB / 403 KiB before JSON parsing | Host-side projection/bridge is a separate read consumer; defer device wire and delta protocol |
| Older remote oracle used for new producer | Starship checkout's reference bytes differed; initial attempt was inconclusive | Copy current reference into a task-owned temporary directory, validate hashes and clean it; do not treat harness failure as producer defect |

The [source receipt](evidence/2026-10-09-state-push-refinement/source-review.json)
binds inspected source/harness bytes. The
[validation report](evidence/2026-10-09-state-push-refinement/REPORT.md) records
both successful bounded native streams and the superseded incomplete probe.

## Research and alternatives

Kubernetes documents rebuilding a cache and establishing a new watch when
retained watch history is unavailable. Its resource-version replay is not
Observer's protocol, but its recovery model supports the same distinction
between restoring state and retaining every historical change.
[Primary watch reference](https://kubernetes.io/docs/reference/using-api/api-concepts/#efficient-detection-of-changes)

RFC 6902 patches apply operations sequentially to an existing target; array
insertions/removals depend on positions. A patch stream would add base/order/
atomicity/recovery requirements here. This is our inference from the standard,
not a claim that patches are inherently unsuitable.
[Primary patch reference](https://www.rfc-editor.org/rfc/rfc6902.html)

Retain complete views because current use needs up-to-date state and robust
resync more than an exhaustive history of view changes. No measured host-side
failure or daily-use latency result justifies a new delta protocol. Measured
unfiltered view size does justify preserving a separate constrained-device
projection boundary; it is not physical device acceptance.

## Validation strength and remaining gates

The independent consumer study uses validated real engine fixture frames and
injected clocks for twelve cases: warming, baseline, unchanged values/new
revision, heartbeat, independent expiry, row order/full identity, gap/status/
resync, reconnect, omission, provider fault and original conversation age.
It is a design example, not an implemented public cache helper or native oracle.

Installed CLI/native studies use the same independently inspected stdlib oracle
on both hosts. Snap's two initial views agree on all membership/runtime/phase;
initial activity cache lag clears at the next connection. Starship agrees on all
comparable facts. Stream scope, clock/sequence/lease checks and new reconnect
baselines pass. Bounded native comparisons do not prove forced transitions,
all sessions, native notification coverage or permanent healthy operation.

The full repository check includes controlled real sockets, coalesced immutable
frames/gap/resync, malformed/slow peers, source-worker lifetime and capacity.
These controlled checks are independent of native source comparisons and do
not establish physical suspend, device delivery or network replay.

Remaining scoped work: optionally implement a pure reusable read-cache/timer
helper, expose consumer conformance vectors, and validate a chosen device
projection as its own client. Existing cached sampling latency, metadata limits,
partial Claude registration coverage and twenty-one older Starship kinds stay
explicit. No ordinary restart, callback installation or provider upgrade pin is
required by this design.
