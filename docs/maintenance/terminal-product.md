# CLI and dashboard product plan

Status: **CLI implemented in source; dashboard remains proposed**. The
[roadmap](roadmap.md#next-milestone-cli-and-dashboard) establishes the product
direction. The user selected the CLI-first P1/P2 slice under luna-goal-loop.
The [sessions guide](../guides/sessions-cli.md) documents the CLI commands and
setup. Source/package qualification is separate from a published release.
Dashboard layout/dependencies, persistent reconnect
and sustained dashboard budgets remain proposed for a later pass.

## Inspected baseline

Planning starts from maintained main
[`3c4f021`](https://github.com/byebyebryan/agent-observer/commit/3c4f021c463861db639129ef34b64cefd0c86a66)
in a separate `plan/cli-dashboard-20261025` worktree. The canonical checkout
remains on `cpu-prepared-admission`; preserve all other worktrees.

| Existing surface | Finding and consequence |
| --- | --- |
| [`cli.py`](../../agent_observer/cli.py) | Top-level list/show/doctor/snapshot/watch are direct diagnostics and can query the provider. Preserve their behavior; introduce separate product commands. |
| [`working_set_cli.py`](../../agent_observer/working_set_cli.py) | One selected host/source, active-lease filtering, diagnostic rendering and a 60-second cap. Preserve this bounded diagnostic interface. |
| [`utility_read.py`](../../agent_observer/utility_read.py) | Demonstrates admission, receiving clocks, quiet expiry and cleanup, but drops labels/activity/field leases from its summary. Its JSON and duration are not product contracts; it has no reconnect supervisor. |
| [`mesh_working_set_read.py`](../../agent_observer/mesh_working_set_read.py) | Public facade supplies full masked member records, uncertain identities, admitted nonmembers, scope coverage and member/field/scope deadlines. Use it as the product's selection authority. |
| [`home_profiles.py`](../../agent_observer/home_profiles.py) | Explicit private local manifest: required default, maximum two profiles, labels/namespaces/sockets/source IDs. This is not a fleet/home catalog. |
| Mesh a25 SDK 1 | Public `configured_reader` binds explicit local/configured hosts and source, with `report_routes=False`. Its host watch already retries channels and emits resyncs; avoid simultaneous SDK/product retry loops. |
| [Service 4](../guides/local-service.md) | Public `frames`/`ReadCache` supports independent full-cache diagnostics without Mesh. It is not an interchangeable working-set reader. |

The inspection environment imports Mesh `0.1.0a25`; the installed Observer CLI
reports `0.7.0a10`. Local configuration identifies this machine as Starship,
with a Default home and a configured directional route to Snap. Its files do
not establish Snap's local configuration or native runtime.

A bounded public-facade read on 2026-10-25 found the following cached metadata:

| Feed | Members | Named titles / current activity | Current workspace / project keys | Coverage |
| --- | ---: | ---: | ---: | --- |
| Starship / `agent_working_set` | 13 | 13 / 13 | 13 / 2 | complete |
| Snap / `agent_working_set` | 3 | 3 / 3 | 3 / 0 | complete |
| Snap / `agent_working_set_work` | 1 | 1 / 1 | 1 / 1 | complete |

This is transient cached-interface evidence, not independent native validation,
an exhaustive inventory or deployment acceptance. No actual titles, paths,
transcripts or raw frames are retained here. Native `name` supplies bounded
titles, falling back to `Codex <thread ID>`; no prompt/preview access is needed.
Project/workspace metadata is optional and expires independently. Title/cwd
have no independent projection field lease: describe them as admitted display
metadata, not freshly sampled native state. Never inspect remote paths/Git.

## Recommended commands and presentation

| Proposed command | Outcome |
| --- | --- |
| `agent-observer sessions` | Default quick overview; equivalent to `sessions overview`: source health, unfiltered counts and at most ten readable rows, with remaining count. |
| `agent-observer sessions list` | All selected current members and uncertain identity stubs, with search/filters/order; no silent row limit. |
| `agent-observer sessions show ID --host HOST --home HOME` | Full native thread ID in exactly one configured host/home; no prefix/title matching. Host/home may be omitted only when one source is selected. |
| `agent-observer sessions show --ref JSON` | Exact five-field identity; mutually exclusive with positional ID. Exact selection bypasses kind/display filters, but cannot recover rows absent from this projection. |
| `agent-observer sessions sources` | Source delivery, coverage, reasons and expected/observed home binding, even with no sessions. |
| `agent-observer sessions sources --configured` | Pure configuration inspection without Mesh imports, connections or provider queries. |
| `agent-observer sessions schema` | Packaged terminal JSON output schema without configuration or optional imports. |
| `agent-observer dashboard` | Standalone persistent TUI until quit/terminal shutdown; no default duration limit. |

Keep bare `agent-observer`, all existing direct/service/mesh/profile commands
and diagnostic `working-set watch` behavior. Product reads always use explicit
working-set caches. First milestone product reads require the optional Mesh
dependency, even for a local bridge. Core and local Service 4 diagnostics stay
usable without Mesh/Textual. Do not invent a Mesh-free working-set reader by
filtering a full inventory; a separate pure local facade is not a prerequisite.

Human columns: `SESSION`, `HOST/HOME`, `MEMBERSHIP`, `RUNTIME`, `PHASE`,
`ACTIVITY`, display ID. Title is primary; optional admitted project key or
workspace/cwd basename is labeled context, never identity. Use `Codex <ID>`
when no useful name exists. Details expose full identity/name, optional path,
metadata issues, exact activity timestamp, independent fact health/reasons,
scope coverage and relevant clock/lease information. Escape terminal, bidi and
markup controls in metadata; never interpret it as commands or terminal links.

For example, using invented labels:

```text
3 sources: 1 complete, 1 partial, 1 reconnecting | 7 members, 2 uncertain | 4 shown
SESSION              HOST/HOME        MEMBERSHIP  RUNTIME  PHASE     ACTIVITY
CLI planning         laptop/Default   active      running  working   2m ago
Renderer review      server/Work      active      running  waiting   8m ago
Release notes        laptop/Default   recent      parked   -         1h ago
Codex <display ID>   server/Work      uncertain   unknown  unknown   unknown
server/Default: reconnecting; current facts revoked
```

Source health precedes rows and survives filtering. Counts distinguish selected
members, uncertainty, known nonmembers, hidden kinds and displayed matches.
Narrow text wraps labels/secondary columns; piped text has no width truncation.

### Common semantics and defaults

- Membership is independent of native state. `active` requires an unexpired
  active branch lease. An otherwise admitted recent member displays `recent`:
  active is not currently proved, not proved false. Uncertain/nonmember outcomes
  come only from the facade. Stored `running` does not match an active filter.
- Runtime is running/parked/unknown. Running phase is working/waiting/blocked/
  unknown; parked has no applicable phase. Waiting does not imply a response is
  required. Show approval/question reasons only when admitted. Expired facts
  display `unknown (stale)`; last-known values are details, never current counts.
- Repeatable selectors: `--source`, `--host`, `--home`, `--membership`
  (active/recent/uncertain/nonmember), `--runtime`, `--phase`, `--query`. OR
  within a selector, AND across selectors. Uncertain rows cannot match positive
  runtime/phase filters. Default shows members and uncertain identities;
  nonmembers remain counted and explicitly inspectable.
- Default hides confirmed child/system kinds only; unknown kind stays visible.
  Add `--include-children`/`--include-system`. Search is case-insensitive literal
  substring over admitted name/project/path, host/home and full native ID, at
  most 256 characters. No regex, content search or persisted search history.
- Default flat list: active first, other members second, uncertainty last;
  within each class, current native activity descending, unknown activity last,
  full identity tuple as tie-breaker. Share `--sort activity|label|host` and
  `--group none|host-home` across CLI/TUI. Label sort uses casefolded label then
  identity; host sort uses host/home then the default activity order.
- Activity uses native `activity.at`. Relative wall-clock age is explicitly
  approximate; show clock-ahead/unknown qualifications and exact timestamp in
  details. Never use display age, thread update time, title changes, polling
  or transport liveness for membership/lease arithmetic. Preserve clock
  discontinuity; reconnect is not a repair for unchanged native activity.

`complete-empty` requires all selected sources to have current admitted
baselines, present complete unexpired scopes and no members, uncertainty or
known nonmembers. Filtering, hidden kinds, missing scopes, capacity limits and
empty configuration cannot establish it. With only admitted nonmembers, say
`0 qualifying members; N known nonmembers`. A filter result is `0 matches`,
with unfiltered counts and source health still visible.

### Scripting and exits

Use `--format text|json`, default text. Human spacing is not a scripting
contract. Piped text has no ANSI/cursor control or pager. Support
`--color auto|always|never`, `TERM=dumb` and nonempty `NO_COLOR`; `NO_COLOR`
takes precedence over always. Reuse the bounded stdout-write approach with
a five-second backpressure deadline.

JSON is one finite document: a new terminal output contract, independent of
API 4/working-set v1 and the utility's diagnostic JSON. Publish a schema and
fixtures with implementation. Proposed envelope:

| Fields | Meaning |
| --- | --- |
| `interface: "agent-observer.terminal"`, `version: 1` | Additive fields allowed; incompatible change requires another version. |
| `generatedAt`, `selection`, `filters`, `totals` | Point-in-time generation, resolved explicit sources and separate unfiltered/displayed counts. Generation renews no evidence. |
| `sources[]` | Consumer source ID, host/home, Mesh source, expected/observed namespace, baseline/delivery, scope coverage, reasons, sample times and receiving-clock context. |
| `sessions[]` | Current member identity/provenance, selected display metadata, membership branches, independently qualified facts and activity. |
| `uncertain[]`, `nonmembers[]` | Explicit exact-identity outcomes and bounded reasons, not current session-state rows. |
| `result`, `error` | Complete/degraded/not-found and optional bounded code; no raw SSH/provider payload. |

Deadline exports carry receiving boot/time-namespace binding and no continuing
authority after read closure; the report is not a live lease transfer. No JSON
watch/event-replay contract is proposed. Diagnostics use stderr. Invalid
invocation may fail before a JSON envelope exists.

| Exit | Meaning |
| --- | --- |
| 0 | Finite read has complete current selected coverage, including zero matches; dashboard explicit quit returns 0 regardless of feed health. |
| 1 | Exact show target unavailable within fully observed selected projection; this does not prove deletion or absence from history. |
| 2 | Invalid arguments/configuration, empty source selection or missing dependency, with actionable stderr explanation. |
| 3 | Report has partial/stale/unavailable/unsupported coverage, blocked source, timeout or capacity failure, including all sources unavailable. Unresolved show uses this rather than not-found. |
| 130 / 143 | Interrupt / termination after owned cleanup and terminal restoration. |
| 141 | Closed output pipe, without traceback. Other output failures use exit 3. |

Finite reads wait for the first settled result from each source or a shared
ten-second total deadline (`--timeout` 1-60 seconds), then close all streams.
They do not print a final revoked line over the report. Preserve per-source
sample times: this is not an atomic fleet snapshot. Reconnect cannot extend
the finite deadline.

## Source/home configuration

Use a separate private consumer file at
`$XDG_CONFIG_HOME/agent-observer/terminal.toml` (fallback
`~/.config/agent-observer/terminal.toml`), overridden by `--config`. Missing
config produces setup guidance, not automatic home/host discovery.

```toml
version = 1
default_sources = ["workstation-default"]

[[sources]]
id = "workstation-default"
host = "workstation"
home = "default"
label = "Default"
mesh_source = "agent_working_set"
scope = "local"
socket = "/run/user/1000/mesh-plus-agent-working-set/read.sock"
namespace = "sha256:<replace with full namespace reported by profiles>"
window_hours = 72
```

Replace the namespace placeholder before use. Remote entries use `scope =
"hosts"`, with a host in the public Mesh catalog; the configured directional
route owns remote delivery. The socket field affects local selection only.
Do not parse/rewrite SSH or chezmoi files to discover remote homes. Remote
home labels/source IDs/namespaces are explicit configuration.

Reuse `profiles --config ... --json` or `load_home_profiles` for pure local route
inspection when preparing entries; do not change the producer manifest. The
existing Mesh codec binds host/source/window but not an expected home namespace,
as recorded in
[`test_home_profile_routes.py`](../../tests/test_home_profile_routes.py).
Require expected namespace and check every scope/identity before assigning a
home label. Mismatch blocks the source and revokes its rows. Do not relabel a
different home or reset namespace automatically on publisher restart.

Validate version, exact keys, bounded labels/IDs, namespace and absolute local
socket before I/O. Follow the profile loader's owner/private-regular-file/
no-symlink policy and 64 KiB limit. Require unique source IDs and host/home
pairs; reject duplicate host/Mesh-source routes. Limit to eight sources.
Select explicitly listed `default_sources` unless source/host/home selectors
choose other configured entries. Unknown selectors or zero selection fail.

Optional per-entry `max_identities` and `max_payload_mib` reserve client capacity
(defaults 1,024 and 4). Validate positive integers, the existing per-source
contract bound and aggregate limits before connecting. This is a visible client
capacity limit, not permission to request a smaller native inventory.

`--socket`/`--window-hours` overrides require exactly one selected source;
socket overrides require local scope. Window selection must match the fixed
publisher window and never reconfigures it. Do not use ambient `CODEX_HOME`
to redirect a cached source. Config contains no credentials/SSH commands and
is frozen during an invocation: no hot-added homes/hosts or automatic routes.

## Dashboard layout and keys

One primary screen contains source health, search/filter status, session list,
selected details and persistent keyboard help. No native terminal pane,
conversation content, notifications, action buttons or runtime controller.

```text
Agent Observer   7 members / 2 uncertain   1 complete / 1 partial / 1 reconnecting
Sources: laptop/Default complete | server/Work partial: clock discontinuity
Find: ...                Host: all  Home: all  Membership: members + uncertain
SESSION LIST                         SELECTED SESSION
> CLI planning                       Runtime: running / current
  Renderer review                    Phase: working / current
  Release notes                      Activity: approximately 2m ago
                                     Membership: active; recent also proved
                                     Full identity, reasons, source and clocks
? help  / search  f filters  s sources  Enter details  r retry  q quit
```

At 120x40 or wider use list/details side by side. At 80x24 use list with Enter
opening full-screen details, keeping health/help visible. At 60x16 use compact
two-line rows and separate details/source panels. Below 60x16 show resize
guidance, health summary and working quit/help keys while continuing expiry.
Non-TTY stdin/stdout or `TERM=dumb` rejects dashboard with guidance to finite
listing. No-color mode spells out every state and selection.

| Key | Action |
| --- | --- |
| Up/Down or j/k, PageUp/PageDown, Home/End | Navigate the ordered list. |
| Enter / Escape | Open details / close panel or cancel search edit. |
| `/` | Edit literal search with 150 ms debounce; input focus owns printable keys. |
| `f` | Source/host/home/membership/runtime/phase/kind filter dialog. |
| `o` / `g` | Choose order / grouping. |
| `s` | Source details, including feeds with no displayed rows. |
| `r` | Retry focused failed source, or choose one in source panel; one-second throttle, no fleet restart. |
| `?` / `q` / Ctrl-C | Help / explicit quit / interrupt. Modal and input focus take precedence. |

Selection uses the full five-field identity, never index/title/cwd/short ID.
Preserve it through insertions, sort and resize. If filters hide it, say
`selected session hidden by filters` with clear-selection control. If it leaves
the projection or its source fails, retain only that selected reference/label
as unavailable; do not jump to another row or show old runtime as current.
Drop this single placeholder when another selection is made. Source ID is
provenance, not identity; reject conflicting duplicate identity claims instead
of merging by recency. Display ID abbreviations cannot select a row.

## Lifecycle, reconnect and resource policy

One worker per host/Mesh-source pair owns its expected namespace, shared
reader/guard profile instance, SDK stream and at most one pending `anext`.
Use public `configured_reader`, admitted delivery and
`PreparedWorkingSetAgentWatch`, with `report_routes=False`. Separate workers
preserve healthy feeds when one fails. Serialize each guard's calls. No private
stores or hidden full-inventory/legacy fallback.

```text
configured -> connecting -> warming -> observing
                              observing may have partial/stale coverage
connecting/warming/observing -> revoked -> retry-wait -> connecting
any state -> blocked (binding/contract/configuration failure)
any state -> closed (quit/cancellation)
```

- Connection/warming never grants positives. Baseline, scope coverage and
  independent fact health remain separate; connected does not mean complete.
- Call public `read(now, clock)` on frames and quiet wakes at most 250 ms
  apart using receiving BOOTTIME/domain. Keep the pending SDK read across quiet
  wakes. Wall time and presentation ticks renew nothing.
- EOF/gap/resync/delivery loss/invalid frame/incarnation transition/cancellation
  first revokes the source model, then disconnects the guard and closes the
  owned iterator/pending read. Do not render candidate resync positives.
  Reconnect creates a new request, reader/profile/guard and requires a fresh
  admitted cached baseline/proof. Tag work by epoch so old results cannot revive
  revoked state. A producer clock guard remains unresolved until native proof
  changes; reconnect is not recovery for that uncertainty.
  Keep SDK proof cadence at its existing Agent default (ten seconds); quiet UI
  checks do not request additional proofs or native samples. A live-but-stale
  source stays visibly stale rather than reconnecting repeatedly to renew facts.
- Mesh already retries channels. Close its iterator on the first observable
  failure/resync so the product becomes the sole continuing retry owner.
  Initial connection/baseline setup has a 15-second deadline. Keep each source's
  bounded original error code plus plain-language explanation.
- Transient failures retry at 1, 2, 4, 8, 16, 30 seconds, then 30 seconds, with
  jitter of 80-100% of the step. Reset after 60 seconds of stable admitted
  delivery. Allow four concurrent setups; stagger retries to at most one start
  per second. Finite CLI deadlines still take precedence.
- Binding/unsupported-contract/namespace/window/capacity failures block until
  explicit retry/restart after correction. Catalog revision/scope change revokes
  and requires explicit retry of the same selected pair. Do not automatically
  expand source selection, accept another namespace or write route health.
- Admit/order-check all wire frames before coalescing presentation. Keep one
  latest replacement per source; revocation/epoch barriers cannot be overwritten
  by a queued earlier positive. No unbounded UI message queue or event history.
- Repaint at most four times/second, age-only updates once/second; unchanged
  heartbeats cause no repaint. Re-evaluate expiry before rendering. Page at
  most 200 list rows while search/filter examines the entire accepted model;
  pagination cannot change completeness/counts.
- Retain one admitted generation/source and no disk history. Respect 4,096
  identities/source; additionally cap aggregate identity outcomes at 8,192 and
  encoded admitted payload at 32 MiB, including uncertainty/nonmembers. Reserve
  shares per source at startup (default 1,024 identities/4 MiB each; explicit
  shares may trade capacity within aggregate limits). Reject/revoke an
  over-budget generation visibly, never trim silently or choose winners by
  admission order. Per-source payload allowance must include its scope/support
  metadata, not just displayed rows.
- Quit cancels workers, disconnects guards and closes owned streams/SSH children
  through SDK cleanup. No publisher/provider is stopped. Budget five seconds
  for cleanup, two seconds for normal terminal restoration; report failed
  cleanup as failed qualification rather than claiming a pass.

Budgets are proposed thresholds, not measurements. If public-facade evaluation
or rendering misses them, report the measured failing checkpoint before
proposing transport/producer changes. Do not import CPU research, weaken
admission or enable delta/view-feed to meet a budget.

## Implementation structure and dependencies

Recommend optional `dashboard = ["textual>=8.2.8,<9"]`, with exact CI/package
qualification locks. The [8.2.8 metadata](https://pypi.org/project/textual/8.2.8/)
admits Python 3.11/3.14. Textual's async model fits Mesh;
[headless Pilot tests](https://textual.textualize.io/guide/testing/) support
keys/terminal sizes and documented
[no-color behavior](https://textual.textualize.io/api/filter/) can be tested
without internal filter APIs. This is a candidate, not tested compatibility.

Textual adds transitive packages. Curses avoids these but requires more custom
layout/input/test infrastructure; recommend Textual for this milestone. Keep
CLI rendering dependency-free. Install `.[mesh]` for product CLI,
`.[mesh,dashboard]` for TUI; import both extras lazily. No syntax/web extras,
core Rich dependency or changes to managed Mesh/collector pins.

Proposed modules under `agent_observer/terminal/`:

| Module | Responsibility |
| --- | --- |
| `config.py` | Bounded pure consumer config, source shares and exact selection. |
| `model.py` | Immutable presentation records, identity/provenance, vocabulary, counts, filters/order and empty-state interpretation; no native classifier or I/O. |
| `sources.py` | Public facade lifecycle, lazy Mesh import, source supervisor and cleanup. |
| `cli.py`, `render.py`, `output.py` | Parsing, finite fan-in, human text and versioned JSON. |
| `dashboard.py` and packaged stylesheet | Lazy Textual import, layout/input/selection and capped rendering. |

Dispatch sessions/dashboard from existing CLI without altering diagnostics.
Keep the bounded utility example; factor only genuinely shared primitives,
not its summary renderer. No demonstrated gap requires core/native/Mesh or
frozen wire/schema edits. Consumer JSON/config schemas are separate contracts.

## Checkpoints and acceptance

The CLI source checkpoint includes deterministic model/configuration tests,
controlled public-facade reads, clean wheel installation on Python 3.11/3.14,
core-only schema/configured inspection, and cached three-feed qualification.
Exact show, zero-match reporting, wrong-namespace isolation, publisher-window
mismatch, plain pipes and real 60/80/120-column PTYs were exercised. Wheel,
installed and source Python/schema bytes matched. Only aggregate metadata was
retained; cached consumer checks do not establish independent native accuracy.
Release/pin selection and managed installation remain separate, and the
persistent dashboard/soak gates below have not run.

| Checkpoint | Reviewable exit |
| --- | --- |
| P0: product review | CLI-first P1/P2 selected by the user; the CLI contract above guides implementation. Dashboard dependency/layout/reconnect/resource choices remain proposed. |
| P1: config/shared model | Implemented and checked with representative states, exact identity, labels, filtering/counts, strict empty-state rules, wrong-home rejection and imports without extras. |
| P2: usable finite CLI | Implemented overview/list/show/sources/schema, JSON v1, bounded output/exits, timeout and failure isolation; installed cached-read and terminal checks passed. |
| P3: persistent dashboard | Shared semantics plus selection/keys/resize/no-color, quiet expiry, fresh-baseline recovery and bounded queues; headless and real-terminal proof. |
| P4: qualification | Full source gate, strict optional pairs, clean installed wheel, public local/two-host recipe, independent native comparisons and sustained/user-facing acceptance. |
| Later delivery | Release/pins, managed installation, hardware consumers and Fleet presentation remain separate. |

Use unittest conventions, deterministic clocks and controlled cached servers.
Add meaningful product/lifecycle tests, not copies of formatting implementation.
Exercise CLI and TUI with the same representative cases:

| Scenario | Required result |
| --- | --- |
| Busy/quiet/parked, active with old activity, recent with unknown runtime | Membership stays distinct from native state; native activity drives display age. |
| Complete empty, nonmembers only, empty members with uncertainty | Distinct labels; only strict complete-empty can claim complete empty. |
| Partial census, clock discontinuity, stale field, unsupported capability | Exact source/fact limitation accessible; no false idle or synthetic recovery. |
| Three feeds, one fails, filters hide all rows | Healthy feeds survive; failures/unfiltered totals remain visible. |
| Quiet member/field/scope expiry, suspend/resume | Model loses authority at deadline; normal screen revokes within 250 ms, without refreshing evidence. |
| Gap/resync/EOF, publisher restart, bad order, wrong namespace/window | Revoke before recovery, reject old epoch work, require new baseline or stay blocked. |
| Same native ID across hosts/homes, duplicate labels, reorder/remove selection | Exact identities remain distinct; selection never silently retargets. |
| Hidden kind/exact show, query/state filters, zero-match selection | Documented counts/exits with no full-inventory lookup. |
| Controls/markup, wide/long Unicode, no-color, blocked pipe | Safe literal labels, usable layout, bounded output and no traceback. |

Record machine/CPU/interpreter/package bytes with these proposed measurements:

- Normal: three sources, 100 identities each, 120x40 terminal. After two-minute
  warmup, 30 quiet minutes average at most 2% of one CPU core and 192 MiB RSS,
  with no native reads or route reports by the client. Report client/owned-child
  CPU separately from existing producer CPU. Eight-hour soak: RSS growth at
  most 16 MiB after warmup, no growing task/FD/child counts or retired generations.
- Capacity: eight sources, 8,192 total identities within assigned shares,
  at most 768 MiB RSS. Admitted-update-to-display/list response p95 at most one
  second, normal workload p95 250 ms. Above-capacity fails visibly.
- At 120x40, 80x24 and 60x16, normal resize/key response p95 at most 100 ms;
  also exercise 40x10 guidance, NO_COLOR and TERM=dumb. Verify actual PTY
  behavior and terminal restoration, not just headless snapshots.
- Warming/source status appears within 500 ms independently of network setup.
  After a controlled cached source becomes available, a new current baseline
  arrives within five seconds of an attempt starting; backoff adds at most
  30 seconds. Native coverage may remain partial after reconnect.
- Ten-minute outage follows retry bounds; 100 controlled disconnect/recovery
  cycles leave no extra tasks/FDs/children. Shutdown closes within five seconds
  without affecting existing owners. Stalled rendering/burst updates cannot
  preserve revoked positives or cause an unbounded queue.

Package matrices cover Python 3.11/3.14, core-only, mesh-only and mesh/dashboard.
Missing extras fail before connection. Run `scripts/check-docs`,
`./scripts/check --require-working-set-mesh`, Ruff and the new dashboard suite
with optional checks explicitly required. Test installed wheels outside source.

The public recipe must cover an existing local working-set publisher/bridge,
explicit directional second-host route and second home without private chezmoi
configuration. Label fixture-only end-to-end evidence synthetic. Compare exact
identities/runtime/phase/activity/age to independent native evidence under the
[validation workflow](validation.md); cached/display results are not native
proof. Keep package, native, user-facing and deployment acceptance separate.

The CLI slice uses sessions commands, JSON v1/exits, explicit namespace-bound
sources and the active-first flat default. Screen/keys, Textual, persistent
reconnect and sustained budgets remain dashboard review decisions. No Agent
Plus/sidebar, WSNav, Tmux, deployment, alerts, content inspection or runtime
control is part of these checkpoints.
