# Read-only Observer retirement checkpoint

Source candidate: Observer 0.7.0a9 with Mesh 0.1.0a25, 2026-10-23. Publication and
installed host acceptance require their own receipts; this source note does not
claim either. Native provider managers own New/Resume and conversation control.

The current package removes agent-observer-write and its write implementation,
and withdraws the standalone active-feed native API, producer cache, Mesh
source/profile and prepared client. Old native requests receive a negative
service response with reason active_feed_retired. Old Mesh active-profile
identifiers are rejected before codec or endpoint selection, with no alias.

Working-set keeps the independent active branch and the recent-activity branch.
Full API 4/snapshot 6/Service 4, working-set 1 and their schema bytes, original
receipt rules, clock domains, limits and uncertainty remain unchanged. Shared
definitions live in projection_support and projection_fields. The retained
default-off sync experiment has private schema bases and a lazy internal
projection; ordinary full/working-set publication creates no active-only cache.

## Cached inspection

With the optional paired Mesh dependency installed:

```sh
agent-observer working-set list --host starship --scope local
agent-observer working-set list --host snap --source agent_working_set_work
agent-observer working-set watch --host snap --active --duration 30
```

The local socket defaults to the current user's mesh-plus-agent-working-set
bridge. Supply --socket for another local endpoint. Remote hosts use configured
Host Mesh routes; --host never adds a peer. The window must match the fixed
publisher policy, ordinarily 72 hours. List waits for one settled cached read;
watch is bounded to 60 seconds and defaults to 30. Both use the existing public
Reader and prepared working-set facade, start no collector/provider and take
no action. Human output shows exact identities, active/recent membership,
runtime/phase and coverage; it includes no titles, paths or conversation content.
The --active filter requires a current active-membership lease, not a stored
running label. Closing a command revokes its own current view and stream.

The developer JSON example now delegates to the packaged utility reader; that
diagnostic projection remains outside the stable wire contracts. Existing full
diagnostic list/watch commands retain their separate behavior.

## Historical compatibility

Published wheels, frozen schema definitions and dated acceptance remain intact.
Those records do not advertise support in this source candidate. Historical
artifact verification still understands old manifests; manifest version 6
requires the read-only entrypoints and independently verifies retired modules
and the writer command are absent from a new installation. Managed cleanup must
remove current selectors, sources and units explicitly, after surviving
consumer compatibility and recovery checks.
