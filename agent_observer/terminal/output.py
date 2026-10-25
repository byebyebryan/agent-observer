"""Finite terminal output helpers and packaged schema access."""

from __future__ import annotations

import json
import os
import select
import time
from importlib.resources import files


class OutputError(OSError):
    pass


def schema_document() -> dict:
    """Load the packaged terminal v1 schema without importing Mesh."""
    raw = files("agent_observer").joinpath("contracts/terminal-v1.schema.json").read_bytes()
    return json.loads(raw)


def json_document(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def write_stdout(value: str, *, timeout: float = 5.0) -> None:
    """Write one bounded document with a finite nonblocking backpressure wait."""
    data = (value.rstrip("\n") + "\n").encode("utf-8")
    try:
        fd = os.dup(1)
    except OSError as error:
        raise OutputError("stdout_unavailable") from error
    blocking = None
    deadline = time.monotonic() + timeout
    try:
        blocking = os.get_blocking(fd)
        os.set_blocking(fd, False)
        while data:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise OutputError("stdout_timeout")
            if not select.select([], [fd], [], remaining)[1]:
                raise OutputError("stdout_timeout")
            try:
                written = os.write(fd, data)
            except BlockingIOError:
                continue
            if written <= 0:
                raise OutputError("stdout_unavailable")
            data = data[written:]
    except BrokenPipeError as error:
        raise OutputError("broken_pipe") from error
    except OutputError:
        raise
    except OSError as error:
        raise OutputError("stdout_unavailable") from error
    except ValueError as error:
        raise OutputError("stdout_unavailable") from error
    finally:
        if blocking is not None:
            try:
                os.set_blocking(fd, blocking)
            except OSError:
                pass
        os.close(fd)


def write_stderr(message: str) -> None:
    try:
        os.write(2, (message.rstrip("\n") + "\n").encode("utf-8", errors="backslashreplace"))
    except OSError:
        pass
