# Current Observer with the corrected control carrier

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Immutable Observer `84d284dab04b68ae0e9070335d017e85564f2ba9` needs no source or
API adaptation for Mesh's compatible control-copy correction at runtime
`14990c789f853441b51af81ea0919facf0aff320`, evidence `50ac1b9e`. This checkpoint
replays only the two existing actual-source runners against that newer pair.
The [receipt](../../evidence/2026-10-17-controller-source/copy-current-pair.json) binds
the immutable exports, unchanged runners, source inventories, loaded files and
new reports/logs. Earlier `a482abb` results retain their original source pins.

On each Python 3.14.8 and 3.11.17, with GC disabled and real errors retained:

| Existing runner | Methods | Scenarios | Result |
| --- | ---: | ---: | --- |
| Basic controller/source/Reader | 2 | 24 | Pass, zero failures/errors/skips |
| Controller/source lifecycle | 2 | 20 | Pass, zero failures/errors/skips |

Each run loads 78 project files whose hashes match the exact owning Git blobs.
The basic runner covers unread Unix IPC and actual pipe stdio, expanded/compact,
full/active and 0/1/4 transactions. It compares received native fragments with
the actual original baseline, transaction, whitespace-padded completion and
head bytes. An independent ordinary Reader admits the material, rejects native
completion and command results as proofs, and confirms with two fresh actual
source heads per scenario before comparing the public native DTO.

The lifecycle runner covers watch survival across acquisition end and expiry,
fresh head/DTO and explicit watch stop. Four-transaction batches plus original
completion retain their five physical input buffers through wire cancellation,
repeated server cancellation, source close and partial write failure. Scope
close revokes usable references while physical credit survives unwind; siblings
still acquire a fresh baseline/head. Final Reader six-counter and relay
five-counter checks are zero. The private physical-buffer inventory and writer
hooks are disclosed test-only audits. Lifecycle Reader admission reserializes
the test oracle; its checks do not add an exact-wire claim beyond the basic
runner. The caller's cache disconnect on partial EOF is also explicit.

The runners use synthetic data and a disposable collection-disabled Runtime,
trusted caller authentication/binding, private Reader nonce setup and native
fixture retirement. Native owner, relay, Reader, client, capture and oracle
storage have separate accounts. These are bounded source integration checks,
not inclusive resource or ordinary selected-route qualification.

Mesh's stamped-header copy/close correction has its own unchanged original
probe, before/final tests and reported 67 focused/386 canonical checks on
Observer `e3441d0`. Those artifacts are verified here, not rerun or attributed to
the current Observer pair. Independent correction closure remains separate
from these four interoperability methods. No public signature change or new
Observer scanner/source capability is needed.

No CPU measurement is rerun. The [current row-reuse owner screen](delta-sync-compact-row-reuse.md)
still fails the strict 25% ceiling: +165.5685% at 500 and +143.5020% at 2,000,
excluding the oracle. Five fallbacks per 2,000-row run and no delivered recovery
baseline remain unqualified. Inclusive overlapping 32 MiB encoded/64 MiB heap,
RSS, dense nine-field capacity, delivered cold/recovery, populated native
providers, fixed SSH, ordinary authenticated/selected Reader routing and exact
immutable installed-pair qualification remain open.

No source/schema/encoding/version allocation, artifact, install, a7/a23
selection, normal service/provider, Tmux/349/writer, sibling or rollout change
accompanies this evidence. Git attribution cleanup remains on HOLD.
