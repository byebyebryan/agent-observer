"""Trusted lazy Agent factory for Mesh's cached publisher SDK interface 1."""


def make_publisher(host, source, socket):
    from mesh_plus.api import CachedPublisher

    from .mesh_profile import AgentProfile
    from .mesh_source import CachedAgentSource

    return CachedPublisher("agent", host, source, CachedAgentSource(host, socket), profile=AgentProfile())


def main():
    from mesh_plus.cli import main as mesh_main

    return mesh_main(publisher_factories={"agent": make_publisher})


if __name__ == "__main__":
    raise SystemExit(main())
