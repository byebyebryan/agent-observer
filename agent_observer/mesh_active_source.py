"""Owned cached active-feed acquisition; no native provider reads or Mesh import."""

import copy

from .active_contract import (
    ACTIVE_FEED_PROTOCOL,
    SELECTOR,
    SELECTOR_DIGEST,
    StreamGuard,
    validate_request,
)
from .mesh_source import CachedAgentSource


class CachedActiveAgentSource(CachedAgentSource):
    """The existing checked socket lifetime with a distinct fixed wire family."""

    def _make_request(self, operation):
        return validate_request({
            "activeFeedProtocol": ACTIVE_FEED_PROTOCOL,
            "operation": operation, "hostScope": self.host,
            "selector": copy.deepcopy(SELECTOR), "selectorDigest": SELECTOR_DIGEST,
        })

    def _make_guard(self, uid):
        return StreamGuard(expected_host=self.host, expected_uid=uid)
