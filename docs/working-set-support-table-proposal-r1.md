# Proposed working-set FactSupport table

**Status: review option only.** This proposes one bounded, lossless encoding for
repeated FactSupport maps in the unreleased working-set scope. It does not
allocate or freeze a protocol/profile ID, revise a frozen schema, or accept a
producer, Mesh, runtime, resource, or consumer gate. The current map-form
candidate remains the only implemented form.

The option is grounded in the current eight-field `FACT_SUPPORT` definition,
map-form validator and projector, the SDK1 profile/read candidate, and the
stdlib arithmetic model at
[`support-density-model`](evidence/2026-10-18-working-set/support-density-model/README.md).
That model used source `610afaac658903ddd6c466c793f9856b45e9f03e`. It showed
single-map duplication in the 500-row synthetic cases, but did not test a new
schema or admission path. The 2,000-row/100-selected input refused before a
full scope existed: the candidate held only 52 members on Python 3.14 and 59
on Python 3.11. No full modeled table or capacity pass exists for that case.
The model represented its candidate as `{scope, supportTable}` around the
original scope, while this proposal places `supportTable` inside each scope.
Its 90,634-byte (50 selected) and 179,184-byte (100 selected) modeled frames
versus the 163,755-byte and 325,455-byte original frames are arithmetic for
that wrapper only, not predicted bytes for this grammar. Exact bytes require
the eventual encoder and unchanged frame/resource qualification.

## Proposed frame-local grammar

Add one `supportTable` array to each working-set `scope`. It contains complete
FactSupport objects. In that same scope, replace a non-null FactSupport object
at the typed positions below with its zero-based table index. Keep each
surrounding key, array, row, and null slot in place. A reference has no scope
locator: it is meaningful only with the table in its enclosing scope.
This is one closed compact form: reject a full map at a reference position,
and do not accept a hybrid or map-form fallback in the same candidate grammar.
All other positions retain their original schema and meaning; ordinary numeric
timestamps and counters elsewhere are not interpreted as support references.

| Existing position | Proposed compact value |
| --- | --- |
| `coverage.supports[]` | index |
| `members[].fieldSupports.{runtime,phase,kind,savedIdentity,activity,outcome,workspace,lastUpdated,latestTurn}` | index or the existing `null` |
| `members[].active.supports[]` | index |
| `members[].recent.supports[]` | index |
| `uncertain[].priorSupport`, `uncertain[].support` | index or the existing `null` |
| `nonmembers[].supports[]` | index |
| `nonmembers[].recent.support` | index or the existing `null` |

No other value is a FactSupport reference. In particular, do not pool
`scope.clocks`, `members[].recent.clock`, receipt objects nested in session
fields, identities, absence evidence, or session rows. Preserve all current
array order and multiplicity; only the table itself has a new canonical order.
The current frame has at most one scope, but references remain strictly local
even if a future candidate permits more.

The table is a set-like canonical sequence of **whole** eight-field maps:
`serviceId`, `provider`, `namespace`, `contextGeneration`, `component`,
`accepted`, `sampledBoottimeMs`, and `expiresBoottimeMs`. Every entry must pass
the existing strict FactSupport shape and value validation. Define its key as
the existing canonical UTF-8 JSON bytes for that full validated map. Include a
map exactly once, ordered by ascending key bytes; equal keys mean equal whole
maps. Do not deduplicate by component, counter, time, expiry, or any partial
identity.

Each reference must be an exact integer (`type(index) is int`; booleans are
rejected), with `0 <= index < len(supportTable)`. For the proposed current
identity bound, the structural maximum is 8,194 entries: at most two historical
scope-valid references in each of 4,096 uncertain entries, plus at most the two
distinct current component receipts (runtime and history). This bound follows
from current semantics: member fields, branch supports, nonmember supports,
and coverage supports must match one of those current receipts; only the two
uncertain slots are allowed to be historical. It must be re-derived if those
semantics or identity limits change. It does not relax the unchanged 1 MiB
scope/clock/decision limit.

An occurrence may be null only where the existing map-form schema allows null;
required support positions and table entries cannot be null. The table may be
empty only when no typed reference occurs. Reject every out-of-range or
non-integer reference, duplicate table maps, unsorted table entries, and any
unreferenced entry. Do not silently sort, clamp, coerce, drop or fill input.
The table is frame-local: an index alone is never a cross-frame identity or
evidence token. A NativeState, restored frame or pinned cache may retain the
indices together with their exact enclosing scope and original table under
that frame's ownership. Never resolve an old index against a replacement
table, including after a newer generation arrives or an old scope retires.

## Validation, policy and Mesh boundary

The compact-form parser first validates the closed candidate shape, complete
FactSupport table entries, canonical uniqueness/order, the 8,194-entry cap,
and every typed reference. It then borrows the exact validated table maps for
the current semantic operation and runs the existing semantic checks unchanged: current
receipt/source joins, scope and clock binding, member field checks, exact
active/recent support sets, negative and absence evidence, coverage, body
membership, and frame limits. No integer index reaches `support_matches`,
`_member`, `_nonmember`, branch/horizon logic, or coverage decisions. Indices
are serialization references only; they do not confer evidence. Iterate one
member, uncertain entry, negative or coverage object at a time. Any shallow
adapter for existing callbacks is bounded to that current entry, read-only to
the caller's data, and retired before advancing. Do not reconstruct a full
expanded scope/member roster as a prerequisite to validation.

The existing policy and authority remain exact: `E AND (A OR R)`, independent
active and recent branches, original published activity timestamp, source
sample and current receipt joins, K monotonic ceiling, last-T regression guard,
current-sample Dhi, positive-only receipt attenuation, and complete-to-partial
rules. Coverage completeness still requires the existing exhaustive census
and all required current decisions. Table lookup cannot make missing, stale,
future, historical, expired, or otherwise unproved support current, and cannot
turn omission or unknown into a negative.

The proposed compact scope changes only the unreleased working-set frame
metadata grammar. Frozen API4 `SESSION` rows and their bytes, ordinary API4
snapshots, active-feed frames, full-feed frames, request policy, provider
payloads, and client predicates stay unchanged. Keep the existing 4,096
identity bound, combined 1 MiB working-set scope/clock/decision bound, 8 MiB
body plus 16 KiB envelope bound, and shared service encoding limits. A shorter
canonical pooled scope is not evidence that any existing allowance can be
reduced or that Python heap use is lower.

For the SDK1 candidate, the packaged public profile schema must accept this
closed compact grammar and reject malformed indices independently. Public
admission must preserve the compact scope in detached `NativeState` metadata;
the pure bridge/read adapter resolves the current entry's support values from
its paired scope table immediately before the unchanged profile receipt and
reader semantics. Preparation returns only its existing detached rules and
does not retain this scratch or a reconstructed full scope. Detached read
results that expose original full-support values must own and account for
their actual copies; they cannot borrow an index without its table or treat
output expansion as free. Restoration joins the untouched service envelope, compact metadata,
and original session records back into the exact compact frame. Roundtrip
acceptance means object equality and canonical-byte equality, including table
order and integer references. The adapter must not mutate caller-owned
metadata or retain decoded rows after rule preparation.

SDK1 currently has no registered descriptor for the candidate profile. This
proposal requires its owning public registration/schema review and supported
descriptor/admission path; it authorizes no fake descriptor, private SDK API,
Reader guard bypass, or monkeypatch. Whether the still-unreleased working-set
version/profile literal stays as-is or changes before that freeze is an open
owner decision.

## Required owner accounting and failure behavior

Do not treat canonical byte savings as a source-capacity result. The existing
1 MiB limit is a combined owner ledger, not a second allocation allowance. A
future implementation must define a conservative preflight charge for the
retained table and support maps, every integer reference and container, table
key bytes, deduplication/index-remap structures, scope/clock/decision state,
and the private full-support last-positive ledger. The ledger is long-lived and
must continue storing original support values, not frame-local numeric indices.
Only physically shared immutable storage can receive a single ownership charge;
equal maps or canonical keys allocated separately still need separate funding.
Charge the old committed ledger and candidate ledger together until commit or
rollback.

The charge and reservation must also account for simultaneously live old and
new scope/table representations, canonicalization and validation copies,
temporary expanded support views, encoded output, and retained exceptions.
Preflight table construction and each growth step before allocating retained
owned keys/maps or growing the candidate structure. Fund the bounded current
entry's semantic scratch and any detached read output through actual retirement. The
existing incremental per-member check cannot be replaced by an uncharged
end-of-build size check.

Keep the current synchronous `Runtime._reserve_working_set` / shared
`Runtime._room` path and its existing `MAX_FRAME_BYTES + 2 * MAX_LEDGER_BYTES`
worst-case reservation; the 64 MiB cap
accounts shared encoded ownership, caches, and peer pins, not a newly claimed
Python-heap ceiling. Retain old encoded bytes while readers or peers own them.
On refusal, roll back the candidate without mutating the old buffer, preserve
K, last-T guards and context anti-regression state, and use the existing
projection-unavailable/error delivery behavior. Do not encode an unreserved
replacement error buffer. On success, publish only after the complete new
representation passes preflight, validation, and frame-size checks; release
old objects only when their real cache/peer references end. Full and active
delivery continue under their current shared accounting and failure rules.

No numeric replacement charge or new success threshold is proposed here.
The model's 500-row arithmetic totals and single-map savings are not inclusive
peak-lifetime accounting. The 2,000-row refusal remains a refusal; a hypothetical
table over its 52/59-member partial prefix cannot be called a complete scope,
canary, or 2,000-row success. Preserve all current bounds until an owning
resource review accepts measured conservative charges and boundary behavior.

## Decisions and acceptance still required

1. Observer contract owner: approve or revise the 8,194 table-entry derivation,
typed position list, canonical byte ordering, unused/duplicate rejection, and
the compact-to-full validation order without narrowing historical uncertainty.
2. Mesh owner: review the closed SDK1 candidate grammar, compact NativeState
roundtrip, detached read-side resolution, profile/version literal, and public
descriptor/schema registration. Current SDK refusal remains the status quo.
3. Observer runtime/resource owner: specify concrete preallocation charges for
table, keys, bounded entry scratch, detached output, old/new overlap and ledgers under the
existing 1 MiB ledger and shared encoded reservation. Keep refusal atomic and
old bytes accounted; do not infer capacity from pooled JSON size.
4. Implementation and acceptance after those reviews: add strict compact
parser/encoder and malformed-index vectors; prove map-form and compact-form
semantic decisions are identical; prove lossless public NativeState roundtrip;
test refusal before owned allocation at table, combined-ledger, reservation,
and frame boundaries; then re-run N=500/2,000 varied workloads with real
accepted frames and pinned readers. A 2,000-row pass is not assumed.

Until those decisions and gates close, this document is one reviewable encoding
option. It does not change the current source contract or make pooled support
references an agreed wire feature.

Source basis at the unchanged `7e5757c` review checkpoint:
[original support semantics](../agent_observer/active_contract.py),
[working-set contract](../agent_observer/working_set_contract.py),
[projector and tracking](../agent_observer/working_set_feed.py),
[SDK1 profile candidate](../agent_observer/mesh_working_set_profile.py), and
[read facade candidate](../agent_observer/mesh_working_set_read.py).
Luna drafted this option; the primary reviewed the historical-reference bound,
paired-index lifetime, per-entry resolution and budget distinctions. This is
source/document review. No compact encoder, schema, experiment, new test vector,
Mesh edit or peer signoff is claimed.
