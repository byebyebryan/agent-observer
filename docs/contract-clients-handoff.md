# Contract and clients handoff

For the latest operational state and next producer checkpoint, read the
[2026-10-06 discovery/monitoring review](discovery-monitoring-contract-review.md).
Provider upgrades have reopened current-image monitoring/write acceptance;
watch/contract findings also need closure. The selected tuple below remains the
earlier exact-artifact baseline. The adjacent Agent Plus checkout's
`docs/observer-client-handoff.md` records client ownership and the renewed
producer gates.

Date: 2026-10-05. The regular primary-owned goal loop closed independent G1/G2
and the subsequent bounded Plus E8 consumer pass. Networking G3 remains deferred;
Plus retains existing Host Mesh composition. The [execution record](contract-clients-execution-status.md)
and [independent Observer report](evidence/2026-10-04-contract-clients/REPORT.md)
define the actual source/package/native acceptance and remaining capabilities.

The initial [operational pass](operational-execution-status.md) selected
the unchanged `0.2.0a3` producer tuple on Snap and Starship, including the global write
entry. It independently accepted installation/watch/recovery before consumer
proofs, then real Tmux/SSH New/Resume and selected passive/headless gates. The
baseline rollout section below is historical. The subsequent independent
[discovery repair pass](evidence/2026-10-04-discovery-repair/REPORT.md) was followed
by the [operational resilience pass](evidence/2026-10-05-operational-resilience/REPORT.md),
which selected Observer `0.2.0a8`. The subsequent independent
[evaluation repair](evidence/2026-10-05-evaluation-repair/REPORT.md) selects
`0.2.0a9` on both hosts. The subsequent
[stopped-runtime checkpoint](evidence/2026-10-05-stopped-runtime/REPORT.md)
selects `0.2.0a11`, preserving the Plus artifact and frozen reader. Use
that report and the managed tuple for current selection and rollback. Wrapper association, silent Plus Resume, age presentation
and graphical acceptance remain a separate consumer checkpoint.

## Delivered tuple

| Component | Source | Version | Selected prefix on Snap and Starship |
| --- | --- | --- | --- |
| Observer | `06af32d` | `0.2.0a11` | `/home/bryan/.local/share/agent-observer/0.2.0a11-999d45171adfc4c4` |
| Plus | `90e5b4f` | `0.14.0a1` | `/home/bryan/.local/share/rofi-agent-plus/0.14.0a1-8ba19a0eba87944a` |

Observer wheel SHA-256:
`999d45171adfc4c4e62fe57b417614c0814de2a556693a6d23bb97b45a0a8b65`.
Plus wheel SHA-256:
`8ba19a0eba87944aec2848542fb3ddcb91f3ccc33790ba42565928e18daa497b`.
Persistent wheels are under each project's `artifacts` directory beneath
`~/.local/share`. Observation/watch wire version is 2; write request/plan/result
version is 1. Snap's independent Observer environment has the source-built
Claude history SDK. Starship and both Plus environments are core-only.
Plus's own reader library remains Observer `0.2.0a3`, source `222c5bf`, wheel
SHA-256 `6aa793e6a0ba5ae37403f73999ea6e6d56bc8c21e5e4c7a10ac52cb946a45a3f`.
The managed gate checks this dependency independently of the selected producer
and verifies their unchanged public schemas before selecting the new producer.

Observer passes 212 tests and its documentation gate; Plus previously passed
309 tests and its full local source gate. Independent installed fixture conformance,
native entry/recovery and selected headless gates pass. Plus E8 evidence lives in its own checkout at
`docs/evidence/2026-10-04-observer-v2/REPORT.md`; no Observer code was changed to
make the consumer pass. No public push, dependency publication or release occurred.

## Use the Observer candidate independently

These calls address the immutable artifact directly and do not start missing
provider daemons or change the pilot links. The ordinary read/write commands
now resolve to this same artifact on the pilot hosts:

```sh
observer_candidate=/home/bryan/.local/share/agent-observer/0.2.0a11-999d45171adfc4c4
"$observer_candidate/bin/agent-observer" --version
"$observer_candidate/bin/agent-observer" list --host-scope snap
"$observer_candidate/bin/agent-observer" doctor --host-scope snap --json
"$observer_candidate/bin/agent-observer" watch --host-scope snap --interval 2 --count 3
ssh starship /home/bryan/.local/share/agent-observer/0.2.0a11-999d45171adfc4c4/bin/agent-observer list --host-scope starship --provider codex
```

For saved public fixtures, use `list/show/doctor/watch --input FILE|-` with no
provider stores. [The public contract](public-contract-v2.md) documents optional
`--workspace-config` roots and project mappings; these are explicit local inputs,
not inferred cross-host project identity. Last-conversation activity uses bounded
native turn/message metadata and orders before saved display caps. Missing clocks
stay unknown; creation ordering is an explicitly labeled alternative.
Sampled watch provides push updates, gap/resync and
heartbeats; brief native transitions can be missed. No hooks were added.

The [write client](write-client-contract.md) is separately available at
`$observer_candidate/bin/agent-observer-write`. Preparation is passive; execute
and native TTY enter are deliberate actions with guarded context/effect results.
New needs no existing row; Resume requires the complete current reference.
Do not treat a prepared plan or historical Tmux label as current attachment
authority. Current-store Codex saved discovery survives runtime failure, while
offline Resume remains guarded. Foreground Claude questions, saved-only runtime
absence, exhaustive legacy discovery, blank background readiness, ephemeral helper ancestry
and current-client binding remain explicit unsupported/pending capabilities.

## Prior rollout baseline

Before the contract/client rollout, the selected tuple was Observer `0.1.0a5-b68ebf4cefbd8b58` and Plus
`0.13.0a3-76f8a951e2975283`. Managed chezmoi templates selected the old read/Plus
entrypoints without a global `agent-observer-write` link. Candidate installation
alone did not perform that rollout.

Review a compatible managed tuple update for every selected target: Observer
read and write entries and both Plus entries, preserving the prior artifacts.
Render and apply scoped managed paths, verify source/installed hashes and exact
links, then test the picker and actual local/remote Tmux native entries. Observer
native operation proofs are independent; E8 used controlled Tmux responses/owned
PTYs and controlled Mesh authority. Desktop selection/focus and ordinary remote
write routing need their own acceptance. Use a separate consumer cache during
side-by-side candidate checks because v7 is a deliberate cache cutover.

Physical suspend/native transport-loss recovery, coordinator reopen, hosted CI
and public release remain separate gates. Plus hosted CI requires the pinned
Observer prerelease to be available. The current coordinator stayed available
throughout this loop and requires no restart to review or use independent reads.
Its deliberate reopen remains a final explicit transition, following the prior
[coordinator handoff](execution-handoff.md).
