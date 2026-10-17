"""Pure synthetic native control byte-bound probe, not relay/resource proof."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from test_sync_acquisition import Budget, wire  # noqa: E402
from test_sync_native import control  # noqa: E402

from agent_observer.contract import ContractError  # noqa: E402
from agent_observer.sync_native import MAX_CONTROL_BYTES  # noqa: E402
from agent_observer.sync_transport import AgentSyncTransportCodec  # noqa: E402


def main():
    results = []
    for view in ("full", "active"):
        facade = AgentSyncTransportCodec(view, encoding_id="fixture-expanded/1", expected_host="fixture")
        original = wire(control(view))
        for method in ("header", "head"):
            for size in (MAX_CONTROL_BYTES, MAX_CONTROL_BYTES + 1, 65536):
                raw = original[:-2] + b" " * (size - len(original)) + b"}\n"
                assert len(raw) == size
                budget, ticket, code = Budget(), None, None
                try:
                    ticket = getattr(facade, method)(raw, budget)
                except ContractError as error:
                    code = error.args[0]
                else:
                    assert ticket.header.materialization_bytes > 0
                finally:
                    if ticket is not None:
                        ticket.close()
                assert budget.used == 0
                assert (code is None) == (size == MAX_CONTROL_BYTES)
                results.append({"view": view, "method": method, "rawBytes": size,
                                "acceptedStructuralHeader": code is None,
                                "code": code, "finalFixtureHeapCredit": budget.used})
    print(json.dumps({"result": "PASS", "nativeControlCap": MAX_CONTROL_BYTES,
                      "outerMeshControlCapFromR4": 65536, "cases": results,
                      "scope": "synthetic strict structural native byte boundary; raw input/test harness outside fixture credit, no Mesh relay/native provider/aggregate resource or material authority proof"},
                     sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
