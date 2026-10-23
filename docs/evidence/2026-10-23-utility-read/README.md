# Bounded read utility qualification

2026-10-23. The [developer example](../../../examples/current_summary.py) and
[public-read guide](../../utility-read-guide.md) exercise existing local Service
4 and optional Mesh SDK1 working-set interfaces. They add no installed command,
collector, provider adapter, daemon, action, profile/schema or deployment target.
The example diagnostic JSON is not a new normative API.

The accepted implementation uses a duration bound and periodic expiry checks.
Local reads use public `frames` and `ReadCache`; Mesh uses one profile instance
for `configured_reader` and `PreparedWorkingSetAgentWatch`. A quiet tick keeps
the pending SDK read alive. Stream/setup failures and final cleanup revoke the
view. Local setup follows the transport's documented minimum-one-second budget.

## Validation

- The final owning `scripts/check --require-working-set-mesh` gate passes with
  the installed a8/a24 interpreter and zero skipped cases. Exact command,
  count, example hash and scope are in [the receipt](receipt.json).
- Seventeen focused tests pass on Python 3.11 and 3.14 with the exact a8/a24
  wheel tuple. Ruff lint and format checks pass. Controlled tests cover real
  Service4/configured Mesh paths, quiet expiry, setup/deadline failures,
  complete-empty/partial/unavailable distinctions, namespace projection,
  terminal revocation and owned cleanup preserving a sibling reader.
- A copied example executes outside every checkout with isolated imports from
  the installed a8/a24 packages. Six cases pass: Starship local service, local
  working-set Mesh, Snap Default, Snap Work, Carbon, and a missing local socket.
  The missing socket is an expected nonzero result. Snap Default/Work namespace
  digests are distinct. Final output always has zero current identities.
- The existing dashboard bundle 164b7f99c40e7676 verifies against its selected
  manifest. Nineteen existing prepared/working-set/two-home consumer tests pass
  with zero skips using its exact selected source 629af372 and a8/a24 packages.

Two review failures were fixed rather than hidden: the first Mesh draft could
cancel its quiet-tick iterator too early; the first installed local smoke then
exposed the public ContractError/deadline boundary. Focused regressions use the
real public exception type. The failed initial smoke receipt and source copy
remain separate from the final qualified artifact.

## Evidence boundary

The smoke checks consume already cached facts and preserve explicit unavailable
scope/lease states. Successful execution is not a claim that every native source
stayed current. No native classification comparison, notification replay,
provider action, physical display/input/ACK, suspend, capacity or performance
acceptance is established. No selected installation was changed.

All existing `agent_observer` runtime/contract files remain byte-identical to
the starting a8 source. This is a developer recipe qualification against an
unchanged released SDK tuple, not a new producer release or a reassignment of
earlier acceptance. Producer, consumer, publication and fleet gates remain
independent.
