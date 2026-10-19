# Final working-set owner resource evidence

This packet brings together three source-only checks against the final Observer
source revision `196a8e2bd114f90aae82c4ee79559db511b9dce7`: the private ledger
screen, the 24-trial owner CPU comparison against accepted A7, and the 14-generation
slow-reader pressure run on Python 3.14 and 3.11. It records outcomes and limits;
it does not accept a native provider, installed service, SDK/Reader, deployed
consumer, heap/RSS bound, or production role selection.

The receipt pins sources, exact lexical Python paths, seed/helper and runner
hashes, copied report hashes, and cache provenance. `summaries/` contains the
compact scalar reports; `runners/` preserves the executed ledger and pressure
scripts, plus the CPU wrapper. The source export and row-shaped synthetic seed
are not copied into this packet. Their commits, manifests, hashes, and original
cache paths are recorded in [receipt.json](receipt.json). The packet contains
no provider payload, session IDs, titles, or cwd values.

## Results

The ledger screen used 2,000 synthetic rows over three accepted generations
for each requested selected count. Both interpreters completed all three
generations at 100 and 200 selected rows. Both explicitly returned
`projection_tracking_capacity` at 400, emitted no partial selection, and
committed a zero-entry ledger on refusal. The preflight refused while preparing
entry 306 on 3.14 and entry 303 on 3.11. At every captured budget checkpoint,
the actual old/candidate owner graphs fit within the recorded owner charges;
the largest observed old-plus-candidate graph union was 34,888 bytes. This is a
bounded graph check, not a process-heap or RSS bound. The 1 MiB tracking cap and
frame limits were unchanged. Recorded charge stayed below 1 MiB; the refusal
is the preflight decision for the next entry, not evidence of a cap overrun. A
400-row refusal remains a refusal, not a capacity pass.

The owner CPU screen ran 24 trials: 500 and 2,000 rows on each interpreter,
with A7, enabled candidate, enabled candidate, A7, and two current-disabled
controls in each group. Each trial excluded one warmup and timed six accepted
attempt/accept generations. Candidate median CPU was 18.13–19.55% below paired
A7 across these four groups, satisfying the stated maximum 25% owner-overhead
gate. The current-disabled medians were lower than the enabled candidate in
all groups, so the A7 comparison is a net source-version result; it does not
claim that enabling the working-set owner is free or faster than the current
disabled source. The measured interval excludes constructor/warmup, native
collection, parsing/reads, SDK, transport, and RSS.

| Python | Rows | A7 median CPU (ms) | Enabled candidate (ms) | Current disabled (ms) | Candidate vs A7 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3.14 | 500 | 643.112 | 517.416 | 392.971 | -19.55% |
| 3.14 | 2,000 | 2,611.376 | 2,112.928 | 1,635.565 | -19.09% |
| 3.11 | 500 | 746.374 | 605.215 | 486.961 | -18.91% |
| 3.11 | 2,000 | 3,058.786 | 2,504.136 | 2,060.832 | -18.13% |

The pressure fixture used 2,000 rows, a 256-character synthetic title and
1,024-character cwd, 10 active plus 10 recent-only rows, 14 accepted
generations under the 72-hour window, and the default 16-peer limit. Thirteen full-feed socketpair
readers held slow body pins alongside healthy full, active, and working-set
readers. The unchanged Runtime encoded limit was 67,108,864 bytes. The actual
counter peak was 59,727,787 bytes. The largest current-plus-stage request before
room-making was 70,228,632 bytes; Runtime room-making dropped the two oldest
pinned slow full-feed peers before admitting the reservation. Every reservation
then fit; each interpreter had 420 inventories (840 total), all matching their
counters and manual charges. Unique physical buffers stayed within the encoded
charge, peer/cache aliases matched, and healthy sibling readers remained live
with accepted stream guards and matching queued-body digests for all 14
generations. The 70,228,632-byte value is a pre-room request, not an admitted
counter value or an observed encoded-limit overrun.

At terminal cleanup, 104,950 encoded bytes remain intentionally owned by the
live ServiceState (`active` 43,813 and `working_set` 61,137); this is not a
zero-live-buffer result. Process RSS high-water values were 153,400 KiB on 3.14
and 153,484 KiB on 3.11. The saved per-generation RSS series include imports,
fixture/oracle/audit objects, DTOs, caches, sockets, and transient parsing.
They establish neither a heap bound nor an RSS limit or plateau.

The original cross-Python audit failure remains preserved in
[pressure-original-run-summary.json](summaries/pressure-original-run-summary.json):
it records 42 `cross_python_route_semantics` failures from requiring the three
route body hashes to match byte-for-byte. The reconciled report records the
actual difference and its cause: each fresh process creates a new
`uuid.uuid4()` `ServiceState.service_id` at `agent_observer/service_state.py:40`,
which is included in serialized service/support metadata. All three per-run
routes still passed `wireDigestMatchesQueuedParts` and StreamGuard checks for
every generation; accepted inputs and the captured logical row, DTO, and
coverage summaries match across interpreters. This packet does not claim
cross-Python full-frame byte parity or equality of unrecorded metadata.

## Reproduction and limits

The owner CPU trial runner is tracked at
`docs/evidence/2026-10-18-working-set/performance-source/owner_matched_with_disabled.py`
(SHA-256 `de84a21389790fb95207fdb0885e2e291c612ec7dbc3f2640691573b786ec13a`);
the seed builder and owner fixture helper are tracked alongside it. The
executed cache orchestration wrapper is copied byte-for-byte to
`runners/run_owner_screen-196a8e2b.py`; the exact 24-trial driver and report are
also pinned by cache path and hash in the receipt.

The copied ledger wrapper and child preserve the exact run-time bytes. They use
the recorded cache paths for the immutable source export, synthetic seed, and
fixture helper. `runners/ledger-source-screen-replay.py` is a separately hashed
configurable replay derivative: it accepts `--root`, `--seed`, `--helper`, and
`--count` so those inputs can be rebuilt in another checkout. It was not used
for these results. For example, run it once per selected count and interpreter:

```sh
rtk /path/to/python -B runners/ledger-source-screen-replay.py --root /path/to/196a8e2b-export --seed /path/to/regenerated-seed.json --helper docs/evidence/2026-10-18-working-set/performance-source/read_matched.py --count 100
```

The copied pressure driver and case preserve the executed scripts and cache
paths. The 196a8e2b pressure case is derived from the
earlier `resource-pressure/pressure_case.py` by three scoped changes: accept an
explicit matching full source/runtime commit pin, assert dropped peers release
their encoded body before room returns, and sample per-generation RSS. Its
original executed SHA-256 is recorded in the receipt. Replaying outside the
original cache layout requires rebuilding the immutable source export and
synthetic seed, then supplying the corresponding paths; the seed is omitted so
the packet stays aggregate-only.

No old source was replayed for the ledger results. The noted prior-candidate
frame comparison uses saved hashes only; its earlier candidate source export is
not present, so that comparison is not an old-source reproduction. The final
ledger screen itself independently records its complete/refused outcomes and
cross-interpreter frame-hash comparisons.

GC was disabled within the screen processes; no explicit collection was used.
No provider, daemon/service process, Mesh/SDK, external network, or device was
queried. This packet is source evidence for the recorded synthetic fixtures and
does not close native/provider, full pipeline, deployment, heap, or physical
acceptance gates.
