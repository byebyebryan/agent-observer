import gc
import hashlib
import json
import pathlib
import sys
import unittest

gc.disable()
root = pathlib.Path(sys.argv[1]).absolute()
mode = sys.argv[2]
sys.path.insert(0, str(root))
suite = unittest.defaultTestLoader.discover(
    str(root / "tests"), pattern="test_working_set_policy.py"
)
result = unittest.TextTestRunner(verbosity=2).run(suite)
failures = sorted(test.id().split(".")[-1] for test, _ in result.failures)
expected = (
    [
        "test_cutoff_out_of_range_with_valid_joined_inputs_is_unknown",
        "test_upper_cutoff_alone_out_of_range_invalidates_both_bounds",
    ]
    if mode == "before"
    else []
)
assert result.testsRun == 15 and failures == expected and not result.errors and not result.skipped
loaded = {}
for module in tuple(sys.modules.values()):
    filename = getattr(module, "__file__", None)
    if filename:
        path = pathlib.Path(filename).absolute()
        if path.suffix == ".py" and path.is_relative_to(root):
            loaded[str(path.relative_to(root))] = hashlib.sha256(path.read_bytes()).hexdigest()
print(
    json.dumps(
        {
            "python": sys.version.split()[0],
            "mode": mode,
            "tests": result.testsRun,
            "failures": failures,
            "errors": len(result.errors),
            "skips": len(result.skipped),
            "gcDisabled": not gc.isenabled(),
            "expectedOutcome": True,
            "loadedInputs": loaded,
        },
        sort_keys=True,
        indent=2,
    )
)
