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

The current installable candidate is `agent-observer 0.1.0a5`, written in Python
with no runtime dependencies. Its host-local JSON
[contract candidate](docs/snapshot-contract.md) separates logical identity,
work, presence, attachment, source health and coverage.

Native isolated proofs on Snap accept Codex 0.160.0 managed-runtime inventories,
working/settled/approval observations, exact saved resume, work after viewer
exit and daemon recovery. Claude Code 2.1.287 accepts direct metadata discovery,
verified workers, background work/completion/approval and work after viewer
exit. General input, interrupted/error transitions and current conversation
binding remain explicitly unsupported. Observer and Agent Plus candidates are
installed on Snap and Starship; ordinary runtime and bounded routed native
action pilots are accepted. Graphical UI, sleep/wake and published release
acceptance remain separate gates.

The [native report](docs/evidence/2026-10-03-native-runtime/REPORT.md),
[execution status](docs/execution-status.md) and
[roadmap](docs/roadmap.md) distinguish those gates from source and fixture tests.
The [reviewed migration plan](docs/native-runtime-migration-plan.md) defines
rollout. The [execution handoff](docs/execution-handoff.md) records the current
coordinator's final deliberate reopen route and remaining checks.

Claude saved history uses the optional pinned `claude-history` extra. The pilot
builds `claude-agent-sdk==0.2.163` from its official source distribution with
`--no-binary=claude-agent-sdk` to avoid the wheel's bundled Claude executable.
The SDK and its Python dependencies belong in Observer's own environment;
Codex-only hosts need no SDK. Observer projects explicit saved titles, UUIDs,
cwd and creation metadata through a bounded passive helper. It does not export
SDK summaries or conversation contents.

## Command candidate

```sh
python -m pip install .
agent-observer snapshot --host-scope snap
agent-observer snapshot --host-scope starship --provider codex
```

Run Observer on the selected host. `--host-scope` is supplied by the consumer's
Host Mesh authority. It does not authenticate a host. Provider configuration
roots can be supplied explicitly. Observation reads existing endpoints/files;
it never starts a missing daemon or invokes a provider action.

## Scope

Agent Observer owns provider discovery, bounded metadata, runtime observations,
source/version capability handling, and reconciliation of stale or conflicting
evidence. Its interface should work across consumer languages.

Agent Plus uses these observations to mesh sessions across providers and hosts.
Provider independence is an architectural requirement. Codex's delivery priority
reflects usage frequency; the completed migration includes strong support for
both Codex and Claude Code.

Saved conversations, logical sessions, runtime workers, and attached terminal
clients have separate identities and lifetimes. Session inventory is separate
from live work state; observation health is separate from both. Unsupported
or ambiguous evidence remains explicit.

Consumers own their presentation and actions. RLCD owns dashboard selection
and device transport; Agent Plus owns picker, host routing and terminal actions.
WSNav's current private-tmux and workstream model does not constrain this
component. Resume, launch, focus, approval, interruption and session deletion
are outside the initial observation API.

Codex is the primary provider: it leads the first complete implementation and
validation across the user's machines. Claude Code is the secondary provider,
with strong support targeted at the user's single work machine. Priority sets
delivery order; both providers require passive observation, exact identity,
reliable recovery and explicit capability limits.

The user's current workflows naturally separate Claude Code for work from
Codex for mostly other activity, with occasional work use. Work context is a
consumer organization concern, separate from provider and host identity.

The proof covers Codex and Claude Code, including foreground and
daemon/supervisor topologies where they can be isolated. Scoped policy changes
apply to fresh launches; existing ordinary sessions remain intact. Codex and Claude Code are the only
providers in the Agent Plus migration. OpenCode integration in Agent Plus is
removed from the migrated candidate; an OpenCode adapter is
outside this migration. Observer multi-host aggregation remains deferred;
Agent Plus uses existing host routing to compose host-local observations.

## Starting points

- [Native runtime migration plan](docs/native-runtime-migration-plan.md):
  accepted product direction, native TUI/action design, implementation ownership,
  delivery dependencies, rollout and acceptance gates.
- [Design review](docs/design-review.md): source/evidence checks, resolved
  planning issues, coverage and remaining proof decisions.
- [Provider runtime and UX study](docs/provider-runtime-ux-study.md): Codex
  daemon and Claude Agent View mode comparisons, everyday workflow changes,
  Agent Plus impact and migration proof requirements.
- [Session-state source study](docs/agent-session-study.md): origins, inspected
  revisions, current interface candidates, evidence boundaries and open questions.
- [Spike plan](docs/agent-session-spike-plan.md): capability preflight, source
  comparison, native transition proof, identity/recovery checks and decision gates.
- [Architecture boundaries](docs/architecture.md): shared responsibilities and
  proposed snapshot/watch/capability interfaces.
- [Consumer fit review](docs/observer-consumer-review.md): Agent Plus routing and
  action boundaries, RLCD model fit and partial-feed handling still to resolve.
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

The check requires Python 3.11 or newer and Git. It checks repository Markdown
links, whitespace, code fences and Git whitespace errors. It does not invoke
providers, install hooks or start services. It also runs the observation invariant, collector and controlled transport tests. These are
synthetic/controlled checks; native runtime acceptance is recorded separately in evidence.

See [AGENTS.md](AGENTS.md) for development boundaries. The project uses the
[MIT license](LICENSE).
