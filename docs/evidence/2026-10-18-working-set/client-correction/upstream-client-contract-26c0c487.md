# Working-set P1 client review

2026-10-18. **Client direction compatible; two bounded corrections remain before
unconditional exact P1 signoff.** This reviews a proposed active-plus-recent
replacement view. It does not implement or select that view, allocate identifiers,
or reopen the deferred dark delta-sync effort.

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

## Requested bounded corrections

**WS-P1-1 — make coverage depend on the selection decision.** R1 lines 173–180
require a proved decision for every identity, then say “Unknown age is partial.”
That unconditional sentence conflicts with the independent OR: eligible active
rows with unknown age are still selected. A current exhaustive scope may prove
all membership decisions even when one selected row's age remains unavailable.
Excluded-kind rows and a disabled recent branch also need no activity proof.

Suggested replacement: “Unknown activity makes affected membership coverage
partial when the selection decision cannot otherwise be proved. Independently
proved active membership remains selected; unavailable activity and age fields
remain unknown.” Preserve exhaustive census and all required current supports.

**WS-P1-2 — enforce R1's cutoff range in the preparatory helper.** R1 lines
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

Publish an identified revised packet or addendum for the coverage wording and
an owning helper correction; preserve the reviewed R1 bytes and their evidence.
Neither correction is a new general permission gate.

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

Future stateful vectors must cover same-event ceilings through quiet loss,
re-entry and reconnect; older events and wall changes; independent active support
with unknown recent evidence; separate quiet/observation revisions; exact absence
joins; and refusal without removal authority. Native schema/profile/runtime,
resource/CPU/native transport and paired installed/client adoption gates remain
open. No live native collection, device change or historical delta test replay
was performed for this review.
