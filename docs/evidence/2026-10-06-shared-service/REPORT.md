# Shared observation service design validation

Date: 2026-10-06. Scope: reviewed proposal, passive measurement, source audit,
primary research and controlled design exercises. No service implementation,
installed service, new provider subscription, hook registration or downstream
migration is accepted here.

## Artifact and provenance

Measurements used the existing independently accepted `0.3.0a2` candidate,
observation wire 3 / API 1, installed at
`/home/bryan/.local/share/agent-observer/0.3.0a2-98ce1f9203f97c13`
on Snap and Starship. Its source is
`7ffbe246e6bac2c9d320328ce639b833b3a73bfa`; wheel SHA-256 is
`98ce1f9203f97c13adc2d19cb11bf8f13a0dc3889fc899debc94da1bf0b1430d`.
See the [a2 acceptance report](../2026-10-06-stable-api/REPORT.md).
The current source audit started from `25731dc`; initial design capture was
committed as `9f0a4ab`. Production modules remain unchanged in this pass.

Installed public CLI measurements were separate processes, with three reads
per single-provider case and two combined reads on Snap. Starship measurement
ran on Starship through SSH; reported timing/CPU is measured inside that host
and excludes the SSH startup. Claude is measured only on Snap. This is ordinary
passive observation through accepted adapters, not an independent native census
or new service passivity proof. No provider settings/actions were requested.

## Retained evidence

| File | What it establishes | Limit |
| --- | --- | --- |
| [measurement-snap.json](measurement-snap.json) | Eight existing CLI timing/CPU/bytes/count/coverage samples | Small ordinary workload; no percentile, idle or maximum-load claim |
| [measurement-starship.json](measurement-starship.json) | Three Codex CLI samples on that host | Does not prove Claude or remote streaming |
| [profile-snap.json](profile-snap.json) | Function counts/timing for one read per provider | Profiling overhead; not future warm-service cost |
| [controlled-result.json](controlled-result.json) | 33 named fixture/model/Unix-socket assertions | No actual service scheduler, fan-out, native events or physical wake |
| [verification.json](verification.json) | Final repository/syntax/metadata checks | Does not establish service/native acceptance |
| [measure_direct.py](measure_direct.py) | Reproducible bounded timing collection | Reruns perform passive reads of then-current ordinary stores |
| [profile_direct.py](profile_direct.py) | Reproducible candidate CLI profile | Reruns perform passive reads on Snap |
| [controlled_review.py](controlled_review.py) | Reproducible fixture/models and disposable local IPC | No provider reads; internal watch inspected as implementation evidence |

Only aggregate metadata, source coverage/reason codes, executable hashes and
static function timing/counts are retained. Native/public snapshot rows were
parsed transiently in memory, then omitted. No credentials, prompts, responses,
tool content, callbacks, terminal captures or raw provider payloads are persisted.

## Measurement results

Snap's full two-provider reads took 2.3818 and 2.3634 seconds, consuming 1.4123
and 1.4168 child CPU-seconds. Their documents were 134,315 bytes with 83 rows.
Single-provider ranges were Codex 1.2805–1.3321 seconds and Claude
1.1414–1.2379 seconds. Starship's Codex reads took 1.7304–1.8465 seconds with
96 rows and 150,985 bytes. CPU includes waited child descendants; OS cache state
was uncontrolled. Runtime counts and coverage are Observer observations only,
not independently confirmed active-session counts.

Codex coverage was current/complete in this sampled context. Claude runtime
coverage was current/complete, while saved coverage remained partial. Sharing
does not remove that source limitation or expand the accepted absence predicate.
Actual runtime binary hashes are diagnostics, not supported-release allowlists.

The Snap profile identifies saved inventory/history, artifact hashing and
quadratic duplicate identity comparison as cost centers. The
[review](../../shared-observation-service-review.md) explains the resulting
cadence/provenance/optimization requirements. No optimization is implemented by
this report and no measurement is presented as a service performance guarantee.

## Controlled checks and exclusions

Existing API v1 fixtures prove strict rejection of new fields, unchanged cached
clocks, heartbeat behavior, explicit gap/resync, retention of original stale
activity and watch restart epochs. Tiny exhaustive interleavings expose the
capture-then-register lost update and validate the atomic transaction model.
Deterministic models cover immutable partial frames, pending coalescing, dirty
generations and changed-context rejection. Fake elapsed clocks expose the
suspend-expiry rule; only clock availability is checked on the actual host.

Disposable private pathname sockets establish actual Linux peer-UID retrieval
and permission checks. A socketpair exercise decodes fragmented newline frames,
reaches nonblocking backpressure and keeps an independent socket usable. This
does not exercise a real service fan-out or prove its fairness/deadlines/memory.
All temporary sockets/directories were closed and removed.

The frame-size exercise is arithmetic only, not a schema-valid maximum-frame
test. Scheduler models are design witnesses, not production implementations.
Physical suspend, native subscriptions, sustained source load, provider/service
lifetime effects, actual fan-out, installed user-unit context, remote transport,
frontend/device input and physical display remain future acceptance gates.

## Reproduction

Run these explicitly; they do not select any normal artifact or start a provider:

```sh
python docs/evidence/2026-10-06-shared-service/measure_direct.py snap
ssh starship python - starship < docs/evidence/2026-10-06-shared-service/measure_direct.py
/home/bryan/.local/share/agent-observer/0.3.0a2-98ce1f9203f97c13/bin/python -I -B docs/evidence/2026-10-06-shared-service/profile_direct.py
/home/bryan/.local/share/agent-observer/0.3.0a2-98ce1f9203f97c13/bin/python -I -B docs/evidence/2026-10-06-shared-service/controlled_review.py
```

The retained scripts format the original timing/profile procedure for readability;
the receipts preserve its original numeric results. The controlled receipt was
generated by the retained controlled script through the accepted a2 Python.
Future reruns are new observations, not byte-for-byte expected results.

## Outcome

The design is ready for the [bounded implementation sequence](../../shared-observation-service-execution-plan.md),
subject to its independent gates. API v1 and existing installed selections remain
unchanged. Shared polling supplies first-class local push without requiring new
provider subscriptions; efficient scheduling, service safety and consumer timing
gaps have explicit follow-up proof requirements.
