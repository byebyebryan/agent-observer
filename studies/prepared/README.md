# Agent owner preparation qualification

These tools belong to Observer, using Mesh's accepted optional preparation
interface rather than a new transport/cache implementation. See the
[execution plan](../../docs/prepared-read-client-plan.md) and
[acceptance ledger](../../docs/evidence/2026-10-14-prepared-reads/REPORT.md).

`cadence.py` observes a bounded installed cached two-host watch. It records only
frame/native revision counts, inventory sizes and dependency provenance; no raw
provider/observation payloads, route writes or actions. A cadence observation is
not independent native completeness proof.

`check_artifact.py` checks every packaged Python/schema file against an isolated
committed source copy. Always build in that copy; an ignored `build/lib` directory
can otherwise resurrect retired files. Reject and preserve a mismatched draft
wheel before installation. Never overwrite an accepted artifact identity.

`compare.py` executes 96 fresh-process trials in two serial ABBA/BAAB blocks per
cell. Its Python must contain the exact installed Observer and Mesh wheels;
`measure.py` uses `-I` and imports owner runtime from that environment. Only the
owned fixture builder is loaded from this checkout. Inputs, source/SDK bindings,
schema admission counts, original leases and normalized active-row expectations
are checked separately before decision timing. Every changed replacement receives
full packaged-profile admission in both implementations.

```sh
rtk proxy /private/driver/bin/python studies/prepared/compare.py \
  --python /private/installed/bin/python --output /private/new-cost-directory
rtk proxy /private/installed/bin/python -I -B studies/prepared/measure.py \
  --mode prepared --hosts 2 --rows 8 --reads 1 --change native \
  --publications 1000 --memory
```

Run legacy and prepared memory cases separately from decision CPU. Report
steady/replacement/retired traced allocation and process RSS separately; prebuilt
synthetic input frames are excluded from tracing but included in process RSS.
Fixed admission time isolates churn allocation and does not prove real-time
freshness. Timing uses actual BOOTTIME and fails if original leases expire.

Timing includes construction, all admission/compilation, owned current results,
source-context handling/active selection and disconnect. It excludes fixture
construction, imports/warm-up, source acquisition, Reader/carrier I/O, serial,
firmware and dashboard policy. Native fixture updates change title/phase and
service ordering, including remote native proof digests; envelope cells change
reader ordering only. Synthetic proofs over owned IPC are not actual SSH proof.

Do not edit the timing harness or runtime while a decision matrix runs. Preserve
exploratory/failed runs separately and repeat decision measurements from frozen
installed bytes. No profile/owner preparation is automatically selected by a
successful matrix. Independent native daemon, fixed SSH, live read-selection and
downstream application proof follow in their own gates.

`compare_deployed.py` compares the old installed a1/a17 legacy tuple with the
complete a2/a18 prepared tuple over eight serial ABBA/BAAB trials at two hosts /
500 rows / three reads per publication. It copies the frozen harness to a
temporary directory, making only the prepared import lazy and omitting missing
old diagnostic files; fixture-root resolution is explicit. Timing/oracle/schema
checks remain unchanged. This separate upgrade result does not attribute SDK
improvements solely to Agent preparation.

`select_reader.py` verifies reader-only rollback/reselection and protected
controls without restarting services. It mutates only its explicit read CLI
symlink. `resources.py` runs four descriptive five-minute steady windows, excludes
ten seconds of startup, records owned CLI/SSH process birth/CPU/RSS/FD and unit
cgroup samples, then stops only its owned reader process groups. Existing
applications remain running. Remote SSH server costs and per-window publication
counts are not captured; summed RSS is not PSS or a strict memory budget.
