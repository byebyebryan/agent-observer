# P0 cached working-set size screen

2026-10-18. The authorized Luna goal loop starts from the reviewed
[working-set plan](../../../working-set-projection-plan.md), with a 72-hour
default. This first screen reads one snapshot from each already-running public
cached service. It starts no provider query, service or daemon, and persists no
raw snapshot, title, cwd, session identity, prompt or conversation content.

Both installed read CLIs resolve to Observer a5; both selected collector
entrypoints resolve to a7. The full Service4 wire remains the accepted interface.
The installed CLI performs the existing socket/peer/clock/frame checks; the
diagnostic only aggregates its returned public fields. Snap is acquired through
the existing fixed SSH alias. [The receipt](receipt.json) pins exact source and
diagnostic bytes, commands, received times and the two sanitized outputs.

| Host | Full rows | User/unknown-kind rows | Active eligible | Active +24h | Active +72h | Active +7d |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Starship | 400 | 145 | 6 | 8 | 12 | 20 |
| Snap | 102 | 64 | 1 | 1 | 4 | 14 |

The 72-hour estimate adds six non-active rows on Starship and three on Snap.
All eligible rows in this sample have current conversation activity and a
current runtime sample clock, with no unknown/future age bucket. Both sources
report complete saved/runtime inventories. Excluded child rows account for 255
Starship and 38 Snap rows. Total running rows also include excluded kinds;
they are not silently counted as eligible active sessions.

Canonical body bytes alone change from 707,756 to 23,677 on Starship and from
183,580 to 7,746 on Snap. These omit all generalized-selector support, coverage,
envelope, cache/copy and timer metadata. They establish a small selected body
set in these two samples, not wire savings, CPU, RSS or a capacity pass.

The age calculation uses the existing public rule: current sample-clock
`runtime.observedAt - activity.at`, with current activity and exact integer
timestamps; missing/negative ages do not qualify. Active eligibility does not
depend on age. This is an estimate from published fields. Full rows do not
export the transient `FactSupport.activity` needed to prove the new selection
contract, and this result must not be used as its independent authority oracle.
The source-clock P0/P1 gate remains open.

Luna's read-only trace identifies a conditional existing latest-turn anchor,
but activity and latestTurn can be selected from different components. Exact
field-support matching is required, and sequential wall/BOOTTIME capture needs
a conservative bound rather than an assumed scheduler skew. The primary is
reviewing a component sample/accept bracket before any production helper or
native schema is implemented. Exhaustive census is a completeness dependency;
it is not required merely to retain an independently proved positive member.

`census.py HOST` is stdlib-only and calls the installed cached CLI with an
explicit existing socket. Run outside a checkout. Its only stdout is aggregate
JSON; errors are bounded public reason codes. It contains no direct collector,
native RPC or autostart fallback. A prior SSH preflight quoting error occurred
before any snapshot request and was corrected with stdin transfer; these two
census runs themselves succeeded without replay.

The current samples support proceeding with the small-set design investigation.
They do not close the clock contract, native parity or any P2/P3 gate. No runtime,
wire, schema, artifact, selection or delta-sync change accompanies this screen.
