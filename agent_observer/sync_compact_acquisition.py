"""Explicit compact structural headers; opaque rows remain unadmitted.

The caller pins/charges raw input. This acquisition-only projection validates
bounded root/dictionary/header framing, never alias resolution, field supports,
group masks, content, roots or native receipt-currentness. Reader normalization
must check every original byte independently. No codec or encoding is selected
from wire bytes or source names.
"""

from __future__ import annotations

import hashlib
from functools import lru_cache
from importlib.resources import files

from .contract import ContractError, validate_shape
from .sync_acquisition import (
    _FIELDS,
    _LIMITS,
    _ROOT_KEYS,
    SCAN_SCRATCH_BYTES,
    AcquisitionHeader,
    _decode,
    _heap_bound,
    _reserve,
    _retire_failure,
    _Scanner,
)
from .sync_commitment import freeze
from .sync_native import (
    MAX_CONTROL_BYTES,
    MAX_HEAD_BYTES,
    MAX_MESSAGE_BYTES,
    RECEIPT_KEY,
    TABLES,
    parse_message,
    validate_message,
)
from .sync_transport import AgentSyncTransportCodec

# 64 dictionary keys (32 per side), each three bounded ASCII components. This
# includes their fully Unicode-escaped spelling and bounded framing slack.
# It is an acquisition header capacity bound, not additional material authority.
MAX_RECEIPT_REF_BYTES = 40 * 1024


class _CompactScanner(_Scanner):
    _root_keys = _ROOT_KEYS | {"receiptRefs"}
    _limits = {**_LIMITS, "receiptRefs": MAX_RECEIPT_REF_BYTES}


@lru_cache(maxsize=1)
def schema_digest():
    raw = files("agent_observer").joinpath("contracts", "sync-compact-frame.schema.json").read_bytes()
    return hashlib.sha256(raw).hexdigest()


def _dictionary(value, *, baseline):
    if type(value) is not dict or set(value) != {"before", "after"}:
        raise ContractError("sync_compact_receipt_refs")
    for side in ("before", "after"):
        keys = value[side]
        if type(keys) is not list or len(keys) > 32 or baseline and side == "before" and keys:
            raise ContractError("sync_compact_receipt_refs")
        seen = set()
        for key in keys:
            if type(key) is not list or len(key) != 3:
                raise ContractError("sync_compact_receipt_key")
            for part, shape in zip(key, RECEIPT_KEY["prefixItems"], strict=True):
                validate_shape(part, shape)
            marker = tuple(key)
            if marker in seen:
                raise ContractError("sync_compact_receipt_key")
            seen.add(marker)


def _parse_compact_header(raw, view, expected_host, budget, *, _scanner=None, _plan=False):
    if type(raw) is not bytes or not raw or len(raw) > MAX_MESSAGE_BYTES:
        raise ContractError("sync_ticket_bytes")
    if (not raw.endswith(b"\n") or raw.find(b"\n", 0, len(raw) - 1) >= 0
            or raw.endswith(b"\r\n")):
        raise ContractError("sync_ticket_framing")
    if raw.startswith(b"\xef\xbb\xbf") or b"\0" in raw:
        raise ContractError("sync_ticket_utf8")
    scratch = _reserve(budget, SCAN_SCRATCH_BYTES)
    reservation = None
    try:
        scanner = (_CompactScanner if _scanner is None else _scanner)(raw)
        scanner.scan()
        if "kind" not in scanner.root:
            raise ContractError("sync_ticket_fields")
        kind = _decode(raw, scanner.root["kind"])
        expected = _FIELDS.get(kind) if type(kind) is str else None
        if type(kind) is str and kind in {"baseline", "transaction"}:
            expected = expected | {"receiptRefs"}
        actual = scanner.groups["root"]
        if (expected is None or kind != "control" and actual != expected
                or kind == "control" and not expected <= actual <= expected | {"baseTag", "targetTag"}):
            raise ContractError("sync_ticket_fields")
        if _plan and kind not in {"baseline", "transaction"}:
            raise ContractError("sync_compact_material_kind")
        if kind in {"head", "control"}:
            limit = MAX_HEAD_BYTES if kind == "head" else MAX_CONTROL_BYTES
            if len(raw) > limit:
                raise ContractError("sync_ticket_header_limit")
            reservation = _reserve(budget, _heap_bound(len(raw), scanner.nodes))
            document = parse_message(raw, view, expected_host)
        else:
            group = "tables" if kind == "baseline" else "operations"
            if scanner.groups.get(group) != frozenset(TABLES):
                raise ContractError("sync_ticket_fields")
            spans = list(scanner.root.values())
            if kind == "baseline":
                spans.append(scanner.receipts)
            reservation = _reserve(budget, _heap_bound(scanner.captured, sum(span[2] for span in spans)))
            document = {name: _decode(raw, span) for name, span in scanner.root.items()}
            refs = document.pop("receiptRefs")
            _dictionary(refs, baseline=kind == "baseline")
            # A public logical header exposes no positional dictionary. The
            # Reader's future input plan owns its own independently checked refs.
            if not _plan:
                refs = None
            document[group] = {name: [] for name in TABLES}
            if kind == "baseline":
                document[group]["receipts"] = _decode(raw, scanner.receipts)
            validate_message(document, view, expected_host)
        result = AcquisitionHeader(document, len(raw), scanner.nodes, reservation)
        reservation = None
        if _plan:
            return result, refs, scanner.arrays
        return result
    finally:
        if reservation is not None:
            reservation.close()
        scratch.close()


def parse_compact_header(raw, view, expected_host=None, *, budget):
    """Internal acquisition projection under an already prepaid call budget."""
    try:
        if not callable(getattr(budget, "reserve", None)):
            raise ContractError("sync_ticket_budget")
        return _parse_compact_header(raw, view, expected_host, budget)
    except BaseException as error:
        _retire_failure(error)
        raw = view = expected_host = budget = None
        raise error from None


class CompactAgentSyncTransportCodec(AgentSyncTransportCodec):
    """Unselected A1 structural facade for the candidate compact wire schema.

    A trusted caller must supply an explicit encoding ID. This class allocates
    no encoding identifier and implements no NativeCodec/admission callbacks.
    """

    __slots__ = ()

    def __init__(self, view, *, encoding_id, expected_host=None):
        super().__init__(view, encoding_id=encoding_id, expected_host=expected_host)
        object.__setattr__(self, "_encoding", freeze({**self.encoding, "schema": schema_digest()}))

    def _projection(self, raw, budget, *, head):
        if head:
            # Head/control bytes are unchanged. Never construct a compact
            # material plan, dictionary or material scanner on the nonce path.
            return super()._projection(raw, budget, head=True)
        return parse_compact_header(raw, self._view, self._expected_host, budget=budget)
