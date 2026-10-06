# Observation wire v3 candidate

Date: 2026-10-06. Package candidate: `0.3.0a1`. This is the source candidate for
the [first stable API execution](stable-api-execution.md), not new installed or
native acceptance. Snap/Starship normal entrypoints still select a11 wire v2.
The first stable API release label is independent of these wire/package numbers.

Wire v3 replaces the strict [v2 prerelease](public-contract-v2.md). There is no
v2 collection option, automatic conversion or additional legacy provider stack.
Historical v2 fixtures/artifact receipts remain for provenance and rollback.
Consumers must validate the explicit supported wire version and migrate their
reader/cache at the separate client checkpoint.

## Changes from v2

- `activity.at` remains a current conversation event timestamp. An absent row
  retained through incomplete coverage has `at=null`, `health=stale` and optional
  `lastKnownAt`, preserving its original event timestamp and source. Repeated
  polls never advance that timestamp. A fresh observation replaces the retained
  evidence. Last-known activity requires stale health, no current timestamp and
  its original nonnull source; it does not establish current work or authority.
- Read-client ordering uses current activity or explicitly stale last-known
  activity after the existing blocked/waiting/working/unknown attention order.
  Human age prefixes last-known ages with `stale:`. Unknown remains unknown;
  collection, creation and file modification do not become conversation age.
- `history.sdkVersion` is bounded diagnostic text, without an approved-version
  enum. Observer's packaged SDK dependency is a separate reproducibility choice.
- Snapshot and watch schema version/URN are 3. Write request/plan/result remain
  version 1, with their required cross-object semantic validation.

Full scoped identity, native IDs, runtime/phase/outcome/health separation,
coverage scope, project context and passive source invariants retain their
previous meanings. Required provider-contract compatibility remains a separate
implementation/native checkpoint; this wire cutover does not replace a11's
provider allowlists by itself.

## Bounded watch and transport

The wire permits at most 4,096 session rows. Canonical snapshots fit within
8 MiB minus 1,024 bytes reserved for the watch envelope. Newline-terminated watch
frames fit within 8 MiB. The public decoder allows at most 2,000,000 JSON nodes
and depth 32, independently of the byte/row limits. All enabled bounds apply;
large shape-valid objects are not automatically valid transport documents.
`parse_snapshot` and `parse_watch` apply both structural and semantic validation.

Watch reconciles the complete fresh inventory before child/provider filtering.
A freshly confirmed child therefore cannot be restored as an old unknown row.
Normal CLI watch/list exclude confirmed children; unknown classification remains
visible. An unavailable or partial scope does not prove deletion or parked.

Retention prioritizes all current rows, then prior rows in the bounded previous
inventory order. Row and serialized-byte budgets can evict old retained rows.
Eviction emits a `gap` with `reason=retention_limit`, followed by a full
bounded `resync` view carrying that finite error. It means loss of Observer's
retained view, never native deletion or inactivity. A client replaces its stream
view on resync rather than merging missing rows forever; its own history cache
is a separately bounded presentation concern. Complete native inventories end
unneeded retention; recovery removes the transient retention-limit diagnostic.

Collection/retention errors stay within the CLI watch loop and emit a gap.
Backpressure remains bounded; restarting watch begins a new stream with a full
snapshot. Heartbeats and stream revisions are collection evidence, not native
turn IDs. No completion-event, lossless delivery or replay guarantee is added.

## Conformance and remaining gates

Export the bundled schemas with `agent-observer schema --kind snapshot` or
`--kind watch`. Metadata-only fixtures are in `tests/fixtures/contract-v3`.
Source cases cover stale age and recovery, unknown-to-child reconciliation,
maximum serialized inventories, repeated retained-row churn and byte overflow,
SDK diagnostic extensibility and explicit rejection of old wire v2.

The stable API surface/error policy, provider contract migration, independent
packaged/native acceptance and downstream reader migration remain pending.
Notification sources/publication are separate; this sampled watch contract is
not a reliable source of every native completion.
