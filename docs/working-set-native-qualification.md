# Working-set native qualification

The opt-in working-set producer needs an independent native comparison as well
as the synthetic source and public Reader checks. The
[qualification tool](../scripts/qualify-working-set-native) compares a private
installed candidate with the existing Codex daemon using the independent stdlib
read client in [evaluate-observation](../scripts/evaluate-observation). It does
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
are checked. The installed run has one narrowly bounded way to independently
recompute the accumulated lower-cutoff ceiling `K`: its exact first accepted
receipt set. This check is private to the installed run path and has no CLI
switch. It runs only after the installed lexical Python, wheel and CLI digests,
the candidate peer, socket incarnation, and exact `serve` argv have passed the
existing provenance checks.

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
unproved. The comparison then preserves the original behavior: recent-only
positives remain conditional on the producer's ceiling. Direct and synthetic
`compare_frame` calls also remain conditional by default. Later accepted
receipts cannot use this shortcut because the public frame carries only current
component clocks while `K` retains every accepted bracket.

The public FactSupport does not carry the original snapshot collection ID. The
qualifier checks the clock's UUID shape, mirrored-sample consistency and exact
component/counter/sampled-BOOTTIME receipt join; it cannot independently compare
that UUID with the private snapshot collection ID. The reviewed installed
capture path supplies that join. Recomputed `K*` uses the bracket values, not
the UUID.

The first-set proof only removes uncertainty about `K` for the corresponding
recent-positive calculation. It does not prove a native census, candidate
coverage, row identity, runtime, or native-before/after stability. The
independent native census, exact joins, and existing one-second precision
boundary still apply. An independently active positive remains independent of
recency. Omitted-row recency requires a complete joined clock census for every
current source component; a missing component cannot establish absence. Native
empty-turn evidence requires an explicit current no-turn result, not a metadata
response that merely omitted turn details.

The focused first-set tests are synthetic controls for the arithmetic and
receipt-state gates. They do not claim an installed native comparison or a
producer acceptance result.

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
