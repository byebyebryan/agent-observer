# State push follow-up execution plan

Date: 2026-10-09. Active plan following the reviewed
[state-only design](state-push-design.md) and
[validation](evidence/2026-10-09-state-push-refinement/REPORT.md).
The preceding native event E0–E5 implementation is deferred. Current API 2,
snapshot/watch 4 and Service 2 already supply accepted discovery/monitoring.
This research checkpoint selects no new production artifact or client.

## P0 — completed design and validation checkpoint

Capture state-view meaning, independent freshness, baseline/reconnect/gap/resync,
full identity, explicit bounds and presentation selection. Review complete views
versus deltas and shared observation versus device/client projection. Record
source, synthetic/controlled and installed/native evidence separately. Amend
current docs so native notification/event-protocol work is explicitly deferred.

Acceptance: current native comparison on Snap and Starship, stream/reconnect
scope/lease checks, counterexample model, existing controlled socket/capacity
suite, owned proof cleanup and no ordinary source/service/settings changes.
This is the current completed pass.

## P1 — optional reusable read-cache helper

If the next implementation request chooses this work, add a small pure
provider-independent consumer helper alongside the read facade. Inputs are
already validated Service 2 frames plus injected host-local clock/display time;
no I/O, provider lookup, networking, alert policy or auto-reconnect.

Own initial baseline, full replacement, gap/EOF/error invalidation, local source
expiry deadlines, last-known display qualification and reset on reconnect or
selection changes. Keep source clocks/reasons unchanged. Expose current view,
health and next expiry; optional full-identity differences are observed values,
not native lifecycle/completion events. Do not expose the study consumer as the
public helper without implementation/conformance review.

Acceptance: independent conformance vectors for both providers, warming/empty/
partial/stale inventory, independent runtime/history deadlines, gap/status/resync,
delayed frame and silent transport, lease refresh without value change, full
identity/filter reset and no dependency on collectors/actions/alerts. Choose
actual public additions and version only a concrete incompatible change.

## P2 — read CLI ergonomics and immutable acceptance

Keep existing `service snapshot/list/watch/status` behavior valid. Improve
human watch/cache/health presentation only after its exact interface is chosen;
retain JSON inspection and unfiltered comparison with `--include-children`.
Frame count includes heartbeat/gap; validation must continue through resync.
CLI filters are explicit presentation, never source negatives.

Acceptance: source tests and `./scripts/check`, explicit immutable candidate
read import/conformance, installed read/stream comparisons to the independent
native oracle on Snap and Starship. Package/deploy only when production bytes
actually change and after the separate operational gate; documentation-only
refinement needs no artifact rebuild, provider action or service restart.

## Independent projections and delivery

Agent Plus can develop against the accepted state interface independently.
Constrained dashboards may use a host-side read consumer to select rows and
compact fields, retaining full identity, stale/coverage signals and conservative
source age. Device-specific schema, transport, memory/flash/display acceptance
belong to that client. Do not imply a direct ESP32 parser for general snapshots.

mesh-plus remains separate and consumes accepted local reads. It supplies its
own authenticated routing/clock accounting and reconnect behavior; no network
implementation is included here. tmux/window matching and actions are external.

Native occurrence callbacks, notification normalization, replay protocol,
Kitty/D-Bus replacement and 349 sender/title/Open remain deferred. Ordinary native
notifications and accepted refresh hints remain independent and unchanged.

No frontend, sibling-repo or provider-policy change is an acceptance gate for
the observation/read producer. A consumer-discovered producer defect reopens
an Observer-only checkpoint rather than joining frontend work into this loop.
