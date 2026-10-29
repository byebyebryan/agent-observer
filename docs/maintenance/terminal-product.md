# CLI and dashboard product contract

The [0.7.0a14 prerelease](https://github.com/byebyebryan/agent-observer/releases/tag/v0.7.0a14)
provides the finite sessions CLI and optional persistent dashboard. This page
records their current behavior, ownership and acceptance limits. Use the
[sessions guide](../guides/sessions-cli.md) and [dashboard guide](../guides/dashboard.md)
for installation, source configuration, commands and keys; use the
[roadmap](roadmap.md) for priorities and deferred work.

## Workflows and public interfaces

| Workflow | Contract |
| --- | --- |
| Quick check | Bare `agent-observer`, `sessions` and `sessions overview` share a finite overview with source health, unfiltered counts and at most ten rows. |
| Investigate | `sessions list` returns all matching rows; `show` selects a full native ID in one host/home or an exact five-field JSON reference. Exact inspection bypasses display filters and hidden kinds, but cannot recover absent history. |
| Inspect delivery | `sessions sources` reports source health even without sessions. `sources --configured` validates configuration without connecting or importing Mesh. |
| Script | Finite `--format json` emits terminal interface 1; `sessions schema` prints its packaged schema without configuration or optional imports. Human text spacing is not a parser contract. |
| Keep watch | `dashboard` remains open until quit or terminal shutdown, over the same configured cached sources. It has no finite lifetime, JSON watch, `--format` or `--timeout` option. |

Terminal interface 1 is independent of API 4, snapshot/watch 6, Service 4 and
working-set v1. Its [packaged schema](../../agent_observer/contracts/terminal-v1.schema.json)
separates selection/filters, unfiltered totals, sources, members, uncertain
identities, known nonmembers and result/error. Additive fields are allowed;
incompatible output needs a new version. The utility example's diagnostic JSON
is not this contract. Existing direct/service/Mesh diagnostics remain separate;
diagnostic `working-set watch` retains its 60-second bound.

## State and presentation rules

Preserve exact `hostScope/provider/namespace/nativeIdKind/nativeId`, with the
configured source as provenance. Labels, paths, project keys and thread-tree
roots are metadata. Duplicate full-identity claims block every claimant rather
than choosing by arrival order. Native observation semantics remain in
[observation boundaries](../reference/observation.md).

- Membership, runtime and phase are independent. `active` needs an unexpired
  active branch; `recent` means recent membership is proved while active is not
  currently proved. A retained running value cannot establish active membership.
  Uncertain/nonmember outcomes come from the public facade, never local guesses.
- Runtime is running/parked/unknown; running phase is working/waiting/blocked/
  unknown. Native idle means running/waiting. Parked requires positive native
  evidence. Waiting alone does not mean a response is required. Expired facts
  become qualified unknown; last-known values remain explicitly noncurrent.
- Source health and unfiltered counts survive filtering, hidden kinds and empty
  results. `complete-empty` requires current admitted baselines, complete
  unexpired scopes and no members, uncertainty or known nonmembers across all
  watched sources. Zero matches, missing scopes and unavailable feeds cannot
  establish it. Only known nonmembers means zero qualifying members, not empty.
- Default presentation hides confirmed child/system kinds, retaining unknown
  kinds. Membership/runtime/phase/query selectors OR within a dimension and AND
  across dimensions. Nonmembers require explicit inclusion; exact inspection
  can still resolve them. Default ordering is active, recent, uncertain, then
  current native activity descending and full identity as tie-breaker.
- Search is a case-insensitive literal substring over admitted name, project,
  reported cwd, host/home and full native ID; queries are 1–256 characters.
  Dashboard search also includes sanitized current repository root/commonDir/
  relativePath. Expired repository fields stop matching independently of other
  metadata. Finite CLI query results and terminal JSON v1 remain unchanged.
- Reported title/cwd have no independent field lease and imply no fresh native
  sample. Optional repository/project metadata uses workspace support; linked
  worktrees remain distinct. No filesystem/Git discovery, branch/dirty queries,
  content search or persisted search history is performed.
- Activity uses native `activity.at`. Approximate display age is not evidence
  renewal, membership arithmetic or phase-entry time. Polls, title changes and
  transport heartbeats do not advance it; reconnect does not repair native
  clock uncertainty.

The dashboard initially shows the full list with details closed. At 80x24 it
uses single-line rows; at 140 columns it adds Repo and separate runtime/phase
columns. Enter opens split details at 120x30 or larger, otherwise a separate
view. At least 60x16 supports compact rows; smaller terminals show guidance,
overall health and help/quit. Source health remains visible in panels and
filtered views. The [dashboard guide](../guides/dashboard.md#read-and-navigate)
owns the key reference and layout explanation.

Selection follows the exact identity through reorder, filtering, paging and
resize. A hidden selection stays pinned. If evidence disappears or its source
is revoked, retain only its identity and sanitized label, marked unavailable;
discard old facts. Fresh evidence for that identity can restore it. Background
updates never select a neighbor. Search input owns printable q/j/k; Escape
restores the pre-edit query. Search edits debounce at 150 ms. Clearing selection
on the main list does not reset filters.

Metadata remains literal: escape terminal/bidi controls and disable markup,
automatic links, clipboard and URL actions. Color and standard glyphs supplement
state words; no special font is required. Nonempty `NO_COLOR` overrides color
settings. Piped finite text has no color/control sequences, pager or truncation.

## Configuration and role ownership

The private version-1 consumer file is
`$XDG_CONFIG_HOME/agent-observer/terminal.toml`, falling back to
`~/.config/agent-observer/terminal.toml`; `--config` selects another file.
Validate before I/O: owner-private readable regular file, no final symlink,
64 KiB maximum, exact keys, bounded IDs/labels, namespace and absolute socket.
Require unique source IDs, host/home pairs and host/Mesh-source routes.

Resolve `default_sources` unless explicit source/host/home selectors choose
other configured entries. Unknown selectors or zero selection fail. Check every
scope and identity against the expected host/provider/namespace before assigning
a home label. A mismatch blocks and revokes; a publisher restart cannot silently
adopt another home. Single-source socket/window overrides are diagnostic only;
socket override requires local scope and the window must match the publisher.
Ambient `CODEX_HOME` never redirects a cached source.

Configuration is frozen during the invocation. Dashboard in-app source/host/home
filters change presentation, retaining the watched set and coverage denominator.
Retry uses the same binding without reloading config or adopting a new namespace.
Restart with explicit selectors/configuration to change the watched set. There
is no automatic host/home discovery, route creation or configuration writing.

Product reads require the public working-set facade and optional Mesh dependency,
even for a local bridge; published recipes pair the reader with Mesh a25.
Core and Service 4 diagnostics import neither Mesh nor Textual. The dashboard
extra is optional; its qualified framework is Textual 8.2.8. Published dependency constraints are linked from
[operations](operations.md#dashboard-reader-release).

The independent CLI/dashboard reader selection does not advance collectors,
working-set/full publishers, hardware dashboards, Agent Plus or Tmux. Readers
never start providers/services, control conversations, send alerts or fall back
to a full inventory. Existing directional Mesh authority owns remote access.

## Read lifecycle

Finite reads wait for each source's first settled result or a shared ten-second
deadline (`--timeout` 1–60), then freeze per-source capture clocks and close all
streams. Recheck expiry while waiting for slower sources. Report generation and
cleanup renew nothing; exported deadlines are not a continuing lease transfer.
A finite fleet report is not an atomic snapshot.

The persistent supervisor owns one attempt per source: profile, configured
reader, request ID, guard, pending read and receiving-clock binding. Views own
no streams. Keep `report_routes=False` and the existing proof cadence. On the
first failure/gap/resync, revoke current positives, retire that attempt and join
owned cleanup before retry; healthy siblings continue independently. Avoid
simultaneous SDK and product retry supervisors.

Retries use 1, 2, 4, 8, 16, then 30 seconds, jittered to 80–100%; reset after
60 seconds of stable admitted delivery. Permit four concurrent setups and at
most one new start per second, including manual retries. Attempt timeout starts
after start scheduling and covers setup through settled baseline: default
15 seconds, `--connect-timeout` 1–60. Binding/namespace/contract/identity/capacity
faults block for inspection/manual retry. Retry never repairs a native source.

Increment a source epoch on revocation and require a fresh admitted baseline
before restoring positives. Keep one coalesced dirty notification and the latest
state per source; stale tasks/projections cannot restore older authority. Recheck
the projection before paint and after scheduling stalls or resume. Revalidate a
changed receiving clock/domain; wall time alone renews nothing.

Schedule quiet expiry from public receiving member/branch/field, scope and
receipt deadlines, without reproducing producer arithmetic or issuing extra
native samples. Unchanged heartbeats do not rebuild the report. Crossed leases
and revoked epochs bypass cosmetic throttling; visible withdrawal must occur
within 250 ms on a draining terminal, including event-loop delays.

The [sessions guide](../guides/sessions-cli.md#pipes-json-and-exits) owns finite
exit meanings. Dashboard quit returns 0 regardless of source health; setup errors
return 2, internal/output/cleanup failure 3, hangup 129, interrupt 130 and
termination 143, after owned cleanup. Feed failures remain visible in the app.

## Output, cleanup and resource budgets

Validate interactive stdin/stdout/stderr on the same cursor-capable Linux
terminal before reads or raw mode; reject pipes and `TERM=dumb` with finite-CLI
guidance. The outer runner owns reads and joins cleanup independently of the
framework's widget lifetime. Repeated cancellation cannot interrupt owned joins.
Timeout is failure evidence, never permission to abandon a live owned handle.

The bounded Linux driver uses the framework extension point and preserves
input/resize/job-control/termios ownership. Preserve encoded FIFO byte order and
inherited descriptor flags; coalesce models before encoding, not terminal diffs
after encoding. On output failure, revoke reads and restore terminal flags
independently of screen-reset delivery. A stopped sink cannot receive a reset
or visible revocation; record that distinction explicitly.

| Boundary | Budget and required proof |
| --- | --- |
| Admission | At most eight sources, 4,096 outcomes/source, 8,192 total and 32 MiB encoded admitted payload. Defaults reserve 1,024 identities/4 MiB per source before I/O. Capacity faults block the affected source, never silently truncate. These are safety bounds, not fleet capacity or peak-RSS guarantees. |
| UI/state | At most four cosmetic paints/second, one age update/second and 200 materialized list rows/page. Filtering/counts span all admitted outcomes. One pending read/source; bounded latest state, no event history or session disk cache. |
| Output | At most 512 KiB pending encoded output and per accepted write; fail after two seconds without drain progress. No blocked event-loop queue put or unbounded writer join. |
| Normal resource profile | Three sources x100 identities, draining 120x40 terminal, two-minute warmup and 30 measured minutes. Client plus owned children <=5% of one core and <=192 MiB RSS; report producer/sampler cost separately. |
| Interaction | Normal key/resize-to-visible p95 <=100 ms; admitted-update-to-visible p95 <=250 ms at its recorded boundary. Test 120x40, 80x24, 60x16 and 40x10 guidance. |
| Recovery | Source/warming UI within 500 ms; controlled available baseline within five seconds of an attempt, plus start queue/backoff. Fresh baseline and healthy siblings required. Verify quiet expiry, receiving-clock changes, job control and 100 controlled disconnect/recovery cycles without resource growth. |
| Shutdown | Terminal flags restored within two seconds and all owned cleanup joined within five. Preserve unrelated native sessions, services and processes. Measure delivered screen reset separately. |
| Practical preview | Twenty-second installed-dashboard check over the actual configured cached fleet: current projection/counts/source health, clean quit and terminal restoration. Supplement with controlled update/input/expiry/recovery checks. This is not sustained-performance or native-accuracy proof. |

Source checks require both optional stacks with
`./scripts/check --require-working-set-mesh --require-dashboard`. Package matrices
cover core-only, Mesh-only, dashboard-only and paired installs on Python 3.11
and 3.14. Core/help/schema/config inspection stays lazy; a dashboard-only install
must explain missing Mesh before I/O. Check packaged code, schema and stylesheet
outside the source tree. Use owned cached fixtures and metadata-only native
comparisons under [validation](validation.md), preserving ordinary providers.

## Qualification and limits

The a14 [manifest](../../artifacts/observer-0.7.0a14.json) and public
[provenance](https://github.com/byebyebryan/agent-observer/releases/download/v0.7.0a14/provenance.json)
bind runtime source, wheel, dependency stack, exact-head CI and source/installed
checks. The CLI/dashboard reader was delivered to Snap, Starship and Carbon;
[operations](operations.md) separates managed selections from publication.
Reader delivery does not close separate producer incidents or establish human,
full native/remote, resource or physical-device acceptance.

Sustained resource/native evidence retains its original source-preview boundary:
source `d57233313f01983361b75fb0953662afa212c513`, wheel SHA256
`fd8ec13ee37470d1e31788df399057ba371eeaad67d412087993eb75995c55f0`
with unreleased a12 metadata. Its fixed normal profile measured 4.88%/4.74%
of one core and 65.17/66.60 MiB peak RSS on Python 3.11/3.14. Later a13/a14
UI/search and package/delivery checks do not claim new sustained runs.
Selected local native comparisons cover only their exact identities/intervals;
agreement with another Observer command is cached-consumer evidence.

The [frozen qualification record](https://github.com/byebyebryan/agent-observer/blob/7dbcd611f7b0ecfbebf7b2e8053963fb25915999/docs/maintenance/terminal-product.md#resource-and-installed-qualification-baseline-t9)
retains detailed measurements, artifact bounds and earlier failures. Prior CPU
and task-minimum failures remain failed; the optional eight-hour soak stopped
after about 3.6 measured hours and remains incomplete. Eight-source/8,192-outcome
reader-only stress runs never reached complete coverage and do not establish
usable dashboard capacity or an exact timeout cause. The user deferred extended
soak, stress qualification and read-path optimization in favor of the practical
preview. Reopen conditions belong to the [roadmap](roadmap.md#deferred-work-and-reopen-conditions).

Completed planning, feasibility and implementation checkpoints remain
[in Git](https://github.com/byebyebryan/agent-observer/blob/7dbcd611f7b0ecfbebf7b2e8053963fb25915999/docs/maintenance/terminal-product.md),
not as additional maintained contracts or current deployment instructions.
