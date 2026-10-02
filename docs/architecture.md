# Agent Observer architecture boundaries

Date: 2026-10-02. Status: initial boundaries; data-source and interface proof
pending. [Roadmap](roadmap.md) and [spike plan](agent-session-spike-plan.md).

## Purpose

Provide one reusable implementation of provider session discovery and
observation for the active RLCD and Agent Plus projects. Keep provider version
and topology behavior in adapters so each consumer does not have to maintain
its own interpretation of the same runtime.

WSNav's lifecycle work is useful historical evidence. It is currently inactive,
may be simplified, and does not set the component's runtime ownership model,
implementation language or acceptance criteria.

## Shared and consumer responsibilities

| Owner | Responsibility |
| --- | --- |
| Agent Observer | Provider adapters, inventory, native identity, bounded metadata, runtime/work observations, capabilities, provenance, freshness and reconciliation |
| RLCD host bridge | Session selection/prioritization, dashboard representation and device transport |
| Agent Plus | Picker UI, host routing, terminal association, launch/resume/focus decisions and action validation |
| Possible future WSNav consumer | Workstream persistence, runtime ownership, workflow decisions and action validation |

Agent Observer reports observations; it does not confer ownership or permission
to act on a session. Consumers must revalidate actions under their own rules.
The initial component is host-local. Existing host routing can invoke it on a
target host later; a new network control plane is outside this proof.

## Observation model

Separate saved-session inventory from live runtime observations. A saved
conversation can be inactive, a job can survive a worker exit, and a session
can have zero or multiple attached clients. A metadata helper can read history
without knowing another runtime's live state.

The provisional model records logical/native IDs, optional provider job and
runtime incarnation IDs, bounded project/title metadata, provider version and
topology, work state and wait reason, and source/observation health. State and
liveness have separate observation timestamps. Conditional or missing fields
remain explicit; unresolved records must not acquire guessed native identity.

Candidate work states are working, needs input, settled, interrupted, error
and unknown. Settled does not establish task success. Preserve bounded native
state codes and capability coverage when normalization would lose a useful
distinction. Keep unavailable/stale observations distinguishable from idle.

## Interface candidates

The initial reuse boundary is language-neutral JSON. The implementation may
offer a library internally, but the active consumers do not require a particular
library language. These operations are proposals, not implemented commands:

| Operation | Purpose |
| --- | --- |
| Snapshot | Read inventory and current observations with coverage and freshness |
| Watch | Emit an initial snapshot and subsequent changes, with explicit gap/recovery behavior |
| Capabilities | Report supported interfaces, versions/topologies and pending or unsupported state coverage |

Keep a schema version and bounded source diagnostics. Exact wire fields,
revision/ordering rules, lifecycle storage and API stability follow the spike.
Choose between a one-shot CLI, foreground watcher and shared local collector
based on measured source behavior and consumer needs; do not require a new
background service merely to share code.

## Provider strategy

Evaluate supported native state feeds first: Claude's documented JSON roster
and Codex reads from the server that owns the runtime. Use passive hooks for
proven gaps or foreground sessions where no native state feed is available.
Process evidence supports identity/liveness reconciliation.

The [source study](agent-session-study.md) records candidates and limitations.
Actual installed versions, compatibility opt-outs, observation side effects,
and waiting/cancellation/recovery coverage must be established by the
[spike](agent-session-spike-plan.md). No source choice is yet accepted.

## Deferred work

Consumer migrations, session actions, OpenCode, multi-host aggregation,
production hook installation, service deployment, provider policy changes,
transcript archives and search remain outside the initial proof. The component
will retain minimal observation metadata; historical evidence systems have
different storage and content responsibilities.
