"""Emit and validate the CF0 historical/current state index."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"
ROOT = Path(__file__).resolve().parents[1]
CF0 = Path("generated/cf0-python-cli-calculator")
DOCS_CF0 = Path("docs/examples/cf0-python-cli-calculator")


class StateIndexError(Exception):
    """Raised when the CF0 historical index cannot be emitted safely."""


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise StateIndexError(f"{path} must contain a JSON object")
    return data


def canonical_json(data: Any) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def digest_json_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(canonical_json(read_json(path)).encode('utf-8')).hexdigest()}"


def digest_bytes_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def artifact(path: str, role: str | None = None) -> dict[str, Any]:
    absolute = ROOT / path
    if not absolute.exists():
        raise StateIndexError(f"referenced artifact does not exist: {path}")
    is_json = absolute.suffix.lower() == ".json"
    record: dict[str, Any] = {
        "path": path,
        "sha256": digest_json_file(absolute) if is_json else digest_bytes_file(absolute),
        "digestMode": "canonical-json" if is_json else "file-bytes",
    }
    if role is not None:
        record["role"] = role
    return record


def fact_ids(code_facts_path: str) -> set[str]:
    facts = read_json(ROOT / code_facts_path).get("facts", [])
    return {
        fact["id"]
        for fact in facts
        if isinstance(fact, dict) and isinstance(fact.get("id"), str)
    }


def overlay_unit_fact_ids(overlay_path: str, unit_id: str) -> set[str]:
    overlay = read_json(ROOT / overlay_path)
    for unit in overlay.get("intentUnits", []):
        if isinstance(unit, dict) and unit.get("id") == unit_id:
            return {
                ref["factId"]
                for ref in unit.get("codeFactRefs", [])
                if isinstance(ref, dict) and isinstance(ref.get("factId"), str)
            }
    return set()


def build_index() -> dict[str, Any]:
    p13_before_source = (CF0 / "p1.3-before-source/calc.py").as_posix()
    p13_before_facts = (CF0 / "p1.3-before-code-facts.json").as_posix()
    p13_before_overlay = (CF0 / "p1.3-before-overlay.json").as_posix()
    p13_after_source = (CF0 / "p1.3-after-source/calc.py").as_posix()
    p13_after_facts = (CF0 / "p1.3-after-code-facts.json").as_posix()
    p13_after_overlay = (CF0 / "p1.3-after-overlay.json").as_posix()
    p17_after_source = (CF0 / "p1.9-before-source/calc.py").as_posix()
    p17_after_facts = (CF0 / "p1.9-before-code-facts.json").as_posix()
    p17_after_overlay = (CF0 / "p1.9-before-overlay.json").as_posix()
    current_source = (DOCS_CF0 / "source/calc.py").as_posix()
    current_facts = (CF0 / "code-facts.json").as_posix()
    current_overlay = (DOCS_CF0 / "intentgraph.overlay.json").as_posix()

    states = [
        {
            "id": "cf0.state.p1.3.before-add-mul",
            "kind": "historical",
            "description": "CF0 before the add-mul maintenance delta.",
            "source": artifact(p13_before_source, "hand-written-historical-copy"),
            "codeFacts": artifact(p13_before_facts),
            "overlay": artifact(p13_before_overlay),
        },
        {
            "id": "cf0.state.p1.3.after-add-mul",
            "kind": "historical",
            "description": "CF0 after add-mul and before the implementation refactor.",
            "source": artifact(p13_after_source, "hand-written-historical-copy"),
            "codeFacts": artifact(p13_after_facts),
            "overlay": artifact(p13_after_overlay),
        },
        {
            "id": "cf0.state.p1.7.after-refactor-multiply",
            "kind": "historical",
            "description": "CF0 after preserving unit.behavior.mul while refactoring its implementation to multiply, before P1.9 overlay-only contract coverage.",
            "source": artifact(p17_after_source, "hand-written-historical-copy"),
            "codeFacts": artifact(p17_after_facts),
            "overlay": artifact(p17_after_overlay),
        },
        {
            "id": "cf0.state.p1.9.current-overlay-unsupported-operation",
            "kind": "current",
            "description": "CF0 current state after adding overlay-only unsupported-operation contract coverage without source behavior changes.",
            "source": artifact(current_source, "hand-written-current"),
            "codeFacts": artifact(current_facts),
            "overlay": artifact(current_overlay),
        },
    ]
    transitions = [
        {
            "id": "cf0.transition.p1.3.add-mul",
            "fromStateId": "cf0.state.p1.3.before-add-mul",
            "toStateId": "cf0.state.p1.3.after-add-mul",
            "delta": artifact((DOCS_CF0 / "deltas/p1.3-add-mul.delta.json").as_posix()),
            "verificationReport": {
                **artifact((CF0 / "p1.3-maintenance-delta-report.json").as_posix()),
                "historical": True,
            },
        },
        {
            "id": "cf0.transition.p1.7.refactor-mul-to-multiply",
            "fromStateId": "cf0.state.p1.3.after-add-mul",
            "toStateId": "cf0.state.p1.7.after-refactor-multiply",
            "delta": artifact((DOCS_CF0 / "deltas/p1.7-refactor-mul-to-multiply.delta.json").as_posix()),
            "verificationReport": {
                **artifact((CF0 / "p1.7-refactor-delta-report.json").as_posix()),
                "historical": True,
            },
        },
        {
            "id": "cf0.transition.p1.9.overlay-unsupported-operation",
            "fromStateId": "cf0.state.p1.7.after-refactor-multiply",
            "toStateId": "cf0.state.p1.9.current-overlay-unsupported-operation",
            "delta": artifact((DOCS_CF0 / "deltas/p1.9-overlay-unsupported-operation.delta.json").as_posix()),
            "verificationReport": {
                **artifact((CF0 / "p1.9-overlay-contract-delta-report.json").as_posix()),
                "historical": False,
            },
        },
    ]
    index = {
        "artifactRole": "intentgraph-cf0-historical-state-index",
        "status": "generated",
        "reportVersion": REPORT_VERSION,
        "scope": "cf0-code-first-overlay-history-index",
        "currentStateId": "cf0.state.p1.9.current-overlay-unsupported-operation",
        "states": states,
        "transitions": transitions,
        "invariants": {
            "sourceTextEqualityRequired": False,
            "hiddenGeneratedCodeSnapshotUsed": False,
            "currentArtifactsMayChangeInFuture": True,
            "historicalArtifactsMustBeStable": True,
            "cf0SpecificIndexOnly": True,
            "generalHistoryEngineClaimed": False,
        },
        "checks": [],
        "errors": [],
    }
    validate_index(index)
    index["status"] = "pass"
    index["checks"] = [
        "all referenced paths exist",
        "artifact digests emitted with sha256 prefix",
        "state ids and transition ids are unique",
        "currentStateId resolves to the single current state",
        "historical states avoid mutable current source/facts/overlay artifacts",
        "P1.3 after-state contains old mul implementation facts",
        "P1.7 current state contains multiply facts and not old mul implementation facts",
        "P1.7 transition preserves unit.behavior.mul while remapping facts",
        "P1.9 current state contains unsupported-operation overlay contract coverage",
    ]
    return index


def validate_index(index: dict[str, Any]) -> None:
    states = index.get("states", [])
    transitions = index.get("transitions", [])
    state_ids = [state.get("id") for state in states]
    transition_ids = [transition.get("id") for transition in transitions]
    if len(state_ids) != len(set(state_ids)):
        raise StateIndexError("state ids must be unique")
    if len(transition_ids) != len(set(transition_ids)):
        raise StateIndexError("transition ids must be unique")
    state_by_id = {state["id"]: state for state in states}
    current_states = [state for state in states if state.get("kind") == "current"]
    if len(current_states) != 1:
        raise StateIndexError("exactly one state must be marked current")
    if index.get("currentStateId") not in state_by_id:
        raise StateIndexError("currentStateId must reference an existing state")
    if state_by_id[index["currentStateId"]].get("kind") != "current":
        raise StateIndexError("currentStateId must reference the current state")

    mutable_paths = {
        (DOCS_CF0 / "source/calc.py").as_posix(),
        (CF0 / "code-facts.json").as_posix(),
        (DOCS_CF0 / "intentgraph.overlay.json").as_posix(),
    }
    for state in states:
        for key in ("source", "codeFacts", "overlay"):
            value = state.get(key, {})
            path = value.get("path")
            digest = value.get("sha256")
            if not path or not isinstance(path, str):
                raise StateIndexError(f"{state.get('id')} missing {key} path")
            if not isinstance(digest, str) or not digest.startswith("sha256:"):
                raise StateIndexError(f"{state.get('id')} missing {key} sha256 digest")
            if state.get("kind") == "historical" and path in mutable_paths:
                raise StateIndexError(f"historical state {state.get('id')} points to mutable current artifact {path}")

    for transition in transitions:
        if transition.get("fromStateId") not in state_by_id:
            raise StateIndexError(f"{transition.get('id')} has unknown fromStateId")
        if transition.get("toStateId") not in state_by_id:
            raise StateIndexError(f"{transition.get('id')} has unknown toStateId")

    p13_after_ids = fact_ids((CF0 / "p1.3-after-code-facts.json").as_posix())
    current_ids = fact_ids((CF0 / "code-facts.json").as_posix())
    old_mul = {
        "fact.function.mul",
        "fact.function.mul.return.left_times_right",
        "fact.function.main.calls.mul",
    }
    new_multiply = {
        "fact.function.multiply",
        "fact.function.multiply.return.left_times_right",
        "fact.function.main.calls.multiply",
    }
    if not old_mul.issubset(p13_after_ids):
        raise StateIndexError("P1.3 after-state must contain old mul implementation facts")
    if not new_multiply.issubset(current_ids):
        raise StateIndexError("P1.7 current state must contain multiply implementation facts")
    if old_mul.intersection(current_ids):
        raise StateIndexError("P1.7 current state must not contain old mul implementation facts")

    p17_historical_ids = fact_ids((CF0 / "p1.9-before-code-facts.json").as_posix())
    if not new_multiply.issubset(p17_historical_ids):
        raise StateIndexError("P1.7 historical state must contain multiply implementation facts")
    if old_mul.intersection(p17_historical_ids):
        raise StateIndexError("P1.7 historical state must not contain old mul implementation facts")

    p17_report = read_json(ROOT / CF0 / "p1.7-refactor-delta-report.json")
    remapped_units = p17_report.get("delta", {}).get("remappedUnits", [])
    if not any(isinstance(remap, dict) and remap.get("unitId") == "unit.behavior.mul" for remap in remapped_units):
        raise StateIndexError("P1.7 transition must preserve and remap unit.behavior.mul")
    current_unit_facts = overlay_unit_fact_ids((DOCS_CF0 / "intentgraph.overlay.json").as_posix(), "unit.behavior.mul")
    if not new_multiply.intersection(current_unit_facts):
        raise StateIndexError("unit.behavior.mul must reference current multiply facts")
    if old_mul.intersection(current_unit_facts):
        raise StateIndexError("unit.behavior.mul must not reference old mul facts in the current overlay")
    current_overlay = read_json(ROOT / DOCS_CF0 / "intentgraph.overlay.json")
    current_unit_ids = {
        unit["id"]
        for unit in current_overlay.get("intentUnits", [])
        if isinstance(unit, dict) and isinstance(unit.get("id"), str)
    }
    if "unit.behavior.unsupported-operation" not in current_unit_ids:
        raise StateIndexError("P1.9 current state must include unit.behavior.unsupported-operation")
    if "fact.function.main.stderr.unsupported_operation" not in current_ids:
        raise StateIndexError("P1.9 current state must include unsupported-operation code fact")


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit the CF0 historical/current state index.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    try:
        index = build_index()
        write_json(args.out, index)
    except (OSError, json.JSONDecodeError, StateIndexError) as error:
        print(f"emit CF0 historical state index failed: {error}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
