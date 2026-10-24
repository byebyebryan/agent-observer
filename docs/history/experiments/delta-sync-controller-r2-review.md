# Observer review of the exact controller R2 packet

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Reviewed Mesh `33cb57c98ca3062f139ea1fd0c68b15bd5abd8d6`,
`docs/delta-sync-controller-proposal-r2.md`, 31,399 bytes, SHA256
`89b24a9f3191bcded303d33c8b2ed973335b703811185abf1186848fbd562f48`.
The accompanying manifest is SHA256
`40092583a0e5732f62512d6026eb96b28fce5623e5e0d4a64e11af291a09ba3c`.
Both were read from an immutable Git export on Starship. This supersedes the
pending R1 review; the original R1 packet and its evidence are unchanged.

Status: **source/head/context/lifetime direction compatible, with one concrete
changes-bound wording clarification required before unconditional exact-byte
agreement**. This is contract review only, with no controller/carrier runtime,
schema allocation, resource, I/O or whole-producer acceptance. The
[receipt](../../evidence/2026-10-16-delta-sync-source/controller-r2-review.json) pins
the actual reviewed bytes, source references and arithmetic outputs.

## Compatible source and ownership boundaries

The configured relay still chooses host/source/profile/descriptor/encoding and
the structural callbacks. Network commands cannot choose imports, native
sockets, user identity, providers or selectors. Observer's expanded and compact
sources keep the same public owned session, CompletedChanges, head, watch and
close interfaces. No native field, support, receipt, tag, cursor, body schema or
source request grammar changes here. A generic command HeaderRef is not an
Observer native header, input ref, profile or authority token.

The narrow terminal receipt record resolves the earlier cleanup contradiction:
end/cancel cleanup may retain only their captured outcome/IDs/original deadline,
while material/proof/work success still requires live work. Exact request or
connection retirement invalidates every receipt. A cancelled head's earlier
deadline can suppress its original result while its cancel command still reports
cleanup within the original capsule deadline. Neither permits more source work,
renewed native evidence, a new proof window or an implicit successful chain.
The two-record bound, locked immutable `through`, original deadline checks and
physical drain requirement preserve bounded cleanup ownership.

The minted carrier's first-userspace-read floor preserves command time through
coalesced tails, fragmentation, paused reads and blocked output. It is explicitly
a local lower bound, not a remote clock comparison or a claim about earlier
kernel arrival. Old/prebuffered userspace bytes without proved provenance reject;
dequeue cannot stamp a new deadline. Conservative range merging can only shorten
a bound. Receipt/frame/ring/header/copy/task storage remains in the shared ledgers
until actual aliases and I/O retire. A carrier owns one connection, never the
shared native source, factory, sibling or ledger.

The proposed `not_after_ms` keyword is a generic relay-side restriction. It can
shorten the existing two-second bound before source I/O and through scanner,
copy, output locks, writes and drains. It changes no Observer source method.
The independent Reader still owns its original acquisition/proof deadline and
fresh nonce. Actual pre-write expiry, ingress provenance, partial output,
cancellation and quarantine behavior remain required implementation evidence.

## Required changes-bound wording

R2's changes table says `1..4 transactions` and `no extra terminal-control
allowance`. That can be read as requiring a nonempty result or counting the
terminal control inside `maxBytes`. Both readings conflict with the already
accepted [completed-source contract](delta-sync-completed-changes.md):

- `maxTransactions` is a capacity in 1..4. The result may contain zero
  transactions only when base and target are exactly equal.
- `maxBytes` bounds the sum of transaction frames, at most 8,388,608 bytes.
  The original Agent completion remains separately bounded by 16,384 bytes;
  the complete nested Mesh control independently fits 65,536 bytes including LF.
- All transaction/control/container/transport bytes still count in the same
  shared resource and wire totals. These separate frame limits add no service
  memory cap or deadline allowance.

Proposed replacement wording for that row:

> Exact live capsule; existing completed-changes path, no watch; exact tags;
> maxTransactions capacity 1..4 and result 0..capacity, zero only for base==target;
> maxBytes bounds transaction bytes only, 1..8,388,608; original completion uses
> its existing independent native/nested-control limits and shared ledgers.

The later R2 paragraph giving Agent 16,384/nested Mesh 65,536 bounds is already
correct. Existing source exact-8-MiB-plus-control and zero-chain cases establish
the behavior; no native field, source/API rewrite or increased allowance is
requested. Mesh has the one concrete wording request. Dependent dispatcher code
must preserve this existing source contract.

## Arithmetic and acceptance limits

Both Python 3.14.8 and 3.11.17 reproduce the R2 oracle output byte-for-byte:
15 positive and 32 rejection cases plus the unchanged R1 14/34 arithmetic.
The 8,484-byte R2 output is SHA256
`97f0b5c5b99329cc1538e996c9cb7a7f80ad884154b17d0df7fcab3e16a3c9ce`.
These are executions of Mesh's stdlib model, not independently designed runtime
or actual ingress tests. They prove neither parser minting nor buffer accounting,
clock sampling, concurrency, native source delivery or cleanup timing.

The [retirement-query implementation](delta-sync-source-retirement.md) is a
separate already-committed source checkpoint, not a remaining shape agreement.
Controller review does not reopen A1/R4/R2 normalization, that source fix, or a
general approval gate. Original CPU failures, shared 32/64 MiB caps, dense/cold
and 2,000-row recovery, populated IPC/fixed SSH, RSS and exact immutable installed
pair gates remain. No sibling, normal service/provider, selection or rollout
change follows this review.
