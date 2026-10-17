"""Mesh-free structural relay codec; no material admission or authority.

The configured encoding ID is supplied by the trusted caller. This expanded
facade allocates no wire identifier and never guesses an encoding from bytes.
Raw inputs remain borrowed under their caller's pin. Header copies require the
caller's separate prepaid reservation for the advertised materialization bound.
"""

from __future__ import annotations

import copy
import threading
import weakref

from .contract import ContractError
from .sync_acquisition import _parse_header, _reserve, _retire_failure, parse_header
from .sync_commitment import descriptor_digest, freeze
from .sync_native import descriptor

_CONTROL_HEAP = 8192
_MINT = object()


class _DeferredLease:
    """Refund retired parser scratch only after its callback frames unwind."""

    def __init__(self, owner, reservation):
        self._owner = weakref.ref(owner)
        self._reservation = reservation
        self._retired = False

    def close(self):
        if self._retired:
            return
        self._retired = True
        owner = self._owner()
        if owner is None or owner.finished:
            self._release()

    def _release(self):
        reservation, self._reservation = self._reservation, None
        if reservation is not None:
            reservation.close()


class _CallBudget:
    def __init__(self, budget):
        self._budget, self._leases = budget, []
        self.finished = False

    def reserve(self, amount, *, encoded=0):
        if self.finished:
            raise ContractError("sync_ticket_closed")
        return self.adopt(self._budget.reserve(amount, encoded=encoded))

    def adopt(self, reservation):
        if not callable(getattr(reservation, "close", None)):
            raise ContractError("sync_ticket_budget")
        try:
            result = _DeferredLease(self, reservation)
            self._leases.append(result)
            return result
        except BaseException:
            reservation.close()
            raise

    def finish(self, failed=False):
        self.finished = True
        leases, self._leases = self._leases, []
        self._budget = None
        for lease in leases:
            if failed or lease._retired:
                lease._release()


def _copy_bound(document):
    # Includes complete detached lists/dicts/keys/scalars and deepcopy's memo
    # and walk scratch. Header size/depth/node limits have already been checked.
    def size(value):
        if type(value) is dict:
            return 512 + 128 * len(value) + sum(size(key) + size(child) for key, child in value.items())
        if type(value) is list:
            return 256 + 32 * len(value) + sum(size(child) for child in value)
        if type(value) is str:
            return 256 + 8 * len(value)
        return 128

    try:
        return 16384 + size(document)
    finally:
        # A recursive helper otherwise keeps its closure/call graph until GC.
        size = None


class HeaderRef:
    """Revocable bounded structural view, retaining no raw input or authority."""

    __slots__ = ("_ticket",)

    def __init__(self, ticket, *, _mint=None):
        if _mint is not _MINT:
            raise ContractError("sync_transport_ticket_owner")
        self._ticket = weakref.ref(ticket)

    def _live(self):
        ticket = self._ticket()
        if ticket is None:
            raise ContractError("sync_ticket_closed")
        return ticket

    @property
    def materialization_bytes(self):
        return self._live()._bound()

    def materialize(self):
        return self._live()._materialize()


class NativeTransportTicket:
    """Immediate revocation with physical header credit retained by active reads."""

    def __init__(self, projection, control, bound, *, _mint=None):
        if _mint is not _MINT:
            raise ContractError("sync_transport_ticket_owner")
        self._projection, self._control, self._copy_bytes = projection, control, bound
        self._lock = threading.RLock()
        self._closed, self._readers = False, 0
        self._header = HeaderRef(self, _mint=_MINT)

    @property
    def header(self):
        with self._lock:
            self._check()
            return self._header

    def _check(self):
        if self._closed:
            raise ContractError("sync_ticket_closed")

    def _bound(self):
        with self._lock:
            self._check()
            return self._copy_bytes

    def _materialize(self):
        projection = document = detached = None
        pinned = False
        try:
            with self._lock:
                self._check()
                self._readers += 1
                pinned = True
                projection = self._projection
            document = projection.document
            detached = copy.deepcopy(document)
            with self._lock:
                self._check()
            return detached
        except BaseException as error:
            # No refund may precede retirement of failed copy/decoder frames.
            _retire_failure(error)
            detached = document = projection = None
            raise error from None
        finally:
            detached = document = projection = None
            if pinned:
                with self._lock:
                    self._readers -= 1
                    if self._closed and not self._readers:
                        self._discard()

    def _discard(self):
        projection, control = self._projection, self._control
        self._projection = self._control = None
        if projection is not None:
            projection.close()
            projection = None
        if control is not None:
            control.close()

    def close(self):
        with self._lock:
            self._closed = True
            if not self._readers:
                self._discard()

    def __del__(self):
        if hasattr(self, "_lock"):
            self.close()


class AgentSyncTransportCodec:
    """Explicit expanded structural facade for one full or active native view."""

    __slots__ = ("_view", "_expected_host", "_encoding")

    def __setattr__(self, _name, _value):
        raise AttributeError("immutable transport codec")

    def __init__(self, view, *, encoding_id, expected_host=None):
        selected = descriptor(view)
        if (type(encoding_id) is not str or not encoding_id or len(encoding_id) > 128
                or not encoding_id.isascii() or any(ord(char) <= 32 for char in encoding_id)):
            raise ContractError("sync_transport_encoding")
        if expected_host is not None and (type(expected_host) is not str or not expected_host
                                          or len(expected_host) > 256):
            raise ContractError("sync_host_mismatch")
        object.__setattr__(self, "_view", view)
        object.__setattr__(self, "_expected_host", expected_host)
        object.__setattr__(self, "_encoding", freeze({
            "id": encoding_id, "schema": selected["schemaDigest"],
            "nativeDescriptor": descriptor_digest(selected),
        }))

    @property
    def encoding(self):
        return self._encoding

    def _scan(self, raw, budget, *, head):
        call = projection = control = result = None
        try:
            if not callable(getattr(budget, "reserve", None)):
                raise ContractError("sync_ticket_budget")
            control = _reserve(budget, _CONTROL_HEAP)
            call = _CallBudget(budget)
            control = call.adopt(control)
            if head:
                projection = _parse_header(raw, self._view, self._expected_host,
                                           budget=call, head_only=True)
            else:
                projection = parse_header(raw, self._view, self._expected_host, budget=call)
            result = NativeTransportTicket(projection, control, _copy_bound(projection.document),
                                           _mint=_MINT)
            projection = control = None
            call.finish()
            call = None
            return result
        except BaseException as error:
            if projection is not None:
                projection.close()
                projection = None
            if result is not None:
                result.close()
                result = None
            _retire_failure(error)
            raw = budget = None
            if call is not None:
                call.finish(failed=True)
                call = None
            if control is not None:
                control.close()
                control = None
            raise error from None

    def header(self, raw, budget):
        try:
            return self._scan(raw, budget, head=False)
        except BaseException as error:
            _retire_failure(error)
            self = raw = budget = None
            raise error from None

    def head(self, raw, budget):
        try:
            return self._scan(raw, budget, head=True)
        except BaseException as error:
            _retire_failure(error)
            self = raw = budget = None
            raise error from None
