# Claude observation wrap-up review

Date: 2026-10-09. Ordinary passive review of the accepted a9 artifact before the
documentation wrap-up; subsequent final selection verification confirms that
same artifact remains selected. This report records independent native
comparisons, installed read-client behavior and residual limits. It adds no new
provider predicate, schema, deployment or controlled lifecycle acceptance.

## Artifact and method

Read/service version: `0.5.0a9`, source
`5f69c0e6adbb485a2176651cdf001bb791ac4188`, wheel SHA-256
`d72cb6c360b35b42e96de2b56d0f85d909823ebb74a5abb1a4438809e6c04ef0`,
prefix `~/.local/share/agent-observer/0.5.0a9-d72cb6c360b35b42`.
[API 2](../../api-v2.md), snapshot/watch 4 and service protocol 2 are unchanged.
The normal writer remains independently selected at a16.

The [evaluation harness](../../../scripts/evaluate-observation), SHA-256
`02d1f4022ca5c2f85bab91379a1719e8c1dc07537ad04f0e3a25e4023f7196a9`,
imports no Observer collector. The Starship copy matched those exact bytes.
Each installed direct/cache comparison has two native-before/CLI/native-after
rounds. Codex reference reads its verified owning daemon; Claude reference reads
provider-owned registrations, authenticated incarnations and bounded saved
metadata under the accepted registration assumption. No client inventory or
ordinary provider action supplies evidence.

[Snap](snap-selection.json) and [Starship](starship-selection.json) final operator
receipts verify installed bytes, the six scoped managed targets and active/enabled
user units. No apply, restart or provider-policy change occurs in this wrap-up.
Codex native daemon provenance is `0.162.0` on both hosts, SHA-256
`50ed828f357c655a3c82054d346cab8434f24901f14ec19b8267571bdd008b38`;
these values are diagnostics, not support allowlists. The preceding
[a9 native report](../2026-10-08-claude-interactive-observer/REPORT.md) retains its
Claude on/off, exit/crash/Resume and isolated proof bounds.

## Ordinary comparison

[Comparisons](comparisons.json), [inventory summaries](inventory.json) and the
[review receipt](review.json) retain bounded IDs, state, clocks and limits only.

| Host/provider | Direct/native rows | Running | Parked | Unknown | Cached difference |
| --- | --- | --- | --- | --- | --- |
| Snap/Codex | 89 | 2 | 87 | 0 | None |
| Starship/Codex | 354 | 6 | 348 | 0 | None |
| Snap/Claude | 35 | 6 | 27 | 2 | One additional disappeared unsaved identity, retained as stale unknown |

All 14 native-reported running sessions match exact identity and sampled work
phase. They are Snap Codex `agent-observer` and `tmux-plus`; Starship Codex
`fluid-2.5d`, `pd-lab-next`, `raster90`, `devlog`, `sleep` and `system`; and Snap
Claude `a100-test`, `spare-gpus`, `pr-review`, `caos-models`, `2026-recap-dedup`
and `embeddings-bf`. Natural phase changes between later inventory samples are
not stable mismatches. This is native-source coverage, not an exhaustive census
of processes or unregistered Claude contexts.

All comparable runtime/phase facts agree: 89 Snap Codex, 354 Starship Codex and
35 Claude rows per round. Native conversation clocks agree wherever proved:
52/106 Codex clocks and 33 Claude clocks. Every classified user conversation has
current activity: 51 Snap Codex, 81 Starship Codex and 33 Claude. Most missing
Codex activity belongs to child history, not ordinary user history. Default list
filters 38/252 proved Codex children; 21 older Starship unknown kinds remain
visible. Exact selection, attention/activity ordering, human age and doctor
counts pass through installed read commands.

Two stable Claude differences remain: setup-only UUID
`e0cba9dd-b642-4730-af4b-beb3b7e9c16c` has native cwd `/home/bryan/code` versus
public null; cached UUID `4359adf3-32f1-49fb-ab95-cc780bfe68de` is absent from
the current native/direct inventory and carries stale unknown/last-known evidence
with `hasSavedHistory=false`. No new runtime/phase/activity mismatch is found.

## Delivery and source checks

[Push summaries](push.json) record four parsed installed service-watch frames
per host: sequence 1–4, stable service incarnation, monotonic view revision and
BOOTTIME, complete views and transport-only heartbeats; no gap or error occurs.
The default watch filters proved children, hence its view row counts differ from
the full service snapshot. This is bounded delivery/stream validation; it does
not independently prove every pushed row or lossless native transitions.

The [pure checks](pure-checks.json) separately run eight source ownership tests
and eight interface-conformance tests against installed a9 in isolated Python
imports outside the checkout. The documentation wrap-up also runs
`./scripts/check`: 383 tests, one skip, local-link/Markdown and diff checks.
The skipped independent JSON Schema check retains its separately managed proof
environment; the installed semantic facade checks here are distinct evidence.

## Resolution and follow-ups

- Stale a8 selection/pending-successor text in current agent instructions,
  validation, API/service pages and client handoff is reconciled with a9.
  Historical a8 reports and their original proof remain historical.
- Background runtime is unsupported. The two old recap histories staying unknown
  are outside the user's forward workflow and do not require compatibility work.
- Missing live native registration, SDK-excluded setup metadata, generic dialogs,
  nested Claude child history, Claude turn outcomes and older unknown Codex kinds
  retain their accepted limits. These samples do not prove away hidden runtime.
- Disappeared unsaved identity retention is a separate
  [shared-core follow-up](../../runtime-only-retention-follow-up.md). A9 still has
  row/byte bounds without time eviction. This report does not claim that repair
  is implemented or that stale unknown is a current running/parked assertion.
- Provider policy, attachment/actions, network forwarding, notifications and
  downstream implementation/native rollout remain independently gated.

The [Claude wrap-up](../../claude-observation-wrap-up.md) closes interactive
observation within this scope. The shared read contract is ready for independent
clients through the current [handoff](../../api-v2-client-handoff.md).
