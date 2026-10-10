# Retention CPU repair

The [execution gates](../../collector-cost-follow-up.md) repair the
[profiled a11 hotspot](../2026-10-09-collector-cpu/REPORT.md), preserving API 2,
snapshot/watch 4, Service 2 and native observation semantics. C0–C5 source, immutable artifact, native, sustained-cost and scoped operational
gates are accepted. Normal collectors select a14 on Snap and Starship; the read
CLI, writer and Mesh bridge retain their independent selections.

## Source behavior and review

Retention reconciles on accepted receipt replacement, source failure, component
lease expiry or the next eligible unsaved deadline. Each changed reconciliation
validates a row identity once and reuses that key locally. Private per-provider
dirty flags and the next eligible deadline skip full roster scans on quiet ticks.
These caches contain no provider facts and add no public fields. Admission still
validates incoming snapshots and owns deep copies; public publication validation
is unchanged. Lease checks remain independent and cheap on every service loop.

Saved identities and current native rows remain protected. Only unprotected
survivors establish a time-only retirement deadline. The deadline is recomputed
after ledger pruning so a missing ledger cannot postpone an existing omission.
Accepted history samples can atomically replace runtime/history and invalidate
the same provider cache; context changes stale other receipts before publication.
Rejected samples leave the cache untouched. Failure/expiry invalidates protection
without updating conversation age or making unknown runtime parked.

The mutation audit finds engine-owned receipt replacement/health updates only;
service callers do not mutate receipt rosters or retention ledgers directly.
The direct sampled-watch retention helper and passive adapters are unchanged.
No terminal inventory, action, provider policy, networking or frontend work is
included. Source version becomes a14 only for a new immutable package; public
contract versions stay unchanged.

## Behavioral and cost evidence

[Source validation](source-validation.json) passes 429 tests without skips in the
existing optional-Mesh interpreter. Ten seeded traces compare 1,200 mixed Codex/
Claude transitions with the frozen a11 full-scan reference in test-only code:
accepted/rejected runtime/history replacements, partial/unavailable/complete
coverage, context changes, failure, heartbeat and exact lease expiry. Snapshots,
revisions, receipt data/public metadata, namespaces/context generations and
retention ledgers match after every operation. Existing fourteen retention/watch
cases retain their source bounds.

Additional regressions require 2,000 saved-roster quiet ticks to avoid repeated
identity validation, preserve an unsaved candidate until its exact deadline and
reject malformed incoming identity without changing owned evidence. This tests
the measured work property rather than requiring a particular cache layout.

The [matched cached-data study](source-cost.json) runs the new engine and frozen
full-scan method under the same interpreter with 128 saved rows and a fixed clock.
Two hundred quiet expiries consume 0.000242 CPU seconds versus 4.247 seconds for
full scans. Fifty profiled optimized calls perform zero identity validations.
Separate five-call tracemalloc runs peak at 192 versus 38,600 bytes. View, receipts
and deadlines remain unchanged. These are source Python 3.14.7 measurements,
not Snap's installed Python 3.12 collector or live service savings.

The [study operator](../../../scripts/study-retention-repair) reads one cached
Service 2 view, keeps all row payloads in memory, compiles only the frozen pure
reference method from the test file and emits bounded counters/hashes. The
component rosters are replicas of merged cached data, not private live receipts.
CPU, allocations and cProfile are separate runs. Installed and native gates must
establish actual package behavior and sustained savings before selection.

## Immutable installed/native acceptance

[a14](../../../artifacts/observer-0.5.0a14.json) freezes source commit
`d567306e0f0113f3c72aa295f7d3ded8c77b8adf`, wheel SHA-256
`16a223f224addc5bf92174be385372e85eb864ba3670d07e7941e7c3485caddf`.
Both hosts install into the new prefix
`~/.local/share/agent-observer/0.5.0a14-16a223f224addc5b`. The passive verifier
accepts exact installed bytes, entrypoints, SDK profile and unchanged contracts.
Snap retains Python 3.12.8 with source-only Claude SDK 0.2.163; Starship uses
Python 3.14.7/core. Existing immutable prefixes are untouched.

The wheel audit against selected a11 finds provider adapters, collection helpers,
service runtime/scheduler byte-identical; `serve` only reorders local imports.
Other changed modules contain the previously accepted a12/a13 read facade, including the
Service read-cache export; only engine retention adds new collector behavior.

[Installed validation](installed-validation.json) runs an affected 86-test
subset from a copied harness outside the checkout, using `-I -B` and installed
imports only. Snap passes all; Starship skips one independent JSON Schema test
because that dependency is absent from the core profile. The source optional
Mesh environment passes all 429 tests, including that schema test. No native
provider executable is bundled with the SDK.

The matched studies use each candidate's exact collector interpreter and cached
host roster: [Snap](installed-cost-snap.json), 128 saved rows, costs 0.000397
versus 7.739 CPU seconds for 200 expiries; [Starship](installed-cost-starship.json),
354 saved rows, costs 0.000089 versus 5.099 seconds. Both optimized profiles
perform zero identity validations on quiet ticks. This is isolated engine cost,
not sustained live-service CPU.

Independent native brackets compare installed direct reads
([Snap](native-direct-snap.json), [Starship](native-direct-starship.json)),
candidate cached pull ([Snap](native-cached-snap.json),
[Starship](native-cached-starship.json)) and initial complete pushed views
([Snap](native-push-snap.json), [Starship](native-push-starship.json)).
The candidate runs beside a11 on explicit private sockets, with the ordinary
30/120-second Snap and 20/60-second Starship cadences and native hints. Snap has
91 Codex and 37 Claude rows, including three active sessions each; Starship has
354 Codex rows, including six active sessions. All active membership, runtime
and phase match. Codex has zero comparison issues across these probes.

Push probes translate only `service snapshot` to the installed
`service watch --count 1 --include-children`, preserving the complete inventory;
all other CLI operations execute unchanged. The first probe omitted child rows
because human watch filters children by default; that probe was rejected and
is not acceptance evidence. Final reports bind the corrected proxy hash.
They prove initial delivery, not ongoing native transition completeness.

The comparison reports retain unresolved metadata explicitly: setup-only Claude
UUID `e0cba9dd-b642-4730-af4b-beb3b7e9c16c` has unavailable cwd/kind/age,
already documented in the accepted baseline. Direct a11/a14 reads both return
that same missing metadata. Cached/pushed Claude conversation clocks sometimes
lag a newer native bracket by the independent sample cadence; direct reads
match. No poll or liveness clock is substituted for conversation activity.
These are existing sampling/metadata bounds, not changes introduced by the repair.

The [isolated installed retention proof](native-retention-snap.json) masks
ordinary provider homes before launching disposable Claude sessions. Normal
exit and forced kill of unsaved sessions produce stale/unknown retained rows
with unchanged original evidence clocks, then finite omission in direct,
cached, pushed and sampled-watch views. Exact UUID reappearance restores the
same logical reference with a new authenticated process. Native registration
source fault/recovery stays unknown then recovers running. Saved history,
Resume and conversation age remain protected. The proof records 196 Service 2
and 150 direct-watch frames. Namespace teardown removes borrowed credentials
and private history; ordinary provider settings and sessions are unchanged.

## Sustained candidate cost

Both transient candidate units run for a measured 600 seconds after 30 seconds
of warmup, using ordinary provider sources and unchanged cadence/native hints.
The [counter operator](../../../scripts/measure-collector-cost) authenticates
systemd MainPID/UID/incarnation and the collector entrypoint; it samples the
bounded owned process tree and separates root CPU from helpers, including reaped
child ticks. It adds no readers or provider operations. Counter receipts retain
no provider payloads. This is ordinary active-host cost, not an idle benchmark.

a11 remains running beside each candidate. Snap's first segment overlaps the
installed/native validation in an isolated namespace; Starship has no disposable
provider sessions. Concurrent workloads and duplicated passive collectors are
explicit limits. A following normal-unit window after teardown/selection must
confirm the sustained production result.

| Host | a11 recent total percent of one core | a14 root | a14 helpers | a14 total | Mean/peak aggregate RSS MiB |
| --- | --- | --- | --- | --- | --- |
| [Snap](candidate-cpu-snap.json) | 57.5–62.8 | 3.520 | 11.527 | 15.047 | 73.2 / 115.6 |
| [Starship](candidate-cpu-starship.json) | 36.6–39.0 | 1.117 | 0.885 | 2.002 | 52.2 / 74.2 |

The old CPU windows and profiling have separate timing/workload bounds in the
[profiling report](../2026-10-09-collector-cpu/REPORT.md). They are not randomized
paired measurements. Both reductions materially clear C4 without promising a
fixed CPU floor. Snap's remaining helper cost is separate from the repaired root
hotspot; it is not hidden by reporting root alone. Aggregate PSS averages 36.5
MiB on Snap and 29.6 MiB on Starship. The resource samples return to three/two
processes and 21/12 FDs at the end; transient workers account for higher peaks.
Memory remains a review threshold, not a strict budget.

## Scoped normal selection

The six-target Observer tuple selects a14 services on Snap/Starship. Normal
provider homes, cadence, workspace, hints and contracts are unchanged. The read
CLI remains a13 and the writer remains a16. Apply verifies the immutable new/old
artifacts, exact old target bytes and unit incarnation before stopping the owned
collector. Both transient candidates were stopped before managed selection.

Independent first selection verifies installed a14 units on
[Snap](verify-initial-snap.json)/[Starship](verify-initial-starship.json), followed
by [a11 rollback on Snap](rollback-snap-fixed.json)/
[Starship](rollback-starship-fixed.json) and
[a14 reselection on Snap](reselect-snap.json)/[Starship](reselect-starship.json).
Private recovery snapshots retain the original six targets at
`~/.local/state/agent-observer/rollback/20261009-a14-snap` and
`~/.local/state/agent-observer/rollback/20261009-a14-starship`.

Initial rollback preflight failed before stopping either a14 collector: its
full-source render evaluated an unrelated unpublished Mesh external (HTTP 404).
The minimal chezmoi helper repair (`06b3237`) passes the explicit selection to `rendered`,
using the same six-target projection as verify/apply. Its new regression rejects
old rollback's global render; scoped self-tests pass on both hosts and actual
rollback/reselection then pass. This is operations tooling, not a wheel/API
change. No Mesh artifact, external pin or networking code is repaired here.

Existing managed-unit delivery passes with three simultaneous healthy readers,
a deliberately unread fourth peer and 100 cached snapshots per host:
[Snap](normal-delivery-snap.json), [Starship](normal-delivery-starship.json).
Healthy readers record 8/5 frames each with zero gaps/errors. The measured windows
are about thirty seconds, not a replacement for historical long-duration
acceptance. Native brackets using the separately selected a13 read CLI compare
normal cached pull ([Snap](normal-native-cached-snap.json),
[Starship](normal-native-cached-starship.json)) and initial push
([Snap](normal-native-push-snap.json), [Starship](normal-native-push-starship.json)).
The same 3+3 Snap and 6 Starship active contexts match membership/runtime/phase;
all Codex comparisons have zero issues. The documented Claude setup-only row and
sample-lag/native-transition clocks retain their bounds.

[Protected Snap paths](protected-verified-snap.json) and
[Starship paths](protected-verified-starship.json) keep provider configuration,
reader/writer links and each Mesh bridge PID/restart count unchanged. Ordinary
provider processes were never stop/action targets. Source preservation receipts
([Snap](unrelated-verified-snap.json), [Starship](unrelated-verified-starship.json))
record concurrent Mesh/Tmux source edits advancing during this loop. Those edits
were preserved; only the Observer tuple, operations helper and its documentation
are changed in canonical chezmoi source. The separate full chezmoi check is
blocked while rendering the package matrix by that separate Mesh a6 wheel 404;
scoped operations checks/dry runs,
exact-byte verification and live rollback/reselection are the Observer evidence.

Normal-unit sustained CPU acceptance passes on the final a14 incarnations:
[Snap](normal-cpu-snap.json) and [Starship](normal-cpu-starship.json). Each window
runs 600 seconds after 30 seconds of warmup, after candidate teardown and
completion of the bounded reader/native acceptance tests. No added sustained
readers or fixture sessions run in these windows; existing Mesh subscriptions
and ordinary host/provider workloads continue. All final root PID/birth values
match the [Snap](verify-final-snap.json)/[Starship](verify-final-starship.json)
verified normal units.

| Host | Normal a14 root percent of one core | Helpers | Total | Mean/peak RSS MiB | Mean PSS MiB |
| --- | --- | --- | --- | --- | --- |
| Snap | 2.720 | 8.290 | 11.010 | 71.4 / 115.9 | 37.8 |
| Starship | 1.115 | 0.908 | 2.023 | 52.0 / 74.2 | 29.4 |

End states return to 3/2 processes and 21/12 FDs. These bounded ordinary-host
measurements materially reduce the profiled a11 root/total CPU and retain the
accepted finite-retention behavior. They do not establish a strict idle floor
or long-term resource guarantee. Snap's remaining helper CPU warrants a separate
focused study before changing collection scope or cadence. Mesh subscriber costs
remain external. Public API 2/wire 4/Service 2, provider policies, ordinary hooks
and action/attachment boundaries are unchanged.

Post-soak native bookends ([Snap](post-soak-native-snap.json),
[Starship](post-soak-native-starship.json)) retain the same active counts and
zero Codex comparison issues. Claude's active runtime/phase/membership matches;
the setup-only metadata omission and a newer conversation clock than the cached
sample remain explicit. Source checks pass all 429 tests. Source, manifest and evidence are committed locally; exact wheels remain in
each installed artifact archive. Remote publication is a separate following
action, with no new release/hosted CI result claimed by this loop.

A final [cached fleet read](normal-mesh-read.json) through the unchanged a13 CLI
and existing Mesh bridge returns a complete transport view with 482 session rows,
matching the combined ordinary inventories. This is a one-shot read/reconnect
smoke check, not a new networking or frontend acceptance gate.
