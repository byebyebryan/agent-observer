# Prepared Agent read acceptance ledger

Execution authorized by the user on 2026-10-13 local / 2026-10-14 UTC under the
[R0–R6 plan](../../prepared-read-client-plan.md). This ledger distinguishes
source, artifact, native, operational and downstream gates.

## R0 — installed cadence

Both endpoints still select Observer 0.7.0a1 / Mesh a17, Agent v3, API 4,
snapshot-watch 6 and Service 4. The private Mesh a18 wheel matches its accepted
SHA-256 `035f0a54a06581e702ad79cce93ecf56f3d5dcf8d28535b533c0098e97ae2098`.
Prepared interface 1 / SDK 1 and the exact Agent v3 descriptor are present.

Two bounded 60-second cached fleet observations used the installed
baseline, existing authority and no route writes. The clocks/windows differ;
they are cadence observations, not an AB performance comparison or an
independent native inventory census. No raw provider/observation payload is
retained. The [probe](../../../studies/prepared/cadence.py) records counts and
shape only and closes its owned iterator/guard.

| Origin | Replacement views | Native view changes Starship / Snap | Approximate 1 Hz reads per replacement | Connections after |
| --- | --- | --- | --- | --- |
| [Snap](snap-cadence.json) | 20 | 4 / 3 | 3.00 | 0 |
| [Starship](starship-cadence.json) | 17 | 3 / 2 | 3.53 | 0 |

The final sampled inventory was 97 Snap rows and 386 Starship rows. Replacement
views include warming/proof delivery updates; native revisions changed less
frequently. The benchmark must include all admitted replacements, not only
native changes, and include roughly three reads per replacement as the observed
device-consumer workload. Actual RLCD selection and physical CPU remain separate.

## R1 — additive owner interface

The [read interface specification](../../prepared-agent-read-interface.md)
binds static compilation to current AgentProfile semantics and provides a small
optional PreparedAgentWatch. It caches original header/source context once per
replacement, exports owned current rows through Mesh, and keeps raw exports
explicit. It adds no source health vocabulary or dashboard policy. The initial
CLI opt-in is `mesh watch --human --prepared`; existing calls remain independent.

## Remaining gates

R2 compiler/helper implementation and certification; R3 full changing-watch cost
and allocation decision; R4 immutable CLI/native acceptance; R5 reader-only
selection and RLCD handoff; R6 independent exact release/publication evidence.
No new live package or downstream selection is accepted by R0/R1.
