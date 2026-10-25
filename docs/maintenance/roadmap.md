# Agent Observer roadmap

Agent Observer provides reusable Codex read-only observation for dashboards,
diagnostics and agent utilities. The next product milestone is a user-friendly
CLI and standalone, always-on terminal dashboard for agents across configured
hosts and homes. Native managers continue to own conversation control.
[Fleet Plus](https://dev.byebyebryan.com/fleet-plus/) carries the shared showcase;
this repository owns native semantics, public interfaces and acceptance evidence.

## Current baseline

The [a10 release](https://github.com/byebyebryan/agent-observer/releases/tag/v0.7.0a10)
supports full API 4/snapshot 6/Service 4 and working-set reads. Collector and
working-set roles have a reviewed Mesh a25 pair; other roles and consumers
retain independent selections. [Operations](operations.md) links exact receipts.

Observer writes, Claude observation and standalone active-only hosting are
retired. Working-set includes active membership and recent context. Earlier
plans for restoring those retired paths are superseded.

Existing direct, service and Mesh commands support diagnostic inspection.
`working-set list` and `working-set watch` already read qualified cached state;
the current watch is bounded to 60 seconds. The terminal product builds on
these capabilities. The dashboard described below is planned, not shipped.

## Next milestone: CLI and dashboard

The terminal product should be useful in ordinary terminals without dedicated
display hardware. The CLI supports quick checks and session investigation;
the TUI stays visible while the user works elsewhere or in another terminal.

| Workflow | Product outcome |
| --- | --- |
| Quick check | A concise fleet summary and readable session list |
| Investigate | Session details explaining state, host/home, freshness and uncertainty |
| Keep watch | A persistent dashboard with live updates, filtering and keyboard navigation |

Working-set supplies active membership and recent context, ordinarily over a
72-hour window. Membership, native runtime and work phase remain separate:
active membership does not mean working, and waiting does not by itself mean
the user must respond. Full inventories remain an explicit diagnostic path.

### Product requirements

- Present readable session labels where admitted metadata supports them,
  host/home, runtime/work phase and meaningful activity time. Keep exact
  identities and technical reasons accessible in details. Check metadata
  availability before promising titles or project labels.
- Use consistent state vocabulary, filtering and interpretation in CLI and
  TUI. Preserve unknown states and explain incomplete or failed observations
  in ordinary language, with deeper diagnostic evidence available.
- Make configured hosts/homes convenient to select. Normal use should avoid
  repeated socket and transport arguments; explicit overrides remain useful.
  Determine discovery and defaults from existing public interfaces and actual
  configuration, without hardcoding the operator's fleet.
- Provide session search, host/home and state filters, predictable sorting,
  stable selection and discoverable keys. Keep source health visible when
  session rows are filtered out.
- Keep the dashboard open until the user quits. Recompute expiry during
  silence, revoke current facts after stream loss and reconnect with a fresh
  baseline. A reconnecting or warming source must remain distinguishable from
  a complete empty source.
- Support terminal resizing, readable narrow layouts and use without color.
  Keep rendering, queues and retained state bounded, and measure idle cost.
- Read only: opening the dashboard must not start a missing provider,
  control conversations or send notifications. Session content is outside
  this milestone; retain the existing bounded metadata boundary.

### Implementation boundary

The expected implementation lives in `agent-observer`: commands, dashboard,
consumer configuration, presentation, read lifecycle, tests and documentation.
Use public cached service/working-set facades and existing Mesh routes for
cross-host delivery. Keep core/local use independent of optional Mesh and
dashboard dependencies. Verify available metadata and read capabilities before
proposing producer, schema or transport changes; any demonstrated cross-repo
gap needs an explicitly scoped follow-up.

Agent Plus remains independently useful for native TUI entry. Tmux components
have no planned work for this milestone. Preserve configured directional host
authority. Chezmoi installation and Fleet Plus presentation are later delivery
steps, separate from source acceptance; new reader/UI packaging must not
implicitly advance collector, publisher or hardware-dashboard pins.

### Delivery sequence

| Stage | Scope and exit |
| --- | --- |
| Detailed planning | Review current commands and available metadata; settle command/output shapes, dashboard screen and keys, configuration/defaults, dependencies, and reconnect/resource policy using representative states |
| Usable CLI | Implement quick overview, readable listing and selected-session details with shared state interpretation; define pipe/output and exit behavior and retain explicit diagnostics |
| Standalone dashboard | Implement the persistent list, source health, search/filters and details; validate selection, resizing, quiet expiry, reconnect and clean shutdown |
| Release and delivery | Qualify the installed package and documented local/two-host setup, then separately review managed installation and showcase updates |

These stages describe dependency order within one product milestone. Exact
command names, default filters/order, key bindings, framework, optional extras
and machine-readable output contract are detailed-planning decisions, not
settled interfaces. A new wire API, daemon or native lifecycle controller is
not a prerequisite.

### Acceptance

Review both CLI output and dashboard behavior with busy, quiet, empty, partial,
stale, unavailable and reconnecting sources. Include multiple hosts/homes and
one failed source alongside healthy ones. Prove that zero displayed rows,
filtering or loss of a source cannot produce a false complete-empty verdict;
silence and disconnect cannot leave current positives alive past their leases.

Exercise a normal terminal at multiple sizes and without color, predictable
selection through updates, filtering/details, interrupted reads and shutdown.
Measure a sustained quiet run and recovery under bounded state/queue budgets;
the detailed plan must choose durations and acceptance thresholds. Verify the
actual installed package and a reproducible public local/two-host recipe,
independent of private chezmoi configuration. Automated/synthetic, package,
native, user-facing and managed-deployment evidence remain separate gates.

Detailed planning starts with [`working_set_cli.py`](../../agent_observer/working_set_cli.py),
[`utility_read.py`](../../agent_observer/utility_read.py),
the [working-set guide](../guides/working-set.md),
[utility guide](../guides/read-utilities.md) and
[observation boundaries](../reference/observation.md). The existing example's
diagnostic JSON is not a stable scripting API. Extend the product experience
without treating its current renderer or 60-second budget as the final design.

## Priorities and acceptance

| Area | Useful next step | Acceptance boundary |
| --- | --- | --- |
| Terminal product | Deliver the CLI/dashboard milestone above | Everyday usability, qualified state, recovery and installed-package proof |
| Native coverage | Investigate a reproducible identity or membership discrepancy | Independent native comparison on the affected host/home |
| Efficiency | Measure the owning collector/read path against an exact baseline | Matched CPU, memory and unchanged freshness/coverage |
| Consumer integration | Adopt an accepted producer interface where useful | Consumer-specific package, UI/device and recovery proof |

The terminal product is the agreed next direction; detailed planning precedes
implementation. Other rows are follow-ups driven by demonstrated need.
Deployment and unrelated infrastructure changes need their own scope.
Working-set coverage now reports a primary census, support or membership blocker.
Clock discontinuities and other legitimate uncertainty remain explicit; complete
native source coverage does not imply complete working-set membership. Reopen
membership semantics only for a reproducible discrepancy with independent native
evidence. Historical unexplained partial samples do not establish a producer bug.

## Deferred work and reopen conditions

- A later Agent Plus client could place an agent list beside a native TUI and
  add explicit focus/open behavior. Revisit after standalone CLI/dashboard
  use provides concrete requirements. WSNav's former design is considered
  deprecated; the earlier Kitty spikes are historical evidence, not a
  requirement to restore tmux-based runtime control. Sidebar layouts, native
  session selection and terminal orchestration do not constrain this milestone.
- Delta synchronization remains dark after failed CPU/capacity gates. Reopen only
  with a concrete measured requirement and a reviewed bounded qualification plan.
- Optional complete-view feed and transport adoption need an actual consumer,
  independent compatibility evidence and explicit role selection.
- New native providers need capability/contract/native review. Reserved wire
  vocabulary is insufficient.
- Native event replay or guaranteed completion notifications need a separate
  producer contract and independent evidence; sampled state watches do not supply it.

Revise this page when direction or acceptance boundaries change. Completed
investigations do not become a permanent roadmap or a collection of status notes.
