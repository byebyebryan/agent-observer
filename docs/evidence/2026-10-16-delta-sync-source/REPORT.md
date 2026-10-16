# Snapshot/delta sync source checkpoint

This is unfinished G1 source evidence on Starship, at Observer `100637b`.
Producer acceptance is **not granted**. There is no candidate wheel, package
selection, installed candidate, live service change or consumer acceptance.
G0's `ed771e5` / `a376bc84` appendix remains unchanged.

Implementation checkpoints are `82feed8` (native cache/local delivery),
`ca9d32d` (strict pure profile/read facade), `1be9f8e` (draft acquisition and
bounded header scanner) and `100637b` (owner allocation/removal work and matched
producer probe). These are isolated branch commits, not accepted releases.

The full source check passes 791 tests, without skips, plus Markdown/link/diff
checks. The focused Python 3.11 check passes 203 tests. Profile/read checks use
the in-progress Mesh source overlay; they do not certify a Mesh artifact or
freeze its pending codec/input APIs. Existing artifacts, normal services,
providers, Tmux, RLCD and 349 remain unchanged.

## Matched producer ABBA

[The probe](../../../tests/bench_sync_producer.py) uses a fixed native-shaped
Codex fixture and six accepted generations, with deterministic clocks and
incarnation. Every sample includes attempt diagnostics, common generation,
both sync views and full snapshot/projection/support/census oracle hashing.
Component timer overhead is included. The legacy process runs installed a7
with isolated Python; sync runs the source overlay. Both use Python 3.14 and
run serially under the existing shared CPU lock.

This measures producer generation only. It does not deliver a cold baseline or
measure IPC, publisher, SSH, Reader, facade, application or owned descendants.
Fixture construction and cold common/root construction are reported separately.
It is not installed candidate or end-to-end qualification.

| 2,000-row workload | Installed a7 median | Source median | Change | Result |
| --- | ---: | ---: | ---: | --- |
| Real N-row observation timestamps | 818.64 ms | 878.94 ms | +7.37% | Source producer target met for this input |
| Stable `lastUpdated.at` changes in all N rows, plus timestamps | 816.55 ms | 1,852.06 ms | +126.82% | Producer overhead gate failed |

Each median pools twelve samples from its two ABBA runs. All six generation
signatures match in every run of each workload. Transitive source hashes match
before/after each run and across the two source runs. Exact samples, components,
module hashes, counters and signatures are in [producer-abba.json](producer-abba.json).
Independent component medians are not additive.

The dense source workload has a 1,295.85 ms median sync stage, compared with
508.59 ms common generation and 46.63 ms oracle hashing. It retains correct
current/predecessor roots, with no cold rebuild or failed view. Its aggregate
heap-account peak is 65,972,597 bytes, below 64 MiB. Internal canonical buffers,
stages, journals and output pins also share the 32 MiB encoded limit.

The dense workload retires the optional change chain once per generation and
returns explicit baseline-required: six counted fallbacks per source run,
not successful incremental delivery. Packed baseline/recovery is unfinished.
No CPU saving may be inferred from omitted recovery work. Both source runs
close with zero accounted live allocations/objects and only the account base.

Example source invocation from the repository root, with the source overlay
and installed Python explicitly selected by the caller:

```sh
python -B tests/bench_sync_producer.py --rows 2000 --mode sync --workload timestamp
```

For the baseline, use installed a7's Python with `-I -B`, no source overlay and
`--mode legacy`. Repeat A/B/B/A serially under the shared advisory lock. The
source-overlay version metadata string does not identify an installed candidate.

## Subsequent token-buffer sharing

At `068f4b0`, the native owner shares each canonical membership-token buffer
between its global map and the corresponding cohort map. Keys, old-value
checks, nodes and commitment roots remain independent. The frozen-tree oracle,
exact replay and physical-sharing checks pass. The full source check passes
792 tests without skips; the focused Python 3.11 buffer/owner check passes 82.

A new serial dense ABBA run measures 837.06 ms installed a7 versus 1,830.43 ms
source, **+118.67%**, so the producer gate still fails. All six signatures match
in every run, and both source runs use identical transitive source bytes.
Accounted aggregate heap peaks at 62,171,223 bytes, with zero live accounted
allocations/objects after close. This is an account measurement, not an RSS gate.
The six explicit baseline-required fallbacks persist in each source run; packed
recovery and end-to-end work are still unqualified. Exact results are preserved
in [dense-sharing-abba.json](dense-sharing-abba.json); the earlier table and data
remain the historical `100637b` checkpoint.

## Compact-layout feasibility

The runtime's expanded baseline still needs 11,823,094 bytes at 2,000 rows,
exceeding the unchanged 8,404,992-byte frame cap. It is not a usable large-roster
wire format.

[packed_feasibility.py](packed_feasibility.py) tests a separate split-table layout:
record alias/identity/birth/body/order definitions first, stable bodies without
their repeated identity, alias-based observations and receipt-index membership
masks. The four small tables remain expanded. No body semantics or support
authority is inferred by packing.

| Full roster | Service 4 bytes | Proposed bytes | Increase |
| --- | ---: | ---: | ---: |
| 100 | 168,077 | 191,973 | 14.22% |
| 500 | 826,477 | 933,175 | 12.91% |
| 2,000 | 3,297,477 | 3,719,681 | 12.80% |

The ten-selected-row active view is 37,904 bytes in each fixture. Detached
reconstruction equals all eight logical tables; an independent full Patricia
rebuild reproduces NativeRoot. Four malformed structural cases per view reject
duplicate definitions, foreign body/observation aliases and inconsistent masks.
The owner closes to its fixed account base, with no live allocations/objects.
Exact results are in [packed-100.json](packed-100.json),
[packed-500.json](packed-500.json) and [packed-2000.json](packed-2000.json).

These are size/root feasibility checks using the current logical descriptor.
The layout is not emitted or accepted by the runtime, is not a frozen schema,
and has no budgeted admission/transport evidence. A changed final descriptor
will change dependent body IDs and field tokens. The detached oracle materializes
tables and is not a proposed sparse receiver implementation.

## Remaining work

- Complete the public owned-input transfer and compact codec ABI with Mesh,
  including provisional alias declarations versus the profile's independently
  derived final alias index, mask assertions and resource ownership.
- Implement packed baseline/change emission and strict budgeted normalization.
  The draft source's full parser/raw-frame lifetime is not an accepted aggregate
  budget handoff.
- Resolve the failed dense producer overhead case and qualify cold/all-body/
  forced recovery. A timestamp pass does not settle those gates.
- Run the remaining exact native, immutable artifact, installed paired IPC/SSH,
  end-to-end CPU/bytes/latency, resource/capacity, compatibility and cleanup gates.
  Empty sources or code probes cannot substitute for populated native parity.

No installation, version allocation, rollout or provider operation is authorized
by this source checkpoint.
