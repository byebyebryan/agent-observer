# API v1 packaged and native acceptance

Date: 2026-10-06. Status: accepted Observer subset; normal selection and client
migration remain separate. No Agent Plus implementation or ordinary provider
action was performed.

## Frozen artifact

- Package: `agent-observer 0.3.0a2`.
- Source: `7ffbe246e6bac2c9d320328ce639b833b3a73bfa`.
- Wheel: `agent_observer-0.3.0a2-py3-none-any.whl`.
- SHA256: `98ce1f9203f97c13adc2d19cb11bf8f13a0dc3889fc899debc94da1bf0b1430d`.
- Candidate prefix on both hosts:
  `/home/bryan/.local/share/agent-observer/0.3.0a2-98ce1f9203f97c13`.
- API 1; snapshot/watch wire 3; write wire 1. Snap has the isolated Claude
  history dependency profile; Starship has the core profile. Wheel bytes,
  entrypoints, schemas, dependency isolation and API declaration are verified.

The [manifest](../../../artifacts/observer-0.3.0a2.json) and host receipts bind
this tuple. Provider image hashes in native reports are provenance and changed
context guards, not release compatibility lists. Normal Observer entrypoints
still select a11/wire 2. The candidate wheel is archived on both hosts. Installing
this immutable prefix did not select it or invoke providers.

## Independent consumer and ordinary native comparisons

The reference consumer imports jsonschema and the standard library, with no
Observer imports. It reads exported schemas, validates all v3/write-v1 fixtures,
round-trips strict input, checks filtering/order/full-reference selection and
passes a serialized 4,096-row CLI inventory. Source tests separately exercise
semantic negatives, byte/node limits, repeated churn, stale age, child
reconciliation, incompatible contracts, duplicate workers and write receipts.

Two bracketed ordinary comparisons on each host use the installed candidate
against independent native protocol/files/process evidence. Another Observer
result is not the reference. Stable field comparisons report no projection
mismatches:

| Host/provider | Public rows | Independently live | Age comparisons | Limit |
| --- | --- | --- | --- | --- |
| Snap Codex | 51 | 6 loaded contexts | 51 | Saved-only running/phase/kind remain unproved |
| Snap Claude | 30 | 3 verified workers | 29 | One command-only history has unproved membership/kind/age; 3 retained terminal jobs prove parked |
| Starship Codex | 96 | 8 loaded contexts | 96 | Saved-only running/phase/kind remain unproved |

The saved CLI-only Claude UUID `1f66423b-8c09-460a-951f-f4a22e353fec` is retained
as unknown. The independent conversation scan cannot prove command-only history
membership; it does not falsely classify local command records as user turns.
Native fallback titles, bounded history tails and unknown saved classifications
are explicit reference limits. Earlier a1 Starship samples had two newly created
contexts with no activity clock and sampling races; later a2 samples had settled.
These changes were external work, not an Observer action.

Two concurrent readers per host each emit four schema-valid, correctly revised
frames at a requested two-second interval. Reports capture RSS/FD ranges and
zero unchanged-value native phase clock renewals. This is bounded read/watch
acceptance, not a long-duration service or suspend/network test.

## Isolated native transitions

Private user/mount/PID namespaces, private temporary directories and masked
ordinary provider paths are established before native startup. Exact installed
CLI bytes are copied and bound only inside those namespaces so ownership maps to
the proof UID; ordinary package images are not modified. Codex uses its current
managed cache target, not an allowlisted release. Test settings and borrowed
authentication exist only in disposable stores. PTY output is discarded.

| Case | Native result |
| --- | --- |
| Codex, both hosts | New, real TTY entry, exact saved/live Resume, repeated entry, native conversation clock and rename/read/mtime age preservation pass |
| Codex, both hosts | Owned daemon failure is visible; saved discovery survives, offline saved Resume rejects, explicit New recovers runtime and exact Resume preserves age |
| Codex, Snap | Changed prepared configuration rejects visibly before provider execution |
| Claude, Snap | New, repeated native attach and native title/clock preservation pass |
| Claude, Snap | Working to held approval and typed question are reported blocked; no answer/approval is supplied |
| Claude, Snap | Viewer detach preserves the worker; explicit native Stop removes the bound worker; three held samples report parked/unknown phase with unchanged age |
| Claude, Snap | Saved Resume explicitly returns a copied UUID; healthy attach and saved Resume survive a missing sibling job record; copied activity remains unknown until native persistence |

The `/exit` command did not close the proof PTY client, so its UI recognition is
unresolved. Detach and explicit native Stop are the accepted cases. This attempt
found a real a1 defect: native local command/output envelopes can omit `isMeta`
and incorrectly advance conversation age. A2 excludes those reserved envelopes;
ordinary slash-looking conversation prompts still count. A1 is a rejected stable
candidate and is never selected.

Owned cleanup receipts verify all three test namespaces stopped and their
borrowed authentication/history were removed. Ordinary entrypoint paths and
installed CLI hashes match the unchanged selected artifacts. No ordinary
configuration, hooks, service or session was selected, interrupted or renamed.

## Acceptance limits

API v1 freezes the documented public consumer semantics, not every upstream
behavior. Claude foreground questions and transient helper ancestry, lossless
native event replay, Codex parked inference, offline saved Codex Resume,
current-client conversation binding, remote/suspend recovery, GUI focus/Open and
physical device acceptance remain unsupported or separate gates. Daily compatible
provider updates do not require registration; semantic drift still requires
independent comparison. Notification source/client work has a separate checkpoint.

The [API contract](../../api-v1.md), [wire specification](../../public-contract-v3.md)
and [execution record](../../stable-api-execution.md) define client migration.
The JSON files here retain bounded metadata only; no prompts, responses, tool
payloads, credentials or terminal captures are repository evidence.
