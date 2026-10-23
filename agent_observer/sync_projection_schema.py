"""Internal frozen schema bases for the default-off sync experiment.

These definitions advertise no standalone active-feed request or producer API.
"""

import copy
import hashlib

from .contract import array, canonical
from .projection_support import PROJECTION
from .service_contract import FRAME as SERVICE_FRAME
from .service_contract import SOURCE

ACTIVE_FEED_PROTOCOL = 1

SELECTOR = {
    "version": 1,
    "providers": ["codex"],
    "kinds": ["unknown", "user"],
    "runtimeValues": ["running"],
    "runtimeHealths": ["current"],
}

SELECTOR_DIGEST = "sha256:" + hashlib.sha256(canonical(SELECTOR).encode()).hexdigest()

SELECTOR_SCHEMA = {"const": copy.deepcopy(SELECTOR)}

FRAME = copy.deepcopy(SERVICE_FRAME)

FRAME["properties"].pop("serviceProtocol")

FRAME["properties"].pop("snapshot")

FRAME["properties"].update(
    activeFeedProtocol={"const": ACTIVE_FEED_PROTOCOL},
    selector=SELECTOR_SCHEMA,
    selectorDigest={"const": SELECTOR_DIGEST},
    projection={"anyOf": [PROJECTION, {"type": "null"}]},
    sources=array(SOURCE, 1),
)

FRAME["required"] = list(FRAME["properties"])
