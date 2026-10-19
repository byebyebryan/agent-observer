# Terminal Runtime callback retirement

A closed Runtime retained itself through four stored bound methods:
`worker_factory`, `_clock_factory`, `_sync_reserver` and
`_working_set_reserver`. Its terminal path cleared the matching ServiceState
reservations but kept these reverse references. With cyclic GC disabled,
dropping the last caller reference therefore left both Runtime and its state
reachable. Closed sockets and zero peers did not establish object retirement.

The correction preserves the existing shutdown order and reservation identity
checks. A final cleanup step drops only those four current values that are
Python bound methods whose owner is that Runtime. External injected factories,
sibling replacement reservations and caller-owned ServiceState outputs remain
untouched. This also runs if Endpoint startup or a later cleanup operation
raises. An existing cleanup exception still interrupts later cleanup operations;
this change does not claim to repair all such failure paths.

The [four regression methods](../tests/test_working_set_runtime_retirement.py)
use actual private Endpoint setup with collection disabled. They cover normal
shutdown and immediate weak-reference retirement, retained state/output buffers,
sibling and injected callable preservation, failed Endpoint startup, and a
selector-close exception. Cyclic GC remains disabled for the assertions and
no explicit collection is used. Overlaying these tests on immutable Observer
`196a8e2bd114f90aae82c4ee79559db511b9dce7` reproduces four failures on both
Python 3.14.8 and 3.11.17. The corrected source passes all four on both.

The initial isolated probe kept the caller's ServiceState alive after Runtime
retirement. Its exact active and working-set buffer objects remained owned by
that state, totaling 10,249 encoded bytes. This is expected live ownership,
not a zero-buffer claim. The correction establishes retirement of the tested
closed Runtime; it establishes neither a process RSS bound nor a steady-state
plateau.

The [owner resource packet](evidence/2026-10-18-working-set/final-owner-resource/README.md)
and earlier installed/transport reports remain pinned to source `196a8e2b`.
They are not reassigned to this correction. Live observation, native clock
capture, admission rules, deadlines, limits and selected services are unchanged.
The full [producer qualification](working-set-producer-checkpoint.md) remains
open, with deployment and consumer/device adoption separate.
