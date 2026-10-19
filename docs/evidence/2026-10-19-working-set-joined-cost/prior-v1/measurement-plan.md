# Joined canonical producer and Mesh SDK cost plan

Status: frozen preparation for primary review. No fixture endpoint, producer
worker, functional run, or timing trial has been started from this directory.
The runner remains inert unless `--run-reviewed-trial` is explicitly supplied.

## Pinned inputs and scope

- Observer: immutable export `final-source-b176ac06`, commit
  `b176ac06b39daeead4be0a33ff9d781304091fe0`, manifest SHA-256
  `c6128a1090e0d36c761e6442dcac3ec3312c07969afc5d4b641f87ca4e94b877`.
- Mesh: immutable export `final-mesh-bfa91a69`, commit
  `bfa91a6936a089d37c1a83752d3267148ba7dc69`, manifest SHA-256
  `d9d9c97f3171c0f6ec3bedcebafad86ee0d16e58b22e5024dbae1a79f5ad7f6a`.
- V6 private process/endpoint/cleanup helper SHA-256:
  `e2ca768a31085cdae261d10095d6db7dca7cbfbf0368c7d70b2869d548f92a01`.

The case joins the unpatched b176 canonical API 4 producer and parent parser
with full and registered working-set Mesh reads on one accepted `ServiceState`
sample. It is a controlled synthetic fixture, not native-provider evidence.
The runner checks every loaded project module against the immutable source
manifests before it starts the disposable endpoint. The copied Python ELF and
private `pyvenv.cfg` make the real endpoint inspector qualify the fixture
through the normal control symlink, socket UID/mode, `SO_PEERCRED`, `/proc` exe
identity, and listener inode checks.

## Input and accepted-source work

Each trial constructs 500 synthetic distinct thread/root identities using only
metadata from the existing `test_codex_snapshot.native` fixture factory:
2 loaded rows (one `active`, one `idle`) and 498 saved `notLoaded` rows. The
saved set has 2 recent parked rows and 496 old parked rows. All 500 turn records
use `itemsView=notLoaded` and empty `items`; the fixture rejects prompt, title,
preview, or tool fields. The expected current 72-hour union is 4 rows. Both full
identity census and thread-ID/session-root/status/activity joins are checked.

The canonical source limits stay unchanged: 1,000 catalog rows, 1,000 saved
classifications, and 512 loaded rows. Thus the route's maximum populated union
is 1,512. This trial uses 500 total rows; it makes no 2,000-row completeness
claim. The actual 10-second worker timeout and default 2,000 ms runtime / 60,000
ms history scheduler intervals are checked. Three generations use fresh
default schedulers and an explicit controlled burst. This does not claim
ordinary cadence performance and does not renew or extend source TTLs.

For each generation, the producer's real `Runtime._start_worker` launches the
pinned `_service_worker.py` with its exact `-I -B` argv. The runner drains the
pipe to EOF, waits for the real `_exit_status` WNOWAIT observation without
reaping the child, bounded by the remaining original `job.deadline` (`state.clock`)
and the case deadline, then calls the unchanged `Runtime._complete` once. That
method retains the source order: WNOWAIT exit check, owned process-group stop,
normal wait, strict `parse_snapshot`, then the single `State.accept`. The
wait4 hook only records direct-child user/system rusage at that normal wait.
Parent parsing and accepting are not invoked a second time.

## Paired public reads

One state is served by the actual local IPC Runtime with collection disabled;
a separate default canonical producer Runtime collects. The same accepted
current sample feeds the two public Mesh stacks. Each generation admits four
fresh full-profile watches and four fresh working-set watches; every watch
performs ordinary Reader, Publisher, proof, and facade work, then retires and
closes. Profile order is full then working-set in replicate 1, and working-set
then full in replicate 2. There are 24 admissions and retirements per trial.

The full consumer's existing `full_consumer_rows` selection runs inside the
full-profile CPU window. Expected-ID, row census, DTO digest, same service ID /
view revision, complete working-set coverage, final-row, and selected-body
checks follow the timed window. Both profiles must join the same service and
view revision, preserve the same four selected DTOs, and report a complete
current 72-hour union. The selected body must be at most one quarter of the
full 500-row body. Reads reuse the current accepted sample; no synthetic
`State.accept` clock is introduced. The already detached full and selected row
collections are retained by reference during timed reads; the post-window
oracle validates then removes them before writing the compact receipt.

## CPU accounting

For the measured three-generation loop, `P` is continuous parent process CPU
from `process_time_ns`, including its runtime thread and all Mesh/Reader work.
It includes harness-side output capture and checks performed inside the read
windows; no parent CPU is subtracted as oracle overhead. `F` and `W` are the
parent CPU windows around the four full or four working-set admissions per
generation. `C` is the sum of direct canonical-worker wait4 user + system CPU
for the six runtime/history children. `S` is the disposable fixture server's
full-lifetime direct wait4 user + system CPU, added once conservatively; it
includes its startup and endpoint-qualification time. Owner cleanup occurs
outside `P` and is reported separately.

The observed joined pair is `P + C + S`. The report also derives two
same-fixture profiles: `full = (P - F - W) + C + S + F` and
`working = (P - F - W) + C + S + W`. These derived values reuse one common
producer and one server cost; they are not two independent observed runs and
must not be described as such. Parent, worker, and fixture-server CPU remain
separate in the receipt. Python GC must be normally enabled; the harness does
not call `gc.collect` or disable GC.

## Bounded trial matrix and commands

There are four trials total, with no warmup: `py311-r1`, `py311-r2`,
`py314-r1`, `py314-r2`. Each has a 300-second outer deadline and the existing
10-second worker deadline. Each run self-acquires
`/home/bryan/.cache/agent-active-feed-cpu.lock`; do not hold that lock outside
the runner. If busy, wait for it to become free before starting. A pre-existing
receipt causes a hard failure; do not overwrite it. Stop the matrix at the
first mismatch, nonzero result, or cleanup failure; do not retry a failing
case or broaden the matrix without review.

Commands, only after primary approval of this frozen harness and plan:

```sh
rtk proxy /home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python joined_sdk_trial.py --run-reviewed-trial --interpreter py311 --replicate 1
rtk proxy /home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python joined_sdk_trial.py --run-reviewed-trial --interpreter py311 --replicate 2
rtk proxy /home/bryan/code/mesh-plus/.venv/bin/python joined_sdk_trial.py --run-reviewed-trial --interpreter py314 --replicate 1
rtk proxy /home/bryan/code/mesh-plus/.venv/bin/python joined_sdk_trial.py --run-reviewed-trial --interpreter py314 --replicate 2
```

The selected interpreter is verified against the named interpreter pin before
setup. The run writes one mode-0600 receipt per interpreter/replicate under
this directory, records no native prompt/title/tool content, and removes only
its exact owned process, endpoint inode, and private run directory. If process
identity or cleanup ownership cannot be proved, the harness fails and retains
the private directory.

## Validation performed before review

Offline validation is limited to source pins, source cap and lifecycle AST
guards, pure fixture-shape construction/parsing, expected 72-hour union
arithmetic, and protocol-census arithmetic. It starts no endpoint, worker,
collector, or timing window. Frozen file digests and command results are in
`preparation-receipt.json`.
