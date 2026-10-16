# Observer owned admission and selected-read acceptance

2026-10-15. **Observer producer accepted for independently pinned integration.**
No production rollout, RLCD/Mesh implementation, provider action or device gate
is included. Normal collectors, readers, publishers and historical writer retain
their previous selections. Snap native coverage in this checkpoint is explicitly
empty-source coverage; populated native state is proved on Starship.

## Exact artifacts and API

Runtime source: `fefa52d9f1fc850753cc72292c37dae78fa1c112`, branch
`cpu-prepared-admission`, based on clean `f313d81`. Starship had already been
reconciled to that accepted base when inspected. The
[manifest](../../../artifacts/observer-0.7.0a6.json) freezes Observer 0.7.0a6:

```text
/home/bryan/code/agent-observer/dist/private/0.7.0a6-fefa52d-e01a7129/agent_observer-0.7.0a6-py3-none-any.whl
SHA256 e01a712934a1c13aaf5dca011321ce62e9cadd6abf2d4b89bd263f57a56e8125
```

Python >=3.11 is retained. Core has no dependencies; optional `mesh` requires
Mesh >=0.1.0a22,<0.2 and explicit admission/selection/preparation capabilities 1.
The independently accepted [Mesh handoff](mesh-handoff.json) binds source
`f1ced05a09124e7eaafb303c8a818301da393824` / evidence `f773154` to wheel SHA-256
`5ac484d7dcb3f60665a66b5b6dcff780a967afa1d24a8c092800a430399f3314`.
The qualification archive retains both exact wheels, manifests, frozen lock and
verifiers. Prior artifacts are retained. No hosted release is created.

[Wheel/source comparison](wheel-source.json) proves all 55 packaged module/schema
files equal the frozen source, without retired/extra files. Exact installed
bytes, entrypoints, schemas, lazy factory and lock checks pass on
[Starship](installed-artifact.json) and [Snap](snap-artifact.json).
An isolated Starship [publisher-role verification](isolated-publisher-artifact.json)
also checks the owner launcher. The qualification prefixes are disposable and
are not selected by any normal entrypoint or unit.

The [supported facade](../../prepared-agent-read-interface.md) is read interface
2. API 4, snapshot/watch 6, Service 4, Agent profile v3, SDK 1 and preparation 1
retain their meanings. The machine-readable [handoff](handoff.json) supplies exact
usage and dependency descriptors.

- `AgentCodec.admit_bridge(payload) -> NativeState` checks native host/source
  binding and performs one complete Service 4/native validation. Mesh still
  checks its envelope, capacity, native round-trip, clock, digest, chronology,
  nonce and proof/receipt arithmetic. Standalone mutable-input callbacks stay
  strict. No cross-call success cache is added.
- `PreparedAgentWatch.accept` accepts strict raw frames or owned replacements
  from `Reader.execute_admitted` / `watch_admitted`. Reader and helper must share
  the exact AgentProfile instance. Context uses Mesh's supported header-only
  export and never exports raw bodies solely for metadata.
- Explicit immutable `AgentSelection` filters providers, kinds, runtime values
  and runtime health. Selected reads return full matching records plus frozen
  full-identity/kind/runtime summaries for **every current record**. This includes
  rejected rows beyond any consumer display prefix. Default reads retain all
  current bodies. No display cap, identity hash, ranking, inferred classification,
  failure/retry presentation or device policy is added.

Both selected bodies and summaries obey the original per-record component and
delivery expiry. Partial-host retention, full raw export, mutation isolation,
heartbeat, gap/resync and disconnect remain independently checked. Missing or
unselected identities do not become positive retirement facts.

## Correctness and native evidence

The [validation ledger](validation.json) and compressed logs separate source,
immutable installed and native evidence:

| Gate | Result |
| --- | --- |
| Source with Mesh, Python 3.14.8 | 434 tests, zero skips |
| Source with exact Mesh a22 wheel, Python 3.11.17 | 434 tests, zero skips |
| Mesh-free `./scripts/check` | 434 tests, 43 expected optional skips |
| Installed affected tests from `/tmp`, Python 3.14 / 3.11 | 26 each, zero skips |
| Installed Agent profile/network conformance, each host | 7 + 10 cases, zero skips |

Tests cover complete identity and summary retention beyond 32 rows, unknown-kind
running inclusion, current parked/child/system facts, independent expiry and
partial hosts. They also prove lossless failed-outcome/latest-turn retry fields,
strict raw mutation rejection, no rejected-body decoding on warm reads,
heartbeat/gap/resync, capability/clock failures and owned IPC cleanup.

[Starship direct](starship-native-direct.json) brackets the installed public CLI
with an independent stdlib native RPC oracle: all 395 identities, runtime, phase,
native IDs and supported clocks agree over two rounds. Activity is proved for
147 rows; 248 older clocks and 46 older kinds remain explicitly unproved.
The native daemon is 0.163.0, authenticated by endpoint/UID/incarnation and the
diagnostic image hash recorded in the receipt; it is not version-allowlisted.

[Starship cached Mesh](starship-native-mesh.json) preserves membership, runtime,
phase and activity across all 395 rows. Its native thread-update timestamps lag
the contemporaneous native oracle by **9–26 seconds** on two/three changing rows.
The raw mismatches are retained. These are sampled cache timestamps within the
original receipts, not exact current native-update or phase-entry clocks.

[Snap direct](snap-native-direct.json) and [Snap cached Mesh](snap-native-mesh.json)
independently find zero rows from the existing 0.163.0 daemon, with no RPC gaps.
The [old a5 direct and service readers](snap-baseline-empty.json) also return
zero from that exact native incarnation. This proves current empty-source
agreement and transport, **not populated Snap runtime/classification coverage**.
No daemon/session/provider repair is inferred or attempted by this CPU checkpoint.

Installed owned/selected fleet watches run from [Starship](starship-selected-cached.json)
and [Snap](snap-selected-cached.json), each for 30 seconds. Complete raw exports,
selected records and all current identity summaries match strict full reads.
The populated Starship roster supplies 395 summaries and eight selected records;
the current Snap source is empty. These comparisons prove facade parity;
independent native completeness comes from the separate oracle receipts above.
Both actual cached publisher factories pass owned IPC and fixed SSH on
[Starship](starship-cached-publisher.json) and [Snap](snap-cached-publisher.json),
with no forbidden collector imports and zero channels after cleanup.

## Fixed-work CPU comparison

The [performance summary](performance.json) and [serial trial order](cost/order.json)
retain twenty fresh-process runs, two per variant in each ABBA group, through
the exact installed a5/a20 baseline and a6/a22 candidate. No source override is
used. Fixtures, warm-up and ordinary acquisition are excluded. Each composition
case processes 15 changed views with four reads per view; its full-record and
whole-current-roster summary signature agrees exactly across variants.

| Fixed synthetic case | Baseline mean | Candidate mean | CPU reduction |
| --- | ---: | ---: | ---: |
| 100 records: old pair/full read vs new pair/owned selected | 885.48 ms | 728.37 ms | 17.74% |
| 500 records: old pair/full read vs new pair/owned selected | 4253.08 ms | 3334.31 ms | 21.60% |
| 500 records, new pair: owned full read vs owned selected | 3548.51 ms | 3352.88 ms | 5.51% |
| 500 records, new pair: strict raw vs owned full read | 4114.49 ms | 3554.78 ms | 13.60% |
| 20 Reader-side generic native bridge admissions, 250 records | 658.66 ms | 380.98 ms | 42.16% |

The 500-row old/new pair admits aggregates 30/15 times and validates native
snapshots 60/30 times. Native bridge operations validate 40/20 times; ordinary
Client admission remains a separate strict boundary outside that operation.
Selected cases retain 30,000 current summaries and 240 full selected records
over sixty reads. Generation classification still visits the entire roster once;
no history truncation or collection slowdown supplies these savings. Context-only
access removes the old 7,500 raw context-row decodes for this 15-view shape.
The percentages describe separate operations and must not be added.

These are CPU milliseconds of exact synthetic work, not managed-service percent,
live application A/B, total fleet cost or device acceptance. Source/provider,
publisher acquisition, SSH/server, collection and serial/rendering costs are
excluded. Ordinary host activity/frequency remain uncontrolled, and two samples
per variant are not a confidence interval. RLCD owns its subsequent pinned
application parity, live CPU and device/feed validation.

A separate [post-change cProfile diagnostic](post-profile.json), including setup
and warm-up, still places generic bounded traversal/schema admission and native
shape checks above JSON encoding: the leading exclusive functions are Mesh tree
traversal 1.04s, Observer shape validation 0.81s and jsonschema descent 0.56s,
versus JSON encoding 0.23s. Profiler timing is perturbed and is excluded from all
ABBA results. This checkpoint retains the existing schema validator; further
schema work needs its own measured, independently checked change. Serialization
is not the leading residual cost. Fresh untrusted bodies still receive complete
required checks.

## Cleanup, rollback and readiness

The [protected-state readback](protected-state.json) matches normal local unit
PIDs, births, restart counts and selected links before/after this work. All owned
watchers, source channels, fixture servers and benchmark processes close.
Private qualification environments and immutable archives remain for review.
No provider action, service restart, production package/link/endpoint change,
RLCD/Mesh source edit, Tmux control, historical writer or hardware change occurs.
The shared [input ledger](inputs.json) identifies the initial CPU evidence and
independent Mesh acceptance by exact digests.

Observer is ready for independently pinned consumer integration within the stated
native bounds. Production adoption is not selected. There is no operational
change to roll back; a later adopter must retain its exact previous a5/a20
Observer/Mesh/consumer tuple and independently prove rollback and live/device
acceptance. Acquisition/watch-body reuse remains deferred under Mesh's frozen
fresh-correlated-reply contract. No post-TUI-closure, physical-suspend or new
provider capability is certified by this checkpoint.
