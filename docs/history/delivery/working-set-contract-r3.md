# Working-set P1: selection coverage and safe cutoff correction

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

2026-10-18. Read together with the immutable
[R1](working-set-contract-r1.md) at Observer995401e
(SHA256 `4b4f55dff8308daee6aec442848a6c841c8e18b128ef4b91c01959e87aa33ec8`)
and [R2](working-set-contract-r2.md) at Observer58b04ac
(SHA256 `937d442402064a4e43258412d12e906fd5ca98b7fe0244c45f9ac1699884ccea`).
Original bytes, evidence and failed counterexample remain preserved. This
addendum clarifies one coverage sentence and records conformance to R1's
existing signed-safe cutoff rule; it introduces no new SDK or clock authority.

## WS-P1-1: coverage depends on the selection decision

Replace R1's blanket sentence “Unknown age is partial” with:

> Unknown activity makes affected membership coverage partial when the selection
> decision cannot otherwise be proved. Independently proved active membership
> remains selected; unavailable activity and age fields remain unknown.

For `E=true, A=true, R=unknown`, the union proves membership. That row does not
make a scope membership-incomplete merely because its age is unknown. The scope
can be complete if the actual exhaustive native census and every other required
selection decision/support are current. Current excluded kind also needs no age
proof. Zero-window R=false needs no activity/clock support. By contrast, an
eligible row with A=false/unknown and R=unknown is unresolved and prevents a
complete claim unless an independent current exclusion applies.

This does not upgrade census completeness, field currentness or age authority.
It preserves R2's downgrade when a member loses its **sole** positive branch,
and the independent A alternative after R expires. Complete-empty still needs
its original exhaustive/negative supports. Existing displayed sampled age is
unchanged. There is no new context timeout or absence inferred from omission.

RLCD's initial exact R1 review is commit26c0c487; its separate R1+R2 contract
acceptance is commit2a4678ef. The latter resolves the client semantics of this
sentence via R2 while keeping the helper correction below open. These are
contract reviews, not implementation, native, resource or adoption acceptance.

## WS-P1-2: no out-of-range usable cutoff

The preparatory `recent_activity` helper now checks both computed Dlo and Dhi
against the inclusive signed interval `[-(2^53-1), 2^53-1]` **before** returning
a time decision. If either lies outside, it returns unknown with reason
`cutoff_out_of_range` and both deadline fields absent (`None`). It does not
clamp, round, wrap, or retain the other bound as usable authority. Zero-window
behavior and valid signed negative bounds remain exact.

The independently reported valid-joined-input counterexample was reproduced
against immutable Observer58b04ac on Python3.14.8 and3.11.17:

| Input/result | Value |
| --- | ---: |
| Safe maximum | 9,007,199,254,740,991 |
| L / U | 9,007,199,254,730,991 / 9,007,199,254,731,001 |
| now / receipt expiry | 9,007,199,254,731,091 / 9,007,199,254,740,990 |
| W / T / window | 1,700,000,000,000 / 1,699,999,999,000 / 259,200,000 |
| Before Dlo / Dhi | 9,007,199,513,929,990 / 9,007,199,513,930,002 |

Before, the helper incorrectly returned true/recent. After, it returns unknown
and no usable bound. This never suppresses an independently proved active
branch: `E=true AND (A=true OR R=unknown)` remains selected.

Three new regression methods preserve the original twelve and cover this case,
upper-only overflow, inclusive signed endpoints and the active/unknown union.
The owning evidence distinguishes immutable before plus final test overlay,
the current after source and the unchanged original client diagnostic. These
are pure-model checks, not actual native frame/sample/cache/timer/GC or producer
acceptance. The stateful K/guard, native/schema/profile and resource/performance
work still require their existing stages; no identifier, package, selected role
or service is changed by this correction.
