# Working-set cached source and client candidate

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

2026-10-18. This follows the [native component](working-set-native-candidate.md)
and the jointly reviewed [R1](working-set-contract-r1.md),
[R2](working-set-contract-r2.md) and [R3](working-set-contract-r3.md) policy.
The feature remains opt-in. The current Mesh a23 descriptor registry rejects
this candidate, so the configured publisher and prepared watch deliberately
refuse construction. No local fake descriptor, full/active fallback, schema or
identifier freeze, installed artifact, consumer adoption or rollout is implied.

## Configuration and ownership

The service accepts `--working-set-window-hours [H]`: absent means disabled;
the bare flag means 72 hours; zero means the active branch only. H is an integer
from zero through 720. The fixed window is checked before adapter/service setup.
`service working-set-api --window-hours H` and
`service working-set-schema --kind request|frame` export pure candidate metadata
without opening a service/socket, loading a provider or importing Mesh.
The existing full and active routes retain their explicit selection.

`CachedWorkingSetAgentSource(host, socket, window_ms=...)` uses the existing
cached acquisition lifetime with a distinct native request family. Each request
carries a fresh detached selector and exact digest. A disabled or mismatched
route fails without another request family. Independent socket operations also
retain a monotonic clock ceiling/generation for the same service clock
incarnation; a delayed older acquisition cannot extend recency.

The pure `WorkingSetAgentCodec` preserves the SDK1 NativeState split, original
receipts, service metadata and exact lossless native restore. Its immutable
host/source/window binding is checked on bridge and native admission.
`WorkingSetAgentProfile` and its static preparation use the public descriptor
registry only. Recent parked and runtime-unknown records remain eligible;
the old active-only running filter is not reused. Generic required receipts
remain conservative conjunctive bookkeeping.

The separate trusted `make_working_set_publisher` function captures the fixed
window in both profile and source. It resolves the public descriptor before
allocating the source, so unsupported registration fails during setup. No normal
publisher CLI dispatch or default profile changes in this slice.

## Independent prepared read policy

`PreparedWorkingSetAgentWatch` retains one detached snapshot from public SDK
admission, then calls `current(now, clock)` before `context()` on every read.
The generic returned row list never decides active OR recent membership or age.
The facade evaluates the retained raw rows with original native supports,
current translated receipt health/counters/deadlines and exact scope/selector
binding. Reader time must not regress; disconnect clears all claims and requires
a new watch. Host/provider binding storage replaces retired scope entries.

The active branch requires its own original support. The recent branch requires
its original activity/kind supports and the positive-only translated cutoff:

```text
hRecent = min(required translated receipts,
              Hactivity - max(0, Enative - Dlo))
hSelected = min(hEligibility, max(hActive, hRecent))
```

Only current, proved branches participate. A shorter branch cannot shorten the
other branch. Equality expires recent selection. Dhi never becomes a receiving
clock negative. Every displayed field is independently masked; recent records
can remain selected with unknown runtime/phase. The facade emits only admitted
native negatives while their original supports remain current.

After a sole positive expires, the row becomes unresolved and complete coverage
becomes partial, even when no body remains. An admitted quiet native negative
may later restore complete absence. Complete-empty scopes still need current
census dependencies. Delivery/context failure removes positive and negative
authority while retaining explicitly informational identity context. This code
adds no presentation history or context-retirement timeout.

### Bounded downstream presentation leases

The additive `WORKING_SET_MEMBER_LEASE_INTERFACE_VERSION = 1` exports a detached
`member_leases` list with each `WorkingSetAgentRead`. Entries match the current
`members` by exact identity and contain `activeExpiresAtMs`,
`recentExpiresAtMs`, `membershipExpiresAtMs`, and a `fieldExpiresAtMs` map.
All deadlines use the receiving Reader's BOOTTIME domain. Expired or unsupported
branches and fields have null deadlines. Membership uses the maximum live branch
horizon, capped by the required kind support for a known kind. The recent horizon
already contains the original positive-only cutoff attenuation.

Consumers use these already-computed leases to bound downstream display packets;
they do not reconstruct membership from raw metadata, translate Dhi into absence,
renew a lease on a timer tick, or infer running from recent membership. A display
packet must also respect the current support of every field it displays. Mutating
the exported list, identity or deadline map does not affect retained state.
Delivery loss, terminal disconnect and positive expiry export no member lease.
This is a read-facade addition: no native frame, Mesh descriptor, schema or wire
contract changes, and it does not independently qualify installed/native delivery.

`WORKING_SET_SCOPE_LEASE_INTERFACE_VERSION = 1` also exports
`scope.coverage.expiresAtMs`: a receiving-clock deadline for complete coverage,
or null for partial/unavailable coverage. It is the minimum of the original
census dependencies, every selected member's independent A OR R membership
deadline (including required kind), and every admitted negative's conjunction
deadline. This applies to a complete empty scope too. Downstream complete totals
and absence claims must expire by this deadline; individual row claims may have
separate shorter or longer leases. A positive timeout still downgrades coverage
and never creates a native negative.

## Evidence boundary

The [component record](../../evidence/2026-10-18-working-set/p2-client/README.md)
separates actual native/CLI/disposable UNIX source checks, pure NativeState and
preparation tests, and domain expiry tests over directly supplied translated
headers. The latter are not SDK proof or Reader admission. Current descriptor
refusal is tested rather than bypassed. Schema/validator/lock integration belongs
to the Mesh owner after exact candidate compatibility review.

The early owner-only cost screen and bounded removal of an unused projection
JSON round trip are recorded separately. Those screens compare disabled and
enabled working sets on this source family, not the required immutable accepted
a7 baseline. They do not accept the 25% owner ceiling or the combined read/byte
gates. Inclusive shared service 64 MiB encoded ownership, heap/RSS, slow readers,
full/active coexistence, dense/burst capacity, native IPC/fixed SSH, exact installed
pairs and rollback remain producer qualification work. Delta stays dark.
