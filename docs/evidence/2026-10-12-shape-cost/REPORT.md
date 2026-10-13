# Pure validation allocation candidate

2026-10-12. Coordinated Mesh performance assessment finished; **private a21 candidate,
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

The immutable private wheel comes from runtime source
`af99914904dee1669ff4d9b8ec8a8dd96dff172c`, SHA256
`c6f89fd8b1782d85e41d54199a1c2b4d6a146f8ffe8fb1951447934b9aad1aa6`.
Its seven packaged schemas equal a20; only version and contract runtime files
differ. Private installed checks pass both hosts, as do cached IPC/fixed SSH,
mixed a21/a20 fleet and short WSS probes. The native capacity gate parses 4096
rows near the service frame ceiling and bounds sixteen attempted retained bodies.
Two 600-second candidate endpoint watches pass their input and cleanup guards;
this is not full-fleet resource or WSS capacity acceptance.

The final decision is **do not promote a21**. Ordinary SSH pipeline block gains
are 2.43–12.11%, and changing inventory/traffic excludes most comparisons. Only
two Starship blocks remain descriptive after qualification; the frozen >=15%
CPU or >=20% PSS gain in three of four blocks is not established. A fixed native
receipt trace through the full pipeline is needed before a further performance
promotion proposal. Correctness acceptance and pure microbenchmark savings do
not certify a fleet gain. This branch remains reviewable; Agent main, a20 assets,
ordinary networking/collection selectors and native service incarnations are
unchanged. Mesh remains released a15/SDK interface 1.

The Mesh-owned [final decision and scope](https://github.com/byebyebryan/mesh-plus/blob/main/docs/evidence/2026-10-12-performance/decision.md)
and its adjacent ledgers retain all 128 matched windows, exclusions, exact wheel
inputs, native/resource receipts and final two-host preservation. WSS operational
promotion and physical suspend remain separately bounded; no provider collection
or normal transport change was made.
