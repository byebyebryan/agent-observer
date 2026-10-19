"""Bounded arithmetic model for per-scope FactSupport interning.

This is source-only synthetic evidence. It leaves the frozen API4 rows and
actual native working-set frames unchanged; the pooled scope grammar is only a
round-trip and byte-count model, not an admitted wire candidate.
"""

from __future__ import annotations

import argparse
import copy
import gc
import hashlib
import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

SOURCE_REVISION = "610afaac658903ddd6c466c793f9856b45e9f03e"
WINDOW_MS = 259_200_000
BOOT_ID = "00000000-0000-0000-0000-000000000001"
SCOPE_CAPTURE_LINE = 387


class ModelError(ValueError):
    """A malformed support-density model value."""


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _get_path(root: Any, path: tuple[str | int, ...]) -> Any:
    value = root
    for part in path:
        value = value[part]
    return value


def _set_path(root: Any, path: tuple[str | int, ...], value: Any) -> None:
    parent = root
    for part in path[:-1]:
        parent = parent[part]
    parent[path[-1]] = value


def _support_slots(scope: dict[str, Any]):
    """Yield only schema-typed FactSupport locations within one scope."""

    for index, support in enumerate(scope["coverage"]["supports"]):
        yield ("coverage", "supports", index), False, support
    for member_index, member in enumerate(scope["members"]):
        for field_name, support in member["fieldSupports"].items():
            yield ("members", member_index, "fieldSupports", field_name), True, support
        for branch_name in ("active", "recent"):
            branch = member[branch_name]
            if branch is None:
                continue
            for index, support in enumerate(branch["supports"]):
                yield ("members", member_index, branch_name, "supports", index), False, support
    for index, entry in enumerate(scope["uncertain"]):
        for field_name in ("priorSupport", "support"):
            yield ("uncertain", index, field_name), True, entry[field_name]
    for entry_index, entry in enumerate(scope["nonmembers"]):
        for support_index, support in enumerate(entry["supports"]):
            yield ("nonmembers", entry_index, "supports", support_index), False, support
        recent = entry["recent"]
        if recent is not None:
            yield ("nonmembers", entry_index, "recent", "support"), True, recent["support"]


def _support_stats(scope, canonical, validate_shape, fact_support_schema):
    occurrences = []
    for path, nullable, support in _support_slots(scope):
        if support is None:
            if not nullable:
                raise ModelError("null_required_support")
            continue
        if not isinstance(support, dict):
            raise ModelError("support_not_object")
        validate_shape(support, fact_support_schema)
        occurrences.append((path, support, canonical(support)))
    first_by_key = {}
    for _path, support, key in occurrences:
        first_by_key.setdefault(key, support)
    sorted_keys = sorted(first_by_key)
    occurrence_bytes = sum(len(key.encode("utf-8")) for _p, _s, key in occurrences)
    unique_bytes = sum(len(key.encode("utf-8")) for key in sorted_keys)
    return {
        "occurrenceCount": len(occurrences),
        "uniqueTupleCount": len(sorted_keys),
        "occurrenceCanonicalMapBytes": occurrence_bytes,
        "uniqueCanonicalMapBytes": unique_bytes,
        "duplicatedCanonicalMapBytes": occurrence_bytes - unique_bytes,
        "keys": sorted_keys,
        "supportByKey": first_by_key,
    }


def _pack_scope(scope, canonical, validate_shape, fact_support_schema):
    stats = _support_stats(scope, canonical, validate_shape, fact_support_schema)
    table = [copy.deepcopy(stats["supportByKey"][key]) for key in stats["keys"]]
    indexes = {key: index for index, key in enumerate(stats["keys"])}
    packed = copy.deepcopy(scope)
    for path, nullable, support in _support_slots(scope):
        if support is None:
            if not nullable:
                raise ModelError("null_required_support")
            continue
        if not isinstance(support, dict):
            raise ModelError("support_not_object")
        _set_path(packed, path, indexes[canonical(support)])
    return {"scope": packed, "supportTable": table}, stats


def _unpack_scope(model, canonical, validate_shape, fact_support_schema):
    if not isinstance(model, dict) or set(model) != {"scope", "supportTable"}:
        raise ModelError("model_shape")
    table = model["supportTable"]
    if not isinstance(table, list):
        raise ModelError("support_table_shape")
    keys = []
    for support in table:
        if not isinstance(support, dict):
            raise ModelError("support_table_entry")
        validate_shape(support, fact_support_schema)
        keys.append(canonical(support))
    if keys != sorted(keys):
        raise ModelError("support_table_order")
    if len(set(keys)) != len(keys):
        raise ModelError("support_table_duplicate")

    scope = copy.deepcopy(model["scope"])
    used = set()
    for path, nullable, reference in _support_slots(scope):
        if reference is None:
            if not nullable:
                raise ModelError("null_required_reference")
            continue
        if type(reference) is not int:
            # This also rejects bool and any attempted cross-scope pair/object.
            raise ModelError("support_reference_type")
        if not 0 <= reference < len(table):
            raise ModelError("support_reference_range")
        used.add(reference)
        _set_path(scope, path, copy.deepcopy(table[reference]))
    if used != set(range(len(table))):
        raise ModelError("support_table_unreferenced")
    return scope


def _first_reference_path(scope):
    return next(
        (path for path, _nullable, value in _support_slots(scope) if value is not None),
        None,
    )


def _expect_model_rejection(model, label, canonical, validate_shape, fact_support_schema):
    try:
        _unpack_scope(model, canonical, validate_shape, fact_support_schema)
    except ModelError:
        return {"name": label, "rejected": True}
    raise AssertionError(f"model_invalid_vector_accepted:{label}")


def _model_vectors(model, canonical, validate_shape, fact_support_schema):
    original_scope = model["scope"]
    reference_path = _first_reference_path(original_scope)
    if reference_path is None or not model["supportTable"]:
        raise AssertionError("support_model_has_no_reference")
    vectors = []

    malformed = copy.deepcopy(model)
    _set_path(malformed["scope"], reference_path, True)
    vectors.append(_expect_model_rejection(
        malformed, "bool_reference", canonical, validate_shape, fact_support_schema
    ))

    malformed = copy.deepcopy(model)
    _set_path(malformed["scope"], reference_path, len(malformed["supportTable"]))
    vectors.append(_expect_model_rejection(
        malformed, "out_of_range_reference", canonical, validate_shape, fact_support_schema
    ))

    malformed = copy.deepcopy(model)
    _set_path(malformed["scope"], reference_path, {"scopeIndex": 1, "supportIndex": 0})
    vectors.append(_expect_model_rejection(
        malformed, "cross_scope_reference_form", canonical, validate_shape, fact_support_schema
    ))

    malformed = copy.deepcopy(model)
    malformed["supportTable"].append(copy.deepcopy(malformed["supportTable"][0]))
    malformed["supportTable"].sort(key=canonical)
    vectors.append(_expect_model_rejection(
        malformed, "duplicate_table_entry", canonical, validate_shape, fact_support_schema
    ))

    unreferenced = copy.deepcopy(model["supportTable"][0])
    unreferenced["accepted"] += 1
    if canonical(unreferenced) in {canonical(item) for item in model["supportTable"]}:
        unreferenced["accepted"] += 1
    malformed = copy.deepcopy(model)
    malformed["supportTable"].append(unreferenced)
    malformed["supportTable"].sort(key=canonical)
    vectors.append(_expect_model_rejection(
        malformed, "unreferenced_table_entry", canonical, validate_shape, fact_support_schema
    ))

    alternate = copy.deepcopy(model["supportTable"][0])
    alternate["accepted"] += 1
    while canonical(alternate) in {canonical(item) for item in model["supportTable"]}:
        alternate["accepted"] += 1
    malformed = copy.deepcopy(model)
    malformed["supportTable"] = [model["supportTable"][0], alternate]
    malformed["supportTable"].sort(key=canonical, reverse=True)
    vectors.append(_expect_model_rejection(
        malformed, "noncanonical_table_order", canonical, validate_shape,
        fact_support_schema,
    ))
    return vectors


def _capture_partial_scope(root, canonical):
    captured = {}
    target_path = (root / "agent_observer" / "working_set_feed.py").resolve()

    def trace_local(frame, event, _arg):
        if event == "line" and frame.f_lineno == SCOPE_CAPTURE_LINE:
            local = frame.f_locals
            scope = local["scope"]
            stats = _support_stats(
                scope,
                canonical,
                lambda _value, _schema: None,
                None,
            )
            ledger_bytes = len(canonical(list(local["ledger"].values())).encode("utf-8"))
            captured.update({
                "guardBytes": local["self"].decisions.guard_bytes,
                "guardCount": local["self"].decisions.guard_count,
                "selectedCandidateScopeObjectBytes": len(canonical(scope).encode("utf-8")),
                "selectedCandidateScopeArrayBytes": len(canonical([scope]).encode("utf-8")),
                "selectedCandidateSupportOccurrences": stats["occurrenceCount"],
                "selectedCandidateUniqueSupportTuples": stats["uniqueTupleCount"],
                "selectedCandidateSupportDuplicateBytes": stats["duplicatedCanonicalMapBytes"],
                "partialMembers": len(scope["members"]),
                "partialUncertain": len(scope["uncertain"]),
                "partialNonmembers": len(scope["nonmembers"]),
                "partialBodies": len(local["bodies"]),
                "candidateRows": len(local["rows"]),
                "candidateTrackingBytesBeforeScopeCheck": local["tracking_bytes"],
                "candidateTrackingCapacityAlreadyExceeded": local["tracking_capacity"],
                "candidateTrackingStaticReserveBytes": 8192,
                "candidateTrackingGuardLedgerStaticBytes": (
                    local["self"].decisions.guard_bytes + ledger_bytes + 8192
                ),
                "candidateTrackingPerMemberMetadataAndEntryBytes": (
                    local["tracking_bytes"]
                    - local["self"].decisions.guard_bytes
                    - ledger_bytes
                    - 8192
                ),
                "candidateTrackingLimitOverByBytes": max(
                    0, local["tracking_bytes"] - local["self"].max_ledger_bytes
                ),
                "candidateLedgerEntries": len(local["ledger"]),
                "candidateLedgerCanonicalBytes": ledger_bytes,
                "candidateCombinedTrackingBytes": local["combined"],
                "candidateCombinedLimitHeadroomBytes": (
                    local["self"].max_ledger_bytes - local["combined"]
                ),
                "candidateCombinedLimitBytes": local["self"].max_ledger_bytes,
                "candidateCombinedFixedReserveBytes": 1024,
                "candidateTrackedIdentities": len(local["tracked"]),
                "candidateIdentityLimit": local["self"].max_identities,
            })
            sys.settrace(None)
            return None
        return trace_local

    def trace_calls(frame, event, _arg):
        if (
            event == "call"
            and frame.f_code.co_name == "_accept_owned"
            and Path(frame.f_code.co_filename).resolve() == target_path
        ):
            return trace_local
        return trace_calls

    return captured, trace_calls


def _case(seed_template, fixture, *, rows, selected_count, root, canonical,
          validate_snapshot, validate_shape, fact_support_schema, parse_full,
          parse_working, ServiceState, expected_uid, trace_refusal):
    seed, wall, _small, _fixture_expected_ids, _fixture_running_ids = fixture.build_workload(
        copy.deepcopy(seed_template), rows, canonical
    )
    if selected_count % 2:
        raise ValueError("selected_count_must_be_even")
    active_count = selected_count // 2
    for index, row in enumerate(seed["sessions"]):
        if index < active_count:
            row["runtime"]["value"] = "running"
            row["phase"] = copy.deepcopy(seed_template["sessions"][0]["phase"])
            row["blockedReasons"] = copy.deepcopy(seed_template["sessions"][0]["blockedReasons"])
        else:
            row["runtime"]["value"] = "parked"
            row["phase"], row["blockedReasons"] = None, []
        age = 3_600_000 if active_count <= index < selected_count else 864_000_000
        row["activity"]["at"] = wall - age
    seed["collectedAt"] = wall
    validate_snapshot(seed)
    accepted_input = canonical(seed).encode("utf-8")
    accepted_input_sha = _sha256(accepted_input)
    selected_ids = {
        row["identity"]["nativeId"]
        for index, row in enumerate(seed["sessions"])
        if index < selected_count
    }
    running_ids = {
        row["identity"]["nativeId"]
        for index, row in enumerate(seed["sessions"])
        if index < active_count
    }
    if len(selected_ids) != selected_count:
        raise AssertionError("fixture_selected_identity_count")

    clock_now = [10_001]
    state = ServiceState(
        host_scope="fixture",
        configs={"codex": ("/fixture/codex", "explicit")},
        uid=expected_uid,
        clock=lambda: clock_now[0],
        boot_id=BOOT_ID,
        clock_domain="time:[123]",
        working_set_window_ms=WINDOW_MS,
    )
    state.attempt("codex", "runtime")
    if trace_refusal:
        captured, tracer = _capture_partial_scope(root, canonical)
        sys.settrace(tracer)
        accepted = state.accept(
            "codex", "runtime", seed, sampled_ms=10_000, ttl_ms=100_000,
            accepted_boottime_ms=10_001,
        )
        sys.settrace(None)
        if not captured:
            raise AssertionError("refusal_local_capture_missing")
    else:
        captured = None
        accepted = state.accept(
            "codex", "runtime", seed, sampled_ms=10_000, ttl_ms=100_000,
            accepted_boottime_ms=10_001,
        )
    if not accepted:
        raise AssertionError("synthetic_snapshot_rejected")

    full = parse_full(
        (canonical(state.frame("status", 1)) + "\n").encode("utf-8"),
        expected_host="fixture", expected_uid=expected_uid,
    )
    working = parse_working(
        (canonical(state.working_set_frame("status", 1)) + "\n").encode("utf-8"),
        expected_host="fixture", expected_uid=expected_uid,
        expected_window_ms=WINDOW_MS,
    )
    independent_rows = fixture.full_consumer_rows(full["snapshot"])
    if len(independent_rows) != selected_count:
        raise AssertionError("independent_selection_count")
    selected_frame_rows = (
        [] if working["projection"] is None else working["projection"]["sessions"]
    )
    working_scope = None
    if working["projection"] is not None:
        working_scope = working["projection"]["scopes"][0]
    complete = (
        working_scope is not None
        and working_scope["coverage"]["status"] == "complete"
        and selected_frame_rows == independent_rows
    )
    refusal = working["kind"] == "error"
    if rows == 2_000 and selected_count == 100:
        if not refusal and not (
            working_scope is not None
            and working_scope["coverage"]["reason"] == "projection_tracking_capacity"
        ):
            raise AssertionError("large_selection_refusal_not_observed")
    elif not complete:
        raise AssertionError("expected_complete_small_support_model_case")

    result = {
        "rows": rows,
        "selectedRows": selected_count,
        "activeRows": active_count,
        "recentOnlyRows": selected_count - active_count,
        "accepted": True,
        "inputCanonicalBytes": len(accepted_input),
        "inputSha256": accepted_input_sha,
        "fullNativeFrameBytesWithLf": len((canonical(full) + "\n").encode("utf-8")),
        "fullOriginalRowArrayBytes": len(canonical(full["snapshot"]["sessions"]).encode("utf-8")),
        "independentlySelectedOriginalRowArrayBytes": len(
            canonical(independent_rows).encode("utf-8")
        ),
        "workingNativeFrameBytesWithLf": len((canonical(working) + "\n").encode("utf-8")),
        "returnedNativeScopeCanonicalBytes": (
            None if working_scope is None else len(canonical(working_scope).encode("utf-8"))
        ),
        "workingKind": working["kind"],
        "coverage": None if working_scope is None else working_scope["coverage"]["status"],
        "coverageReason": working.get("reason") if working_scope is None else working_scope["coverage"]["reason"],
        "completeExactDTOEquality": True if complete else None,
        "exactDTOEqualityChecked": complete,
        "expectedTrackingCapacityRefusal": rows == 2_000 and selected_count == 100,
        "activeIdentityCount": len(running_ids),
        "expectedSelectedIdentityCount": len(selected_ids),
        "actualSelectedIdentityCount": len({
            row["identity"]["nativeId"] for row in selected_frame_rows
        }),
        "projectionPresent": working["projection"] is not None,
        "actualFrameInputSha256": accepted_input_sha,
    }
    if complete:
        model, stats = _pack_scope(
            working_scope, canonical, validate_shape, fact_support_schema
        )
        restored = _unpack_scope(model, canonical, validate_shape, fact_support_schema)
        original_bytes = canonical(working_scope).encode("utf-8")
        restored_bytes = canonical(restored).encode("utf-8")
        if restored != working_scope or restored_bytes != original_bytes:
            raise AssertionError("support_model_roundtrip_not_exact")
        if [canonical(item) for item in model["supportTable"]] != stats["keys"]:
            raise AssertionError("support_model_table_not_complete_original_maps")
        model_bytes = canonical(model).encode("utf-8")
        model_case_frame = copy.deepcopy(working)
        model_case_frame["projection"]["scopes"] = [model]
        model_frame_bytes = len((canonical(model_case_frame) + "\n").encode("utf-8"))
        actual_guard = state.working_set_projector.decisions.guard_bytes
        actual_ledger_bytes = len(
            canonical(list(state.working_set_projector._ledger.values())).encode("utf-8")
        )
        scope_array_bytes = len(canonical([working_scope]).encode("utf-8"))
        model_scope_array_bytes = len(canonical([model]).encode("utf-8"))
        max_ledger = state.working_set_projector.max_ledger_bytes
        actual_combined = scope_array_bytes + actual_guard + actual_ledger_bytes + 1024
        modeled_combined = model_scope_array_bytes + actual_guard + actual_ledger_bytes + 1024
        if actual_combined > max_ledger:
            raise AssertionError("complete_scope_exceeds_current_combined_budget")
        vectors = _model_vectors(model, canonical, validate_shape, fact_support_schema)
        result["scope"] = {
            "originalCanonicalBytes": len(original_bytes),
            "supportOccurrenceCount": stats["occurrenceCount"],
            "uniqueSupportTupleCount": stats["uniqueTupleCount"],
            "supportOccurrenceCanonicalMapBytes": stats["occurrenceCanonicalMapBytes"],
            "uniqueSupportCanonicalMapBytes": stats["uniqueCanonicalMapBytes"],
            "duplicatedSupportCanonicalMapBytes": stats["duplicatedCanonicalMapBytes"],
            "supportTableEntryCanonicalMapBytes": sum(
                len(canonical(item).encode("utf-8")) for item in model["supportTable"]
            ),
            "supportTableCount": len(model["supportTable"]),
            "modeledCanonicalBytes": len(model_bytes),
            "modeledScopeArrayCanonicalBytes": model_scope_array_bytes,
            "scopeByteDelta": len(original_bytes) - len(model_bytes),
            "modeledWholeNativeFrameBytesWithLf": model_frame_bytes,
            "nativeFrameByteDelta": len((canonical(working) + "\n").encode("utf-8")) - model_frame_bytes,
            "roundTripObjectEqual": restored == working_scope,
            "roundTripCanonicalBytesEqual": restored_bytes == original_bytes,
            "tablePreservesEveryUniqueOriginalMap": True,
            "modelRejectVectors": vectors,
            "currentGuardBytes": actual_guard,
            "currentPriorLedgerCanonicalBytes": actual_ledger_bytes,
            "currentScopeArrayBytes": scope_array_bytes,
            "currentCombinedTrackingBytes": actual_combined,
            "modeledCombinedTrackingBytesArithmeticOnly": modeled_combined,
            "combinedTrackingLimitBytes": max_ledger,
            "modeledCombinedWithinLimitArithmeticOnly": modeled_combined <= max_ledger,
            "modelQualification": "arithmetic only; candidate grammar is not frozen or admitted",
        }
    if captured is not None:
        result["preFailureLocals"] = captured
        result["hypotheticalFullSelectedScope"] = {
            "constructed": False,
            "note": "No full 100-member scope was built inside the callback or inferred from its partial local candidate.",
        }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--seed", type=Path, required=True)
    parser.add_argument("--fixture-helper", type=Path, required=True)
    parser.add_argument("--exports", type=Path, required=True)
    parser.add_argument("--setup", type=Path, required=True)
    parser.add_argument("--python-entrypoint", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)

    gc.disable()
    root = args.root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(root)
    sys.path.insert(0, str(root))
    from agent_observer.active_contract import FACT_SUPPORT
    from agent_observer.contract import canonical, validate_shape, validate_snapshot
    from agent_observer.service_contract import parse_frame as parse_full
    from agent_observer.service_state import ServiceState
    from agent_observer.working_set_contract import parse_frame as parse_working

    spec = importlib.util.spec_from_file_location("support_density_fixture", args.fixture_helper)
    if spec is None or spec.loader is None:
        raise RuntimeError("fixture_helper_load_failed")
    fixture = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fixture)

    seed_bytes = args.seed.read_bytes()
    seed_template = json.loads(seed_bytes)
    export_data = json.loads(args.exports.read_text())
    setup_bytes = args.setup.read_bytes()
    setup_data = json.loads(setup_bytes)
    setup_version = setup_data.get("pythonVersion")
    if setup_version and not sys.version.startswith(setup_version):
        raise RuntimeError("interpreter_setup_version_mismatch")
    if export_data.get("candidate", {}).get("revision") != SOURCE_REVISION:
        raise RuntimeError("immutable_source_revision_mismatch")

    results = []
    cases = ((500, 50), (500, 100), (2_000, 100))
    for rows, selected_count in cases:
        results.append(_case(
            seed_template,
            fixture,
            rows=rows,
            selected_count=selected_count,
            root=root,
            canonical=canonical,
            validate_snapshot=validate_snapshot,
            validate_shape=validate_shape,
            fact_support_schema=FACT_SUPPORT,
            parse_full=parse_full,
            parse_working=parse_working,
            ServiceState=ServiceState,
            expected_uid=seed_template["host"]["uid"],
            trace_refusal=(rows, selected_count) == (2_000, 100),
        ))

    loaded = {}
    for name, module in tuple(sys.modules.items()):
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.is_relative_to(root) and path.suffix == ".py":
            loaded[name] = {
                "path": str(path.relative_to(root)),
                "sha256": _sha256(path.read_bytes()),
            }
    data = {
        "sourceRevision": SOURCE_REVISION,
        "sourceRoot": str(root),
        "sourceExportVerifiedFiles": export_data["candidate"].get("gitFilesVerified"),
        "scope": (
            "stdlib arithmetic representation model over strictly parsed synthetic source frames; "
            "not frozen-schema, admission, resource, CPU, heap, RSS or provider qualification"
        ),
        "pythonVersion": sys.version.split()[0],
        "pythonExecutable": sys.executable,
        "pythonEntrypoint": args.python_entrypoint,
        "gcEnabled": gc.isenabled(),
        "seedFileSha256": _sha256(seed_bytes),
        "fixtureHelperSha256": _sha256(args.fixture_helper.read_bytes()),
        "exportsSha256": _sha256(args.exports.read_bytes()),
        "interpreterSetupSha256": _sha256(setup_bytes),
        "runnerSha256": _sha256(Path(__file__).read_bytes()),
        "fixtureHelperPath": str(args.fixture_helper),
        "results": results,
        "loaded": dict(sorted(loaded.items())),
    }
    args.output.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(args.output), "cases": len(results)}, sort_keys=True))


if __name__ == "__main__":
    main()
