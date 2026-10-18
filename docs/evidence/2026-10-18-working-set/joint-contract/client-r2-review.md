# Working-set P1 client review

2026-10-18. **Exact R1+R2 client contract accepted at bounded contract scope.**
R2 completes the independent branch and coverage lifetimes. The preparatory
helper's cutoff-range correction remains open; this signoff does not assert
helper conformance or producer/runtime acceptance. No view is implemented or
selected here, no identifier is allocated, and dark delta-sync remains deferred.

## Exact reviewed packet

Observer commit `995401e0a902c2f69571a731d7cd433f5bf40739`, in the isolated
`agent-observer-working-set` worktree:

| Artifact | Exact bytes |
| --- | --- |
| `docs/working-set-contract-r1.md` | 16,800 bytes; SHA-256 `4b4f55dff8308daee6aec442848a6c841c8e18b128ef4b91c01959e87aa33ec8` |
| `docs/evidence/2026-10-18-working-set/p1-review.json` | SHA-256 `84546ecfc2ee67dfde9b53202b7f8cfb5a065873bd5b7537150576c40c5a7755` |

All 17 packet artifacts and 15 declared source inputs match the immutable Git
objects. The saved 961-test canonical result was verified, not rerun. Candidate
native/profile identifiers remain unallocated and unfrozen.

The announced R2 supplement is Observer
`58b04ac478edcfb47ab1695199f7db728d5a1238`:

| Artifact | Exact bytes |
| --- | --- |
| `docs/working-set-contract-r2.md` | 6,604 bytes; SHA-256 `937d442402064a4e43258412d12e906fd5ca98b7fe0244c45f9ac1699884ccea` |
| `docs/evidence/2026-10-18-working-set/p1-r2-review.json` | SHA-256 `eed4a58e1b9a3ed25012d0a0ba54ad512ea4b6867a6a50b74629de1522a76224` |

All ten R2 manifest artifacts match immutable Git objects. Source, tests and
`pyproject.toml` are byte-unchanged from R1. Original R1 bytes and the initial
review at RLCD `26c0c48749e5f6f7658dc2177d5c1ae6cbed5c2f` remain provenance.

## R2 completion and exact client signoff

The service-level scalar `K=max(W-L+1)` is a conservative replacement for
per-identity positive-cutoff history: `T+Q-K` equals the minimum of all accepted
candidate lower cutoffs for fixed T/Q. K is nondecreasing within its clock
incarnation and survives roster, capacity, namespace and provider-context
changes. Only a new service/boot/time-domain baseline resets it. Dhi remains
the exact current bracket's upper cutoff and is never inferred from K.

The bounded last-T guard and explicit `recent_tracking_capacity` latch prevent
same-scope eviction from silently re-arming recency. Existing independent active
membership may continue under its own limits. Missing guards or clock evidence
cannot manufacture a negative. These are accepted requirements, not evidence of
an implemented cache, capacity recovery or timer.

For current eligible rows, use the maximum of each available branch's minimum
support horizon, capped by eligibility. Flattening both alternatives into one
minimum incorrectly expires the union with its shorter branch. These horizons
govern current positive claims and establish no presentation timeout.

R2 explicitly requires complete coverage to become partial/unresolved when a
member's sole positive branch expires without a separately admitted current
negative. Checking the census alone and filtering the row from a still-complete
scope would create false absence authority. A live active alternative can still
select a row after recent expiry. Conservative earlier loss of complete scope
is also permitted; it does not erase that independent active claim. All required
negative and census supports remain currentness dependencies, including for
complete-empty. Delayed quiet replacements cannot bypass the facade's checks.

These explicit union/coverage rules resolve the semantic concern in WS-P1-1
below. The original blanket unknown-age sentence may conservatively reduce
coverage; it cannot suppress proved active membership or convert unknown into
absence. No remaining client contract conflict is identified in the exact
R1+R2 tuple. Mesh's public SDK/profile review and source implementation gates
remain their existing owning assignments.

## Compatible client semantics

- Selection is independently supported `E AND (A OR R)`: current running,
  including waiting/blocked, survives unknown recent activity; proved recent
  activity can select a parked or runtime-unknown row. Recent membership grants
  no runtime or action authority. Default recency is 72 hours; zero disables it.
- The `L/W/U` source bracket and one-millisecond flooring allowances preserve a
  conservative unknown interval. Same-event positive cutoffs cannot renew on
  heartbeat, proof, reconnect or repeated observation. Older events and detected
  clock discontinuity supply no new recent or outside-window authority.
- Positive expiry yields unresolved retained context. Removal requires a current
  proved negative or a current exhaustive accepted replacement whose coverage
  establishes the selection decision. There is no added context timeout.
- Quiet `Dlo`/`Dhi` transitions publish replacements and advance projection
  revision while observation revision remains unchanged. No-op reads and proofs
  renew neither supports nor revisions. Partial reconnect omission cannot retire
  prior presentation context.
- Complete scope requires the exhaustive current saved-plus-loaded identity
  union and the supports needed to decide every identity. Loaded-only census,
  aggregate activity flags and skipped/failed activity reads cannot establish
  recent-history absence. The proposed `no_native_turn` exception must join the
  exact same accepted row/sample and current latest-turn support.
- Full history remains an explicit rare read. There is no full fallback, top-N
  truncation or implicit consumer migration. Keep the proposed 4,096-identity,
  1 MiB combined-ledger and 32-receipt bounds, frame limits, and inclusive costs
  for simultaneous caches, generations, clocks, pins and copies. P0 body counts
  are a sizing screen; proposed CPU/byte gates still require measurement.

Mesh's existing same-byte review owns confirmation that positive attenuation
`H - max(0, E - Dlo)` uses the exact original receipt expiry and its current
translated receipt under matching context/accepted bindings. This formula can
only shorten positive authority. It cannot translate `Dhi` into an early negative
time proof. No additional Mesh review request is created here.

The existing displayed-age contract remains source-sampled
`runtime.observedAt - activity.at` under its current/sample support. A new
membership clock does not implicitly change that UI field or its authority.

## Initial R1 corrections and current disposition

**WS-P1-1 — client semantics resolved by R2; editorial clarification remains
useful.** R1 lines 173–180 require a proved decision for every identity, then say
“Unknown age is partial.” The initial review flagged the missing distinction
between selected membership and coverage availability. Eligible active rows with
unknown age remain selected. A current exhaustive scope may prove all membership
decisions even when one selected row's age remains unavailable; R2 also permits
conservative partial coverage without dropping that member. Excluded-kind rows
and a disabled recent branch need no activity proof.

Suggested replacement: “Unknown activity makes affected membership coverage
partial when the selection decision cannot otherwise be proved. Independently
proved active membership remains selected; unavailable activity and age fields
remain unknown.” Preserve exhaustive census and all required current supports.

**WS-P1-2 — open preparatory-helper conformance.** R1 lines
94–98 require out-of-range cutoff arithmetic to make recent unknown. Exact
`recent_activity()` currently returns `True`/`recent` with cutoffs beyond the
signed safe-integer envelope. Both Python versions reproduce this input:

| Input/result | Value |
| --- | ---: |
| Maximum allowed cutoff | 9,007,199,254,740,991 |
| L / U / now | 9,007,199,254,730,991 / 9,007,199,254,731,001 / 9,007,199,254,731,091 |
| Current original receipt expiry | 9,007,199,254,740,990 |
| W / activity T / Q | 1,700,000,000,000 / 1,699,999,999,000 / 259,200,000 |
| Actual Dlo / Dhi | 9,007,199,513,929,990 / 9,007,199,513,930,002 |

All input integers are within the safe-integer bound; sample, support, service,
boot and context joins match. Expected outcome is unknown with no usable
out-of-range cutoff. This is preparatory-model conformance, not an integrated
runtime failure or producer qualification result.

The announced R2 is the identified coverage/lifetime completion. The existing
owning helper correction request remains outstanding; it was not resent.
The contract already requires unknown on overflow, so client contract signoff
does not certify the unchanged preparatory helper. This creates no new general
permission gate. Preserve all original R1 and failed-vector evidence.

## Verification and remaining scope

On Python 3.14.8 and 3.11.17, in an immutable export under the shared advisory
lock, all 12 unchanged helper tests pass with GC disabled. The unchanged stdlib
oracle passes 11,804 floored capture checks and 410 positive translations.
Separately authored client vectors verify all 27 selection combinations,
44,380 flooring checks and 960 positive translations across different clock
offsets, and reproduce WS-P1-2. The three project modules loaded by those vectors
match exact Git blobs. Dual-version vector results agree apart from the version.

Private reproducible evidence is retained at repository-root
`.cache/observer-working-set-20261018/p1-995401e/review.json`, SHA-256
`15f926c1cb4869713bd651aebce3c5e44241495ffd070e88fb0489cc9acd3d0c`,
with the immutable export, input pins, scripts and raw logs.

The R2 review separately replays all 16 unchanged upstream named models on
Python 3.14.8 and 3.11.17; output exactly matches the pinned producer JSON.
New independent finite models pass 1,024 scalar-prefix checks, 16,384 exact
candidate-minimum checks, 5,200 union-horizon checks and 3,564 coverage-expiry
checks on each version. The WS-P1-2 range counterexample separately reproduces
on exact R2 source; its three loaded project modules match Git blobs. All model
and counterexample outputs are byte-equal between Python versions. These are
finite equations/decisions, not actual cache, receipt, capacity or GC qualification.
Unchanged helper suites and the full canonical suite were not rerun for R2.

The separate private R2 evidence is repository-root
`.cache/observer-working-set-20261018/p1-r2-58b04ac/review.json`, SHA-256
`84253f07957d6a7efcdbf1a4440d22e4915a62ea112c23fffe78a5fac267f835`,
with immutable export, scripts, raw outputs and pins. Runs were serialized under
the shared advisory lock. The saved R2 961-test result was read/hash-verified.

Future stateful vectors must cover same-event ceilings through quiet loss,
re-entry and reconnect; older events and wall changes; independent active support
with unknown recent evidence; separate quiet/observation revisions; exact absence
joins; and refusal without removal authority. Native schema/profile/runtime,
resource/CPU/native transport and paired installed/client adoption gates remain
open. No live native collection, device change or historical delta test replay
was performed for this review.
