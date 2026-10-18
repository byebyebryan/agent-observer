"""Trusted explicit working-set factory; no default-route or import-time I/O."""

from .working_set_policy import DEFAULT_WINDOW_MS


def make_working_set_publisher(host, source, socket, *, window_ms=DEFAULT_WINDOW_MS):
    from mesh_plus.api import CachedPublisher

    from .mesh_working_set_profile import WorkingSetAgentProfile
    from .mesh_working_set_source import CachedWorkingSetAgentSource

    # Resolve the exact public descriptor before allocating the native source.
    # An SDK without this candidate refuses; it cannot fall back to full/active.
    profile = WorkingSetAgentProfile(window_ms)
    native = CachedWorkingSetAgentSource(host, socket, window_ms=window_ms)
    return CachedPublisher("agent", host, source, native, profile=profile)
