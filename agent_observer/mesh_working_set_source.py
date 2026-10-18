"""Explicit cached working-set acquisition, with no provider or Mesh import."""

from .contract import ContractError
from .mesh_source import CachedAgentSource
from .working_set_contract import StreamGuard, selector, selector_digest, validate_request
from .working_set_policy import DEFAULT_WINDOW_MS


class CachedWorkingSetAgentSource(CachedAgentSource):
    def __init__(self, host, path, *, window_ms=DEFAULT_WINDOW_MS, timeout=15.0):
        policy = selector(window_ms)
        self._policy_digest = selector_digest(policy)
        self._window_ms = window_ms
        self._clock_incarnation = None
        self._clock_watermark = (None, 0)
        super().__init__(host, path, timeout=timeout)

    @property
    def window_ms(self):
        return self._window_ms

    def _make_request(self, operation):
        # A new detached selector is exported; neither a request consumer nor
        # a newer owner can reinterpret this trusted startup policy.
        return validate_request(
            {
                "workingSetProtocol": 1,
                "operation": operation,
                "hostScope": self.host,
                "selector": selector(self._window_ms),
                "selectorDigest": self._policy_digest,
            },
            expected_window_ms=self._window_ms,
        )

    def _make_guard(self, uid):
        return StreamGuard(
            expected_host=self.host, expected_uid=uid, expected_window_ms=self._window_ms
        )

    def _admit(self, frame, *, history):
        # Separate socket operations may complete out of order. Reject a stale
        # clock ceiling even across streams: a lower K could extend unchanged
        # event authority. Commit this watermark only after base admission.
        incarnation = frame["serviceId"], frame["bootId"], frame["clockDomain"]
        ceiling, generation = frame["clockCeiling"], frame["clockGeneration"]
        if incarnation == self._clock_incarnation:
            prior_ceiling, prior_generation = self._clock_watermark
            if (
                prior_ceiling is not None
                and (ceiling is None or ceiling < prior_ceiling)
                or generation < prior_generation
            ):
                raise ContractError("working_set_acquisition_clock_regression")
        result = super()._admit(frame, history=history)
        self._clock_incarnation = incarnation
        self._clock_watermark = ceiling, generation
        return result
