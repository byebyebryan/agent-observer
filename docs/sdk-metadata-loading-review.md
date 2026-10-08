# Read-only SDK metadata initialization review

Date: 2026-10-07. This is a focused producer cost review, independent of provider
policy, frontend work and the pending aggregate-memory budget clarification.
The SDK is an Observer dependency; its source lock is not a native provider
version allowlist. The [cost follow-up](native-hints-cost-follow-up.md) retains
the original resource targets and separately installed artifact bounds.

## Demonstrated cost and proposed binding

The installed a10 worker imports the SDK's public package initializer for
`list_sessions`. That initializer also loads client, MCP, transport, mutation
and model code which the metadata scan does not call. A disposable read-only
prototype imports the existing SDK metadata implementation under a private
package namespace, without executing that broad initializer. It does not patch
SDK files, replace its parser or retain cross-request transcript caches.

On 31 identical owned synthetic histories, full and leaf loading produce
byte-identical allowlisted projections. One run measured 0.551 versus 0.057
CPU-seconds. This is a small initialization spike, not native coverage or cost
acceptance. The pinned SDK's `_internal.sessions` imports its own `types` and
session-store validation plus standard library/AnyIO. The package initializer
re-exports the same metadata functions. This code inspection explains the
prototype result; it is not an upstream promise that private modules stay stable.

The worker already depends on private SDK lite-parser functions to bind a
proved conversation file rather than the global catalog's companion preference.
Make the additional initialization dependency explicit and confined to that same
isolated worker. Keep SDK 0.2.163 as the reproducible library lock. Resolve the
single canonical installed package directory with Python's isolated search path,
construct a worker-private package namespace and load `_version` and
`_internal.sessions` relative to it. Verify the required version, callable
metadata functions and owned package paths. No SDK class or module name enters
the public JSON contract. Missing/changed bindings fail bounded history coverage;
there is no speculative fallback to another provider or SDK implementation.

## Authority and failure boundaries

- Install the existing immutable write/network/process audit guard **before**
  loading any SDK module. Preserve it for the helper's entire lifetime.
- Retain the existing one-request helper, owned group, hard deadline, bounded
  output, census, file-descriptor bookends and publisher-death cleanup. Do not
  inline the SDK into the publisher or relax the guard to save a process.
- Continue calling the SDK's actual metadata parser and catalog implementation.
  Core validation, companion resolution, child classification, native message
  clocks and partial coverage remain unchanged.
- Reject ambiguous package locations, loader/path substitution and unavailable
  functions. A future intentional SDK dependency upgrade requires focused
  binding and equivalence proof; native CLI upgrades keep their contract rules.

## Acceptance before artifact or rollout claims

First test a package whose initializer would fail or launch a client, verifying
that only its metadata subtree loads. Check absent/malformed required functions
and loader locations, and ensure the existing audit guard rejects attempted
writes/network/process actions. Compare full and leaf projection over synthetic
companions, unknown kinds and real privately copied saved histories with stable
bookends; retain metadata-only comparison results and remove copied histories.
Then freeze separately, verify both profiles and public schemas/consumers, prove
ordinary installed CLI/native IDs/ages and focused disposable Claude workflows,
and repeat matched quiet/active CPU/RSS measurements. The memory target is not
redefined by this optimization. Hint-unit selection and 30-minute operational
acceptance still follow P5, never from the loading spike alone.
