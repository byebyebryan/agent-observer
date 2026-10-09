# State/event design research and validation

Date: 2026-10-09. Source baseline `43b8d3e`; study-only scripts and documentation.
Normal installed read/service artifact is `0.5.0a11` on Snap and Starship, with
API 2/read wire 4/Service 2. The writer remains independently selected at a16.
This report accepts a reviewed design and bounded source-feasibility results,
**not** a production event implementation, new public API or managed rollout.

The [design](../../state-and-events-design.md),
[deep review](../../state-and-events-design-review.md),
[execution gates](../../state-and-events-execution-plan.md) and
[research authorization](../../state-and-events-research-plan.md) are the
associated checkpoint. The ESP32-349 handoff is one client's request and does
not settle universal source, filtering, message or transport semantics.

## Method and provenance

Inspect official source interfaces, local implementation boundaries and actual
running provider owners before a controlled source proof. Use `native-isolation`
to establish owned user/mount/PID namespaces, private temporary storage and
ordinary provider-path masks before launch. Existing auth is borrowed only into
the private fixture and removed at cleanup. Native actions create/control only
disposable sessions; no ordinary session is resumed, stopped, renamed or used
as a test prompt target.

The [preflight](provider-preflight.json) records ordinary Codex daemon owners
independently on both hosts: CLI `0.161.0`, running/cached daemon `0.162.1`.
Claude on Snap is `2.1.294`. Native fixture hashes and installed prefixes are
included in source receipts. These are provenance, not a provider support list.

[Harness hashes](study-harness.json) bind copied scripts actually executed.
The native driver uses existing owned PTY/entry helpers to create fixtures;
native RPC/schema/callback facts do not import Observer as their oracle.
Installed public CLI state is a separate comparison. The callbacks are reduced
at collection to allowlisted scalar IDs/enums/clocks; prompts, responses, tool
payloads, terminal output, credentials and raw provider JSON are not retained
in repository evidence.

## Native results

| Receipt | Result | Bound |
| --- | --- | --- |
| [Snap Codex](codex-snap.json) | Two independently completed user-root turns have callback thread/turn IDs matching native RPC and installed running/waiting rows | Private interactive clients; not all callback topologies or terminal outcomes |
| [Starship Codex](codex-starship.json) | The same comparison passes for two roots on the second host | Independent owner/artifact scope; not inferred from Snap |
| Both Codex listeners | Each sees account/thread/status/name methods; neither sees `turn/completed` for targeted turns | Passive initialized connection; no resume/load/start/subscription by observer |
| [Actual daemon schema](daemon-schema.json) | Installed schema includes turn methods and `thread/unsubscribe`, but no passive `thread/subscribe` | Methods existing does not prove their delivery scope |
| [Extra Codex callbacks](codex-callback-classification.json) | Two targeted user-root IDs classify natively; two extra callback IDs have unavailable native detail and remain unknown | Current detail unavailable is not proof of child identity; metadata reads preserve loaded roster |
| [Snap Claude](claude-snap.json) | Two Stop callbacks share a prompt ID, with `stop_hook_active` false/true and intervening parallel-hook continuation | Stop is response-end evidence, not final turn success |
| Snap Claude attention | PermissionRequest precedes a permission Notification by 6017 ms; installed exact UUID is running/blocked; held tool never executed | Specific interactive approval; no general question/elicitation/failure coverage |
| [Claude child callback](claude-child-callback.json) | SubagentStop supplies parent logical UUID plus distinct native actor ID | Actor fact only; it cannot reclassify the parent's state row |
| Snap Claude configuration | These sources work with Agent View and native alerts disabled in isolation | No ordinary Agent View policy change, background compatibility or desktop delivery |

The four root Codex comparisons are:

| Host | Native thread | Independently queried native turn | Native outcome / CLI state |
| --- | --- | --- | --- |
| Snap | `01a12270-9ce0-7f13-bb40-1b986088b771` | `01a12270-d463-72e2-b805-d1c542a1c177` | completed; running/waiting |
| Snap | `01a12270-bace-7390-9ffa-6e6f05a4a6f2` | `01a12270-d658-7262-b8f7-6b728601057d` | completed; running/waiting |
| Starship | `01a12272-d4e9-7003-b4a6-9b79d9609436` | `01a12273-0bbe-79f3-b1a2-908cd728c953` | completed; running/waiting |
| Starship | `01a12272-f255-78a3-8307-9171ab1f5784` | `01a12273-0db3-7801-9c6b-2dc5ca0d16ab` | completed; running/waiting |

The Claude parent UUID is `d847e484-8eae-4bd7-8a8e-93c86aa54033`. Its Stop
correlation remains one prompt across continuation; the child response-end and
permission request are separately observed facts. Native source meanings are
not reconstructed from the installed state snapshots.

The observed absence of Codex turn events is a bounded counterexample to the
proposed global-stream assumption, not proof about every future server build.
Provider contract changes can add a passive capability after focused proof.
The documented start/resume subscription is outside observation authority.

## Synthetic design and callback failures

[Replay model](replay-model.json), reproducible with
`python3 -I -B scripts/study-event-publication-design`, completes 50,000 generated
operations, 19,992 reads, 20,181 admissions and 4,994 publisher restarts.
An independent audit/reference suffix checks the bounded deque under count,
byte and age limits. Nine explicit examples cover scanned-filter progress,
replay boundary, replay receipt identity, empty expired loss floor, epoch fencing,
state-diff incompleteness, prompt correlation, full host/store correlation and
child actor/state independence.

This is a sequential feasibility model. It does not prove real concurrent
replay/live atomicity, Unix transport, production resource limits or native replay.
Those are E2/E4 acceptance gates. Model bounds are deliberately small to force
evictions; they are not the proposed production retention defaults.

[Failure injection](emitter-failures.json) checks the isolated study sink:
invalid JSON, oversized input, unknown event, invalid notify input and a
symlinked output sink all return neutral output/exit, without exception or raw
payload text. Observed process durations are 18–20 ms. Hook output is only `{}`;
notify emits nothing. This validates the study sink's failure path, not a future
production emitter's deadlines, queues, socket authentication or hook selection.

## Current ordinary state comparison

Independent native reads bracket the **installed** a11 public CLI after fixture
cleanup. No Observer source import serves as the reference; read-client checks
exercise exact-reference show, children, urgency/activity order, age and doctor.

| Receipt | Inventory / running | Result |
| --- | --- | --- |
| [Snap](ordinary-snap.json), Codex | 91 rows; 3 running native threads | Membership/runtime/phase and all comparable metadata agree; 38 positively classified children |
| [Starship](ordinary-starship.json), Codex | 354 rows; 6 running native threads | All comparable facts agree; 252 children, 21 accepted older unknown kinds |
| Snap, Claude | 35 saved UUIDs; 6 running contexts | Membership/runtime/phase agree; accepted setup-only cwd omission and one activity sampling race |
| [Claude recheck](ordinary-snap-claude-recheck.json) | Same 35 UUIDs / 6 running | Activity race clears; 33 comparable activity clocks agree; known cwd omission persists |

The cwd omission is the previously accepted setup-only UUID
`e0cba9dd-b642-4730-af4b-beb3b7e9c16c`, documented in the
[a11 report](../2026-10-09-runtime-only-retention/REPORT.md). It is a metadata
limit, not a running/parked mismatch. Two old background Claude histories remain
unknown and outside forward interactive support. Current source coverage and
unproved title/activity/outcome fields remain explicit in the receipts.

This check validates unchanged current observation against native data. It does
not accept an event service, cached event subscriber or downstream notification.
The controlled source tests likewise compare installed state only; production
event publishing is explicitly false in their receipts.

## Cleanup and preservation

[Snap preservation](snap-preservation.json) and
[Starship preservation](starship-preservation.json) confirm exact owned namespace
shutdown and removal of borrowed auth/private native history. The ordinary
Codex daemon PID/birth remains identical to preflight on both hosts; no provider
restart or service selection was needed.

Snap ordinary Codex config, Claude settings and codex-notify helper hashes match
baseline; Starship's ordinary Codex config/helper hashes also match. Snap's
mutable ordinary `.claude.json` hash changed during the study. The private mask
was established before provider launch, and the study did not write that ordinary
path. A baseline hash alone cannot identify changed keys or the writer; this
report does not claim exact preference-byte preservation. The changed ordinary
file was left intact, with no restoration or overwrite.

No hooks/helpers/provider policy were installed or replaced, no ordinary session
was stopped, and no frontend, desktop, mesh, artifact selection or consumer repo
was changed. Only metadata receipts and study source/docs are retained here.

## Checkpoint acceptance and following work

Accepted: two read products, passive event/core versus service/delivery ownership,
source-specific bounded meanings, metadata privacy, actor/identity separation,
partial callback coverage and bounded replay design. The review found no design
blocker after the recorded counterexamples were resolved.

Pending: E0 concrete contract export, E1 production neutral emitter/sources,
E2 concurrent bounded service delivery, E3 read inspector, E4 immutable native
acceptance, and separately authorized E5 operations. Candidate idle/elicitation/
failure/headless/general terminal-outcome sources need their own proof. Alerts,
Kitty/349 physical Open, attachment/actions and mesh-plus remain separate.

Repository verification is recorded in [check results](check-results.json):
`./scripts/check`, study-script parsing, metadata JSON/privacy-field checks and
the replay model. No new production runtime code is part of this checkpoint.

## Primary research

- [Codex App Server](https://learn.chatgpt.com/docs/app-server)
- [Codex notify versus TUI notifications](https://learn.chatgpt.com/docs/config-file/config-advanced#notify-vs-tuinotifications)
- [Codex hooks](https://learn.chatgpt.com/docs/hooks)
- [Claude hooks](https://code.claude.com/docs/en/hooks)

Official references guide the hypotheses; current isolated native receipts and
independent installed/native comparisons bound acceptance.
