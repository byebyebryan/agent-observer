# Working-set client gap correction

The candidate facade now revokes current material on a nonterminal delivery gap
without retiring that watch's clock, scope-continuity or reader-time watermarks.
The candidate still requires real SDK registration and independent Reader
admission. This correction adds no descriptor, schema, transport or generic SDK
capability.

Mesh found the issue in the immutable [client candidate](working-set-client-candidate.md)
at `c6a238fbe60ba9b4084734ef9302a9205fc99ca1`. The same affected source bytes
remain in `c4db1200279477c02679b41d8dc56bb11d080521`. Previously, both
`retain(None)` and `evaluate(None, now)` called the terminal reset operation.
The public diagnostic snapshot path also reset everything when no generation
was available. A later resync could therefore lose the already accepted K bound,
scope continuity and monotonic reader time. Individually valid native frames do
not prove continuity across replacements.

`_WorkingSetSelection.revoke()` drops the detached snapshot and row dictionary.
It preserves the bounded current host/provider bindings, native clock-incarnation
watermarks and last reader time. The no-generation read validates and advances
reader time before returning no claims. `clear()` remains the terminal reset used
by explicit disconnect; a subsequent watch still needs its own independent
baseline and proof. The facade uses only public SDK methods and continues to
call `current(now, clock)` before `context()`.

The [evidence directory](evidence/2026-10-18-working-set/client-gap/README.md)
preserves Mesh's original diagnostic and byte-identical result files separately
from the owning regressions. The unchanged first three owning methods reproduce
four failed checks on the immutable previous source on both Python versions.
The final five methods cover K regression, scope regression, reader-time
regression during and after a gap, repeated valid same-incarnation resync and
terminal state retirement. A valid resync cannot renew the expired positive or
infer a negative from its timeout.

This is bounded Observer policy evidence over strictly admitted synthetic native
frames and directly supplied translated receipt headers. It does not substitute
for the still-pending actual SDK guard, Reader proof, transport, resource, native
or installed-pair qualification. The independent
[worker-provenance correction](working-set-worker-provenance.md), accepted-a7
[source cost comparison](evidence/2026-10-18-working-set/performance-source/README.md)
and historical results retain their original source tuples.
