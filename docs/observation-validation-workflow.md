# Observer CLI validation workflow

Date: 2026-10-09. This is the current Observer development workflow. Validate
the public CLI against independent native evidence before starting a separate
frontend checkpoint. Ordinary active sessions establish operational inventory;
isolated test sessions establish controlled transitions and failure behavior.
Both forms of evidence are useful, but their coverage differs.

[API 2](api-v2.md), snapshot/watch wire 4 and service protocol 2 are the current
prerelease read contracts. The [a9 Claude report](evidence/2026-10-08-claude-interactive-observer/REPORT.md)
records independent artifact/native and scoped operational acceptance on Snap,
with Codex preserved on Snap/Starship. Read/service commands select a9; the writer
retains a16 independently. A later receipt must record the selected artifact anew.
The [interactive Claude plan](claude-interactive-observation-plan.md) accepts
I0–I4 and retains an independent native oracle. Existing a8 receipts keep their
historical bounds; a9 adds Observer-native on/off and lifecycle proof.
The [native-source proof](evidence/2026-10-08-claude-interactive-source/REPORT.md)
establishes tested positive on/off flows and disproves exhaustive registration.
Validate the user's accepted registration assumption explicitly: normal/crash
parked and cold start within scope, detected faults as unknown, and a live missing
registration as a documented possible false parked result with partial coverage.
The [wrap-up review](evidence/2026-10-09-claude-wrap-up/REPORT.md) records ordinary
active/history comparison bounds. Background execution remains unsupported and
old background histories are outside the user's forward workflow.

## Installed CLI and ordinary sessions

1. Record the selected Observer artifact, schema, host, provider version and
   runtime topology. Run the installed entrypoint outside the source checkout;
   checkout tests do not establish installed behavior. Check Codex independently
   on Snap and Starship. Record versions/hashes as provenance and incarnation
   guards, not support allowlists. Validate another provider only after its own
   adapter gate establishes a passive reference and supported semantics.
2. Collect direct public `snapshot`, `list` and `doctor` results with explicit
   host and provider selection. Also inspect installed `service snapshot`,
   `service list` and bounded `service watch` against the explicit existing
   socket. Record sample/emission times, source leases, saved/runtime coverage
   and aggregate health. The normal list excludes proved children and retains
   unknown kinds. Cached reads/subscribers must not start a publisher or silently
   fall back to direct collection.
3. Obtain an independent native inventory and state sample. Read provider-owned
   IDs, clocks and state metadata directly, rather than treating another
   Observer command or its normalized collector as the reference. Use existing
   passive Codex RPCs on the verified owning endpoint: `thread/list` with explicit
   source kinds/database-only scope, `thread/loaded/list`, metadata-only
   `thread/read` and `thread/turns/list` excluding items. Preserve each returned
   thread's native status, including catalog/detail status outside loaded
   membership. Authenticate the source's UID, namespace and daemon incarnation;
   endpoint process identity does not determine any session's runtime or phase.
   For Claude, read authenticated provider-owned registrations/status and bounded
   saved metadata independently. Native PID-domain/birth checks authenticate UUID
   records; they do not discover terminal clients. Independently validate the
   adapter's reviewed parked predicate and declared assumptions. For the accepted
   interactive Claude target, positively saved UUIDs with a healthy bounded scan,
   no matching live incarnation and no relevant unresolved conflict may become
   parked under the accepted registration assumption. Missing registration alone
   is not a universal absence proof; retain the invisible-live-runtime limitation.
   A native command that can write metadata, adopt workers or auto-start a daemon
   is not an ordinary read probe. The standalone stdlib
   [evaluation harness](../scripts/evaluate-observation) imports no Observer
   collector and records bracketing native comparisons.
4. Compare exact host/provider/store/native references, titles, child
   classification, runtime presence, work phase, conversation activity and
   working-directory/Git metadata where supported. Age is derived from native
   conversation activity at the sample time; creation and file mtime are not
   substitutes. Matching labels, cwd or process counts do not prove identities.
5. Bound the comparison with timestamps and, when a row changes, a second
   sample. Separate a demonstrated mismatch from a native transition between
   reads, missing evidence or an unsupported topology. Report confirmed rows,
   missing/extra rows, conflicts and unresolved classifications separately.
6. For push, validate sequence/incarnation/clock binding and leases. Compare full
   view/resync snapshots with independent native samples. A heartbeat establishes
   transport liveness only. A gap requires conservative invalidation until a
   full resync; healthy readers may receive coalescing gaps. If a bounded frame
   count stops on a gap, extend the probe through resync before accepting recovery.
   Current-view agreement does not establish lossless transitions or alerts.

For example, these selected commands are passive reads:

```sh
cd /tmp
/home/bryan/.local/bin/agent-observer --version
/home/bryan/.local/bin/agent-observer snapshot --host-scope snap --provider codex
/home/bryan/.local/bin/agent-observer list --host-scope snap --provider codex --json
/home/bryan/.local/bin/agent-observer doctor --host-scope snap --provider codex
/home/bryan/.local/bin/agent-observer service snapshot --host-scope snap --socket /run/user/1000/agent-observer/read.sock
/home/bryan/.local/bin/agent-observer service watch --host-scope snap --count 8
ssh starship 'cd /tmp && /home/bryan/.local/bin/agent-observer list --host-scope starship --provider codex --json'
```

Codex's runtime authority is the owning daemon's status across discovered threads.
`idle` means running/waiting, `active` means running with a supported phase or
explicitly unknown phase, and `systemError` preserves running while phase is
unknown. Current `notLoaded` plus a positively readable saved identity means
parked with phase null. Neither loaded-list absence nor terminal exit proves
parked. Compare exact thread identity separately from session-tree-root metadata.
TUI, tmux, window and process censuses are outside observation acceptance;
attachment/context matching belongs to a separate client layer.

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
held approval/question, completed-turn waiting, children, positive parked discovery,
conversation age preservation, missing metadata or owned-runtime recovery.
New native variants/topologies remain unknown/unsupported until independently
proved. Physical sleep/wake and post-TUI-closure lifetime remain deferred.

Test the separate write client only when its behavior is in scope. New/Resume
acceptance must independently verify the provider effect and exact resulting or
requested identity; successful observation alone does not accept the action.
The [a5 native state/recovery report](evidence/2026-10-08-codex-observation-completion/REPORT.md)
and [a6 successor comparisons](evidence/2026-10-08-codex-observation-gaps/REPORT.md)
retain their own bounds. Neither replaces a fresh ordinary check or accepts a
future artifact automatically.

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

## Historical observations from the 2026-10-05 ordinary check

These belonged to the earlier contract/provider selections. They are retained
as historical evidence, not current adapter acceptance or open Codex runtime
predicates. Use the current contract and a fresh independent comparison above.

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
