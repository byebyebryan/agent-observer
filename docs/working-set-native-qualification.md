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
are checked, but the producer's accumulated clock ceiling K is not independently
proved by this tool. A recent-only positive that depends on that K is reported
as conditional and prevents a full-set pass. An independently active positive
does not depend on recency. Omitted-row recency requires a complete joined clock
census for every current source component; a missing component cannot establish
absence. Native empty-turn evidence also requires an explicit current no-turn
result, not a metadata response that merely omitted turn details.

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
