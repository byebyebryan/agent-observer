"""Private Mesh-free compact material-plan primitive, currently unselected.

The caller pins and charges the original immutable frame through plan cleanup.
Only eight array offsets and bounded header/dictionary data survive open. A
trusted codec supplies per-value schema validation; no row is decoded at open.
Private row tickets require prepaid detached-copy credit exactly as headers do.
They are not generic normalization DTOs, admission handles or a public raw API.
"""

from __future__ import annotations

import threading
import weakref

from .contract import ContractError
from .sync_acquisition import SCAN_SCRATCH_BYTES, _decode, _heap_bound, _reserve, _retire_failure
from .sync_compact_acquisition import _CompactScanner, _parse_compact_header
from .sync_native import TABLES
from .sync_transport import (
    _CONTROL_HEAP,
    _MINT,
    NativeTransportTicket,
    _CallBudget,
    _copy_bound,
)

_COUNTS = dict.fromkeys(TABLES, 4096)
_COUNTS.update(memberships=36864, receipts=32, cohorts=32, scopes=65536, metadata=65536)


class _MaterialScanner(_CompactScanner):
    def __init__(self, raw):
        super().__init__(raw)
        self.arrays = {}
        self._outer = None

    def _table(self, group, key, depth, boundary):
        start, before = self.position, self.nodes
        self._outer = (start, _COUNTS[key] * (2 if group == "operations" else 1))
        try:
            super()._table(group, key, depth, boundary)
            self.arrays[key] = start, self.position, self.nodes - before
        finally:
            self._outer = None

    def _array(self, depth, boundary):
        if self._outer is None or self.position != self._outer[0]:
            return super()._array(depth, boundary)
        maximum = self._outer[1]
        self.position += 1
        self._skip(boundary)
        if self.position < self.end and self.raw[self.position] == 93:
            self.position += 1
            self._check(boundary)
            return
        count = 0
        while True:
            count += 1
            if count > maximum:
                self._error("sync_compact_table_capacity")
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


class _ValueProjection:
    def __init__(self, document, credit):
        self.document, self._credit = document, credit

    def close(self):
        self.document = None
        credit, self._credit = self._credit, None
        if credit is not None:
            credit.close()


class _ValueTicket:
    """Internal one-value loan; detached values remain caller-owned/charged."""

    def __init__(self, projection):
        self._ticket = NativeTransportTicket(projection, None, _copy_bound(projection.document), _mint=_MINT)
        self.closed = False

    @property
    def materialization_bytes(self):
        return self._ticket._bound()

    def materialize(self):
        return self._ticket._materialize()

    def close(self):
        self.closed = True
        self._ticket.close()


class _ValueIterator:
    def __init__(self, plan, space, span, credit, budget):
        self._plan = weakref.ref(plan)
        self._space, self._position, self._end = space, span[0] + 1, span[1]
        self._credit, self._current = credit, None
        self._budget = budget
        self._closed, self._busy, self._first = False, False, True
        self._lock = threading.RLock()

    def __iter__(self):
        return self

    def __next__(self):
        plan = raw = scanner = document = projection = credit = result = None
        pinned = entered = False
        try:
            with self._lock:
                if self._closed:
                    raise ContractError("sync_compact_iterator_closed")
                if self._busy or self._current is not None and not self._current.closed:
                    raise ContractError("sync_compact_value_live")
                self._current = None
                self._busy = True
                entered = True
            plan = self._plan()
            if plan is None:
                raise ContractError("sync_ticket_closed")
            with plan._lock:
                plan._check()
                plan._readers += 1
                pinned = True
                raw = plan._raw
            scanner = _CompactScanner(raw)
            scanner.position = self._position
            scanner._skip(self._end)
            if scanner.raw[scanner.position] == 93:
                self.close()
                raise StopIteration
            if not self._first:
                if scanner.raw[scanner.position] != 44:
                    raise ContractError("sync_ticket_json")
                scanner.position += 1
                scanner._skip(self._end)
            start = scanner.position
            scanner._value(3, self._end)
            span = start, scanner.position, scanner.nodes
            credit = _reserve(self._budget, _heap_bound(span[1] - span[0], span[2]) + _CONTROL_HEAP)
            document = _decode(raw, span)
            try:
                plan._validate(self._space, document, plan._kind == "transaction")
            except Exception as error:
                # A third-party schema error can carry the complete instance
                # in attributes as well as its traceback. Propagate only our
                # bounded code, never that payload-bearing exception object.
                _retire_failure(error)
                raise ContractError("sync_compact_value_shape") from None
            with plan._lock:
                plan._check()
                with self._lock:
                    if self._closed:
                        raise ContractError("sync_compact_iterator_closed")
                    projection = _ValueProjection(document, credit)
                    document = credit = None
                    result = _ValueTicket(projection)
                    projection = None
                    self._current = result
                    self._position, self._first = scanner.position, False
            return result
        except StopIteration:
            raise
        except BaseException as error:
            _retire_failure(error)
            document = raw = scanner = None
            if projection is not None:
                projection.close()
                projection = None
            if result is not None:
                result.close()
                result = None
            if credit is not None:
                credit.close()
                credit = None
            if entered:
                self.close()
            raise error from None
        finally:
            document = raw = scanner = projection = credit = result = None
            if pinned:
                with plan._lock:
                    plan._readers -= 1
                    if plan._closed and not plan._readers:
                        plan._discard()
            plan = None
            if entered:
                with self._lock:
                    self._busy = False
                    if self._closed:
                        self._release()

    def _release(self):
        credit, self._credit = self._credit, None
        self._budget = None
        if credit is not None:
            credit.close()

    def close(self):
        with self._lock:
            self._closed = True
            current, self._current = self._current, None
            if current is not None:
                current.close()
            if not self._busy:
                self._release()

    def __del__(self):
        if hasattr(self, "_lock"):
            self.close()


class _CompactMaterialPlan(NativeTransportTicket):
    def __init__(self, raw, projection, refs, arrays, control, validate, validator_owner=None):
        super().__init__(projection, control, _copy_bound(projection.document), _mint=_MINT)
        self._raw, self._refs, self._arrays = raw, refs, arrays
        self._kind = projection.document["kind"]
        self._validate, self._iterator = validate, None
        self._validator_owner = validator_owner

    def _values(self, space, budget):
        with self._lock:
            self._check()
            if space not in TABLES:
                raise ContractError("sync_compact_space")
            current = None if self._iterator is None else self._iterator()
            if current is not None and not current._closed:
                raise ContractError("sync_compact_iterator_live")
            credit = _reserve(budget, SCAN_SCRATCH_BYTES + _CONTROL_HEAP)
            try:
                result = _ValueIterator(self, space, self._arrays[space], credit, budget)
                self._iterator = weakref.ref(result)
                return result
            except BaseException:
                credit.close()
                raise

    def _discard(self):
        validator, self._validator_owner = self._validator_owner, None
        self._raw = self._refs = self._arrays = self._validate = None
        super()._discard()
        if validator is not None:
            validator.close()

    def close(self):
        with self._lock:
            self._closed = True
            iterator = None if self._iterator is None else self._iterator()
        if iterator is not None:
            iterator.close()
        with self._lock:
            if not self._readers:
                self._discard()


def _open_compact_plan(raw, view, budget, *, validate_value, expected_host=None, _validator_owner=None):
    """Internal parser construction; generic NativeCodec integration is separate.

    validate_value(space, decoded_value, is_operation) must fully validate the
    trusted local schema. It must not retain the borrowed value. Its configured
    schema/callback storage and detached copies are separately caller-charged.
    """
    call = projection = control = result = refs = arrays = None
    try:
        if not callable(validate_value) or not callable(getattr(budget, "reserve", None)):
            raise ContractError("sync_ticket_budget")
        control = _reserve(budget, _CONTROL_HEAP)
        call = _CallBudget(budget)
        control = call.adopt(control)
        projection, refs, arrays = _parse_compact_header(
            raw, view, expected_host, call, _scanner=_MaterialScanner, _plan=True)
        result = _CompactMaterialPlan(raw, projection, refs, arrays, control, validate_value, _validator_owner)
        projection = control = refs = arrays = None
        call.finish()
        call = None
        return result
    except BaseException as error:
        _retire_failure(error)
        raw = budget = validate_value = refs = arrays = _validator_owner = None
        if projection is not None:
            projection.close()
            projection = None
        if result is not None:
            result.close()
            result = None
        if call is not None:
            call.finish(failed=True)
            call = None
        if control is not None:
            control.close()
            control = None
        raise error from None
