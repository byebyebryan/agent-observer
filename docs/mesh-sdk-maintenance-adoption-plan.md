# Mesh SDK v1 maintenance and publisher ownership

Planning checkpoint updated, 2026-10-11, after Mesh accepted its publisher seam.
The user requested a pass to bring Observer's Mesh integration up to date, then
explicitly included publisher ownership extraction. The current observation and
networking contracts
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

The a14 source/private-wheel checkpoint adds optional WSS and an
additive lock revision 2. Existing SDK exports, signatures, Agent descriptor and
native/read/delivery schemas retain their bytes. WSS is a separate transport
selection with its own authentication, configuration and real-fleet acceptance.
It is outside this maintenance adoption.

Mesh now accepts the additive SDK v1 publisher surface in its a15 private
candidate. The runtime checkpoint is `c46262c0f0185244e96c79ea2036e4f57b2e4e1e`;
the inspected owner handoff/evidence commit is `de2ee36`. The accepted wheel is
`mesh_plus-0.1.0a15-py3-none-any.whl`, SHA-256
`42b25045f8f89afda61e56525f443a189dcc6769637aee5bcab959f096527f0f`, retained at
`/tmp/mesh-publisher-promotion/wheel/`. Its bytes were checked against that receipt
during this plan refresh. The
[public API](https://github.com/byebyebryan/mesh-plus/blob/de2ee36/docs/publisher-api.md)
and [installed acceptance](https://github.com/byebyebryan/mesh-plus/blob/de2ee36/docs/evidence/2026-10-11-publisher-factory/README.md)
are the implementation input. A15 is not yet a public release or deployed tuple.
All previous SDK signatures/exports survive; three publisher exports are added.
The contract lock and frozen schemas retain their a14 bytes.

Target new reader and publisher environments against this exact accepted a15
input; an intermediate a13 reader selection is optional, not a prerequisite.
Publisher extraction requires a successor Observer wheel. It cannot be completed
by repinning the existing bridge environment. Reader and publisher acceptance
remain independent. Retained a10 bridging remains the prior operational selection
until the new publisher passes its gates. Never replace accepted a18 bytes with
an extraction build or report reader-only maintenance as completed publisher
ownership. Public immutable Mesh release and the owner artifact/operational gates
remain prerequisites for managed adoption, rather than for source integration
and private candidate acceptance.

## Accepted Mesh publisher input

The current local bridge and fixed SSH command construct Mesh's reference
`ObserverAdapter`. That adapter performs Agent-native Service 2 IPC, parsing and
stream checks as well as generic proof/envelope construction. The reader's owned
`AgentProfile` does not remove this publisher coupling.

The reviewed Tmux [extraction design](https://github.com/byebyebryan/tmux-observer/blob/2fc30aa/docs/publisher-extraction-plan.md)
and [producer-first backlog](https://github.com/byebyebryan/tmux-observer/blob/2fc30aa/docs/publisher-extraction-review.md)
propose a generic Mesh publisher plus trusted factory injection. Its 17 study
checks and six profile cases establish bounded Tmux research feasibility only;
the copied CLI/prototype is not a production API or Agent-native acceptance.

That producer implementation prerequisite is now satisfied by the accepted a15
source/private wheel. Mesh's installed gates exercise both profiles, local and
real fixed SSH publication, optional WSS, mixed a10 reference bridging, factory
failure/default dispatch, receipt/copy guards and cancellation. Those gates use
reviewed old Observer packages and synthetic owner sources; they do not accept
Agent's proposed extracted Service 2 source, current daemon parity, fleet
selection or resource costs. This Agent plan edits no Mesh or Tmux source.

The supported surface is now concrete:

```python
from mesh_plus.api import CachedPublication, CachedPublisher, CachedSource
from mesh_plus.cli import configured_adapter, main

# make_agent_publisher is a proposed Agent-owned factory, not an existing export.
publisher = configured_adapter(
    private_sources_toml, source_id,
    publisher_factories={"agent": make_agent_publisher},
)
main(publisher_factories={"agent": make_agent_publisher})
```

`CachedSource.snapshot()` asynchronously returns a checked cached native frame.
Its `watch()` returns an async iterator with `aclose()`, yielding
`CachedPublication(frame, epoch, barrier)`. Construct
`CachedPublisher("agent", host, source, native, profile=AgentProfile())` rather
than a reference-adapter subclass. The synchronous factory receives
`(host, source, socket)` and acquires no resources during construction. Mesh's
embedded async `run` also accepts the keyword-only factory mapping.

The stock Mesh console entrypoint still selects reference adapters. The selected
trusted launcher named `mesh-plus` must supply the static lazy Agent factory for
both local `serve` and the actual remote `bridge` command. Intentionally omitted
domains retain the reference branch; an explicitly selected factory failure or
invalid returned binding has no fallback. No public config, wire or executable
selector was added. SDK v1 and current read/profile/delivery contracts suffice;
Observer's broad dependency floor alone does not accept this new artifact.

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
Construction must acquire no connections or background tasks. There is no global
publisher shutdown callback: each snapshot and watch iterator owns its resources.
Connection acquisition, guard-construction failure, active IO and repeated
cancellation must retire all admitted channels, tasks and iterators. Bound native
frame size, pending IO and admitted history explicitly; a synchronous factory or
profile callback cannot be preempted by Mesh.

Native requests remain cached `status` and `watch`. A proof's checked native
cached read must begin after nonce admission; retained watch data supplies no
fresh proof. Core collection, provider queries/actions and terminal matching
cannot enter this source. Keep warming, complete-empty, partial/stale, gap,
EOF and new-service-incarnation cases distinct. Heartbeats and equal accepted
counters cannot extend original component expiry or conversation age.

The same static owner factory must execute for local publication and
`mesh-plus bridge --source SOURCE --stdio` through the actual configured SSH
route. A local-only extraction does not complete the boundary. The owner launcher
must include Agent in its static map, with its implementation import inside the
factory. A selected factory whose dependency is missing, which fails, or which
returns the wrong binding must fail explicitly without reference fallback.
Omitting Agent from the map selects the reference path and fails Agent ownership
acceptance. Preserve Mesh's independently reviewed default and
other-domain dispatch, plus its catalog-only lazy import path. No factory/module
name is admitted from wire payloads, source configuration or plugin discovery.

Admitted source frames and barriers must be owned copies or have an equivalently
proved immutable boundary. Failed admission cannot update accepted counters.
Counter monotonicity and equal-counter expiry are scoped to the native publisher
and clock binding; replacement requires revocation and a fresh accepted binding.
Mesh tracks receipts present in consecutive accepted samples, not all retired
components. Agent's native source must independently enforce ordering across
snapshot/watch acquisitions and component disappearance/reappearance, using
bounded native incarnation/stream policy. Generic wrapping is not a substitute
for those native checks.

## Execution and acceptance

| Gate | Work | Acceptance |
| --- | --- | --- |
| U0 baseline/input | Refresh both hosts' selections, protected controls/incarnations, actual local/SSH entrypoints and independent CLI/native comparisons; verify the accepted a15 wheel/API/lock against Mesh's receipts | Source, private package, released package and live state remain distinct; current creation-clock/older-history limits explicit; producer seam available, owner acceptance pending |
| U1 owner tooling | Add repeatable owner profile and owned IPC/proof lifecycle conformance using the installed a15 Mesh kit; add bounded cached assessment with explicit `AgentProfile`; use the exact a15 candidate in an isolated optional CI job | Every selected case explicitly passes without skips; forged proof, missing/expired receipts, restart/gap and cancellation reject/revoke correctly; core imports stay Mesh-free; hosted CI may use the candidate before release only with authenticated immutable retrieval |
| U2 native source feasibility | Settle Agent's bounded asynchronous Service 2 transport, cross-acquisition ordering and native barriers against the accepted publisher surface; prove a disposable source/factory and decide the scoped launcher wiring | Real cached status/watch only, nonce-before-read, UID/host/clock binding, component disappearance/reappearance, concurrent reads, source loss/restart and cancellation cleanup; no factory resources or shared launcher changes |
| U3 Agent ownership implementation | Add cached Service 2 source, pure-profile generic publisher factory and trusted lazy entrypoint used locally and through fixed SSH | No Mesh reference-adapter inheritance/imports, collection/provider/action/client inventory; socket/peer/clock/stream guards, selected-factory failure, mutation isolation and owned cancellation tested |
| U4 immutable candidates | Freeze a successor Observer wheel and fresh reader/publisher prefixes against the exact a15 input, with exact role manifests/verifier/dependency receipts | Installed native/profile/SDK/schema/entrypoint gates; owner factory actually selected; ordinary runtime unchanged; old reader/new publisher and new reader/old reference bridge checked; a13 remains a released maintenance compatibility input |
| U5 native delivery | Compare installed direct/cached/local/fleet reads to independent daemon metadata; prove actual local and fixed SSH factory invocation, fresh nonce-bound proof, publisher update/restart/outage/empty and repeated cancellation | Exact identities/runtime/phase/activity/order within known bounds; lossless native frames/original receipts; cached-only passivity; failure/restart revocation and all owned cleanup |
| U6 resource review | Compare exact old/new local/fleet reader and publisher workloads, normal and declared-capacity cases, including copy/validation costs and cleanup | CPU/PSS/FD/process/byte attribution and deadlines; no unexplained regression; conformance success is not a performance claim |
| U7 scoped rollout | After public immutable package release, independently select reader and Agent-owned publisher on Snap/Starship; coordinate any shared factory launcher change and prove prior-tuple rollback/reselection | Exact released bytes, controls and UID/PID/birth guards; collector/provider/writer/authority/Tmux behavior unchanged; real local/SSH cached recovery; prior artifacts retained for operational rollback |
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
plus bridge work. Neither a13 maintenance nor the a15 publisher acceptance claims
to repair that cost. Record an independent regression comparison and hand mixed
Observer/Mesh validation optimization to
its own checkpoint. Physical suspend, GUI/device acceptance and post-TUI-closure
native lifetime proof retain their existing deferred status.

## Preflight evidence and pending work

The preceding review compared deployed a11 against current a14 source: all SDK
exports/signatures and the Agent descriptor match; existing read/delivery/native
schemas are unchanged. The accepted private a14 wheel with Observer a18 passed
353 source tests, seven independent profile cases and ten owned IPC/proof cases.
Those results establish bounded compatibility with that exact candidate, not
released-a13 adoption, WSS operation or managed selection.

The refreshed release inspection confirms a13 remains the latest published Mesh
artifact. Mesh source/private-wheel acceptance now provides the previously
missing generic publisher and installed factory seam; the exact a15 hash was
verified locally. The earlier external U2 implementation prerequisite is closed.
U2 now covers Agent-native feasibility before production integration. Observer's
U0–U8 execution remains pending: source work/private candidate acceptance can
proceed without further Mesh API implementation, while public release and scoped
owner acceptance still precede operational adoption. Agent-native publisher
feasibility, fixed-entrypoint proof and resources remain independent of Mesh's
generic tests and the Tmux research result.

This plan now includes publisher extraction as a required completion outcome.
Any completed reader-only checkpoint is reported as partial progress until
publisher ownership and its operational gates close. Current accepted runtime
remains intact throughout planning.
