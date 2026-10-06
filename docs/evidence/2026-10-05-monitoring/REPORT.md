# Monitoring checkpoint

Date: 2026-10-05. Status: source and final immutable a10 package accepted within
the subset below. The [execution plan](../../monitoring-execution.md) preserves the
Observer/frontend separation. Selected Observer remains a9.

## Independent native source evidence

[Bounded metadata](native-source.json) records private user/mount/PID namespace
proofs with ordinary provider paths masked and terminal output discarded.
Codex CLI 0.160.0 drives the exact 0.160.1 managed image. Claude is the exact
2.1.289 installed image. No ordinary provider action or hook installation occurs.

Codex latest metadata-only turns prove in-progress, completed and interrupted
results. A separate ordinary read confirms the previously observed failed turn
under systemError, without reading turn items. Source projection keeps outcome
independent from phase and clears a past outcome on new work.
An additional [native question proof](codex-question.json) holds Plan mode
waitingOnUserInput across three samples on Snap. An earlier question attempt
overlapped an owned daemon recovery and establishes no question semantics;
only the sequential rerun accepts the exact 0.160.1 question flag.

Claude foreground first prompt and completed turns are idle; held work and a
Stop-hook continuation stay busy; held AskUserQuestion is waiting/input needed.
The question has an independent tool request event and remains held after viewer
exit in the background case. A foreground background-child proof samples 216
observations, including root Stop with running background tasks; none is idle
while that running-child evidence remains current. Those exact-image registry
predicates accept foreground readiness. The packaged gate rejected foreground
blocked/unknown reason, correctly enforcing the existing v2 semantic invariant.
Static inspection establishes that input needed is shared with other dialogs;
the source preserves foreground question phase as unknown. Linked background
job block/questions structure with working/blocked state accepts question reason
without reading or exporting question text. A future foreground question source
needs independently bound event facts or another explicit native discriminator.

Background proof demonstrates retained done state during later work and a held
question. It also observes 44 idle samples with queued work. Current-image work
and input-wait registry predicates take precedence over older terminal state;
background readiness requires latest terminal metadata and all three explicit
in-flight counters at zero. Missing/invalid counters and blank background
readiness remain unknown. Surviving 2.1.287 workers retain older accepted limits.

The ordinary history census has 33 top-level candidate files, 31 UUIDs and 30
projected conversations: two resolved companion duplicates, one SDK omission,
zero unresolved identities and zero display exclusions. This explains coverage
without inventing a session from a filename. Counts are sampled diagnostics;
whole-store coverage remains partial.

The first private Claude attempt failed authentication and establishes no work
semantics. A refreshed private credential copy allowed the accepted rerun;
the proof did not write ordinary credentials. Their guard hash changed during
concurrent ordinary use and was not restored; the private namespace masks ordinary
provider paths. An initial shell-only
predicate also failed: foreground tool work uses busy on this image. Neither
attempt is promoted to acceptance. Hook facts are disposable reference evidence,
not an installed production source.

## Final packaged acceptance

The [manifest](../../../artifacts/observer-0.2.0a10.json) freezes version
`0.2.0a10`, source `66f8eb12c000a9e4c77e6837e4100e8456d8af98`, and wheel SHA-256
`7b6129af6ddbec0d23ef2241536355e9a86134d3ebdfe6a6fe58d43cc9f55a7b`.
The same archived wheel and verified entrypoints are installed on both hosts at
`~/.local/share/agent-observer/0.2.0a10-7b6129af6ddbec0d`.
Snap uses the source-only Claude history SDK 0.2.163 profile; Starship uses core.
Snapshot/watch v2 and write v1 remain unchanged. Only this final tuple is accepted;
intermediate package proofs do not establish acceptance of other bytes.

[Bounded package metadata](package-acceptance.json) records two outside-checkout
CLI/native comparison rounds per host, using the independent evaluator without
Observer imports. Snap has 51 Codex and 30 Claude rows; Starship has 96 Codex rows.
There are no missing identities or mismatches in independently proved fields.
Default list excludes three and six proved children respectively. Age, attention
and activity ordering, include-children inventory, exact-reference show, doctor,
host/store identity and current source health pass. Counts are sampled inventories.
Unknown saved runtime/phase/kind and unavailable title/outcome facts remain
unproved; this comparison does not establish every field for every row.

Snap verifies six loaded Codex contexts (three users and three children) and six
Claude workers. Starship verifies eight loaded contexts (two users and six children).
The failed Codex child has an explicit failed outcome and unknown runtime-error
phase. Two surviving older Claude idle workers retain unknown phase. These are
reported limits rather than hidden or reclassified sessions.

Final installed public clients pass isolated Codex New/Resume on both hosts and
Claude New/Resume on Snap, including repeated entry, exact identity, conversation
activity and age preservation through reads/rename/resume. Codex Plan mode holds
blocked/question across three native samples on each host. Claude held approval
and typed background question pass; the question is sampled through the final
public CLI. Isolated Codex daemon failure preserves independent saved discovery;
offline Resume remains explicitly unsupported, New restores the owned runtime,
and exact saved Resume then succeeds without changing conversation age.

Three watch frames and the frozen a3 consumer reader pass. That reader accepts
all 81 Snap and 96 Starship snapshot rows. This validates read compatibility;
it does not accept Agent Plus graphical or action behavior. The optional
`doctor --history-census` reports the bounded 33-file/31-UUID/30-session census
without adding snapshot fields or claiming complete history.

Both owned native namespaces are stopped, and their borrowed credentials and
provider history are removed. Ordinary configurations, hooks and provider
binaries are preserved. Normal Observer entrypoints still select a9 on both hosts;
no frontend source, ordinary provider restart, hook installation or public release
belongs to this checkpoint. Source checks pass 203 tests and the required
documentation/link validation; scoped Ruff checks pass.

To inspect the accepted candidate on Snap without changing normal entrypoints:

```sh
observer_candidate="$HOME/.local/share/agent-observer/0.2.0a10-7b6129af6ddbec0d/bin/agent-observer"
"$observer_candidate" list --host-scope snap
"$observer_candidate" doctor --host-scope snap --provider claude --history-census
```

## Remaining gates

Foreground Claude questions still lack a concrete passive blocked-reason source.
Older Claude workers retain their earlier readiness limits; blank background
readiness, pending-work ambiguities and untyped native blocked jobs remain unknown.
Claude failure/cancellation outcomes and older Codex questions remain unproved.
One Starship saved turn lacks independently proved outcome metadata. History
coverage remains partial, with one SDK omission rather than a proved invalid
session. Older TUI binding/cutover, recorded versus recent cwd, event-source
installation, physical/graphical acceptance, candidate selection and consumer
implementation remain separate work.
