# Contract and clients handoff

Date: 2026-10-04. The regular primary-owned goal loop closed independent G1/G2
and the subsequent bounded Plus E8 consumer pass. Networking G3 remains deferred;
Plus retains existing Host Mesh composition. The [execution record](contract-clients-execution-status.md)
and [independent Observer report](evidence/2026-10-04-contract-clients/REPORT.md)
define the actual source/package/native acceptance and remaining capabilities.

The subsequent [operational pass](operational-execution-status.md) has selected
this exact unchanged tuple on Snap and Starship, including the new global write
entry. It independently accepted installation/watch/recovery before consumer
proofs, then real Tmux/SSH New/Resume and selected passive/headless gates. The
baseline rollout section below is historical; use the operational record for
current selection, rollback and morning acceptance.

## Delivered tuple

| Component | Source | Version | Selected prefix on Snap and Starship |
| --- | --- | --- | --- |
| Observer | `222c5bf` | `0.2.0a3` | `/home/bryan/.local/share/agent-observer/0.2.0a3-6aa793e6a0ba5ae3` |
| Plus | `90e5b4f` | `0.14.0a1` | `/home/bryan/.local/share/rofi-agent-plus/0.14.0a1-8ba19a0eba87944a` |

Observer wheel SHA-256:
`6aa793e6a0ba5ae37403f73999ea6e6d56bc8c21e5e4c7a10ac52cb946a45a3f`.
Plus wheel SHA-256:
`8ba19a0eba87944aec2848542fb3ddcb91f3ccc33790ba42565928e18daa497b`.
Persistent wheels are under each project's `artifacts` directory beneath
`~/.local/share`. Observation/watch wire version is 2; write request/plan/result
version is 1. Snap's independent Observer environment has the source-built
Claude history SDK. Starship and both Plus environments are core-only.

Observer passes 153 tests and its documentation gate; Plus passes 309 tests and
its full local source gate. Independent installed fixture conformance and native
entry proofs pass. Plus E8 evidence lives in its own checkout at
`docs/evidence/2026-10-04-observer-v2/REPORT.md`; no Observer code was changed to
make the consumer pass. No public push, dependency publication or release occurred.

## Use the Observer candidate independently

These calls address the immutable artifact directly and do not start missing
provider daemons or change the pilot links. The ordinary read/write commands
now resolve to this same artifact on the pilot hosts:

```sh
observer_candidate=/home/bryan/.local/share/agent-observer/0.2.0a3-6aa793e6a0ba5ae3
"$observer_candidate/bin/agent-observer" --version
"$observer_candidate/bin/agent-observer" list --host-scope snap
"$observer_candidate/bin/agent-observer" doctor --host-scope snap --json
"$observer_candidate/bin/agent-observer" watch --host-scope snap --interval 2 --count 3
ssh starship /home/bryan/.local/share/agent-observer/0.2.0a3-6aa793e6a0ba5ae3/bin/agent-observer list --host-scope starship --provider codex
```

For saved public fixtures, use `list/show/doctor/watch --input FILE|-` with no
provider stores. [The public contract](public-contract-v2.md) documents optional
`--workspace-config` roots and project mappings; these are explicit local inputs,
not inferred cross-host project identity. Last conversation activity remains
unavailable with the accepted native sources. Creation ordering is an explicitly
labeled alternative. Sampled watch provides push updates, gap/resync and
heartbeats; brief native transitions can be missed. No hooks were added.

The [write client](write-client-contract.md) is separately available at
`$observer_candidate/bin/agent-observer-write`. Preparation is passive; execute
and native TTY enter are deliberate actions with guarded context/effect results.
New needs no existing row; Resume requires the complete current reference.
Do not treat a prepared plan or historical Tmux label as current attachment
authority. General question/input detection, parked inference, offline Codex
discovery, foreground Claude readiness and current-client binding remain explicit
unsupported/pending capabilities.

## Prior rollout baseline

The ordinary selected tuple remains Observer `0.1.0a5-b68ebf4cefbd8b58` and Plus
`0.13.0a3-76f8a951e2975283`. Managed chezmoi templates select the old read/Plus
entrypoints; there is no global `agent-observer-write` link. Candidate installation
does not perform the rollout.

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
