"""Prerelease local-service facade and pure read-consumer utility."""

from .bounded_json import WireError
from .contract import ContractError, canonical
from .read_cache import ReadCache
from .service_contract import (
    SERVICE_PROTOCOL,
    StreamGuard,
    interface,
    parse_frame,
    parse_request,
    schema_document,
    validate_frame,
    validate_request,
)

__all__ = [
    "SERVICE_PROTOCOL", "ContractError", "WireError", "canonical", "StreamGuard",
    "interface", "parse_frame", "parse_request", "schema_document",
    "validate_frame", "validate_request",
    "ReadCache",
]
