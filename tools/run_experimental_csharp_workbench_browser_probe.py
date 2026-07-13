"""Run the static project Workbench through an installed Chromium browser."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import html
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import struct
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from typing import Any
import zlib


REPO_ROOT = Path(__file__).resolve().parents[1]
BROWSER_CANDIDATES = (
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
)
RUNTIME_REPORT_PATTERN = re.compile(
    r'<script[^>]*id="intentgraph-runtime-probe-report"[^>]*>(.*?)</script>',
    re.DOTALL,
)
REQUIRED_RUNTIME_CHECK_IDS = (
    "full-node-count-loaded",
    "full-edge-count-loaded",
    "single-graph-instance",
    "overview-canvas-nonblank",
    "overview-material-nonblank",
    "astral-forged-glass-material-active",
    "material-sprite-cache-bounded",
    "material-viewport-candidates-bounded",
    "selected-endpoint-material-detailed",
    "logical-zoom-100",
    "renderer-zoom-100",
    "effective-geometry-zoom-100",
    "virtual-geometry-scale-unity",
    "maximum-canvas-nonblank",
    "maximum-material-nonblank",
    "model-geometry-stable-at-actual-zoom",
    "selected-edge-screen-width",
    "selected-edge-opacity",
    "selection-inspector-populated",
    "runtime-errors-empty",
)


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def repo_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


def path_is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def validate_output_paths(workbench: Path, output: Path, screenshot_output: Path) -> None:
    if output.resolve() == screenshot_output.resolve():
        raise ValueError("report and screenshot output paths must be different")
    if path_is_within(output, workbench) or path_is_within(
        screenshot_output, workbench
    ):
        raise ValueError("report and screenshot outputs must be outside the input workbench")


def artifact_evidence(path: Path) -> dict[str, Any]:
    return {
        "path": repo_path(path),
        "byteLength": path.stat().st_size,
        "sha256": sha256_file(path),
    }


def find_browser(explicit: Path | None = None) -> tuple[Path, str]:
    candidates = (explicit,) if explicit is not None else BROWSER_CANDIDATES
    for candidate in candidates:
        if candidate is not None and candidate.is_file():
            family = "edge" if "edge" in candidate.name.lower() else "chrome"
            return candidate.resolve(), family
    raise FileNotFoundError("Microsoft Edge or Google Chrome was not found")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: Any) -> None:
        return


def start_server(root: Path) -> tuple[ThreadingHTTPServer, threading.Thread]:
    def handler(*args: Any, **kwargs: Any) -> QuietHandler:
        return QuietHandler(*args, directory=str(root), **kwargs)

    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def browser_base_args(browser: Path, profile: Path) -> list[str]:
    return [
        str(browser),
        "--headless=new",
        "--disable-background-networking",
        "--disable-component-update",
        "--disable-default-apps",
        "--disable-extensions",
        "--disable-sync",
        "--metrics-recording-only",
        "--mute-audio",
        "--no-default-browser-check",
        "--no-first-run",
        "--force-device-scale-factor=1",
        "--run-all-compositor-stages-before-draw",
        "--window-size=1440,1000",
        f"--user-data-dir={profile}",
    ]


def run_browser_capture(
    browser: Path, profile: Path, url: str, output: Path
) -> tuple[str, str]:
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()
    completed = subprocess.run(
        browser_base_args(browser, profile)
        + [
            "--dump-dom",
            f"--screenshot={output.resolve()}",
            "--virtual-time-budget=12000",
            url,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            "headless browser capture failed: "
            + (completed.stderr.strip() or f"exit {completed.returncode}")
        )
    if not output.is_file():
        raise RuntimeError("headless browser did not create the screenshot")
    return completed.stdout, completed.stderr


class VSFixedFileInfo(ctypes.Structure):
    _fields_ = [
        ("signature", ctypes.c_uint32),
        ("structureVersion", ctypes.c_uint32),
        ("fileVersionMs", ctypes.c_uint32),
        ("fileVersionLs", ctypes.c_uint32),
        ("productVersionMs", ctypes.c_uint32),
        ("productVersionLs", ctypes.c_uint32),
        ("fileFlagsMask", ctypes.c_uint32),
        ("fileFlags", ctypes.c_uint32),
        ("fileOs", ctypes.c_uint32),
        ("fileType", ctypes.c_uint32),
        ("fileSubtype", ctypes.c_uint32),
        ("fileDateMs", ctypes.c_uint32),
        ("fileDateLs", ctypes.c_uint32),
    ]


def windows_file_version(path: Path) -> str:
    version_api = ctypes.windll.version
    size = version_api.GetFileVersionInfoSizeW(str(path), None)
    if size <= 0:
        raise RuntimeError("browser file version resource was not found")
    buffer = ctypes.create_string_buffer(size)
    if not version_api.GetFileVersionInfoW(str(path), 0, size, buffer):
        raise RuntimeError("browser file version resource could not be read")
    pointer = ctypes.c_void_p()
    length = ctypes.c_uint()
    if not version_api.VerQueryValueW(
        buffer, "\\", ctypes.byref(pointer), ctypes.byref(length)
    ):
        raise RuntimeError("browser fixed file version was not found")
    info = ctypes.cast(pointer, ctypes.POINTER(VSFixedFileInfo)).contents
    if info.signature != 0xFEEF04BD:
        raise RuntimeError("browser fixed file version signature is invalid")
    return ".".join(
        str(value)
        for value in (
            info.fileVersionMs >> 16,
            info.fileVersionMs & 0xFFFF,
            info.fileVersionLs >> 16,
            info.fileVersionLs & 0xFFFF,
        )
    )


def browser_identity(browser: Path, family: str) -> dict[str, Any]:
    return {
        "family": family,
        "version": windows_file_version(browser),
        "versionSource": "windows-file-version-resource",
        "executableName": browser.name,
        "executableSha256": sha256_file(browser),
    }


def parse_runtime_report(dom: str) -> dict[str, Any]:
    match = RUNTIME_REPORT_PATTERN.search(dom)
    if match is None:
        raise ValueError("runtime probe report was not found in the rendered DOM")
    value = json.loads(html.unescape(match.group(1)))
    if not isinstance(value, dict):
        raise ValueError("runtime probe report must be a JSON object")
    return value


def paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left


def png_evidence(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"exists": False, "validPng": False}
    data = path.read_bytes()
    result: dict[str, Any] = {
        "exists": True,
        "validPng": False,
        "byteLength": len(data),
        "sha256": sha256_file(path),
        "path": repo_path(path),
    }
    if len(data) < 24 or data[:8] != b"\x89PNG\r\n\x1a\n":
        return result
    offset = 8
    width = height = bit_depth = color_type = interlace = None
    compressed = bytearray()
    while offset + 12 <= len(data):
        length = struct.unpack(">I", data[offset : offset + 4])[0]
        kind = data[offset + 4 : offset + 8]
        payload = data[offset + 8 : offset + 8 + length]
        offset += 12 + length
        if kind == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif kind == b"IEND":
            break
    result.update({"width": width, "height": height})
    channels = {2: 3, 6: 4}.get(color_type)
    if (
        not isinstance(width, int)
        or not isinstance(height, int)
        or bit_depth != 8
        or channels is None
        or interlace != 0
    ):
        result["decodeStatus"] = "unsupported-png-layout"
        return result
    stride = width * channels
    raw = zlib.decompress(bytes(compressed))
    if len(raw) != (stride + 1) * height:
        result["decodeStatus"] = "unexpected-scanline-length"
        return result
    rows: list[bytearray] = []
    previous = bytearray(stride)
    cursor = 0
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        source = raw[cursor : cursor + stride]
        cursor += stride
        row = bytearray(stride)
        for index, value in enumerate(source):
            left = row[index - channels] if index >= channels else 0
            up = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                predictor = paeth(left, up, upper_left)
            else:
                result["decodeStatus"] = f"unsupported-filter-{filter_type}"
                return result
            row[index] = (value + predictor) & 0xFF
        rows.append(row)
        previous = row
    x_start, x_end = width // 5, width * 4 // 5
    y_start, y_end = height // 10, height * 7 // 10
    step = max(1, min(width, height) // 100)
    color_buckets: set[tuple[int, int, int]] = set()
    luminance_values: list[int] = []
    chromatic_samples = 0
    sample_count = 0
    for y in range(y_start, y_end, step):
        row = rows[y]
        for x in range(x_start, x_end, step):
            index = x * channels
            red, green, blue = row[index : index + 3]
            sample_count += 1
            color_buckets.add((red // 16, green // 16, blue // 16))
            luminance_values.append((red * 3 + green * 6 + blue) // 10)
            if max(red, green, blue) - min(red, green, blue) > 12:
                chromatic_samples += 1
    result.update(
        {
            "validPng": True,
            "decodeStatus": "pass",
            "sampleCount": sample_count,
            "uniqueColorBucketCount": len(color_buckets),
            "luminanceRange": (
                max(luminance_values) - min(luminance_values)
                if luminance_values
                else 0
            ),
            "chromaticSampleCount": chromatic_samples,
        }
    )
    return result


def read_expected_counts(workbench: Path) -> tuple[int, int]:
    projection = json.loads((workbench / "projection.json").read_text(encoding="utf-8"))
    return len(projection["graph"]["nodes"]), len(projection["graph"]["edges"])


def validate_runtime_observation(
    observation: dict[str, Any],
    screenshot: dict[str, Any],
    expected_node_count: int,
    expected_edge_count: int,
    expected_material: str = "cached-astral-forged-glass-v3",
) -> list[str]:
    errors: list[str] = []
    if observation.get("result") != "pass":
        errors.append("browser runtime observation did not pass")
    graph = observation.get("graph", {})
    if graph.get("nodeCount") != expected_node_count:
        errors.append("browser runtime node count mismatch")
    if graph.get("edgeCount") != expected_edge_count:
        errors.append("browser runtime edge count mismatch")
    checks = observation.get("checks", [])
    check_ids = [item.get("id") for item in checks if isinstance(item, dict)]
    missing_checks = sorted(set(REQUIRED_RUNTIME_CHECK_IDS) - set(check_ids))
    if missing_checks:
        errors.append("browser runtime required checks missing: " + ", ".join(missing_checks))
    duplicate_checks = sorted(
        identifier for identifier in set(check_ids) if check_ids.count(identifier) > 1
    )
    if duplicate_checks:
        errors.append("browser runtime duplicate checks: " + ", ".join(duplicate_checks))
    failed_checks = [
        item.get("id", "unknown")
        for item in checks
        if isinstance(item, dict)
        if item.get("passed") is not True
    ]
    if failed_checks:
        errors.append("browser runtime checks failed: " + ", ".join(failed_checks))
    overview = observation.get("overview", {})
    overview_pixels = overview.get("pixels", {})
    if int(overview_pixels.get("canvasCount") or 0) < 1:
        errors.append("browser runtime graph canvas was not observed")
    if int(overview_pixels.get("totalOpaqueSampleCount") or 0) < 1:
        errors.append("browser runtime graph canvas was blank")
    if int(overview_pixels.get("materialOpaqueSampleCount") or 0) < 1:
        errors.append("browser runtime material canvas was blank")
    maximum = observation.get("maximum", {})
    maximum_state = maximum.get("state", {})
    maximum_pixels = maximum.get("pixels", {})
    if int(maximum_pixels.get("totalOpaqueSampleCount") or 0) < 1:
        errors.append("browser runtime maximum-zoom graph canvas was blank")
    if int(maximum_pixels.get("materialOpaqueSampleCount") or 0) < 1:
        errors.append("browser runtime maximum-zoom material canvas was blank")
    try:
        endpoint_geometry_scale = float(maximum.get("endpointGeometryScale"))
    except (TypeError, ValueError):
        errors.append("browser runtime endpoint geometry scale is missing")
    else:
        if abs(endpoint_geometry_scale - 1.0) > 0.01:
            errors.append("browser runtime endpoint geometry scale mismatch")
    numeric_expectations = (
        ("logicalZoom", 100.0, 0.001),
        ("rendererZoom", 100.0, 0.001),
        ("effectiveGeometryZoom", 100.0, 0.001),
        ("virtualGeometryScale", 1.0, 0.001),
        ("selectedEdgeRenderedWidth", 0.55, 0.002),
        ("selectedEdgeRenderedOpacity", 0.68, 0.002),
    )
    for key, expected, tolerance in numeric_expectations:
        try:
            actual = float(maximum_state.get(key))
        except (TypeError, ValueError):
            errors.append(f"browser runtime {key} is missing")
            continue
        if abs(actual - expected) > tolerance:
            errors.append(f"browser runtime {key} mismatch")
    material_pixels = maximum.get("selectedEndpointMaterialPixels", {})
    material_thresholds = (
        ("opaqueSampleCount", 120),
        ("chromaticSampleCount", 12),
        ("uniqueColorBucketCount", 8),
        ("luminanceRange", 35),
    )
    for key, minimum in material_thresholds:
        try:
            actual = int(material_pixels.get(key, 0))
        except (TypeError, ValueError):
            actual = 0
        if actual < minimum:
            errors.append(
                f"browser runtime selected endpoint material {key} is below {minimum}"
            )
    try:
        material_candidate_count = int(maximum_state.get("materialCandidateCount", 0))
    except (TypeError, ValueError):
        material_candidate_count = 0
    if not 0 < material_candidate_count < expected_node_count:
        errors.append("browser runtime material viewport candidate count is unbounded")
    if maximum_state.get("materialProfile") != expected_material:
        errors.append("browser runtime material profile mismatch")
    selection_text = maximum.get("selectionText")
    if not isinstance(selection_text, str) or not all(
        marker in selection_text for marker in ("source", "target")
    ):
        errors.append("browser runtime selection inspector is incomplete")
    if observation.get("errors") != []:
        errors.append("browser runtime reported script errors")
    if screenshot.get("validPng") is not True:
        errors.append("browser screenshot is not a valid PNG")
    if int(screenshot.get("width") or 0) != 1440 or int(screenshot.get("height") or 0) != 1000:
        errors.append("browser screenshot dimensions mismatch")
    if int(screenshot.get("byteLength") or 0) < 10000:
        errors.append("browser screenshot is unexpectedly small")
    if int(screenshot.get("uniqueColorBucketCount") or 0) < 16:
        errors.append("browser screenshot lacks visual variation")
    if int(screenshot.get("luminanceRange") or 0) < 24:
        errors.append("browser screenshot luminance range is too narrow")
    return errors


def run_probe(
    workbench: Path,
    output: Path,
    screenshot_output: Path,
    browser_path: Path | None = None,
    expected_material: str = "cached-astral-forged-glass-v3",
) -> dict[str, Any]:
    workbench = workbench.resolve(strict=True)
    output = output.resolve()
    screenshot_output = screenshot_output.resolve()
    validate_output_paths(workbench, output, screenshot_output)
    errors: list[str] = []
    observation: dict[str, Any] = {}
    screenshot: dict[str, Any] = {}
    browser_family = "unavailable"
    browser_details: dict[str, Any] = {}
    input_artifacts: dict[str, Any] = {}
    expected_node_count = expected_edge_count = 0
    try:
        if not (workbench / "index.html").is_file() or not (workbench / "projection.json").is_file():
            raise ValueError("workbench must contain index.html and projection.json")
        input_artifacts = {
            name: artifact_evidence(workbench / name)
            for name in ("index.html", "projection.json", "manifest.json", "validation-report.json")
        }
        expected_node_count, expected_edge_count = read_expected_counts(workbench)
        browser, browser_family = find_browser(browser_path)
        browser_details = browser_identity(browser, browser_family)
        server, thread = start_server(workbench)
        try:
            url = f"http://127.0.0.1:{server.server_port}/?intentGraphRuntimeProbe=1"
            with tempfile.TemporaryDirectory(prefix="intentgraph-browser-probe-") as temporary:
                temporary_root = Path(temporary)
                dom, _ = run_browser_capture(
                    browser,
                    temporary_root / "capture-profile",
                    url,
                    screenshot_output,
                )
                observation = parse_runtime_report(dom)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)
        screenshot = png_evidence(screenshot_output)
        errors.extend(
            validate_runtime_observation(
                observation,
                screenshot,
                expected_node_count,
                expected_edge_count,
                expected_material,
            )
        )
    except Exception as error:  # The report remains useful on environment failures.
        errors.append(str(error))
    result = "pass" if not errors else "fail"
    report = {
        "artifactRole": "intentgraph-workbench-headless-browser-regression-report",
        "status": (
            "intentgraph-workbench-headless-browser-regression-passed"
            if result == "pass"
            else "intentgraph-workbench-headless-browser-regression-failed"
        ),
        "scope": "p9.33-actual-100x-astral-material-regression",
        "result": result,
        "input": {
            "workbench": repo_path(workbench),
            "expectedNodeCount": expected_node_count,
            "expectedEdgeCount": expected_edge_count,
            "expectedMaterial": expected_material,
            "artifacts": input_artifacts,
        },
        "browser": {
            **browser_details,
            "family": browser_family,
            "headless": True,
            "loopbackOnly": True,
            "thirdPartyAutomationDependency": False,
            "capture": {
                "singleProcessDomAndScreenshot": True,
                "viewport": {"width": 1440, "height": 1000},
                "virtualTimeBudgetMilliseconds": 12000,
                "runtimeQuery": "intentGraphRuntimeProbe=1",
            },
        },
        "runtimeObservation": observation,
        "screenshotEvidence": screenshot,
        "boundary": {
            "externalNetworkRequired": False,
            "graphMutation": False,
            "sourceMutation": False,
            "snapshotMutation": False,
            "targetRepositoryMutation": False,
            "browserObservationIsSemanticAuthority": False,
        },
        "errors": errors,
    }
    write_json(output, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a real headless browser regression over a static project Workbench."
    )
    parser.add_argument("--workbench", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--screenshot-out", required=True, type=Path)
    parser.add_argument("--browser", type=Path)
    parser.add_argument(
        "--expected-material", default="cached-astral-forged-glass-v3"
    )
    args = parser.parse_args()
    try:
        report = run_probe(
            args.workbench,
            args.out,
            args.screenshot_out,
            args.browser,
            args.expected_material,
        )
    except (FileNotFoundError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    print(json.dumps({"result": report["result"], "errors": report["errors"]}))
    return 0 if report["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
