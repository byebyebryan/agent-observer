# Mesh SDK v1 integration execution

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

This is the historical a17 integration checkpoint. The following
[Claude retirement](../providers/claude-retirement-plan.md) selects Codex-only a18 collector/
reader artifacts while retaining the same SDK 1 and a16/a10 bridge boundary.
See the [current report](../../evidence/2026-10-11-claude-retirement/REPORT.md).
The following [owned publisher/read handoff](mesh-publisher-operator-handoff.md)
selects a20/Mesh a15 reads/publication, keeping a18 collection independent.

Started 2026-10-11 following the user's goal-loop request, with accepted checkpoints
committed as work proceeds. The [reviewed plan](../design/mesh-sdk-v1-integration-plan.md)
defines M0–M5 and the [planning report](../../evidence/2026-10-10-mesh-sdk-planning/REPORT.md)
retains its pre-implementation bounds. API 2/read 4/Service 2 are preserved.

| Phase | State | Evidence and following gate |
| --- | --- | --- |
| M0 prerequisites | Source/owned fixture validation complete | CI explicitly installs the checksummed upstream chezmoi 2.73.0 Linux artifact. Separate-prefix bridge authentication rejects foreign arguments/PID changes and rechecks before stop. Full checks pass with user-installed tooling excluded from PATH. Hosted CI remains a following source-publication receipt. |
| M1 pure profile | Source tests complete | Frozen bindings, pure public/service facades, exact reconstruction and independent provider/namespace receipts. Callback tests block reference/collector imports. |
| M2 explicit reader | Source tests complete | One profile through configured reader, guards and all view helpers; optional Mesh floor and CI wheel select SDK v1. Core/local commands remain Mesh-free. |
| M3 immutable conformance | Source and installed package complete | a17 source `3650e5e`, exact wheel/archive/SDK/profile gates pass on both hosts. All 466 checks pass on Python 3.14 with no skips; 3.11 has two unrelated memfd skips. a10 reference parity preserves native frames and expected 5/2/0 expiry counts. Hosted CI remains a publication receipt. |
| M4 native/mixed-artifact | Complete within declared bounds | Independent native pull, real two-host SSH push and owned SSH-exit/reconnect pass. a11 owner readers use retained a10 bridges. Short matched CPU/PSS/latency windows accept the bounded SDK overhead; older-history metadata and sampling differences remain explicit. |
| M5 operational selection | Complete | a17/a11 reader-only selection, a16 rollback and a17 reselection pass serially on Snap/Starship. Both ordinary collector/bridge incarnations, writer/provider settings, shared Mesh CLI and unrelated Starship edits are preserved. Dotfiles selection commit `50685bc`. |

The selection at this checkpoint was a17/a11 reader, retained a16/a10 bridge,
collector a15 and writer 0.4.0a16. The reference publisher stays supported. Mesh's portable
conformance-kit/diagnostic follow-up is independent; its unimplemented testing
surface is not a dependency. Provider workflows and settings remain outside this
execution. No frontend, terminal attachment, device or event-product work is included.

The [integration evidence](../../evidence/2026-10-11-mesh-sdk-integration/REPORT.md)
records individual gates and retains the distinction between owned fixtures,
immutable installation, independent native evidence and selection.

M0–M5 are complete within the report's declared bounds. Changes are committed
locally; hosted CI and an a17 release publication are following receipts, not
claims made by this pass. No ordinary session restart was needed. Moving the
reference cached publisher into Observer remains separate work.
