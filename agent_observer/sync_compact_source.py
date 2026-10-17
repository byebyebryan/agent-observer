"""Explicit compact native acquisition through prepaid, unadmitted sessions.

This source never guesses an encoding or falls back to expanded material. Its
ordinary byte methods reject before I/O: compact material must use open_session
with the caller's public input owner and independently configured Reader codec.
No Mesh, observation engine, service or provider import belongs here.
"""

from .contract import ContractError
from .sync_acquisition import parse_header
from .sync_compact_acquisition import parse_compact_header
from .sync_contract import MAX_CHANGE_BYTES, MAX_TRANSACTIONS
from .sync_source import CachedAgentSyncSource


class CachedCompactAgentSyncSource(CachedAgentSyncSource):
    """A trusted constructor choice for one compact full or active endpoint.

    open_session/inspect/aclose and all owned session/result/control lifetimes
    match the expanded source. This allocates no schema or encoding identifier.
    """

    @staticmethod
    def _owned_header(raw, view, expected_host, *, budget, head=False):
        if head:
            # Original nonce-bound head/control framing has no compact material
            # dictionary or body-schema work, just as in the relay facade.
            return parse_header(raw, view, expected_host, budget=budget)
        return parse_compact_header(raw, view, expected_host, budget=budget)

    async def baseline(self):
        raise ContractError("sync_source_input_owner")

    async def head_after_nonce(self, challenge):
        raise ContractError("sync_source_input_owner")

    async def changes(self, base, *, target, max_transactions=MAX_TRANSACTIONS,
                      max_bytes=MAX_CHANGE_BYTES):
        raise ContractError("sync_source_input_owner")

    def watch(self, cursor):
        raise ContractError("sync_source_input_owner")
