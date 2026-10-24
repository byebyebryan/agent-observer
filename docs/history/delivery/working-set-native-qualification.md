# Working-set native qualification

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

The opt-in working-set producer needs an independent native comparison as well
as the synthetic source and public Reader checks. The
[qualification tool](../../../scripts/qualify-working-set-native) compares a private
installed candidate with the existing Codex daemon using the independent stdlib
read client in [evaluate-observation](../../../scripts/evaluate-observation). It does
not start a Codex daemon, start the candidate service, repair an endpoint, or
perform session actions.

This tool is one part of P3 in the
[working-set plan](working-set-projection-plan.md). It cannot establish the
whole producer exit by itself. Delta-sync remains dark; full and legacy active
services and their selected artifacts are independent.

## Isolated sequence

Build and inspect an exact Observer/Mesh wheel pair in a private virtual
environment. Verify installed package bytes and schema parity against those
wheels and the reviewed commits before any native proof. Use that environment's
lexical Python entrypoint, rather than its resolved base interpreter. Both CLI
entrypoints must belong to the same environment. The tool checks the wheel
SHA-256 values recorded in noneditable installed distribution metadata; it
refuses an installation that does not record them. A wheel digest in an
unverified filename or a caller's label is insufficient.

Choose an existing, inspected Codex home and its exact current owned socket.
Choose a new candidate socket inside a dedicated mode-0700 directory under the
current user's runtime directory. The candidate socket must not exist yet.
Leave ordinary services, provider configuration, endpoints and launchers alone.

Run the tool with explicit paths, wheel digests, Python and CLI digests, host
scope and window. `--help` lists the required arguments without accessing a
provider. It first checks installation and endpoint identity, then obtains a
bounded native-before census. Only after its `native_before_complete` progress
record may the caller start the private service. The exact allowed invocation
is the candidate Python, the candidate `agent-observer-service` entrypoint,
`serve`, and these five option/value pairs:

```text
--host-scope HOST --socket PRIVATE_SOCKET --provider codex
--codex-home EXISTING_HOME --working-set-window-hours 72
```

The tool verifies the private socket listener's UID, executable, process birth,
arguments, socket incarnation and installed parser. It reads the candidate's
first cached working-set view and then obtains a native-after census. The
caller must stop and join only the private service it started, including its
owned worker cleanup, on success, failure or cancellation. The tool closes its
own read connections. It does not close or signal the native daemon.

## Comparison and limits

Native payloads remain transient. Reports contain bounded counts, finite reason
codes, artifact/process metadata and per-run keyed identity digests. Do not save
raw provider responses, prompts, titles, cwd values, native IDs or tool content.

Selection and field comparisons require stable, exact identities and native
before/after facts. A changed or incomplete census, unsupported metadata,
inconsistent native identity, missing clock support or failed join remains
unresolved. Missing loaded membership does not prove parked. A current native
`notLoaded` response for a readable saved identity is required. Metadata reads
exclude turns/items; a nonempty unexpected content array is rejected.

The original accepted-sample clock joins and a coarse external time envelope
are checked. Direct and synthetic `compare_frame` calls retain the first-set
clock check described below. The installed run instead uses a bounded observed
clock-prefix proof so it can wait through an incomplete initial view without
assuming that the first complete view is the service's first accepted sample.
This check is private to the installed run path and has no CLI switch. It runs
only after the installed lexical Python, wheel and CLI digests, the candidate
peer, socket incarnation, and exact `serve` argv have passed the existing
provenance checks.

The candidate reader observes no more than the existing 16-frame limit and
still requires the first returned projection to be a complete single Codex
scope. Before that complete view, every parsed frame contributes only a bounded
pair of runtime/history receipt counters and clock tuples plus fixed service,
source and scope metadata. No earlier DTO, roster or native identity is kept.
The first projected receipt set may have counters 0 or 1; a first value above 1
is unproved. After that baseline, each component counter must either stay
unchanged with its exact full clock tuple unchanged, or increase by exactly one
with a new valid joined clock. Counter gaps, regression, a changed clock at the
same counter, an unprojected acceptance, clock-ceiling mismatch, failed/stale
receipt, clock outside the native-before-to-receive envelope, context or scope
change, missing complete view, or any other prefix failure stays unproved for
the rest of the read. A later clean frame cannot restore it.

An installed prefix may begin with a neutral context-0 status or heartbeat.
That frame must be warming, have no projection or clock ceiling, and contain
both runtime and history receipts in their exact never-accepted state with
counter zero. It establishes the retained zero baseline. The canonical first
context-1 projection may carry the first accepted sample in the same frame;
that transition is accepted only when every component advances from zero to
at most one with its exact joined clock. A separate unprojected acceptance,
coalesced first count, missing first clock, later context reset, or source or
scope rebind leaves the prefix unproved. Direct first-set comparison remains
strictly bound to context generation 1 and does not use this neutral-prefix
rule.

For every projected prefix frame, the reported ceiling must equal the maximum
`W - L + 1` among the currently joined clocks and the previously observed
ceiling. This preserves a larger earlier `K` when a later component mirrors a
new sample with a smaller lower bound. The native comparison rechecks the final
receipt/census and coarse external bracket, then verifies a per-run keyed
fingerprint of the final fixed metadata, receipt/clock pair, ceiling and frame
marker before using this recomputed value. A prefix report contains only finite
status/reason codes, bounded frame and transition counts, component counters,
the recomputed ceiling and its keyed fingerprint. Prefix mode never falls
back to the first-set proof when the observed prefix failed; recent-only
membership then remains conditional or unresolved. Direct/synthetic calls
without the private installed provenance flag cannot use a supplied prefix as
proof.

For that first-set proof, the frame must be a view with exactly one Codex source
bound to the selected home and namespace; source and scope context generation
must be exactly 1, scope continuity exactly 1, and `clockGeneration` exactly 0.
The initial scope-continuity requirement also excludes prior projection
failure/refusal and recovery. Runtime and history receipts
must each be exact integer count 0 or 1. Every count-1 receipt must be current or
partial and have exactly one clock joined to its accepted counter and sampled
BOOTTIME. A count-0 receipt is allowed only in the canonical never-accepted
state: warming, `not_observed`, null sample/expiry, with no clock and no
FactSupport entry for that component. The current clock census and external
wall/BOOTTIME bracket must be complete. The qualifier then computes
`K* = max(W - L + 1)` across those accepted clocks and requires the frame's
`clockCeiling` to equal `K*` exactly. Mirrored component clocks for the same
sample are allowed when their bracket metadata agrees.

Any accepted count above 1, malformed/coerced count, stale or failed receipt,
missing or extra clock, context mismatch/reset, discontinuity, incomplete
census, source-scope mismatch or ceiling mismatch leaves the first-set proof
unproved. In installed prefix mode, a later count above 1 is allowed only when
each intervening increment and its new joined clock were observed; a missing
step remains unproved. Recent-only positives stay conditional on the producer
ceiling whenever the applicable proof is unproved. Direct and synthetic
`compare_frame` calls remain conditional by default. A final current frame
alone cannot recover a missing prefix because the public frame carries only
current component clocks while `K` retains every accepted bracket.

The public FactSupport does not carry the original snapshot collection ID. The
qualifier checks the clock's UUID shape, mirrored-sample consistency and exact
component/counter/sampled-BOOTTIME receipt join; it cannot independently compare
that UUID with the private snapshot collection ID. The reviewed installed
capture path supplies that join. Recomputed `K*` uses the bracket values, not
the UUID.

A valid first-set proof or observed prefix only removes uncertainty about `K`
for the corresponding recent-positive calculation. It does not prove a native
census, candidate coverage, row identity, runtime, or native-before/after
stability. The independent native census, exact joins, and existing one-second
precision boundary still apply. An independently active positive remains
independent of recency. Omitted-row recency requires a complete joined clock
census for every current source component; a missing component cannot
establish absence. Native empty-turn evidence requires an explicit current
no-turn result, not a metadata response that merely omitted turn details.

The report also includes additive `projectedFieldStatus` and `projectionStatus`
values. `projectedFieldStatus` compares runtime, kind and activity for every
selected body, plus every field represented by a compact nonmember fact: kind
for excluded child/system entries and runtime/activity for parked entries.
Fields omitted from compact nonmember bodies are unrequested by this comparison.
The legacy `fieldStatus`, its reason/count fields, overall `status` and
`exitCode` retain their existing stricter full-row semantics; for example, a
parked negative can have `projectedFieldStatus=match` while
`fieldStatus=unresolved`, overall `status=unresolved` and `exitCode=3`.
`projectionStatus` is an additive projection-scope result: it is `match` only
when the unchanged membership result and projected field result match and the
native census, candidate scope coverage and candidate binding are complete.
Represented field or membership mismatches remain mismatches, and missing or
unknown represented evidence remains unresolved. A projected match does not
claim full-history body parity or change the qualifier's existing exit result.
The additive projected field counts distinguish compared identities,
unresolved and mismatched identities, and compact nonmember bodies with
intentionally unrequested fields; they contain no raw identity values.

The focused first-set and observed-prefix tests are synthetic controls for the
arithmetic, ordering and receipt-state gates. They do not claim an installed
native comparison or a producer acceptance result.

Exit 0 means all of this tool's full-set comparisons matched. Exit 2 records a
mismatch. Exit 3 records unresolved or unsupported evidence, and exit 4 records
another bounded qualification failure. A nonzero result is retained as evidence
and is never converted to a pass by removing difficult rows or changing the
expected view.

Before/after reads cannot exclude an intermediate state that changed and then
returned to the same value. This is native observation evidence, not exact
phase-entry timing, provider action authority, performance/RSS proof, SSH proof,
consumer adoption or deployment acceptance. The remaining P3 gates keep their
original limits and provenance.
