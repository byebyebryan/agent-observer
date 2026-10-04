# Coding-agent session-state spike plan

Date: 2026-10-02. Status: P1 active; bounded empty-state evidence recorded.
Populated native-session proof and adapter implementation remain pending.
Context: [agent-session-study.md](agent-session-study.md).

This plan moved from the RLCD repository into Agent Observer on 2026-10-02.
[Architecture](architecture.md) defines the shared boundary and
[roadmap](roadmap.md) records checkpoint status. The
[migration plan](native-runtime-migration-plan.md) defines later runtime and
consumer delivery; the [Snap report](evidence/2026-10-02-p1-snap/REPORT.md)
records the completed bounded P1 slice.

## Objective

Prove a small, passive source of Codex/Claude session inventory and state
for the active RLCD and Agent Plus consumers. Select the source from current
provider capabilities rather than importing the reference projects'
historical assumptions.

The deliverable is host-side JSON, a capability/coverage table, and evidence
of correct transitions. Firmware, display layout, production daemons,
multi-host networking, notifications, session controls and OpenCode stay
outside this spike. Do not add a full collector service before source
selection is justified.

For Agent Observer, validate the observation contract against
the active RLCD and Agent Plus needs: live session state, saved-session
inventory, exact identity, and freshness. Keep inventory and live observations
distinct. This does not add consumer integration or session actions to the
spike. WSNav supplies historical design evidence and may become a consumer
later; its integration, language, and current runtime model do not set the
scope or acceptance criteria.

The migration target is provider-managed execution with individual native TUI
entry, Codex first and Claude second. Evaluate foreground modes as comparative
or transition evidence; full foreground feature parity is not required for
managed-runtime delivery. Keep each topology's coverage explicit. Early Claude
identity/lifecycle evidence checks the shared model before schema stabilization.
Consumer migration and provider runtime policy changes remain separate work.

## Execution boundaries

Preserve ordinary sessions, current compatibility opt-outs and existing
hooks. Use disposable workspaces and explicit per-run configuration/endpoints.
Verify isolation before any launch that could auto-start or connect to a
supervisor. An isolated App Server experiment is not by itself proof of the
provider's managed-daemon behavior.

Do not bootstrap services, install packages, update providers, enable Remote
Control, stop ordinary daemons, or change managed dotfiles as part of the
spike. If a provider cannot be isolated with its supported configuration,
record that topology as pending rather than altering the working environment.
Hook experiments must use provider-native trust/configuration flows in the
disposable setup and event-specific passive output.

Keep credentials transient and outside Git/evidence. Do not capture ordinary
transcripts or terminal buffers. Human observations refer only to disposable
cases and report visible state, not conversation content.

## Phase 1: capability and topology preflight

Before choosing an adapter, record for each actual target host:

- Executable path, CLI version, and running server/supervisor version when
  available; account/feature availability without recording credentials.
- Relevant effective settings, their provenance, and which opt-outs disable
  an interface versus only daemon auto-start.
- Actual topology: foreground TUI, daemon client, supervised worker, or none.
  Validate process birth/socket ownership; stale PID files are insufficient.
- Available read-only commands, installed protocol/schema fields, source
  coverage, and absent/conditional identifiers.
- Whether a candidate read starts a daemon, loads a session, subscribes,
  changes settings or affects worker lifetime. Check before/after state.

Bounded initial inspections include installed `--version`/help, selected
Codex features and generated schemas, and documented version/status commands.
Inspect only known non-secret config keys. Check version-specific command
routing before invoking Claude diagnostics; do not rely on shell aliases.

First candidates:

| Provider/topology | Candidate | Question to resolve |
| --- | --- | --- |
| Claude foreground | Native `agents --json`, if available under the opt-out | Does it include live interactive IDs and accurate status without enabling agent view? |
| Claude supervised | Native JSON roster and documented supervisor status | How do job state, process status, native UUID and worker lifetime relate? |
| Codex foreground | Passive lifecycle hooks; exact stored metadata for enrichment | Which live transitions and current IDs can be established without a shared server? |
| Codex daemon-backed | Passive App Server reads from the owning runtime; hooks if needed | Is authorized observation available without resuming/loading a thread or changing runtime ownership? |

For Claude, distinguish a job's short ID from the native conversation UUID.
For Codex, decide which interactive source kinds belong in the roster; test
forked/resumed identities instead of inheriting the CLI-only history filter.
Metadata reads from a new helper are never evidence of another runtime's
live status.

Phase exit: write `capabilities.json` and the minimum isolated launch/read
procedure for each supported row. Record unsupported and unavailable cases
with reasons. Do not substitute the old reference implementation when a
current interface is missing.

## Phase 2: compare sources with the smallest harness

Create temporary, study-only adapters that emit bounded metadata JSON. Start
with the native read interfaces established in Phase 1. Add hook capture only
where it answers a specific coverage/timing question.

For a hook, retain an allowlist of session/turn IDs, event name, reason code,
and observation time. Keep delivery local and bounded; enrich names outside
the hook path. Observer failure must not approve/deny a tool, inject context,
continue a turn, or stall the provider. Prove the passive output for each
event rather than copying WSNav's older configuration unchanged.

Proposed output fields, to refine from observed capabilities:

| Field | Meaning |
| --- | --- |
| `host`, `provider`, `native_session_id` | Logical identity; missing native IDs remain unbound |
| `provider_job_id`, `runtime_incarnation` | Optional job/worker identity, separate from the conversation |
| `topology`, `provider_version` | Evidence context; not inferred from a cached launch command |
| `cwd`, `title` | Bounded metadata; omit prompt-derived previews |
| `presence`, `attachment` | Runtime presence and client attachment, each independently unknown when unproved |
| `work_state`, `wait_reason` | Normalized work state and a reason code; never copied question/tool text |
| `state_observed_at`, `presence_observed_at` | Separate timestamps for state and liveness |
| `source`, `observation_health` | Provenance and current/stale/unavailable/ambiguous/unsupported status |

Candidate work states are `working`, `needs_input`, `settled`, `interrupted`,
`error`, and `unknown`. `settled` does not mean task success. Preserve native
state codes when useful for diagnosis; do not equate a provider's job `done`
with verified tests or completed background work.

An initial proposal is a one-second native snapshot interval, a five-second
observation-health timeout, and a 100 ms maximum hook handoff. These are test
targets, not measured behavior or production commitments. Event-derived state
must not expire merely because a long command emits no hooks, nor stay current
solely because its process is alive. Establish reconciliation rules from the
actual evidence; after an unobserved interval, report unknown until recovered.

Phase exit: one disposable session per available topology, raw state codes
and normalized output compared with operator-observed state. A synthetic SDK
session cannot substitute for the native TUI cases.

## Phase 3: transition proof

Run the core cases once per provider/topology that Phase 1 can safely exercise.
Use tiny disposable tasks and deliberate approval prompts; a no-approval
configuration cannot establish permission-wait coverage. Repeat only failed
or ambiguous cases after a targeted change.

| Case | Action and independent observation | Required result |
| --- | --- | --- |
| Start and completion | Submit a small task; observe activity and return to prompt | Exact native identity; working then settled; distinguish initial idle |
| Approve a long tool | Hold an approval, then approve a harmless command lasting at least 10 seconds | Needs input while prompt is open; clears within two seconds of approval, before tool completion |
| Deny a tool | Hold then deny an approval | Waiting clears; report actual subsequent working/settled/error state |
| User question | Exercise a blocking native input request, then answer it | Correct waiting reason and resolution; distinguish final conversational questions from blocking requests |
| Cancellation | Interrupt a turn from its native UI | Leaves working/waiting; interrupted when proven, otherwise explicit unknown |
| Exit and observation failure | Exit the disposable foreground session; interrupt the collector connection | Foreground exit is recognized; unavailable observation does not become idle |

Compare native snapshots and hook events on the same timeline where both are
available. In particular, check whether a permission hook preceded an actual
prompt and whether another Stop hook continued work. Never clear a wait only
after a long-running approved tool returns.

Use a case-local monotonic clock for latency and ordering, plus UTC capture
times for attribution. Record operator-observed transition times separately
from provider/collector times. Label timing inconclusive if the observation
method cannot resolve the two-second target. A passing parser or schema check
is not a passing native session transition.

## Phase 4: identity and recovery proof

Run the applicable cases that distinguish current runtime management from
the older foreground-only correlation model:

| Case | Required assertion |
| --- | --- |
| Two concurrent sessions in the same directory | Different native IDs; no cwd/title-based merge or cross-session state |
| Native clear/new/resume/fork | Current conversation is rebound correctly; delayed old events cannot update the new binding |
| Collector starts/restarts mid-turn or mid-wait | Recover from an authoritative snapshot, or expose unknown until new evidence; never infer settled from silence |
| Viewer close, native detach/reattach and TUI exit | Distinguish each native operation and its cancellation/lifetime effects; no false logical-session exit or assumed work persistence |
| Multiple clients for one logical session | One session row with separate attachment evidence |
| Disposable worker exit/restart | PID loss is not automatically logical-session completion; new incarnation is reconciled |
| Saved old session remains live | Catalog pagination/recency cap does not silently remove it |
| Missing/conflicting/late evidence | Explicit unknown/ambiguity, no first-match guesses or stale state overwrite |

Exercise error reporting when it arises naturally or through a safe isolated
failure. Synthetic error/duplicate/out-of-order fixtures may validate adapter
handling, but must be labeled synthetic; they do not establish live provider
coverage. Do not disrupt credentials or an ordinary server to force an error.

If a controlled socket App Server is the only available Codex server case,
report it as a controlled server result. Managed-daemon support remains
pending until its actual behavior is exercised. Likewise, Claude's documented
JSON roster is not live acceptance until tested on the intended version.

## Evidence and decision

Use a dated directory under `docs/evidence/` for sanitized artifacts:

- `capabilities.json`: versions, selected toggles, topology, candidate coverage,
  commands/interfaces used, and supported/pending reasons.
- `observations.jsonl`: allowlisted provider evidence with case/run IDs and
  timestamps; no raw responses, transcripts or terminal captures.
- `transitions.jsonl`: normalized state with the evidence that caused it.
- `results.json`: case assertions, latency, disagreements and outcome per
  provider/topology; distinguish live, static and synthetic evidence.
- A short results document: chosen source per topology, remaining gaps,
  minimum required configuration, cleanup and effect on ordinary sessions.

Review the artifact allowlist and secret/content exclusion before capture.
Record observer overhead, timeouts/dropped events, and behavior when the sink
is unavailable. Compare relevant config hashes and the ordinary runtime set
before/after; cleanup only processes/endpoints created by the spike.

The final coverage table must distinguish `passed`, `failed`, `unsupported`,
`unavailable`, and `not_run`. Basic completion passing cannot silently cover
approval, cancellation, daemon support, or identity recovery.

Source selection criteria:

1. Exact identity and accurate normal/waiting transitions on the intended
   versions/topologies, including prompt resolution before tool completion.
2. Observation is passive and ordinary compatibility configuration is intact.
3. Missed events, restarts and conflicting sources produce explicit uncertainty
   and a documented recovery path.
4. Retained sessions, attached clients and worker processes remain distinct.
5. Evidence is bounded and content-free; overhead meets the stated targets.

If native feeds cover the cases, prefer them and omit redundant hooks. If a
provider needs hooks, specify exactly which coverage they add. If a core state
cannot be established reliably, report that limitation and revisit the source
before firmware integration. Any standalone-only result is partial with
respect to daemon-backed support; changing the ordinary opt-outs is a separate
compatibility decision, not a prerequisite hidden inside the spike.
