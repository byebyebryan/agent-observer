# Working-set support-density representation model

This source-only probe tests whether repeated full `FactSupport` maps dominate
the native working-set scope. It does not edit the producer, frozen API4 row
shape, native schema or Mesh. The candidate encoding is hypothetical and is
not admitted by the current working-set contract.

The source defines `FactSupport` as the complete eight-field object in
[`active_contract.py`](https://github.com/byebyebryan/agent-observer/blob/aade4826c785af6dc98842dfb662a090828dda17/agent_observer/active_contract.py).
The model builds one table per scope, sorted by each full map's canonical JSON
bytes. At the existing typed support positions only, it replaces a non-null map
with an exact integer table index. Those positions are `fieldSupports`, active
and recent `supports` arrays, coverage `supports`, uncertain `priorSupport` and
`support`, and nonmember `supports` and recent `support`. Nulls remain null.
There is no scope locator in a reference: the reference is interpreted only
against its enclosing scope table, and object/pair references (including a
cross-scope form) are rejected. `unpack` also rejects bool/out-of-range
indexes, invalid full maps, unsorted or duplicate table entries, and unused
entries.

For each successful case the script strictly parses the original full and
working-set frames, verifies the selected DTOs equal the independent API4
consumer filter byte for byte, packs and unpacks the scope, and checks both
object equality and canonical byte equality. Model byte counts use UTF-8
canonical JSON without a newline; full and working native frame sizes include
the final LF. “Duplicated support bytes” is the sum of canonical full-map bytes
at typed support positions minus one copy of each unique map. It does not
include list punctuation or field names. The candidate modeled frame replaces
the one scope with `{scope, supportTable}` and is only a size calculation; it
does not pass the current frame validator.

## Results

All inputs use the same synthetic builder and accepted sample as the existing
[wire-density source screen](../wire-density-source/run_wire_density.py).
Their complete accepted-snapshot hashes, native full/working frame sizes and
the wire screen's reports match in all three cases on both interpreters.

| Rows / selected | Full frame B | Selected original rows B | Working frame B | Native scope B | Support occurrences / unique maps | Duplicated map B | Modeled scope B | Modeled full frame B |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 500 / 50 | 621,770 | 65,026 | 163,755 | 97,411 | 276 / 1 | 73,425 | 24,290 | 90,634 |
| 500 / 100 | 625,195 | 130,051 | 325,455 | 194,086 | 551 / 1 | 146,850 | 47,815 | 179,184 |

The original API4 row arrays are unchanged: the 50- and 100-row selected arrays
are respectively 10.49% and 20.88% of the full 500-row array. In the arithmetic
model, interning lowers the scope by 73,121 B and 146,271 B, respectively. The
modeled whole working frame is 73,121 B and 146,271 B smaller. Every observed
support occurrence in these fixtures is the same complete 267-byte runtime
receipt map; this says nothing about workloads with more component samples,
contexts, censuses or longer receipt values.

The 2,000-row / 100-selected case is an explicit producer tracking refusal,
not a complete view. The returned native frame has `coverage.status=unavailable`
and `reason=projection_tracking_capacity`; its returned unavailable scope is 479 B
and its session list is empty. A read-only `sys.settrace` hook at
[`working_set_feed.py:387`](../../../../agent_observer/working_set_feed.py#L387)
reads scalar counts and canonical byte lengths from the existing local scope
immediately before the tracking-capacity branch. It retains no row/support
payload and does not mutate producer state. That local scope is only the prefix
constructed before refusal: 52 members on Python 3.14 and 59 on Python 3.11.
No full 100-member scope was created or inferred from that prefix.

| Interpreter | Guard bytes / identities | Candidate ledger entries / bytes | Partial scope array B | Incremental tracking bytes / limit | Combined partial scope + guard + ledger + fixed B / limit |
| --- | ---: | ---: | ---: | ---: | ---: |
| 3.14.8 | 906,938 / 2,000 | 52 / 27,353 | 104,520 | 1,048,658 / 1,048,576 (82 over) | 1,039,835 / 1,048,576 (8,741 headroom) |
| 3.11.17 | 890,962 / 2,000 | 59 / 31,035 | 117,582 | 1,049,426 / 1,048,576 (850 over) | 1,040,603 / 1,048,576 (7,973 headroom) |

The producer refuses while adding the per-member metadata/entry charge, before
the later combined-scope check. The recorded decision guard count is identical,
but `guard_bytes` differs because the current guard charges `sys.getsizeof`
for its owned tuples, strings and integer objects as well as a prepaid
dictionary-table bound.
That runtime-dependent accounting is preserved as measured; it is not a
support-table saving and is not a reason to change either limit. The modeled
500-row combined totals (scope array + actual guard + ledger + existing 1,024 B
fixed reserve) are 279,055 / 275,079 B for 50 selected and 328,880 / 324,904 B
for 100 selected on Python 3.14 / 3.11. These are arithmetic comparisons only.
The failed 2,000-row input has no complete native scope, so no full 100-row
pooled-scope size or modeled capacity pass is reported.

The model checks exact round trips and six malformed representations per
successful scope: bool index, out-of-range index, cross-scope reference form,
duplicate table map, unreferenced map, and noncanonical table order. The
synthetic malformed table rows are validation probes, not producer facts.

## Reproduction and provenance

Both runs disabled GC and used the exact interpreter entrypoints shown below. For a new replay, replace each output path with a fresh filename; preserve the saved reports.
Each JSON report records the executable, entrypoint, complete accepted-input
hashes, seed/helper/setup hashes, runner hash, source revision and hashes of
all loaded Python source modules under the immutable exported source root. The
reports contain scalar metadata only; no raw session or provider payload is
copied here.

```sh
rtk /home/bryan/code/mesh-plus/.venv/bin/python -B docs/evidence/2026-10-18-working-set/support-density-model/run_support_density.py --root /home/bryan/.cache/agent-observer-working-set-20261018/cadence-cost-610afaa/candidate --seed /home/bryan/.cache/agent-observer-working-set-20261018/cadence-cost-610afaa/seed.json --fixture-helper /home/bryan/code/agent-observer-working-set/docs/evidence/2026-10-18-working-set/performance-source/read_matched.py --exports /home/bryan/.cache/agent-observer-working-set-20261018/cadence-cost-610afaa/exports.json --setup /home/bryan/.cache/agent-observer-working-set-20261018/cadence-cost-610afaa/setup-candidate-314.json --python-entrypoint /home/bryan/code/mesh-plus/.venv/bin/python --output docs/evidence/2026-10-18-working-set/support-density-model/support-density-314.json
rtk /home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python -B docs/evidence/2026-10-18-working-set/support-density-model/run_support_density.py --root /home/bryan/.cache/agent-observer-working-set-20261018/cadence-cost-610afaa/candidate --seed /home/bryan/.cache/agent-observer-working-set-20261018/cadence-cost-610afaa/seed.json --fixture-helper /home/bryan/code/agent-observer-working-set/docs/evidence/2026-10-18-working-set/performance-source/read_matched.py --exports /home/bryan/.cache/agent-observer-working-set-20261018/cadence-cost-610afaa/exports.json --setup /home/bryan/.cache/agent-observer-working-set-20261018/cadence-cost-610afaa/setup-candidate-311.json --python-entrypoint /home/bryan/code/agent-observer/.local/active-feed-20261016/installed311/bin/python --output docs/evidence/2026-10-18-working-set/support-density-model/support-density-311.json
```

Reports: [Python 3.14](support-density-314.json) and
[Python 3.11](support-density-311.json). They preserve all complete
accepted-snapshot digests:

| Rows / selected | Complete accepted-snapshot SHA-256 |
| ---: | --- |
| 500 / 50 | `2d949c04af95c791a0a12d0cc0d537cf0d128d1318b3f006cad675ab978a77b3` |
| 500 / 100 | `94c4fe357b9b77a469a6285a65e235e199268a3a13e93595330b0d79da66cd7b` |
| 2,000 / 100 | `88a84606bacd1862eb443f4e99689f4d9b5555eed0d20d7b5e8affed98b464ac` |

Provenance pins:

- Immutable candidate source: `610afaac658903ddd6c466c793f9856b45e9f03e`, with 243 exported files verified by the supplied export manifest.
- Seed JSON SHA-256: `92c1d88dd8f2b37d513d8383b88f33821686524886e52b79f9b814429b60fad9`.
- Fixture helper SHA-256: `ccf91435e078fc5c1aadc5a1070e7e1973bdb06265351a8e1508b07c3644895b`.
- Export manifest SHA-256: `71574437196fc8b026d7fea63b1467281dd30dabe1ddf821649b2f06c06a9808`.
- Candidate setup diagnostic SHA-256 (both): `1d235fe82c27d7b46b1664e91701821b8cab18a5d407a9c1a454c35e6bc07192`.
- Executed runner SHA-256 (both): `7149fb872a7a3a341385378c3c52aa02ce7002ec0fdde92cf100513e2916c3b6`.

The scoped runner checks passed with GC disabled on Python 3.14.8 and 3.11.17.
Ruff passed for the new runner. This model does not change source estimates or
caps, establish physical memory use, qualify an SDK schema, or make the
2,000-row refusal complete.
