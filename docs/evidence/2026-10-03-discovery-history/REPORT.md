# Discovery and history follow-up acceptance

Date: 2026-10-03 local time. The authorized unattended follow-up is complete
for the bounded source, consumer action and installed pilot gates. Candidates
remain uncommitted and unpublished. No clean history slate or parallel legacy
collector was introduced.

## Installed tuple and checks

| Component | Candidate | Wheel SHA-256 | Installed scope |
| --- | --- | --- | --- |
| Observer | `0.1.0a5` | `b68ebf4cefbd8b58fbfabf32cdbc2c2c3a4017a4c210e00d849cf1b75e99f163` | Snap and Starship; all 13 module hashes match source/wheel |
| Agent Plus | `0.13.0a3` | `76f8a951e29752838e992ffdb36256db32378da136b087e4196e83a9d738bc50` | Snap and Starship; all 21 Python/SVG hashes match source/wheel |

Independent prefixes are recorded in [candidate artifacts](candidate-artifacts.json)
and [installed verification](installed-verification.json). Four managed entry
links per host are now verified: Observer, the two Agent Plus CLI entry points
and the Rofi script callback. Other provider settings, published external
pins and other managed hosts were preserved. The current source gates pass
127 Observer tests and 367 Agent Plus tests, lint, format and package checks.
Host Mesh/Tmux bundle sync also passes.

The optional `claude-agent-sdk==0.2.163` dependency is installed only in Snap's
Observer environment from the official source distribution, SHA-256
`269821ad5acff5967522ff15f444b0598840fd9bdc45c645de569a5478061a53`.
The source-built package has no bundled Claude executable. Starship remains
Codex-only and has no SDK installation. Full-package import/list passivity was
checked independently in Python 3.12.8, then the installed production helper
and action path were exercised in Python 3.14.7. The exact dependency versions
and installed footprint are in the verification record; the earlier package
proof is [full SDK passivity](full-sdk-passivity.json).

## Discovery and identity

[Installed discovery](installed-refresh.json) passes from both origins without
feed errors: Snap has 48 Codex and 31 Claude conversations; Starship has 90
Codex conversations. All 31 Claude rows carry saved metadata, including 26
saved-only rows and five exact UUID merges with native registry/retained-job
observations. Twenty-nine have native titles; unassigned titles retain the UUID
fallback. Explicit creation metadata reaches 2026-07-13 UTC, before runtime
cutover. The existing 40-row display pool includes ten saved-only Claude rows
in this finite sample; the per-host inventory remains separate from that cap.

The official global SDK API selects and deduplicates top-level conversations.
The bounded filesystem census found 34 root files, 32 distinct UUID filenames
and two UUIDs present under more than one project. Those filenames alone are
not duplicate returned identities. Observer preserves the SDK's unique result,
without reconstructing transcripts or choosing metadata from file timestamps.
Nested subagent transcripts are excluded by this SDK API. Healthy saved
coverage remains incomplete with `metadata_scan`; excluded or unreadable
records are not promoted to complete coverage. Summaries, first prompts and
conversation content never enter the observation contract.

Saved-only work and presence remain unknown and unobserved. History failure
uses a separate finite `claude-history` warning in Plus and does not stale a
healthy live row. SDK creation time can order saved rows; file mtime cannot
refresh work, presence or consumer recency. Native cwd spacing is preserved.
An unavailable cwd leaves a visible row with no invented action directory.

Observer now projects confirmed Codex children from explicit native origin
metadata, preserving unknown/conflicting classifications. Plus excludes only
confirmed children from ordinary rows and rejects child/conflicting actions.
[Installed native reads](codex-child-native.json) confirm both `thread_spawn`
and `review` sources classify as children without loading them or changing the
daemon incarnation. Controlled consumer tests establish picker exclusion.
An ordinary loaded-child workflow was not run; it is not claimed as accepted.
Claude's three previously suspicious retained rows were owned earlier migration
proof jobs, not confirmed subagent sessions. Their ordinary history was preserved.

### Reported picker rows and callback correction

After this pass, the operator reported Starship Codex `Run sleep 20` and Snap
Claude `Agent plus Claude entry accepted` as possible child rows. Exact UUIDs
match earlier owned native proofs: Codex
`01a10056-0cb5-7370-9696-9361ad332f2b` in
[the Starship task proof](../2026-10-03-native-runtime/codex-starship-pilot-task-proof.json),
and Claude `ff8a5f7f-891a-406d-88b1-e1f112fa0819` in
[the explicit New proof](../2026-10-03-native-runtime/agent-plus-claude-snap-new.json).
These were top-level test conversations. A current read-only native metadata
check reports Codex origin `vscode` and Claude root transcript
`isSidechain=false`; the finite examples do not demonstrate child-filter failure.
Their history was retained, which explains the picker clutter.

The audit also found a deployment defect: the first install checked the two
Plus CLI links but missed `.config/rofi/scripts/agent-plus`, whose managed
template and installed links still selected `0.13.0a2` on both hosts. That
single template now selects `0.13.0a3`; scoped diff, dry-run, apply and verify
passed on Snap and Starship. All four entry links per host match. Public
discovery through the actual script path passes from both origins with zero
feed errors and zero confirmed child rows; see
[callback follow-up](rofi-callback-follow-up.json). No provider action or history
deletion was performed. This headless check does not establish graphical
rendering or focus acceptance.

### Explicitly requested test-history cleanup

The operator subsequently requested removal of remembered test sessions.
[Cleanup metadata](test-session-cleanup.json) records five exact owned targets:
Codex `Run sleep 20` on Starship and `Run harmless marker command` on Snap;
Claude `Agent plus Claude entry accepted`, `Observer Claude empty pilot complete`
and `claude job runner setup` on Snap. The last Claude job's exact creation
cue was matched to the earlier coordinator action record in memory. Other
isolated proof and unsaved New UUIDs were already absent from ordinary stores.
Titles alone were not deletion criteria.

Fresh complete loaded inventory and ordinary Claude registry reads excluded
the targets before action; their owned job records were terminal and had no
worktree fields. The operator used native Codex `delete --force FULL_UUID`
against each already verified existing daemon. Claude's native `rm SHORT_ID`
removed the stopped jobs but retained their conversations, so the operator
unlinked only their exact prevalidated UUID transcript files and removed their
owned UUID session-environment directories. No project-wide purge was used.
These actions belong to the authorized operator cleanup, not Observer's API.

Both ordinary picker caches were refreshed through the actual Rofi callback.
Each origin now reports 47 Codex and 28 Claude conversations on Snap, and 89
Codex on Starship, with zero errors and zero surviving target identities.
Twenty-six Claude rows retain native titles. Non-target database identities and
root transcripts were preserved, as were both ordinary live Claude registrations,
the preexisting loaded Codex sessions, the coordinator identity and both daemon
PID/birth tuples. Claude settings and Codex config hashes remain equal; all
managed configuration diffs are empty. The native global preferences file
changed during the action interval, so whole-file preference equality is not
claimed. It was not manually edited or restored.

## Native saved Resume acceptance

The isolated operator first created a real named conversation, then closed its
foreground client. [Native history proof](claude-native-history-resume.json)
confirmed full-UUID background resume retaining identity and an explicit fork
changing identity. No ordinary sessions were accessible inside the namespace.

The installed Plus lifecycle used the real public Observer command and the
installed Tmux Plus command in that private namespace. Each action dispatched
`claude --resume FULL_UUID --bg` once with closed stdin. The exact native attach
cue selected a short job ID, and public Observer resolved the actual session.

- [Saved-row Resume](claude-installed-history-resume.json) started from unknown,
  unobserved presence and resumed the same UUID.
- [Retained history Resume](claude-installed-history-copy.json) started from an
  exact terminal retained job with unobserved worker presence. Claude
  automatically created a different UUID; Plus used that actual identity for
  its viewer. This action did not request a forced fork.
- Both proofs opened a real individual attachment client through an explicitly
  owned terminal. The native worker remained present after viewer exit.

Eligibility is explicit: canonical saved metadata, or an exact terminal
retained job with fresh SDK history and no present/ambiguous worker evidence.
Present supervised jobs attach directly. Present foreground, working retained,
conflicting and stale identities cannot dispatch saved Resume. A failed or
uncertain command never retries another route; post-action identity/viewer
failure preserves the provider result and cannot dispatch another resume.

## Preservation and remaining gates

[Cleanup and preservation](cleanup-and-preservation.json) records stopped owned
jobs, exited private namespaces, removed borrowed credentials and deletion of
the private raw runtime/workspace. Ordinary native preferences and hook/settings
configuration are unchanged. No ordinary history was deleted. The ordinary
credential file was not restored or edited by the operator and remained stable
during the installed proofs; the earlier interval included independent live
credential refresh, so whole-run credential digest equality is not claimed.
Both Codex daemon PID/birth tuples are unchanged. The current coordinator is
still open and was neither restarted nor resumed.

Luna implemented the Codex classification/filter, Claude SDK collector and
consumer validator, and reviewed the action boundary. The primary resolved
contracts and review findings, implemented saved Resume, ran native proofs,
installed the candidates and verified the final fleet state.

Graphical picker/terminal/focus acceptance, sleep/wake and SSH-loss recovery,
current-client conversation binding and published release remain separate.
Native focus, session-specific Close and batch actions remain disabled. An
already open picker must be reopened to load the new Python candidate; provider
sessions and daemons need no restart for this follow-up.
