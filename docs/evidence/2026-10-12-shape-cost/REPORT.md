# Pure validation allocation candidate

2026-10-12. Active coordinated Mesh performance pass; **private a21 candidate,
not released or selected**. Normal collection remains a18 and networking remains
a20/Mesh a15 on Snap and Starship. The Mesh wire/SDK and Observer API 2/read 4/
Service 2, schemas, native acquisition, collection cadence and source semantics
are unchanged. No deployment or provider action is performed.

The existing type matcher allocated a six-entry predicate dictionary on every
call. Single type specs also allocated a list and generator. The candidate
selects the same predicate for plain JSON values and plain string specs; unusual
Python values/subclasses/spec objects retain the original lookup behavior. Type
union ordering, booleans versus integers, exact const/enum types and all field,
text/control/pattern/range and native semantic checks remain. Every admission
validates fresh input; no frame memo, callback weakening or validation removal
is introduced.

Three focused admission tests pass, including malformed specs, subclasses,
nullable unions and non-type rejection codes. Python 3.14.8 `scripts/check`
passes 379 tests and 136 Markdown/link/diff checks with Mesh a15/jsonschema
4.26.0 installed; no skips were reported. The installed baseline a20 contract
and candidate runtime digests and timing values are retained in
[differential evidence](differential.json). Source validation is separate from
artifact acceptance.

The Mesh-owned differential helper compares the original installed package
against this isolated source package using 336 type/union shapes plus 600
deterministic native-frame mutations. All 936 exact acceptance/error outcomes
match. A private origin-host 94-row frame supplies four ABBA pure validation
CPU blocks: candidate reductions are 20.13%, 20.03%, 19.73% and 20.55%. Native
frame bodies remain private. This is a fixed-input pure-validator measurement,
not publisher/reader/fleet CPU, latency, capacity or deployment acceptance.

The remaining gates are a clean tracked-source immutable wheel, installed byte
and schema parity, both-host owner conformance/cached IPC/SSH/WSS, matched normal
carrier/candidate windows, declared capacity/recovery/cleanup and final decision.
Ordinary selection and published a20 assets remain unchanged. No Mesh package
change or new public callback is required for this candidate.
