"""Separate prerelease service facade. API v1 public symbols remain unchanged."""

from .bounded_json import WireError
from .contract import ContractError, canonical
from .service_contract import (
    SERVICE_PROTOCOL, StreamGuard, interface, parse_frame, parse_request,
    schema_document, validate_frame, validate_request,
)

__all__ = [
    "SERVICE_PROTOCOL", "ContractError", "WireError", "canonical", "StreamGuard",
    "interface", "parse_frame", "parse_request", "schema_document",
    "validate_frame", "validate_request",
]
