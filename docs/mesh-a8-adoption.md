# Mesh a8 transport adoption

The reviewed Mesh 0.1.0a8 artifact adds proactive channel rotation and redacted
transport counters while preserving the frozen Agent state profile. Its exact
inputs are in [the manifest](../artifacts/mesh-0.1.0a8.json).

Adoption uses new immutable reader and bridge prefixes containing the existing
Observer a13 and a12 wheels, respectively, plus Mesh a8. The collector stays on
accepted a15; the writer stays independently selected on a16. No provider
settings, collection cadence or native public contracts change.

The archived verifier accepts exactly one reviewed a4 or a8 Mesh manifest,
checks installed wheel bytes and dependencies, and proves pure imports without
collection or provider invocation. Old roots and archived verifiers remain
rollback inputs. Source a15 is not promoted as the read CLI by this change.

Operational and recovery acceptance is recorded separately after scoped
selection on Snap and Starship. Metrics do not establish native provider truth,
GUI behavior, physical suspend or lossless event replay.

Mesh a9 follows a8 with owned-IO cancellation refinement. It uses new `-mesh-a9`
roots with the same Observer wheels, profiles, collector and writer selections.
The verifier independently admits the reviewed a9 manifest and rejects unknown
versions or multiple Mesh manifests before invoking archived verification.
