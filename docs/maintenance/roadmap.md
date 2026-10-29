# Agent Observer roadmap

Agent Observer provides reusable Codex read-only observation for dashboards,
diagnostics and agent utilities. The CLI and persistent terminal dashboard are
available in the a13 prerelease with the qualification boundaries below.
Native managers continue to own conversation control.
[Fleet Plus](https://dev.byebyebryan.com/fleet-plus/) carries the shared showcase;
this repository owns native semantics, public interfaces and acceptance evidence.

## Current baseline

The [a11 release](https://github.com/byebyebryan/agent-observer/releases/tag/v0.7.0a11)
supports full API 4/snapshot 6/Service 4 and working-set reads. Collector and
working-set roles have a reviewed Mesh a25 pair; other roles and consumers
retain independent selections. [Operations](operations.md) links exact receipts.

Observer writes, Claude observation and standalone active-only hosting are
retired. Working-set includes active membership and recent context. Earlier
plans for restoring those retired paths are superseded.

Existing direct, service and Mesh commands support diagnostic inspection.
`working-set list` and `working-set watch` already read qualified cached state;
the current watch is bounded to 60 seconds. The terminal product builds on
these capabilities. The a13 package includes the dashboard as an optional extra;
its managed reader role stays independent of collector/publisher selection.

The [a12 sessions CLI](../guides/sessions-cli.md) provides configured
overview/list/show/source inspection and versioned JSON output. It has source,
clean-package and cached-consumer checks and includes the a11 clock-recovery
source. CLI reader selection/configuration is independent of the a11
collectors/publishers and other consumers. The a13 dashboard retains separate
package, native, resource, human and managed-deployment acceptance boundaries.

## Current milestone: CLI and dashboard qualification

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

Implementation lives in `agent-observer`: commands, dashboard, consumer
configuration, presentation, read lifecycle, tests and documentation.
Use public cached service/working-set facades and existing Mesh routes for
cross-host delivery. Keep core/local use independent of optional Mesh and
dashboard dependencies. Verify available metadata and read capabilities before
proposing producer, schema or transport changes; any demonstrated cross-repo
gap needs an explicitly scoped follow-up.

Agent Plus remains independently useful for native TUI entry. Tmux components
have no planned work for this milestone. Preserve configured directional host
authority. Managed reader installation has its own artifact and host checks,
separate from source acceptance; Fleet Plus presentation remains a separate
step. Reader packaging must not implicitly advance collector, publisher or
hardware-dashboard pins.

### Delivery sequence

| Stage | Scope and exit |
| --- | --- |
| Detailed planning | Reviewed; command/output shapes, configuration, dashboard screen/keys, dependencies and lifecycle/resource policy are recorded in the terminal product plan |
| Usable CLI | Released in 0.7.0a12; its finite CLI and JSON v1 remain the published interface |
| Standalone dashboard | Available in a13 with the optional dashboard extra, readable workspace/repository details and the recorded source/installed, recovery and realistic-fleet checks. Resource/native measurements retain their earlier exact-artifact bounds; extended soak and large-fleet stress testing remain deferred |
| Release and delivery | A13 is published and the independent CLI/dashboard reader role is selected on Snap, Starship and Carbon. Installed CLI/terminal and short dashboard checks pass; human/native/resource acceptance retains the recorded boundaries. Fleet presentation remains separate |

The terminal product plan records the selected command names, filters/order,
key bindings, optional extras and machine-readable output contract. The dashboard
does not change the finite CLI/JSON v1 contract and needs no new wire API, daemon
or native lifecycle controller.

### Acceptance

Review both CLI output and dashboard behavior with busy, quiet, empty,
partial, stale, unavailable and reconnecting sources. Include multiple
hosts/homes and one failed source alongside healthy ones. Prove that zero
displayed rows, filtering or loss of a source cannot produce a false
complete-empty verdict; silence and disconnect cannot leave current positives
alive past their leases.

The plan defines the resource durations and thresholds. The fixed
3-source/300-identity normal installed-dashboard profile and paired package
matrix pass on this candidate. An eight-hour soak is optional future testing,
not a preview gate. The user replaced
the eight-source/8192-outcome stress gate with a quick practical check of the
actual configured cached fleet. Existing controlled installed update,
interaction and source-recovery results supplement that short snapshot.
The new twenty-second installed-dashboard check passed with a current projection,
three complete sources, 16 members, zero uncertainty, clean exit and restored
terminal flags/reset. It stores aggregate metadata only and does not claim
new native or sustained-capacity proof.
Large-fleet stress testing and optimization are deferred. Verify the documented
public local/two-host recipe independently
of private chezmoi configuration.
Automated/synthetic, package, native, user-facing and managed-deployment
evidence remain separate gates.

Detailed planning starts with [`working_set_cli.py`](../../agent_observer/working_set_cli.py),
[`utility_read.py`](../../agent_observer/utility_read.py),
the [working-set guide](../guides/working-set.md),
[utility guide](../guides/read-utilities.md) and
[observation boundaries](../reference/observation.md). The existing example's
diagnostic JSON is not a stable scripting API. Extend the product experience
without treating its current renderer or 60-second budget as the final design.

## Priorities and acceptance

The [detailed terminal product plan](terminal-product.md) records the CLI
contract, implemented dashboard interaction and measurable gates. The resource
and installed qualification baseline is product source commit
`d57233313f01983361b75fb0953662afa212c513`; its frozen wheel has SHA256
`fd8ec13ee37470d1e31788df399057ba371eeaad67d412087993eb75995c55f0` and keeps
a12 distribution metadata, distinct from published a12. The later source preview
also corrects tiny-terminal help rendering and clears manual-retry cooldowns
when the receiving clock changes. Focused regressions check visible help and
retry with revoked facts/fresh baselines. The resource/native measurements below
retain their original baseline; these corrections do not claim a new sustained run.

The candidate passed 1,298 strict Mesh/dashboard source tests on each of Python
3.11.17 and 3.14.8. Eight installed variants passed with 112 package-file
parity checks and 98 paired dashboard tests per runtime with zero skips. The
installed `agent-observer dashboard` ran the fixed normal profile for three
sources x100 identities on a draining 120x40 terminal, with an external sampler.
It measured 4.88% and 4.74% of one core, with peak RSS of 65.17 and 66.60 MiB
and no measurement coverage misses. This does not establish capacity.
Earlier T6 Python 3.11 evidence at 5.1597% remains a failure; the candidates and
measurement windows differ, so these results do not prove a speedup.

The optional T9 eight-hour soak was stopped after about 3.6 measured hours,
with its owned test processes and sockets cleaned up and terminal restored.
It remains incomplete, not an eight-hour pass. Preview acceptance uses the
completed normal resource and controlled recovery checks.
Historical 8-source/8192-outcome stress capacity remains unmet: baseline
and traced reader-only runs never reached eight complete sources. Their sampled
maximum was four complete sources/4,096 members; they ended with three/3,072
after timeouts.
Consumer CPU was 45.60–47.38 seconds per minute and maximum event-loop lateness
was 1.43–1.48 seconds. The trace localizes work but does not prove the exact
timeout cause, measure the dashboard, or establish capacity. The original T5
task-minimum failure remains failed. No optimization, SDK tuning or validation
bypass has been adopted. Those stress results are retained as an unqualified
large-fleet limit, not a blocker for the revised realistic preview scope.

The detailed plan retains the earlier T5/T6 failures and current measurement
boundaries. Selected local native comparisons and public CLI checks are bounded
evidence; they do not establish full native, remote, human or physical-device
acceptance. Package publication and managed reader selection have their own
receipts, linked from [operations](operations.md); they do not broaden those
native/resource measurement claims.

| Area | Useful next step | Acceptance boundary |
| --- | --- | --- |
| Terminal product | Use the a13 CLI/dashboard reader and report concrete usability or recovery defects | Source/package and scoped deployment receipts remain distinct from human/native/resource acceptance |
| Native coverage | Investigate a reproducible identity or membership discrepancy | Independent native comparison on the affected host/home |
| Efficiency | Measure the owning collector/read path against an exact baseline | Matched CPU, memory and unchanged freshness/coverage |
| Consumer integration | Adopt an accepted producer interface where useful | Consumer-specific package, UI/device and recovery proof |

The terminal product remains the current direction; a13 publishes the checked
CLI/dashboard reader without promoting the historical stress failures to passes. Other rows are follow-ups driven by demonstrated need.
Deployment and unrelated infrastructure changes need their own scope.
Working-set coverage now reports a primary census, support or membership blocker.
Clock changes use bounded recency uncertainty and retain a detector incident
record; complete native source coverage does not imply complete working-set
membership. See [clock recovery](../guides/working-set.md#clock-changes-and-recovery)
for the producer policy and its limits. Source/package qualification does not
advance managed collector or consumer pins. Reopen membership semantics for a
reproducible discrepancy with independent native evidence; historical unexplained
partial samples do not establish a producer bug.

## Deferred work and reopen conditions

- Extended eight-hour soak testing is optional future work. Reopen for a
  suspected leak, resource growth during ordinary use or a concrete stronger
  uptime requirement. The cancelled partial soak is not an eight-hour pass.
- Large-fleet stress capacity and read-path optimization are deferred. The
  configured identity/payload caps are safety bounds, not proven fleet capacity.
  Reopen for an observed limitation at the user's actual workload or a concrete
  requirement for a larger deployment.
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
