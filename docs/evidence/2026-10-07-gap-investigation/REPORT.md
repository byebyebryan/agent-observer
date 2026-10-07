# Remaining-gap investigation and a8 candidate acceptance

Date: 2026-10-07. The authorized regular loop investigated every remaining gap
from the overview. Two independently demonstrated Observer defects are repaired
in source and accepted through a separate installed a8 candidate. The normal
selected baseline remains a7. Provider support follows required contracts and
observed capabilities; native versions/hashes below are diagnostic proof bounds,
not support allowlists.

## Artifact, scope and independent comparison

A8 source is `3c71f216a716a36f2403f7c71fa5935c41c9917f`, version `0.4.0a8`,
wheel SHA256 `a8370b0f96d2669ff3bbf290ff01b9387cd7dfdacdf263c9f3baffbaf2343926`.
The [manifest](../../../artifacts/observer-0.4.0a8.json) and wheel are archived on
both hosts under `~/.local/share/agent-observer/artifacts/0.4.0a8-a8370b0f96d2669f`.
The separate installed prefix is
`/home/bryan/.local/share/agent-observer/0.4.0a8-a8370b0f96d2669f` on both.
[Snap](artifact-a8-snap.json) includes the source-only Claude-history SDK;
[Starship](artifact-a8-starship.json) uses core. Installed wheel bytes, all three
entrypoints, API 1, snapshot/watch 3, write 1 and separate service protocol 1
verify. No public schema or action command changed.

Ordinary installed native diagnostics were Codex CLI 0.160.1 and cached managed
daemon 0.161.0 on both hosts; Claude 2.1.292 on Snap. Ordinary native evidence was
read-only. Actions/hooks used disposable user/mount/PID namespaces masking
ordinary stores and copied native binaries; terminal and provider content were
discarded. The independent native reference imports no Observer collectors.

| Feed | A8 installed CLI versus independent native evidence, two rounds |
| --- | --- |
| Snap Codex | 50 rows; 2 loaded user contexts. Identity, phase, title where available, cwd and activity checks agree. 48 older rows retain unknown kind/runtime/phase. |
| Snap Claude | 31 CLI rows versus 32 bounded native candidates; 30 conversations and 4 live workers. The one omission is the setup-only candidate investigated below. All other compared fields agree. |
| Starship Codex | 92 rows; 4 loaded user contexts. Compared fields agree; 88 older rows retain explicit unknown classification/runtime/phase. |

[Candidate Snap](candidate-direct-snap.json),
[candidate Starship](candidate-direct-starship.json) and the before-baseline
receipts retain exact IDs, clocks, provenance, coverage and read-client checks.
Default confirmed-child filtering, full inventory selection, attention/activity
ordering, human age rendering and exact-reference lookup pass. Unknown kind is
retained; this ordinary sample does not prove that every older row is top-level.
Historical child-specific native acceptance remains independently scoped.

## Gap-by-gap verdict

| Gap | Result and remaining boundary |
| --- | --- |
| Slow configured polling | Fixed in a8. Successful and failed jobs configured above five minutes were silently shortened to five minutes. The scheduler now preserves the configured base interval and caps only additional retry backoff. Five/ten/sixty-minute and short-interval failure regressions pass. Ordinary selected cadences are unchanged. |
| Claude foreground questions | Fixed and installed-native accepted in a8. An actual held AskUserQuestion with verified interactive worker, no job and exact native `waiting`/`input needed` metadata reports blocked/question. Generic dialogs or missing/conflicting worker evidence remain unknown. |
| Codex default cold entry | Root cause narrowed on both hosts: mixed CLI/server feature defaults disagree on `api_key_model_discovery`. Both matched default pairs enter privately. This is a provider entry/configuration issue, not discovery failure; ordinary policy was preserved. |
| Claude live foreground attach | Still rejected by the writer as `unsupported_resume_route`. The native foreground registration is not a positively bound background job. Saved Resume and verified background attach remain separate supported routes. |
| Native `/exit` | Foreground prompt exit is now independently recognized; the native hook reports `prompt_input_exit` and that registration disappears. The attached-background attempt still did not prove recognition and left the worker live. Do not equate viewer exit with native worker stop. |
| Codex parked | Reader lifetime is proved in current private topology, including a held passive native listener. General parked inference remains unavailable: complete managed loaded inventory does not prove absence of an unbound standalone context or general worker end. |
| Old history and children | No heuristic compatibility reader added. Older Codex metadata explicitly leaves `threadSource` unknown; source/cwd/title cannot establish user versus child. Keep those rows unknown and expose the coverage boundary. |
| Claude history omission | Investigated: the omitted candidate has zero conversation records and only setup/system/cost metadata. No omitted active conversation was established. SDK history remains partial; do not invent rows or advertise complete legacy coverage. |
| Faster native monitoring | Feasible private Codex global start/status hints and Claude registry filesystem wakeups are proved. Production push currently still follows scheduled pulls. Loss, reconnect, bounded scheduling and event coverage are the next independent gate. |
| Notifications | Existing experimental source/normalization/client tests remain separate from API 1. Native lifecycle/input metadata does not establish a Kitty originating pane, unfocused delivery, desktop Open, duplicates or 349 mirroring. Normal hooks were preserved. |
| Remote recovery | Independent SSH schema/epoch consumer passes disconnect/reconnect against the selected Starship publisher. Remote CLI validates its local endpoint/clock. No cross-host BOOTTIME comparison, network replay or networking component is claimed. |
| Physical wake and overhead | Controlled expiry/restart/crash tests remain accepted historically. Physical suspend/wake and graphical/device checks still require a suitable operator window. Native-provider and whole-host idle CPU remain unattributed; no new resource claim replaces the existing publisher measurements. |
| Client/release readiness | API 1 and wire versions are unchanged. A8 is independently frozen/installed; managed selection, Agent Plus migration, device bridge and public release/CI remain separate deliveries. |

## Native entry, wait and lifetime evidence

The [Snap entry matrix](codex-entry-matrix-snap.json) and
[Starship matrix](codex-entry-matrix-starship.json) compare three private stores:
ordinary CLI 0.160.1/server 0.161.0 rejects feature skew; matched 0.160.1 and
matched 0.161.0 enter with default feature configuration. Local feature inspection
finds that API-key model discovery defaults changed from false to true. The
matched current [Snap New/Resume proof](codex-entry-resume-a7-snap.json) accepts
exact identity, repeated entry, native conversation clocks and rename/resume/
housekeeping age preservation. Versions are experiment coordinates only.

The ordinary repair belongs to provider management: keep the client/server
feature configuration coherent, then reprove cold New/Resume. Do not silently
select a cached native binary, add a provider-version allowlist, retry an uncertain
write or change every session just to repair passive observation. A frontend must
surface deferred native TTY entry errors; a prepared writer receipt is not entry
success.

[A7 foreground](foreground-a7-snap.json) returned unknown phase for the real
held question. [A8 foreground](foreground-a8-snap.json) reports three direct and
private-service blocked/question samples with the same conversation timestamp.
A neutral PreToolUse metadata hook independently confirms AskUserQuestion;
SessionEnd confirms actual prompt `/exit`. No question is answered by this proof.
This uses an initial positional prompt in a native foreground TUI; it does not
accept bare Agent View entry or foreground attachment. The
[a8 background regression](background-question-a8-snap.json) also accepts three
held job-question samples with stable age. An initial regression attempt sampled
Observer just before native wait began; the proof now obtains its projection
after the independent held predicate rather than treating that transition as a
stable mismatch.

The [attached-background exit attempt](background-exit-a7-snap.json) received no
recognition hook. Native registry/job remained present, job done/idle, and Observer
correctly retained running/present/waiting with age preserved. This attempt cannot
establish that a typed command was recognized or that native `/exit` never works
in that route. Explicit native stop/parked retains its earlier independent gate.

[Current-pair polling lifetime](codex-lifetime-a7-snap.json) unloads the observed
context at about 61 seconds; its quiet control is unloaded at the first probe
around 92 seconds. With a long-lived initialized read-only native peer and a8
publisher, the [paired listener lifetime](codex-listener-lifetime-a8-snap.json)
unloads the observed context by about 82 seconds and the quiet control is unloaded
when first probed around 112 seconds. Nine listener messages were discarded.
These are sampled bounded proofs that readers did not indefinitely keep these
contexts alive; they do not establish identical exact retirement timing or a
general Codex parked predicate.

## Native events, notification sources and cached age

The [Snap listener sample](codex-listener-snap.json) and
[Starship sample](codex-listener-starship.json) initialize before an owned
New and never resume or subscribe. They receive global `thread/started` and
`thread/status/changed` hints for the exact new user UUID, plus a child context.
These samples receive no turn-start/completion feed; status hints cannot become
lossless completion notifications. Native generated schema and official
[app-server documentation](https://learn.chatgpt.com/docs/app-server) distinguish
metadata reads from resume/subscription. Incoming native content is discarded;
only whitelisted method counters and exact-ID hints enter evidence. The peer must
remain a separate passive listener if this capability is implemented.

The Claude foreground test sees nine inotify registry events with no overflow.
That proves a wakeup input, not that filenames/mtime identify or timestamp a
conversation. A production watcher must handle atomic replacement, new
directories, overflow, permissions and loss, and trigger authoritative bounded
reads. See the [next implementation gate](../../event-assisted-monitoring-plan.md).

A fresh Starship listener fixture needs an explicitly owned bootstrap TUI to
start its private native daemon. Connecting a passive reader to a nonexistent
endpoint does not start one. The proof exposes that optional bootstrap explicitly;
ordinary observer behavior still has no autostart fallback.

Official [Claude hooks](https://code.claude.com/docs/en/hooks) document lifecycle
and attention callbacks. Agent View's `agent_needs_input`/`agent_completed`
notifications depend on that view; they are not an all-background completion
feed. Foreground idle notifications and deferred attention notifications have
delays. The short held-question lifecycle test was not an acceptance of those
Notification timings. Keep native event correlation, notification formatting
and explicit terminal-origin routing separate. A daemon environment is not a
current terminal binding. Normal publication and graphical/device Open still
need the [notification client gate](../../notification-client-contract.md).

Final selected-service comparison retains age differences when active Claude
history advances between scheduled history reads. The 120-second history cadence
is a user-visible latency boundary, even while component health remains current.
The [catch-up receipt](cached-age-catchup-snap.json) confirms all three captured
native activity targets reached or were exceeded by the cached view at the next
check. It does not claim a zero-latency latest-state view. This is a reason to
implement independently gated native hints for history as well as runtime; never
replace conversation age with registry activity or a transport heartbeat.

## Closing gates and preservation

The independent [public API consumer](public-api-a8-snap.json) validates exported
schemas, strict input, exact references, ordering, write fixtures and 4096-row
serialized CLI output without importing Observer. The
[remote consumer](remote-reader-starship.json) validates service frames, host/UID,
sequence/revision and publisher stability. It discards its view on disconnect;
reconnect starts sequence one with the same publisher. A7 serving with an a8
reader also demonstrates unchanged service/read compatibility in this case.

Source checking passes 290 tests, with one optional system-jsonschema test skipped;
the separate installed public consumer uses jsonschema 4.26.0 and passes. All
proof scripts parse; documentation/link/whitespace/staged checks are required
before the closing commit. No frontend or provider-management code changed.

Five Snap namespaces are [stopped and removed](cleanup-snap.json), including all
borrowed credentials and generated native conversation stores. The
[Starship cleanup](cleanup-starship.json) verifies all five owned namespaces
are stopped and borrowed stores removed. Preservation before/after hashes for native
configuration and external pins, selected links and ordinary Observer unit PIDs
match on both hosts. Managed final verification confirms the six selected a7
targets and active enabled units; no ordinary provider action or restart was
performed. Final comparisons retain explicit setup-only/unknown/race/cadence
findings rather than declaring every cached row latest or complete.

The final Starship service inventory contains 93 rows after one new empty saved
row appears. Its native conversation clock is unproved and the CLI keeps age
unknown. This is retained separately from the earlier stable 92-row comparison.

For physical wake acceptance, record the selected artifact, publisher UUID/PID,
host boot/time domain, component receipts and native inventory before the operator
suspends the owning host. On wake, obtain a new service frame before rendering:
check expired receipts become stale rather than idle, reconnect starts a new
connection epoch, and independent native reads converge to the resumed inventory
within configured collection bounds. Repeat with a reader on the other host;
invalidate the held remote view on silence and validate clocks on its owning host.
Record actual wake timing and bounded predicates, not terminal captures. Existing
synthetic BOOTTIME tests and ordinary unit recovery do not substitute for this
physical window. Graphical notification/Open and device mirroring need their own
originating Kitty/tmux pane and desktop/device checks.

The immediate next deliveries are: select the already accepted a8 producer through
the managed artifact/recovery gate; implement bounded event-assisted collection
with native loss/lifetime/cost proof; then start an independent Agent Plus/client
migration against the exact chosen producer. Physical wake, terminal notification
publication, networking and public release keep their own acceptance windows.
