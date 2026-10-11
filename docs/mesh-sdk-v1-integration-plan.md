# Mesh SDK v1 integration plan

Date: 2026-10-10. Status: planning/research checkpoint; production implementation,
new artifact acceptance and operational selection are pending. The user requested
a plan followed by review/research/validation before implementation. The
[planning report](evidence/2026-10-10-mesh-sdk-planning/REPORT.md) records completed
source review and isolated package/fixture probes with their limits.

## Goal and baseline

Agent Observer owns its pure Agent state profile and explicitly supplies it to
Mesh SDK v1. Mesh owns transport, authority, fleet composition, proof/lease
admission and connection lifetime. This makes networking development independent
of both the Mesh reference integration and Tmux Observer's checkout. Preserve
the accepted observation semantics and optional dependency boundary.

Observer source starts at `611be2c88daf2327a3117154ee4642998b1d89f6`.
The reviewed Mesh documentation starts at `17b8096beed20eeece3d0d86e2df655d1bc1f8ed`;
the released `0.1.0a11` wheel comes from
`9d570c59041832d177519fd634d26c56ed572e81`, SHA-256
`9d3c2446b2391ab2271236804b4dfc03dfa5d29f2766d72b3d12086848b36359`.
Use its [SDK specification](https://github.com/byebyebryan/mesh-plus/blob/17b8096beed20eeece3d0d86e2df655d1bc1f8ed/docs/sdk-api.md)
and [owner handoff](https://github.com/byebyebryan/mesh-plus/blob/17b8096beed20eeece3d0d86e2df655d1bc1f8ed/docs/sdk-owner-handoff.md).

The inspected managed configuration selects Observer `0.5.0a16` readers and
separate resident bridge prefixes with Mesh `0.1.0a10`. Collection remains
Observer `0.5.0a15`; the writer independently retains `0.4.0a16`. This is a
configuration/archive baseline, not a new both-host live acceptance receipt.
Earlier a12/a4, a13 and a9 adoption reports retain their historical bounds.

SDK interface 1, Mesh Read/Delivery wire 1, the Agent profile
`agent-observer.mesh-candidate.v1`, Observer API 2, snapshot/watch 4 and Service 2
are separate version axes. This migration needs no public wire or native
semantic change. A concrete incompatible change would reopen contract review.

## Ownership and implementation shape

Add an optional `agent_observer.mesh_profile` module containing an Agent
`StateProfile` and immutable host/source-bound codec. Import Mesh only for
explicit networking work. Use `agent_observer.public` and `service_public` for
native identity and frame admission. Profile callbacks perform no provider,
filesystem, service, network, action, attachment or alert I/O.

| Surface | Responsibility |
| --- | --- |
| Descriptor | Use `descriptor("agent")`; require SDK 1 and the existing native/profile contract and frame ceiling. Do not invent a profile ID or derive support from provider release numbers. |
| Bound codec | Validate Service 2 frames and exact native host binding; project native clock, publisher, emission and original component receipts. Keep host/source/profile binding immutable. |
| Response callback | Perform only additional pure domain checks, if needed. Mesh validates the aggregate schema and reconstructs/admit-checks native frames; do not recursively call its response validator from this callback. |
| Native state/reconstruction | Retain complete service metadata, snapshot metadata, canonical row order and every row field. Reconstruct exactly, including warming `snapshot: null`. |
| Identity | Use the full public identity tuple: host, provider, namespace, native ID kind and native ID. Preserve children and unknown classifications in raw frames. |
| Receipts | Preserve opaque `provider:namespace` native source IDs and each original component's accepted counter, health and expiry. Configured source selector `agent` is a different identity. |
| Eligibility | Preserve the accepted reference policy. Unsaved rows require current runtime health and a positive runtime receipt. Saved rows remain subject to conservative Mesh receipt admission. |
| Read CLI | Supply one explicit profile consistently; retain original conversation age, presentation-only filters, qualifications and timed expiry rendering. |
| Mesh | Enforce packaged schemas, byte limits, uniqueness/order, lossless roundtrip, nonce/digest, original receipt/lease bounds, delivery barriers and owned cleanup. |

Mesh's concurrently authored `docs/sdk-maintenance-plan.md` proposes a portable
conformance kit, compatibility diagnostics and explicit-profile measurements.
These are pending Mesh-owned work, not new SDK guarantees. They do not block
this owner pass. Do not infer current evidence validity from `doctor` package
availability or `probe` acquisition success; use the profile-bound Reader and
current-view/guard checks for acceptance.

Preserve the current receipt policy exactly: for a row's provider/namespace, the
required set consists of its native current/partial component receipts. Every
required receipt must remain usable in Mesh. No matching positive receipt means
no effective row. Neither an empty set nor fresh sibling-provider history grants
authority. Refining this conservative policy is a separate semantic checkpoint.

SDK DTOs are shallowly frozen. Projection, reconstruction, admission and human
presentation must leave caller frames and nested metadata unchanged. Test that
nonmutation explicitly; immutable codec binding alone does not establish it.

Use `mesh_plus.api` for versioned state/read entry points. Explicit configuration
still uses Mesh's existing catalog/authority surface. Move the CLI's clock-domain
import away from `mesh_plus.observer` to the generic Mesh evidence helper;
BOOTTIME and clock-context I/O stay in the CLI/transport boundary. The SDK's
documented example also uses generic evidence/protocol/transport modules.
Do not copy their implementations into Observer or turn clock reads into profile
callbacks. The profile validates native/domain input; generic proof enforcement
stays in Mesh. No new raw `Client` facade is exposed in this pass.

The Mesh reference cached publisher may remain in place. Pure profile adoption
does not imply publisher extraction. The first candidate must demonstrate a11
reader compatibility with the independently selected a10 bridge.

## Execution sequence

### M0 — portable checks and safe operations prerequisite

Repair the current operations self-test/CI dependency on undeclared `chezmoi`.
Either make the default fixture gate independent of external deployment tooling
and keep a mandatory separate tool-backed gate, or explicitly provision its
required tool in CI. Preserve the real rendering/ownership assertions; silent
skips are not acceptance. Include finite stdout diagnostics in failed assertions.

Repair `scripts/mesh-selection-acceptance` to authenticate the selected resident
bridge prefix, independently of the reader. Add a meaningful fixture covering
different prefixes, foreign process rejection and pre-stop incarnation guards.
Do not exercise its real stop/rollback path during source tests.

Acceptance: clean-environment core checks and declared operational checks;
separate reader/bridge fixture passes; no loss of pre-mutation safety. The CI
repair gates new package acceptance. The bridge guard repair gates live rollback.

### M1 — pure native profile

Implement the optional profile/codec using supported facades. Establish bounded
native parsing, exact projection and immutable bindings without importing
collection, service runtime, provider adapters, writes or Mesh's reference
Observer module. Core/local service remain Mesh-free.

Acceptance: valid empty/warming/current/partial/historical views; both providers
and multiple namespaces; exact reconstruction and independent receipts; native
invalid/oversized input and conflicting bindings rejected. Preserve accepted
unknowns and Claude coverage limitations.

### M2 — explicit reader and presentation wiring

Update `mesh_cli.run` to use SDK v1 entry points. Pass the same profile to
`configured_reader`, `ReadGuard`, `validate_response`, `current_sessions` and
the reconstruction callback supplied to `human_view`. Preserve host/source
selection, route-reporting opt-out and stream shutdown on count, cancellation,
invalid frames, output failure and EOF. Keep raw machine envelopes lossless.

Raise the optional Mesh dependency floor to the release providing SDK 1 while
retaining a reviewed compatibility range. Runtime compatibility follows the SDK
descriptor/contract; exact wheel hashes belong to artifact provenance. Missing
or incompatible SDKs fail with bounded diagnostics. Core and local read commands,
`mesh api` and help remain usable without Mesh.

Acceptance: source tests run with a pinned released a11 SDK and no Tmux Observer;
all explicit profile paths exercised with reference imports blocked. Local,
fleet and hosts scopes, raw/human pull/watch, silent expiry, children and age
presentation, healthy sibling isolation and repeated cancellation are covered.

### M3 — independent conformance and immutable package

Make Observer's Mesh CI job install the reviewed a11 wheel by checksum rather
than the current a9 artifact. Test both the Mesh-free core and the explicit
profile environment on supported Python versions; optional cases cannot silently
skip in the Mesh gate. Keep the sibling checkout out of required CI.

Add owner-native frozen Service 2 fixtures for Codex, Claude, combined and
multi-namespace sources. Compare reconstruction and effective selection against
the selected a10 reference at original time, component expiry and late time.
Supplement parity with independently specified expected eligibility/fault
outcomes so matching implementations are not the only oracle.

Cover wrong host/source/hello, duplicate identity, malformed native frame,
forged digest/nonce, receipt removal/health upgrade/lease extension, empty
requirements, warming/historical rows, publisher restart, gap/resync, catalog
replacement, disconnect and cancellation. Use owned IPC and disposable SSH
routes for transport faults. Reuse the SDK's case design through Owner tests;
do not require Mesh's test checkout in normal Observer development.

If Mesh's portable conformance kit is independently accepted and released before
this gate, pin that artifact and supply Owner fixtures and independent expected
results. Otherwise use bounded Agent projection/receipt/wiring cases and owned
delivery tests, with the existing Mesh boundary suite as supplementary evidence.
Do not build a generic conformance kit or copy Mesh's whole transport suite into
Observer, or bind tests to an unreleased `mesh_plus.testing` interface.

Build a new immutable Observer wheel and isolate its installation with the
released Mesh wheel. Update `verify-mesh-artifact` to validate SDK/profile/native
capabilities, manifest/checksum and installed bytes. Replace its growing package
version admission list with the reviewed artifact/contract checks; old archived
verifiers remain intact for rollback. Verify imports and `pip check` from outside
the checkout. Record hashes and frozen wire/schema parity.

Acceptance: source/CI, frozen conformance, installed wheel and owned transport
gates all pass independently. This accepts no provider inventory or live rollout.

### M4 — fresh installed native and mixed-artifact proof

Use the [CLI/native workflow](observation-validation-workflow.md). Independently
query existing Codex daemons on Snap and Starship and provider-owned Claude
interactive evidence on Snap. Compare exact identity, state, phase, child kind,
conversation clocks and declared uncertainty against the installed candidate's
direct/local cached/fleet pull and replacement push, with bracketing samples.
An Observer-to-Observer comparison establishes delivery parity only.

Demonstrate a11 candidate reader against the retained a10 bridge, then against
an isolated a11 reference bridge if its selection is proposed. Establish recovery
on owned test endpoints without restarting providers or normal collectors.
Continue through gaps to full resync. Record host/provider/package/topology and
source sampling bounds; retain only bounded metadata and finite reasons.

Measure matched warm-read/watch CPU, RSS/PSS, reader cleanup and latency with one
and several readers. Confirm no extra collection loop or persistent growth.
Compare with the selected baseline; investigate meaningful regressions rather
than inventing a new memory/CPU budget. Previous soaks are historical evidence.

Acceptance: independently explained active/history comparisons within existing
provider limits; original age and component leases preserved; passive read
delivery and cleanup proved. Physical suspend and GUI/device behavior stay deferred.

### M5 — staged operational selection and handoff

Freeze separate reader and bridge selections, capture exact rollback controls
and protected collector/writer/provider configuration, and verify process birth
and owned socket/unit identity before mutation. Select the accepted reader first;
the existing bridge can remain. Any bridge/Mesh CLI selection follows a separate
gate and coordination with owners sharing the global Mesh selection.

Run serialized Snap/Starship reader checks, reconnect and reviewed scoped
rollback/reselection using the repaired prefix guard. Verify protected state
before and after. Keep artifact and live receipts distinct; concurrent unrelated
deployment drift stops selection until reconciled. No Tmux, SSH Plus authority,
provider policy, frontend or device rollout is inferred.

Update current guides and the native/read handoff with the actual selected tuple,
SDK 1 obligations and accepted limitations. Historical reports keep their bounds.

Acceptance: selected reader behaves like the accepted package on both hosts;
retained or separately accepted bridge is explicit; rollback and preservation
pass; current guide matches the selection. No ordinary session restart is needed.

## Completion and following work

The integration is complete when Observer supplies its explicit native profile,
read wiring/conformance and immutable/native gates pass, and its separately
selected reader is operationally accepted. Core/service remain optional-Mesh-free;
API 2/read 4/Service 2 and existing discovery/monitoring evidence are preserved.

Moving the cached native publisher into Observer is an independently scheduled
following checkpoint. It would need after-nonce cached Service 2 reads, guarded
publication, original receipts and owned iterator cleanup; Mesh still hosts its
transport. It is not a prerequisite for SDK profile ownership. Broker services,
event replay, notification normalization, refresh/actions, attachment, arbitrary
new profiles/providers and downstream UI/device migration are outside this pass.

No production implementation or managed selection is authorized merely by this
planning document. The next execution request can target M0–M4, with M5 requiring
the concrete accepted package and coordinated selection inputs.
