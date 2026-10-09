# State publication and native event design research

Date: 2026-10-09. Authorized analysis/research/spike/validation goal. This pass
locks down a reviewed design and an implementation gate, not a new production
event API, hook installation, alert client or managed selection.

## Intent and requirements authority

Observer supplies two distinct read products: the current discovery/monitoring
view and bounded evidence of native events. The existing API 2/read wire 4/local
Service 2 remains the accepted state product. Native refresh hints schedule
authoritative reads; they are not session state or completion authority.

The ESP32-349 [handoff](notification-handoff.md) is one client's request. Its
sender/title/body, Kitty-only routing, unfocused delivery, child suppression and
Open behavior must not become universal Observer semantics. Other clients may
need complete child-event evidence, different formatting or different delivery.
The notification panel remains a generic desktop-notification consumer under
that request. Event normalization belongs to passive observation; alert policy
and attachment/actions remain separate clients. Networking moves to the user's
separate mesh-plus repository/thread.

## Research sequence and acceptance

1. Audit current core/service/CLI and experimental notification source/client.
   Identify semantic and policy coupling without changing accepted behavior.
2. Compare current official provider documentation and installed native schemas.
   Record CLI and daemon artifacts separately; versions are proof provenance,
   not support allowlists. Documentation is not installed runtime proof.
3. Use existing native-isolation ownership/masking before all native launch.
   Prove Codex passive-listener versus completion-callback coverage on Snap and
   Starship. Prove Claude interactive callback identity, Stop continuation and
   attention on Snap. Retain scalar metadata only; discard terminal and payload
   contents. Unsupported/unobserved cases remain explicit.
4. Run an independent study model against replay bounds, cursor fencing,
   duplicate correlation, sparse consumer selection, snapshot/event ordering,
   source gaps and restart. This is synthetic design feasibility, not acceptance
   of an unimplemented publisher or a guarantee of lossless native input.
5. Review a concrete product/ownership/event/source/delivery design against CLI,
   Agent Plus, RLCD, 349 requests and future clients. Capture counterexamples and
   corrections. Freeze an implementation/acceptance sequence with independent
   producer/native and delivery/client gates.
6. Check documentation, source regressions and proof cleanup. Leave ordinary
   providers, services, configurations, installed artifacts and sibling repos
   unchanged. No production deployment or network/frontend implementation.

The design must distinguish Observer delivery loss from unobservable native
input loss; a state resync cannot backfill missed completion events. Stable
native correlation and receipt identity have different duplicate semantics.
No mandatory hook source may become a requirement for current discovery or
monitoring. No provider read may subscribe through resume/load or take action.

## Baseline

Source starts at 43b8d3e, clean, with normal read/service a11 selected. Snap CLI
preflight reports Codex 0.161.0 and Claude 2.1.294. Snap and Starship cached
Codex daemon images report 0.162.1; running owner provenance is checked
independently. Provider source proofs, design model and unchanged state-product
validation will be recorded under the focused evidence directory.

## Results

Completed: the [design](state-and-events-design.md),
[deep review](state-and-events-design-review.md),
[native/model/ordinary evidence](evidence/2026-10-09-state-and-events-design/REPORT.md)
and [implementation gates](state-and-events-execution-plan.md) settle the
two-product and ownership design. Codex source proofs ran independently on both
hosts; Claude permission/Stop continuation/child facts ran on Snap. A 50,000-step
model exercised bounded replay and counterexamples. Ordinary installed/native
checks retain accepted metadata limits. Owned namespaces/auth were cleaned.

Production event schemas, sources, service replay and event CLI remain following
work. No new event API, hook selection, alert client, provider policy, mesh or
frontend deployment is accepted by this research checkpoint.
