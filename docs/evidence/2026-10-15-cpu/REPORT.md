# Remaining Agent CPU: attribution and source correction

Date: 2026-10-15. Baseline source `f3e16db`, selected Observer a4/Mesh a20
readers/publishers and independently selected core-only a3 collectors. This pass
changes source only. No selected links, managed services, provider configuration,
Mesh runtime, Tmux controls or RLCD application were changed.

## What currently costs CPU

A [45-second normal-workload sample](normal-resources.json), without an added
reader or concurrent benchmark, reports percent of one core:

| Role | Snap | Starship |
| --- | ---: | ---: |
| Collector cgroup, including helpers | 1.66% | 1.85% |
| Resident Agent publisher | 0.00% | 4.37% |
| Extra Agent source process | 2.18% | None matched |
| RLCD dashboard cgroup | Inactive | 19.85% |

All sampled service PIDs were stable. Snap's extra source PID 651856 has the
independently inspected lineage `mesh-plus -> sshd-session -> sshd-session ->
sshd -> systemd`; its cost is outside the resident publisher cgroup. The
measurement does not attribute it to a particular consumer. This is why the
resident unit alone is not the total cost of remote publication. Cgroup and
per-process values overlap; do not add them. Created/lost process and generic
SSH server/encryption cost are not fully captured. These are descriptive short
ordinary-host samples, not idle baselines or causal comparisons.

A separate [60-second installed prepared fleet watch](reader-spans.json)
on Snap consumes 10.844 process CPU seconds, **18.07% of one core**. It admits 19
complete views and invokes the human output sink 25 times, including its final
revocation line. Inventory reaches **490 rows: 101 Snap and 389 Starship**.
Reader process CPU excludes collector, publisher and SSH child/server CPU.
This window includes setup, first admission and cancellation; it is not a
warm steady-state comparison with the prior five-minute resource windows.

Synchronous spans show:

- Observer snapshot validation: **4.346 CPU seconds / 40.1%** of the process.
- Generic aggregate admission excluding nested Observer validation: **3.665
  seconds / 33.8%**. This includes packaged schema, projection/proof/receipt
  checks, serialization and bounded traversal; it is not just JSON Schema.
- Prepared generation compilation: **0.481 seconds / 4.4%**.
- Owned current-row reads: **0.302 seconds / 2.8%**.
- Ordering/filtering/copying for human presentation excluding nested snapshot
  validation: **0.106 seconds / 1.0%**.

Human ordering also calls snapshot validation: its inclusive cost is 1.190
seconds / 11.0%. That overlaps the first item, so these inclusive figures must
not be summed. The renderer receives admitted rows but its general public helper
validates the reconstructed snapshots again. This remains a separate possible
optimization, not an unreviewed validation bypass in this correction.

The [initial cProfile trace](profile-hotspots.json) locates roughly 2.98 million
`validate_shape` calls and 9.35 million Mesh bounded-tree calls in 45 seconds.
Its heavy instrumentation changes cadence and causes seven resyncs; its 62%
process CPU is **not** the normal watch cost. Epoll's reported self time is
blocked wall time. Lightweight spans above establish the operational attribution.

## Source changes

1. **Do only the requested type test.** `_matches_type` built a six-entry
   dictionary and evaluated every predicate for every typed JSON node. It now
   branches to the requested predicate. Scalar schema types also avoid a
   temporary list and generator. Union types, exact integer/boolean distinctions,
   text/Unicode checks, bounds and all semantic validation remain intact.
2. **Admit each local service wire frame once.** Both the local read client and
   optional cached Agent source called `guard.accept(parse_frame(data))`.
   `parse_frame` and `accept` each fully validated the same frame. The combined
   `StreamGuard.parse(data)` performs the same bounded, newline-framed JSON decode
   followed by one full scope-aware admission and the existing stream checks.
   Standalone `parse_frame` and `accept` remain strict. Authentication, socket
   replacement detection, chronology, component evidence and receipt expiry are
   unchanged.

No contract schemas, API 4/read 6/Service 4 meanings, provider predicates, proof
cadence, polling intervals or public CLI defaults change. This does not replace
Mesh admission or cache validation success across mutable bodies.

## Controlled comparison

[Eight fresh-process trials](benchmark-comparison.json) use serial ABBA/BAAB
order, the same installed Mesh a20/dependencies/Python 3.14.8, two owned synthetic
hosts and 250 rows per host. Runtime is frozen for the matrix; fixture creation
and one warm-up per case are excluded. Cross-variant snapshot and full human
display oracles match.

| Case | Baseline mean | Candidate mean | CPU reduction |
| --- | ---: | ---: | ---: |
| 20 snapshot validations, 250 rows | 409.90 ms | 297.24 ms | 27.49% |
| 20 wire decodes plus complete guard admission, 250 rows | 987.45 ms | 433.80 ms | 56.07% |
| Prepared consumer, 4 changed 500-row views, 3 human renders per view | 1827.34 ms | 1607.81 ms | 12.01% |

Baseline/candidate ranges are 403.55–423.22 / 293.88–300.08 ms for snapshot,
969.21–1015.25 / 422.67–444.05 ms for wire, and 1809.62–1861.75 /
1571.17–1631.22 ms for the consumer. Savings establish these fixed workloads,
not a universal percentage for the complete fleet or RLCD application.

## Native cached-source observations

The [owned publisher windows](publisher-spans.json) execute the actual optional
factory against each ordinary host's existing Service 4 cache, with a watch and
one nonce-bound cached proof every five seconds. Every window completes nine
proof reads and closes its source channels. They exclude Bridge/carrier work:

| Host | Baseline CPU seconds / 45s | Candidate | Baseline / candidate watch publications |
| --- | ---: | ---: | ---: |
| Snap | 0.885 | 0.542 | 3 / 2 |
| Starship | 3.010 | 1.911 | 4 / 3 |

The directional improvement is consistent with fewer native validations, but
the native publication counts differ. These are not matched causal savings.
Collector/runtime state is not independently re-certified by another cache read.
The candidate uses source overrides, identified by [file digests](source-digests.json),
not a new installed wheel. Snap's distribution metadata resolves stale a3 egg
metadata during source overrides; it is not the code identity.

A separate type-only candidate fleet window processes the same 19 views with
176 snapshot validations, using 9.998 versus baseline 10.844 CPU seconds.
Of the candidate's repeated host appearances, Snap has 15 unchanged and 2 changed
native view revisions; Starship has 11 unchanged and 4 changed revisions.
Changes to transport proof/emission still trigger full roster composition and
admission. Workload activity is uncontrolled; do not promote this into a 7.8%
fleet saving or infer that unchanged revision permits skipping proof/lease checks.

## Remaining opportunities and ownership

1. **Package and separately accept these source corrections.** Build immutable
   owner artifacts, run current-profile installed/native and concurrency/expiry
   checks, then scoped reader/publisher/local-client selection and rollback.
   Do not silently update the collector or the shared Tmux factory. Current
   installed a3/a4 artifacts and downstream RLCD are unchanged.
2. **Reduce repeated native-body work at the Mesh boundary.** Proof refreshes
   repeatedly carry, compose and admit the full saved roster, including unchanged
   history. Any reuse must bind exact owned immutable native bytes to the current
   profile/incarnation while independently rechecking envelope, proof, sequence,
   clock, nonce, socket ownership and original leases. An unchanged revision alone
   is insufficient. This is a focused Mesh-owner design/spike, not an Observer
   shortcut; the private a21 candidate remains unpromoted.
3. **Avoid reconstruction/revalidation solely for presentation.** A certified
   prepared path could supply an owned admitted header and rows to formatting
   without running the arbitrary-input public snapshot helper again. Keep strict
   public admission, caller ownership, filtering/order parity and exact expiry;
   do not add a blanket `validate=False` switch. The helper currently also exports
   a full raw snapshot once per replacement only to retain its header.
4. **Keep dashboard adoption independent.** RLCD is the largest continuously
   running consumer here and retains its older independent reader bundle. Its
   prepared-helper adoption and matched application/device measurements already
   have a handoff; Observer changes do not establish application savings.

Collection is smaller than the read/publication path in this sample. No evidence
justifies weakening native authority, slowing monitoring, trimming discovery
history or removing proof/expiry checks as a first response. Fleet fan-out still
multiplies acquisition/admission work per reader; service multiplexing, filtered
publication or deltas would require their own contract and correctness study.

## Validation

The source correction passes all **423 tests with Mesh a20 present**, no skips,
on Python 3.14 and 3.11. The default Mesh-free `./scripts/check` also passes
with its 34 expected optional-Mesh skips. Final checks cover 159 Markdown files,
local links, fences and whitespace. Runtime checks include
native/profile conformance, source ordering, expiry, concurrent cached
reads, strict local framing and socket replacement. New tests cover all scalar
and union type predicates, boolean/integer confusion, single full wire admission,
forbidden fields, framing, host/UID scope and sequence rejection. No native
provider action, ordinary process stop or service restart was performed.

Reproduction tools and interpretation limits are in
[studies/cpu](../../../studies/cpu/README.md).
