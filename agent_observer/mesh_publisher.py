"""Trusted lazy Agent factory for Mesh's cached publisher SDK interface 1."""

FULL_PROFILE_ID = "agent-observer.mesh-candidate.v3"


def make_publisher(host, source, socket, *, profile_id=FULL_PROFILE_ID):
    from mesh_plus.api import CachedPublisher
    from mesh_plus.protocol import check

    if profile_id == FULL_PROFILE_ID:
        from .mesh_profile import AgentProfile
        from .mesh_source import CachedAgentSource

        profile, native = AgentProfile(), CachedAgentSource(host, socket)
    else:
        from .mesh_active_profile import ACTIVE_PROFILE_ID, ActiveAgentProfile
        from .mesh_active_source import CachedActiveAgentSource

        check(profile_id == ACTIVE_PROFILE_ID, "profile_descriptor")
        profile, native = ActiveAgentProfile(), CachedActiveAgentSource(host, socket)
    return CachedPublisher("agent", host, source, native, profile=profile)


def main():
    from mesh_plus.cli import main as mesh_main

    return mesh_main(publisher_factories={"agent": make_publisher})


if __name__ == "__main__":
    raise SystemExit(main())
