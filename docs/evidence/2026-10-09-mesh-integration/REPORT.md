# Mesh state integration acceptance

Date: 2026-10-09. S0–S3 in the [execution plan](../../mesh-integration-plan.md)
are complete. Observer a12 and Mesh a4 are independently packaged, accepted and
selected on Snap and Starship for state-only reading/delivery. Core collection
and normal services remain a11; the writer remains a16. No provider policy,
ordinary provider/session process, notification, attachment or frontend change
is included.

## Exact candidate and source boundary

Observer source `e55825e2843905f9f60ce332f94014f53331987f`, wheel SHA-256
`e292e689a1dd1b32fec1a10617330cf32777c8e347d98512c2c0c3fabfd39568`;
Mesh source `2cc12accb331db7ee65ab426da09576a907b291c`, wheel SHA-256
`55a8ef018e0bab994ce3dd2106552a69fdcb5a397ed607cd9cab92afb51659dd`.
The [Observer manifest](../../../artifacts/observer-0.5.0a12.json) and
[Mesh manifest](../../../artifacts/mesh-0.1.0a4.json) bind both. Prefix on both:
`~/.local/share/agent-observer/0.5.0a12-e292e689a1dd1b32`, with exact wheels,
manifests and verifier in `artifact/`. Snap retains source-only Claude SDK;
Starship retains the core profile. No public release/upload is claimed.

API 2, snapshot/watch 4, service 2 and `agent-observer.mesh-candidate.v1`
remain unchanged. Frozen Mesh lock SHA-256 is
`2b93e1c1e0b533be00e6646ea0ef62aefec357ba00e1e8a51489578ccde38489`.
Mesh gets frame limits from Observer's public service descriptor. Its shared
configured-reader binding disables route reporting by default. Observer never
queries providers through Mesh or implements SSH in core. The conservative
current selector omits unsaved rows with lost runtime authority; raw native rows
and saved metadata remain lossless. Filters/order are human presentation only.

The historical exact-HEAD `--check-sources` gate rejects newer sibling commits.
[Independent digest comparison](current-source-parity.json) matches every
recorded file in all five repositories. Lock/reference inputs are preserved;
historical HEAD equivalence is not claimed.

## Source and immutable package gates

`./scripts/check` passes 406 tests. The normal dependency-free environment
skips two optional Mesh tests and one existing native-only check; the Mesh
environment passes all 406 without skips. Focused lint passes. Tests cover
descriptor/dependency isolation, no provider/action imports, rejection before
dispatch, snapshot/watch admission, output failure and owned stream cleanup,
cross-host urgency/age sorting and presentation-only child filtering.

Mesh lock/schema checks pass (18 inputs, 20 packaged schemas), design 116 and
Delivery 169 checks. The [isolated wheel/core gate](mesh-wheel-core.json) passes
56 tests with neither Observer installed. The
[isolated wheel/native gate](mesh-wheel-native.json) passes all 84 tests using
exact Agent a12 and the accepted Tmux a1 wheel, including owned IPC/SSH fixtures,
catalog replacement, source failure/expiry, concurrency, gap/resync and cleanup.
These are controlled domain fixtures, separate from ordinary native evidence.

The [first full-suite attempt](mesh-wheel-agent-only-attempt.json) omitted the
required optional Tmux producer package; its missing-domain errors are preserved
as rejected harness evidence. The corrected disposable two-domain environment
passes; production reader prefixes do not acquire Tmux dependencies.

[Snap artifact](snap-artifact.json) and [Starship artifact](starship-artifact.json)
verify installed bytes against both exact wheels, entrypoints, pure imports,
unchanged descriptors, dependency consistency and source-only/core profiles
outside source checkouts. Importing Mesh bindings loads no collector/action code.

## Independent native and fleet comparisons

The stdlib native oracle imports no Observer code. `evaluate-mesh` only adapts
the installed Mesh local owner's lossless frame to that oracle's existing CLI
input; native-before/native-after evidence still queries the owning Codex daemon
and authenticated Claude registrations/history. No terminal/client census or
provider action is used.

- [Snap two-round comparison](snap-native.json): 91 Codex and 37 Claude rows;
  all 3 running Codex and 8 running Claude contexts agree on runtime/phase.
  Codex has no comparison issues. Active Claude conversation clocks can advance
  between cache collection and the native bracket; second-scale cache lag and
  sampling races are reported, without rewriting native activity. The known
  setup-only UUID `e0cba9dd-b642-4730-af4b-beb3b7e9c16c` retains unavailable cwd.
- [Starship two-round comparison](starship-native.json): all 354 Codex rows,
  including 6 running contexts, agree in both rounds with no comparison issues.
- Packaged [Snap fleet pull](snap-fleet-pull.json) and
  [Starship fleet pull](starship-fleet-pull.json) are complete. Each remote owner
  has a fresh nonce-bound cached proof and original receipts. Row counts changed
  normally on Snap between samples (128/129); both hosts' scope and identities
  remain attributable. Complete delivery does not upgrade Claude partial coverage.
- [Snap fleet push](snap-fleet-push.json) and
  [Starship fleet push](starship-fleet-push.json) admit ordered pending/partial
  baselines followed by complete views; ReadGuard validates all frames and
  owned reads close after five frames. Ordinary human fleet reads render age,
  shared urgency/activity order, coverage and confirmed-child filtering.

Claude's registration assumption, unsupported old background histories,
unknown clocks/metadata and Codex pre-daemon history limits retain their original
acceptance bounds. Mesh adds no native completeness or event-replay guarantee.

## Scoped operational acceptance

Managed selection lives in chezmoi's separate Observer Mesh tuple. Only five
targets change: read CLI link, Mesh command link, private source descriptor,
Agent bridge unit and its enablement link. Fixed source `agent` reads the owning
`/run/user/1000/agent-observer/read.sock`; the private bridge endpoint is
`/run/user/1000/mesh-plus-agent/read.sock`. Both bridge units are enabled/active.
Existing SSH Plus continues using shared authority a1; its pin/code bytes and
ordinary Tmux services are preserved. Source archives remain immutable.

[Snap bridge recovery](snap-bridge-recovery.json) and
[Starship bridge recovery](starship-bridge-recovery.json) explicitly revoke the
local view during bridge loss and deliver ready resync after restart. Only the
new bridge units are stopped. The production Observer services remain the same
PIDs (`2165818` / `3096121`) with unchanged restart counters.

[Snap rollback/reselection](snap-rollback-reselection.json) and
[Starship rollback/reselection](starship-rollback-reselection.json) restore all
five captured targets, the a11 reader and a ready original cache, then reselect
the reviewed candidate. Forced apply is restricted to targets still matching
the captured baseline or candidate. The first harness needed this explicit
chezmoi changed-file policy; the accepted rerun verifies it before applying.
Protected provider/workspace/service/authority/external-pin hashes and Starship's
unrelated Kitty source change are preserved.

Final [Snap Mesh gate](snap-agent-observer-mesh-operations.json) and
[Starship Mesh gate](starship-agent-observer-mesh-operations.json) accept exact
installed artifacts, five rendered/installed targets, unit syntax/enablement,
live entry/interpreter/incarnation, kernel IPC peer matching the unit and cached
read. Independent [Snap original service gate](snap-agent-observer-operations.json)
and [Starship original service gate](starship-agent-observer-operations.json)
still accept the a11 service/a16 writer and native host scope. Selection never
restarts their provider or collection processes.

## Costs and remaining scope

[Snap bridge samples](snap-resource.json) and
[Starship bridge samples](starship-resource.json) cover one/two local readers on
ordinary active hosts. Five-second windows show roughly 34–39 MiB bridge RSS
and 0.85–1.81 CPU seconds per window, depending on host/update rate. These
exclude reader/SSH/Observer costs and are descriptive, not idle benchmarks or
strict-budget acceptance. Reader-inclusive [Snap](snap-reader-resource.json) and
[Starship](starship-reader-resource.json) samples show about 34–38 MiB per CLI
reader, including cold startup. Aggregate reader CPU ranges from 0.58 to 1.92
seconds per five-second window. Sustained idle/fleet CPU attribution is unproved.
Multiple readers still own independent connections/validation; a shared fleet
broker/pool is deferred. Profile sustained whole-fleet costs before adding one.

Public package publication, downstream adoption, physical suspend, device/GUI
acceptance, native occurrence events and alert normalization remain separate.
The observation and Mesh state contracts are ready for independent consumers;
future client work should use the [CLI/SDK guide](../../mesh-read-client.md)
and preserve native coverage, receipts, raw reconstruction and expiry rules.
