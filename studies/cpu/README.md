# Remaining Agent CPU attribution

These bounded studies separate collection, cached publication, fleet admission
and presentation. They never call a provider action or alter selected services.
Only counts, sizes, code digests, CPU timings and public function names are
retained. Run through an explicit installed Python containing Mesh a20.

```sh
rtk proxy /selected/prefix/bin/python -I -B studies/cpu/profile_watch.py \
  --scope fleet --seconds 60 --spans --output /private/reader.json
rtk proxy /selected/prefix/bin/python -I -B studies/cpu/profile_watch.py \
  --workload publisher --host-scope snap --seconds 45 --spans \
  --output /private/publisher.json
rtk proxy python studies/cpu/units.py
```

The reader uses the real configured prepared human CLI, discarding its output.
The publisher workload constructs an owned factory, consumes one local cached
watch and requests one nonce-bound cached proof every five seconds. It excludes
Bridge/carrier work and closes its channels when the bound expires. Neither
workload is another independent native completeness comparison.

Synchronous spans measure thread CPU. Their exclusive values can be summed;
nested inclusive values cannot. Run `--profile` separately to diagnose recursive
call paths. cProfile substantially perturbs timing and may cause proof timeout
and resync, so its CPU/cadence is not a normal operational measurement. The CLI's
final revocation line is counted as a human render.

`units.py` samples cgroup CPU and stable process births for 45 seconds without
adding a reader. Explicit extra `--source agent` processes are reported separately;
they are not assumed to belong to a particular consumer or SSH connection.
Process and cgroup numbers overlap and must not be added. Created/lost process
CPU and generic SSH encryption/server work are not fully accounted for.

For source experiments, `--owner-root /isolated/source` overrides Observer only;
Mesh/dependencies still come from the selected Python. Owner paths and digests
identify the code. Distribution metadata can resolve a different source tree,
so it is not candidate artifact provenance.

`benchmark.py` uses owned synthetic IPC fixtures, two hosts and 250 rows per
host. It times 20 snapshot validations, 20 service wire admissions, and a complete
prepared consumer with four changed publications and three human renders each.
Fixture construction and one warm-up per case are excluded. Its wire case uses
the installed guard/parser pair before the new combined parser is available.

```sh
rtk proxy /selected/prefix/bin/python -I -B studies/cpu/benchmark.py \
  --output /private/baseline.json
rtk proxy /selected/prefix/bin/python -I -B studies/cpu/benchmark.py \
  --owner-root /isolated/source --output /private/candidate.json
```

Run timing trials serially, freeze runtime and harness bytes, keep tests/profile
runs separate, and compare cross-variant snapshot/display oracles. The accepted
study uses eight fresh processes in ABBA/BAAB order. Native source activity is
uncontrolled in live windows; synthetic savings do not establish fleet or
application savings, immutable artifact acceptance or managed rollout.

Results and follow-up ownership are in the
[CPU report](../../docs/evidence/2026-10-15-cpu/REPORT.md).

## Owned admission and explicit selection

`selected_read.py` compares the complete synchronous compose/admit/prepare/read
path using two owned synthetic Agent hosts and either 100 or 500 total records.
The selected bodies and whole-current-roster summaries have one full-body
semantic signature across variants. Running unknown-kind, child and system
records are included; no display limit is imposed. One warm-up and fixture IPC
setup are excluded. The fixed workload has 15 replacements and four reads each.

```sh
rtk proxy /baseline/prefix/bin/python -I -B studies/cpu/selected_read.py \
  --rows 500 --output /private/baseline.json
rtk proxy /candidate/prefix/bin/python -I -B studies/cpu/selected_read.py \
  --rows 500 --owned --mode selected --output /private/candidate.json
```

Use `--mode full` to retain full-row reads and isolate the owned-admission change.
Omit `--owned` to exercise strict raw admission. Optional source overrides are
`--owner-root` and `--mesh-root`; these identify experimental modules and do not
establish installed artifact provenance. Counted aggregate admissions and native
snapshot validations describe only the measured synchronous path, excluding
fixture setup. All variants retain complete raw snapshots, expiry checks and
proof arithmetic. Record process CPU and serial ABBA order, then compare exact
signatures and cleanup; do not interpret CPU milliseconds as live service CPU
or dashboard/device acceptance. Provider/collector/publisher/acquisition/SSH and
device costs are outside this workload. First selected read compiles the entire
generation, while later reads avoid decoding rejected full bodies.

`native_admission.py --output /private/native.json` measures twenty complete
Reader-side generic bridge admissions over 250 synthetic records. It compares
the legacy two-owner-validation operation with the optional combined codec
operation; strict ordinary Client admission remains separate. Setup/warm-up is
excluded and full returned records share a signature. The
[a6/a22 receipt](../../docs/evidence/2026-10-15-prepared-selection/REPORT.md) retains
serial installed-wheel trials and a separate diagnostic profile.
