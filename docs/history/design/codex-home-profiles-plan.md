# Codex home profiles: implementation and delivery plan

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Status: first explicit-home increment implemented and selected, 2026-10-19.
Observer, the public consumer composition and managed routes are in use on Snap
and Starship. Native, consumer, lifecycle, device-outage/recovery and bounded
resource results are recorded in the [home-profile evidence report](../../evidence/2026-10-19-home-profiles/REPORT.md).
The earlier working-set source checkpoint stays closed; delta sync stays dark.
This increment reuses the existing one-home collector and wire contracts.

## Outcome and first checkpoint

Observe explicitly configured Codex homes simultaneously, preserving one real
host identity and each home's separate namespace. With no filter, show the union
of configured profiles; startup and CLI selection can request all or an exact
configured profile. The default/all-profiles preference is resolved and
implemented. Profile labels are presentation metadata. Interactive device
filter controls remain outside this increment.

The first checkpoint is complete: Snap's existing `~/.codex` and
`~/.codex-work` scopes are available together through the public Reader. The
work session `yearly-recap-review` is independently matched and appears as
running/waiting; Snap's default scope remains explicitly empty. Starship's
default profile continues to work. Wrong-home binding, partial-source behavior,
expiry/closure and sibling lifecycle results are in the evidence report.

Use the existing active-plus-recent policy with the reviewed default 72-hour
window. Preserve per-profile full diagnostics and active reads. The dashboard's
current loaded-session presentation remains its own policy; profile composition
does not add parked rows to the panel or restart the deferred delta work.

## Scope and measured starting point

A Codex home profile is a named Observer configuration binding an existing
`CODEX_HOME` to its native endpoint, cached service and delivery route. It is
different from a Codex `-p` configuration overlay. Sessions from overlays sharing
the watched home/daemon are already visible. Exact native overlay-name discovery,
account discovery and remote app-server discovery are separate requirements.

The original passive baseline, before profile selection on 2026-10-19, found:

| Host / home | Native state | Current Observer coverage |
| --- | --- | --- |
| Starship `~/.codex` | 405 rows; 14 running, including seven human roots | Matches; seven active human rows, ten active-plus-recent rows |
| Snap `~/.codex` | No loaded or DB-only catalog rows | Matches this empty scope |
| Snap `~/.codex-work` | One loaded user session, `yearly-recap-review`, working | Outside the configured Observer scope |

This table is the dated pre-change baseline; it is retained as planning
provenance. The private comparison and metadata-only evidence are at
`~/.cache/observer-live-reconcile-20261019T235156Z/REPORT.md` on Starship. These are
dated observations; the post-change comparisons are summarized in the new report.

The initial review inspected Observer `74bc2012`, Mesh `2fb502da`, RLCD
`39d1d07e`, and the managed ChezMoi unit/launcher templates. The implementation
and accepted source/consumer/ops lineage are recorded in the evidence report.

## Implemented first route

The implementation uses one existing Observer collector per configured home,
one cached publisher per profile feed, and reader-side composition of
independently admitted feeds. Existing single-profile native wire contracts and
Mesh descriptors remain unchanged; no combined owner frame is fabricated.

The existing default collector, socket and source IDs remain the default
profile. Snap adds only the extra work-profile collector, publisher and reader
route. The stable IDs are `default` and `work`; labels are presentation metadata
and may change without changing session identity.

| Layer | Preserved contract | Implemented route |
| --- | --- | --- |
| Session identity | Host/provider/namespace/native-kind/native-ID | Same real host; configured homes retain separate namespaces; no `snap-work` host alias |
| Native adapter | One configured home per collection | Existing adapter runs independently once per configured home |
| Collector/service | One home per provider; independent worker and receipt lifetime | Separate owned instances and sockets per configured profile |
| Mesh configuration | Source ID selects an explicit socket; publisher captures that source | Explicit profile source IDs and matching publisher endpoints |
| Managed working-set launcher | Accepts only the selected single source ID | Admits exactly the configured profile routes through trusted factories |
| Reader | One guard/subscription for the selected source across hosts | One guard/subscription per configured route and selected host set |
| RLCD projector | Source dictionary keyed only by host | Compose profile results before producing one host summary |

Mesh's configured factory receives `(host, source, socket)`. Its catalog and
public views require unique real hosts, so additional homes use separate streams,
not duplicate host entries in one stream. The public two-route check passed
without a Mesh SDK or schema change; the Mesh source stayed at `2fb502da`.

An integrated multi-home collector remains a later option if measured process
overhead warrants it. It would require changing provider-keyed scheduling,
receipts, hints and context ownership, plus versioned multi-scope service/feed
contracts and matching Mesh registration. It is outside this first increment.

## Configuration and lifecycle

One private, bounded TOML manifest supplies startup-fixed values. It is a local
Observer configuration, independent of provider and wire versions:

```toml
version = 1
host = "snap"

[profiles.default]
label = "Default"
codex_home = "/home/bryan/.codex"

[profiles.work]
label = "Work"
codex_home = "/home/bryan/.codex-work"
```

The loader requires version 1 and the `default` profile, accepts at most two
profiles, and reads an owner-private, non-symlink regular file up to 64 KiB.
Profile IDs are safe lowercase identifiers; labels are 1–32 printable,
nonblank characters. Configured home strings must be absolute, contain no `..`,
and already use the lexical spelling preserved by `Path` (no redundant separators,
`.` segments or trailing separator except the root). Accepted strings are
preserved for the existing namespace calculation, including symlink spelling;
physical resolution is used only to reject aliases/duplicate homes. This keeps
the route namespace equal to the service CLI's captured home namespace. A missing
home remains independently unavailable and is never created. UID and runtime
root are explicit inputs to the loader.

The manifest records each route once rather than requiring independent
hand-written collector, publisher and client mappings:

| Field | Meaning |
| --- | --- |
| Host and profile ID | Stable local configuration key; profile ID is not provider identity |
| Display label | Optional human name; no credentials or account identifier |
| Codex home | Explicit absolute path to an existing configured home |
| Collector unit/socket | Existing default route or distinct private per-profile route |
| Mesh source and publisher socket | Distinct trusted route IDs/endpoints |
| Configured and selected | Profiles exist by manifest presence; the client selects all or an exact configured-ID subset |

The default route retains `agent-observer.service`, its existing collector
socket, Mesh source `agent_working_set` and its publisher. A profile named
`work` gets `agent-observer-profile-work.service`, its own collector socket and
runtime directory, Mesh source `agent_working_set_work`, publisher unit and
socket. Profile runtime directories are separate, not nested under the default
runtime directory. `agent-observer profiles --config PATH` lists resolved
routes; `--profile ID` selects one configured route and `--json` emits JSON.
This command only reads configuration and derives routes.

All configured working-set profiles use the immutable reviewed 72-hour window.
The selected first increment has two homes on Snap (default/work) and one on
Starship (default). Additional homes are a later scope extension.

- Configuration validation runs before owned helpers start. It rejects
  duplicate profile IDs, duplicate sockets/source IDs and duplicate physical home
  targets. Keep the existing configured-path namespace calculation; aliases and
  labels cannot mint a second identity for the same configured home.
- The default unit/socket/source bindings are preserved. An extra profile gets its
  own private runtime directory, singleton lock and separately stoppable unit.
  The default runtime directory must not own the extra profile's directory;
  stopping the default unit must not remove a live sibling socket.
- Missing homes, missing daemons or unreadable endpoints report that profile as
  unavailable. Never create homes, initialize credentials, scan arbitrary
  directories or auto-start/restart a Codex daemon.
- Restarting an Observer profile affects its own collector/publisher/guard only.
  Native sessions, hooks, clients and daemon settings stay untouched.
- Labels can change freely. Changing a home's binding is an explicit source
  replacement with normal namespace/incarnation retirement, not reuse of the
  previous profile's facts. Removing a profile withdraws its observation scope; it
  does not claim that native sessions ended or became parked.
- Configure the remote home only on hosts where it is intended. A work profile
  absent from Starship's manifest is not a failed Starship source.

## Implemented reader and dashboard composition

The consumer keeps an independent public acquisition/guard for every `(host,
profile, source)` binding. Its Fleet checks the configured home and admitted
namespace against the feed owner context; it rejects a valid native frame bound
to the wrong home. Labels are joined only after this binding succeeds. The
consumer composes profile sources before projection and leaves the base row DTO,
host identity, frozen API 4 session bodies and Mesh frames unchanged. Profile
names are not inferred from cwd/model/title.

Union rows by the complete existing five-part identity. Identical native IDs in
different home namespaces remain distinct. Duplicate exact identities from two
configured routes are configuration conflicts to reject, not newest-row wins.
Each guard retains its original deadlines, receipt support and continuity/clock
watermarks. Reconnection of one stream cannot renew or reset its sibling.

Compose host presentation after per-profile admission and expiry:

- Healthy rows remain usable while another configured profile is unavailable.
  A host-wide minimum expiry must not shorten or renew independent row leases.
- A host is complete/current only when every selected configured profile has
  current complete coverage. A failed or unresolved profile makes the combined
  scope partial; report individual profile health in host-side diagnostics.
- Complete-empty applies only to the exact admitted namespace. Exclusions and
  negative census from one profile cannot remove another profile's rows or
  retained context. An omitted profile is not an empty profile.
- Apply the existing host-level ordering and 32-row device limit after combining
  profile identities. Keep per-row timing/category and exact identity tokens.
- Expose all/one-profile selection through startup/CLI configuration first.
  Selection changes observation scope; do not reinterpret filtered-out rows as
  native negatives. Profile labels can use existing host-side presentation and
  label text. Do not require a firmware wire extension or new device controls.

The original RLCD projector collapsed inputs with `{s.host: s for s in sources}`;
passing two Snap sources directly would have lost one. The consumer now uses
`ProfileFleet`, `combine_sources` and `ProfileProjector` to aggregate after
per-route admission, then projects one composed source per real host. The base
projector and source DTOs remain intact. Public route, filter, wrong-home and
sibling-lifetime results are summarized in the evidence report.

## Completed work sequence and reviewable checkpoints

| Step | Owner / work | Concrete completion |
| --- | --- | --- |
| P0: route proof | Observer integration, using public Mesh seams | Passed public two-route fixtures on one host, including equal native UUIDs in distinct namespaces, independent proofs/lifetimes and consumer wrong-home rejection; no Mesh SDK change |
| P1: named-profile operations | Observer profile config/helpers; managed templates in ChezMoi | Validated manifest, retained default bindings, isolated Snap work collector/publisher, per-profile route listing and no native daemon start |
| P2: composition | RLCD host bridge / optional read CLI | Profile-aware composition, label/filter behavior, expected-home binding and partial/empty/expiry isolation through public readers |
| P3: bounded delivery | Producer and consumer owners | Selected on both hosts; Snap default-empty/work-populated and Starship default parity; outage/recovery, sibling stop/start, readback and short resource sample recorded |

The P0/P1 and P2/P3 checkpoints are complete within the bounds below. They
required no provider/schema work and did not alter the accepted working-set
policy. The evidence report records implementation lineage and live results;
future expansion to more homes or device-side filtering is not implied.

## Acceptance results and limits

The focused acceptance covered the original cases as follows:

1. Same-UUID fixtures remained distinct across namespaces; duplicate physical
   homes/routes and wrong-home consumer bindings were rejected. An empty default
   and populated work feed composed correctly. Complete-empty, expiry and close
   paths affected only their own configured profile.
2. All-profile and exact-profile reads returned the expected routes and labels.
   Actual native evaluation matched Snap default (0 rows), Snap work (1 loaded
   user row) and Starship default (401 native rows; 7 running, comprising 5 user
   and 2 child rows). The selected loaded-user dashboard union contained six
   rows; the default filter contained five and work-only contained one Snap row.
3. Native identity/runtime/phase checks matched the seven Starship running
   references. Two `lastUpdated` comparisons differed within the bracketed
   sampling interval; fields not proved by the native contract remain unknown.
   The evaluator now takes explicit `--codex-home`, defaults to `~/.codex`, and
   checks the same selected home used by its native RPC reference.
4. Three work-profile stop/start cycles left both default feeds current
   and removed only work-profile sockets while stopped. No Codex daemon was
   restarted; independent PID/start-time/executable checks remained unchanged.
5. During a live work-profile outage, the device retained six rows with partial
   health, one uncertain row, three waiting and two working. Recovery restored
   current health with six rows, four waiting, two working and no uncertainty.
   Both boards returned source-admitted six-row ACKs with health 0 and no missed
   frames. These are software ACK/readback checks, not visual or reboot tests.

The bounded host resource window was approximately 30 seconds per sample. The
combined cgroup `MemoryCurrent` maximum changed from 93,757,440 to 139,653,120
bytes; the added work collector/publisher pair peaked at 46,915,584 bytes
(46.9 MB decimal). Aggregate CPU changed from 3.376% to 6.048% of one core in
those windows. This is descriptive process accounting, not RSS, a causal CPU
comparison, a long-term capacity estimate or a claim that existing per-feed
limits apply to the aggregate.

Consumer validation passed 89 tests and 65 documentation checks over 398 files;
managed source/artifact gates passed. The Observer gate recorded 1,178 tests and
257 Markdown checks before the final evaluator-home filtering correction. The
primary owner will rerun the full Observer gate after this documentation handoff.
The evidence report contains artifact/source lineage and evidence boundaries.
No raw native frames, prompts, responses or tool payloads are included here.

## Rollout, rollback and effort

The profile-aware dashboard bundle is selected on Snap and Starship. Snap runs
both its retained default route and the added work route; Starship continues to
use only its configured default home. The exact former profile-less wire3 bundle
`1ad6ef316f2aba74` remains the rollback selection in the managed gate; rollback
would select that bundle and stop only the added Observer collector/publisher.
Rollback was not executed during this pass. No firmware changed and no Codex
restart or session migration occurred.

Rough engineering estimate: P0/P1 about one focused day, P2 one to two days,
P3 about half to one day: roughly two to four focused days overall, with consumer
owner availability affecting elapsed delivery. The earlier one-to-two-day
estimate covered collection/routing; the inspected host-keyed dashboard needs
additional composition work. This is a planning estimate, not a performance or
delivery guarantee. An integrated one-collector/multi-scope redesign is larger
and is not needed to reach this checkpoint.

The first increment is implemented and selected within the reported bounds.
This report does not authorize new providers, additional homes, device controls,
delta sync or broader performance claims.
