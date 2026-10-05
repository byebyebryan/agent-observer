# Independent discovery repair acceptance

Date: 2026-10-04. [Bounded evidence](acceptance.json) and the
[execution plan](../../discovery-repair-execution-plan.md) describe this reopened
Observer checkpoint. Agent Plus implementation is a separate pass.

The exact accepted Observer artifact is `0.2.0a7`, source `0526106`, wheel SHA-256
`1d42506cf2b5cc7c75a3d8df4ee3279493b132d7b87cb8cd79b1f5b360e4ebc2`.
Installed bytes, entrypoints and public schemas pass on Snap with the source-built
Claude SDK `0.2.163` and on Starship with the core-only profile. There is no
bundled Claude executable. 172 source tests and scoped Ruff checks pass.

## Accepted independently of consumers

| Provider and topology | Exact native artifact | Accepted cases |
| --- | --- | --- |
| Codex managed daemon, Snap and Starship | 0.160.0, manifest executable hash | New, exact saved/live Resume, repeated real TTY entry, metadata-only latest-turn activity, unchanged age through reads/rename/housekeeping/resume, private daemon failure visible, public New recovery followed by exact saved Resume, visible TTY guard rejection before provider execution |
| Claude native BG workers, Snap | 2.1.287, manifest executable hash | New, exact typed attach and repeated TTY entry, message-envelope activity, unchanged age through reads/rename/housekeeping/attach, healthy live attach and saved Resume through a fault-injected sibling with missing job metadata, explicit copied UUID and first prompt activity |

Every native action used owned private user/mount/PID namespaces, provider stores,
authentication copies and endpoints. Source reads never launched providers.
Native terminal output and conversation bodies were discarded; repository evidence
contains bounded metadata and reason codes only. The missing-job case is a native
worker fixture with controlled metadata removal, not a claim that Observer
reproduced every possible native registry failure.

The existing snapshot/watch v2 and write v1 schema shapes suffice. They exactly
match the frozen `0.2.0a3` reader dependency inside Agent Plus `0.14.0a1`; no
consumer wheel or frontend implementation is changed by this acceptance.

## Limits and consumer handoff

Native Codex turn timestamps absent in older histories remain unknown; there is
no creation or mtime fallback. The ordinary passive reads found 34/47 Snap and
85/90 Starship Codex clocks, plus 25/25 listed Snap Claude clocks. Counts are one
sample, not a fixed inventory. Claude remains a healthy partial source with
explicit native blocked-phase and duplicate-history capability warnings.

Claude saved Resume creates a new UUID before persisting its copied transcript;
activity remains unknown until native persistence. Its fixed copy note uses job
IDs, so those hints are consistency checks. Exact post-launch metadata supplies
the new full session identity. Unknown work is never promoted to urgency blocked
or waiting. General questions, parked predicates and foreground Claude readiness
retain their previous independent gates.

Codex saved Resume cannot prepare while its history daemon is unavailable. Public
New can restart the native runtime, after which saved Resume works. Offline
discovery/resume support is a separate capability; no legacy storage reader is
added here.

The reported ordinary silent Plus Resume failure remains unlocalized: first-party
installed CLI entry works and its guard failure is visible under a real PTY.
A read-only consumer review found `_create_handoff` uses `resultingIdentity`
for wrapper tags even when prepared Codex Resume/Claude attach correctly leaves
that field null; the full requested reference is available in the handoff. That
presentation/correlation defect needs its own consumer checkpoint and is not
claimed as the cause of the earlier silent failure. Graphical focus and picker
operation remain consumer acceptance gates.

## Delivery

R0–R4 are accepted for the subset above. Scoped producer selection, exact managed
verification and owned native cleanup remain R5 at this checkpoint. Ordinary
provider configuration and native sessions remain outside the deployment scope.
