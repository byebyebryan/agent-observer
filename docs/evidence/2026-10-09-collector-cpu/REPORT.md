# Collector CPU attribution

The main cause is the a11 runtime-only retention reconciliation, added in commit
`4f99e0daa5d1b8b29d3ee19ef2129a4094048b1a`. It scans the entire receipt roster and
revalidates identities on every service-loop iteration. Consistent live samples
place 94.9% of Snap's captured Python execution and 97.2% of Starship's inside
`ObservationEngine._retire_runtime_only()`. This is a performance defect in the
shared core; fixing it does not require changing the observation contract.

This pass profiles the existing collector and updates the research operator.
It does not implement or deploy a producer repair. No provider, collector or
Mesh service is restarted, no settings are changed, and no attachment/client
inventory is queried.

## Live CPU measurements

Percentages are fractions of one logical CPU core. Root CPU comes from the
collector's own `/proc/PID/stat` user/system ticks. Owned-helper CPU is the
subtree total minus root CPU, including live and reaped descendants. Provider
daemon, Mesh bridge, profiler and SSH server CPU are outside this measurement.
Short process handoffs can introduce small subtree-accounting races.

| Host and window | Seconds | Collector root | Owned helpers | Total |
| --- | ---: | ---: | ---: | ---: |
| Snap, nonblocking profile | 91.09 | 46.76% | 10.75% | 57.50% |
| Snap, consistent GIL profile | 61.43 | 47.97% | 10.13% | 58.10% |
| Snap, no profiler attached | 60.76 | 50.89% | 11.87% | 62.76% |
| Starship, nonblocking profile | 92.63 | 38.01% | 1.00% | 39.02% |
| Starship, consistent GIL profile | 61.04 | 35.73% | 0.82% | 36.55% |
| Starship, no profiler attached | 61.02 | 36.66% | 0.89% | 37.55% |

These are sequential ordinary-workload windows, with the corresponding host
windows run concurrently. No watch clients were added. They establish persistent
cost and root/helper attribution, not matched incremental profiler overhead or
an idle-host baseline. The earlier ten-minute 54.66%/36.73% totals remain
historical sustained evidence; today's short-window totals vary with live work.
Almost all measured helper CPU was accounted for in the root's reaped-child
counter. Exact per-provider/per-component helper attribution remains open.

The collector remains `0.5.0a11-b1b755c8df0d4676` on both hosts. Snap uses Python
3.12.8; Starship uses Python 3.14.7. PID/start-tick authentication stayed unchanged:
Snap `2165818/57600605`, Starship `3096121/57642006`. Installed source hashes and
per-second counters are in [Snap](collector-snap.json) and
[Starship](collector-starship.json).

## Live stack attribution

[py-spy](https://github.com/benfred/py-spy) sampled only the authenticated collector
root, at 79 Hz, without subprocess sampling or local-variable capture. Initial
90-second nonblocking captures had substantial read errors: Snap 857 errors with
2,545 samples, Starship 1,031 errors with 1,692 samples. One corrupt Snap stack
was discarded. These are secondary evidence because incomplete reads can bias
the distribution.

A second 60-second consistent capture, restricted to GIL-holding threads, obtained
2,348 samples with one error on Snap and 1,763 samples with zero errors on Starship.
Consistent capture briefly pauses the collector for stack reads; providers are
not attached or profiled. The following shares describe captured Python execution,
not an exact partition of all OS CPU time. Inclusive shares overlap.

| Function in consistent samples | Snap | Starship |
| --- | ---: | ---: |
| `_retire_runtime_only` | 94.93% | 97.22% |
| `identity_key` | 95.49% | 96.60% |
| `validate_shape` | 95.70% | 95.24% |
| Worker completion `_complete` | 5.83% | 3.29% |
| Publication `publish` | 3.96% | 1.47% |

The dominant path is `Runtime.run -> ObservationEngine.expire ->
_retire_runtime_only -> identity_key -> validate_shape`. Validation recursively
checks five identity fields, including per-character Unicode control checks,
type/field checks and regular expressions. Retention rebuilds saved/current
identity sets, checks rows in both receipts, and calls `RuntimeOnlyRetention.prune`,
which builds another validated identity set. Saved rows are protected from
retirement but still incur these scans and validations.

`Runtime.run()` calls expiry every iteration. Its selector's 50 ms timeout is a
maximum idle wait, not a fixed 20 Hz schedule: work takes additional time and
worker pipes, hints or peers can wake it earlier. Actual iteration frequency was
not counted. Full scans also occur during publication. The installed line
numbers in JSON refer to a11, which differs from current checkout line numbers.
Raw stack files are not copied into repository evidence; retained data contains
only bounded function/file/line metadata, counters, hashes and coverage notes.

## Exact-interpreter cached-data comparison

The controlled studies load one cached Service 2 view through the installed a13
CLI, then run entirely in memory with the a11 collector's interpreter and package.
Python isolated mode (`-I`) prevents the checkout from shadowing installed code.
The installed engine hash is identical on both hosts:
`a4bae205524331ebc811a2aaf6d129767487d415c3f402c2ef8bb4eebed4bfb1`.

Each provider's merged cached roster is replicated into runtime/history receipts
at a fixed clock. It is an approximate workload replica, not extraction of the
running service's private receipt shapes. Both cached rosters contained only
saved rows and had zero retirement deadlines, so no row could be retired.

| Host | Rows | Identity validations per expiry | Full scan, ms/call | Trusted identities, ms/call |
| --- | ---: | ---: | ---: | ---: |
| Snap, Python 3.12.8 | 128 | 768 | 56.842 | 0.694 |
| Starship, Python 3.14.7 | 354 | 2,124 | 37.359 | 0.879 |

Unprofiled full scans consumed 11.368/7.472 CPU seconds across 200 calls.
Keeping the scan but replacing repeated identity validation with direct tuple
construction in the isolated, already validated replica reduced this to
0.139/0.176 seconds. Skipping the scan entirely reduced 200 calls to
0.000274/0.000092 seconds. A separate 50-call cProfile capture records millions
of character-check operations. Inclusive profiler times are reported separately
from the unprofiled measurements and must not be mixed.

These counterfactuals identify avoidable repeated work. They do not establish a
safe production patch, retirement parity, an exact live post-fix CPU target or
permission to remove public input validation. The original Snap study used a
different interpreter; its code hash matches but its timing is not the exact
running collector's cost. Host, workload and interpreter differences also prevent
a causal cross-version comparison. Fresh receipts are in
[Snap](retention-snap-exact.json) and [Starship](retention-starship-exact.json).

The extended [research operator](../../../scripts/study-retention-cost) now emits
Python provenance, per-call timings, identity counts, inclusive hotspots and the
trusted-identity counterfactual. These receipts were produced by its temporary
instrumented precursor. To repeat against an installed collector, use its own
prefix's interpreter with `-I`, the normal read CLI, and a temporary output path:

```sh
~/.local/share/agent-observer/0.5.0a11-b1b755c8df0d4676/bin/python -I \
  ./scripts/study-retention-cost --host snap \
  --cli ~/.local/bin/agent-observer --output /tmp/observer-retention-cost.json
```

## Repair gate and preserved operations

The next producer pass should cache validated identity keys/sets at receipt
admission or replacement and reconcile retirement only when a candidate deadline,
lease expiry or relevant receipt change requires it. Cheap lease checks must
remain independent from roster scans. Do not reduce discovery cadence or omit
saved history to hide this cost.

Keep public validation, positive saved/current protection, fixed unsaved
deadlines across partial reads, context replacement and source-failure semantics.
Prove old/new engine parity, then independently accept an immutable collector
against native sessions on both hosts and repeat the sustained ten-minute cost
gate before selection. The [producer follow-up](../../collector-cost-follow-up.md)
records this gate. The remaining helper CPU deserves separate attribution if it
remains material after the core repair; Mesh reader/bridge costs stay a separate
networking checkpoint.

Post-profile cached reads remained available: Snap 128 rows, current Codex
runtime/history and accepted partial Claude runtime/history; Starship 354 rows
with current Codex runtime/history. This is read-health evidence, not a new native
provider acceptance. Collector restart counters remained one on both hosts;
Mesh bridge counters remained zero, with PIDs `2181472` and `461500`. Source,
reader, publisher and provider selections remained unchanged.
