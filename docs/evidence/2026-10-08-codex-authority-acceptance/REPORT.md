# Codex daemon-authority acceptance

Date: 2026-10-08. Status: D1–D4 accepted for the independently installed
`0.5.0a3` Codex candidate on Snap and Starship. The supported writer subset has
its own native acceptance below. Normal links and user services still select
`0.4.0a16`; no managed rollout or frontend migration is accepted by this report.

## Artifact and authority

The frozen source is `2818e1bd6ba03d7abb0c00f392740c94616f19ac`.
The wheel is `agent_observer-0.5.0a3-py3-none-any.whl`, SHA-256
`3cee9e01474be64632fa406952e2763c5972630261a967846847a1eedef15f64`.
Its [manifest](../../../artifacts/observer-0.5.0a3.json),
[Snap installation](snap-artifact.json) and
[Starship installation](starship-artifact.json) bind the same core-only prefix:
`/home/bryan/.local/share/agent-observer/0.5.0a3-3cee9e01474be646`.
There is no bundled native executable or Claude SDK in this artifact.

The interim [a2 manifest](../../../artifacts/observer-0.5.0a2.json) is retained
as provenance, not final acceptance. Its Snap comparison passed, but Starship
exposed a native typed memory-consolidation child that remained unknown in that
candidate. A3 recognizes the validated typed variant and repeats its own
both-host artifact/native gate; it does not inherit a2's partial result.

API 2 uses snapshot/watch wire 4, local service protocol 2 and a separate writer
wire 2. The daemon supplies exact thread status; observation does not inspect
TUI/tmux attachment or own provider lifetime. Clients own New/Resume, foreground
entry and terminal placement. This candidate deliberately rejects Claude and
the previous read/service/write wires. There is no private saved-store fallback.

The observed owning daemons are `0.162.0`; the independently copied native TUI
image is `0.161.0` on both hosts. [Native provenance](native-provenance.json)
records bytes, namespace isolation and diagnostic versions. These are test
provenance, not compatibility allowlists. Support binds the required passive
status, database-only catalog, exact identity and TTY-entry contracts.

## Independent ordinary comparison

The stdlib native oracle imports no Observer module. It reads the authenticated
ordinary daemon before and after the installed public CLI. It now treats current
catalog/detail status as authoritative independently of loaded-list membership,
and separately checks readable saved identity, exact IDs and native turn clocks.

| Host | Native/public rows | Running | Parked | Known activity clocks | Native classification |
| --- | --- | --- | --- | --- | --- |
| Snap | 89 | 2 | 87 | 52 | 51 user, 38 child |
| Starship | 353 | 5 | 348 | 105 | 80 user, 252 child, 21 unknown |

Two direct rounds and one cached round per host have zero issues:
[Snap direct](snap-direct.json), [Starship direct](starship-direct.json),
[Snap cache](snap-cache.json), [Starship cache](starship-cache.json).
The final oracle adds explicit `hasSavedHistory` checks without weakening saved
active-clock requirements: [Snap final](snap-final-direct.json) and
[Starship final](starship-final-direct.json), also zero issues.
The active roots are Snap's agent-observer and tmux-plus, and Starship's fluid-2.5d,
pd-lab-next, raster90, devlog and sleep. Phase changes between rounds are compared
against bracketed native samples; the receipt is a sampled observation, not a
promise that these sessions remain active indefinitely.

The cached Snap sample also records native systemError for tmux-plus as
running/unknown phase. A later direct sample reports working. The earlier error
remains provider-state evidence, rather than being normalized to waiting or
treated as an unavailable source.

Default child filtering, include-children inventory, urgency/activity ordering,
human age, exact-reference show and doctor counts passed. Known children are
hidden; the 21 older Starship records with unproved native classification remain
visible as unknown. Missing native title/activity/outcome fields are counted as
unproved, rather than reconstructed from names, files or collection time.

The catalog is the bounded native database-only, non-archived saved inventory,
with all ten declared source kinds, complemented by loaded/runtime records.
It is not a filesystem census, an archived-history browser or an unlimited
recent-history guarantee. Row/page/byte bounds and unreadable native summaries
make coverage partial rather than silently excluding supported running records.

## Isolated native state and passivity

All provider actions use owned private user/mount/PID/tmp namespaces, disposable
provider homes and borrowed authentication. Ordinary provider paths and images
are masked before entry. Action/PTY helpers may import transport code; their
reference comparisons use the separate stdlib native oracle. Terminal output is
drained and discarded. Only bounded predicates, identity and event clocks are
retained in these receipts.

| Case | Snap | Starship | Accepted result |
| --- | --- | --- | --- |
| All-parked startup | [read](snap-native-read.json) | [read](starship-native-read.json) | Positive native notLoaded/readable saved identity agrees with direct, cached and pushed parked rows; phase null |
| Held work/input | [monitor](snap-native-monitor.json) | [monitor](starship-native-monitor.json) | Working is observed directly; approval/question waits and initial waiting agree with direct/cache/push and native age; interrupt returns native idle/direct waiting |
| Database-only catalog | [catalog](snap-native-catalog.json) | [catalog](starship-native-catalog.json) | Three database-only queries omit an owned unindexed log and do not repair it; explicit default-repair negative control reinserts metadata |
| Daemon outage/recovery | [recovery](snap-native-recovery.json) | [recovery](starship-native-recovery.json) | Three direct reads return unavailable/empty without starting a daemon; cached/pushed saved rows become unknown with their original age; explicit New and exact Resume recover |
| New-turn outcome | [outcome](snap-native-outcome.json) | [outcome](starship-native-outcome.json) | Fast native sampling clears an older completion during a new turn and publishes the new terminal clock while the slower history sample remains unchanged |

The catalog negative control accepts the no-repair selector semantics in an
owned store. It is not a blanket audit of every provider filesystem write.
The monitor uses a continuously draining push reader and allows bounded initial
sample convergence. Earlier harness attempts exposed a slow-reader mistake and
native runtime-only stubs with unproved creation/activity clocks. The corrected
oracle reports those fields as unproved, rejects invented activity, and preserves
the native unknown result. It does not accept stable creation chronology for
uninitialized runtime-only stubs.

No experiment establishes post-TUI-closure lifetime or headless entry. Parked is
accepted from positive current daemon responses; this report does not infer why
those native contexts were unloaded.

## Separate native writer gate

New, initialized saved/live exact Resume and repeated TTY entry passed through
the installed writer on both hosts. Native conversation clocks remain unchanged
by Resume, read, rename and owned housekeeping. Offline Resume fails finitely;
only explicit New restarts the private daemon. Preparation/revalidation are
passive; `enter` is the explicit native action boundary.

[Snap fork](snap-native-fork.json) and [Starship fork](starship-native-fork.json)
verify a new turn targets the exact fork while the original conversation's
latest turn is unchanged. Both native fork cases returned equal thread/tree-root
IDs. The unequal-ID TUI case was not produced and remains guarded with
`session_tree_entry_unproved`; an initialized history proof does not accept blank
runtime-only Resume. These limits do not weaken read-side daemon authority.

## Read transport, workspace and cost

Packaged schema/strict-reader conformance passed with an independent jsonschema
reader on [Snap](snap-public.json) and [Starship](starship-public.json), including
maximum 4096-row serialized inputs and exact references. [Sampled watch](watch.json)
has valid wire-4 snapshots/heartbeats and parked phase null on ordinary inventories.
Native cached push covers gap/resync, monotonic sequence/revision, preserved age
through failure/recovery and a fresh subscriber's complete view.

Owned publisher [Snap lifecycle](snap-service-lifecycle.json) and
[Starship lifecycle](starship-service-lifecycle.json) accept missing-service
non-autostart, singleton and wrong-host rejection, forced publisher EOF, helper
self-expiry, stale socket recovery, new service incarnation and graceful cleanup.
This does not replace a managed user-unit rollout/rollback gate.

Independent local Git/root/project checks match direct and cached views:
[Snap](snap-workspace.json) and [Starship](starship-workspace.json).
The controlled [notification adapter](notifications.json) passes wire-4 input and
exact-reference/title handling; physical notification delivery is not accepted.

| Four-minute owned service check | Snap | Starship |
| --- | --- | --- |
| Runtime/history cadence | 30/120 seconds | 20/60 seconds |
| Native hints | enabled | enabled |
| Cached CLI reads | 100 | 100 |
| p95 read time | 105.23 ms | 145.87 ms |
| Publisher plus owned helpers, one-core CPU | 1.65% | 4.87% |
| Peak aggregate RSS | 69,029,888 bytes | 77,385,728 bytes |
| Healthy push readers | 3, zero errors | 3, zero errors |
| Observed gaps per reader | 3, with replacement views | 6, with replacement views |

[Snap cost](snap-service-soak.json) and [Starship cost](starship-service-soak.json)
include the read burst and one connected unread slow client. These are finite
four-minute checks, with explicit gaps rather than lossless delivery. They are
not matched incremental a16 CPU comparisons, 30-minute managed-unit soaks or
physical suspend/wake acceptance. The relaxed memory target remains a reported
cost, not a strict 64 MiB rejection gate.

## Delivery and remaining scope

[Cleanup](cleanup-and-preservation.json) verifies both owned namespaces stopped
and borrowed authentication/private history were removed. Ordinary daemon
incarnations match the first acceptance samples. Configuration, frontend links,
normal Observer links and user-unit bookends are identical across cleanup;
the narrower cleanup-window comparison is not a full-loop configuration audit.
The a3 prefix remains installed and unselected; both normal services remain
a16/protocol 1. No ordinary provider action or downstream edit was required.

The next delivery gate is an explicitly scoped Observer-only selection with
restart/crash/reconnect/rollback receipts. Claude must first reconcile its own
authority and native workflow to API 2; no background-job or Codex-topology
assumption is inherited. [API 2 client handoff](../../api-v2-client-handoff.md)
allows separate consumer work against the explicit candidate. Networking,
Agent Plus, Tmux Plus, dashboards, physical notifications, sleep/wake and the
deferred identity/lifetime cases retain their own gates.
