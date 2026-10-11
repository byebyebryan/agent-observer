# Mesh SDK integration planning review

Date: 2026-10-10. Scope: plan, source review, package/fixture feasibility and
validation gates before implementation. Outcome: the additive SDK v1 seam fits
Observer's boundaries; proceed through the staged
[integration plan](../../mesh-sdk-v1-integration-plan.md) on a following execution
request. Production profile implementation and package/native/rollout acceptance
remain pending.

## Baseline and research

Observer HEAD `611be2c88daf2327a3117154ee4642998b1d89f6` and Mesh HEAD
`17b8096beed20eeece3d0d86e2df655d1bc1f8ed` were clean at preflight.
Reviewed Observer README/architecture/roadmap, observation boundary, pure public
and service facades, Mesh CLI/tests, dependency/CI and artifact/operations helpers.
Reviewed Mesh SDK specification, owner handoff, API/state interface, reference
codec, reader/response admission, fixture profile and a11 package evidence.
The archived receipt is [probe.json](probe.json).

The current managed source selects a16/a10 reader and bridge environments with
different prefixes. Collector a15 and writer 0.4.0a16 remain independent. Reading
selection JSON and local archives does not establish a fresh remote deployment
receipt. No normal service, provider session, settings or managed configuration
were changed during this pass.

## Review decisions and findings

| Area | Finding | Decision/gate |
| --- | --- | --- |
| Ownership | An explicit structural profile uses installed pure native facades. Mesh enforces generic proofs and lifecycle regardless of callbacks. | Fits the implemented boundary; no transport fork or core dependency. |
| Wire and versions | SDK 1 is additive; existing Agent profile, Mesh wires, API 2/read 4/Service 2 are preserved. | No public version bump required by this migration. |
| Reader propagation | Current CLI selects default reference profiles and imports the clock helper through `mesh_plus.observer`. Validation and human reconstruction are separate call paths. | Explicitly bind every path in M2; block reference imports in its gate. |
| Receipts/eligibility | Native provider/namespace IDs differ from configured selector `agent`. History/runtime leases are independent; raw reconstruction includes unsaved/child rows. | Preserve conservative current required-receipt and unsaved eligibility rules; do not alter semantics under an SDK migration. |
| Callback purity | Public native facades are sufficient; Mesh generic clock helper performs filesystem I/O. | Keep clock lookup in CLI/transport, outside pure callbacks. No need to duplicate proof/transport implementation. |
| Mutation/recursion | SDK DTO immutability is shallow and Mesh calls the profile's response callback during its own admission. | Keep projections nonmutating and domain callbacks free of recursive SDK validation; cover both in M1/M2. |
| Independence | A new profile can precede publisher extraction; retaining Mesh's reference publisher is supported. | Test a11 reader/a10 bridge; no dependency on Tmux checkout, Plus or new providers. |
| Shared test tooling | The concurrent Mesh maintenance plan proposes a portable conformance kit; current released boundary tests still need checkout fixtures. | Adopt a separately released kit when available; do not block on it or build a competing generic kit. Keep required Owner CI checkout-independent. |
| Diagnostics | Mesh `doctor` checks package availability; acquisition `probe` is not a current-view proof/expiry assessment. | Use injected Reader/current/guard validation for acceptance; richer shared diagnostics remain Mesh work. |
| Packaging | Mesh optional floor is a4, artifact verifier allows only a4/a8/a9/a10, and CI pins a9. | Update dependency/SDK capability checks and exact immutable a11 selection in M2/M3. |
| CI prerequisite | Both hosted jobs fail the operations self-test; `chezmoi` is not declared/provisioned by the workflow. Its failure assertion omits stdout diagnostics. | Repair portable/default versus tool-backed checks before package acceptance; preserve meaningful assertions. |
| Rollback prerequisite | Selection acceptance authenticates the unit against the reader prefix; managed bridge prefix is different. | Repair and exercise pre-stop ownership/foreign-process guards before live rollback. |
| Documentation | Current-facing read/selection prose still describes several superseded tuples. | Link this baseline/plan now; reconcile exact selected tuple at M5 without rewriting historical proof. |

The inspected hosted failure is
[run 38088981082](https://github.com/byebyebryan/agent-observer/actions/runs/38088981082).
Its self-test failure reproduces the prior review's operational gap; SDK adoption
does not repair it automatically. No repair was made in this planning pass.

## Validation performed

The disposable environment installed the released Mesh `0.1.0a11` wheel
(`9d3c2446b2391ab2271236804b4dfc03dfa5d29f2766d72b3d12086848b36359`)
and selected archived Observer `0.5.0a16` wheel
(`94705baebfa51a9664e9dbfa7603dcb932d6301146cf9a59017017c5285b3b17`).
Both hashes were verified before installation. It uses Python 3.11.10 and no
Tmux Observer or Claude history SDK. Earlier temporary same-version candidates
have different hashes and were not admitted.

- Existing Observer Mesh CLI tests: 7 pass with the released a11 installed;
  human-watch tests: 4 pass. No optional SDK cases skip in that environment.
- Mesh's isolated SDK boundary suite: 10 pass with the released a11 installed.
  It blocks native/reference imports and covers configured pull/push, binding,
  proof/expiry, guards and cancellation. Its route connector probe uses owned
  IPC, so this run is not actual SSH acceptance.
- Disposable explicit profile probe: the Mesh test fixture profile was coupled
  to Observer's installed `service_public.validate_frame` and public identity
  validator. Reference Mesh Observer, Tmux, collection/service-runtime/provider
  adapter/write imports were blocked. Six frozen Agent cases and 18 timed
  selections exactly matched the separately installed selected a10 reference.
  Exact native reconstruction, warming/empty/partial/historical views and
  original expiry behavior passed. Wrong host, duplicate identity, forged
  accepted receipt, lease extension and invalid native clock were rejected.
- The same probe used an owned Unix socket/bridge and explicit profile through
  configured Reader, validation, current selection, reconstruction and ReadGuard.
  Pull/watch, guard disconnect revocation and complete connection/iterator
  cleanup passed. No catalog lookup, provider collection or live service mutation.
- The ordinary Mesh-free CLI gate passed its five core cases and explicitly
  skipped its two SDK cases. This proves optional-dependency behavior only;
  the separately installed a11 gate above covers those SDK cases.

This is feasibility evidence, not an implemented or accepted owner profile.
The probe reuses fixture logic; its parity checks are not independent provider
semantics or a native active-session census. Actual mixed-artifact SSH delivery,
both-provider receipt-failure cases, new installed CLI/native comparison,
sustained resource checks and managed rollback remain M3–M5 obligations.
The broader Mesh a11 package/native/differential receipts are external SDK
acceptance and do not substitute for those owner gates.

## Review result

No SDK architecture blocker was found in the reviewed scope. Implement a small
pure owner profile and consistent reader wiring first, keeping reference
publication explicitly retained. Establish CI portability and the separate
bridge guard, then complete immutable conformance, independent native and staged
operational gates. Keep publisher extraction and consumer work separate.

The full repository documentation/synthetic check is recorded in
[checks.json](checks.json). Both local runs passed 450 tests: the Mesh-free host
run skipped four optional cases; the installed a11/Python 3.11 run skipped only
two unrelated sealed-memory Claude memo cases because that interpreter lacks
Linux memfd support. All Mesh cases ran there. Local success does not replace the still-failing
hosted baseline or the later clean-environment prerequisite repair.
