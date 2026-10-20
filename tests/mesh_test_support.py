"""Optional SDK tests use public capabilities, never version allowlists."""

import importlib.util
import unittest

WORKING_SET_PROFILE = "agent-observer.mesh-working-set.v1"


def require_working_set_sdk():
    """Skip discovery only when this optional SDK/profile is unavailable.

    Broken imports and unexpected descriptor errors remain failures. The
    required-pair check in scripts/check separately rejects an absent profile,
    so an integration gate cannot silently pass by skipping its tests.
    """
    if importlib.util.find_spec("mesh_plus") is None:
        raise unittest.SkipTest("optional Mesh SDK is not installed")

    from mesh_plus.api import descriptor
    from mesh_plus.protocol import ProtocolError

    try:
        descriptor("agent", profile_id=WORKING_SET_PROFILE)
    except ProtocolError as error:
        if error.code != "profile_descriptor":
            raise
        raise unittest.SkipTest("optional Mesh working-set profile is not registered") from None
    return True
