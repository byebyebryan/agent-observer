# Retention CPU repair

The [execution gates](../../collector-cost-follow-up.md) repair the
[profiled a11 hotspot](../2026-10-09-collector-cpu/REPORT.md), preserving API 2,
snapshot/watch 4, Service 2 and native observation semantics. C0–C3 source, immutable artifact and native gates are accepted. Sustained
candidate cost and scoped collector selection remain pending at this checkpoint.

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
