# Agent Observer API v1

Date: 2026-10-06. Status: stable API v1 within the independently accepted
[a2 packaged/native subset](evidence/2026-10-06-stable-api/REPORT.md). This is a compatibility
policy for clients, separate from package versions and provider releases.

## Public surface

`agent-observer api` declares API 1, observation snapshot/watch wire 3 and write
wire 1. Bundled schemas describe structural validation; semantic validation is
also required. Schema-valid fields alone do not establish a valid identity,
current fact or confirmed write effect.

| Surface | API v1 promise |
| --- | --- |
| Read JSON | `snapshot`, `list --json`, `show --json`, sampled newline-framed `watch`; schema export for snapshot/watch |
| Write JSON | Separate `agent-observer-write prepare`, `execute`, `enter`, and request/plan/result schema export |
| Pure Python | The names in `agent_observer.public.__all__`: interface/schema export, bounded parsers, semantic validators, full identity/store keys, selection/order/listing and diagnostics |
| Diagnostics | `doctor`, history census, human text, timings and executable versions/hashes help operators; their text formatting is not a machine interface |
| Internal | Collector modules, adapters, worker/process readers and native proof scripts are implementation details |

`enter` replaces the process with a native TTY client on success; it does not
return a JSON success receipt. `execute` can prepare a TTY handoff without
launching a Codex session. A Claude background launch can have confirmed effects
even if its viewer handoff fails. Results preserve requested and resulting
identities separately; saved Claude Resume can create a different UUID.

Plans are opaque, short-lived context guards produced by the writer. Clients
pass them back unchanged and re-prepare after a rejected changed context. No
client may redispatch an uncertain launch automatically. The guard binds actual
executable/configuration/cwd and refreshed provider runtime/native job mapping;
it is not a lock, signed permission or transaction across the native TTY launch.

## Identity, state and metadata

Identity is the full host/provider/store-namespace/native-kind/native-ID tuple.
Host authority comes from the caller; the caller validates its selected route
and machine. Store namespace uses provider, exact config path, selector and UID.
Runtime birth and job IDs are separate. Equal titles/cwd/project keys or equal
UUIDs on different hosts never merge conversations. New profiles and networking
are separate capabilities, not inferred from host-local identity.

Runtime `running` means a loaded Codex managed context or verified registered
Claude worker. `parked` currently requires the Claude terminal-job and complete
absence predicate. Saved-only absence and Codex unloaded contexts stay unknown.
Phase is working/blocked/waiting/unknown. Blocked approval and question are
distinct. Runtime, worker, phase, attachment and latest outcome retain separate
health and clocks. Worker/TUI exit does not end a conversation. A current
completed outcome does not imply runtime readiness or present task success.

Title is bounded native metadata: explicit Codex name, accepted user-set Claude
registry/job name or SDK custom title, then `Codex <UUID>`/`Claude <UUID>` fallback.
It is display text, not an identity or uniqueness claim. AI-generated titles and
agent nicknames are not promised; no prompt/response preview is generated.

Current conversation activity uses explicit native turn/message event time.
Claude's reserved local-command envelopes and meta records are housekeeping;
ordinary slash-looking prompts remain conversation activity.
Creation and SDK file modification remain separate. Retained stale activity uses
`lastKnownAt`, original source and stale health; polling never renews that age.
Attention ordering is blocked, waiting, working, unknown, then most recent
current/last-known activity and full identity. Missing and clock-ahead ages remain
explicit. Consumers can choose presentation policy without changing evidence.

Source capabilities describe usable observation predicates in the sampled
context, not guarantees for every row or write permission. Coverage applies to
its declared saved/runtime scope. Partial scopes cannot prove missing sessions
stopped. Unknown classifications remain visible; only confirmed children are
excluded by default. Claude transient helper ancestry remains a stated limit.

## Compatibility, errors and recovery

Observation wire 3 explicitly replaces prerelease wire 2; no automatic converter
or legacy collector is provided. Adding/removing a field, enum value, provider,
or changing a field's meaning requires a new wire version and conformance corpus.
Clients reject unsupported versions/fields. Package patch releases may repair
implementation defects while retaining the documented semantics. New finite
reason/error codes may be added: an unrecognized code remains diagnostic and
must not become idle, successful, stopped or action authority.

Provider releases are diagnostic. Required native contracts select capabilities;
compatible daily updates require no hash/version registration. Own dependency
locks and artifact receipts remain reproducibility tools. Private provider fields
can change semantics without changing shape; independent CLI/native comparisons
remain necessary. No shape checker promises perfect upstream drift detection.

Malformed input/unsupported wire or invalid references yield exit 2 with bounded
JSON error metadata. Read success, including partial/unavailable sources, yields
exit 0 with per-source errors and coverage; zero exit alone does not accept native
coverage. Interrupt is 130. Argument parsing errors are operator usage errors.
Write results, rather than process exit alone, determine confirmed/uncertain
effects. Failure must not log raw native payloads, prompts, tool output or secrets.

Watch revisions increase within one stream UUID. Initial snapshot and
change/resync frames contain full views; heartbeat/gap contain none. Replace the
view on resync, mark gaps, and start a new epoch after reconnect. No native turn
event IDs, replay, lossless completion delivery or cross-host ordering are
promised. Bounds and stale retention are in the [wire 3 specification](public-contract-v3.md).

## Acceptance and handoff

The [execution record](stable-api-execution.md) tracks source, frozen artifact and
independent Snap/Starship native proof separately. API v1 stability accepts only
these documented scopes. New native predicates, notification event sources,
networking, graphical focus/Open and device rendering require their own gates.
Agent Plus and other clients consume public observations/write receipts; they
do not implement private provider discovery or select provider release versions.
