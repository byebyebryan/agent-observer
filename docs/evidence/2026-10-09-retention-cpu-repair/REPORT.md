# Retention CPU repair

The [execution gates](../../collector-cost-follow-up.md) repair the
[profiled a11 hotspot](../2026-10-09-collector-cpu/REPORT.md), preserving API 2,
snapshot/watch 4, Service 2 and native observation semantics. C0–C2 source gates
are accepted. Immutable artifact, independent native, sustained candidate cost
and scoped collector selection remain pending at this source checkpoint.

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
