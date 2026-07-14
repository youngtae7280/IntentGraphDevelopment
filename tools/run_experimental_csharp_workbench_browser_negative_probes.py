"""Fail-closed probes for the Graphify-style browser observation validator."""

from __future__ import annotations

import argparse
from copy import deepcopy
import json
from pathlib import Path
from typing import Any, Callable

from run_experimental_csharp_workbench_browser_probe import (
    REQUIRED_RUNTIME_CHECK_IDS,
    canonical_pretty,
    validate_output_paths,
    validate_runtime_observation,
)


WINDOWSUTILITY_NODE_COUNT = 8194
WINDOWSUTILITY_EDGE_COUNT = 7986


def good_observation() -> dict[str, Any]:
    checks = [
        {"id": identifier, "passed": True, "actual": True, "expected": True}
        for identifier in REQUIRED_RUNTIME_CHECK_IDS
    ]
    return {
        "result": "pass",
        "graph": {
            "nodeCount": WINDOWSUTILITY_NODE_COUNT,
            "edgeCount": WINDOWSUTILITY_EDGE_COUNT,
        },
        "overview": {
            "pixels": {
                "canvasCount": 3,
                "totalOpaqueSampleCount": 2200,
                "totalChromaticSampleCount": 1800,
                "communityColorCount": 9,
                "defaultLabelCount": 24,
                "ordinaryCodeVisibility": {
                    "nodeId": "code.method.example",
                    "opacity": 1.0,
                    "backgroundOpacity": 1.0,
                    "renderedWidth": 3.5,
                },
            },
            "selectedEdgeEndpointDistance": 42,
        },
        "maximum": {
            "pixels": {"totalOpaqueSampleCount": 180},
            "endpointGeometryScale": 1.0,
            "state": {
                "logicalZoom": 512,
                "rendererZoom": 512,
                "effectiveGeometryZoom": 512,
                "virtualGeometryScale": 1.0,
                "selectedEdgeRenderedWidth": 2.0,
                "selectedEdgeRenderedOpacity": 0.90,
                "selectedEdgeLineStyle": "solid",
                "selectedEdgeArrowShape": "none",
                "selectedSourceRenderedWidth": 12,
                "selectedTargetRenderedWidth": 12,
                "selectedEdgeLinePixels": {
                    "sampleCount": 621,
                    "observedSampleCount": 621,
                    "longestMissingRun": 0,
                    "coverage": 1.0,
                    "visibleSegmentLength": 620,
                },
            },
            "graphifyPaletteApplied": True,
            "allVisibleNodeShapesDot": True,
            "materialOverlayPresent": False,
            "unsupportedConfidenceFallsBackToUnknown": True,
            "pixelDetectorHiddenLineControl": {
                "sampleCount": 621,
                "observedSampleCount": 0,
                "longestMissingRun": 621,
                "coverage": 0.0,
                "visibleSegmentLength": 620,
            },
            "selectedEdgeKind": "invokes-syntax",
            "navigation": {
                "hundred": {"logicalZoom": 100, "rendererZoom": 100},
                "nearMaximum": {
                    "logicalZoom": 511,
                    "rendererZoom": 511,
                    "selectedSourceRenderedWidth": 12,
                    "selectedTargetRenderedWidth": 12,
                },
                "afterZoomOut": {"logicalZoom": 284.4, "rendererZoom": 284.4},
                "panDelta": {"x": 18, "y": -12},
                "unselectedMaximumAnchorDistance": 0,
                "hiddenSelectionMaximumAnchorDistance": 0,
                "hundredInteractionMilliseconds": 180,
                "nearMaximumInteractionMilliseconds": 200,
                "maximumInteractionMilliseconds": 220,
                "panInteractionMilliseconds": 18,
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


def set_path(*path: str, value: Any) -> Mutation:
    def mutate(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
        target: dict[str, Any] = observation
        for key in path[:-1]:
            target = target[key]
        target[path[-1]] = value

    return mutate


def mutate_failed_check(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["checks"][0]["passed"] = False


def mutate_missing_check(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["checks"] = observation["checks"][1:]


def mutate_line_pixels(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["maximum"]["state"]["selectedEdgeLinePixels"] = {
        "sampleCount": 621,
        "observedSampleCount": 410,
        "longestMissingRun": 8,
        "coverage": 410 / 621,
        "visibleSegmentLength": 620,
    }


def mutate_impossible_line_pixels(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["maximum"]["state"]["selectedEdgeLinePixels"] = {
        "sampleCount": 621,
        "observedSampleCount": 622,
        "longestMissingRun": 0,
        "coverage": 622 / 621,
        "visibleSegmentLength": 620,
    }


def mutate_pan(observation: dict[str, Any], _screenshot: dict[str, Any]) -> None:
    observation["maximum"]["navigation"]["panDelta"] = {"x": 0, "y": 0}


def mutate_screenshot(_observation: dict[str, Any], screenshot: dict[str, Any]) -> None:
    screenshot["validPng"] = False


PROBES: tuple[tuple[str, Mutation, str], ...] = (
    ("wrong-node-count", set_path("graph", "nodeCount", value=1), "node count mismatch"),
    ("wrong-edge-count", set_path("graph", "edgeCount", value=1), "edge count mismatch"),
    ("failed-page-check", mutate_failed_check, "runtime checks failed"),
    ("missing-required-page-check", mutate_missing_check, "required checks missing"),
    ("blank-overview", set_path("overview", "pixels", "totalOpaqueSampleCount", value=0), "graph canvas was blank"),
    ("achromatic-overview", set_path("overview", "pixels", "totalChromaticSampleCount", value=0), "lacks chromatic community contrast"),
    ("single-community-color", set_path("overview", "pixels", "communityColorCount", value=1), "too few community colors"),
    ("labels-not-sparse", set_path("overview", "pixels", "defaultLabelCount", value=WINDOWSUTILITY_NODE_COUNT), "labels are not hub-sparse"),
    ("dim-code-node", set_path("overview", "pixels", "ordinaryCodeVisibility", "opacity", value=0.2), "ordinary code visibility opacity"),
    ("blank-maximum", set_path("maximum", "pixels", "totalOpaqueSampleCount", value=0), "maximum-zoom graph canvas was blank"),
    ("mutated-model-geometry", set_path("maximum", "endpointGeometryScale", value=0.5), "endpoint geometry scale mismatch"),
    ("fragmented-edge", mutate_line_pixels, "edge line pixels are discontinuous"),
    ("impossible-edge-samples", mutate_impossible_line_pixels, "edge line pixels are discontinuous"),
    ("inconsistent-visible-edge-summary", set_path("maximum", "state", "selectedEdgeLinePixels", "coverage", value=0.99), "selected edge line pixel summary is inconsistent"),
    ("inconsistent-hidden-edge-summary", set_path("maximum", "pixelDetectorHiddenLineControl", "longestMissingRun", value=0), "hidden-line pixel summary is inconsistent"),
    ("blind-hidden-line-control", set_path("maximum", "pixelDetectorHiddenLineControl", "coverage", value=1.0), "edge pixel detector did not reject a hidden line"),
    ("selected-edge-dashed", set_path("maximum", "state", "selectedEdgeLineStyle", value="dashed"), "edge is not solid"),
    ("selected-edge-arrow", set_path("maximum", "state", "selectedEdgeArrowShape", value="triangle"), "edge arrow is not disabled"),
    ("wrong-palette", set_path("maximum", "graphifyPaletteApplied", value=False), "categorical palette is not applied"),
    ("wrong-node-shape", set_path("maximum", "allVisibleNodeShapesDot", value=False), "dot node shapes are not applied"),
    ("second-renderer", set_path("maximum", "materialOverlayPresent", value=True), "still has a second material renderer"),
    ("unsupported-confidence-not-closed", set_path("maximum", "unsupportedConfidenceFallsBackToUnknown", value=False), "unsupported confidence did not fail closed"),
    ("off-center-unselected", set_path("maximum", "navigation", "unselectedMaximumAnchorDistance", value=48), "unselected maximum anchor is off center"),
    ("off-center-hidden", set_path("maximum", "navigation", "hiddenSelectionMaximumAnchorDistance", value=48), "hidden-selection maximum anchor is off center"),
    ("wrong-effective-zoom", set_path("maximum", "state", "effectiveGeometryZoom", value=24), "effectiveGeometryZoom mismatch"),
    ("oversized-selected-edge", set_path("maximum", "state", "selectedEdgeRenderedWidth", value=4), "selectedEdgeRenderedWidth mismatch"),
    ("wrong-selected-opacity", set_path("maximum", "state", "selectedEdgeRenderedOpacity", value=0.3), "selectedEdgeRenderedOpacity mismatch"),
    ("oversized-node", set_path("maximum", "state", "selectedSourceRenderedWidth", value=60), "source endpoint size is unbounded"),
    ("broken-100x", set_path("maximum", "navigation", "hundred", "logicalZoom", value=24), "100x control mismatch"),
    ("unstable-511x-node-size", set_path("maximum", "navigation", "nearMaximum", "selectedSourceRenderedWidth", value=32), "near-maximum node sizes are unstable"),
    ("broken-zoom-out", set_path("maximum", "navigation", "afterZoomOut", "logicalZoom", value=512), "zoom-out control mismatch"),
    ("broken-pan", mutate_pan, "maximum pan control mismatch"),
    ("invalid-interaction-diagnostic", set_path("maximum", "navigation", "maximumInteractionMilliseconds", value=-1), "virtual-time diagnostic is invalid"),
    ("empty-selection", set_path("maximum", "selectionText", value=""), "selection inspector is incomplete"),
    ("runtime-error", set_path("errors", value=["synthetic error"]), "reported script errors"),
    ("invalid-screenshot", mutate_screenshot, "not a valid PNG"),
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Graphify-style workbench negative probes.")
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    probe_results: list[dict[str, Any]] = []
    for identifier, mutate, expected_error in PROBES:
        observation = deepcopy(good_observation())
        screenshot = deepcopy(good_screenshot())
        mutate(observation, screenshot)
        errors = validate_runtime_observation(
            observation,
            screenshot,
            WINDOWSUTILITY_NODE_COUNT,
            WINDOWSUTILITY_EDGE_COUNT,
            capture_elapsed_milliseconds=16000,
        )
        probe_results.append(
            {
                "id": identifier,
                "expectedError": expected_error,
                "expectedFailureObserved": any(expected_error in error for error in errors),
                "errors": errors,
            }
        )

    wall_clock_errors = validate_runtime_observation(
        good_observation(), good_screenshot(), WINDOWSUTILITY_NODE_COUNT, WINDOWSUTILITY_EDGE_COUNT,
        capture_elapsed_milliseconds=45000,
    )
    probe_results.append(
        {
            "id": "slow-headless-browser-capture",
            "expectedError": "headless browser capture exceeds the wall-clock budget",
            "expectedFailureObserved": any(
                "headless browser capture exceeds the wall-clock budget" in error
                for error in wall_clock_errors
            ),
            "errors": wall_clock_errors,
        }
    )

    workbench = Path("workbench").resolve()
    for identifier, report_path, screenshot_path, expected_error in (
        ("report-overwrites-workbench-input", Path("workbench/report.json"), Path("evidence/screenshot.png"), "outside the input workbench"),
        ("screenshot-overwrites-workbench-input", Path("evidence/report.json"), Path("workbench/index.html"), "outside the input workbench"),
        ("report-screenshot-output-collision", Path("evidence/output.bin"), Path("evidence/output.bin"), "must be different"),
    ):
        errors: list[str] = []
        try:
            validate_output_paths(workbench, report_path.resolve(), screenshot_path.resolve())
        except ValueError as error:
            errors.append(str(error))
        probe_results.append(
            {
                "id": identifier,
                "expectedError": expected_error,
                "expectedFailureObserved": any(expected_error in error for error in errors),
                "errors": errors,
            }
        )

    result = "pass" if all(item["expectedFailureObserved"] for item in probe_results) else "fail"
    report = {
        "artifactRole": "intentgraph-workbench-browser-runtime-negative-probes-report",
        "status": "intentgraph-workbench-browser-runtime-negative-probes-passed" if result == "pass" else "intentgraph-workbench-browser-runtime-negative-probes-failed",
        "scope": "p9.34r5-graphify-visual-parity-edge-continuity-negative-probes",
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
