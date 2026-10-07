# Shared-service implementation evidence

Date: 2026-10-06. Execution in progress; final sustained/lifetime outcomes follow.
This is an Observer producer checkpoint. No frontend, notification hook, normal
unit/link selection, ordinary provider action or physical host suspend occurred.

## Source and candidates

- B1: `93121fb`, pure separately prerelease service protocol 1, bounded strict
  request/frame codecs, schemas and stream guard. API v1 facade remains unchanged.
- B2: `398e763`, source leases, conservative reconciliation, independent fair
  jobs, private sockets and bounded shared immutable fan-out.
- B3–B5: `69715f5`, existing-only owned workers; runtime/history adapter split
  and indexed exact identity composition, preserving direct collection defaults.
- B6: `06c1200`, explicit cached CLI, foreground service, manifest-v2 extension
  and immutable `0.4.0a1` candidate. Wheel SHA256
  `a5261577bdbfdbe7fbe950682bae97aedc05da90014f5a126feb4b4c126fd2f1`.
- Worker repair: `1e2f5fe`, `0.4.0a2`, owned nested SDK group plus unreaped-leader
  cleanup. Wheel SHA256
  `c08aa4e0cd6703c2f85136c880c00d8852b65a39aae589836f193374d910a366`.

A1 artifact receipts: [Snap](artifact-snap.json), [Starship](artifact-starship.json).
A2 is installed separately in
`/home/bryan/.local/share/agent-observer/0.4.0a2-c08aa4e0cd6703c2` on both hosts.
Snap uses source-only Claude SDK 0.2.163; Starship uses the core profile.
This SDK reproducibility pin is unrelated to daily native provider support.

The native contexts inspected were Codex managed 0.160.1 on both hosts and
Claude 2.1.291 on Snap. Compatibility uses required predicates and actual
executable/endpoint/birth ownership, never a version/hash allowlist.

## Controlled source and delivery checks

Tests exercise actual Unix sockets and owned fake-source subprocesses:
initial warming, private endpoint/singleton, strict fragmented/incomplete input,
request/write deadlines, cached readers without extra jobs, immutable partial
frames and explicit coalescing gap/resync. State tests cover source isolation,
expiry without events, preserved evidence clocks, changed native context and
partial inventory retention. Scheduler tests cover fairness, deadlines, dirty
storms, generation rejection and bounded retry.

The maximum-frame test decodes an actual valid near-8-MiB, 4096-row service
snapshot. The actual encoded-body admission path handles sixteen distinct
pinned bodies while enforcing the 64-MiB global budget by disconnecting slow
peers. This is encoded retention acceptance, not a claim that total decoded
Python state/worker RSS equals that bound.

Review found a nested SDK helper could escape the outer deadline because it
started a new session. A2 keeps it in the verified collection-worker group.
Direct SDK history still owns its independent helper group. Deadline and exited
leader tests use real subprocesses to prove helper termination and leader reaping;
cleanup never signals a native provider group. Latest full check at that repair:
266 tests, one optional independent-jsonschema skip; 64 Markdown files passed.
Independent JSON Schema validation also passed separately against an installed
A2 schema and actual service frame. Installed pure imports load no collectors,
provider image inspectors or write client.

## Ordinary native comparison

[evaluate-observation](../../../scripts/evaluate-observation) imports no Observer
module. Its existing-only independent Codex RPC and Claude registry/job/history
references bracket installed CLI reads. A new explicit service-socket option
unwraps the service view; ordinary read/list/show/doctor projection checks remain
additional regression evidence, not the native reference.

A1 [Snap comparison](ordinary-snap.json): all 51 Codex identities and supported
fields matched, including three loaded phases. Claude matched 30 independently
known identities, six runtime states and supported phase/title/kind fields.
One Claude activity timestamp was newer than the initial service history sample;
this is expected saved-metadata cadence lag, not renewed runtime-derived age.
One additional unknown-runtime history UUID was unproved by the independently
bounded scanner. That row is unresolved, not established as a false session.

A1 [Starship comparison](ordinary-starship.json): all 96 Codex identities and
supported fields matched, including eight loaded phases. Saved/unloaded runtime
and unproved classification remain explicit, rather than inferred parked.
Native references have their own history and state coverage limits recorded in
the JSON receipts. A2 final comparisons remain a separate installed checkpoint.

## Disposable native and user-unit checks

A1 installed service native cases passed [Snap](native-snap.json) and
[Starship](native-starship.json): new/native TTY entry, native conversation age,
rename/housekeeping preservation, exact saved/live Resume and owned Codex
outage/recovery. Snap includes required Claude entry/age/resume. The tests ran
inside verified user/mount/PID namespaces with private tmp and masked ordinary
stores/CLI images. They discard terminal/provider output and persist predicates.

The initial direct fixture assumed waiting plus an activity clock meant turn
completion. Mixed service component samples invalidated that assumption; the
service fixture now requires explicit terminal outcome before its independent
native completion-clock assertion. Consumers must keep phase, activity and
outcome separate. Another failure used a direct-read one-second recovery wait;
service validation now allows the configured read cadence. These were proof
assumptions, not accepted provider actions or invented completion mappings.

An owned transient user unit ran on each host with explicit candidate/socket,
Type=exec, NoNewPrivileges and UMask=0077; no enable/linger operation occurred.
[Snap receipt](unit-snap.json) confirms native-visible stores, UID/time domain,
accepted runtime/history reads and inode-aware socket cleanup. Both initial
30-second units stopped and were collected. A2 unit acceptance follows separately.

## Sustained and lifetime gates

A1 and A2 each have 30-minute, three-healthy-reader plus never-read-peer runs
on Snap and Starship. The proof measures 100 installed cached reads, payload
size, publisher plus reaped-child CPU, aggregate RSS/FD/process peaks and source
job receipts. Current results are pending until the corresponding run completes.
Client/reference/proof processes are outside the service CPU accounting; an
active unreaped job at a measurement bookend may slightly undercount its final
CPU. No full-host idle claim is made while ordinary work continues.

Paired A2 Codex retirement tests continuously observe a private store at the
20-second runtime cadence while probing its separate control only at bootstrap
and retirement bookends. Both stores run identical inspected native bytes.
The [primary lifecycle documentation](https://learn.chatgpt.com/docs/app-server)
describes a 30-minute no-subscriber/no-activity grace. The installed outcomes
remain pending; documentation alone does not establish the installed policy.
If the control retires and the observed thread remains loaded, the producer
lifetime gate fails. If neither retires, the native retirement predicate remains
unproved. This proof does not accept Claude idle-retirement semantics.

Physical suspend/wake remains pending. Fake sleep-inclusive clock expiry is a
source logic check. Optional native push/hook inputs, networking/remote streams,
notification publication, consumer migration and normal service selection have
independent follow-on gates.
