"""API v1: pure consumer validation and selection; no provider/action imports.

The acceptance record is separate from this interface's version declaration.
Observation wire 3 and write wire 1 are independently versioned documents.
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
from .write_contract import validate_plan, validate_request, validate_result
from .write_contract import schema_document as write_schema_document

API_VERSION = 1


def interface():
    return {
        "apiVersion": API_VERSION,
        "schemas": {"snapshot": 3, "watch": 3, "write": 1},
        "readCommands": ["snapshot", "list", "show", "watch", "schema"],
        "writeCommands": ["prepare", "execute", "enter", "schema"],
        "hostLocal": True,
        "nativeEventReplay": False,
    }


__all__ = [
    "API_VERSION", "ContractError", "WireError", "canonical", "identity_key",
    "interface", "parse_snapshot", "parse_watch", "schema_document",
    "store_namespace", "validate_snapshot", "validate_watch", "diagnostic",
    "listing", "ordered_rows", "select", "validate_plan", "validate_request",
    "validate_result", "write_schema_document",
]
