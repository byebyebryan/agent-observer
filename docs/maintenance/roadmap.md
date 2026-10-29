# Agent Observer roadmap

Agent Observer provides read-only Codex observation for everyday terminal use,
dashboards, diagnostics and agent utilities. Native managers own conversation
control. [Fleet Plus](https://dev.byebyebryan.com/fleet-plus/) carries the shared
showcase; this repository owns observation semantics and the terminal product.

## Delivered baseline

The [a14 prerelease](https://github.com/byebyebryan/agent-observer/releases/tag/v0.7.0a14)
provides the configured CLI and optional standalone dashboard. Its independent
reader role is delivered to Snap, Starship and Carbon; collectors/working-set
publishers retain the reviewed a11/Mesh a25 pair. Other consumers and roles
retain their own selections. [Operations](operations.md) owns release provenance
and managed-role guidance.

| Workflow | Current product |
| --- | --- |
| Quick check | Bare `agent-observer`: readable fleet overview, source health and up to ten rows |
| Investigate | `sessions list/show/sources`: all matching rows, exact-session details, coverage and terminal JSON v1 |
| Keep watch | `dashboard`: persistent list, literal metadata/repository search, filters, exact pinned selection, adaptive details and source recovery |
| Host the first source | [First-source setup](../guides/source-setup.md): private foreground a11 collector + Mesh a25 publisher to the released a14 reader |

Working-set supplies active membership and recent context, ordinarily over
72 hours. Membership, runtime and phase remain separate; active does not mean
working, and waiting does not itself mean a response is required. Explicit full
inventories remain diagnostic. Observer writes, Claude observation and standalone
active-only hosting are retired.

The [Fleet Plus showcase](https://dev.byebyebryan.com/fleet-plus/projects/agent-observer/)
and Devlog presentation are delivered. Detailed pages use released a14 terminal
captures and an opt-in demo over fictional cached sources, with explicit
provenance. The small portfolio card uses a readable workflow figure centered
on Agent Observer and local/multi-host use. Fleet Plus owns those presentation
choices; they add no native, resource or physical qualification.

## Current focus: everyday CLI and dashboard use

Use the installed reader in ordinary terminals and turn concrete usability or
recovery defects into bounded follow-ups. The [sessions guide](../guides/sessions-cli.md)
and [dashboard guide](../guides/dashboard.md) own setup/use; the
[terminal product contract](terminal-product.md) owns semantics, lifecycle,
resource budgets and current acceptance limits.

| Priority | Next useful work | Acceptance boundary |
| --- | --- | --- |
| Everyday usability | Check whether names, workspace context, search, selection and source-health explanations answer routine questions | Real user feedback; source/package tests do not establish human acceptance |
| Recovery | Investigate expired facts shown as current, false empty results, failed reconnects or terminal restoration | Exact reader/dependency bytes, affected source, lease/baseline transitions and owned cleanup |
| Native coverage | Investigate a reproducible identity/runtime/membership discrepancy on its owning host/home | Independent native evidence; a frontend release or a later complete sample does not close a producer incident |

Implementation remains in `agent-observer` unless evidence identifies a specific
cross-repo gap. Reuse public cached facades and configured directional Mesh
routes. Agent Plus independently opens native TUIs; Tmux components and hardware
dashboards have no automatic migration. Reader packaging does not advance any
producer or other consumer pin.

## Acceptance boundary

The released reader has source, installed-package, controlled lifecycle and
short actual-fleet terminal checks. The original source-preview normal resource
profile passed at the user-accepted <=5% of one core. Those measurements and
selected native comparisons retain their exact earlier artifact bounds; a14
adds no new sustained-resource or full native/remote claim. The
[qualification summary](terminal-product.md#qualification-and-limits) links
immutable evidence and preserves failed/incomplete historical results.

Keep source, public package, installed role, native accuracy, consumer behavior,
resource and human/physical acceptance separate. A current cached read is not
an independent native census or proof that a recurring producer issue is fixed.
Working-set's primary coverage blocker and
[clock-recovery policy](../guides/working-set.md#clock-changes-and-recovery)
help explain incomplete results without inferring a producer bug from an
unexplained historical sample.

## Deferred work and reopen conditions

- **Extended soak:** the cancelled partial run is not an eight-hour pass. Reopen
  for suspected leaks, ordinary-use resource growth or a stronger uptime need.
- **Large-fleet capacity and optimization:** failed eight-source/8,192-outcome
  checks remain unqualified. Admission caps are safety bounds, not usable
  capacity. Reopen for an actual workload limit or a concrete larger deployment;
  measure the owning read/collector path against exact bytes without weakening
  freshness, coverage or validation.
- **Agent Plus sidebar/native composition:** revisit when standalone use shows
  repeated need for an agent list beside a native TUI. The old WSNav design is
  deprecated; Kitty spikes are historical evidence, not a tmux-runtime mandate.
- **Delta synchronization:** remains dark after failed CPU/capacity gates.
  Reopen only for a measured requirement and a bounded qualification plan.
- **Optional complete-view/prepared delivery:** needs an actual consumer,
  independent compatibility evidence and explicit role selection.
- **New providers:** require capability, contract and independent native review;
  reserved wire vocabulary does not enable an adapter.
- **Event replay/completion notifications:** need a separate producer contract;
  sampled state watches do not guarantee every transition or turn completion.

Revise current priorities and contracts as decisions change. Completed plans,
measurements and investigation history remain in Git and immutable release
provenance rather than growing this roadmap.
