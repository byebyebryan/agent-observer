# Discovery/monitoring state-push refinement

Date: 2026-10-09. Research/refinement/validation checkpoint starting at
`bca4c26`. The user chose to defer native notification integration and focus
on existing discovery/monitoring push. This changes documentation and adds
study harnesses only; production core/service/read bytes, normal provider
settings, installed artifacts, refresh hints and ordinary notifications remain
independent and unchanged.

Associated [design](../../state-push-design.md),
[review](../../state-push-design-review.md) and
[following plan](../../state-push-execution-plan.md) supersede the scheduling
of native occurrence-event E0–E5 work. Their previous source research remains
historical evidence, not a requirement to implement notification normalization.

## Source and method

[Source review](source-review.json) binds the inspected engine, service
envelope/runtime/transport/CLI and new study scripts. Current pure read API 2,
snapshot/watch wire 4 and Service 2 already supply current-state publication.
No new event wire, server-side filtering, patch protocol or replay store is added.

The [normal-service preflight](normal-service-preflight.json) verifies selected
a11 CLI and unchanged normal units. Snap uses runtime/history intervals 30/120
seconds, Starship 20/60, both with ten-second collection deadlines and existing
native hints. Corresponding live runtime/history leases are 90/360 seconds and
60/180 seconds. These are measured configurations, not universal latency targets.

The read-only study invokes the installed CLI from `/tmp`, captures complete
`service watch --include-children` views, validates connection scope, sequence,
publisher/boot/time identity and current lease deadlines, and compares the first
view to independent native samples immediately before/after receipt. A second
connection establishes a new sequence/baseline. The stdlib native oracle
imports no Observer collector; another Observer result is not its authority.
All provider reads are passive. Normal session state changes are not induced.

Only bounded service counters, exact identities, classifications, activity
clocks and finite comparison outcomes are retained. No full watch snapshot,
raw native payload, conversation body, tool payload, terminal capture or
credentials are persisted. The two study scripts are development tools, not
new public client APIs or production publisher implementations.

## Installed/native stream results

| Receipt | Ordinary inventory | Result |
| --- | --- | --- |
| [Snap](installed-snap.json), connection 1 | 91 Codex rows, three running; 36 Claude UUIDs, seven running | All membership/runtime/phase agree; two Claude activity clocks lag cached sampling; accepted setup-only cwd omission |
| Snap, connection 2 | Same inventories/running counts | All comparable activity clocks agree, including 34 Claude clocks; only the accepted cwd omission remains |
| [Starship](installed-starship.json), connections 1 and 2 | 354 Codex rows, six running | All comparable facts agree, including 106 activity clocks; 21 accepted older kinds remain unknown |

Source coverage stays explicit: Codex within bounded daemon/catalog contracts;
Claude partial saved/runtime scope under the accepted interactive-registration
assumption. A live missing Claude registration can still be missed/falsely
parked, and background runtime remains unsupported. This study does not change
those accepted limits or claim a complete all-session census.

Snap's initial activity differences are UUIDs
`9fd1ae71-76f0-41c3-925f-da4756e64953` (26,507 ms) and
`fac5ee15-8b9c-4527-8976-0a808ab93ac7` (7,298 ms). Both clear on reconnect;
the first view's receipts precede the native bracket. The result demonstrates
cached-sampling latency, not age rewriting or an unresolved current mismatch.
The persistent cwd omission is the previously accepted setup-only UUID
`e0cba9dd-b642-4730-af4b-beb3b7e9c16c`.

Snap's two connections receive seven views and one heartbeat over about 24
seconds. Starship receives four views and four heartbeats over about 51 seconds.
All connection sequences are contiguous; reconnect starts at one with the same
unchanged publisher. No native action, ordinary service restart, forced delivery
gap or provider failure is part of this live proof. First full-view CLI latency
is 295–315 ms on Snap and 409–410 ms on Starship; this includes CLI startup,
parsing and serialization, not the preceding native-reference work or collection
latency for a newly changed provider state.

Unfiltered full views measure 151,903–151,936 encoded bytes on Snap (about 148
KiB) and 413,086–413,087 bytes on Starship (about 403 KiB). JSON parse/object memory
is additional and unmeasured on a physical device. These sizes support a
separate host-side compact consumer projection for constrained hardware, not
an immediate new producer delta protocol or device acceptance claim.

## Incomplete probe and correction

The first Starship attempt used its checkout's older native reference script,
whose hash differs from the current Snap reference. Two attempts did not produce
a usable native comparison; the retained
[finite failure](starship-attempt-failure.json) is unclassified. These failures
are not reported as producer mismatches or accepted native proof.

The accepted retry sends the same current driver/oracle bytes into a task-owned
private temporary directory on Starship, runs the passive study, then removes
that directory in `finally`. Both accepted receipts record the same current
oracle SHA-256. It neither changes the remote checkout nor synchronizes source,
provider config or installed artifact selection. A successful retry with the
current reference does not identify the precise original exception.

## Consumer counterexample study and controlled evidence

[Consumer model](consumer-model.json), reproducible with
`python3 -I -B scripts/study-state-push-consumer`, runs validated real checkout
engine frames against an independent example cache with injected clocks.
Twelve cases cover warming/null, initial baseline, new revision without value
change, heartbeat/no renewal, independent source expiry, row order/full identity,
gap/status/resync, reconnect, omission, source fault and preserved known activity.
The example cache is conservative and is not exported as a supported helper.
No native transition or production client implementation is accepted by it.

The repository check includes actual controlled Unix sockets and fake source
workers: immutable partial-frame delivery, gap/resync after coalescing, malformed
and slow peers, no extra collection jobs per read subscriber, worker deadlines,
near-limit frames and bounded pinned encoded bodies. These are controlled
transport/source tests, distinct from ordinary native comparison. The bounded
ordinary readers did not themselves trigger a live slow-reader gap.

[Check results](check-results.json) record the full repository suite and scoped
source/docs/evidence verification. No production repair was necessary for this
design checkpoint.

## Preservation, acceptance and remaining scope

Both successful receipts assert ordinary unit PID/birth/restart counts unchanged
across each host study. Normal Codex config, existing Claude settings where
present, and codex-notify helper hashes also match before/after. Mutable ordinary
Claude preferences are not claimed byte-stable or restored. No normal session
is stopped/resumed/renamed, no hooks or helper are installed, and no sibling repo,
network/runtime component, artifact or UI/device selection is changed.

Accepted: the existing complete-view state-push design, explicit scoped
discovery/runtime/phase meanings, baseline and source-specific expiry rules,
reconnect/gap/resync obligations, full identity, original conversation clocks,
client-side presentation and separate device projection boundary. Current read
clients can use the established interface independently of notification work.

Remaining: optional reusable read-cache/timer helper and conformance vectors,
CLI ergonomics if requested, and independent downstream compact/device/mesh
delivery. Existing sampling latency, accepted metadata/provider limits,
physical suspend/wake and device transport are not silently promoted. Native
occurrence/completion/attention normalization, event protocol/replay and desktop
notification replacement are explicitly deferred.

## Primary research

- [Kubernetes watch recovery](https://kubernetes.io/docs/reference/using-api/api-concepts/#efficient-detection-of-changes): state-cache recovery after unavailable history; not a dependency or protocol adoption.
- [RFC 6902](https://www.rfc-editor.org/rfc/rfc6902.html): sequential patch semantics; added base/order/recovery cost is a design inference.

Installed/native observations establish local proof. External references inform
the full-view/recovery versus delta tradeoff, not provider runtime behavior.
