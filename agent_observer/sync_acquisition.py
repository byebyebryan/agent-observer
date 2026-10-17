"""Bounded lexical acquisition headers for the expanded native sync shape.

These tickets confer no domain, commitment, receipt-currentness or proof
authority. The complete original input still needs independent Mesh admission.
Opaque tables/operations are scanned for JSON grammar, UTF-8, integer, depth
and node limits, but their entry shapes, duplicate object keys and domain keys
are deliberately deferred to that admission. Root/group keys and all decoded
header objects are closed and duplicate-checked here.

No Mesh import or full-body JSON decode occurs. The caller owns/charges the
immutable input buffer; this parser reserves only its own scratch and bounded
decoded projection. An injected budget implements reserve(amount, encoded=0)
and returns an idempotently closeable lease. The returned ticket owns its
decoded reservation until close; retaining detached application values remains
the caller's responsibility. The opt-in owned source separately prepays and
transfers its input buffer; neither ticket grants admission authority.
"""

from __future__ import annotations

import traceback
from dataclasses import dataclass, field

from .bounded_json import WireError, decode_document
from .contract import ContractError
from .sync_native import (
    MAX_CONTROL_BYTES,
    MAX_HEAD_BYTES,
    MAX_MESSAGE_BYTES,
    MAX_MESSAGE_DEPTH,
    MAX_MESSAGE_NODES,
    TABLES,
    parse_message,
    validate_message,
)

SCAN_SCRATCH_BYTES = 64 * 1024
MAX_HEADER_HEAP_BYTES = 64 * 1024 * 1024
MAX_CAPTURED_BYTES = 384 * 1024
MAX_BINDING_BYTES = 256 * 1024
MAX_RECEIPT_BYTES = 64 * 1024
MAX_KEY_BYTES = 256

_FIELDS = {
    "baseline": frozenset(("kind", "descriptor", "nativeBinding", "tag", "cursor", "tables")),
    "transaction": frozenset(
        (
            "kind",
            "descriptor",
            "nativeBindingDigest",
            "transactionId",
            "baseTag",
            "resultTag",
            "baseCursor",
            "resultCursor",
            "operations",
        )
    ),
    "head": frozenset(
        (
            "kind",
            "descriptor",
            "nativeBindingDigest",
            "tag",
            "challenge",
            "ownerClock",
            "originalReceipts",
            "cohortHeads",
            "attenuation",
        )
    ),
    "control": frozenset(("kind", "descriptor", "status", "reason", "tag", "cursor", "ownerClock")),
}
_LIMITS = {
    "kind": 32,
    "descriptor": 16 * 1024,
    "nativeBinding": MAX_BINDING_BYTES,
    "nativeBindingDigest": 512,
    "transactionId": 512,
    "tag": 512,
    "cursor": 512,
    "baseTag": 512,
    "resultTag": 512,
    "baseCursor": 512,
    "resultCursor": 512,
    "challenge": MAX_HEAD_BYTES,
    "ownerClock": MAX_HEAD_BYTES,
    "originalReceipts": MAX_HEAD_BYTES,
    "cohortHeads": MAX_HEAD_BYTES,
    "attenuation": MAX_HEAD_BYTES,
    "status": 256,
    "reason": 1024,
}
_ROOT_KEYS = frozenset().union(*_FIELDS.values(), ("baseTag", "targetTag"))
_LIMITS["targetTag"] = 512


class _Lease:
    def __init__(self, budget, amount):
        self.budget, self.amount, self.closed = budget, amount, False

    def close(self):
        if not self.closed:
            self.closed = True
            self.budget.used -= self.amount


class _Budget:
    def __init__(self):
        self.used = 0

    def reserve(self, amount, *, encoded=0):
        if encoded or self.used + amount > MAX_HEADER_HEAP_BYTES:
            raise ContractError("sync_ticket_heap_capacity")
        self.used += amount
        return _Lease(self, amount)


@dataclass(slots=True)
class AcquisitionHeader:
    """Small structural projection, never an admitted native/Mesh state.

    Baseline tables are empty except original receipts; transaction operations
    are all empty. The ticket retains neither raw input nor opaque byte spans.
    Call close (or use a context manager) after consuming the projection.
    """

    _document: dict | None = field(repr=False)
    scanned_bytes: int
    scanned_nodes: int
    _reservation: object = field(repr=False)

    @property
    def document(self):
        if self._document is None:
            raise ContractError("sync_ticket_closed")
        return self._document

    def close(self):
        self._document = None
        reservation, self._reservation = getattr(self, "_reservation", None), None
        if reservation is not None:
            reservation.close()

    def __enter__(self):
        if self._document is None:
            raise ContractError("sync_ticket_closed")
        return self

    def __exit__(self, *_args):
        self.close()

    def __del__(self):
        self.close()


class _Scanner:
    """One recursive grammar frame per bounded depth, no opaque key/value tree."""

    def __init__(self, raw):
        self.raw, self.end, self.position = raw, len(raw) - 1, 0
        self.nodes = 0
        self.root, self.groups = {}, {}
        self.receipts = None
        self.captured = 0

    def _error(self, code="sync_ticket_json"):
        raise ContractError(code)

    def _check(self, boundary):
        if boundary is not None and self.position > boundary:
            self._error("sync_ticket_header_limit")

    def _skip(self, boundary):
        while self.position < self.end and self.raw[self.position] in b" \t\r":
            self.position += 1
        self._check(boundary)

    def _node(self):
        self.nodes += 1
        if self.nodes > MAX_MESSAGE_NODES:
            self._error("sync_ticket_structure_limit")

    def _hex(self, position):
        if position + 4 > self.end:
            self._error()
        value = 0
        for index in range(position, position + 4):
            char = self.raw[index]
            digit = (
                char - 48
                if 48 <= char <= 57
                else char - 87
                if 97 <= char <= 102
                else char - 55
                if 65 <= char <= 70
                else -1
            )
            if digit < 0:
                self._error()
            value = value * 16 + digit
        return value

    def _string(self, boundary):
        self.position += 1
        while self.position < self.end:
            char = self.raw[self.position]
            if char == 34:
                self.position += 1
                self._check(boundary)
                return
            if char < 32:
                self._error()
            if char == 92:
                self.position += 1
                if self.position >= self.end:
                    self._error()
                escape = self.raw[self.position]
                if escape == 117:
                    value = self._hex(self.position + 1)
                    self.position += 5
                    if 0xD800 <= value <= 0xDBFF:
                        if (
                            not self.raw.startswith(b"\\u", self.position)
                            or not 0xDC00 <= self._hex(self.position + 2) <= 0xDFFF
                        ):
                            self._error("sync_ticket_unicode")
                        self.position += 6
                    elif 0xDC00 <= value <= 0xDFFF:
                        self._error("sync_ticket_unicode")
                elif escape in b'"\\/bfnrt':
                    self.position += 1
                else:
                    self._error()
            elif char < 128:
                self.position += 1
            else:
                if 0xC2 <= char <= 0xDF:
                    width, low, high = 2, 0x80, 0xBF
                elif 0xE0 <= char <= 0xEF:
                    width, low, high = (
                        3,
                        0xA0 if char == 0xE0 else 0x80,
                        0x9F if char == 0xED else 0xBF,
                    )
                elif 0xF0 <= char <= 0xF4:
                    width, low, high = (
                        4,
                        0x90 if char == 0xF0 else 0x80,
                        0x8F if char == 0xF4 else 0xBF,
                    )
                else:
                    self._error("sync_ticket_utf8")
                if (
                    self.position + width > self.end
                    or not low <= self.raw[self.position + 1] <= high
                ):
                    self._error("sync_ticket_utf8")
                for index in range(self.position + 2, self.position + width):
                    if not 0x80 <= self.raw[index] <= 0xBF:
                        self._error("sync_ticket_utf8")
                self.position += width
            self._check(boundary)
        self._error()

    def _number(self, boundary):
        start = self.position
        if self.raw[self.position] == 45:
            self.position += 1
        digits = self.position
        if self.position >= self.end or not 48 <= self.raw[self.position] <= 57:
            self._error()
        if self.raw[self.position] == 48:
            self.position += 1
        else:
            while self.position < self.end and 48 <= self.raw[self.position] <= 57:
                self.position += 1
                if self.position - digits > 20:
                    self._error("sync_ticket_integer")
        self._check(boundary)
        if self.position < self.end and self.raw[self.position] in b".eE0123456789":
            self._error("sync_ticket_integer")
        number = int(self.raw[start : self.position])
        if not -(2**63) <= number <= 2**64 - 1:
            self._error("sync_ticket_integer")

    def _value(self, depth, boundary=None, group=None):
        if depth > MAX_MESSAGE_DEPTH:
            self._error("sync_ticket_structure_limit")
        self._node()
        self._skip(boundary)
        if self.position >= self.end:
            self._error()
        char = self.raw[self.position]
        if group is not None and char != 123:
            self._error("sync_ticket_group_shape")
        if char == 123:
            self._object(depth, boundary, group)
        elif char == 91:
            self._array(depth, boundary)
        elif char == 34:
            self._string(boundary)
        elif char == 45 or 48 <= char <= 57:
            self._number(boundary)
        else:
            for literal in (b"true", b"false", b"null"):
                if self.raw.startswith(literal, self.position):
                    self.position += len(literal)
                    self._check(boundary)
                    return
            self._error()

    def _array(self, depth, boundary):
        self.position += 1
        self._skip(boundary)
        if self.position < self.end and self.raw[self.position] == 93:
            self.position += 1
            self._check(boundary)
            return
        while True:
            self._value(depth + 1, boundary)
            self._skip(boundary)
            if self.position >= self.end:
                self._error()
            char = self.raw[self.position]
            self.position += 1
            if char == 93:
                self._check(boundary)
                return
            if char != 44:
                self._error()

    def _capture(self, target, key, start, before):
        size = self.position - start
        self.captured += size
        if self.captured > MAX_CAPTURED_BYTES:
            self._error("sync_ticket_header_limit")
        target[key] = start, self.position, self.nodes - before

    def _object(self, depth, boundary, group):
        fields = {} if group is not None else None
        self.position += 1
        self._skip(boundary)
        if self.position < self.end and self.raw[self.position] == 125:
            self.position += 1
        else:
            while True:
                if self.position >= self.end or self.raw[self.position] != 34:
                    self._error()
                self._node()  # object keys count toward the native node limit
                start = self.position
                self._string(
                    min(start + MAX_KEY_BYTES, boundary)
                    if boundary is not None and group is not None
                    else start + MAX_KEY_BYTES
                    if group is not None
                    else boundary
                )
                key = None
                if group is not None:
                    key = _decode(self.raw, (start, self.position, 1))
                    allowed = _ROOT_KEYS if group == "root" else TABLES
                    if key not in allowed or key in fields:
                        self._error("sync_ticket_fields")
                    fields[key] = None
                self._skip(boundary)
                if self.position >= self.end or self.raw[self.position] != 58:
                    self._error()
                self.position += 1
                self._skip(boundary)
                start, before = self.position, self.nodes
                if group == "root":
                    if key in {"tables", "operations"}:
                        self._value(depth + 1, boundary, group=key)
                    else:
                        self._value(depth + 1, start + _LIMITS[key])
                        self._capture(self.root, key, start, before)
                elif group in {"tables", "operations"}:
                    if self.position >= self.end or self.raw[self.position] != 91:
                        self._error("sync_ticket_table_shape")
                    if group == "tables" and key == "receipts":
                        self._value(depth + 1, start + MAX_RECEIPT_BYTES)
                        holder = {}
                        self._capture(holder, "receipts", start, before)
                        self.receipts = holder["receipts"]
                    else:
                        self._value(depth + 1, boundary)
                else:
                    self._value(depth + 1, boundary)
                self._skip(boundary)
                if self.position >= self.end:
                    self._error()
                char = self.raw[self.position]
                self.position += 1
                if char == 125:
                    break
                if char != 44:
                    self._error()
                self._skip(boundary)
        self._check(boundary)
        if group is not None:
            self.groups[group] = frozenset(fields)

    def scan(self):
        self._value(0, group="root")
        self._skip(None)
        if self.position != self.end:
            self._error()


def _decode(raw, span):
    start, end, nodes = span
    try:
        return decode_document(
            raw[start:end], max_bytes=end - start, max_depth=MAX_MESSAGE_DEPTH, max_nodes=nodes
        )
    except WireError:
        raise ContractError("sync_ticket_header_json") from None


def _heap_bound(size, nodes):
    # Prepay parsed lists/dicts/keys/scalars and duplicate-pair scratch, the
    # validator's walks and frozen canonical copy, plus UTF-8/encoding buffers.
    # These conservative charges apply only to bounded captured headers.
    return 16384 + 16 * size + 512 * nodes


def _reserve(budget, amount):
    reservation = budget.reserve(amount, encoded=0)
    if not callable(getattr(reservation, "close", None)):
        raise ContractError("sync_ticket_budget")
    return reservation


def _parse_header(raw, view, expected_host=None, *, budget=None):
    """Scan one expanded newline frame and return its bounded header ticket.

    Header byte caps are acquisition capacity limits, not new native schemas.
    The supplied input is borrowed; no input-buffer reservation is minted here.
    Source endpoint/UID/local-clock/order guards remain the acquiring client's
    responsibility. This function performs the native structural binding checks.
    """
    if type(raw) is not bytes or not raw or len(raw) > MAX_MESSAGE_BYTES:
        raise ContractError("sync_ticket_bytes")
    if not raw.endswith(b"\n") or raw.find(b"\n", 0, len(raw) - 1) >= 0 or raw.endswith(b"\r\n"):
        raise ContractError("sync_ticket_framing")
    if raw.startswith(b"\xef\xbb\xbf") or b"\0" in raw:
        raise ContractError("sync_ticket_utf8")
    budget = _Budget() if budget is None else budget
    if not callable(getattr(budget, "reserve", None)):
        raise ContractError("sync_ticket_budget")
    scratch = _reserve(budget, SCAN_SCRATCH_BYTES)
    reservation = None
    try:
        scanner = _Scanner(raw)
        scanner.scan()
        if "kind" not in scanner.root:
            raise ContractError("sync_ticket_fields")
        kind = _decode(raw, scanner.root["kind"])
        expected = _FIELDS.get(kind) if type(kind) is str else None
        actual = scanner.groups["root"]
        if (
            expected is None
            or (kind != "control" and actual != expected)
            or (kind == "control" and not expected <= actual <= expected | {"baseTag", "targetTag"})
        ):
            raise ContractError("sync_ticket_fields")
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
            reservation = _reserve(
                budget, _heap_bound(scanner.captured, sum(span[2] for span in spans))
            )
            document = {name: _decode(raw, span) for name, span in scanner.root.items()}
            document[group] = {name: [] for name in TABLES}
            if kind == "baseline":
                document["tables"]["receipts"] = _decode(raw, scanner.receipts)
            validate_message(document, view, expected_host)
        result = AcquisitionHeader(document, len(raw), scanner.nodes, reservation)
        reservation = None
        return result
    finally:
        if reservation is not None:
            reservation.close()
        scratch.close()


def _retire_failure(error):
    # Suppressed decoder contexts can also retain their input fragments and
    # intermediate maps. Clear unwound frames throughout the chain before
    # detaching it, rather than relying on a future cyclic-GC pass.
    pending, seen = [error], set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        pending.extend(
            item for item in (current.__context__, current.__cause__) if item is not None
        )
        traceback.clear_frames(current.__traceback__)
        current.__traceback__ = current.__context__ = current.__cause__ = None


def parse_header(raw, view, expected_host=None, *, budget=None):
    """Return an acquisition-only header, with bounded decoded ownership.

    The borrowed input remains the caller's responsibility. Expected native,
    decoder and capacity errors keep their type/code, but not construction
    traces or argument references that could outlive their retired credits.
    """
    try:
        return _parse_header(raw, view, expected_host, budget=budget)
    except (ValueError, RecursionError) as error:
        # The private implementation has completed its reservation finally
        # blocks. This boundary frame stays in the new traceback, so clear its
        # own arguments as well as all already-unwound construction frames.
        _retire_failure(error)
        raw = view = expected_host = budget = None
        raise error from None
