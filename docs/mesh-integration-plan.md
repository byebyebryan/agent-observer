# State-only Mesh integration

Date: 2026-10-09. Authorized implementation following the Mesh catch-up and
[state-push design](state-push-design.md). Mesh source starts at `dc79623`
(unreleased a3); Observer starts at `8776cc6`. The frozen Agent profile is
`agent-observer.mesh-candidate.v1`, consuming API 2 / snapshot 4 / service 2.
No native observation or public wire version changes are required.

## Ownership and delivery

Observer core/local service retain collection, reconciliation, coverage, native
clocks and finite unsaved retirement. Mesh transports cached state through
fixed configured host sources and owns IPC/SSH, immutable catalog scope,
nonce-bound remote validity and reconnect. The optional Observer mesh read
client uses the Mesh Reader and ReadGuard; it does not implement another SSH
backend, query providers or write route health. Native local diagnosis remains
available. No notification/event, action, attachment, device or frontend work is
included. A shared fleet broker remains outside this pass.

Mesh raw envelopes preserve all native rows and metadata, including children.
The effective facade conservatively omits unsaved historical runtime rows;
saved metadata and unrelated providers retain independent validity. Human
presentation may filter/order rows. Machine frames retain the lossless profile,
original source receipts and host-grouped canonical rows.

## S0 — adapter and SDK acceptance

Bind the Agent adapter to the supported service descriptor for frame limits.
Close the unsaved stale-runtime projection gap with a regression covering
independently fresh history and unchanged raw reconstruction. Supply reusable
configured Reader binding in Mesh, with route reporting explicitly disabled for
read-only consumers. Preserve the frozen lock, schemas and authority bytes.
Use a new unreleased Mesh a4 candidate rather than replacing prior package proof.

Acceptance: frozen source/profile parity, core and both-domain owned IPC/SSH
checks, strict lifecycle/expiry/concurrency tests, and isolated wheel parity.

## S1 — optional mesh read CLI

Add `agent-observer mesh api|snapshot|list|watch`. Snapshot and default watch emit
unfiltered Mesh profile frames. List and explicit human watch use the effective
facade, original age and shared urgency/activity ordering. Filters never alter
canonical machine envelopes or provide negative evidence. Validate every frame;
disconnect/close owned readers on errors, cancellation and output failure.
Load Mesh only for these commands; core/local service remain dependency-free.

Acceptance: dependency/import isolation, same local/fleet parser, warming/empty/
partial outcomes, saved/unsaved faults, children, exact identities, age/order,
gap/resync and EOF handling, bounded output, and the full Observer check.

## S2 — immutable and current-host proof

Build new Observer a12 and Mesh a4 wheels, bind source revisions and checksums,
then verify installed bytes/imports independently of source. Prove packaged
local and fleet pull/push against owning Observer CLI and independent ordinary
native evidence on Snap and Starship. Record source/cache timing and accepted
provider limitations. Use owned temporary bridges/endpoints for induced faults;
never restart providers or kill normal sessions for this integration.

## S3 — scoped operational selection

After S0–S2, select reviewed client/bridge artifacts through managed configuration,
fixed private source descriptors and a separate host-local Agent bridge unit.
Keep current provider settings, a11 collection/service and a16 writer selection.
Preserve the deployed SSH Plus authority and unrelated Tmux services. Verify
serialized per-host bridge recovery, reader reconnect, source fault isolation,
catalog replacement, rollback/reselection and actual one/multiple-reader costs.
Preserve source/installed/live evidence separately. Physical suspend, GUI/device
acceptance and downstream adoption remain separate.

The public optional dependency follows Mesh's supported contract; exact artifacts
are operational provenance, not provider release allowlists. Commit coherent
checkpoints and preserve unrelated source/live drift. A detected producer defect
opens an Observer-only fix gate before continuing client rollout.
