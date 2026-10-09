# Finite runtime-only observation retention

Date: 2026-10-09. Producer source, immutable artifact and focused native/read
acceptance complete; the separate scoped normal read/service operational gate
also passes on Snap and Starship. Normal commands select a11 and the writer
independently stays a16. This checkpoint changes no frontend, provider policy
or ordinary sessions.

## Artifact and policy

The accepted candidate is `0.5.0a11`, source
`0b1420a161def114ed8d4a09d220905531a7d254`, wheel SHA-256
`b1b755c8df0d4676f5f5f8fb47f10b689dabfadcd95593565da31e15af7e40eb`,
prefix `~/.local/share/agent-observer/0.5.0a11-b1b755c8df0d4676`.
The [manifest](../../../artifacts/observer-0.5.0a11.json) retains API 2,
snapshot/watch wire 4, independent writer wire 2 and service protocol 2.
Snap installs source-only Claude-history SDK 0.2.163; Starship installs core.
The SDK/build and provider versions are provenance, not native support allowlists.

Shared-core deadline memory uses exact scoped identities and host-local BOOTTIME.
Service retention expires at the original accepted runtime lease, not the newest
partial receipt: 90 seconds on Snap and 60 seconds on Starship at normal cadence.
Current accepted rows are protected, including unsaved rows with unknown phase.
Positive saved proof from either component protects the identity and original
conversation age through faults. Expired unsaved rows are removed from both
component caches; delayed metadata cannot restore them. Fresh exact reappearance
supplies new evidence. No retention/heartbeat/enrichment/delivery clock becomes
conversation activity. Bookkeeping follows bounded component rows and dies with
the collector incarnation.

Direct sampled watch uses a fixed 60-second bound from collection start and
applies expiry at the next sample. Collection gaps invalidate the view until
resync. A one-shot direct read retains no previous memory. Retirement is omission
of stale observation memory, never parked, ended, deleted or action permission.
Full pushed views carry removal; no public native-event stream is introduced.
See the [policy and execution plan](../../runtime-only-retention-follow-up.md).

## Rejections and focused repair

The first frozen a10 candidate passed native normal-exit expiry but failed its
forced-kill gate. The [partial receipt](a10-native-partial.json) and
[independent admission finding](a10-native-admission-gap.json) show a dead,
unsaved interactive registration absent from the native runtime/history oracle,
yet still returned as a fresh unknown candidate by the adapter. Core could not
retire a repeatedly supplied identity. A11 also omits this residue when a
healthy native bracket/guard and every matching interactive incarnation prove
absence, with no saved identity or relevant unresolved/background conflict.
It preserves native files, all live matching incarnations, saved proof and
uncertainty. The provider predicate stays entirely in the passive Claude adapter.

Two a11 harness attempts remain explicit evidence, not accepted runs. The
[timing attempt](a11-harness-timing-partial.json) asserted immediately after
forced exit, before the next collection; the corrected harness waits for bounded
sample convergence and discards pushed views on gaps. The
[named-empty attempt](a11-named-empty-partial.json) became saved during native
exit because the fixture used a name. Saved identity must survive; expiry cases
now use unnamed disposable sessions. Neither issue required changing the frozen
a11 wheel. [Harness hashes](proof-harnesses.json) bind the accepted proof helpers;
the native oracle imports no Observer implementation.

## Installed and native acceptance

`./scripts/check` passes 399 tests with one existing skip, Markdown/local-link
and diff checks. [Installed regressions](installed-regressions.json) run 41 tests
with isolated installed imports outside the checkout. The separate
[schema consumer](consumer-conformance.json), jsonschema 4.26.0, validates strict
input/selection/order and 4096-row CLI serialization with zero provider actions.
These are source/package/interface checks, distinct from native proof.

The [native receipt](native-retention.json) uses owned disposable user/mount/PID
namespaces, private provider paths, Agent View on and all hooks disabled.

| Native case | Installed result |
| --- | --- |
| Unnamed New and `/exit` | Native runtime/saved identity absent; direct, cached pull, pushed view and sampled watch omit the UUID after bounded retention; stale unknown precedes retirement; all-path convergence 58.988 seconds |
| Exact unsaved UUID reappearance | All four read paths restore the same scoped reference as running with a new native incarnation |
| Registry source fault/recovery | Native scan fault remains explicit; cache/push preserve unknown during the bounded gap; exact live identity recovers across all read paths |
| Forced kill after recovery | Dead native record may remain; authenticated runtime and saved identity absent; direct/cache/push/watch omit the UUID; all-path convergence 59.935 seconds |
| Saved New/exit/Resume/exit | Independent native brackets agree with direct/cache/push on running/waiting and parked/null; activity remains `1791535287842` through Resume and final exit |

The stream records 198 service frames and 141 direct-watch frames. Sequence,
incarnation and read convergence pass within the bounded run. This is sampled
delivery, not lossless event replay. [Cleanup](native-cleanup.json) stops the
owned namespace and removes borrowed authentication/history. A9's prior on/off
and wider lifecycle cases retain their historical artifact bounds; this focused
a11 native proof uses Agent View on and makes no new off-mode or generic-dialog claim.

## Ordinary native comparison and service readers

Every comparison has two independent native-before/CLI/native-after rounds:
[Snap direct](ordinary-snap-direct.json), [Snap cache](ordinary-snap-cache.json),
[Starship direct](ordinary-starship-direct.json) and
[Starship cache](ordinary-starship-cache.json). The reference uses owning Codex
daemon status and Claude provider-owned registrations/incarnations/saved metadata;
no terminal inventory or another normalized Observer result is authority.

All 89 Snap Codex and 354 Starship Codex rows agree on runtime/phase; all 35
Claude rows agree within the accepted registration assumption. All 14 running
contexts match. Comparable conversation clocks, child filtering, age/attention
ordering, exact selection and diagnostics pass. The accepted setup-only Claude
cwd omission remains the sole metadata mismatch. Candidate cached Claude has
35 rows, without a9's additional disappeared unsaved identity. Re-starting a
candidate alone does not prove retirement; the live unsaved cases above do.

[Snap](candidate-readers-snap.json) and [Starship](candidate-readers-starship.json)
three-minute separately owned candidate publishers each pass 100 cached reads,
three independent healthy watchers and an unread subscriber, with zero watcher
gaps/errors. Their ordinary units remain unchanged. CLI p95 is about 274/377 ms
under this concurrent proof workload; peak aggregate publisher/helper RSS is
about 115/73 MiB. These are bounded reader/resource samples, not matched latency,
long-term stability or physical wake acceptance.

## Remaining boundaries

The separate scoped operational gate is complete; its evidence follows below.
Writer a16, workspace mapping, provider settings and frontend selection remain
independent.

Invisible Claude registration can still cause missed running or false parked;
background runtime remains unsupported. Accepted setup metadata, generic dialogs,
nested child history, Claude turn outcomes and older Starship kinds retain their
limits. This repair introduces no client inventory, tmux/TUI authority, native
mutation, notification event contract or networking implementation.

## Scoped operational acceptance

[Snap operations](operations-snap.json) and
[Starship operations](operations-starship.json) bind prior a9 preflight, a11
first selection, exact six-target a9 rollback, a11 reselection, installed artifact
and live unit checks, restart/forced-publisher-failure/reconnect and unchanged
provider settings. Each failure proof ends the old watch; reconnect starts at
sequence one under a new service identity. Only owned Observer publishers are
restarted or killed. No ordinary provider action, frontend target or lingering
change occurs. Managed source commits are Snap `9015eb1` and Starship `0c6611d`.
Unrelated Snap generated bytecache and Starship Kitty/source divergence remain
untouched.

Private rollback snapshots retain a9 at
`~/.local/state/agent-observer/rollback/20261009-a11-snap` and
`~/.local/state/agent-observer/rollback/20261009-a11-starship` on their hosts.
The final selected service identities are Snap
`1a79cb4d-104e-4523-8194-7901ab0b5a3f` and Starship
`a93b577e-6746-4015-87c7-6f87149f3bf4`.

[Snap normal readers](normal-readers-snap.json) and
[Starship normal readers](normal-readers-starship.json) each pass three minutes,
100 cached reads, three healthy watchers and an unread subscriber. Healthy
watchers receive 27/21 frames each with zero gaps/errors. CLI p95 is about
281/437 ms; peak aggregate publisher/helper RSS is about 114/75 MiB, with 37/23
file descriptors and 5/3 owned processes at sampled peaks. The harness's
runtime/history/nativeHints fields are launch defaults, not existing-unit
configuration: exact live operations verify Snap 30/120 seconds and Starship
20/60 seconds, both with native hints. These bounded checks run alongside native
comparisons, include cached-reader/collection work and are not idle-cost,
matched-latency, long-duration or physical-wake acceptance.

Post-selection [Snap direct](selected-snap-direct.json),
[Snap cache](selected-snap-cache.json),
[Starship direct](selected-starship-direct.json) and
[Starship cache](selected-starship-cache.json) each repeat two independent native
brackets through normal commands. All 89 Snap Codex, 35 Snap Claude and 354
Starship Codex runtime/phase classifications agree; all 14 running contexts and
comparable conversation clocks remain correct. The only metadata mismatch is
the accepted setup-only Claude cwd omission. The disappeared unsaved a9 row is
absent from selected cached views; isolated live expiry above, rather than the
restart alone, proves the repair. The [client handoff](../../api-v2-client-handoff.md)
now names the selected a11 tuple and finite-retention consumer meaning.
