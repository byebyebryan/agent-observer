# Observation boundaries

This reference describes the current Codex-only, read-only implementation.
API 4, snapshot/watch 6 and Service 4 are prerelease contracts; working-set
has a separate version-1 projection. [Architecture](architecture.md) maps the
components; [API reference](read-api.md) links the packaged schema and public facades.

## Observation authority

The passive adapter queries an existing owning Codex daemon. The shared engine
owns sample ordering, reconciliation, retention, refresh planning and expiry.
The service owns Observer helper/process lifetime, authenticated IPC, timers,
bounded subscriber queues and cleanup. Neither starts a missing provider daemon,
resumes a conversation or changes ordinary provider configuration.

The pure read facade performs no collection, filesystem/network discovery,
terminal matching, action or alert delivery. Optional Mesh networking consumes
cached state and pure profiles; it adds no provider classifier.

## Identity, runtime and coverage

- Preserve the full `hostScope/provider/namespace/nativeIdKind/nativeId` reference.
  A native thread ID and its tree-root ID remain different metadata.
- Saved presence, runtime (`running`, `parked`, `unknown`), work phase and
  classification are independent. Daemon idle means running/waiting.
- Parked requires positive saved identity and the reviewed native `notLoaded`
  predicate. Missing membership, endpoint failure, terminal closure and worker
  exit alone do not prove it.
- Work phase is working, blocked, waiting or unknown for running sessions.
  Approval/question evidence grants no authority to respond.
- Raw observations retain admitted user, child, system and unknown identities.
  Default list presentation hides confirmed child/system rows; diagnostic
  inclusion and exact selection remain available. Unknown kind stays visible.
- Partial discovery cannot prove exhaustive membership or removal. Complete-empty
  requires complete, current relevant coverage, not an empty rows array.

## Evidence and time

Conversation activity advances from native conversation evidence. Polling,
receiving a push, title changes and lease renewal do not advance that clock.
Liveness never refreshes old runtime/phase evidence. Independent facts may
expire at different times; unavailable reads cannot become idle observations.

Local caches evaluate expiry using their own boot/time-namespace context.
Mesh translates receipt lifetime into the receiver's clock domain while
retaining source attribution. Never compare raw remote and local boottimes.
Quiet clients must recompute expiry without waiting for another frame.

## Hints, state delivery and alerts

Passive native signals are bounded refresh hints. They wake authoritative
queries and cannot create runtime facts, prove saved existence, advance activity
or renew a lease. Periodic reconciliation remains necessary after hint loss.

Service and Mesh watches carry sampled reconciled state with baseline/gap/resync
rules. A heartbeat proves transport liveness only. Disconnect, terminal error
or lost baseline revokes the consumer's current view. This is not an event
replay or per-turn completion API.

User-facing notification policy, deduplication, focus and device delivery belong
to separate consumers. State reads and service startup send no alerts.

## Control and external clients

Native managers own New/Resume and conversation control. Observer's writer and
standalone active-only source/profile/client are removed. Working-set retains
active membership and recent context; a current active lease is required for
an active filter. A retained `running` label alone is insufficient.

Terminal/window attachment and action validation belong outside observation.
An unmatched window does not make a session parked; an attached TUI does not
make uncertain runtime evidence current. Agent Plus independently discovers
native homes and owns its launched windows without consuming Observer.

Claude native use in Agent Plus remains external. Reserved provider vocabulary
and synthetic fixtures do not enable a Claude adapter here. A future adapter
requires independent capability, contract and native review; see
[provider compatibility](provider-compatibility.md).
