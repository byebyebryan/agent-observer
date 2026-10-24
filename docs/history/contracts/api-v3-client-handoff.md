# API 3 read-client handoff

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

2026-10-13. The producer supplies Codex-only discovery and monitoring, native
latest-turn and thread-update metadata, local cached pull/push, and optional
two-host Mesh delivery. [Observer a2](../../../artifacts/observer-0.6.0a2.json) is the
exact read/service/publisher artifact. Its [acceptance record](../../evidence/2026-10-13-native-timing-rollout/REPORT.md)
distinguishes installed/native, controlled transport and managed deployment proof.
RLCD/349 own their feed, clock presentation and physical rendering acceptance.
Agent Plus, attachment/actions, approximate phase tracking and richer notification
events remain deferred. Claude native use remains external to Observer.

## Contract and ownership

Bind to [API 3](api-v3.md), snapshot/watch wire 5, Service 3 and the explicit
`agent-observer.mesh-candidate.v2` profile through Mesh SDK 1. Read 1 and Delivery
1 remain unchanged. The packaged schemas and descriptor are strict; do not
convert older observations or mix a Service 2 reader with the new endpoint.
The historical writer and Tmux's profile/factory remain independent.

Key a row by host/provider/namespace/native-kind/native-ID. A Codex thread ID is
the session identity; its tree root is separate metadata. The owning daemon
supplies running/parked and work phase. TUI/tmux presence, cwd, title, PID,
completion and loaded-list absence cannot establish runtime state. Parked needs
a current positive saved-thread `notLoaded` observation; idle means running and
waiting. Confirmed children are hidden by default; unknown historical kinds stay
visible with their limitation. Do not merge references because their titles or
project paths match.

Discovery, runtime, phase, activity and each timing dimension have independent
evidence health. A stale/unavailable observation is not idle or an empty roster.
One failed source does not invalidate healthy siblings. Warm-up null, partial
coverage, gaps, expiration and new service/source/clock incarnations require
conservative admission and resynchronization. Current-state push sends accepted
replacement views; it does not replay every native transition or notification.

## Clock meanings

| Data | Supported meaning | Display limit |
| --- | --- | --- |
| `activity.at` | Last conversation activity; completion else start | Existing default age/order clock; missing or stale stays explicit |
| `lastUpdated.at` | Native thread-update timestamp | Can change during work or metadata operations; never phase entry |
| `latestTurn.value.startedAt` | Native latest-turn start | Includes blocked time; nullable, second-resolution on Codex |
| `latestTurn.value.completedAt` | Native terminal-turn completion | Does not establish when an idle runtime was resumed |
| `latestTurn.value.durationMs` | Independent native terminal duration | Can differ from rounded end minus start |

A current null latest-turn value is known-empty. An unavailable/stale null has a
different meaning; inspect health. Previously admitted values may survive only
under the explicit last-known fields, with original provenance. Never join a
new turn to an old boundary or treat last-known values as current timers.

`agent_observer.public.age_ms` uses source-wall age at the original observation;
negative clock deltas remain unknown. `ongoing_turn_age_ms` also checks that
current runtime/phase and in-progress timing support the display. Non-atomic
contradictory reads suppress the timer; compatible samples are not an atomic
status/turn join. Exact blocked/current-phase age is unavailable.

For local cached Python clients, admit/expire a Service 3 frame through
`agent_observer.service_public.ReadCache` before passing same-domain
`now_boottime_ms` to the timing helper. Never substitute a device's clock or
another host's BOOTTIME. A field's receipt names its original runtime/history
component sample and source generation. Heartbeats, a different component,
duplicate delivery and client reconnect cannot renew it.

For remote clients, Mesh's profile, ReadGuard, reader clock and proof accounting
own lease admission. The existing remote human CLI displays source-sampled
timing ages; it does not advance them using the receiving host's wall clock.
A dashboard can initially display those sampled ages and refresh on accepted
views. A continuously advancing remote timer needs an independently accepted
source-to-reader clock policy; this handoff does not claim that a device clock
and a native Unix timestamp provide an exact timer. Expiry/disconnect must revoke
current display even when no new frame arrives.

Default urgency remains blocked, waiting, working, then unknown/parked, with
conversation activity newest first. Clients choose labels and sorting policy;
the new update clock does not silently change existing activity ordering.

## Commands and pure clients

On the owning host, replace `snap` with `starship` there:

```sh
agent-observer api
agent-observer service api
agent-observer mesh api
agent-observer service list --host-scope snap
agent-observer service watch --host-scope snap --count 3
agent-observer service watch --host-scope snap --human
agent-observer mesh list
agent-observer mesh watch --human
agent-observer mesh assess --scope fleet --mode subscribe --timeout-ms 15000
agent-observer schema --kind snapshot
agent-observer schema --kind watch
agent-observer service schema --kind request
agent-observer service schema --kind frame
```

The local endpoint is `/run/user/1000/agent-observer/read.sock`; the resident Agent
Mesh endpoint is `/run/user/1000/mesh-plus-agent/read.sock`. Cached reads never
autostart a service or fall back to native acquisition. For an independent
native refresh, explicitly use `agent-observer snapshot --host-scope snap
--provider codex` without the service prefix. Direct reads can be slower and
their timing receipts are null; they grant no cached lease authority.

Python clients use `agent_observer.public` and `service_public` for strict pure
parsing/admission; `service_client.frames` provides local delivery. Mesh clients
inject `agent_observer.mesh_profile.AgentProfile()` into every configured reader,
guard, reconstruction/current-view helper and read request. One Mesh-validated
view can feed multiple dashboard outputs. Other languages must implement both
the exported schemas and their documented semantic/receipt checks.

The generic Mesh CLI/default Agent descriptor intentionally remains profile v1
for older owners. It is not the entry for this v2 Agent endpoint. Use the
Observer-owned `agent-observer mesh` commands or an explicitly selected profile;
an unsupported profile fails closed. Tmux keeps profile v1.

## Consumer acceptance and remaining limits

Start client work against the accepted schemas and producer commands. Each client
still needs separate roster/filter, urgency, missing/stale clocks, gap/reconnect,
expiry/disconnect, bounded feed and display tests. Validate human CLI labels
`ACTIVITY_AGE`, `NATIVE_TURN` and `THREAD_UPDATE_AGE` without conflating them.
Provider support follows required contracts/capabilities, not daily version
allowlists. Saved-native timing is currently Codex-only; unproved runtime-only
timing stays unsupported. Bounded native inventory, historical unknown kinds,
native creation/sampling races and post-TUI-closure/physical-suspend lifetime
checks retain their accepted limits. No provider action, terminal matching,
frontend migration or device flashing is authorized by read acceptance.

## Managed role and rollback notes

The selected collector, read CLI and Agent publisher all use the immutable a2
prefix. Normal service units are `agent-observer.service` and
`mesh-plus-agent.service`. Their selectors live in the managed dotfiles
`deployments/agent-observer.json` and `agent-observer-mesh.json`; the common
launcher has a reviewed profile-v2 path selection and two lazy factories.
The previous a18 collector / a20 reader-publisher / Mesh a15 remains installed.

Each host retains a private exact baseline at
`~/.cache/agent-observer-timing-20261013/paired-baseline.json` (mode 0600 in a
0700 directory). It contains original/candidate controls and selectors. The
[acceptance harness](../../evidence/2026-10-13-native-timing-rollout/paired-selection.py)
records the guarded transition, not an unscoped apply or a provider action.
For a later coordinated rollback, verify captured controls and current unit
entry/interpreter/start identity, stop only those two owning Observer units,
restore the captured collector/read/publisher selectors and target bytes,
reload user units, then start collector before publisher. Validate the old API 2 /
Service 2 / Agent-profile-v1 tuple together before accepting reads. Reselection
uses the same guarded procedure with the captured a2 controls. Stop on unrelated
drift; do not overwrite it. Tmux controls/owner and the historical writer are
outside this transition.

The older Mesh-only rollback tool cannot establish a valid old read tuple while
leaving the Service 3 collector selected. The paired old/new rollback and
reselection were exercised on both hosts; their receipts are in the producer
acceptance record. This read handoff supplies no provider/attachment authority.
