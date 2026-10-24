# Compact material-plan parser primitive

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Status: **unselected Observer-owned G1 parser component**. The optional
[Agent codec/profile integration](delta-sync-compact-codec.md) now connects this
primitive to committed public Mesh R2 APIs; the parser surface below stays
private to Observer. Mesh compatibility
confirmation `e-7a500abe` accepts the exact `c161090` raw/native convention for
dependent integration. The accepted schema, proposal, vectors and independent
verifier remain byte-identical to that commit. No encoding/schema identifier is
allocated or frozen; no runtime route or installed selection changes.

## Scope and retained data

The private `sync_compact_plan._open_compact_plan` helper prepares the parser
portion of the agreed NativeInputPlan. Its returned object exposes the existing
revocable `header`/`close` pattern. It is **not itself a NativeCodec or an admission path**. The separate optional
[Agent adapter/profile](delta-sync-compact-codec.md) now supplies CodecSpec/
AliasSpec DTOs, record-first normalization, positional reference resolution,
canonical packing and compact-mask admission through committed public APIs.
That unselected source integration has its own evidence; native serialization/
journal/source configuration and full qualification remain separate G1 work.

Open scans the complete strict frame once for grammar, UTF-8, integers, bounded
root/header/dictionary fields and all eight closed table/operation arrays. The
scanner retains exactly eight array spans plus bounded header/dictionary data,
not an offset per row or a decoded opaque roster. The original immutable frame
is borrowed. Its owner must keep the original input pin and physical encoded
credit through every active parser/callback and cleanup; this component neither
mints an input pin nor charges a copied input buffer.

The expanded scanner's private `_table` hook only extracts its preceding table
handling. Default expanded and structural compact/header/head behavior is
preserved. The material scanner additionally enforces the reviewed per-table
raw count limits while scanning, including the doubled transaction limits.
Head/control cannot open a material plan. Ordinary head acquisition still uses
the separate original bounded LF frame and never constructs this parser.

## One-value lifetime

The budget capability passed to open is not retained. Each private iterator
receives the current normalization context budget, from the same aggregate
ledger; independent metadata reservations survive their originating call.

Only one private iterator and one current raw-value ticket may be live per
plan. Opening another iterator or advancing past an unclosed value rejects
without retiring the existing value or interfering with an active decode.
Iteration locates one complete value, reserves its decoded/validator/control
heap bound **before slicing or decoding**, then invokes a trusted configured
per-value schema validator. No value is yielded before that validator succeeds.
Duplicate opaque object keys and late malformed values therefore reject when
their complete value is reached; a successful prefix grants no authority.

The private ticket advertises `materialization_bytes`. Its detached decoded
copy requires a separate caller reservation before `materialize`, retained
until every copy/child/error frame actually retires. The caller must close the
current ticket before requesting another value. This primitive deliberately
returns raw values only to the future trusted Observer adapter; these tickets
are not the generic NormalizedEntry/Operation DTOs and are not a new supported
Mesh interface or a public raw-buffer export.

A trusted validator must fully check the selected closed local value schema and
retain no borrowed value. Its configured schema storage is separately charged
by its eventual codec owner. The parser itself imports no jsonschema, Mesh,
provider, engine or service. Tests inject independent Draft 2020-12 validators;
that fixed test configuration is outside the isolated fixture heap ledger.
Payload-bearing third-party validation exceptions are converted to the bounded
`sync_compact_value_shape` code after their unwound frames/context are cleared.
No parsed instance is retained in a propagated schema exception.

Plan close immediately revokes its header, iterator and current value. A parser
or validator already in progress keeps its input/header/iterator/value credit
through unwind and cannot return a late usable ticket. A copied value in progress
keeps its independently owned decoded graph charged until copy unwind; caller
copies remain separately caller-owned. Weak iterator/plan links avoid a terminal
ownership cycle. Closing or dropping a plan never closes the shared aggregate
budget or a sibling plan.

## Evidence and boundaries

The [source manifest](../../evidence/2026-10-16-delta-sync-source/compact-plan.json)
pins exact source inputs, schema/vector preservation and validation logs. Seventeen
new tests run with cyclic GC disabled and no explicit collection. They cover all
eight baselines/ten transactions, strict framing/dictionary checks, table counts,
one-value iteration, pre-copy refusal, duplicate/late schema rejection, retained
errors/handles, reentrant/concurrent close and sibling isolation. Existing
expanded acquisition and both structural facade suites remain separate
regression checks around the scanner hook.

Fixture heap counters cover parser/header/current-value/copy reservations only.
Raw input buffers, fixed test schema configuration and harness allocations are
excluded; this is not aggregate resource, RSS, dense-capacity or CPU acceptance.
No alias/birth/receipt-existence, expected-old, field/support/domain/join,
mask-expansion, table/cohort/native/source root or fresh-proof authority is
established by this parser. All remain independently required at generic and
Agent admission. A caller cannot treat partial iteration or a structural header
as successful material admission.

The remaining gates include full configured streaming NativeCodec/profile/export,
atomic rollback and revocation through actual generic owned inputs, exact paired
encoding/schema freeze, inclusive shared 64 MiB heap and overlapping 32 MiB
encoded ownership, dense/cold/recovery total CPU and bytes, deliverable 2,000-row
recovery, populated IPC/fixed SSH, RSS and independent immutable installed-pair
qualification. Earlier CPU failures retain their original failed status. The
completion-transfer/controller seam is separate. No package, sibling, provider,
service, consumer or rollout action accompanies this component.
