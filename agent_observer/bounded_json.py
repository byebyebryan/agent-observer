"""Bounded JSON decoding for study transports; errors never echo payloads."""

from __future__ import annotations

import json


class WireError(ValueError):
    """Finite, content-free transport failure code."""


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise WireError("duplicate_key")
        result[key] = value
    return result


def _constant(_value):
    raise WireError("nonfinite_number")


def _integer(value):
    if len(value.lstrip("-")) > 20:
        raise WireError("integer_limit")
    number = int(value)
    if not -(2**63) <= number <= 2**64 - 1:
        raise WireError("integer_limit")
    return number


def decode_document(
    data: bytes,
    *,
    max_bytes: int = 8 * 1024 * 1024,
    max_depth: int = 32,
    max_nodes: int = 100000,
    line_framed: bool = False,
):
    """Decode in memory only. Consumers still select an explicit field allowlist."""
    if (
        not isinstance(data, bytes)
        or isinstance(max_bytes, bool)
        or not isinstance(max_bytes, int)
        or max_bytes < 1
        or isinstance(max_depth, bool)
        or not isinstance(max_depth, int)
        or not 1 <= max_depth <= 128
        or isinstance(max_nodes, bool)
        or not isinstance(max_nodes, int)
        or max_nodes < 1
    ):
        raise WireError("invalid_limit")
    if len(data) > max_bytes:
        raise WireError("byte_limit")
    if data.startswith(b"\xef\xbb\xbf") or b"\x00" in data:
        raise WireError("invalid_encoding")
    if line_framed and (not data.endswith(b"\n") or b"\n" in data[:-1] or data.endswith(b"\r\n")):
        raise WireError("invalid_framing")
    try:
        value = json.loads(
            data.decode("utf-8", "strict"),
            object_pairs_hook=_pairs,
            parse_constant=_constant,
            parse_int=_integer,
        )
    except WireError:
        raise
    except (UnicodeError, ValueError, RecursionError, OverflowError):
        raise WireError("invalid_json") from None
    stack = [(value, 0)]
    seen = 0
    while stack:
        node, depth = stack.pop()
        seen += 1
        if seen > max_nodes:
            raise WireError("node_limit")
        if depth > max_depth:
            raise WireError("depth_limit")
        if isinstance(node, dict):
            stack.extend((item, depth + 1) for item in node.values())
            seen += len(node)
        elif isinstance(node, list):
            stack.extend((item, depth + 1) for item in node)
        elif isinstance(node, float):
            import math

            if not math.isfinite(node):
                raise WireError("nonfinite_number")
        if seen > max_nodes:
            raise WireError("node_limit")
    return value
