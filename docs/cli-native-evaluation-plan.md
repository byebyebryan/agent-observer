# CLI versus native evidence evaluation

Date: 2026-10-05. This pass executes the
[validation workflow](observation-validation-workflow.md) against the selected
Observer artifact. Its deliverable is a bounded comparison report and gap list,
not producer fixes or frontend acceptance.

Execution is complete; the [evaluation report](evidence/2026-10-05-cli-native-evaluation/REPORT.md)
records the exact samples, reference checks, current Codex failure and follow-up
gates. `scripts/evaluate-observation` is the standalone, observation-only
reference tool, not an adapter or a native capability registration.

```sh
python3 -B scripts/evaluate-observation --host-scope snap \
  --provider codex --provider claude --rounds 2 \
  --codex-reference-sha256 f34a4d2301892ae96c90097786bfe5dc269f187b6f69faf42a7b357b8c081e35
```

The explicit digest is only for the independently inspected current daemon
image in this evaluation. An unregistered image otherwise rejects the reference
probe; this study option cannot change production Observer support. Run the
probe on each owning host, selecting only Codex on Starship.

## Sequence and independent reference

1. Recheck source cleanliness, selected CLI/version/schema and exact installed
   provider images on Snap and Starship. Claude is evaluated only on Snap.
2. Bracket an installed public snapshot with native reads. Use a standalone
   reference probe without importing Observer collectors or projections:
   existing Codex Unix WebSocket RPCs and direct Claude registry/job/transcript
   metadata, verified process births and executable images. No native roster
   command, session operation or daemon startup is part of the ordinary check.
3. Compare saved and live membership, exact native IDs, explicit titles, cwd,
   runtime presence, phase, child evidence and native activity clocks. Compare
   state only when the independent before/after facts agree; otherwise report
   an observation race or unsupported predicate. Check installed list filtering,
   ordering, age rendering, doctor and exact-reference show against the captured
   public snapshot without recollecting it.
4. Inspect workspace/Git metadata independently where present. Inventory
   completeness is measured within each native scope. Terminal-client counts
   are supporting topology evidence, never an identity join or missing-session
   count. Preserve missing timestamps and unknown child classification.
5. If ordinary sessions expose a semantic gap, assess whether an isolated native
   case can independently establish it. Establish namespace/store/endpoint and
   cleanup isolation before any test entry. Record unrun cases rather than
   promoting earlier evidence or guessing from an idle status.
6. Document exact artifact/host/version/topology coverage, confirmed matches,
   mismatches, bounded scans, sampling races, unsupported and unrun cases, and
   prioritized follow-ups. Run `./scripts/check`, review and commit the scoped
   validation checkpoint. Any producer repair or frontend work follows separately.

## Acceptance and evidence limits

- Native expected identity/state comes from provider evidence, not another
  Observer result. A transport implementation may use the same native protocol;
  adapter projection and reference comparison remain separate.
- Ordinary-session evaluation is read-only. Controlled state/action transitions
  require separate owned fixtures and independent expected outcomes; they are
  not assumed merely because previous acceptance reports passed.
- Only bounded metadata, counts, comparison outcomes and finite reasons are
  retained in repository evidence. Raw provider RPCs, conversation records,
  credentials, process arguments and terminal captures stay out of reports.
- Fresh aggregate health does not accept unknown phase/readiness, parked state,
  current viewer binding, arbitrary versions, event replay or complete discovery
  beyond the declared runtime/history scope.
