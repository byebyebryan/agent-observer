# Working-set producer source candidate

This is P2 implementation under the [accepted P1 direction](evidence/2026-10-18-working-set/joint-contract/README.md).
It is unreleased, opt-in and not a producer acceptance or schema/identifier
freeze. The existing full/active routes and dark delta disposition remain
unchanged. SDK profile/facade/factory, public CLI configuration and remaining
producer qualification follow this component checkpoint.

## Owner and source clock

`ServiceState(..., working_set_window_ms=259200000)` creates one fixed working
set. The default `None` creates no working-set clock or projection cache and
rejects the new request family. Zero disables recency. The window is read-only
after startup; a different window requires a new owner incarnation.

Runtime captures the upper BOOTTIME bound immediately after parsing the
canonical worker snapshot. ServiceState installs the bracket only after the
engine returns actual acceptance. The lower bound is the original job start;
the wall sample is the original snapshot `collectedAt`. Exact `collectionId`,
component accepted counter, context and original support join the bracket.
History mirroring binds the same original sample separately to each actual
accepted receipt. Process exit or scheduler success cannot install a clock for
a superseded sample or stale a newer healthy receipt.

`WorkingSetClocks` holds at most two component bindings and constant-size
clock-incarnation state. Its monotonic ceiling survives source-context changes;
wall/BOOTTIME discontinuity advances a separate generation. The pure classifier
retains one bounded last-T guard per exact full identity across row retirement.
The guard owns and shares the fixed identity prefix, prepays string/key/table
growth and latches recency unavailable when capacity is refused. Only a real
source context change can clear that latch; the clock ceiling remains intact.

## Selection and quiet replacement

The projector implements `E AND (A OR R)` with independent original branch
supports. A recent body can be parked or runtime-unknown; it retains that
meaning. Current user-kind eligibility still needs its original support.
Unknown-kind eligibility retains the existing policy. Current parked negatives
require the original saved-identity/runtime join, and no-turn absence requires
the exact current native latest-turn absence and clock receipt. The negative
wire includes that typed original latest-turn record and the paired unavailable
activity record, with exact reasons and a causal timing-receipt binding.

The earliest quiet lower/upper cutoff is scheduled without provider collection.
At the lower bound a sole recent positive becomes unresolved and completeness
becomes partial. Only the upper bound with a current proved inactive alternative
can emit outside-window authority. An independent active branch can continue.
Quiet changes advance `viewRevision`; `observationRevision` retains the engine
revision. Ordinary reads export the cache without renewing either evidence or
membership. Timers may recompute from the owned in-memory roster; no full-history
I/O is triggered. Further CPU/cadence qualification is still required.

Prior-positive context and timestamp guards have separate lifetimes. Expiring
or dropping context is not a removal claim. Native scope metadata, retained
prior-positive entries, guards and fixed clock bookkeeping share the 1 MiB
tracking bound. Tracking/frame refusal produces explicit unavailable coverage.
It never substitutes an active-only or full feed and never marks native
collection failed.

The ledger's `horizonBoottimeMs` is an informational context-retention bound,
not the selected union horizon. In particular it can outlive Dlo so uncertainty
survives during Dlo..Dhi. Current authority always uses the independent branch
supports/cutoffs; a long recent receipt cannot keep membership current after
both active support and the recent cutoff end. The prepared facade must apply
the accepted `min(hE,max(hA,hR))` rule independently of that context bound.

## Native candidate and delivery

`working_set_contract.py` defines the closed candidate request/frame grammar
using `workingSetProtocol=1`. The selector and canonical digest bind the exact
window; clients cannot widen it. Selected API 4 bodies preserve frozen row
semantics. Each scope carries current clock bindings, original field supports,
independent active/recent proofs, uncertainty, explicit negatives and coverage.
Recent metadata includes the native conservative lower and upper cutoffs.

`StreamGuard` binds host, UID, service/boot/time domain, selector and source
configuration. Both revisions, sequence, clock generation and global ceiling
cannot regress. Gaps require resynchronization. A reused projection revision
cannot carry different material. No SDK identifier is registered by this source
module, and schema exports are still candidates.

Runtime dispatches this family explicitly alongside Service 4 and active v1.
It keys body reuse and watch ordering by the working-set revision. Slow peers
keep their original body generation while later replacements are encoded;
same-generation readers share the delivery body. Opt-in accounting includes
actual active/working owner buffers and delivery buffers in the existing shared
64 MiB encoded limit. The source asks for bounded frame/ledger staging room
before reconstruction; refusal yields working-set unavailability independently
of provider health. This initial reservation and fixture accounting are not an
inclusive physical/RSS acceptance: legacy construction, all temporary/copy
overlap, concurrent full reads, installation and real workload peaks still need
the agreed producer resource gates.

## Validation boundary

The [component receipt](evidence/2026-10-18-working-set/p2-native/README.md)
records the exact source inventory, focused dual-Python execution and repository
gate. Tests use synthetic ServiceState data, disposable UNIX sockets and owned
worker fixtures. They do not establish populated provider behavior, remote
clock translation, Mesh facade admission, fixed SSH, installed immutable pairs,
whole-process RSS, the CPU targets, delivery savings or consumer adoption.

No selected service, artifact, version, normal role or consumer changes in this
checkpoint. Delta synchronization remains dark.
