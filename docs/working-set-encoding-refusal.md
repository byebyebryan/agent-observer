# Working-set encoding reservation refusal

A refused working-set staging reservation now returns the existing native
`error` frame with reason `projection_encoding_capacity` and no projection.
It does not encode a new unavailable projection after the reservation failed.
Any previously committed encoded buffer remains physically retained and counted
by Runtime, while the projector hides it from snapshot and delivery reads.

The earlier source allocated that replacement error buffer inside
`WorkingSetProjector.refuse_capacity`. The owning resource audit found that
there was no separate admission for those new bytes. This was an allocation
ordering defect; it was not a demonstrated default-limit or physical-memory
overrun. The [bounded regression](evidence/2026-10-18-working-set/encoding-refusal/README.md)
places the test-only Runtime limit at its already retained byte count. Without
an encoder hook, the previous source returns with 878 bytes against that
fixture's 562-byte limit on both Python versions. The corrected source retains
the original 562 bytes and returns no working-set material.

Refusal clears the positive presentation ledger and advances the projection's
failure continuity. It preserves the native clock ceiling, last-event guards
and source context. Repeated refusal does not replace the old buffer or keep
advancing the view revision when the clock state is unchanged. Unrelated
publication or expiry cannot retry the same refused accepted sample. A new
accepted sample/context may attempt a fresh reservation; only a committed
replacement clears the blocked state. Removing Runtime's reserver is not an
unbudgeted recovery path.

Healthy native observations remain accepted and current. Full and legacy-active
reads stay available. The working-set route does not fall back to either one.
Its standard error-frame behavior retires that delivery; recovery still needs
a new independently admitted baseline/proof through the normal client path.
The frame/request schemas, selector bytes, IDs and existing caps are unchanged.

The three owning methods run against the immutable previous source plus only
the final test-file overlay, then the final source export, on Python 3.14.8 and
3.11.17 with GC disabled. Before has three expected failed checks, including the
unhooked byte-counter failure; after has three passes. They cover first refusal,
old-buffer retention/accounting, provider and legacy-view health, guard/K
preservation, repeated refusal, existing native stream validation and reserved
recovery. They do not qualify aggregate heap/RSS, real maximum-bound traffic,
native provider behavior, transport or installed artifacts.

Luna implemented the native refusal slice. The primary reviewed it, added the
unhooked counter regression and integrated it with the independent
[client gap correction](working-set-client-gap.md). Existing accepted-a7
[cost measurements](evidence/2026-10-18-working-set/performance-source/README.md)
retain their original source tuple and scope. SDK registration, actual Reader,
inclusive resource/performance and native/installed-pair gates remain open.
