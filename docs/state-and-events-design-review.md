# State and native event design review

Date: 2026-10-09. Primary-led review of the
[design](state-and-events-design.md), official provider interfaces, existing
source/client boundaries, isolated native sources and an independent synthetic
delivery model. No production event stream is accepted by these experiments.

**Subsequent scope decision:** the readiness verdict below retains its research
bounds. Native event implementation is now deferred in favor of the
[state-push refinement](state-push-design-review.md). Its accepted state contract
does not require this proposed event product.

## Verdict

The design is ready for a separately authorized implementation pass. It fits
the accepted observation boundary and does not require API 3 or changes to
API 2/read wire 4/Service 2. Add a separate event record/facade/local envelope;
preserve existing current-state semantics. Concrete schema export and strict
conformance are the first implementation gate, not an implied installed API.

Core owns reusable passive event meaning. The local service hosts sources,
intake, optional cached context and bounded replay. All alert presentation,
filtering, delivery and actions remain clients. mesh-plus is external. The
349 handoff is requirements input, not authority over other consumers.

The main source risks are now concrete: passive Codex daemon traffic is not the
documented detailed turn subscription; Claude Stop is not final-turn authority;
optional callbacks have partial and sometimes unobservable input coverage.
The design preserves those limits rather than disguising them as reliability.

## Review findings and resolutions

| Failure or coupling | Evidence / counterexample | Design resolution |
| --- | --- | --- |
| Treat every Codex notification method as globally delivered | Four completed root turns across two hosts produced no passive turn-completed events; installed schema lacks passive subscribe | Use daemon hints for state refresh and independently proved optional notify callbacks for completion notices; never resume/load to subscribe |
| Infer native completion history from state diff | Two turn ends can occur between two working samples | State resync and native events are separate products; no reconstructed completion fallback |
| Treat Claude Stop as success/final completion | Parallel fixture hook continued the same prompt between two Stop callbacks | Publish response-end observation only, with original correlation; final outcome remains unsupported |
| Delay urgent attention until Notification | Permission notice followed PermissionRequest by 6017 ms | Preserve both source meanings; clients choose urgency/coalescing; current phase remains native-read authority |
| Make optional hooks a discovery dependency | Current state sources have independent accepted daemon/registration proof | Missing callbacks disable/limit event coverage, never discovery/monitoring |
| Let callback or heartbeat renew state | Receipt is unrelated to a current runtime lease/native conversation clock | Event admission and delivery cannot mutate runtime/phase/activity/retirement evidence |
| Child callback changes parent classification | Claude SubagentStop carries parent UUID and child actor ID | Keep session identity/kind and event actor distinct; preserve child facts in feed |
| Classify unknown Codex callback IDs by absence | Two additional Snap callback IDs lacked current readable native detail | Keep actor/session kind unknown; no timing, cwd, title, PID or UUID inference |
| Turn 349 filtering into core semantics | Other clients may want child/debug/native evidence | Remove suppression/disposition/body/Kitty fields from new core events; retain client policy separately |
| Block callback handling on title/provider lookup | A native title may arrive later; source can fail independently | Admit bounded facts promptly, enrich from accepted cache only, preserve null/reason and immutable record context |
| Pretend metadata revision proves event causality | State refresh and callback arrival race independently | Revision labels enrichment context only; no atomic cross-product barrier promised |
| Global receipt dedupe loses related facts | PermissionRequest and Notification describe related but distinct observations | Preserve separate receipts; clients coalesce only for their own presentation |
| Prompt ID becomes event ID | Multiple response ends or attention requests occur within one prompt | Prompt correlation only; full scoped native turn correlation where independently proved |
| Same numeric cursor survives restart | A replacement publisher can reuse sequence 1 | Bind epoch/scope and reject old cursors before delivery |
| Empty queue claims complete history | TTL expiration can empty a previously populated ring | Retain loss floor even when empty; gap/restart remains explicit |
| Replay/live race loses a concurrent admission | Subscriber starts while another record is admitted | Atomic high-water barrier, replay through it, then later sequences; concurrency proof remains an implementation gate |
| Client filter causes replay loop | Client displays sequence 1 and hides sequences 2–4 | Checkpoint scanned high-water mark, not last displayed record; initial server has no filters |
| Rejected input silently preserves apparent completeness | Oversized/malformed supported callback cannot become a record | Finite rejected/detected-loss counters/status separate from admitted sequence continuity; native completeness never asserted |
| Healthy local transport proves all native callbacks | Missing emitters can be undetectable | Ready means intake readiness; explicit partial source scope; no mandatory ledger or lossless input claim |
| Slow subscribers affect state/provider work | Unbounded per-client event queues amplify memory and backpressure | Independent bounded intake/replay/output, gap or disconnect, no provider query per reader |
| Reconnect snapshot fabricates lost alerts | Snapshot restores current phase only | Event gap remains unfilled; restore state independently and let client report/reset alert history |
| Same-user caller becomes trusted native authority | Unix ownership only proves local permitted access | Distinct configured-callback/native-daemon provenance, bound scope, no action permission |
| Callback output controls provider behavior | Hook failures can block/continue/inject context | Neutral exit zero and `{}`, no decision/context/terminal fields, finite deadlines; packaged fault proof required |
| Mesh treats source clocks as local | BOOTTIME domains differ by host/boot/time namespace | External mesh preserves identity/epochs/clock domain and adds conservative authenticated transport handling |

## Strength of validation

The [native report](evidence/2026-10-09-state-and-events-design/REPORT.md) compares
scalar callback/native RPC facts against the installed a11 CLI in isolated
ordinary interactive topologies. It does not use Observer as its native source
oracle. Both hosts' source namespaces are owned and cleaned separately.

The synthetic model executes 50,000 operations over a bounded deque and checks
it against an independently maintained audit/reference suffix. It checks
retention, cursor/epoch fencing, filtered progress and counterexamples. It does
not implement concurrent subscribers, OS sockets, actual service scheduling,
source authentication, source-loss detection or performance. The sequential
high-water example proves the intended rule, not a production race-free server.

Failure injection establishes neutral behavior for the study callback sink on
invalid JSON, oversize input, unknown events, invalid notify input and a
symlinked sink. It does not accept the future production emitter, endpoint
authentication, overflow handling or hook installation. Those must be repeated
against immutable candidate bytes before operations.

The fresh ordinary read/native comparison agrees on all Codex rows and runtime/
phase on both hosts, and all Claude membership/runtime/phase on Snap. It retains
the accepted setup-only Claude cwd omission and a bounded activity sampling
race. This is regression context, not a new event implementation acceptance.

## Explicit deferred scope

- A complete Codex detailed passive stream, arbitrary headless publishers,
  failed/interrupted completion coverage, and distinct tree-root/thread hook
  identity require new source capability proof. No auto-resume subscription.
- Claude questions/elicitation/idle/failure callbacks need focused immutable
  native proof before their mapping is advertised as supported. Claude final
  outcomes and background jobs are not part of this delivery.
- Native losses while optional emitters are absent may be undetectable.
  Durable replay, offline catch-up and exactly-once desktop delivery are absent.
- Initial buffer defaults need service/resource validation, with measured limits
  reported rather than a strict universal memory target.
- Endpoint paths, concrete wire schemas, error enums and CLI command spelling
  are frozen at E0, before implementation. This design is not a new package.
- Kitty sender/focus/Open, originating tmux pane, DMS mirroring and physical 349
  acceptance belong to the alert-client pass. No observation-side attachment
  implementation is needed to finish this event producer.
- No sibling-repo, normal hook/provider-policy, managed artifact or network
  deployment is authorized by this research checkpoint.

No remaining uncertainty blocks the selected two-product/ownership design.
The listed unknown capabilities are scoped exclusions or independent following
acceptance gates, not filled by compatibility paths or guessed evidence.
