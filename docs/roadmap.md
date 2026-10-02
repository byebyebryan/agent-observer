# Agent Observer roadmap

Date: 2026-10-02. The [spike plan](agent-session-spike-plan.md) defines detailed
procedures and acceptance; this document records checkpoint status.

| Checkpoint | Status | Exit |
| --- | --- | --- |
| B0: repository bootstrap | Complete | Separate repository, migrated study/plan, scope/ownership boundaries and documentation check |
| P1: capability/topology preflight | Next; not run | Target runtime versions, effective opt-outs, actual topology, safe observation/isolation procedures and capability table |
| P2: minimal source comparison | Planned | Study-only adapters and bounded JSON compared with observed native sessions |
| P3: transition proof | Planned | Working/settled, approvals/denials, blocking input, cancellation and observation failure outcomes per topology |
| P4: identity/recovery proof | Planned | Concurrent sessions, native switches, restart/gap recovery and applicable client/worker lifetime cases |
| P5: source and interface decision | Planned | Chosen adapter paths, explicit gaps/configuration requirements, proposed contract and measured overhead |

## Next task

Begin P1 with fresh read-only inspection on the actual target host. Identify
Claude's executable/version and effective agent-view opt-out, establish Codex's
actual foreground/daemon topology, and check candidate interfaces against those
versions. Determine observation side effects and isolation before invoking a
command that may start a supervisor or launch a live experiment.

Previous local/static observations are recorded in the
[study](agent-session-study.md); they do not satisfy this checkpoint's live
coverage or establish that the target environment has remained unchanged.

## Later adoption

RLCD and Agent Plus are the active consumer targets. Check the proposed
contract against RLCD's live roster and Agent Plus's inventory/identity needs
before stabilizing it. Integrate consumers incrementally after the source
proof; migration and production deployment are not spike acceptance gates.
WSNav is an optional future consumer and may use a simpler architecture.
