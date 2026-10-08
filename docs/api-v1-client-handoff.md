# API v1 client handoff

API 1 remains the selected a16 baseline. New clients target the breaking
[API 2 handoff](api-v2-client-handoff.md), accepted against an independently
installed but unselected a3 candidate. Do not combine its wire 4/protocol 2
with the ordinary a16 endpoint.

Date: 2026-10-06. The independent Observer gate is accepted; this handoff does not
implement or select Agent Plus, RLCD, 349 or a terminal/mux client.

The [current service handoff](shared-observation-service-handoff.md) supersedes
this historical a2 installation tuple: normal Observer links and the user unit
now select a16 with native hints, while Agent Plus keeps its old frozen reader.
API 1, snapshot/watch 3 and write 1 remain unchanged; service protocol 1 is
separately prerelease. The current handoff records the exact a16 artifact,
endpoint, reconciliation cadences and client responsibilities. Choose that
explicit producer artifact/endpoint before client work. Native/cost and managed
rollout gates are recorded in the [delivery report](evidence/2026-10-07-native-delivery/REPORT.md);
producer selection does not accept a downstream migration.

The [daily-use repair pass](evidence/2026-10-07-daily-use-gap/REPORT.md) updates
the current producer without decoder changes: runtime-only Claude rows no longer
stick in partial history, saved Codex kind uses bounded passive detail, human ages
advance at display time, and missing cwd/config preparation has specific finite
codes. Tmux Plus work blocks Agent Plus implementation; keep its source and
installed reader untouched until the separate client gate resumes.

## Historical accepted producer and selected baseline

| Property | Accepted candidate |
| --- | --- |
| Package/source | `0.3.0a2` / `7ffbe246e6bac2c9d320328ce639b833b3a73bfa` |
| Wheel SHA256 | `98ce1f9203f97c13adc2d19cb11bf8f13a0dc3889fc899debc94da1bf0b1430d` |
| Prefix, both hosts | `/home/bryan/.local/share/agent-observer/0.3.0a2-98ce1f9203f97c13` |
| Public versions | API 1; snapshot/watch 3; write 1 |
| Native scope | Snap Codex/Claude; Starship Codex; managed daemon plus individual TTY entry |
| Profiles | Snap Claude-history with source-only SDK; Starship core |

[Manifest](../artifacts/observer-0.3.0a2.json), [API](api-v1.md),
[wire 3](public-contract-v3.md), [writer](write-client-contract.md),
[public facade](../agent_observer/public.py) and
[producer evidence](evidence/2026-10-06-stable-api/REPORT.md) are the reference.
Canonical fixtures live under `tests/fixtures/contract-v3` and `write-v1`.
`scripts/check-public-api` is a separate jsonschema/CLI reader; the source check
passes 231 tests. CLI and Python public semantics are stable within these scopes.
No upstream release/hash is a client support filter.

At this a2 gate, normal Observer entrypoints remained a11/wire 2. Selected Plus is still `0.14.0a1`
with its frozen a3/wire-2 reader. Use explicit candidate paths and separate cache
roots during development. Its venv also contains old Observer console scripts;
putting that venv first in PATH can choose the wrong collector or deferred writer.
The archived wheel is under `~/.local/share/agent-observer/artifacts` on both
hosts; package/public release and hosted dependency availability are separate.

```sh
observer_candidate=/home/bryan/.local/share/agent-observer/0.3.0a2-98ce1f9203f97c13
"$observer_candidate/bin/agent-observer" api
"$observer_candidate/bin/agent-observer" list --host-scope snap
"$observer_candidate/bin/agent-observer" snapshot --host-scope snap --provider codex --provider claude
"$observer_candidate/bin/agent-observer" watch --host-scope snap --interval 2 --count 3
ssh starship /home/bryan/.local/share/agent-observer/0.3.0a2-98ce1f9203f97c13/bin/agent-observer list --host-scope starship --provider codex
```

These reads are passive and need no session restart. Source a1 failed the native
Claude local-command age case; do not select its artifact.

## Consumer rules

| Input | Rule |
| --- | --- |
| Identity | Preserve the full host/provider/store-namespace/native-kind/native-ID tuple. Validate reached host authority; never merge by UUID alone, title, PID, cwd or project key. |
| Kind/title | Exclude only confirmed children; unknown stays visible. Reconcile fresh classification before retention. Title is bounded native provider metadata or UUID fallback, not an Observer-generated preview or identity. Codex can settle its name after a completion callback. |
| Runtime/phase | Running, parked and unknown are distinct. Phase is blocked/waiting/working/unknown. Blocked is approval or question. A completed turn can still be running; a missing worker or partial row cannot prove parked. |
| Health/coverage | Preserve each source and dimension. Failed hosts/providers retain healthy siblings. Capability predicates are context-scoped and are not permission or a known fact for every row. |
| Activity/order | Use current `activity.at` or explicitly stale `lastKnownAt`, never refresh/create/mtime. Default attention: blocked, waiting, working, unknown, then descending activity and full identity. Missing/clock-ahead values stay explicit. |
| Project | Recorded cwd, root/relative path and Git context have provenance. Only explicit mappings join projects across hosts. Context categories are UI policy, independent of provider/host. |
| Watch | Snapshot/change/resync replace the view; heartbeat retains it; gap marks uncertainty. Track stream UUID and revisions; reconnect begins a new epoch. No completion replay or cross-host event ordering. |
| Reasons | New finite codes are diagnostic. Unknown codes do not become idle, successful, stopped or action authority. |

Use `agent_observer.public` for pure parsing/validation/selection, or the public
JSON CLI with exported schemas plus semantic validation. Other Python modules,
private stores, collector internals and native proof scripts are not client APIs.
Human output and doctor formatting are diagnostic. Wire 3 is an intentional
cutover: reject old inputs and reset/version the consumer cache; no v2 converter
or parallel legacy discovery stack is supplied. Provider updates alone do not
reset the public wire/cache.

Claude parked is accepted only for terminal done/stopped idle jobs plus complete
stable inventory and positively absent matching workers. Saved-only absence,
Codex parked inference, generic Claude dialogs/transient helper ancestry and
current-client binding retain explicit limits. The newer a8 predicate accepts
verified foreground exact input waits as blocked/question and is now selected.
Equal titles are valid. Rename,
resume and local UI commands do not renew conversation age.

## Optional write client

Read-only consumers need no action client. Plus can use the separate public
writer on the owning host: prepare is passive, execute and TTY enter are explicit
actions. Pass opaque short-lived plans unchanged; bind/revalidate host route,
executable, config, cwd, native runtime and refreshed identity/job mapping.

Interpret status, effect, requested/resulting identity and handoff together.
Codex execute can return a prepared TTY entry without creating a session. Claude
saved Resume may confirm creation of a new UUID. A confirmed effect survives a
viewer failure; uncertain launches must never be retried automatically or routed
elsewhere. Entry success is native process replacement, not a JSON success
receipt. Make deferred terminal-entry errors visible to the user.

Plus retains Host Mesh, cache/presentation, terminal association and route policy.
Tmux Plus owns terminal/window lifecycle. Historical tmux options and attach
counts do not bind the current conversation or grant session-specific focus,
Close or group actions. OpenCode stays removed. Observer producer defects found
by a client reopen a separate checkpoint with an exact public reproducer.

## Separate client acceptance

1. Freeze producer/reader/client tuples and fixture conformance; migrate wire and
   cache together using private cache roots.
2. Validate age/order, parked/unknown labels, duplicate titles, child retention,
   partial host/provider failure, watch gap/reconnect and selection preservation.
3. Prove single native New/Resume and delayed TTY rejection on both Snap providers
   and cross-host Codex, without reconstructing native argv in the frontend.
4. Review artifact/managed selection separately; then prove real picker launches,
   Kitty/tmux association, graphical focus/Open and remote behavior.

RLCD selection/rendering/transport and physical readability stay in its own repo.
349 consumes desktop notifications, not provider state or transcript lookups.
A future Kitty mux client can reuse this same read boundary and optional writer;
its current-view binding must be independently proved. Networking is deferred.
