#!/usr/bin/env python3
"""Version-bound Mesh a25 launcher for Agent Observer a11 working-set.

This composes the published static Mesh publisher-factory hook with Observer's
installed a11 working-set factory. It is intentionally not a general Observer
API or a replacement for Mesh's normal launcher.
"""

from __future__ import annotations

import sys
from pathlib import Path

SOURCE_ID = "agent_working_set"
_HOSTING_COMMANDS = {"bridge", "serve"}


def make_working_set_publisher(host: str, source: str, socket: str):
    """Load the pinned Observer factory only when this exact source is selected."""
    from agent_observer.mesh_working_set_publisher import make_working_set_publisher as factory

    return factory(host, source, socket)


def _option_values(arguments: list[str], option: str) -> list[str | None]:
    values: list[str | None] = []
    index = 0
    while index < len(arguments):
        token = arguments[index]
        if token == option:
            if index + 1 < len(arguments) and not arguments[index + 1].startswith("-"):
                values.append(arguments[index + 1])
                index += 2
            else:
                values.append(None)
                index += 1
        elif token.startswith(option + "="):
            values.append(token[len(option) + 1 :])
            index += 1
        else:
            index += 1
    return values


def _abbreviated_values(arguments: list[str], option: str) -> list[str | None]:
    values: list[str | None] = []
    index = 0
    while index < len(arguments):
        token = arguments[index]
        spelling, separator, assigned = token.partition("=")
        if spelling.startswith("--") and option.startswith(spelling) and spelling != option:
            if separator:
                values.append(assigned)
                index += 1
            elif index + 1 < len(arguments) and not arguments[index + 1].startswith("-"):
                values.append(arguments[index + 1])
                index += 2
            else:
                values.append(None)
                index += 1
        else:
            index += 1
    return values


def _selected_config(arguments: list[str]) -> tuple[bool, Path | None]:
    """Resolve only the fully-spelled source/config flags used by Mesh a25."""
    if not arguments or arguments[0] not in _HOSTING_COMMANDS:
        return False, None

    options = arguments[1:]
    if SOURCE_ID in _abbreviated_values(options, "--source"):
        raise ValueError("unsupported_source_flag")
    sources = _option_values(options, "--source")
    if SOURCE_ID not in sources:
        return False, None
    if len(sources) != 1 or sources[0] != SOURCE_ID:
        raise ValueError("ambiguous_source_binding")

    if _abbreviated_values(options, "--config"):
        raise ValueError("unsupported_config_flag")
    configs = _option_values(options, "--config")
    if len(configs) > 1 or (configs and not configs[0]):
        raise ValueError("ambiguous_config_binding")
    if configs:
        return True, Path(configs[0])
    return True, Path(__file__).absolute().with_name("mesh-sources.toml")


def _mesh_main(*, publisher_factories=None):
    from mesh_plus.cli import main as mesh_main

    if publisher_factories is None:
        return mesh_main()
    return mesh_main(publisher_factories=publisher_factories)


def main(argv: list[str] | None = None) -> int:
    """Delegate Mesh commands, opting in only for the checked source binding."""
    original_argv = sys.argv
    supplied = argv is not None
    arguments = list(sys.argv[1:] if argv is None else argv)
    if supplied:
        sys.argv = [original_argv[0], *arguments]
    try:
        # Mesh authority dispatch must stay ahead of Observer imports and config.
        if arguments and arguments[0] == "mesh":
            return _mesh_main()

        try:
            selected, config = _selected_config(arguments)
        except ValueError as error:
            print(f"mesh-plus Observer launcher: {error}", file=sys.stderr)
            return 2
        if not selected:
            return _mesh_main()

        assert config is not None
        try:
            from mesh_plus.cli import configured_descriptor

            _host, domain, _socket = configured_descriptor(config, SOURCE_ID)
            if domain != "agent":
                raise ValueError("source_domain_mismatch")
        except Exception:
            # A bad selected descriptor must not silently reach Mesh's reference
            # adapter for the Observer source ID.
            print(
                "mesh-plus Observer launcher: agent_working_set requires a valid private agent source descriptor",
                file=sys.stderr,
            )
            return 2

        if not any(token == "--config" or token.startswith("--config=") for token in arguments[1:]):
            sys.argv[2:2] = ["--config", str(config)]
        return _mesh_main(publisher_factories={"agent": make_working_set_publisher})
    finally:
        if supplied:
            sys.argv = original_argv


if __name__ == "__main__":
    raise SystemExit(main())
