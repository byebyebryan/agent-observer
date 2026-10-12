# Mesh SDK v1 maintenance and publisher ownership

Planning checkpoint, 2026-10-11. The user requested a pass to bring Observer's
Mesh integration up to date, then explicitly included publisher ownership
extraction. The current observation and networking contracts
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

Reader maintenance can use fresh environments containing accepted Observer a18
and released Mesh a13. Publisher extraction requires a successor Observer wheel
and a separately accepted Mesh artifact exposing the generic publisher/factory
boundary described below. It cannot be completed by repinning the existing
bridge environment. Reader and publisher acceptance remain independent; a13
reader maintenance can proceed while the Mesh producer prerequisite is pending.
Retained a10 bridging remains the prior operational selection until the new
publisher passes its gates. Never replace accepted a18 bytes with an extraction
build or report reader-only maintenance as completed publisher ownership.

## Mesh producer prerequisite

The current local bridge and fixed SSH command construct Mesh's reference
`ObserverAdapter`. That adapter performs Agent-native Service 2 IPC, parsing and
stream checks as well as generic proof/envelope construction. The reader's owned
`AgentProfile` does not remove this publisher coupling.

The reviewed Tmux [extraction design](https://github.com/byebyebryan/tmux-observer/blob/2fc30aa/docs/publisher-extraction-plan.md)
and [producer-first backlog](https://github.com/byebyebryan/tmux-observer/blob/2fc30aa/docs/publisher-extraction-review.md)
propose a generic Mesh publisher plus trusted factory injection. Its 17 study
checks and six profile cases establish bounded Tmux research feasibility only;
the copied CLI/prototype is not a production API or Agent-native acceptance.

Neither released a13 nor the inspected a14 source exports the proposed generic
publisher or CLI factory hook. Mesh must first implement and independently
accept that public boundary and freeze an immutable package. Proposed names
`CachedSource`, `CachedPublication` and `CachedPublisher`, and keyword-only
`publisher_factories` injection, are settled by the Mesh producer review. The
expected change is additive under SDK v1 with unchanged wire/profile schemas;
bind the accepted interface/capabilities when available, not assumed names or a
guessed future package version. This Agent plan edits no Mesh or Tmux source.

## Ownership and boundaries

Observer owns native validation/projection, identities, source receipts and
eligibility, plus its cached Service 2 source policy and publisher factory.
Mesh owns transport, catalog, generic admission, candidate/proof construction,
receipt counter/expiry checks and delivery lifetime. The observation core/local
service remains Mesh-free; the new cached source belongs to the optional
networking component and uses supported pure Service/public facades.
Conformance and diagnostics use the explicit owner profile and never invoke
provider collection or actions. No dependency is inferred from another
Observer's checkout or live artifact.

This pass leaves Codex/Claude native settings and sessions, collector cadence and
hints, writer, SSH authority, Tmux behavior and consumer entrypoints outside
selection. Preserve unrelated work in all checkouts. A shared launcher change
needed for Agent factory injection is separately coordinated with its Mesh/Tmux
owners and accepted domains; it is not a broad shared CLI/authority upgrade.
WSS, shared fleet brokers, event/replay products and attachment/actions remain
separate work. Ordinary bridge replacement, if accepted, affects cached
networking delivery; it can cause a client gap and must preserve conservative
revocation/reconnect behavior.

## Extracted publisher boundary

| Owner | Responsibility |
| --- | --- |
| Agent cached source | Canonical private socket/peer UID policy; Service 2 cached status/watch; native parsing and host/UID/boot/time-namespace binding; StreamGuard sequence/revision/incarnation checks; native epoch/publication barrier; bounded owned IO and cleanup |
| Agent profile | Existing pure native validation, projection/reconstruction, identities, component receipts and eligibility |
| Mesh generic publisher | Explicit profile binding, immutable admitted frame/barrier ownership, candidate/proof envelopes and digests, receipt counter/lease constraints, Bridge delivery and owned publication lifetime |
| Trusted installed entry point | Static lazy Agent factory selection shared by local serving and the actual fixed SSH bridge command; admitted descriptor binding before construction |

Implement an Agent-owned source/factory without inheriting or importing
`mesh_plus.observer.ObserverAdapter`. Do not copy Mesh's generic proof logic or
study CLI into Observer production. Existing `service_client` and
`service_public` provide native policy/guard references; select supported bounded
async transport rather than leaving blocking readers in an unowned executor.
Connection acquisition, guard-construction failure, active IO and repeated
cancellation must retire all admitted channels, tasks and iterators.

Native requests remain cached `status` and `watch`. A proof's checked native
cached read must begin after nonce admission; retained watch data supplies no
fresh proof. Core collection, provider queries/actions and terminal matching
cannot enter this source. Keep warming, complete-empty, partial/stale, gap,
EOF and new-service-incarnation cases distinct. Heartbeats and equal accepted
counters cannot extend original component expiry or conversation age.

The same static owner factory must execute for local publication and
`mesh-plus bridge --source SOURCE --stdio` through the actual configured SSH
route. A local-only extraction does not complete the boundary. A selected Agent
factory missing, failing or returning the wrong binding must fail explicitly
without reference fallback. Preserve Mesh's independently reviewed default and
other-domain dispatch, plus its catalog-only lazy import path. No factory/module
name is admitted from wire payloads, source configuration or plugin discovery.

Admitted source frames and barriers must be owned copies or have an equivalently
proved immutable boundary. Failed admission cannot update accepted counters.
Counter monotonicity and equal-counter expiry are scoped to the native publisher
and clock binding; replacement requires revocation and a fresh accepted binding.

## Execution and acceptance

| Gate | Work | Acceptance |
| --- | --- | --- |
| U0 baseline | Refresh both hosts' selections, protected controls/incarnations, actual local/SSH entrypoints and independent CLI/native comparisons; record a13 maintenance and separate publisher prerequisites | Source, package and live state remain distinct; current creation-clock/older-history limits explicit |
| U1 owner tooling | Add repeatable owner profile and owned IPC/proof lifecycle conformance using the installed Mesh kit; add bounded cached assessment with explicit `AgentProfile`; select a13 in the optional CI job | Every selected case explicitly passes without skips; forged proof, missing/expired receipts, restart/gap and cancellation reject/revoke correctly; core imports stay Mesh-free |
| U2 Mesh producer prerequisite | Mesh owner accepts a generic publisher and static factory seam, then freezes and documents its immutable artifact/public API | No producer/reference imports in generic helper; profile/proof/receipt/copy/cleanup guards; default CLI and authority compatibility; research code does not satisfy this gate |
| U3 Agent ownership implementation | Add cached Service 2 source, pure-profile generic publisher factory and trusted lazy entrypoint used locally and through fixed SSH | No Mesh reference-adapter inheritance/imports, collection/provider/action/client inventory; socket/peer/clock/stream guards, selected-factory failure, mutation isolation and owned cancellation tested |
| U4 immutable candidates | Freeze a successor Observer wheel and fresh reader/publisher prefixes against the accepted Mesh input, with exact role manifests/verifier/dependency receipts | Installed native/profile/SDK/schema/entrypoint gates; owner factory actually selected; ordinary runtime unchanged; old reader/new publisher and new reader/old reference bridge checked |
| U5 native delivery | Compare installed direct/cached/local/fleet reads to independent daemon metadata; prove actual local and fixed SSH factory invocation, fresh nonce-bound proof, publisher update/restart/outage/empty and repeated cancellation | Exact identities/runtime/phase/activity/order within known bounds; lossless native frames/original receipts; cached-only passivity; failure/restart revocation and all owned cleanup |
| U6 resource review | Compare exact old/new local/fleet reader and publisher workloads, normal and declared-capacity cases, including copy/validation costs and cleanup | CPU/PSS/FD/process/byte attribution and deadlines; no unexplained regression; conformance success is not a performance claim |
| U7 scoped rollout | Independently select reader and Agent-owned publisher on Snap/Starship; coordinate any shared factory launcher change and prove prior-tuple rollback/reselection | Exact controls and UID/PID/birth guards; collector/provider/writer/authority/Tmux behavior unchanged; real local/SSH cached recovery; prior artifacts retained for operational rollback |
| U8 closure | Update current read/publisher/operator handoff and manifests, run source checks, commit checkpoints and report source/installed/native/resource/CI receipts | Both local and fixed SSH publication use Agent source plus supported generic Mesh helper; observation/wire/SDK versions change only for a concrete incompatibility, while runtime packages receive successor versions; hosted success verified after any authorized push |

Conformance-tool interfaces are separate from the runtime SDK and wire. Do not
copy Mesh's test internals into Observer or treat its sample profile as a native
oracle. Diagnostics must distinguish acquired delivery from current receipts,
partial hosts and expired rows, return finite redacted codes, disable route
writes and close every owned connection. An assessment grants no retained
authority or action permission.

Use the existing Agent-owned selection tooling and authenticated archives.
Snapshot only scoped controls; never use a broad chezmoi apply. Reader and publisher
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
Source inspection confirms the generic publisher/factory prerequisite is not
implemented in a13 or the inspected a14 source. U0–U8 execution remains pending;
U1 reader maintenance can proceed independently, while U3 production extraction
waits for U2. Agent-native publisher feasibility, fixed-entrypoint proof and
resources must be established independently of the Tmux research result.

This plan now includes publisher extraction as a required completion outcome.
Any completed reader-only checkpoint is reported as partial progress until
publisher ownership and its operational gates close. Current accepted runtime
remains intact throughout planning.
