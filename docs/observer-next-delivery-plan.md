# Observer next delivery and remaining-gap plan

Date: 2026-10-07. Status: planning pass; no implementation, deployment or native
action is authorized merely by this document. The starting source is `3de9e35`.
The [gap investigation](evidence/2026-10-07-gap-investigation/REPORT.md) accepts
installed a8 on both hosts; normal Observer commands and units still select a7.
The [event design](event-assisted-monitoring-plan.md) supplies the source boundary.
This plan turns those findings into ordered, independently reviewable deliveries.

Execution outcome: the [delivery report](evidence/2026-10-07-native-delivery/REPORT.md)
records P0/P1 selection of a8, bounded P2-P4 implementation and separately
installed a9 native/artifact acceptance subsets. P5's resource gate is not
accepted, so P6 hint selection and its 30-minute soaks are withheld. P7 hands off
selected a8 and explicit candidate limits. The
[cost follow-up](native-hints-cost-follow-up.md) retains the original targets;
the table below remains the intended sequence, not a claim every gate passed.
The user subsequently relaxed the 64 MiB aggregate memory target and resumed
execution. It is a review threshold; P6 still requires exact artifact/native
acceptance, recovery, rollback and 30-minute resource/reader checks. Retain
absolute/added RSS and add idle/collection RSS/PSS without imposing a new cap.

## Outcome and priorities

Deliver a usable normal Observer baseline, then an independently accepted
publisher that reacts promptly to native changes in runtime and conversation
history. Preserve API 1, snapshot/watch 3 and write 1. Service protocol 1 remains
separately prerelease. Producer acceptance precedes frontend implementation;
notifications, networking and devices retain their own boundaries.

Codex leads implementation and native proof on Snap and Starship. Claude remains
required on Snap, including a Claude-only service configuration. Support follows
required contracts and observed capabilities, never provider release allowlists.
Record freshly inspected versions/hashes as provenance and incarnation guards.

The main sequence is P0 through P7 below. Native entry/lifecycle investigations
have their own bounded branch. Their supported subset and explicit limits must
be settled before handoff; complete legacy reconstruction, arbitrary foreground
attachment and general parked inference are not release requirements.

## Ordered producer checkpoints

| Checkpoint | Concrete deliverable | Exit evidence |
| --- | --- | --- |
| P0: current baseline | Reinspect source/managed/installed/live state on both hosts; compare installed direct and service CLI with independent native inventory; record configuration, links and provider/service incarnations | Exact identity/state/age/coverage comparison with races and cadence lag explicit; approved source boundaries and metadata-only proof/cleanup procedure |
| P1: a8 operational promotion | Audit and support a verified old-to-new Observer unit transition; stage the exact a8 manifest/wheel in the managed archive format; update only Observer selection and its owning user unit | Old/new ownership and foreign/drift rejection tests; rendered six-target diff; Snap then Starship apply, restart, rollback and reselection; final native CLI comparisons and preservation bookends |
| P2: bounded hint integration | Connect a private hint-source port to the existing scheduler, with independent runtime/history cooldowns, bounded coalescing, source epochs and owned helper shutdown | Controlled bursts, malformed/late hints, hint-while-job-active, timeout/backoff storms, fair history scheduling, no overlapping provider jobs and unchanged receipt clocks until accepted reads |
| P3: Codex hint source | Long-lived initialized passive peer on an existing verified owning endpoint; whitelisted start/status/name hints trigger appropriate runtime/history reads | Native both-host New/work/wait/completion/title/activity comparisons; listener loss/reconnect and daemon incarnation changes; no action-based subscription or provider startup |
| P4: Claude hint source | Bounded registry/job/history directory watching, including atomic replacement and new project/job directories; metadata events request authoritative reads | Snap foreground/background waits, completion, new history, title and activity comparisons; Claude-only service; overflow, directory replacement, permission failure and watch-limit recovery |
| P5: integrated producer acceptance | Freeze a new candidate from the reviewed checkpoint; install separately; run public/schema/reference consumers, independent native transitions, paired lifetime and resource/latency checks | Both providers and Codex hosts pass within stated topology/capability bounds; loss falls back to periodic reconciliation; target results and all exclusions are recorded before managed selection |
| P6: event-capable operational rollout | Reuse the proved old-to-new selection path to promote the independently accepted candidate; enable the accepted hint mode in Observer configuration only | Exact artifact/flags/profiles verified; Snap then Starship restart/crash/rollback/reselection; 30-minute multi-reader checks per host; native comparison and provider/config preservation |
| P7: contract and client handoff | Update API/service guides, canonical fixtures, capability matrix, operations runbook and exact artifact/endpoint handoff | Pure reference consumer conformance, transport expiry/reconnect tests and documented native/action limits; no frontend implementation used to close a producer gate |

Commit each accepted checkpoint with its appropriate checks. Failed source or
native proof reopens that checkpoint. Do not select a partially accepted event
candidate to make progress appear complete. A successful a8 rollout can remain
the normal baseline while a later hint candidate is being repaired.

## P1 upgrade work discovered during planning

Source inspection of the chezmoi `agent-observer-operations` helper shows that its
existing-unit guard expects the target prefix, and its preexisting-config guard
expects the target unit contents. A running known a7 unit can therefore be
rejected when the desired tuple becomes a8. This is a source-derived upgrade
concern, not a failed live migration performed during this planning pass.

Before promotion, bind the prior installed artifact/unit/arguments and the new
verified desired tuple separately. Capture a private rollback snapshot before
stopping the positively owned Observer unit. Prove that an unknown executable,
changed PID birth, edited target, changed workspace configuration or concurrent
managed drift is rejected before mutations. Keep those guards when accepting the
known old incarnation; do not broadly weaken foreign-unit protection.

The archive verifier expects `manifest.json`, while the a8 candidate archive
contains its named manifest. Stage an exact byte-identical canonical manifest
for managed verification. Keep wheel hash, source revision, prefix and profiles
coherent. Change only the six Observer targets and required managed selection/
operations sources; preserve unrelated chezmoi changes and all Agent Plus pins.
Historical operational acceptance is not proof of this new upgrade transition.

## P2-P4 implementation boundaries

`Scheduler.hint()` already supplies component dirty/follow-up behavior. Extend
that path rather than introduce a second scheduling system. Keep its existing
one active collection job per provider and separate runtime/history receipts.
Review fairness and retry cooldown explicitly: a continuing hint storm must not
bypass failure backoff or starve history.

Use publisher-owned hint helpers when provider I/O/parsing could block the IPC
loop. Their private bounded messages carry only source epoch, component and a
finite wakeup/loss reason. The publisher validates scope and coalesces hints;
workers perform authoritative native reads. Reject old epochs after helper/store/
endpoint changes. Bound helper counts, watch counts, input bytes, queued wakeups
and retry rates; shut down only owned helpers with the publisher.

Codex global thread start/status/name events are wakeup evidence, not a complete
turn event feed. Map events conservatively to runtime/history reads and prove
both actual state and conversation-age improvement. Unknown native methods and
content are discarded. An unavailable endpoint keeps polling/unavailable
semantics; it never causes native daemon startup or resume.

Claude registry/job changes request runtime reads; conversation-store changes
request history reads. Watch directory identity and subtree creation, not just a
fixed list of files. Overflow or loss requests a budgeted full reconciliation
and rearm. Filesystem names/mtime never become identity, phase or activity clocks.
Watching does not require replacing ordinary hooks.

Use an explicit candidate hint mode, initially disabled for normal selection.
Keep the existing periodic cadences while measuring the new mode. Collect
bounded diagnostic counters/reasons outside unchanged API/service frame shapes;
extra fields must not silently change a strict schema. Hint loss does not renew
leases or discard otherwise valid current samples without contrary evidence.

## Performance and correctness acceptance

The following are proposed engineering targets, not existing guarantees. Set
the measurement harness and bounds before implementation; report missed targets
as gaps rather than changing them after observing results.

| Dimension | Initial target / proof |
| --- | --- |
| Runtime latency | Healthy supported native transitions reach a cached current view at p95 within 5 seconds in controlled tests; record event-arrival-to-view and independently bracketed native-transition-to-view separately |
| Activity/history latency | Supported conversation changes reach a current native activity clock at p95 within 15 seconds; rename/housekeeping must not advance conversation age |
| Burst limits | Initially evaluate a 1-second minimum runtime gap and 10-second minimum history gap, with at most one pending wakeup per source/component; verify bounded trailing work and history fairness |
| Idle collection | After startup, idle hints do not cause more authoritative reads than the polling baseline; unrelated native traffic is ignored |
| Owned resource budget | Compare equivalent workloads/modes; incremental mean CPU at most one percentage point. User-relaxed 64 MiB aggregate RSS is a review threshold; report absolute/added RSS and idle/collection PSS, with bounded helper/FD/watch behavior and no sustained unexplained growth over the soak |
| Failure recovery | With hints unavailable, convergence returns to the configured periodic interval plus collection bound; source health, expiry and old conversation clocks remain truthful |
| Native passivity | Loaded-set bookends and paired quiet-control retirement with a long-lived peer, plus unchanged ordinary settings/hooks/native process ownership |
| Reader behavior | Multiple readers share collection work, slow readers receive conservative gap/resync or disconnect, and remote silence/reconnect invalidates held claims correctly |

Qualify latency by source coverage, supported topology and collection success.
One successful hint sample cannot establish every native transition. Native
provider/whole-host CPU requires separate attribution and is not covered by the
owned-publisher budget. If targets conflict with measured safe collection cost,
retain the candidate separately and record the tradeoff for review.

## Native workflow branch and remaining limitations

Run the native branch before final P7 handoff, using freshly inspected ordinary
topology read-only and verified disposable stores for actions. It can proceed
independently of hint implementation; it cannot turn observation into control.

| Concern | Bounded next proof / decision |
| --- | --- |
| Codex ordinary cold New/Resume | Reinspect client/server feature contracts and installation/configuration ownership. Produce the smallest concrete provider-management repair and prove it privately. Applying ordinary provider updates/settings or restarting sessions is a separately scoped delivery; provider versions are not compatibility gates. |
| Claude attached-background `/exit` | Use neutral metadata lifecycle recognition plus exact worker/job/attachment bookends. If recognition still cannot be proved, retain the supported explicit native-stop route and document the viewer/worker distinction. |
| Claude live foreground attach | Investigate a provider-supported exact-ID route. Retain `unsupported_resume_route` unless independently proved; saved Resume/background attach remain the supported writer routes. |
| Codex parked | Seek positive provider-owned absent-runtime evidence covering the relevant contexts, not only a missing loaded ID. Without it, keep unknown; no PID/title/cwd heuristic. |
| Older child/history classification | Accept explicit native metadata only. Preserve unknown kind and partial Claude history; do not add a legacy reconstruction stack to recover setup-only entries. |
| Generic Claude dialogs | Keep unknown unless a distinct native input/permission predicate is demonstrated. The accepted foreground question predicate is not generic dialog coverage. |

Each investigation ends with an accepted predicate/route, a demonstrated source
defect and scoped fix, or an explicit unsupported verdict with evidence needed
to reopen it. Repeating an unchanged inconclusive experiment does not close a
gap. Optional limitations may remain in a usable producer; advertised facts and
enabled actions must meet their own proof gate.

## Subsequent independent deliveries

1. **Agent Plus migration:** begin against the exact P7 producer/endpoint after
   Observer acceptance. First validate service/read/write decoding, source
   freshness, cache cutover, age/order and host/provider scope with fixtures and
   installed CLI. Then implement picker/rendering/routes and visible deferred
   entry errors; validate Codex across both hosts and Claude on Snap. Native
   entry repair gates affected action acceptance, not read-only integration.
   Producer defects reopen an Observer pass. OpenCode remains deprecated.
2. **Notifications:** keep the experimental normalizer/client separate. Prove
   completion/attention correlation and continuation/duplicates before replacing
   normal hook wiring. Then accept originating Kitty/tmux pane, unfocused
   delivery and desktop Open. 349 mirroring/Open follows as a device gate.
3. **Dashboard/networking:** RLCD or other bridges consume accepted public
   frames, own remote clock/freshness handling and device transport. Optional
   shared networking can share this repo but has its own failure/authority
   contract. No provider-private collector moves into a bridge or frontend.
4. **Physical wake and release:** use a scheduled operator window for actual
   host suspend/wake and graphical/device tests. Publish a release and hosted CI
   only under a separately scoped delivery, with exact accepted artifacts and
   supported claims. Physical evidence cannot be replaced by synthetic expiry.

## Unattended batch and completion definition

A future regular goal loop can take P0-P7, committing accepted checkpoints.
The planning turn itself edits documentation only. Native proof actions remain
inside owned disposable namespaces. Normal changes in that execution scope are
Observer-only managed selection/unit restarts after gates; preserve provider
configuration, live conversations, ordinary hooks, frontend selections and
unrelated source drift. No active Codex session restart is a requirement for an
Observer-only rollout.

At each checkpoint, separate source checks, frozen artifact, installed behavior,
independent native comparison and normal selection. Run `./scripts/check` before
commits and the affected runtime/native/reference checks for implementation.
Archive bounded metadata only. Remove owned proof processes and borrowed auth/
history, verify preservation bookends and write exact rollback/selection state.

Finish with an accepted normally usable producer, measured hint/cadence behavior,
an updated limitations matrix and an independent client handoff. If a required
gate fails, leave the last accepted baseline selected, fix or document the
specific checkpoint, and use remaining time on independent Observer work.
Never lower the gate or start frontend implementation to mask a producer defect.
