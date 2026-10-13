# Native timing producer checkpoint

2026-10-12. C0–C3 of the [execution plan](../../native-timing-execution.md),
against the immutable [Observer 0.6.0a1](../../../artifacts/observer-0.6.0a1.json)
core/local-read wheel from `280ddab6e8f8a28fa92e08461a4888e0a504d4ca`.
API 3, snapshot/watch 5 and Service 3 are implemented. The following Mesh owner
extension uses a separate a2 artifact; no networking/normal role selection is
accepted by this producer checkpoint.

## Scope and exact inputs

The [input receipt](inputs.json) records the wheel and private controlled-harness
digests. Fresh tracked-source export, installed wheel byte/schema verification
and independent jsonschema CLI admission pass. No removed Claude modules,
Claude SDK or provider binary is packaged. Historical wire-4 fixtures retain
their hashes; current wire-5 parsers reject old inputs. The writer remains
independently selected and unchanged.

The local gate passes 395 tests, including 18 new timing normalization/engine/
cache/clock cases, with 24 optional Mesh cases excluded from the Mesh-free gate.
The subsequent Mesh-capable source gate passes all 395 under its explicit new
profile; that is source integration, not immutable networking acceptance.

## Ordinary CLI versus independent native evidence

| Host | Two ordinary rounds | Stable runtime/phase comparisons | Native update / latest-turn comparisons | Limits |
| --- | --- | --- | --- | --- |
| Snap | 97 rows each; 5 running | 194 / 194 match | 193 update, 120 nonempty latest turns match | One moving update-clock sampling race |
| Starship | 387 rows each; 7 running | 774 / 774 match | 768 update, 272 nonempty latest turns match | Three unsaved creation-clock races each round; 46 older unknown kinds |

See [Snap](snap-ordinary.json) and [Starship](starship-ordinary.json).
The stdlib oracle authenticates the ordinary Unix daemon independently of
Observer, reads metadata-only native RPCs and brackets the installed public CLI.
There are no stable mismatches. Null clocks are counted separately, rather than
as proved event times. Unsaved native timing remains unsupported. The separate
Snap observation contains 37 positively saved known-empty latest-turn records.
Existing activity ordering/filtering/exact-reference CLI checks pass.

These are dated bounded ordinary inventories, not exhaustive provider coverage.
Native versions/hashes are diagnostic inputs, not support allowlists. No TUI,
tmux or window inventory participates in classification or timing.

## Controlled native and cached delivery

Both hosts run real Codex `0.162.1` under copied, private owned binary/config/
Unix endpoints with a deterministic local HTTP Responses stub. Each passes
19 installed CLI/native samples: held working, repeat working, approval/question
blocked, repeated blocking, blocked recovery, completed and interrupted turns,
quiet reads and metadata operations. Native turn start remains stable through
blocking; interruption is cancelled. An initial unsaved empty thread stays
timing-unproved. Each sequence uses six local stub requests and zero paid model
requests. See [Snap](snap-controlled.json) and [Starship](starship-controlled.json).

The following owned restart proves positive saved `notLoaded` as parked, with
the previous native turn retained. A local HTTP 400 proves a failed native turn.
Direct, cached pull and pushed timing agree under original receipts on each
host: [Snap](snap-parked-failed.json), [Starship](starship-parked-failed.json).
All owned processes retire. Ordinary provider actions remain zero.

The first failure probe incorrectly expected waiting after a native failure.
Codex actually reports `systemError`; Observer preserves running disposition,
failed outcome and timing while phase stays unknown. The corrected probe checks
that native meaning. Missing/malformed boundaries, equal-order conflict and
non-atomic read races have production synthetic/controlled-transport checks;
they are not attributed to a live native case that did not expose them.

Separate 60-second installed owned services on ordinary endpoints pass cached
pull, three independent pushed readers, slow-reader isolation and cleanup:
[Snap](snap-owned-service.json), [Starship](starship-owned-service.json).
Snap's measured service/helpers are 3.02% of one core, with 100 cached reads and
69.3 MB peak aggregate RSS. This short startup/subscriber observation is neither
a causal baseline improvement nor the sustained managed resource gate.

## Data cost, preservation and remaining gates

The [same-observation byte analysis](size.json) attributes 42,441 extra bytes
to timing in a 97-row Snap snapshot: 155,822 bytes versus 113,381 without the
extension. This is serialization attribution, not a runtime converter or a
matched fleet-performance claim. No new provider RPC, transcript scan, collector
or normal polling cadence is introduced.

[Preservation](preservation.json) confirms ordinary configs, selected commands,
shared Mesh controls and ordinary service incarnations unchanged on both hosts
during the native pass. Controlled fixtures never use ordinary sessions/auth.

C4 exact successor Mesh owner/package/fleet acceptance, C5 sustained resources,
scoped rollback/selection and C6 consumer handoff remain following gates.
Approximate phase tracking, attachment/actions, alerts, new providers, physical
display acceptance, suspend and post-TUI-closure lifetime remain outside scope.
