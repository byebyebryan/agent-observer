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

## Proposed refinement: a read-only session board

**Planning status, 2026-10-30:** the user adopted an independent, always-on
dashboard beside their normal Codex window. The following defaults are proposed
for review; they are not implemented or part of the a14 release. Native TUI
control and its feasibility spike are deferred.

The product should answer: what are my agents doing, where is the session I
care about, and how trustworthy is this view? Its success criterion is whether
it earns an open terminal during ordinary work. Native Codex continues to own
conversation selection, drafts, prompts and approvals.

### Research and existing seams

The reviewed maintained baseline is
[0d6cff4](https://github.com/byebyebryan/agent-observer/commit/0d6cff4ff7adac7610f67cf6ab0990e5e2eddf45).
It already supplies literal search, filters, exact selection, adaptive details,
paging and source recovery. This pass changes organization rather than adding
another client or read path.

- [Row ordering](../../agent_observer/terminal/model.py) already supports
  activity, label and host. Activity puts membership categories first, then
  current native activity newest first; label is case-insensitive name order;
  host sorts by host/home, then membership/activity. Exact identity breaks ties.
  Host/home grouping is an outer key. Reuse these rules and explain them in
  the existing menus; a configurable multi-column sorter is unnecessary here.
- [Dashboard presentation](../../agent_observer/terminal/dashboard.py) separates
  admitted rows, presentation filtering and rendered pages. Insert favorite
  partitioning after filtering and before paging. Selection follows exact
  identity through reordering; existing "pinned selection" means retained
  inspection focus, independently of the proposed favorites.
- The dashboard renders bounded `SessionLine` widgets rather than `DataTable`.
  Textual documents [stable row keys](https://textual.textualize.io/widgets/data_table/#textual.widgets.DataTable.RowKey)
  across visual movement; keep that identity principle with the current renderer.
  A widget migration or dependency upgrade has no demonstrated benefit.
- htop distinguishes [following a selected process from sorting](https://github.com/htop-dev/htop/blob/main/htop.1.in).
  This supports treating focus and ordering separately; it does not establish
  a persistent-favorites design. Favoriting a row must not change selection.
- The [XDG Base Directory specification](https://specifications.freedesktop.org/basedir/latest/)
  places restartable view/layout state under `XDG_STATE_HOME`. Use that
  boundary for optional display state, keeping source authority in the existing
  private `terminal.toml`.

These are source/design findings. No native session, terminal focus, service,
managed selection or installed package was changed during this planning pass.

### Minimal interaction and layout

Use **Pinned** as the section label and **pin/unpin** for the action. A pin is a
local favorite of one exact identity, with no effect on membership or runtime.

| Interaction | Proposed behavior |
| --- | --- |
| `p` with a visible session selected and list focus | Toggle its pin; append a newly pinned identity to the end of the saved pin order. Keep that exact selection after it moves. |
| `P` outside text input | Open a small Pins panel listing saved identities, including those absent from the current view; `p` removes the focused pin, Escape closes. This supplies removal without needing the session to reappear. |
| Existing `o` / `g` | Reuse the three orderings and host/home grouping. Preview within the menu; Enter/Space accepts, Escape restores the pre-menu choice. Save only an accepted change. |
| Existing Enter, search, filters, details, sources and retry | Retain their current roles. Enter continues to open Observer details. Text input owns printable `p` and `P`. |

The sort/group cancellation rule above is an intentional small refinement:
a14 previews on arrow keys and Escape currently closes without reverting.
Other existing shortcuts and terminal/input ownership remain unchanged.

An illustrative layout with fictional sessions, abbreviated columns and no
claim about live state:

```text
Agent Observer
Sources 2: workstation complete | server partial
Pinned 2 in view / 3 saved | Order activity | Group none
  Pinned
> * Review source recovery   workstation/default   active  running/waiting
  * Refine renderer          server/work           active  running/working
  Other sessions
    Audit release notes      workstation/default   recent  parked
3 matching rows | coverage degraded
p unpin | P pins | Enter details | / search | ? help | q quit
```

Show matching pinned rows first, in first-pinned order. The remaining rows keep
their existing order and grouping; host/home grouping applies within that
remaining region. Pinned rows still show host/home context. Each row appears
once. Without matching pins, preserve the current list layout. Use an ASCII
`*` marker and text, retaining no-color and compact readability.

Pins scroll as part of the existing list. Section/group headings consume the
normal line budget; selection must stay visible through page boundaries and
resize. "Stable" means relative order among matching pins, not reserved screen
coordinates: filters, membership changes and terminal dimensions still affect
what fits. Dynamic status updates never reorder the pinned region.

### Missing sessions, filters and source truth

Pinning never widens the watched set, requests full inventory or bypasses
search, source/host/home filters, kind visibility or identity admission.
Only current admitted matching rows enter the session list. A pin cannot
choose between duplicate claims or authorize a different namespace.

Retain a saved pin when its row leaves the projection. It contributes no
synthetic session row, member count or runtime fact. Show `Pinned N in view /
M saved`; the Pins panel can show an exact reference as `not in this view`.
That phrase alone does not diagnose filtering, deletion, native state or a
source failure. Resolve friendly labels only from the invocation's admitted
metadata; otherwise use host and an abbreviated ID with the full reference
available in the panel. Never match by title, path or ID prefix.

A returning exact identity recovers its existing pin position; a same-name new
identity does not. Source health, unfiltered counts, lease expiry, qualified
unknowns and the current retained-selection behavior remain authoritative.
An unavailable pin or zero visible pins cannot establish a complete empty fleet.

### Remembered view: deliberately small state

Propose one local file,
`$XDG_STATE_HOME/agent-observer/dashboard-view.json`, falling back to
`~/.local/state/agent-observer/dashboard-view.json`. It contains only a format
version, ordered five-field identity references, and accepted sort/group values.
Proposed bounds are 32 unique pins and 64 KiB; reaching a bound gives readable
feedback without evicting a pin. Pins are local-user favorites shared across
invocations on this machine; no cross-machine synchronization, separate board
catalog or per-configuration identity is introduced.

Persist no session labels, paths, source definitions, sockets, observed facts,
searches, filters, selected identity, scroll position or history. Source
selection still comes solely from startup configuration and explicit selectors.
Restart with ordinary filters and the saved order/group. Explicit
`--sort`/`--group` wins over saved state, which wins over current defaults;
startup overrides alone do not rewrite the saved view. Existing filter Reset
continues to reset filters without removing favorites or changing order/group.

Add a dashboard-only `--no-saved-view` escape hatch: skip state-file I/O and use
in-memory pins for that invocation. It also gives fixture/media recipes an
explicit isolation path. Finite CLI commands, help/schema/config inspection
and terminal JSON v1 neither read nor write this file.

Missing state is normal and startup creates nothing. Accept only bounded,
versioned, owner-private regular state; reject a symlink or unsafe destination.
Malformed, unsupported or unreadable existing state is preserved, with one
visible session-only warning and persistence disabled for that invocation.
A failed save keeps the in-memory choice and reports that it was not saved.
Create only the owned application state directory when needed, use private
permissions and atomic replacement, and never repair unrelated directories.

For multiple dashboards, the latest successful explicit edit saves a complete
view; there is no merge, live reload or synchronization. Document this small
last-save-wins behavior. All saves must serialize within one invocation.
Persistence must stay outside projection/paint/lease processing and preserve
the existing terminal and owned-cleanup budgets. A slow or failed filesystem
must not stall freshness withdrawal. This is the main implementation risk:
prove a small bounded save path before UI integration; return a scope decision
if it requires a general worker or settings framework.

### Bounded implementation sequence and acceptance

All implementation belongs in `agent_observer/terminal/` and focused tests.
Keep public report construction, schemas, reader/source policy, producer
packages, other repositories and managed selections unchanged.

| Step | Reviewable outcome and gate |
| --- | --- |
| 1. Pure presentation and state | Test favorite partitioning with every existing sort/group, immutable inputs, exact identity, filter/kind exclusion, missing/returning rows, limits and state-file validation/atomic failure cases. Establish bounded save/cleanup behavior before connecting it to the app. |
| 2. Existing dashboard integration | Add pin actions, the bounded Pins panel, section accounting and remembered sort/group. Test input ownership, menu cancel/accept, selected-row retention, unavailable-pin removal, grouped page boundaries and unsaved-state feedback. Reuse the current renderer. |
| 3. Candidate qualification | Run docs/lint and the full Mesh/dashboard source gate; qualify packaged imports/resources and installed CLI isolation. Exercise missing/corrupt/read-only/unsupported state, two-writer last-save behavior and the no-state flag with disposable roots. Use controlled fixtures for expiry/recovery and terminal cleanup. |
| 4. Ordinary-use decision | Review 140-column, 80x24, 60x16 and tiny guidance layouts, dark/light/no-color, then use one dashboard beside an independently opened Codex TUI. Record whether stable favorites help and whether manual double-navigation dominates. Human usefulness remains an explicit acceptance decision. |

Do not add tests that merely mirror implementation details. Reuse existing
identity, recovery, output and lifecycle cases, adding coverage where the new
ordering or persistence can break them. Keep source, installed, human-use,
release and managed delivery gates separate. No new native accuracy claim,
stress capacity or extended-soak pass follows from this refinement.

The first implementation should prove pin/order behavior in isolation, then
integrate persistence and layout as one bounded candidate. Publication and
deployment require their normal later release decisions; this planning commit
selects no package or role.

### Proposed decisions and scope limit

The adopted direction is the independent read-only companion dashboard.
First-pinned order, the removable-reference Pins panel, the small saved-state
shape and last-save-wins are recommendations from this pass, awaiting review.

Arbitrary row movement, extra sort dimensions, multiple boards, aliases,
persistent filters, notifications and inferred attention/completion states are
deferred until ordinary use identifies a concrete need. Procedural TUI
switching, native-client/window ownership and a coupled sidebar remain deferred.
Reopen native entry only if repeated double-navigation makes this useful
standalone view materially frustrating; it needs its own design and proof.
