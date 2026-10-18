# Native working-set component checkpoint

This checkpoint implements the opt-in owner clock/guard, active-or-recent cache,
strict native candidate and local request/watch dispatch described by the
[source guide](../../../working-set-native-candidate.md). It follows joint P1
agreement and retains the original R1/R2 and corrective R3 provenance.

The source inventory and execution results are bound in `receipt.json`.
`run_focused.py` reproduces the focused working-set tests with cyclic GC disabled
and records exact imported project blobs. The repository gate additionally
checks the legacy runtime and documentation. An initial gate's one expectation
mismatch is retained separately; it is not a before/fix claim for native
behavior. Final source claims use the final recorded gate only.

Luna implemented the bounded accepted-clock store and row classifier/guard;
the primary reviewed them, required shared-prefix ownership and pre-allocation
corrections, and implemented native validation, accepted-only capture, cached
projection/timers and local dispatch. The primary owns integration decisions
and final review.

This is synthetic/component evidence. It does not qualify the optional Mesh
profile/facade, populated native providers, inclusive resource/CPU/wire gates,
fixed SSH, immutable installed pairs, schema/identifier freeze or consumers.
No selection, installation or rollout is included; delta remains dark.
