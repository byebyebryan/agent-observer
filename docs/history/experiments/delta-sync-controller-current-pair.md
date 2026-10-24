# Current Observer source with the public Mesh controller

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

Bounded source integration passes for immutable Observer
`f7f7a55e1bbc019d2b866f7e48da85c815c2e031` and Mesh runtime
`a482abbd463d23ebf66f23c60e4e95a521c19cc6`. The Mesh export is evidence commit
`f667588acc9e41010ce30829bf7fb6b46e6f2b6b`; its runtime, tests, contracts and
package metadata are identical to the runtime commit. No Observer API or source
change was necessary. The [receipt](../../evidence/2026-10-17-controller-source/current-pair.json)
pins both exports, the upstream checkpoint, all imported modules and test output.

On each Python 3.14.8 and 3.11.17, with cyclic GC disabled:

- The unchanged Mesh actual-source runner passes two methods containing 24
  scenarios: Unix IPC or real two-pipe stdio, expanded/compact, full/active,
  and zero/one/four transactions.
- Sixty-five existing owning source-retirement, owned-source, completed-change,
  compact-source and compact-export tests pass with no failures, errors or skips.
- All 78 controller-run and 90 owning-run imported project files per version
  match their immutable Git blobs. The complete selected source inventories also
  remain unchanged after execution.

The controller runner uses the supported minted carrier factories and
`serve_sync_relay`, plus the existing owning source, structural HeaderRef and
CompletedChanges methods. It compares original native baseline, transaction,
whitespace-padded completion and head fragments with bytes received through the
controller. The ordinary independent Reader fully admits the material, then two
distinct fresh actual source/relay head proofs produce the exact owning DTO.
Native completion and command results reject as proofs. Physical wire counters
match bytes sent/received after sender drain bookkeeping. Fixture assertions
return Reader's six and relay's five counters to zero and retire native owner
scratch with GC still disabled.

This is an independent execution of the owning Mesh composition runner and
existing Observer tests against the newer pair, not independent test design.
The trusted caller supplies authentication and request binding. Private Reader
nonce setup and native fixture close remain disclosed test scaffolding. The
native Runtime uses synthetic ServiceState with collection disabled. Fixture
captures/client buffers/oracles and separate native/Reader/relay accounts are
outside an aggregate resource measurement. Slow-callback debug messages from
large owning quota fixtures are not latency measurements or test failures.

The Mesh 64-method carrier/controller/relay suite, 383-test canonical gate and
its named before regressions retain their original e344-based evidence; they
are verified from the upstream receipt and are not rerun or reattributed here.
The required current owning repository check is recorded separately. The guide
and runner are retrieved from the evidence commit, since they are not part of
the earlier runtime commit.

The [exact controller contract agreement](delta-sync-controller-agreement.md)
and source-consuming-ref closure remain closed. Current
[owner CPU](delta-sync-compact-transaction-pass.md) still fails the strict ceiling;
five 2,000-row baseline fallbacks and missing delivered recovery remain explicit.
Ordinary authenticated/selected Reader integration, actual compact watch/cancel
and expired-edge stress, inclusive 32/64 MiB accounting, RSS, dense nine-field
2,000-row delivery/recovery, populated native IPC, fixed SSH and immutable
installed-pair acceptance remain open. No schema/encoding/version or package
freeze, producer readiness, normal a7/a23 selection, provider/service, sibling
or rollout changes accompany this evidence-only checkpoint. Git attribution
cleanup remains on HOLD.
