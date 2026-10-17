# Agent compact codec and profile integration

Status: **unselected G1 source integration through committed Mesh R2 APIs**.
This builds on the [private material-plan parser](delta-sync-compact-plan.md) and
same-byte `c161090` compatibility accepted by both owners/coordinator. The four
reviewed raw proposal/schema/vector/verifier files remain unchanged. Encoding
and schema identifiers remain unallocated/unfrozen; no default or route selects
this codec and no package/service/provider/consumer rollout occurs.

## Supported optional codec

`agent_observer.mesh_sync_codec.AgentCompactSyncCodec(view, *, encoding_id,
expected_host=None)` implements public `spec`, `open`, `entries`, `operations`
and `head` through Mesh commit `030da1f0ac083fc51bf9ad10fc93e62678719cdc`.
It uses the public exported frozen AliasSpec/CodecSpec and NormalizedEntry,
NormalizedOperation, MembershipGroup/Change DTOs. Its required feature is exactly
`provisional-memberships/1`; AgentSyncProfile explicitly advertises that feature.
An absent configured codec preserves strict expanded behavior. Failure never
falls back to expanded decoding, a full profile or a guessed encoding/source.

The trusted caller must provide an explicit encoding ID. Tests use only
`fixture-compact/1`. CodecSpec binds the existing reviewed raw schema digest,
selected logical native descriptor digest, nine ordered fields and alias index
`aliases` with `("alias",)`/`("birth",)` paths. The codec configuration is immutable
and has no native/provider/cache/profile acquisition or admission capabilities.
Only this optional module imports Mesh; the owner/parser/validation modules
remain independent of Mesh and third-party validation libraries. The R4 relay
uses the separate Mesh-free `CompactAgentSyncTransportCodec` structural facade;
this NativeCodec is for independently admitting Reader caches and supplies no
relay `header`/encoding protocol. The two roles share no authority handles.

## Streaming and exact reference sides

The native plan scans strict complete framing while retaining one borrowed,
caller-pinned raw frame and eight array spans. Per-value schema validation
finishes under reserved credit before a private value ticket is yielded. The
adapter prepays one detached value copy and bounded public reference copies,
restores it and synchronously calls public `ctx.pack`. Its yielded DTO and key
remain inside that credit until generic adoption resumes/closes the iterator.
No full decoded roster, per-field cell-operation list, native JSON synthesis or
private generic graph/helper access is added.

Mesh controls record-first, then receipt and remaining-space phases. Record
slots restore exact bound epoch/birth/order/scope data before other references.
Literal receipt/metadata values need no alias lookup. Before other spaces, the
bounded private receipt dictionaries are checked for exact keyed before/after
existence, including unused keys. Public sided AliasViews and keyed state
lookups resolve each typed position. No old key falls back to a provisional key
or a newer receipt. Retained context/negative/uncertain support remains literal.
Before-A/after-B alias reuse requires the reviewed separate group operations.

The generic engine independently recomputes raw transaction identity, including
receiptRefs, then checks expected-old values, links, aliases, masks, all eight
tables, seals and native/source roots. Structural or partial parsing grants no
material/current/proof authority. Head calls the existing bounded decoder with
the original native LF frame. It neither opens a plan nor loads schema/body
state. The Reader still independently parses and verifies the original head,
nonce, receipts, clock, incarnation, root and deadlines.

## Profile compact branch

Compact admission reads public membership intents to include mask-only affected
identities. Declared positive bits must match the row's exact observation
supports and birth. For each affected row, every current support requires its
provisional after mask bit; abandoned old support and removed records require
those bits absent. Expanded mode retains real-cell/token checking.

After-cell token lookups intentionally remain blocked during compact callbacks.
For a new/changed stable body the profile derives all nine exact value tokens
and supplies them to the generic patch. Unchanged bodies retain already admitted
tokens. Mesh independently compares old/new tokens and expands retained cells,
including omitted/equal masks. Removed rows remove their nine admitted tokens.
The compact callback returns `membership_expansion == ()`; Mesh remains the sole
cell writer after validation. Original Agent schema/join/support/receipt/coverage,
lease, negative horizon and order checks continue in the same logical profile.

## Owned validation configuration and lifetime

The core `sync_compact_validation` interpreter applies the exact bundled local
schema vocabulary, with strict bool/integer/null/tuple and closed-object rules.
It checks the reviewed raw-schema SHA256 before use. It adds no runtime jsonschema
dependency or uncharged global parsed-schema/validator cache.

One schema graph belongs to each active native plan. Before resource read/decode,
its loader reserves a conservative **8 MiB heap** plus bounded temporary read
heap/encoded credit in the same caller ledger. The temporary bytes retire after
load; the schema reservation lasts until the plan's last parser/validator frame
unwinds. This deliberately conservative reservation is included in source
checks; it is not a claim that dense capacity/resource targets pass. Tighter
configuration representation/accounting and cold CPU remain qualification work.

The parser can explicitly own the validator configuration. Plan close revokes
new accesses immediately, but cannot refund schema/parser/value credit while a
validation/copy call is still active. Iterators use current context budgets, and
public lookup copies reserve advertised bounds before materialization. Saved
errors retain only bounded codes after unwound private frames retire. Shared
budgets, siblings and native owners are never closed by this codec.

## Source evidence and outstanding gates

The [source manifest](evidence/2026-10-16-delta-sync-source/compact-codec.json)
pins Observer and immutable Mesh inputs/check logs. Fifteen new tests use
cyclic GC disabled, retained errors and explicit cleanup without collection.
Actual generic admission reproduces eight frozen baselines and ten transaction
chains, including their independent native roots and separately configured
valid SDK SourceRoots; eight
schema-valid negative fixtures reject at the intended birth/group/old-mask/
expected-old/body/seal gates. Frozen dotted source names such as `agents.full` remain arithmetic-only inputs:
Mesh source configuration rejects them. Tests preserve those fixture bytes,
reproduce their source-root arithmetic independently, then separately compute
the runtime wrapper for explicit valid `agents_full`/`agents_active` sources.
No SDK name check is weakened. Both full/active synthetic fresh proof paths
losslessly export the native DTO through public confirmed views, while schema
loading is forbidden during head confirmation. Equal-mask token changes,
unused wrong-side dictionaries, explicit feature negotiation, strict routing,
pre-read reservation refusal, retained handles, schema graph retirement and
reentrant configuration-close credit are also checked.

This is bounded synthetic source integration, not populated native evidence,
actual compact source dispatch, installed/native pairing, relay/controller or
whole-pipeline acceptance. Runtime native serialization/journal/source encoding
configuration, dense/full/active allocation and RSS, sparse visit/cell counts,
CPU and total cold/recovery bytes, deliverable 2,000-row recovery, populated IPC/
fixed SSH and immutable paired artifact acceptance remain open. Earlier failed
performance results stay failed. The separate completion-transfer/controller
seam and normal a7/a23/full/Tmux/349/writer/provider selections remain unchanged.
