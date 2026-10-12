# Mesh SDK v1 maintenance adoption

Planning checkpoint, 2026-10-11. The user requested a pass to bring Observer's
Mesh integration up to date. The current observation and networking contracts
remain API 2, snapshot/watch 4, Service 2, Mesh Read/Delivery 1 and SDK interface 1.
The preceding [owner integration](mesh-sdk-v1-integration-status.md) and
[operational cleanup](evidence/2026-10-11-ops-cleanup/REPORT.md) remain accepted
for their exact artifacts. This plan records the proposed execution gates;
no source implementation or managed selection has changed at this checkpoint.

## Current and target artifacts

Both hosts select Observer a18 collection and a18/Mesh a11 readers. Independent
bridges select Observer a16/Mesh a10, and the historical writer retains its own
selection. Observer already supplies a pure `AgentProfile` consistently through
the supported configured Reader, guard and view interfaces.

The latest released Mesh prerelease is
[v0.1.0a13](https://github.com/byebyebryan/mesh-plus/releases/tag/v0.1.0a13),
tagged at `d9cdac4ba6314430c3c8eb4d948a9d697c90b411`. Its wheel is
`mesh_plus-0.1.0a13-py3-none-any.whl`, SHA-256
`62b42bc76e7d79d95d89c41ee6f73c5e0169d24e2f1ac911c151c13f1f2b6f07`.
A12/a13 add portable owner conformance and opt-in SDK diagnostics/assessment
without changing SDK v1 or the existing read/delivery schemas.

The following a14 source/private-wheel checkpoint adds optional WSS and an
additive lock revision 2. Existing SDK exports, signatures, Agent descriptor and
native/read/delivery schemas retain their bytes. WSS is a separate transport
selection with its own authentication, configuration and real-fleet acceptance.
It is outside this maintenance adoption.

Target fresh immutable reader and bridge environments containing accepted
Observer a18 and released Mesh a13. Accept each role separately; a reader upgrade
does not require a bridge upgrade to succeed. Retained a10 bridging remains a
supported intermediate selection if a bridge gate fails. Existing a18 wheel
bytes are reused. Tooling/tests/docs alone do not require a new Observer wheel;
changes to packaged runtime code require a successor immutable Observer artifact.

## Ownership and boundaries

Observer owns native validation/projection, identities, source receipts and
eligibility. Mesh owns transport, catalog, generic admission, proofs, expiry and
delivery lifecycle. The observation core/local service remains Mesh-free.
Conformance and diagnostics use the explicit owner profile and never invoke
provider collection or actions. No dependency is inferred from another
Observer's checkout or live artifact.

This pass leaves Codex/Claude native settings and sessions, collector cadence and
hints, writer, shared Mesh CLI/SSH authority, Tmux integrations and consumer
entrypoints outside selection. Preserve unrelated work in all checkouts.
Publisher extraction, WSS, shared fleet brokers, event/replay products and
attachment/actions remain separate work. Ordinary bridge replacement, if
accepted, affects only cached networking delivery; it can cause a client gap and
must preserve conservative revocation/reconnect behavior.

## Execution and acceptance

| Gate | Work | Acceptance |
| --- | --- | --- |
| U0 baseline | Refresh both hosts' selections, protected controls/incarnations and independent CLI/native comparisons; download exact a13 bytes and compare required schema/SDK bindings | Source, package and live state remain distinct; current creation-clock/older-history limits explicit |
| U1 owner tooling | Add repeatable owner profile and owned IPC/proof lifecycle conformance using the installed Mesh kit; add bounded cached assessment with explicit `AgentProfile`; select a13 in the optional CI job | Every selected case explicitly passes without skips; forged proof, missing/expired receipts, restart/gap and cancellation reject/revoke correctly; core imports stay Mesh-free |
| U2 immutable candidates | Build fresh a18/a13 reader and bridge prefixes with exact manifests, verifier hashes and dependency receipts; use a successor Observer wheel only if runtime code changed | Installed bytes, SDK descriptor, schemas, entrypoints and profile gates pass; ordinary selections unchanged |
| U3 native delivery | Compare candidate direct/cached/local/fleet reads to independent daemon metadata; exercise real SSH pull/push and isolated owner recovery/cancellation cases | Identity/runtime/phase/activity/order match within known sampling bounds; cached reads trigger no collection or native action; owned resources retire |
| U4 resource review | Compare normal and candidate local/fleet readers against the same workloads, including independent bridge cost and cleanup | Explicit CPU/PSS/FD/process attribution; no unexplained regression; conformance success is not a performance claim |
| U5 scoped rollout | Select reader, verify native delivery and rollback/reselection, then independently accept/select the bridge on Snap and Starship | Exact controls and UID/PID/birth guards; collector/provider/writer/shared authority unchanged; retained prior artifacts usable for rollback |
| U6 closure | Update current read/operator handoff and manifests, run source checks, commit checkpoints and report source/installed/native/resource/CI receipts | No public version bump without an incompatible change; hosted success is verified after any authorized push |

Conformance-tool interfaces are separate from the runtime SDK and wire. Do not
copy Mesh's test internals into Observer or treat its sample profile as a native
oracle. Diagnostics must distinguish acquired delivery from current receipts,
partial hosts and expired rows, return finite redacted codes, disable route
writes and close every owned connection. An assessment grants no retained
authority or action permission.

Use the existing Agent-owned selection tooling and authenticated archives.
Snapshot only scoped controls; never use a broad chezmoi apply. Reader and bridge
selection are serial checkpoints with explicit previous tuples. Do not overwrite
accepted/released wheels or reuse a failed candidate prefix. A producer defect
reopens its own source/candidate gate before operational selection.

The earlier measurements found roughly 8–10% of one core per raw fleet watcher
plus bridge work. A13 does not claim to repair that cost. Record an independent
regression comparison and hand mixed Observer/Mesh validation optimization to
its own checkpoint. Physical suspend, GUI/device acceptance and post-TUI-closure
native lifetime proof retain their existing deferred status.

## Preflight evidence and pending work

The preceding review compared deployed a11 against current a14 source: all SDK
exports/signatures and the Agent descriptor match; existing read/delivery/native
schemas are unchanged. The accepted private a14 wheel with Observer a18 passed
353 source tests, seven independent profile cases and ten owned IPC/proof cases.
Those results establish bounded compatibility with that exact candidate, not
released-a13 adoption, WSS operation or managed selection.

Release API inspection confirms a13 remains the latest published Mesh artifact.
U0–U6 execution remains pending. This planning checkpoint prepares the concrete
maintenance pass while preserving the independently accepted current runtime.
