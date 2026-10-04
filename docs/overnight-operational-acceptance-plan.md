# Overnight operational acceptance and scoped rollout

Date: 2026-10-04. Planning pass; no installation selection or provider action
has been performed. The user selected **finish operational acceptance and scoped
rollout** as the next batch's priority. This plan is ready for a subsequent
regular goal loop, with the primary working directly.

The [handoff](contract-clients-handoff.md) and
[execution record](contract-clients-execution-status.md) establish the completed
Observer-first implementation and separate Plus integration. This batch closes
operational gaps around the accepted tuple. New monitoring features, optional
networking, RLCD/349 and Kitty product development remain separate tracks.

## Verified starting point

- Observer checkout: clean `main`, local HEAD `74f56d0`, nine commits ahead of
  the locally recorded upstream. Source artifact `222c5bf`, `0.2.0a3`, 153 tests.
- Plus checkout: clean `main`, local HEAD `59eb4f8`, three commits ahead of the
  locally recorded upstream. Source artifact `90e5b4f`, `0.14.0a1`, 309 tests.
- Both accepted wheels are installed unselected on Snap and Starship, with exact
  hashes/prefixes in the handoff. Nothing has been pushed or published.
- Fresh reads on both hosts still select Observer `0.1.0a5-b68ebf4cefbd8b58`
  and Plus `0.13.0a3-76f8a951e2975283`; neither has a global write-client entry.
- Installed Codex remains 0.160.0 with its accepted executable hash on both
  hosts. Snap Claude remains 2.1.287 with its accepted hash.
- Chezmoi is clean and one commit ahead of locally recorded upstream. Tmux Plus
  is clean and synchronized with its locally recorded upstream. Preserve those
  existing commits and all later unrelated drift.
- The current coordinator has neither DISPLAY nor WAYLAND_DISPLAY. Graphical
  acceptance cannot be claimed from this execution environment.

The original independent native checks passed public CLI/provider entry under
owned PTYs. Plus E8 used controlled Tmux responses and controlled Mesh authority.
Its real SSH read used an explicit candidate executable override. Those successes
do not yet prove the complete installed Tmux/SSH entry path or normal launchers.

## Batch order and acceptance

| Package | Work | Required result |
| --- | --- | --- |
| O0: recheck and ownership | Refresh target versions, wheel hashes, dependency profiles, routing, managed source/live drift and current coordinator identity; establish disposable endpoints and exact cleanup ownership | Known compatible tuple and preserved ordinary runtime; changed/unaccepted provider artifacts stop affected native cases |
| O1: independent operational tooling | Add reproducible artifact manifests, install/verify commands and repeatable Observer checks; measure bounded native read/watch recovery and concurrent-reader cost | Fresh install outside checkouts; complete read/write entries, core-only and source-built SDK profiles, bounded resource/latency evidence |
| O2: actual consumer path | Exercise installed Plus with actual Host Mesh reads, real SSH and real Tmux lifecycle, owned terminal attachments and private provider stores | Codex New/Resume locally and across Snap/Starship, Claude New/live/saved Resume on Snap, exact identity/effect preservation and actual deferred entry |
| O3: managed candidate preparation | Prepare a compatible Snap/Starship selection patch and update candidate/live gates for Observer v2, cache v7 and the pinned public library | Rendered paths, exact artifact checks, clean-source provenance and runnable rollback reviewed before apply |
| O4: scoped provisional pilot | Apply only the compatible managed entry/config paths on the two accepted hosts after O1-O3 pass; verify selected passive commands and headless callbacks | New tuple selected and ordinary workflows available for morning testing; automated pass recorded separately from desktop acceptance |
| O5: recovery and handoff | Validate retained facts, bounded SSH loss and disposable provider restart; clean owned stores/clients; commit scoped changes and record selection/rollback state | No uncertain write retry, no ordinary provider interruption, exact final source/artifact/selected status and short morning checklist |

O1 accepts Observer independently before O2 consumer work. Keep the accepted
public contract and producer code frozen while validating consumer/managed
selection. If a producer defect appears, record it, repair and accept a new
Observer checkpoint/artifact independently, then update the Plus dependency and
consumer corpus. Do not modify both sides together merely to make a test pass.

## O1: reproducible installation and independent operational checks

The durable tuple manifest records package source/version/wheel hash, installed
prefix, read/write entry names, schema versions, dependency profile and accepted
provider executable fingerprints. Installation verifies the supplied artifacts
before creating an owned prefix; it does not start a daemon or select global links.
An existing mismatched prefix is rejected rather than overwritten.

Use a verified local wheel input so fresh installation and development are
possible without publication. Codex-only/core installs have no Claude SDK.
Snap's optional SDK is source-built without a bundled native executable; its
dependency profile and helper passivity remain independently checked. Prepare
Observer CI and Plus's exact-artifact CI/bootstrap inputs. Public availability
of the pinned Observer prerelease is still a publication gate, and hosted CI
success cannot be claimed until it actually runs.

Repeatable validation should become repository-owned tooling rather than rely
on surviving `/tmp` scripts. Keep fixtures and reports metadata-only, and keep
credentials, private histories and native terminal output outside repository
evidence. Tooling distinguishes pure public fixtures, controlled failures,
installed passive reads and native action proofs.

For read/watch, measure a bounded single-reader and concurrent-reader window:
collection duration, sample spacing, timeout/coverage counts, RSS/FD growth and
revision/gap/resync behavior. Check that liveness samples preserve older phase
clocks and no missing row becomes parked or deleted through partial coverage.
Restart or remove only an owned disposable daemon/source to test recovery.
Do not introduce a shared service, change polling promises or add hooks merely
to improve a benchmark. A measured limitation remains an explicit result.

## O2: full Tmux/SSH path without a graphical acceptance claim

Use the existing installed public Host Mesh/Tmux interfaces. Freeze their exact
provenance and preserve existing route hints/history. Native tests run against
owned private stores/endpoints, never ordinary saved conversations or the current
coordinator. Host authority remains caller-supplied, not inferred from hostname.

Actual Tmux creates a private deferred viewer session containing only the public
write-client handoff. An owned terminal/PTY adapter attaches to that real session
and releases its gate. It must not fabricate Tmux responses or provider success.
Report the terminal adapter explicitly: this closes real Tmux/deferred execution,
not Kitty/Niri appearance, focus or trust-dialog UX.

For cross-host cases, establish isolation on the owning host before any possible
provider launch. Use the actual configured route and SSH transport with a
test-owned entry environment. If an isolation wrapper or candidate PATH override
is necessary, record it and keep ordinary-route selection acceptance separate.
Do not loosen isolation or use an ordinary session to make a case pass. If a
required route cannot be proved safely, leave selection pending and continue
the independent tooling/preparation work.

Cover viewer exit while native work remains, exact Resume, saved Claude history,
replaced/expired handoff, failed terminal entry and loss after a possible write.
Preparation may choose a read route; execution pins it and never redispatches
after uncertainty. Preserve confirmed provider work after presentation failure.
Retain requested and resulting identity separately when Claude copies history.
Current-client conversation binding remains unsupported; no focus, session-specific
Close or batch authority is added from historical launch labels.

## O3-O4: managed selection and rollback

Five managed entrypoints must move together on Snap and Starship:

1. `~/.local/bin/agent-observer`
2. New `~/.local/bin/agent-observer-write`
3. `~/.local/bin/rofi-agent-plus`
4. `~/.local/bin/rofi-agent-plus-rofi`
5. `~/.config/rofi/scripts/agent-plus`

The fifth path is independently pinned in chezmoi and still names the old Plus
prefix. Updating only the command links would leave some launch paths old.
Constrain new selections to the target hosts and preserve other host branches.
Leave SSH Plus/Tmux Plus binaries and unrelated managed drift unchanged unless
an observed defect requires a separately reviewed producer checkpoint.

The existing suite candidate/live scripts still assume historical Agent Plus
snapshots and provider stages, including OpenCode. Update the affected gates for
the accepted public Observer/v2 wheel tuple and cache v7. Preserve their existing
Host Mesh/Tmux contract, exact-reference cleanup and SSH-history invariants.
Do not relabel a deterministic self-test as installed acceptance. Record the
pure Observer library dependency separately from the CLI-only Rofi suite boundary.

Capture prior managed sources, selected links and relevant private consumer state
before apply. Render and inspect the concrete patch, verify both hosts' candidate
prefixes, then perform a short coordinated selection window. Mixed protocol
versions may briefly fail visibly; do not add a legacy discovery stack. Verify
all five links, wheel/module provenance, read/write schema, remote passive reads,
Plus dependency resolution and bounded diagnostic/Rofi callbacks immediately.

Cache v7 is a deliberate cutover. Preserve prior cache/UI state for rollback;
invalidate only owned versioned observation cache through its normal migration.
Do not delete saved provider history or borrow unrelated user UI state for tests.
Rollback restores the exact old selected tuple and prior consumer state after
fresh ownership checks; the newly added write link is removed only if still
owned and unchanged. Rollback never stops native work or restores provider auth
or settings over live changes. Retain both candidate and old artifact prefixes.

O4 is a provisional pilot selection, eligible only after the automated gates.
It makes the normal entrypoints available for morning review; it does not close
desktop UX, physical suspend, release or coordinator-reopen gates. This planning
turn does not execute the apply. A subsequent goal loop accepting this plan can
include that scoped reversible cutover without another mid-run confirmation.

## O5 and morning acceptance

Exercise bounded real SSH disconnect/reconnect and owned provider-runtime restart
without restarting sshd, changing firewall rules, suspending either host or
interrupting ordinary providers. Recovery must report gaps/uncertainty and regain
fresh authority. A possible write is never automatically repeated. Cleanup owns
only exact disposable clients, stores, server references and borrowed credential
copies; retain no test rows in ordinary history.

Run appropriate source checks before scoped local commits. Record source versus
built, installed, selected and published state per host, including every pending
native case. Prepare release manifests/notes and CI inputs, but public push,
package/release publication and broader fleet rollout remain outside this batch
unless separately authorized.

Morning manual acceptance is a short checklist: open the normal picker, check
pages/selection and both providers' labels, use New/Resume here and across hosts,
verify terminal placement/focus and native trust handling, and perform physical
sleep/wake if desired. The current coordinator stays available throughout;
its deliberate reopen is last and is not an unattended step.

If all unattended gates pass, the morning result is a selected v2 provisional
pilot on both hosts, repeatable installation/acceptance tools, tested real
Tmux/SSH paths, scoped commits and a rollback record. If a mandatory gate fails,
the old pilot stays selected (or is restored), with complete artifacts/preparation
and the exact failed gate recorded. Do not lower acceptance to claim rollout.

Monitoring expansion is a later independent Observer batch: conversation activity,
parked/offline predicates, broader input/questions, foreground Claude readiness,
native events and optional networking. None of these unproved capabilities is
silently included in the operational milestone.
