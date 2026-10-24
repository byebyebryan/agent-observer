# Mesh a24 upgrade: complete views, delta delivery disabled

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

The optional networking dependency now targets released Mesh Plus 0.1.0a24.
It supplies the working-set SDK1 registration previously checked against a
private counterpart. Full, active and working-set sources continue to publish
complete selected views through ordinary `CachedPublisher`, `Bridge`, `Client`
and `Reader` APIs. The 72-hour working-set default, independent active branch,
explicit full-history route and home namespaces are unchanged.

## Exact dependency and route choice

The reviewed [released manifest](../../../artifacts/mesh-0.1.0a24.json) pins:

- [Published experimental release](https://github.com/byebyebryan/mesh-plus/releases/tag/v0.1.0a24).
- Wheel `mesh_plus-0.1.0a24-py3-none-any.whl`, SHA-256
  `9bca5b554babfa59ba56b1a4ac5e8e5c66a85e63709731ee1fe7d4f0ed6a18a6`.
- Runtime source `7e152d22fa57fc45049438b50877433d8c96f6d8`; signed release tag
  `v0.1.0a24` peels to `bb0c45399e5b8264c9936ca48457cc9a442431df`.
- Optional source requirement `mesh-plus>=0.1.0a24,<0.2`. Core runtime
  dependencies remain empty. Versions identify artifacts; public interfaces
  and profile/schema checks still decide compatibility.

The released package includes two opt-in delta implementations. Neither is
selected by Observer's ordinary routes:

1. The retained semantic sync engine stays dark. The local service defaults to
   `experimental_sync=False` and rejects sync requests before constructing material.
2. The new `mesh_plus.view_feed` protocol is unselected. Observer does not wire
   `ViewFeedBridge`, `ViewFeedClient`, its `configured_reader`, `view-feed-serve`
   or `view-feed-bridge` into the chosen reader/publisher paths.

Ordinary delivery sends the complete selected view on publication and obtains
fresh full native nonce proofs. Heartbeats and unchanged views do not renew
source receipts. Existing currentness, expiry, gap/resync, source-incarnation
watermarks and cleanup requirements remain in force. The Tmux product choice
motivates this scope; it supplies no measured Agent CPU or memory result.

## Owner checks

CI retains core-only discovery and the explicit released a23 compatibility
lane. The required working-set lane now uses the hash-pinned public a24 wheel
on Python 3.11 and 3.14 on normal CI events; it no longer needs a manual private
Mesh source revision. Unsupported optional tests skip only for SDK/profile
absence. Unexpected import, schema or descriptor failures remain errors.

The isolated installed gate accepts the downloaded wheel and published manifest:

```sh
/absolute/prefix/bin/python -I -B scripts/check-mesh-release \
  --prefix /absolute/prefix --manifest artifacts/mesh-0.1.0a24.json \
  --wheel /absolute/download/mesh_plus-0.1.0a24-py3-none-any.whl
./scripts/check --require-working-set-mesh
./scripts/check-mesh-owner --installed
```

The first command compares every immutable installed wheel file and package
inventory with the hashed archive, rejects editable/source installs and checks
ordinary full/active/working-set factory wiring. It opens no native socket.
Delivery tests separately block the delta entrypoints while exercising complete
unchanged/changed publications, fresh proofs, expiry, reconnect and cleanup.
The historical `verify-mesh-artifact` archive gate retains its original manifest
formats and release bounds; it is not used to reinterpret the new public manifest.

## Installed candidate and managed boundary

The [qualification report](../../evidence/2026-10-20-mesh-a24/REPORT.md) records exact
isolated wheel/source inputs, executed gates and exclusions. Its installed
environments are disposable candidates; they do not replace normal services.

Managed owners can prepare a replacement of the prior private Mesh wheel with
the exact public a24 URL/hash above in each independently owned reader/publisher
prefix. Preserve the explicit trusted Agent factory, profile/window, host/home
binding and ordinary bridge command. A named owner launcher can call
`agent_observer.mesh_publisher.main` without overwriting the wheel's `mesh-plus`
entrypoint. The cached publisher gate accepts `--publisher-launcher` for this
purpose; its historical default shim remains supported.

Normal service links, collectors, publishers, dashboards, provider daemons and
Tmux's independent selection are unchanged by this source/dependency checkpoint.
No consumer repository, new schema/ID, package release, fleet rollout or delta
pilot is included. Previous native, cost, capacity and physical-device evidence
keeps its original tuple; this upgrade adds no performance claim.
