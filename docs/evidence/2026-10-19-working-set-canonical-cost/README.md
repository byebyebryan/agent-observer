# Working-set canonical worker component cost

The saved V6 matrix passed eight controlled cases across Python 3.11.17 and 3.14.8, A7 and b176, and two replicates per cell. Each case ran the canonical runtime/history worker pair against the same protocol-controlled 500-row synthetic fixture. The measured component includes parent spawn/drain/wait and the selected strict parser, direct `wait4` CPU for each worker, and fixture-server CPU added once per pair. The peer parser used for parity checks is excluded from CPU accounting.

| Python | Source | Parent selected slices ms | Direct worker `wait4` ms | Fixture server once ms | Component-pair median ms |
| --- | --- | ---: | ---: | ---: | ---: |
| 3.14.8 | A7 | 78.273 | 250.847 | 67.542 | 396.661 |
| 3.14.8 | b176 | 57.054 | 235.161 | 73.682 | 365.897 |
| 3.11.17 | A7 | 78.220 | 276.659 | 56.587 | 411.465 |
| 3.11.17 | b176 | 56.395 | 241.909 | 56.976 | 355.280 |

Each value is the median of two whole runtime/history component-pair trials for that Python/source cell. The complete per-trial values and accounting are preserved in `artifacts/primary-summary.json` and the eight case receipts. This is bounded component evidence; it does not establish a literal SDK-input join or a whole-producer CPU pass. `fullPipelineInputJoin` is false in the saved summary. State acceptance, service/SDK delivery, and an actual native provider were excluded. Earlier SDK 91–93% measurements belong to a separate tuple/component study and are not combined with these values.

The final matrix recorded 16 same-raw strict-parser joins and 8,000 identity joins. It verified actual A7 and b176 source roots, commits, and route-module hashes in the case receipts. All 16 canonical worker child processes and all 8 fixture servers were reaped; every case records endpoint, private-config, directory, lock, and owned-process cleanup as passed. The full matrix took 5.846 seconds under per-case exclusive locking with no warmup.

The synthetic case has 500 catalog rows and two loaded rows; its fixture SHA256 is `2e6e43f1180a89da2a4b3557f118ee24eae6e334c6c14bcee0f057b8bad0b35f`. The canonical route limits are 1,000 catalog rows, up to 1,000 saved classifications, and 512 loaded rows, for at most 1,512 distinct emitted IDs. A complete 2,000-ID canonical case cannot be represented under those limits. The single included plan, `artifacts/measurement-plan-resolution.md`, resolves the earlier mistaken 256-row assumption and states these limits.

Earlier harness failures remain visible in `prior-attempts.json` and the finite JSON diagnostics under `prior/`. V3 used b176 fixture code while labeling the source A7, then failed worker identity cleanup; its worker reap was not proved and its private config is retained. A later read-only inventory found no matching live source-worker argv, which cannot retroactively prove that unrecorded child's retirement. V4 first stopped before execution because its copied `BASE` pointed at V3, then its corrected one-case attempt hit a measurement-harness `NameError`; all owned processes were reaped. V5 had valid component method counts and cleaned up, but the harness expected three fixture connections where five were observed. Those harness failures do not establish a product defect or a successful component case.

The current V6 runner, fixture server, controller, matrix record, pre-execution review, result summary, eight receipts, and their stdout/stderr snapshots are copied byte-for-byte under `artifacts/`. Prior runs remain in the private cache; V1/V2 are reference-only there, and only V3–V5 finite diagnostics and hash pointers are included. No ELF files, private configuration directories, raw 500-row fixture payloads, or actual-provider reports are in this packet. Core/runtime source was not changed. No native, SSH, test, adoption, or rollout gate was run; no commit was created. `SHA256SUMS` covers every packet file except itself.
