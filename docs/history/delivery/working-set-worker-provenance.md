# Canonical worker clock provenance correction

> Historical record. This document preserves its original checkpoint and may describe retired providers, interfaces or plans. Use the [current documentation](../../README.md) for supported setup and behavior.

2026-10-18. Mesh's exact review of native component e48240d identified a conflict
with [R1](working-set-contract-r1.md): Runtime installed a causal L/W/U bracket
for any accepted injected worker, although only the canonical collector promises
that its wall sample W is taken after collection. This is a source prerequisite
finding, not a reported native exploit or a new SDK/wire requirement.
The [record](../../evidence/2026-10-18-working-set/worker-provenance/README.md)
preserves the original review and before result.

Runtime now captures the exact installed canonical spawn method at construction.
Each started worker receives a private local provenance token only when that
same method actually created it. Injected, replaced and subclass worker hooks
receive no token. A copied or cached structurally valid snapshot cannot supply
one through the worker pipe. No custom-worker attestation API or native frame
field is introduced. Equivalent alternative workers need an explicit owning
contract review before acquiring this capability.

After successful parsing, Runtime supplies accepted BOOTTIME to ServiceState
only for a worker with that token. ServiceState still installs clock metadata
only when the engine actually accepts the sample. Scheduler/process success
alone grants no bracket. Unsupported workers may continue to contribute accepted
ordinary observations and independent active membership. Their recency remains
unresolved; prior clocks cannot rebind to a new accepted counter/sample. A
canonical history sample still mirrors its exact original clock into the
runtime/history receipts. Superseded accepted-false samples retain the original
healthy receipt and clock.

The focused before probe uses the unchanged injected-worker completion path:
ordinary state is accepted, but the old code incorrectly exports a clock.
The final cases exercise that rejection, canonical runtime/history wiring,
replacement/subclass hooks, independent active selection, no borrowing of a
previous canonical clock and accepted-false rejection. Popen is mocked and
pipes are controlled; this is not native-provider or installed qualification.

[Client candidate](working-set-client-candidate.md) APIs, native frame/request
schemas and frozen R1/R2/R3 bytes are unchanged. The public SDK registration and
actual working-set Reader remain open. The separately pinned a7/c6 owner/read
cost measurements do not execute Runtime workers and keep their original source
provenance. This correction makes no performance, memory/RSS, transport or
producer acceptance claim, and changes no selected service or consumer route.
