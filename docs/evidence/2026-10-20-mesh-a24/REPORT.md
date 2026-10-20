# Released Mesh a24: ordinary complete-view qualification

This source/dependency checkpoint upgrades optional Mesh to exact released
0.1.0a24 and explicitly excludes both semantic delta sync and view-feed routes.
The [upgrade guide](../../mesh-a24-complete-view-upgrade.md) defines the selected
ordinary APIs, exact artifact and managed-owner handoff. Runtime provider,
service, consumer and fleet selections remain unchanged.

## Inputs and result

The implementation starts at Observer
`58b90e1a4a6b57e2c07d10856206908d2619af5b`. The optional requirement changes
to `mesh-plus>=0.1.0a24,<0.2`; no observation runtime/profile/native schema bytes
change. CI keeps core-only and a23 compatibility lanes and makes the exact
released a24 working-set lane automatic on Python 3.11 and 3.14. The prior manual
private-counterpart SHA workaround is removed.

The public release assets were freshly downloaded, checked against SHA256SUMS
and GitHub's signed release attestation. The remote annotated tag readback peels
to `bb0c45399e5b8264c9936ca48457cc9a442431df`. Mesh wheel SHA-256 is
`9bca5b554babfa59ba56b1a4ac5e8e5c66a85e63709731ee1fe7d4f0ed6a18a6`.
The exact published manifest is retained at
[artifacts/mesh-0.1.0a24.json](../../../artifacts/mesh-0.1.0a24.json).

A local, unpublished Observer wheel is installed beside that released wheel
in separate private Python 3.11.17 and 3.14.8 prefixes. It retains the existing
package version as a source qualification build; it is not the hosted a7 artifact.
Its SHA-256 is
`f3f9278c2e9bd4735433d2e255389c22ce9d623210237bdcf8f9a9558741511b`.
Installed checks compare all 105 immutable Observer wheel files and 111 Mesh
wheel files with their archives. Neither package is editable. Optional PEP 610
archive hashes may be omitted by uv for local files; direct archive installation
and actual file/inventory parity are independently required.

## Executed gates

The [receipt](receipt.json) binds final source inputs, output hashes, interpreter
versions, exact counts and exclusions. The private output root is
`/home/bryan/.cache/observer-mesh-a24-20261020`; raw provider payloads are not
collected or stored. Reproduce the installed checks with
[verify_installed.py](verify_installed.py), using each isolated prefix's Python
with `-I` and the two exact wheel paths.

- `scripts/check --require-working-set-mesh` checks the full repository against
  released a24 on Python 3.11 and 3.14, including existing proof/lease/continuity
  and default-off semantic-sync regressions.
- Clean core-only and released a23 compatibility checks preserve their explicit
  optional skips. Missing SDK/profile rejection in required mode is retained.
- Installed owner conformance runs seven profile and ten network cases per
  interpreter, with zero failures/errors/skips.
- The new selected-wiring test makes published view-feed and sync entrypoints
  fail if called, while ordinary factories and real disposable IPC deliver
  unchanged and changed complete views. Fresh native proof nonces differ,
  restored native frames equal the source captures, original expiry revokes
  membership, and reconnect/close leaves no owned channels or pending reads.
- Installed public CLI/local IPC and fixed-command localhost SSH reach the
  three-row synthetic source with ordinary full-view proofs. Connections and
  cleanup counters return to zero; the owned Runtime thread stops. The named
  owner launcher supplies the trusted Agent factory without modifying the
  wheel-generated `mesh-plus` entrypoint.
- Ruff, workflow syntax, pip dependency checks, Markdown links/fences and Git
  whitespace checks are part of this checkpoint. Hosted CI is not dispatched by
  local qualification.

Luna implemented the dependency/CI change and focused selected-route regression.
The primary reviewed/integrated it, verified the released assets and exact
installed wheels, added the release/owner-launcher checks and evidence runner,
and ran the required final gates. No public SDK incompatibility or observation
runtime correction was needed for this upgrade.

## Delivery boundary

Both delta routes remain unselected. Existing view windows, identities,
source-clock/currentness/expiry meanings, original receipts and full nonce
proofs are preserved. The earlier delta CPU/capacity/recovery failures are not
rerun, reopened or promoted. No new performance/capacity saving is claimed.

The installed prefixes and owned SSH server are disposable local fixtures with
synthetic accepted state and `collect=False`; no native provider is invoked.
This is not a populated native/fleet comparison, actual remote fixed-SSH rollout,
inclusive RSS/resource gate or consumer/device acceptance. Normal links,
services, daemons, selected dashboards, Tmux and sibling repositories are
unchanged. Managed owners receive the exact released dependency proposal in
the upgrade guide; production adoption is a separate scoped operation.
Historical a23/private-pair evidence retains its original provenance.
