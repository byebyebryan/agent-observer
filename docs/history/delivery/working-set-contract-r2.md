# Working-set P1: bounded cutoff and coverage completion

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

2026-10-18. Read together with the immutable
[R1 candidate](working-set-contract-r1.md) at Observer995401e, SHA256
`4b4f55dff8308daee6aec442848a6c841c8e18b128ef4b91c01959e87aa33ec8`.
This supplement replaces only per-identity positive cutoff storage and makes
the branch/coverage lifetime requirements explicit. It allocates no identifier
and authorizes no dependent native/profile implementation before joint review.

## One monotonic clock ceiling

R1's lower cutoff rearranges exactly to:

```text
k = W - L + 1
Dlo_candidate = T + Q - k
K_next = max(K_previous, k)
Dlo_effective = T + Q - K_next
```

K is a signed safe integer, initialized only from an accepted canonical bracket.
Keep one K for the service/boot/time-domain clock incarnation, outside the
per-identity projection ledger. Runtime and history share the same wall and
BOOTTIME domain, so a single scalar can conservatively cover both. Any proposed
alternative worker without that guarantee remains clock-unproved.

For fixed T/Q, this is the minimum of all accepted candidate lower cutoffs.
It can only preserve or shorten positive authority, and is never later than
the current bracket's own lower bound. A wide old bracket can make a later
comparison conservatively uncertain earlier; it cannot create an early negative.
No per-event clock/support history or repeated deadline allocation is needed.
K changes are metadata changes and recompute the projection/revision/timer.

Never reset K when an identity retires, a ledger is full, a receipt expires, a
provider context changes or a wall discontinuity is detected. It can survive
namespace/context changes within the same service clock incarnation. Only a
new service/boot/time-domain incarnation resets it, with explicit new baseline
and no continuity or positive authority borrowed from the old incarnation.
This in-memory guarantee does not span service restart or reboot; no persistent
cross-reboot clock state is proposed.

Dhi is still exactly `U + Q - (W - T) + 1` from the current supported bracket.
K never changes Dhi or proves outside-window. Exact native admission checks
declared K>=current k and Dlo=T+Q-K, plus original support/clock joins and signed
safe-integer bounds. Stream continuity requires K nondecreasing within its
clock incarnation. A larger K grants no new authority. An already-admitted old
frame still has only its original supports/deadline; a delayed update cannot
extend those.

## Event regressions and capacity

R1's older-event guard remains: keep at most one last activity timestamp per
tracked full identity, not a bank of events or cutoffs. Older T is unknown and
cannot supply a negative Dhi; equal/newer current supported T may compare.
Retain this guard across roster/positive-ledger retirement, under the same
4,096 identity and combined 1 MiB ledger bound. Account its keys/containers and
overlap with current/new projection ownership. K itself is separately bounded
constant service metadata included in the same applicable accounting.

If the event guard cannot be retained, latch recency unavailable for that scope
until a real source-context or service/clock incarnation change establishes a
new baseline. Do not clear guards and silently re-arm the same scope. Publish
changed continuity and explicit `recent_tracking_capacity` coverage failure;
existing independently proved active selection may continue under its own
limits. If capacity also prevents safely enumerating selected active records,
fail the affected projection visibly under the existing resource rule. Never
claim complete-empty, manufacture a negative or shut down a healthy sibling.
Recovery is an explicit fresh-incarnation test, not same-scope ledger eviction.

Detected clock discontinuity keeps K and the guard, invalidates unchanged-event
recency and exposes partial coverage. The existing R1 new-event rule applies;
ordinary reads/proofs/heartbeat/reconnect cannot repair or renew evidence.

## Independent union and complete-scope lifetimes

For a currently proved eligible row, let hE be its eligibility support horizon
(unbounded for the explicit unknown-kind policy), hA the minimum expiry across
the active branch's exact supports, and hR the minimum expiry across the recent
branch's exact supports and effective Dlo. An absent/unproved branch supplies no
positive horizon. Its current selected horizon is:

```text
hSelected = min(hE, max(hA, hR))
```

Use only available positive branches in the maximum. Flattening active and
recent supports into one minimum incorrectly ends the union with the shorter
branch. The prepared facade evaluates the two branches separately with their
original translated receipts. Apply R1's positive-only E/H attenuation to R;
never use Dhi as a positive horizon. Prior horizons/provenance retained after
expiry are context only and establish no global presentation timeout.

**Complete coverage also expires with selection dependencies.** If a frame was
complete at emission and its only positive branch for a selected member later
expires, a reader must downgrade scope coverage to partial/unresolved unless
it has a separately admitted current negative decision for that identity.
Filtering a row from the positive body list while leaving complete coverage
would otherwise turn mere positive expiry into false absence authority.

The facade must therefore check scope support currentness AND current union
membership for every member of an admitted complete scope before claiming it
complete. Conservatively expiring complete coverage at the earliest positive
Dlo is also safe, including when an active alternative still holds; the next
replacement may restore complete coverage. A or R can still select healthy
rows while scope coverage is partial. Exact complete-empty scopes with no
positive transitions remain bound to their explicit original census/negative
supports. Native quiet timers publish at Dlo/Dhi as R1 specifies; delayed,
disconnected or lost delivery cannot bypass this independent facade check.

Required new vectors: monotonic K with unrelated/alternating components,
identity and capacity-ledger retirement, namespace change without clock reset,
fresh service reset, earlier/wider brackets, signed old cutoffs, old-event
guard refusal/latching, longer-A/shorter-R and converse, both branches lost,
complete-to-partial at quiet positive expiry, and explicit negative replacement
restoring complete absence. Preserve all original R1 native/resource/performance
gates. This completion is a model/contract candidate, not runtime acceptance.
