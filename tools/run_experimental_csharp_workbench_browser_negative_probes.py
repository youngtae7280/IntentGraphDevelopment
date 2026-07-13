"""Fail-closed probes for the P9.33 browser observation validator."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Callable

from run_experimental_csharp_workbench_browser_probe import (
    REQUIRED_RUNTIME_CHECK_IDS,
    canonical_pretty,
    validate_runtime_observation,
    validate_output_paths,
)


def good_observation() -> dict[str, Any]:
    checks = [
        {"id": identifier, "passed": True, "actual": True, "expected": True}
        for identifier in REQUIRED_RUNTIME_CHECK_IDS
    ]
    return {
        "result": "pass",
        "graph": {"nodeCount": 8208, "edgeCount": 8023},
        "overview": {
            "pixels": {
                "canvasCount": 4,
                "totalOpaqueSampleCount": 1200,
                "materialOpaqueSampleCount": 300,
            }
        },
        "maximum": {
            "pixels": {
                "totalOpaqueSampleCount": 180,
                "materialOpaqueSampleCount": 12,
            },
            "endpointGeometryScale": 1.0,
            "state": {
                "logicalZoom": 100,
                "rendererZoom": 100,
                "effectiveGeometryZoom": 100,
                "virtualGeometryScale": 1.0,
                "selectedEdgeRenderedWidth": 0.55,
                "selectedEdgeRenderedOpacity": 0.68,
                "materialProfile": "cached-astral-forged-glass-v3",
                "materialCandidateCount": 2,
            },
            "selectedEndpointMaterialPixels": {
                "opaqueSampleCount": 800,
                "chromaticSampleCount": 120,
                "uniqueColorBucketCount": 24,
                "luminanceRange": 120,
            },
            "selectionText": "relation\nsource\nproject.project\ntarget\nwork.item",
        },
        "checks": checks,
        "errors": [],
    }


def good_screenshot() -> dict[str, Any]:
    return {
        "validPng": True,
        "width": 1440,
        "height": 1000,
        "byteLength": 100000,
        "uniqueColorBucketCount": 80,
        "luminanceRange": 180,
    }


Mutation = Callable[[dict[str, Any], dict[str, Any]], None]


def mutate_node_count(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["graph"]["nodeCount"] = 1


def mutate_edge_count(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["graph"]["edgeCount"] = 1


def mutate_failed_check(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["checks"][0]["passed"] = False


def mutate_missing_required_check(
    observation: dict[str, Any], _screenshot: dict[str, Any]
) -> None:
    observation["checks"] = observation["checks"][1:]


def mutate_blank_graph(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["overview"]["pixels"]["totalOpaqueSampleCount"] = 0


def mutate_blank_material(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["overview"]["pixels"]["materialOpaqueSampleCount"] = 0


def mutate_blank_maximum_graph(
    observation: dict[str, Any], _screenshot: dict[str, Any]
) -> None:
    observation["maximum"]["pixels"]["totalOpaqueSampleCount"] = 0


def mutate_blank_maximum_material(
    observation: dict[str, Any], _screenshot: dict[str, Any]
) -> None:
    observation["maximum"]["pixels"]["materialOpaqueSampleCount"] = 0


def mutate_geometry_scale(
    observation: dict[str, Any], _screenshot: dict[str, Any]
) -> None:
    observation["maximum"]["endpointGeometryScale"] = 0.5


def mutate_material_detail(
    observation: dict[str, Any], _screenshot: dict[str, Any]
) -> None:
    observation["maximum"]["selectedEndpointMaterialPixels"] = {
        "opaqueSampleCount": 8,
        "chromaticSampleCount": 0,
        "uniqueColorBucketCount": 1,
        "luminanceRange": 2,
    }


def mutate_material_candidates(
    observation: dict[str, Any], _screenshot: dict[str, Any]
) -> None:
    observation["maximum"]["state"]["materialCandidateCount"] = 8208


def mutate_zoom(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["maximum"]["state"]["effectiveGeometryZoom"] = 24


def mutate_edge_width(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["maximum"]["state"]["selectedEdgeRenderedWidth"] = 2.5


def mutate_material(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["maximum"]["state"]["materialProfile"] = "plastic-orb"


def mutate_selection(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["maximum"]["selectionText"] = ""


def mutate_runtime_error(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["errors"] = ["synthetic browser error"]


def mutate_screenshot(_observation: dict[str, Any], screenshot: dict[str, Any]) -> None:
    screenshot["validPng"] = False


PROBES: tuple[tuple[str, Mutation, str], ...] = (
    ("wrong-node-count", mutate_node_count, "node count mismatch"),
    ("wrong-edge-count", mutate_edge_count, "edge count mismatch"),
    ("failed-page-check", mutate_failed_check, "runtime checks failed"),
    (
        "missing-required-page-check",
        mutate_missing_required_check,
        "required checks missing",
    ),
    ("blank-graph-canvas", mutate_blank_graph, "graph canvas was blank"),
    ("blank-material-canvas", mutate_blank_material, "material canvas was blank"),
    (
        "blank-maximum-zoom-graph-canvas",
        mutate_blank_maximum_graph,
        "maximum-zoom graph canvas was blank",
    ),
    (
        "blank-maximum-zoom-material-canvas",
        mutate_blank_maximum_material,
        "maximum-zoom material canvas was blank",
    ),
    (
        "mutated-model-geometry-at-actual-zoom",
        mutate_geometry_scale,
        "endpoint geometry scale mismatch",
    ),
    (
        "flat-selected-endpoint-material",
        mutate_material_detail,
        "selected endpoint material opaqueSampleCount is below",
    ),
    (
        "unbounded-material-viewport-candidates",
        mutate_material_candidates,
        "material viewport candidate count is unbounded",
    ),
    ("wrong-effective-zoom", mutate_zoom, "effectiveGeometryZoom mismatch"),
    ("oversized-selected-edge", mutate_edge_width, "selectedEdgeRenderedWidth mismatch"),
    ("wrong-material", mutate_material, "material profile mismatch"),
    ("empty-selection-inspector", mutate_selection, "selection inspector is incomplete"),
    ("runtime-script-error", mutate_runtime_error, "reported script errors"),
    ("invalid-screenshot", mutate_screenshot, "not a valid PNG"),
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run repeatable negative probes for browser runtime observations."
    )
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    probe_results: list[dict[str, Any]] = []
    for identifier, mutate, expected_error in PROBES:
        observation = deepcopy(good_observation())
        screenshot = deepcopy(good_screenshot())
        mutate(observation, screenshot)
        errors = validate_runtime_observation(observation, screenshot, 8208, 8023)
        observed = any(expected_error in error for error in errors)
        probe_results.append(
            {
                "id": identifier,
                "expectedError": expected_error,
                "expectedFailureObserved": observed,
                "errors": errors,
            }
        )
    output_guards = (
        (
            "report-overwrites-workbench-input",
            Path("workbench/report.json"),
            Path("evidence/screenshot.png"),
            "outside the input workbench",
        ),
        (
            "screenshot-overwrites-workbench-input",
            Path("evidence/report.json"),
            Path("workbench/index.html"),
            "outside the input workbench",
        ),
        (
            "report-screenshot-output-collision",
            Path("evidence/output.bin"),
            Path("evidence/output.bin"),
            "must be different",
        ),
    )
    workbench = Path("workbench").resolve()
    for identifier, report_path, screenshot_path, expected_error in output_guards:
        errors: list[str] = []
        try:
            validate_output_paths(
                workbench, report_path.resolve(), screenshot_path.resolve()
            )
        except ValueError as error:
            errors.append(str(error))
        probe_results.append(
            {
                "id": identifier,
                "expectedError": expected_error,
                "expectedFailureObserved": any(
                    expected_error in error for error in errors
                ),
                "errors": errors,
            }
        )
    result = "pass" if all(item["expectedFailureObserved"] for item in probe_results) else "fail"
    report = {
        "artifactRole": "intentgraph-workbench-browser-runtime-negative-probes-report",
        "status": (
            "intentgraph-workbench-browser-runtime-negative-probes-passed"
            if result == "pass"
            else "intentgraph-workbench-browser-runtime-negative-probes-failed"
        ),
        "scope": "p9.33-browser-runtime-validation-negative-probes",
        "result": result,
        "probeCount": len(probe_results),
        "probes": probe_results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(canonical_pretty(report), encoding="utf-8")
    print(json.dumps({"result": result, "probeCount": len(probe_results)}))
    return 0 if result == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
