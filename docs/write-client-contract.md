# First-party New/Resume write client

Candidate: `agent-observer-write`, request/plan/result schema version 1. This is
a separate client of the [public observation contract](public-contract-v2.md).
Passive collection/read commands never import this module or perform actions.
It has no Tmux, SSH, Agent Plus or dashboard dependencies.

## Interface and ownership

```sh
agent-observer-write prepare --request request.json
agent-observer-write execute --plan plan.json
agent-observer-write enter --plan handoff.json
agent-observer-write schema --kind request
```

Each input also accepts bounded literal `--request-json` or `--plan-json`.
This lets terminal clients pass a public handoff as one argv element without
creating another file or owning a provider-specific launch command. The literal
uses the same strict parser, guards and execution-time revalidation as files.

Prepare consumes an exact request, checks current local context and returns a
plan without dispatching a provider action. Execute revalidates the plan. Codex
New/Resume and Claude live attach return a prepared TTY handoff with effect none.
Enter requires a native TTY, revalidates again, chdirs and replaces itself with
the native executable. It emits no machine JSON into native TUI output. The
caller owns terminal/window presentation and host routing; the provider owns
its work. No launch association becomes a current conversation binding.

New Here requires no existing row:

```json
{"schemaVersion":1,"operation":"new","hostScope":"snap","provider":"codex","configHome":"/home/bryan/.codex","configHomeKind":"explicit","cwd":"/home/bryan/code/agent-observer","reference":null}
```

Resume uses the same envelope with operation resume and the complete identity
from a current snapshot. Display names, cwd, PID, UUID prefixes and Tmux labels
are never action targets. Host scope is supplied by the caller's route authority;
this client does not attest the local machine. A remote caller must invoke it on
the selected owning host. Request config/cwd must be canonical absolute local
directories; symlinks and changed directory incarnations are rejected.

## Native routes and guards

The accepted executable fingerprints are pinned independently of PATH. Codex
uses `/opt/openai-codex/bin/codex`; Claude uses `/opt/claude-code/bin/claude`.
Preparation binds executable hash/inode/device, UID, cwd/config directory
incarnations, selected settings digest and resume runtime provenance. Execution
checks those facts again. A stale plan, changed artifact/settings, ambiguous
identity, child, unsupported selector or mismatched cwd is a bounded rejection.
Plans contain no credentials or inherited environment; native argv is derived
locally rather than supplied by the caller.

Partial aggregate source coverage does not invalidate a healthy selected target.
Unsupported work/tempo/terminal-clock metadata does not by itself prevent native
entry. Identity, directory, artifact and runtime ambiguity still reject. Claude
live attach additionally requires a current verified worker and a retained job
record linked to its exact full session and native job ID; a registry-only row
whose job metadata is missing cannot use this route. Observation health never
becomes blanket action authority.

Codex native resume uses the separate native sessionId, not an inferred equality
with threadId. New leaves identity pending until native entry creates context.
Native trust/login handling remains in the TUI; this client does not approve it.

Claude live resume requires a verified current background worker and exact short
job ID. Saved resume requires current explicit saved UUID/history evidence or a
terminal retained job with history and no verified running worker. It invokes
the exact full saved UUID once. New/saved resume use closed stdin and native
`--bg`, with the per-launch `worktree.bgIsolation=none` setting. Default Claude
configuration unsets CLAUDE_CONFIG_DIR; explicit isolated roots supply it.
These selectors have distinct provenance and are not silently substituted.

## Results, uncertainty and cancellation

After one verified Claude launch, a transient ambiguous native phase can delay
attach. The client reobserves that exact identity within its existing deadline;
it never launches again. A deadline preserves the confirmed native effect and
resulting identity while reporting unavailable handoff. Artifact, settings and
identity failures retain their ordinary rejection behavior.

Claude 2.1.287 can append a fixed note that an already-backgrounded session was
copied and that an inline attach command opens the original. This is not the
new viewer receipt. The parser validates the fixed note's original/copied job
IDs or UUIDs and consistency with the requested reference and launch receipt.
Short IDs never become full identity: exact post-launch provider metadata must
supply one verified worker/session/job mapping. When a note supplies a full copied
UUID, it must also match that metadata. The parser requires one new background/attach
receipt and rejects conflicting notes or arbitrary embedded attach mentions.

Native background launch output is bounded in memory and never exposed or
persisted. An exact native attach cue selects the resulting job; an independent
public observation resolves its actual full session identity. Claude can copy
saved history, so requestedIdentity and resultingIdentity are separate.

Results distinguish effect none, confirmed and uncertain. Timeout, excess output,
nonzero launch, ambiguous/missing cue or failed post-action observation never
triggers another provider launch. No idempotency or safe retry is promised.
After verified creation, handoff-preparation failure keeps the confirmed effect
and resulting identity while reporting handoff_unavailable. Consumers must
preserve that work and avoid repeating New/Resume creation.

Launcher cleanup stops only the exact owned launcher. It never kills the
process group containing provider-managed descendants. A controlled descendant
test covers that ownership distinction; native lifetime proof remains separate.
TTY exec failure affects presentation and must not cause another background
creation. SIGINT during background launch reports an uncertain effect.

JSON results exit 0 when prepared/ready, 3 for rejected/uncertain launch results;
preflight/shape/context errors exit 2 with finite stderr diagnostics. Schema
files are bundled package data. Independent packaged/native acceptance is
recorded in the [execution record](contract-clients-execution-status.md).
