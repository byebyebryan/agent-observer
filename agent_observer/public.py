"""API v2: pure consumer validation and selection; no provider/action imports.

The acceptance record is separate from this interface's version declaration.
Observation wire 4 is independent of the separately gated write client.
"""

from .bounded_json import WireError
from .contract import (
    ContractError,
    canonical,
    identity_key,
    parse_snapshot,
    parse_watch,
    schema_document,
    store_namespace,
    validate_snapshot,
    validate_watch,
)
from .read_client import diagnostic, listing, ordered_rows, select

API_VERSION = 2


def interface():
    return {
        "apiVersion": API_VERSION,
        "schemas": {"snapshot": 4, "watch": 4},
        "readCommands": ["snapshot", "list", "show", "watch", "schema"],
        "hostLocal": True,
        "nativeEventReplay": False,
    }


__all__ = [
    "API_VERSION", "ContractError", "WireError", "canonical", "identity_key",
    "interface", "parse_snapshot", "parse_watch", "schema_document",
    "store_namespace", "validate_snapshot", "validate_watch", "diagnostic",
    "listing", "ordered_rows", "select",
]
