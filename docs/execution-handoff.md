# Native runtime migration handoff

Date: 2026-10-03. The unattended implementation/pilot is complete for the
bounded subset in [execution status](execution-status.md). Source is
checkpointed in local commits; candidates are installed, with no published release.

## Installed state

| Host | Observer | Agent Plus | Provider policy |
| --- | --- | --- | --- |
| Snap | `0.1.0a5`, independent prefix, managed command verified | `0.13.0a3`, independent prefix, three managed entry links verified | Codex daemon auto-start enabled; Claude Agent View enabled, individual-entry preferences false; both providers observed |
| Starship | Same Observer wheel and managed command | Same Agent Plus wheel and entry links | Codex daemon auto-start enabled; Codex-only discovery; Claude uninstalled, its policy targets ignored |

The [artifact/cutover records](evidence/2026-10-03-native-runtime/migration-pilot-cutover.json)
and [native report](evidence/2026-10-03-native-runtime/REPORT.md) contain exact
hashes and proof limits. Prefixes remain separate from other packages' Python
environments. Previous owned extension archives and published external pins
are preserved; the managed links select the candidate override on Snap and
Starship. Other managed hosts retain their prior Plus targets and ignore the
new Observer link.

The [discovery/history acceptance](evidence/2026-10-03-discovery-history/REPORT.md)
records the current Observer `0.1.0a5` and Plus `0.13.0a3` tuple. Snap's optional
SDK is built from the pinned official source distribution with no bundled
Claude executable; Starship remains Codex-only without the SDK. All runtime
module hashes and managed links are verified. Reopen an existing picker to load
the new candidate; this follow-up needs no provider-session or daemon restart.

The subsequent [Rofi callback check](evidence/2026-10-03-discovery-history/rofi-callback-follow-up.json)
found that `.config/rofi/scripts/agent-plus` still selected `0.13.0a2` while
the two Plus CLI links selected `0.13.0a3`. Its managed template and installed
link are now corrected on both hosts. All four links, including Observer, pass
scoped verification. Public discovery through the actual Rofi script path
passes from both origins. The reported `Run sleep 20` and
`Agent plus Claude entry accepted` rows are owned top-level migration test
conversations, with their exact identities in earlier native proof records;
they were saved history rather than confirmed child rows. The subsequent
[user-requested cleanup](evidence/2026-10-03-discovery-history/test-session-cleanup.json)
removed five exact owned test conversations: one Codex conversation per host
and three Claude conversations on Snap. Both ordinary picker caches were
refreshed, with zero errors and no removed targets remaining. Non-target
conversations, ordinary live Claude registrations, loaded Codex sessions and
both Codex daemon births were preserved.

Discovery from both origins now returns 28 Claude conversations on Snap, with
history back to July 13 and 26 native titles. Work/presence of saved-only rows
stay unknown. Confirmed Codex children are excluded from the picker; ordinary
unknown older classifications remain visible. Installed Claude saved Resume
passed same-UUID and automatic-copy cases; the viewer binds the actual returned
job/session. Earlier migration, provider-selection and native-name records
remain dated evidence rather than current artifact records.

Agent Plus uses only the public host-local Observer snapshot for provider
discovery. Host Mesh still owns routing and Tmux Plus owns terminal lifecycle.
OpenCode integration is removed from this candidate; its history was preserved.
Native focus, session-specific Close and native batch actions remain excluded
because current-client conversation binding is unsupported. Fresh Resume and
New routes were exercised with disposable attached clients on both Codex hosts
and the Claude work host. Visual desktop/focus acceptance remains pending.

The coordinator did not inherit a display environment. A final read-only check
found an active same-user Waypipe proxy, with no local compositor or focus-control
endpoint. The installed picker was smoke-tested through that proxy; see
[process-smoke metadata](evidence/2026-10-03-native-runtime/picker-waypipe-smoke.json).
This check does not establish a rendered surface, remote compositor readiness
or visual/focus acceptance. The existing proxy birth was preserved.

For supervised Claude New, Agent Plus creates an empty native `claude --bg`
job with closed stdin, then attaches its exact typed short ID. A bare ordinary
Claude TUI remains foreground even with Agent View enabled. Existing foreground
sessions were preserved and observed; they were not converted, and the
candidate cannot attach them through the supervised-job route. Ordinary
configuration leaves `CLAUDE_CONFIG_DIR` unset; explicit custom roots use the
separate explicit configuration context.

## Coordinator continuity

The preserved coordinator is on **Snap**:

| Field | Value |
| --- | --- |
| Provider | `codex` |
| Config home | `/home/bryan/.codex` |
| Namespace | `sha256:cf971cf9393cf9719046ccc9b5e1b61d82c9836df3bbee5182375c6164015186` |
| Native ID kind | `thread` |
| Native thread ID | `01a0fece-0176-7a33-abb3-e99fdb38417a` |
| Explicit native saved-session ID | `01a0fece-0176-7a33-abb3-e99fdb38417a` |

The final passive read found that exact identity once in saved inventory with
current source health; see [coordinator metadata](evidence/2026-10-03-native-runtime/coordinator-handoff.json).
It does not establish the old client's runtime owner or an in-place migration.
The coordinator was never resumed concurrently or closed by this rollout.

When ready, finish/quiesce the old session and close its client deliberately.
Then, on Snap, reopen through the selected ordinary config namespace:

```sh
env CODEX_HOME=/home/bryan/.codex codex resume --all 01a0fece-0176-7a33-abb3-e99fdb38417a
```

The same exact saved-ID route was proved on disposable conversations on both
hosts. This conversation itself remains a manual final acceptance step. Check
native `/status` for the UUID after reopening, then read this handoff and
`docs/execution-status.md` before continuing. The old owner must quiesce first.

## Remaining work

The discovery/history goal is complete for its bounded source, native action
and installed gates. Source checks pass 127 Observer and 367 Plus tests, along
with lint/format and contract sync. No legacy collector or clean slate was
needed. The following acceptance and publication work remains separate.

1. On a graphical desktop, inspect the managed picker, selection preservation,
   terminal launch and focus behavior for local/remote Codex and supervised
   Claude. The coordinator had no graphical display connection; a successful
   launch request alone was excluded from native-entry acceptance.
2. Review the source changes in Agent Observer, Agent Plus and chezmoi. Publish
   a compatible release tuple after acceptance; the current pilot links and
   wheels are deliberately recorded as unpublished candidates.
3. Keep sleep/wake, SSH-loss recovery, unsupported state transitions and
   current-client binding explicit. Native batch/focus/close support needs its
   own proved authority before those controls can be enabled.
4. Continue the [RLCD bridge candidate](rlcd-bridge-candidate.md) in the separate
   RLCD project. Its source tests and installed-native-input projection do not
   prove firmware transport or physical display acceptance. Existing RLCD user
   changes were preserved.
5. Hook capture remains unproved. Historical trusted references were preserved,
   but the inspected Snap state lacked `~/.codex/hooks.json`, `swbctl` and
   `~/.claude-mem`; the goal did not repair that preexisting state.

Provider history and ordinary daemons remain intact. Disposable clients and
their exact owned wrappers/jobs were cleaned up, borrowed credentials were
removed, and the private Claude raw-proof tree was deleted after checking
ownership and process references. If a candidate fails, keep direct native
entry available and diagnose the bounded source health/reason codes before
changing runtime or package policy. Restoring a prior launcher or flag alone
does not establish compatible standalone behavior.
