# Provider compatibility policy

Codex is the only implemented native observation adapter. Support follows the
required contracts and observed capabilities, not a provider version or
executable-hash allowlist. Current reads use the authenticated owning daemon,
including its saved metadata catalog; private saved-store fallback is removed.

## Required evidence

An adapter must establish exact native identity, namespace and source
incarnation, bounded discovery scope and coverage, authoritative runtime
predicates, independent work/activity clocks and explicit failure states.
Unsupported capabilities stay unknown or unsupported. A TUI, tmux session,
window, PID, path or file timestamp cannot substitute for a native predicate.

Version and executable metadata remain diagnostics, test provenance and
incarnation guards. A routine upgrade preserving required semantics does not
need release registration. A changed native contract, topology or capability
requires focused independent proof before changing the accepted interpretation.

## Extending support

Keep provider-neutral model, engine, read and Mesh interfaces. New adapters need
their own native capability and contract review; they need not copy Codex's
protocol or daemon layout. Prove passivity and failure behavior with isolated
resources, then separately qualify artifacts, managed selection and consumers.
See [validation](../maintenance/validation.md).

Claude observation is retired. Frozen provider vocabulary and historical
multi-provider fixtures do not imply native support. Ordinary Claude history,
settings and sessions remain outside Observer; Agent Plus's Claude TUI entry
is a separate product capability.
