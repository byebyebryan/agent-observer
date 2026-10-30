"""Private one-shot helper for bounded dashboard view-file operations."""

from __future__ import annotations

import sys
from pathlib import Path

# The parent invokes this fixed installed/source file with Python isolated mode.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from agent_observer.terminal.dashboard_view import (  # noqa: E402
    MAX_STATE_BYTES,
    SavedViewError,
    load_view_bytes,
    save_view_bytes,
)


def _write_error(code: str) -> int:
    sys.stdout.buffer.write(b"ERROR\n" + code.encode("ascii", "replace") + b"\n")
    sys.stdout.buffer.flush()
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] not in {"load", "save"}:
        return _write_error("saved_view_helper_failed")
    operation, root_arg = argv
    root = Path(root_arg)
    try:
        if operation == "load":
            payload = load_view_bytes(root)
            if payload is None:
                sys.stdout.buffer.write(b"MISSING\n")
            else:
                sys.stdout.buffer.write(b"OK\n" + payload)
            sys.stdout.buffer.flush()
            return 0

        payload = sys.stdin.buffer.read(MAX_STATE_BYTES + 1)
        if len(payload) > MAX_STATE_BYTES:
            return _write_error("saved_view_too_large")
        save_view_bytes(root, payload)
        sys.stdout.buffer.write(b"OK\n")
        sys.stdout.buffer.flush()
        return 0
    except SavedViewError as error:
        return _write_error(error.code)
    except Exception:
        return _write_error("saved_view_io_failed")


if __name__ == "__main__":
    raise SystemExit(main())
