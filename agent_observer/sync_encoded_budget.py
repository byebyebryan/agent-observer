"""Incremental canonical-buffer ownership using the shared heap identity index.

Configure one ledger per AllocationAccount before constructing encoded tables.
Canonical buffers count once per physical identity under the encoded cap and
the heap cap. Stages/leaves share encoded reference counters on a bytes-only
``_Held`` subclass; no second identity index or per-buffer claim is retained.
``preflight(delta)`` only checks capacity, before ``used`` grows.
"""

from __future__ import annotations

import sys
import traceback
from functools import wraps

from .sync_commitment import _SMALL_REFS, AllocationAccount, BudgetExceeded, CommitmentError, _Held

MAX_ENCODED_BYTES = 32 * 1024 * 1024
_WORKING = 16384


def _boundary(method):
    @wraps(method)
    def call(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except (ValueError, RecursionError):
            traceback.clear_frames(sys.exception().__traceback__)
            args = kwargs = None
            raise
    return call


def _ref_size(refs):
    return sys.getsizeof(refs) if refs > 256 else 0


class _EncodedBuffer(_Held):
    __slots__ = ("encoded_refs", "encoded_owner")


_ENCODED_OVERHEAD = sys.getsizeof(_EncodedBuffer(None, 0)) - sys.getsizeof(_Held(None, 0))


class EncodedOwnership:
    """Atomic unique-buffer batches, keyed through the account's own index.

    ``used`` sums len(buffer), ``count`` counts unique objects, and ``peak`` is
    their encoded high-water. A unique buffer adds one ordinary heap root ref;
    encoded stage/leaf refs share its two extra metadata slots. That slot delta
    and nonpooled encoded counters are paid by the ledger's bookkeeping lease.
    Scratch is prepaid once and grows only for unusually large argument batches.
    ``close`` requires no live claims. Different ledgers cannot claim the same
    live physical buffer; ordinary heap clients remain independent.
    """

    __slots__ = ("account", "preflight", "limit", "_used", "_peak", "_count",
                 "_extra_bytes", "_storage", "_working", "_closed")

    @_boundary
    def __init__(self, account, *, preflight=None, limit=MAX_ENCODED_BYTES):
        if not isinstance(account, AllocationAccount):
            raise CommitmentError("sync_allocation_account")
        if preflight is not None and not callable(preflight):
            raise CommitmentError("sync_encoded_preflight")
        if type(limit) is not int or not 1 <= limit <= MAX_ENCODED_BYTES:
            raise CommitmentError("sync_encoded_limit")
        self.account, self.preflight, self.limit = account, preflight, limit
        self._storage = self._working = None
        self._closed = False
        self._used = self._peak = self._count = self._extra_bytes = 0
        with account.reserve(_WORKING, kind="stage"):
            self._storage = account.reserve(512, kind="containers")
            self._working = account.reserve(_WORKING, kind="stage")

    @property
    def used(self):
        return self._used

    @property
    def count(self):
        return self._count

    @property
    def peak(self):
        return self._peak

    def _book_size(self):
        return 512 + self._extra_bytes

    def _prepare(self, buffers):
        if self._closed:
            raise CommitmentError("sync_encoded_ownership_closed")
        needed = _WORKING + 768 * len(buffers)
        if self._working._size < needed:
            self._working.resize(needed)
        plan = {}
        for buffer in buffers:
            if type(buffer) is not bytes:
                raise CommitmentError("sync_encoded_bytes_required")
            marker = id(buffer)
            if marker in plan:
                plan[marker][1] += 1
            else:
                plan[marker] = [buffer, 1]
        return plan

    def _fast_refs(self, buffers, direction):
        if self._closed or not 1 <= len(buffers) <= 2:
            return False
        held = self.account._held
        first = held.get(id(buffers[0]))
        if (type(buffers[0]) is not bytes or not isinstance(first, _EncodedBuffer)
                or first.encoded_owner is not self):
            return False
        second = None
        if len(buffers) == 2:
            if buffers[0] is buffers[1]:
                return False
            second = held.get(id(buffers[1]))
            if (type(buffers[1]) is not bytes or not isinstance(second, _EncodedBuffer)
                    or second.encoded_owner is not self):
                return False
        low, high = (1, 255) if direction == 1 else (2, 256)
        if (not low <= first.encoded_refs <= high
                or (second is not None and not low <= second.encoded_refs <= high)):
            return False
        first.encoded_refs = _SMALL_REFS[first.encoded_refs + direction]
        if second is not None:
            second.encoded_refs = _SMALL_REFS[second.encoded_refs + direction]
        return True

    @_boundary
    def retain(self, *buffers):
        with self.account._lock:
            if self._fast_refs(buffers, 1):
                return
            plan = self._prepare(buffers)
            fresh, changed = [], []
            delta = extra_delta = 0
            for marker, (buffer, refs) in plan.items():
                held = self.account._held.get(marker)
                if isinstance(held, _EncodedBuffer):
                    if held.encoded_owner is not self:
                        raise CommitmentError("sync_encoded_ownership_conflict")
                    previous_refs = held.encoded_refs
                else:
                    previous_refs = 0
                    fresh.append((marker, buffer))
                    delta += len(buffer)
                    extra_delta += _ENCODED_OVERHEAD
                next_refs = previous_refs + refs
                extra_delta += _ref_size(next_refs) - _ref_size(previous_refs)
                changed.append((marker, next_refs))
            held = None
            if self._used + delta > self.limit:
                raise BudgetExceeded("sync_encoded_limit")
            if delta and self.preflight is not None:
                self.preflight(delta)
            previous_size = self._storage._size
            self._storage.resize(self._book_size() + extra_delta)
            acquired = 0
            try:
                for marker, buffer in fresh:
                    self.account._acquire(0, "containers", {
                        marker: (buffer, sys.getsizeof(buffer), "value_bytes")})
                    acquired += 1
            except BaseException:
                for index in range(acquired):
                    self.account._drop(0, "containers", (fresh[index][0],))
                self._storage.resize(previous_size)
                raise
            for marker, refs in changed:
                held = self.account._held[marker]
                if not isinstance(held, _EncodedBuffer):
                    replacement = _EncodedBuffer(held.value, held.refs)
                    replacement.encoded_owner = self
                    self.account._held[marker] = held = replacement
                held.encoded_refs = _SMALL_REFS[refs] if refs <= 256 else refs
            self._extra_bytes += extra_delta
            self._count += len(fresh)
            self._used += delta
            self._peak = max(self._peak, self._used)

    def _drop_root(self, marker):
        # Restore exactly the generic size charged by AllocationAccount before
        # releasing its root. Other heap clients can keep the bytes alive.
        held = self.account._held[marker]
        self.account._held[marker] = _Held(held.value, held.refs)
        self.account._drop(0, "containers", (marker,))

    @_boundary
    def release(self, *buffers):
        with self.account._lock:
            if self._fast_refs(buffers, -1):
                return
            plan = self._prepare(buffers)
            changed, extra_delta = [], 0
            for marker, (_, refs) in plan.items():
                held = self.account._held.get(marker)
                if (not isinstance(held, _EncodedBuffer) or held.encoded_owner is not self
                        or refs > held.encoded_refs):
                    raise CommitmentError("sync_encoded_unclaimed_buffer")
                next_refs = held.encoded_refs - refs
                extra_delta += _ref_size(next_refs) - _ref_size(held.encoded_refs)
                if not next_refs:
                    extra_delta -= _ENCODED_OVERHEAD
                changed.append((marker, next_refs))
            held = None
            for marker, refs in changed:
                held = self.account._held[marker]
                if refs:
                    held.encoded_refs = _SMALL_REFS[refs] if refs <= 256 else refs
                else:
                    self._used -= len(held.value)
                    self._count -= 1
                    held = None
                    self._drop_root(marker)
            held = None
            self._extra_bytes += extra_delta
            self._storage.resize(self._book_size())

    def close(self):
        with self.account._lock:
            if self._closed:
                return
            if self._count:
                raise CommitmentError("sync_encoded_buffers_in_use")
            self._closed = True
            self._storage.release()
            self._working.release()

    def _release_leaf(self, *buffers):
        if self._closed:
            return
        if self._storage._released or self._working._released:
            self._force_close()
            return
        self.release(*buffers)

    def _force_close(self):
        if getattr(self, "_closed", True):
            return
        self._closed = True
        # One explicit teardown scan, no N-sized key list. After revocation
        # nobody may consume encoded counters, so reuse that existing slot as
        # an intrusive link until every ledger heap root has been dropped.
        head = None
        with self.account._lock:
            for shard in self.account._held._shards:
                for held in shard.values():
                    if isinstance(held, _EncodedBuffer) and held.encoded_owner is self:
                        held.encoded_refs = head
                        head = held
            held = None
            while head is not None:
                held, head = head, head.encoded_refs
                self._drop_root(id(held.value))
                held = None
            self._used = self._count = self._extra_bytes = 0
            if self._storage is not None:
                self._storage.release()
            if self._working is not None:
                self._working.release()

    def __del__(self):
        self._force_close()
