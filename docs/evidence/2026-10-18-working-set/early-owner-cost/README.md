# Early owner CPU screen

2026-10-18. This is an early **synthetic diagnostic**, not the accepted-a7
comparison required by the [plan](../../../working-set-projection-plan.md).
It compares the same source family with the working-set owner disabled and
with its 72-hour window enabled. Every case has six accepted generations,
three fresh owners, GC disabled, and process CPU timing around attempt/accept.
Fixture construction and final outcome checks are outside timing. No native
collection, read/proof, transport, startup, RSS or installed acceptance is measured.

The fixture contains 100/500/2,000 eligible unknown-kind rows, a small running
set, an equally small recent parked set, and otherwise ten-day-old parked rows.
It is not a dense/burst/full-active workload. Original support and capability
metadata remain synthetic. Selected sets have 2/4/20 bodies and complete native
fixture coverage; a capacity refusal is never counted as a cheap success.

The six original outputs and `owner_cpu.py` are byte-preserved. Their added
owner medians were about 30.7%, 33.8% and 30.1%. R2 accepts a source root argument
and resets the constructor clock before each trial, fixing a diagnostic setup
asymmetry without rewriting the original outputs. It executes disabled/enabled
before, then enabled/disabled after, once at each size; this is a small screen,
not a repeated or randomized performance qualification.

| R2 source | Rows | Disabled median ms | Enabled median ms | Added work |
| --- | --- | --- | --- | --- |
| e482 native component | 500 | 419.091 | 530.709 | 26.63% |
| current candidate | 500 | 401.410 | 527.250 | 31.35% |
| e482 native component | 2,000 | 1,657.250 | 2,163.165 | 30.53% |
| current candidate | 2,000 | 1,656.151 | 2,131.023 | 28.67% |

All four R2 cases remain above the early 25% screen. Variation between runs
prevents a timing-saving claim from this sample. The bounded source cleanup
removes one duplicate projection serialization and an unused decoded return
from the owning refresh; public acceptance still returns a detached snapshot.
Final recovery continuity is included in the byte check, including decimal
digit growth. No allocation estimate, cap or semantic requirement was reduced.
Full-roster classification and census work remain; this result does not start
an optimization campaign or accept the producer cost gates.

The [receipt](receipt.json) binds all sixteen raw scripts/outputs and verifies
every loaded project module: 25 for disabled cases and 30 for enabled cases.
Before outputs match immutable e48240d; after outputs match a detached copy of
the final measured runtime. Later pure client files are not reachable in this
owner benchmark. The final source manifest in the
[client record](../p2-client/README.md) identifies the same measured runtime.
No peer source, provider, service, selection, artifact or dark-delta state changed.
