# Observer operational baseline execution

Date: 2026-10-07. Status: scoped O0–O5 complete after the authorized regular goal loop. This is an Observer producer/operations pass. Agent Plus,
networking, native event signals, notification publication and firmware have
separate implementation and delivery gates.

## Outcome and boundaries

Complete service workspace configuration, freeze an independently accepted
artifact, then select Observer-only CLI entrypoints and a persistent user service
on Snap and Starship. Snap observes Codex and Claude; Starship observes Codex.
Preserve ordinary provider sessions, settings, hooks and downstream selections.
API v1 snapshot/watch 3 and write 1 remain unchanged; service protocol 1 stays
separately prerelease. Provider compatibility follows required contracts, not
release/hash allowlists. The older selected wire-2 CLI has a deliberate cutover;
selection does not migrate Agent Plus's bundled reader.

Initial cadence is runtime/history 30/120 seconds on Snap and 20/60 on Starship,
with the existing 10-second collection deadline. A user service must retain the
native UID/PID/time/home/endpoint context. No socket activation, lingering or
ordinary provider-policy changes belong to this rollout.

## Checkpoints

| Checkpoint | Exit | Status |
| --- | --- | --- |
| O0 baseline | Selected and candidate installed CLI/native comparisons, preservation bookends and host topology | Complete; old selected image gates lose supported native facts, while candidate matches its accepted subset |
| O1 workspace | Startup-only bounded workspace configuration; same direct/history enrichment and leases | Source complete as a7; 283 tests and focused Ruff checks pass; installed gate remains O2 |
| O2 artifact | Immutable wheel, installed read/write/service conformance and affected native proof | Accepted a7 on both hosts; native entry is bounded to the explicitly configured disposable pairing |
| O3 operations | Observer-only managed selectors/unit/manifest/check/apply/rollback; dry run and drift review | Source accepted in chezmoi `1d42b72`; six-target dry runs pass; Starship's preexisting source drift is preserved |
| O4 selection | Scoped rollout, normal commands, unit restart and rollback/reselection verified | Accepted on both hosts; six-target rollback, reselection, restart and forced publisher failure pass |
| O5 closure | Sustained multi-reader measurements, final independent native comparison and client handoff | Complete: both 30-minute normal-unit checks, direct/cached native comparisons and current client handoff pass within documented limits |

Each accepted checkpoint runs `./scripts/check` and affected checks before a
scoped commit. Source changes require a new immutable artifact; historical
acceptance receipts are not rewritten. Managed source lives in chezmoi and gets
its own scoped validation/commit. Its existing combined Observer/Plus pilot
selector must not be used as the new rollout authority.

The installed public CLI is compared with independent native references using
[the validation workflow](observation-validation-workflow.md). Another Observer
projection is a regression check, not independent proof. Native writes for proof
use only verified disposable namespaces and masked ordinary homes. Metadata-only
receipts live in [the operational evidence](evidence/2026-10-07-observer-operations/REPORT.md).

## Remaining independent gates

Physical suspend/wake needs an operator window. Claude foreground questions and
PTY `/exit` recognition, general Codex parked inference, every topology's idle
retirement and event-assisted latency remain explicit limits. Shared push still
distributes views from polling. Remote streams, notification events, Agent Plus
and dashboard/device acceptance remain separate tasks after producer acceptance.

The current installed Codex CLI and managed daemon disagree on the default
`api_key_model_discovery` setting in a fresh disposable store. Native entry
acceptance explicitly disables that setting only in the fixture; it does not
establish ordinary default New/Resume startup or authorize a provider settings
change. Native observation succeeds with the ordinary current runtime. This
provider entry limitation remains separate from producer read/service acceptance.
