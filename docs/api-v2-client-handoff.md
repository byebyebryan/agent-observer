# API 2 client handoff

Date: 2026-10-11. [Observer a18](evidence/2026-10-11-claude-retirement/REPORT.md)
is the independently accepted Codex-only collector and read artifact on Snap and
Starship. The optional reader uses Mesh a11/SDK 1 with an explicit Observer-owned
profile. Separate a16/Mesh a10 bridges, the shared Mesh CLI and historical
0.4.0a16 writer retain their independently selected artifacts. The retirement
pass removes Claude native collection, SDK/history, hints and service memo.
Claude remains under native session management/Agent View.

API 2/read wire 4/Service 2/Mesh SDK 1 are unchanged. Reserved provider vocabulary
and synthetic supplied data remain valid for pure conformance; Claude native
selection and its old CLI/configuration options are unsupported. No dormant
adapter or compatibility collector remains. This handoff supplies no consumer,
provider-policy, frontend, attachment/action or Mesh-upgrade acceptance.

## Bind to the contract

Use [API 2](api-v2.md), snapshot/watch wire 4 and
[service protocol 2](service-protocol-v2.md). Writer wire 2 is independent of the
pure read facade. The [reader manifest](../artifacts/observer-0.5.0a18.json) identifies the
accepted candidate; provider release numbers are diagnostic provenance, not
support allowlists. Do not carry forward wire-2/wire-3 readers or protocol-1
caches. Reject unsupported input and rebuild the consumer cache from a new view.

Python read clients use `agent_observer.public` for bounded parsing, semantic
validation, exact identity selection and ordering. Service clients use
`service_public` plus `service_client.frames`, or independently implement both
schema and semantic checks. Other-language clients can obtain schemas with
`schema --kind snapshot|watch` and `service schema --kind request|frame`.
Both API descriptors operate without a provider or service. Local Service clients
can use [service_public.ReadCache](read-cache-client.md) for admission and
independent receipt expiry. Consumers still own IO, timers, reconnect, selection
and presentation. Mesh clients use Mesh SDK 1's ReadGuard and reader clock with
one explicit Observer-owned `mesh_profile.AgentProfile` through every read/view
helper. The [Mesh guide](mesh-read-client.md) gives the optional-package/binding
requirements. API 2/read 4/Service 2 and current-state push semantics are unchanged;
this producer checkpoint does not establish a downstream consumer or GUI gate.

The [state-push guide](state-push-design.md) consolidates complete-view baselines,
idle expiry timers, selection and semantic comparison. Its
[installed/native study](evidence/2026-10-09-state-push-refinement/REPORT.md)
revalidates the accepted state stream without changing public versions. Native
occurrence events and Kitty/D-Bus notification integration are deferred; they are
not read-client dependencies.

The [synthetic mixed-provider fixture](../tests/fixtures/contract-v4/claude-interactive.json)
remains useful for parser, identity, partial-coverage, source-isolation and expiry
conformance. Its reserved data does not represent native provider support.
Consumer source/native/deployment acceptance remains separate.

## Required consumer behavior

- Key rows by the complete host/provider/namespace/native-kind/native-ID tuple.
  Codex `threadId` is the exact thread; `sessionTreeRootId` is independent metadata.
- Treat running/parked/unknown as normalized native evidence within declared
  scope and assumptions. Codex's daemon is its authority. Clients do not query provider registries or validate PIDs.
  No tmux, TUI PID, cwd, title, loaded-list absence or completion callback supplies
  client-side runtime authority.
- Handle parked phase null and unknown phase evidence. Blocked reasons are a
  bounded set containing approval, question or both. Default urgency is blocked,
  waiting, working, then unknown/parked, with conversation activity newest first.
- Preserve missing/stale activity clocks. Display age from the event clock and
  current display time; collection, cache delivery and Resume do not change age.
- `hasSavedHistory` differs from runtime and inventory. Hide only confirmed
  children; unknown kinds stay visible unless a separately explicit UI policy
  says otherwise. Query bounds/coverage and stale source errors stay visible.
- Consume one service view for cached pull and push. Warm-up null is not an empty
  roster; gap/resync, silence, lease expiry and incarnation changes require
  conservative invalidation and a fresh guard/view, never native event inference.
- Keep local Git/root/relative-path/project facts separate from logical identity.
  Project keys can group rows across hosts without merging session references.
- Own user intent, terminal/TUI lifetime, tmux/Kitty placement, routing and viewer
  association in the client. Observation supplies no attachment or worker fields.
- Accept unfamiliar valid diagnostic/limitation codes while keeping wire fields,
  versions and state enums strict. Do not depend on an exhaustive coverage claim
  or discard every known row merely because its source coverage is partial.

Partial runtime coverage can briefly retain a disappeared unsaved UUID as stale
unknown with `retained_after_gap`, even when a fresh direct read omits it. A11
retires it at the original runtime lease: 90 seconds on Snap and 60 on Starship
at the selected cadence. Partial samples, history enrichment and heartbeats
cannot slide that deadline. Direct sampled watch uses 60 seconds from collection
start and applies expiry at the next sample. Current rows and positive saved
identities survive, with original conversation age. Clients preserve uncertainty
until replacement/resync and treat omission as observation-memory retirement,
never a native end/parked event or action permission. The
[retention record](runtime-only-retention-follow-up.md) binds the policy and proof.

The normal writer is selected independently and read acceptance grants no new
action capability. Parked never grants automatic resume, stop, approval or
attachment permission. Conversation metadata has a separate lease; native
runtime refresh cannot move its age. Passive Codex refresh hints complement
periodic reconciliation. Push distributes the accepted replacement view, not
every native transition or an alert/event stream.

## Inspect the observation service

Use the selected read CLI for ordinary discovery and monitoring:

```sh
agent-observer api
agent-observer service api
agent-observer service list --host-scope snap
agent-observer service watch --host-scope snap --count 3
agent-observer service watch --host-scope snap --human
agent-observer mesh list
agent-observer mesh watch --human
agent-observer list --host-scope snap --provider codex
```

The managed publisher is already running on each host. Cached pull and push use
the same view at `/run/user/1000/agent-observer/read.sock`. No subscriber starts
the publisher or falls back to direct native collection. For an independent
direct read, invoke `list` or `snapshot` without the `service` prefix. Direct
reads collect metadata anew and can take longer than cached reads.

For explicit artifact checks, use its immutable prefix:

```sh
candidate_prefix=/home/bryan/.local/share/agent-observer/0.5.0a18-06544d27ae62f590-mesh-a11-reader
"$candidate_prefix/bin/agent-observer" api
"$candidate_prefix/bin/agent-observer" list --host-scope snap --provider codex
"$candidate_prefix/bin/agent-observer" snapshot --host-scope snap --provider codex \
  --workspace-config /home/bryan/.config/agent-observer/workspace.json
"$candidate_prefix/bin/agent-observer" watch --host-scope snap --provider codex --count 2
```

Run on the owning host, replacing host scope with `starship` there. A direct read
does not start an unavailable daemon. For cached development, explicitly start
an owned foreground Observer publisher in another terminal:

```sh
"$candidate_prefix/bin/agent-observer-service" serve --host-scope snap \
  --provider codex --socket /run/user/1000/observer-api2-dev/read.sock \
  --workspace-config /home/bryan/.config/agent-observer/workspace.json
"$candidate_prefix/bin/agent-observer" service api
"$candidate_prefix/bin/agent-observer" service list --host-scope snap \
  --socket /run/user/1000/observer-api2-dev/read.sock
"$candidate_prefix/bin/agent-observer" service watch --host-scope snap \
  --socket /run/user/1000/observer-api2-dev/read.sock --count 3
```

The immediate endpoint directory must be canonical, same-user and private;
the publisher creates it if absent. Use the owning UID's runtime path. Stop this
explicit publisher with Ctrl-C; it owns only Observer work. Never pair a protocol-2
client with a historical protocol-1 endpoint. Subscriber reads do not autostart
a service or fall back to direct collection.

## Actions and acceptance boundaries

Actions and attachment are deferred from the completed observation scope. The
normal `agent-observer-write` still selects the historical a16 artifact and is
not this API-2 read handoff. A future action client must select and validate its
own accepted writer tuple; it must not infer writer compatibility from the
reader's version or link.

The separate API-2 writer prepares and revalidates an explicit local TTY handoff with
`effect=none`; only `enter` performs native New/Resume. New identity is pending
until native discovery. Exact Resume validates the requested reference through
native `thread/read` and metadata-only `thread/turns/list`, independently of
listing caps. An explicitly non-ephemeral summary and readable stored history
are required; failed/unsupported reads return `resume_saved_history_unproved`.
Missing activity alone does not reject saved identity. Consumer attachment/runtime
ownership remains external; remote routing belongs to the owning host/client.

The earlier [a4 writer acceptance](evidence/2026-10-08-codex-evidence-repair/REPORT.md)
accepts initialized saved/live Resume, repeated native entry and equal-ID fork
targeting. This observation pass adds no writer capability or selection gate.
Blank runtime-only Resume and distinct thread/tree-root TUI entry
are not accepted; blank runtime-only Resume fails with
`resume_saved_history_unproved` and distinct-ID entry fails with
`session_tree_entry_unproved`. Positive empty-history responses have controlled
coverage; native empty-saved TTY entry remains unaccepted. Offline
Resume is unavailable until an explicit action restores the provider runtime.
Do not convert observed running/parked state into automatic action permission.

Each consumer validates its own parsing/caches, ordering/age, uncertainty, exact
references and action routing against the unchanged candidate, then performs
its own graphical/device/terminal acceptance. A producer defect reopens an
Observer-only checkpoint. Agent Plus and Tmux Plus development remain separate;
there are no downstream repository edits in this handoff. Future terminal
observation/attachment can integrate tmux-observer through the client boundary.
The [retirement report](evidence/2026-10-11-claude-retirement/REPORT.md) records the
current independent artifact/native and scoped Observer operational gates.

An independent read-client pass may now implement schema/semantic validation,
exact-reference selection, age/attention presentation, mixed-provider views and
cached pull/push with gap/resync/lease handling. Use the accepted a18 producer for
current Codex behavior and synthetic fixtures for provider-neutral conformance.
A future provider requires its own native/capability gate. Actual New/Resume/
attach, device presentation and user-facing notifications require separate
contracts/proofs. Keep client work independent of Observer adapter changes.
