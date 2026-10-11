# Claude support retirement

Date: 2026-10-11. The user explicitly retires Claude support and authorizes a
regular execution goal loop with commits as accepted checkpoints are reached.
This supersedes the prior required-second-provider and maintenance-only scope.
Claude use continues through native session management/Agent View.

## Scope and contract decision

Codex is the only implemented observation provider after this pass. Remove
Claude native collection/projection/history, SDK dependencies, hints, service
metadata-memo transport, launch cues and Claude-specific notification intake/
rendering. Remove active Claude operator/acceptance paths and their dedicated
implementation tests. Keep shared reconciliation, leases, uncertainty, identity,
read-cache, multiple-source isolation and Mesh semantics provider-neutral.

API 2, snapshot/watch 4, Service 2 and Mesh SDK 1 remain the read boundary.
The frozen wire vocabulary can describe Claude-shaped supplied observations;
that is pure data admission, not native provider support. Retain those schema
bytes and generic multi-source fixtures. Reject unsupported native selection
before any source, process or filesystem access. No compatibility collector,
fallback or dormant Claude runtime implementation is retained.

Dated evidence and released artifacts retain their original bounds. Links to
removed source/tooling should point to immutable pre-retirement Git source.
Native Claude sessions, history, settings, hooks and Agent View are not changed.
Attachment/actions, downstream clients, Mesh source/runtime upgrades, publisher
extraction and notification/event development remain separate work.

## Execution and acceptance

| Checkpoint | Work | Required acceptance |
| --- | --- | --- |
| R0 scope | Record the decision and inventory current source/selected artifacts | Existing checks pass; explicit Codex-only direction and frozen-wire decision |
| R1 removal | Remove Claude implementations/dependencies and private service plumbing; reconcile active tooling and meaningful shared tests | No removed-provider imports or reachable collectors; explicit rejection before I/O; all remaining core/Mesh checks pass |
| R2 package/native | Build a clean immutable successor with core and optional Mesh profiles only | Exact installed bytes/dependencies, independent native Codex comparisons on Snap/Starship, local/fleet cached pull/push and expiry/cleanup gates |
| R3 operations | Select accepted Codex-only collector/read artifacts on both hosts with captured rollback | Scoped verification, restart/recovery and rollback/reselection; no Claude sources/children/dependency in selected Observer runtime; provider/bridge/writer/foreign state preserved |
| R4 handoff | Update current guides/support declaration and evidence; review and commit | Current documentation matches source and selection; dated history is clearly historical; source/installed/native/operations receipts remain distinct |

The existing Mesh reference bridge can keep its independently accepted artifact:
it consumes the new Codex-only cached Service 2 view without collecting providers.
Its old package contents are rollback/provenance, not enabled Claude support.
Do not rewrite frozen archived artifact verifiers or released manifests.

Runtime/sample correctness is proved against independent existing Codex daemon
reads. Observer-to-Observer comparison establishes delivery parity only. Capture
bounded identity/state/age/coverage metadata, not native conversation payloads.
Preserve cadence, native hints, original receipts and all accepted Codex limits.
No provider restart or current conversation exit is required.

## Status

R0 is accepted (466 baseline tests). R1 removes the native adapter, SDK/history,
service memo and Claude hint/notification intake. Obsolete combined/background
proofs are retired; focused Codex authority, saved, read and service gates remain.
Shared core retention/expiry and synthetic multi-provider tests remain. R1
passes 353 tests, including rejection before I/O and byte-identical read schemas.
R2 package/native is accepted; [bounded receipts](evidence/2026-10-11-claude-retirement/REPORT.md)
record exact artifacts, direct/cached Codex comparisons and owned service
lifecycle on both hosts. R3–R4 remain pending until operational/handoff receipts. Source baseline is `b2125b4`; selected
reader a17/Mesh a11, collector a15, bridge a16/Mesh a10 and writer 0.4.0a16.
