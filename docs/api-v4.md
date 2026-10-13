# Observation API 4 system classification

The dashboard refinement candidate is Observer 0.7.0a1, API 4,
snapshot/watch 6 and Service 4. Explicit Mesh Agent profile v3 through SDK 1
carries these records. The accepted API 3 tuple remains selected until independent
artifact, native, delivery and operational gates accept its replacement.

## Classification and selection

`kind` is `user`, `child`, `system` or `unknown`. Codex's supported
`threadSource=system` tag classifies an internal client helper. This is an
optional client-supplied analytics classification, not an OS process type.
Ephemeral persistence alone does not classify a system thread. Valid native
child signals retain their existing precedence; inconsistent, malformed or
unsupported classification stays unknown with a bounded metadata issue.

Raw snapshots preserve every admitted row, including system identities.
`listing` and human/direct/cached/Mesh list and watch views hide confirmed
system rows by default. `include_system=True` and CLI `--include-system` make
those rows visible. Exact identity `select` and `show` preserve diagnostic access.
Unknown classifications remain visible. Filtering happens after reconciliation,
so a retained unknown identity positively classified as system stops appearing.

Classification never determines runtime, phase, history presence or activity.
Daemon idle remains running/waiting, and parked still requires its reviewed
positive native predicate. All [API 3 timing semantics](api-v3.md) remain.

## Compatibility

This is a breaking prerelease enum extension. API 3/wire 5/Service 3 and Agent
profile v2 do not accept the new tuple. No converter or automatic downgrade is
provided. Mesh SDK 1, Read 1, Delivery 1, Tmux v1 and the selected historical
writer remain independent. Immutable producer/read/publisher packages, native
metadata comparisons and both-host cached IPC/SSH proofs gate adoption.
