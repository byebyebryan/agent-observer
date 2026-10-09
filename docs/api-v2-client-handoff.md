# API 2 client handoff

Date: 2026-10-08. The Codex observation core/read/service are accepted against
[0.5.0a6](evidence/2026-10-08-codex-observation-gaps/REPORT.md) on Snap and
Starship. Normal read CLI links and user services select a6 after independent
installed/native, managed recovery, rollback/reselection and focused reader checks.
The preceding a5 thirty-minute acceptance retains its historical artifact bounds.
The normal writer retains a16. This handoff does not
select a consumer or authorize provider policy, frontend, terminal-runtime or
networking changes.

## Bind to the contract

Use [API 2](api-v2.md), snapshot/watch wire 4 and
[service protocol 2](service-protocol-v2.md). Writer wire 2 is independent of the
pure read facade. The [manifest](../artifacts/observer-0.5.0a6.json) identifies the
accepted candidate; provider release numbers are diagnostic provenance, not
support allowlists. Do not carry forward wire-2/wire-3 readers or protocol-1
caches. Reject unsupported input and rebuild the consumer cache from a new view.

Python read clients use `agent_observer.public` for bounded parsing, semantic
validation, exact identity selection and ordering. Service clients use
`service_public` plus `service_client.frames`, or independently implement both
schema and semantic checks. Other-language clients can obtain schemas with
`schema --kind snapshot|watch` and `service schema --kind request|frame`.
Both API descriptors operate without a provider or service.

## Required consumer behavior

- Key rows by the complete host/provider/namespace/native-kind/native-ID tuple.
  Codex `threadId` is the exact thread; `sessionTreeRootId` is independent metadata.
- Treat running/parked/unknown as daemon facts. No tmux, TUI PID, cwd, title,
  loaded-list absence or completion callback supplies runtime authority.
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

Codex is the sole native adapter in a6. Explicit Claude collection/service/write
selection returns `unsupported_provider`. Reserved Claude schema examples are
contract fixtures, not native acceptance. Claude is the next producer checkpoint.

## Inspect the observation service

Use the selected read CLI for ordinary discovery and monitoring:

```sh
agent-observer api
agent-observer service api
agent-observer service list --host-scope snap
agent-observer service watch --host-scope snap --count 3
```

The managed publisher is already running on each host. Cached pull and push use
the same view at `/run/user/1000/agent-observer/read.sock`. No subscriber starts
the publisher or falls back to direct native collection. For an independent
direct read, invoke `list` or `snapshot` without the `service` prefix. Direct
reads collect metadata anew and can take longer than cached reads.

For explicit artifact checks, use its immutable prefix:

```sh
candidate_prefix=/home/bryan/.local/share/agent-observer/0.5.0a6-9240493982e041c8
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
The [completion report](evidence/2026-10-08-codex-observation-completion/REPORT.md)
records the separate Observer read/service operational gate.
