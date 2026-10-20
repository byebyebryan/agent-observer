"""Reproduce isolated installed a24 parity and ordinary IPC/fixed-SSH gates.

Run PREFIX/bin/python -I -B verify_installed.py --output PRIVATE_DIRECTORY
--mesh-wheel DOWNLOADED_WHEEL --observer-wheel LOCAL_CANDIDATE_WHEEL.
Only disposable collect=False state and the SDK-owned localhost SSH fixture are
used. No provider query, normal service change or package launcher overwrite.
"""

import argparse
import hashlib
import importlib.metadata
import json
import re
import subprocess
import sys
import sysconfig
import zipfile
from pathlib import Path, PurePosixPath


def invoke(command, output, name, *, expected=0):
    result = subprocess.run(command, capture_output=True, text=True, timeout=120)
    (output / f"{name}.stdout").write_text(result.stdout)
    (output / f"{name}.stderr").write_text(result.stderr)
    if result.returncode != expected:
        raise AssertionError(f"{name}: exit {result.returncode}; see {output}")
    return result.stdout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mesh-wheel", type=Path, required=True)
    parser.add_argument("--observer-wheel", type=Path, required=True)
    args = parser.parse_args()
    assert sys.flags.isolated
    root = Path(__file__).resolve().parents[3]
    prefix = Path(sys.prefix).resolve()
    output = args.output.resolve()
    output.mkdir(parents=True, mode=0o700, exist_ok=True)

    release = json.loads(invoke([
        sys.executable, "-I", "-B", str(root / "scripts/check-mesh-release"),
        "--prefix", str(prefix), "--manifest", str(root / "artifacts/mesh-0.1.0a24.json"),
        "--wheel", str(args.mesh_wheel),
    ], output, "release"))
    invoke([sys.executable, "-I", "-m", "pip", "check"], output, "pip-check")
    site = Path(sysconfig.get_path("purelib"))
    observer_distribution = importlib.metadata.distribution("agent-observer")
    observer_origin = json.loads(observer_distribution.read_text("direct_url.json") or "{}")
    assert "archive_info" in observer_origin and "dir_info" not in observer_origin
    observer_files = 0
    with zipfile.ZipFile(args.observer_wheel) as archive:
        for name in archive.namelist():
            path = PurePosixPath(name)
            assert not path.is_absolute() and ".." not in path.parts
            if name.endswith("/") or name.endswith(".dist-info/RECORD"):
                continue
            assert (site / name).read_bytes() == archive.read(name), name
            observer_files += 1

    owner = json.loads(invoke([
        sys.executable, "-I", "-B", str(root / "scripts/check-mesh-owner"), "--installed",
    ], output, "owner"))
    assert owner["status"] == "passed"
    invoke([
        sys.executable, "-I", "-B", "-m", "unittest", "discover",
        "-s", str(root / "tests"), "-p", "test_mesh_full_view_delivery.py", "-v",
    ], output, "selected-delivery")
    delivery_report = (output / "selected-delivery.stderr").read_text()
    assert re.search(r"Ran [1-9][0-9]* tests?", delivery_report)
    assert "\nOK\n" in delivery_report and "skipped" not in delivery_report

    # Keep the package-generated mesh-plus entrypoint byte-identical. The
    # explicit owner launcher supplies the trusted ordinary Python factory.
    original_launcher = (prefix / "bin/mesh-plus").read_bytes()
    launcher = prefix / "bin/observer-mesh-plus"
    launcher_body = (f"#!{prefix}/bin/python\nfrom agent_observer.mesh_publisher import main\n"
                     "raise SystemExit(main())\n")
    if launcher.exists():
        assert launcher.read_text() == launcher_body
    else:
        launcher.write_text(launcher_body)
        launcher.chmod(0o700)

    sys.path.insert(0, str(root / "tests"))
    from test_service_runtime import Running
    from test_working_set_registered_sdk import state_with_rows

    import agent_observer.service_runtime as runtime_module

    assert Path(runtime_module.__file__).is_relative_to(prefix)
    state, _sample = state_with_rows(window=60_000, count=3)
    with Running(state=state) as native:
        assert not native.runtime.collect and not native.runtime.experimental_sync
        publisher = json.loads(invoke([
            sys.executable, "-I", "-B", str(root / "scripts/check-mesh-publisher"),
            "--prefix", str(prefix), "--host-scope", "fixture",
            "--service-socket", str(native.path), "--ssh",
            "--publisher-launcher", str(launcher),
        ], output, "publisher"))
        assert publisher["status"] == "passed" and publisher["nativeChannelsAfterClose"] == 0
    assert not native.thread.is_alive()
    assert (prefix / "bin/mesh-plus").read_bytes() == original_launcher
    result = {
        "status": "passed", "python": sys.version.split()[0], "prefix": str(prefix),
        "meshWheelSha256": release["meshWheelSha256"],
        "observerWheelSha256": hashlib.sha256(args.observer_wheel.read_bytes()).hexdigest(),
        "observerInstalledFilesVerified": observer_files,
        "meshInstalledFilesVerified": release["installedWheelFilesVerified"],
        "ownerConformance": owner["status"],
        "carriers": [carrier["carrier"] for carrier in publisher["carriers"]],
        "installedRuntime": runtime_module.__file__, "nativeThreadRetired": True,
        "packageLauncherUnchanged": True, "semanticSyncSelected": False,
        "viewFeedSelected": False,
        "limits": ["synthetic accepted rows, collect=False", "localhost owned SSH fixture",
                   "no normal selected route/provider/fleet change", "no cost or capacity claim"],
    }
    (output / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
