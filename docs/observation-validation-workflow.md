# Observer CLI validation workflow

Date: 2026-10-05. This is the current Observer development workflow. Validate
the public CLI against independent native evidence before starting a separate
frontend checkpoint. Ordinary active sessions establish operational inventory;
isolated test sessions establish controlled transitions and failure behavior.
Both forms of evidence are useful, but their coverage differs.

## Installed CLI and ordinary sessions

1. Record the selected Observer artifact, schema, host, provider version and
   runtime topology. Run the installed entrypoint outside the source checkout;
   checkout tests do not establish installed behavior. Check Codex independently
   on Snap and Starship, and Claude on Snap.
2. Collect public `snapshot`, `list` and `doctor` results with explicit host and
   provider selection. Record sample times and saved/runtime coverage as well as
   aggregate health. The normal list excludes proved children and retains rows
   whose classification is unknown.
3. Obtain an independent native inventory and state sample. Read provider-owned
   IDs, clocks and state metadata directly, rather than treating another
   Observer command or its normalized collector as the reference. Use existing
   passive Codex RPCs on the verified owning endpoint and Claude's native
   registry/job/history metadata. Verify worker birth and executable identity
   where required. A native command that can adopt workers, write metadata or
   auto-start a daemon is not an ordinary read probe.
4. Compare exact host/provider/store/native references, titles, child
   classification, runtime presence, work phase, conversation activity and
   working-directory/Git metadata where supported. Age is derived from native
   conversation activity at the sample time; creation and file mtime are not
   substitutes. Matching labels, cwd or process counts do not prove identities.
5. Bound the comparison with timestamps and, when a row changes, a second
   sample. Separate a demonstrated mismatch from a native transition between
   reads, missing evidence or an unsupported topology. Report confirmed rows,
   missing/extra rows, conflicts and unresolved classifications separately.

For example, these selected commands are passive reads:

```sh
cd /tmp
/home/bryan/.local/bin/agent-observer --version
/home/bryan/.local/bin/agent-observer snapshot --host-scope snap
/home/bryan/.local/bin/agent-observer list --host-scope snap --json
/home/bryan/.local/bin/agent-observer doctor --host-scope snap
ssh starship 'cd /tmp && /home/bryan/.local/bin/agent-observer list --host-scope starship --provider codex --json'
```

Codex's accepted runtime inventory covers loaded daemon threads. Terminal
clients, subagents and daemon processes are different units; their counts need
not match. Process metadata can reveal an unobserved topology, but cannot bind
a TUI to its current thread. Claude worker identity likewise requires native
session metadata and verified birth, not a PID or title alone.

Fresh source health means a source was observed successfully within its stated
scope. It does not establish all-session coverage, a known phase for every
worker or absence of unsupported sessions.

## Controlled native sessions

Use operator-owned disposable provider stores, workspaces and endpoints when
ordinary sessions cannot independently establish the expected behavior. Prove
isolation and cleanup ownership before native entry, and leave ordinary provider
sessions, hooks and settings intact.

Establish the expected native identity and event independently of the normalized
Observer result, then compare the installed CLI before, during and after the
affected transition. Choose cases appropriate to the change: working,
held approval, completed-turn waiting, children, saved-only discovery,
conversation age preservation, missing metadata or owned-runtime recovery.
Unsupported question/readiness/parked predicates remain explicit until proved.

Test the separate write client only when its behavior is in scope. New/Resume
acceptance must independently verify the provider effect and exact resulting or
requested identity; successful observation alone does not accept the action.
The existing [native acceptance report](evidence/2026-10-05-operational-resilience/REPORT.md)
records bounded controlled cases; it does not replace a current ordinary check.

## Review and delivery

Record bounded metadata, timestamps, finite reasons and comparison outcomes;
retain no conversation bodies, tool payloads, credentials or terminal captures
in repository evidence. An unresolved observation remains unresolved rather
than being normalized to waiting or parked.

For a producer repair, review the scoped change, run `./scripts/check` and
appropriate affected native cases, then commit the accepted checkpoint. Freeze
and independently validate a new installed artifact when production bytes
change. Installation and consumer migration retain their own gates. A
documentation-only clarification does not require provider actions or rebuilding
the unchanged artifact. See [artifact operations](artifact-operations.md) and
the [execution gates](contract-and-clients-execution-plan.md).

## Open observations from the 2026-10-05 ordinary check

- Two Claude background sessions had verified live workers and native registry
  `idle`, while retained jobs reported `working` with tempo `blocked`. The CLI
  preserved unknown phase. Resolve the native semantics through a separate
  controlled proof before accepting an additional phase mapping.
- An older Snap Codex TUI process was outside the confirmed loaded-thread
  inventory. Its current conversation binding and topology remained unproved.
  This does not establish a missing daemon thread or require restarting it.
- A transient Claude runtime row had no saved title or activity clock and was
  absent on a later read. Its top-level/subagent classification remained
  unproved. Codex children were excluded by the normal list; this does not
  establish equivalent Claude child coverage.

These observations are sampled gaps, not accepted new capabilities or fixes.
Agent Plus presentation, routing and graphical acceptance remain a separate
consumer pass.
