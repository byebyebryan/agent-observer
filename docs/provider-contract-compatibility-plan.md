# Provider contract compatibility

Date: 2026-10-06; current provider scope clarified 2026-10-08. Status: accepted
support policy, implemented for the API-2 Codex and passive Claude adapters. The
[a5 completion report](evidence/2026-10-08-codex-observation-completion/REPORT.md)
records its installed/native proof. This supersedes the release-registration
direction in the
[discovery/monitoring review](discovery-monitoring-contract-review.md).
The original a11/`0.3.0a1` transition and execution table below are historical.
Current Codex reads use the owning daemon only, including its database-only
metadata catalog; private saved-store fallback is removed. The independent
[a8 Claude gate](evidence/2026-10-08-claude-observation/REPORT.md) accepts passive
registration/status, bounded terminal-job and saved metadata reads on Snap.
The next [interactive-only plan](claude-interactive-observation-plan.md) requires
new census/absence and mode-off proof; it does not inherit those capabilities
from a8 or provider release labels.

## Support policy

Provider compatibility follows the protocol, metadata and CLI contracts Observer
uses. Routine Codex/Claude upgrades that preserve those contracts remain usable
without adding a version or executable hash to an allowlist, rebuilding Observer
or restarting ordinary sessions for requalification.

Record actual versions, hashes, topology and process births for diagnostics and
test provenance. Retain executable/file/endpoint ownership and incarnation checks.
A prepared action still binds its actual executable and configuration: replacement
between preparation and entry invalidates that plan. A fresh plan may use the
replacement once its required entry contract is established. This distinction
keeps context-change protection without a list of approved provider releases.

Observer's own public wire versions, packaged artifact receipts and dependency
locks retain their existing reproducibility/compatibility roles. A provider
release number must not become an accepted-value domain in the public model.

## Required contract inventory

The current Codex observation dependency is the daemon status-v2 and
database-only-catalog-v1 contract recorded in the artifact manifest. Shape and
semantic checks remain independent of release numbers. Current Claude reads bind
the registry/job metadata contract plus independent saved identity/history reads.
Writer requirements and historical receipts do not grant extra observation
capabilities. The interactive census contract is proposed, not accepted.

| Capability | Required contract | Independent conditions |
| --- | --- | --- |
| Codex managed discovery | Existing owning endpoint; `initialize` namespace; database-only `thread/list`, `thread/loaded/list`, `thread/read` UUID/tree-root/name/cwd/status and pagination metadata | Kernel peer/listener ownership, expected configuration scope and unchanged runtime birth; no daemon launch, private-store fallback or thread load for discovery |
| Codex runtime, phase and kind | Native idle/active/notLoaded status, active flags and explicit native child/user signals | Idle/active establishes running; positive notLoaded plus readable non-ephemeral saved identity establishes parked; loaded-list absence does not. Unknown/conflicting values remain unresolved per row |
| Codex activity/outcome | Latest `thread/turns/list` metadata with unloaded/empty items; native start/completion clock units and explicit terminal status | No conversation content; outcome, phase and runtime remain independent; a missing optional clock or outcome does not disable discovery |
| Claude discovery/presence at a8 | Provider registry UUID, worker PID/birth/PID-domain/kind/cwd; exact job short-ID/UUID relation where used | Authenticated stable native registration establishes running; no terminal/client inventory or mutating roster CLI |
| Claude phase/parked at a8 | Registry state/time/wait discriminator, job terminal state/time/tempo, typed questions and in-flight counters | Independently proved interactive status/waits; terminal jobs need saved identity, no pending work and complete stable native inventories; saved-only absence/foreground exit remain unknown |
| Claude saved history at a8 | SDK session-list API and required metadata fields; exact non-sidechain transcript envelope ID/type/time contract; bounded positive UUID proof | Independent saved coverage/clock failure; optional history dependency on Snap; no negative lifecycle from saved existence |
| Codex New/Resume | Native TTY entry; configured store selection; exact Resume session-ID argument and normal native permission/trust handling | Current cwd/config/executable/endpoint context, exact refreshed Resume reference and entry revalidation |
| Historical Claude New/live attach/saved Resume | Background launch and bounded receipt identity, exact typed job attach, saved Resume identity behavior and settings/context selectors | Reference only; action/attachment and the Claude runtime decision are deferred |

Compatibility includes behavior, not only JSON shape. A field named `idle` does
not establish prompt readiness on its own. A terminal job does not establish
runtime absence. Existing independently proved predicates must have their
semantic requirements expressed in the profiles and checked against available
native evidence. New predicates or actual contract changes require focused native
proof; a different release label alone does not require that proof.

Claude private registry/job fields and the removed Codex saved-store
fallback are internal provider interfaces. Contract checks reduce needless
upgrade failures, but
cannot guarantee detection of every upstream semantic change. Prefer a passive
public interface when it supplies the required information. Keep independent
ordinary comparisons and controlled lifecycle/clock tests as ongoing validation,
without requiring a complete manual certification pass for every daily build.

## Compatibility and feature detection

1. Establish source provenance and owning runtime/worker identity. These are
   required even when all expected fields appear in a response or file.
2. Use available declared protocol/schema/capability information and bounded
   validated metadata to select the required contract profile. Where no declaration
   exists, use the observed minimal field/type/state relations plus explicit
   semantic predicates. Do not fingerprint the whole native payload or every
   optional field: an unrelated additive change should remain compatible.
3. Probe only already accepted passive operations against an existing runtime.
   Do not create, resume, stop, adopt, approve or mutate ordinary sessions to
   discover support. Entry behavior without a safe query uses documented CLI
   requirements and controlled conformance tests; real writes remain deliberate.
4. Decide compatibility independently for saved discovery, live presence, phase,
   activity, outcomes, parked and each entry route. A missing method or incompatible
   field disables the affected capability with a finite reason. Healthy sibling
   capabilities/providers/rows remain usable.
5. Treat unknown native enum variants as unknown observations. Accept unrelated
   native fields through the bounded allowlist projection. Keep Observer's own
   public wire validation strict, so native tolerance does not create an accidental
   extensibility rule for consumer input.
6. Cache compatibility only with the relevant source/worker/runtime incarnation
   and inspected file context. Recheck on restart, replacement or required-shape
   change. A cache hit never renews the phase or conversation clock.

Capabilities report the contracts actually usable in the observed context.
Adapter-potential states must not advertise current compatibility. A writer's
requirements remain separate from a read capability; functioning saved discovery
does not guarantee that a native entry route is available.

The independent evaluation tool follows the same policy boundary while retaining
its own implementation and native evidence: unknown releases are recorded, not
silently omitted. Unsupported contracts, duplicate workers and incomplete native
reference coverage remain explicit.

## Observer-only execution checkpoints

| Checkpoint | Work and acceptance |
| --- | --- |
| P0: concrete dependency contracts | Inventory used RPC fields/methods, filesystem and SQLite metadata, SDK API, CLI flags/cues and required semantics. Separate compatibility from executable provenance/incarnation. Reuse existing native evidence for its predicates, recording the actual images as provenance. |
| P1: compatibility layer | Replace runtime `registered`/`supported_versions` gates and release-based phase selection with minimal required capability profiles and bounded checks. Remove whole-migration fingerprints as compatibility selectors where an independently validated required projection is available. Preserve kernel/ownership/changed-context checks. |
| P2: adapter and writer migration | Bind each read dimension and entry route to its required contract. Separate installed CLI, daemon peer, worker and saved store contracts. Eliminate global Claude installed-image gating of compatible worker reads and maintain explicit duplicate-context ambiguity. |
| P3: conformance and diagnostics | Test a changed version/hash with an unchanged required contract, irrelevant native additions, missing required methods/fields, new state variants, mixed worker generations, duplicate IDs and a real executable replacement during a prepared handoff. Diagnostics identify the contract/capability/reason alongside observed release provenance. |
| P4: independent artifact acceptance | Build an Observer candidate, exercise public read/write and independent native comparisons on Snap/Starship, verify affected New/Resume/phase/age/parked routes in isolated contexts and check passivity/cleanup. This accepts the contract-based adapter and writer; it does not create a new daily release allowlist. |

The Codex 0.160.1 and Claude 2.1.291 images recorded in the original pass are test points,
not the next hardcoded supported versions. Older surviving contexts should be
recognized by their required contracts, with conflicting/missing evidence still
explicit. Public SDK-version representation and any capability metadata shape
change require the normal versioned consumer conformance gate; no silent v2
extension or legacy discovery stack is introduced.

Other review findings, especially watch age/classification/bounds and write-result
identity validation, retain their separate acceptance cases. Observer is accepted
independently before a separate Plus implementation/rollout checkpoint. The
adjacent Plus checkout's `docs/observer-client-handoff.md` records this support
policy and must not impose provider release pins in its UI or cache.
