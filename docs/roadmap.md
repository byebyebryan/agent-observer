# Agent Observer roadmap

Date: 2026-10-02. The [spike plan](agent-session-spike-plan.md) defines detailed
procedures and acceptance; this document records checkpoint status.

| Checkpoint | Status | Exit |
| --- | --- | --- |
| B0: repository bootstrap | Complete | Separate repository, migrated study/plan, scope/ownership boundaries and documentation check |
| P1: capability/topology preflight | Starship read-only report complete; native passivity/isolation and Claude preflight on Snap pending | Target runtime versions, effective opt-outs, actual topology, safe observation/isolation procedures and capability table |
| P2: minimal source comparison | Planned | Study-only adapters and bounded JSON compared with observed native sessions |
| P3: transition proof | Planned | Working/settled, approvals/denials, blocking input, cancellation and observation failure outcomes per topology |
| P4: identity/recovery proof | Planned | Concurrent sessions, native switches, restart/gap recovery and applicable client/worker lifetime cases |
| P5: source and interface decision | Planned | Chosen adapter paths, explicit gaps/configuration requirements, proposed contract and measured overhead |

## Next task

Continue P1 on Snap for both Codex and Claude. The user chose Snap as the work
host because Claude is available only there. Start with the
[Snap handoff](handoff-snap.md) and fresh host inspection.

Use the [Starship preflight report](evidence/2026-10-02-p1-starship/REPORT.md)
and [capability evidence](evidence/2026-10-02-p1-starship/capabilities.json)
as dated Starship evidence. Codex 0.160.0 installed capabilities and terminal
process topology were inspected; native work state and managed-daemon behavior
were not tested. The user identifies Snap as the sole Claude host; inspect its
executable/version and effective agent-view opt-out there. Close native
observation side-effect and isolation gates before invoking a command that may
start a supervisor or launch an experiment. Reinspect Codex on Snap as well;
Starship results do not establish its version, settings or topology there.

Previous local/static observations are recorded in the
[study](agent-session-study.md). Neither the study nor the new static/host
report satisfies native live coverage or establishes unchanged state on a
later run or another host.

## Later adoption

RLCD and Agent Plus are the active consumer targets. Check the proposed
contract against RLCD's live roster and Agent Plus's inventory/identity needs
before stabilizing it. Integrate consumers incrementally after the source
proof; migration and production deployment are not spike acceptance gates.
WSNav is an optional future consumer and may use a simpler architecture.
