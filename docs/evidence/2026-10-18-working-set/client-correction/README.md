# Client P1 correction evidence

This is the pure-helper and wording correction recorded in
[contract R3](../../../working-set-contract-r3.md). It does not implement
the native working-set source, clock cache, timer, schema or Mesh profile.

`original-client_vectors.py` is the unchanged RLCD diagnostic SHA256
`43c1e65ae47e42200b185b719a2a9565c2240e84c63f6868f42d2f98e8983817`.
It deliberately asserts the historical bad range result; it is not an after-fix
acceptance script. Its two saved `original-before` outputs reproduce the exact
counterexample against immutable Observer58b04ac. The unchanged independent
union/floor/translation checks in that original diagnostic remain its own scope.

`verify_cutoff_range.py SOURCE --expect before|after` preserves the exact
counterexample input and explicitly chooses the expected historical or corrected
result. Both modes also check that an independent active positive stays selected.
Its saved before/after JSON includes exact loaded project-file hashes.

`run_policy_overlay.py SOURCE before|after` runs the final fifteen policy tests
with GC disabled. The immutable before source has only the final test-file
overlay: exactly the two named overflow regressions fail, while the original
twelve and the inclusive-boundary method pass. On the corrected source all
fifteen pass. Each saved JSON distinguishes expected before failures from after
success and pins loaded source/test bytes. No test failure is hidden as a pass.
These are arithmetic/model regressions, not physical lifetime or GC acceptance.

Both exact Python3.14.8 and3.11.17 venv entrypoints were used. The final runner
was formatted/linted before the recorded final replays. Scope does not include
actual native DTO admission, service/provider actions, clocks sampled from a
live worker, resource/CPU/transport qualification or any consumer rollout.

The initial RLCD client review and its later R1+R2 acceptance have separate
commits/hashes; the owning receipt binds them separately rather than attributing
the later wording/signoff to the initial review. Original R1/R2 packet bytes,
saved canonical gates and independent before evidence remain unchanged.
