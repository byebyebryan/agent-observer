# Measurement-plan resolution: saved classification budget

This note supersedes the unresolved conclusion in
`measurement-plan-addendum.md`. That earlier addendum is preserved as a record
of the initial 256-row instruction and the resulting diagnostic conflict. The
256 claim is mistaken for the pinned canonical route.

Both immutable source pins define `MAX_SAVED_CLASSIFICATIONS = 1000` in
`agent_observer/codex_snapshot.py` and apply it when classifying saved rows that
are absent from loaded membership. The collector defaults to
`history_limit=1000`, `live_limit=512`, and `timeout=10.0`; the adapter passes
no replacement classification cap. The source comparison records
`codex_snapshot.py` byte-identical between A7 and b176. The limit is also
applied before attempting each saved summary read, with `reads` incremented
once per attempted row.

For a fixture containing 500 saved catalog IDs and two of those IDs also in the
loaded set, 498 saved IDs need saved-summary classification. The source budget
admits all 498. A later case may be described as complete only if each source's
actual output reports complete saved coverage and all 500 emitted IDs join to
the same frozen input, with the two loaded rows and 498 classified saved rows
represented accurately. Any deadline, transport, identity, coverage, or
cross-source row mismatch remains an explicit failure or limitation; static
budget capacity alone is not evidence that the run completed.

Use the exact same ordered fixture, loaded IDs, and endpoint replies for A7 and
b176. Verify thread IDs, distinct session-tree root IDs, and current status
joins against the fixture before comparing the two canonical outputs. Do not
combine counts across sources when inputs, emitted ID sets, or joins differ.

The unchanged defaults permit at most 1000 catalog rows plus 512 loaded rows,
or 1512 distinct emitted IDs. A complete 2000-ID case is not representable by
this route under its existing limits. Preserve the existing 10-second worker
timeout and collector deadline; neither may be increased to force a pass.

No endpoint proof, timing, or 500-row run has occurred in V2. Primary review of
the private fixture and finalized argv is required before those runs.
