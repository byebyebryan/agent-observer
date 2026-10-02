# Agent Observer

Shared host-side discovery and state observation for Codex and Claude Code
sessions. Agent Observer gives consumers a consistent view of session identity,
runtime state, and observation freshness while preserving native workflows.

The initial consumer projects are
[ESP32 RLCD](https://github.com/byebyebryan/esp32-rlcd) and
[Agent Plus](https://github.com/byebyebryan/rofi-agent-plus).
[WSNav](https://github.com/byebyebryan/wsnav) contributes historical lifecycle
work and may become a consumer later; it is currently inactive and may be
simplified.

## Status

The repository contains the source study, spike plan, architecture boundaries,
a documentation check, and a
[Starship read-only preflight report](docs/evidence/2026-10-02-p1-starship/REPORT.md).
Installed Codex capabilities and bounded host topology have been inspected;
native passivity/isolation proof, Claude preflight on Snap, adapters,
live transitions and consumer integration remain pending.

The active checkpoint is **P1: capability and topology preflight**.
See [the roadmap](docs/roadmap.md). Implementation language, the public schema,
and any background collector will be chosen from the proof results.

Continue execution on Snap at `~/code/agent-observer`, where the user reports
Claude is available. Read the [Snap handoff](docs/handoff-snap.md) for retained
context, evidence boundaries, open decisions and the first task there.

## Scope

Agent Observer owns provider discovery, bounded metadata, runtime observations,
source/version capability handling, and reconciliation of stale or conflicting
evidence. Its interface should work across consumer languages.

Saved conversations, logical sessions, runtime workers, and attached terminal
clients have separate identities and lifetimes. Session inventory is separate
from live work state; observation health is separate from both. Unsupported
or ambiguous evidence remains explicit.

Consumers own their presentation and actions. RLCD owns dashboard selection
and device transport; Agent Plus owns picker, host routing and terminal actions.
WSNav's current private-tmux and workstream model does not constrain this
component. Resume, launch, focus, approval, interruption and session deletion
are outside the initial observation API.

The first proof covers Codex and Claude Code, including foreground and
daemon/supervisor topologies where they can be isolated. Existing compatibility
opt-outs remain intact on ordinary sessions. OpenCode and multi-host aggregation
are deferred.

## Starting points

- [Session-state source study](docs/agent-session-study.md): origins, inspected
  revisions, current interface candidates, evidence boundaries and open questions.
- [Spike plan](docs/agent-session-spike-plan.md): capability preflight, source
  comparison, native transition proof, identity/recovery checks and decision gates.
- [Architecture boundaries](docs/architecture.md): shared responsibilities and
  proposed snapshot/watch/capability interfaces.
- [Roadmap](docs/roadmap.md): checkpoint status and the next bounded task.

The study and spike plan originated in the RLCD repository on 2026-10-02 and
now live here. Their earlier provider observations are dated evidence;
preflight must establish the actual installed versions and topology.

Agent Observer focuses on current session observations. Related projects
[Agent Bookkeeper](https://github.com/byebyebryan/agent-bookkeeper) and
[Agent Historian](https://github.com/byebyebryan/agent-historian) cover historical
evidence and cross-session continuity.

## Development

From a clone, run:

```sh
./scripts/check
```

The bootstrap check requires Python 3 and Git. It checks repository Markdown
links, whitespace, code fences and Git whitespace errors. It does not invoke
providers, install hooks or start services. Runtime checks will be introduced
with the implementation they validate.

See [AGENTS.md](AGENTS.md) for development boundaries. The project uses the
[MIT license](LICENSE).
