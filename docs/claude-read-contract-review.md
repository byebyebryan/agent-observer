# Claude alignment with the shared read contract

Date: 2026-10-08. Status: shared read interface settled for this pass. API 2,
snapshot/watch wire 4 and service protocol 2 accommodate the
[accepted interactive Claude design](claude-interactive-observation-plan.md).
No public schema, descriptor, enum or validator changes are required by that
design. The subsequent [a9 execution gate](evidence/2026-10-08-claude-interactive-observer/REPORT.md)
now accepts the adapter and scoped read/service selection on both hosts.
The contract remains prerelease; a future
incompatible interface change still requires a versioned gate.

This review accepts public contract fit and permits independent read-client
development. Its original synthetic checks below remain distinct from the
subsequent I1–I4 producer gates. Agent View settings remain unchanged.

## Findings and resolution

Three documentation issues could mislead a client implementer:

1. The shared discovery table used only Codex's native status names. The service
   text also treated `notLoaded` as the universal parked predicate. Shared row
   meanings are now separate from each adapter's native evidence and assumptions.
2. The earlier plan proposed an `interactive_sessions` scope enum and automatic
   API/wire/service bumps. Existing `provider_sessions`, partial coverage and
   bounded reason/limitation fields represent the agreed scope without that change.
3. At the original alignment checkpoint, the client handoff and service page
   retained a6/a5 selection examples while describing a8 as current. That review
   reconciled them with a8; the subsequent wrap-up updates current guides to a9.

No blocking shared-interface mismatch was found. This conclusion rests on both
semantic review and synthetic conformance through unchanged source and installed
validators; schema acceptance alone would not settle the native predicate.

## Contract fit

| Requirement | Existing representation | Decision |
| --- | --- | --- |
| Stable logical identity | Host/provider/store namespace/native-kind/native-ID; Claude `sessionId`, Codex `threadId` with separate tree-root metadata | Keep; labels/cwd/PIDs do not substitute |
| Running/parked discovery | `runtime` evidence with value, health, source, reason, observed time and clock; `hasSavedHistory` independent | Fits the scoped Claude predicate; no attachment fields |
| Monitoring | Running plus working/blocked/waiting/unknown phase; approval/question reason set | Fits authenticated interactive status; unsupported dialogs preserve unknown phase |
| Inactive phase | Current parked has phase null and no blocked reasons; stale parked becomes runtime/phase unknown with last-known evidence | Keep; no stopped/background enum needed |
| Age and ordering | Native conversation activity with independent health/clock; attention order followed by newest activity | Keep; runtime refresh and delivery cannot advance age |
| Workspace/project | Recorded cwd and bounded root/relative-path/Git metadata | Keep; optional metadata is not identity/runtime authority |
| Interactive-only scope and registration assumption | `provider_sessions`, partial runtime coverage, bounded reasons/limitations | Fits without new fields or enum values |
| Runtime/history independence | Service's existing runtime and history component receipts | Fits; exact saved-identity proof may accompany runtime without renewing catalog/activity |
| Read delivery | Direct snapshot/watch and service snapshot/watch carrying the same wire-4 view | Keep; sampled push, leases and full resync remain required |
| Actions, context matching, meshing and notifications | Separate client/components and gates | Outside this read contract; no new authority implied |

The common contract describes normalized evidence within declared source scope.
Adapters can use different native mechanisms: Codex's owning daemon or Claude's
provider-owned UUID registrations authenticated by incarnation. Clients consume
the common fact and uncertainty; they do not reproduce those mechanisms.

### Claude scope and guarantees

For the interactive successor, retain `coverage.runtime.scope=provider_sessions`,
set runtime coverage partial and use reason `interactive_registration_assumed`.
Declare these source limitations:

- `interactive_runtime_only`: ordinary interactive observation is supported;
  background execution/continuation is outside the runtime target.
- `native_registration_assumed`: negative lifecycle relies on supported ordinary
  sessions registering while running.
- `unregistered_interactive_runtime_unproved`: a live failed/lost registration
  can be omitted or falsely reported parked, including after readable recovery.
- `background_runtime_unsupported`: a minimal native guard prevents known
  unsupported work from becoming parked; no full background lifecycle projection.

Other saved/status limitations remain independent. Partial coverage means the
all-context roster is incomplete; it does not discard independently qualified
row facts. A healthy bounded scan, positive saved UUID and no matching live
incarnation or relevant unresolved conflict can support parked under the
accepted assumption. Detected unreadability, bounds, ambiguity and expiry still
prevent an affected negative assertion. No directory recovery or schema test
proves an exhaustive census.

The native predicate and source capabilities remain adapter implementation
obligations. A validator can check provenance fields, identity relations, current
health, phase consistency and saved-identity presence; it cannot independently
prove that a producer read Claude correctly. Public semantic validation and
independent native acceptance are both required for producer rollout.

### Extension and freshness rules for clients

Wire fields, versions and enums are closed. Valid evidence-source, reason, error
and limitation codes use a bounded open vocabulary. Unknown valid codes remain
diagnostic data; clients do not reject a whole view or reclassify runtime because
they lack a presentation string. A new provider enum or incompatible shared
meaning still requires a versioned interface; provider-neutral does not mean an
unbounded wire schema.

Capabilities are scoped dimensions, not permission or guaranteed exhaustive
membership. Source health, coverage and per-row health are distinct. Saved
identity is separate from full history coverage: an adapter can freshly prove
an exact saved UUID during runtime collection while title/activity enrichment
remains stale. That does not renew the history lease or conversation clock.

Cached pull and push share a published view. Heartbeats only establish transport
liveness. Warming null, a gap, source expiry or silence cannot imply parked.
Readers require the existing clock/lease guards and complete resync. Cross-host
forwarding must preserve source age and host-local clock boundaries through a
separately accepted transport; receipt arrival is not a new event time.

## Conformance evidence

The [synthetic mixed-provider example](../tests/fixtures/contract-v4/claude-interactive.json)
contains a Codex blocked row and Claude running/question, parked/null and
saved/unknown rows. It declares the target limitations and partial coverage.
These are constructed examples, not native observations or deployed behavior.

The eight [alignment tests](../tests/test_claude_contract_alignment.py) exercise:

- Strict snapshot parsing, exact selection, partial scoped parked and the
  existing API/wire/service versions.
- All supported work phases and approval/question combinations.
- Extensible diagnostic codes while rejecting unknown wire fields, scope enums
  and versions; no public worker or attachment data.
- Rejection of parked without saved identity, with non-null phase, blocked
  reasons or stale current evidence.
- Standalone watch and service frame parsing, gap/resync and snapshot equality.
- Runtime expiry rejection and a valid stale unknown/last-known parked form.
- Fresh runtime/saved-identity proof alongside expired history and stale age.
- Provider-independent selection/ordering and saved/unknown presentation.

All eight pass against the checkout's pure facades and, outside the checkout
with isolated Python imports, the unchanged installed a8 artifact:
`0.5.0a8-2d302213b95af76a` (wheel SHA-256
`2d302213b95af76a8e5da888bba1783015eb4770a0cfaade404f7f181cce8b99`).
The installed CLI's explicit `--input` list also accepts the fixture and returns
the three Claude rows with blocked, null and unknown phase respectively.
Descriptors report API 2/wire 4/service 2. These checks invoke no provider or
publisher and make no ordinary configuration changes.

Reproduce that historical a8 consumer check without native collection:

```sh
cd /tmp
candidate_prefix=/home/bryan/.local/share/agent-observer/0.5.0a8-2d302213b95af76a
"$candidate_prefix/bin/python" -I -B \
  /home/bryan/code/agent-observer/tests/test_claude_contract_alignment.py -v
"$candidate_prefix/bin/agent-observer" list --provider claude --json \
  --input /home/bryan/code/agent-observer/tests/fixtures/contract-v4/claude-interactive.json
```

The [native-source report](evidence/2026-10-08-claude-interactive-source/REPORT.md)
separately establishes tested registration/status/exit behavior and its failure
counterexample. This review's a8 conformance checks do not add native proof or
accept a producer successor. The later
[a9 report](evidence/2026-10-08-claude-interactive-observer/REPORT.md) supplies
independent oracle/private-boundary acceptance, runtime-only parked refresh,
duplicate/switch/background-guard native proof, direct/cache/push conformance
and scoped operational selection. I5 provider-policy rollout remains deferred.

## Client readiness and next producer checkpoint

Read clients can now implement parsing/validation, exact identity selection,
mixed-provider presentation, age/attention ordering, unknown/stale/partial display,
and cached pull/push with leases and resync against the settled interface.
Use a9 for current installed behavior and the synthetic example for interface
conformance. Preserve scoped parked facts, missing-registration limitations and
stale unknown retention rather than reinterpreting native mechanisms in clients.

Client source development can proceed independently against the accepted
[handoff](api-v2-client-handoff.md). Selecting a future producer or rolling out a completed client still needs
the relevant artifact/native and consumer acceptance. New/Resume/attach, terminal
matching, network forwarding and completion alerts are not settled by this review.
Producer defects reopen an Observer-only checkpoint, not simultaneous frontend
and adapter edits.

Observer's I1–I4 work is complete within the declared bounds. Provider policy,
consumer implementation/native acceptance, actions/attachment and network
forwarding remain separate. Reopen an Observer-only checkpoint if a consumer
finds a producer defect; reopen the shared wire only for a concrete missing
public guarantee or incompatible semantic change.
