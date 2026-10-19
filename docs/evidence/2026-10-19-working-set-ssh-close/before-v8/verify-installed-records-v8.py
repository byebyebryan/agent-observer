from __future__ import annotations

import base64
import csv
import hashlib
import json
import os
import sys
import sysconfig
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parent
PACKAGE_ROOT = ROOT.parent
SPECS = {
    "agent_observer": ("agent_observer-0.7.0a7-py3-none-any.whl", "agent_observer-0.7.0a7.dist-info"),
    "mesh_plus": ("mesh_plus-0.1.0a23-py3-none-any.whl", "mesh_plus-0.1.0a23.dist-info"),
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fail(code: str) -> None:
    raise RuntimeError(code)


def parse_record(data: bytes) -> list[list[str]]:
    return list(csv.reader(data.decode("utf-8").splitlines()))


def validate_record_rows(rows: list[list[str]], available, *, installed_root: Path | None = None, allowed_root: Path | None = None, dist_name: str) -> dict:
    seen: set[str] = set()
    checked = 0
    unhashed = []
    for row in rows:
        if len(row) != 3:
            fail("record_row_shape")
        name, hash_value, size_value = row
        relative = PurePosixPath(name)
        if not name or relative.is_absolute() or (installed_root is None and ".." in relative.parts) or name in seen:
            fail("record_path_invalid_or_duplicate")
        seen.add(name)
        if installed_root is None:
            if name not in available:
                fail("wheel_record_target_missing")
            data = available[name]
        else:
            target = (installed_root / name).resolve(strict=True)
            try:
                target.relative_to((allowed_root or ROOT).resolve())
            except ValueError:
                fail("installed_record_path_escape")
            if not target.is_file():
                fail("installed_record_target_missing")
            data = target.read_bytes()
        if not hash_value and not size_value:
            if name != f"{dist_name}/RECORD" and not (name.endswith(".pyc") and "/__pycache__/" in name):
                fail("unexpected_unhashed_record_entry")
            unhashed.append(name)
            continue
        if not hash_value.startswith("sha256=") or not size_value.isascii() or not size_value.isdecimal():
            fail("record_hash_or_size_shape")
        actual = base64.urlsafe_b64encode(hashlib.sha256(data).digest()).decode("ascii").rstrip("=")
        if actual != hash_value.removeprefix("sha256=") or len(data) != int(size_value):
            fail("record_hash_or_size_mismatch")
        checked += 1
    return {"recordEntries": len(rows), "sha256EntriesVerified": checked, "unhashedAllowedEntries": len(unhashed),
            "unhashedRecordSelf": f"{dist_name}/RECORD" in unhashed, "allUnhashedEntriesAreInstalledBytecodeOrRecord": True}


def main() -> None:
    slot = "venv-314" if sys.version_info[:2] == (3, 14) else "venv-311" if sys.version_info[:2] == (3, 11) else None
    if slot is None:
        fail("unsupported_interpreter")
    venv = PACKAGE_ROOT / slot
    if Path(sys.executable).absolute() != venv / "bin" / "python" or Path(sys.prefix).resolve() != venv.resolve():
        fail("candidate_venv_identity_mismatch")
    purelib = Path(sysconfig.get_paths()["purelib"]).resolve()
    try:
        purelib.relative_to(venv.resolve())
    except ValueError:
        fail("candidate_site_packages_mismatch")
    packages = {}
    for package, (wheel_name, dist_name) in SPECS.items():
        wheel = ROOT / "wheels" / wheel_name
        wheel_records = []
        with zipfile.ZipFile(wheel) as archive:
            names = [name for name in archive.namelist() if not name.endswith("/")]
            records = [name for name in names if name.endswith(".dist-info/RECORD")]
            if len(records) != 1:
                fail("wheel_record_shape")
            rows = parse_record(archive.read(records[0]))
            wheel_data = {name: archive.read(name) for name in names}
            wheel_records.append(validate_record_rows(rows, wheel_data, dist_name=dist_name))
            recorded_names = {row[0] for row in rows}
            if recorded_names != set(names):
                fail("wheel_record_inventory_mismatch")
        installed_dist = purelib / dist_name
        if not installed_dist.is_dir():
            fail("installed_distribution_missing")
        installed_rows = parse_record((installed_dist / "RECORD").read_bytes())
        installed_result = validate_record_rows(installed_rows, None, installed_root=purelib, allowed_root=venv, dist_name=dist_name)
        packages[package] = {"wheelRecord": wheel_records[0], "installedRecord": installed_result}
    report = {"schema": "agent-observer.installed-wheel-records.v1", "status": "pass",
              "pythonVersion": ".".join(map(str, sys.version_info[:3])), "lexicalInterpreter": str(sys.executable),
              "privateVenvPrefixExact": True, "packages": packages}
    target = ROOT / ("installed-records-v8-" + str(sys.version_info.major) + str(sys.version_info.minor) + ".json")
    fd = os.open(target, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write((json.dumps(report, sort_keys=True, indent=2) + "\n").encode())
        handle.flush()
    print(json.dumps({"status": "pass", "packages": sorted(packages), "report": str(target)}, sort_keys=True))


if __name__ == "__main__":
    try:
        main()
    except RuntimeError as exc:
        code = str(exc) if str(exc).replace("_", "").isalnum() and len(str(exc)) <= 96 else "record_verification_failed"
        print(json.dumps({"status": "failed", "reasonCode": code}, sort_keys=True))
        raise SystemExit(1)
