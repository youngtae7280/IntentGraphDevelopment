"""Emit a static local WindowsUtility workbench export."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any


EXPORT_VERSION = "0.1.0"
WORK_ITEM = "P8.31 Static Local Workbench Export Prototype"
EXPORT_SCOPE = "p8.31-static-local-workbench-export-prototype"
VALIDATION_SCOPE = "p8.31-static-local-workbench-export-validation"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def file_summary(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    summary: dict[str, Any] = {
        "path": path.as_posix(),
        "byteLength": len(raw),
        "sha256": digest_bytes(raw),
    }
    if path.suffix.lower() == ".json":
        data = read_json(path)
        for key in ["artifactRole", "status", "scope", "result", "decision", "workItem"]:
            if key in data:
                summary[key] = data[key]
    return summary


def git_state(target_root: Path) -> dict[str, str]:
    def run_git(args: list[str]) -> str:
        result = subprocess.run(
            ["git", "-C", str(target_root), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        return result.stdout.strip()

    return {
        "status": run_git(["status", "--short", "--branch"]),
        "head": run_git(["rev-parse", "HEAD"]),
        "originMain": run_git(["rev-parse", "origin/main"]),
    }


def rewrite_screenshot_path(value: Any) -> Any:
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, child in value.items():
            if key == "screenshotPath":
                result[key] = "assets/screenshot.png"
            else:
                result[key] = rewrite_screenshot_path(child)
        return result
    if isinstance(value, list):
        return [rewrite_screenshot_path(item) for item in value]
    return value


def build_review_guide() -> dict[str, Any]:
    return {
        "title": "What this page is",
        "oneLine": "A static review dashboard for one proposed IntentGraph workflow over WindowsUtility shell/workspace code.",
        "plainLanguageSummary": (
            "This is not the WindowsUtility application. It is a local review surface that lets a human inspect "
            "whether IntentGraph has correctly gathered the mapping, evidence, and safety boundaries for one small "
            "WindowsUtility workflow before any source changes are allowed."
        ),
        "represents": [
            {
                "id": "represents.accepted-mapping",
                "label": "Accepted mapping",
                "meaning": "Which WindowsUtility shell/workspace area this IntentGraph slice is currently about.",
            },
            {
                "id": "represents.code-surface",
                "label": "Covered code surface",
                "meaning": "The files and workflow records that the slice claims to understand.",
            },
            {
                "id": "represents.non-applied-proposal",
                "label": "Non-applied proposal",
                "meaning": "A smoke-evidence proposal that has been described but not applied to WindowsUtility source.",
            },
            {
                "id": "represents.evidence",
                "label": "Evidence",
                "meaning": "Build, launch, screenshot, and browser checks collected from sandboxed/generated artifacts.",
            },
            {
                "id": "represents.authority-boundary",
                "label": "Authority boundary",
                "meaning": "Flags proving this page does not grant source-write, hardware, packaging, release, or productization authority.",
            },
        ],
        "reviewChecklist": [
            "Can you tell what WindowsUtility area this slice is about?",
            "Can you see what evidence exists and where it came from?",
            "Can you see that the proposal is not applied to source code?",
            "Can you see what remains blocked and unauthorized?",
            "Is this review surface clear enough to guide the next IntentGraph iteration?",
        ],
        "notThis": [
            "Not the WindowsUtility product UI.",
            "Not a source-code change.",
            "Not a proposal application.",
            "Not a packaging or release artifact.",
            "Not proof that IntentGraph is productized.",
        ],
    }


def build_projection(source_projection: dict[str, Any], scope: str, work_item: str, export_version: str) -> dict[str, Any]:
    projection = rewrite_screenshot_path(source_projection)
    if not isinstance(projection, dict):
        raise ValueError("projection must be an object")
    projection["artifactRole"] = "intentgraph-static-local-workbench-export-projection"
    projection["status"] = "intentgraph-static-local-workbench-export-projection-emitted"
    projection["scope"] = scope
    projection["exportVersion"] = export_version
    projection["workItem"] = work_item
    projection["reviewGuide"] = build_review_guide()
    projection.setdefault("claimScope", {})
    projection["claimScope"]["staticLocalExport"] = True
    projection["claimScope"]["networkRequired"] = False
    projection["claimScope"]["packagingClaimed"] = False
    projection["claimScope"]["releaseClaimed"] = False
    return projection


def escape_html(value: Any) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def render_html(projection: dict[str, Any]) -> str:
    data = json.dumps(projection, sort_keys=True, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>IntentGraph WindowsUtility Static Workbench Export</title>
  <style>
    :root {{
      --ink: #172033;
      --muted: #617087;
      --paper: #ffffff;
      --wash: #f4f6f9;
      --line: #d8dee8;
      --accent: #285ac8;
      --accent-soft: #edf3ff;
      --ok: #14724f;
      --warn: #8b6100;
      --blocked: #8b2b22;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--wash);
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      letter-spacing: 0;
    }}
    .layout {{ display: grid; grid-template-columns: 280px minmax(0, 1fr) 370px; min-height: 100vh; }}
    nav, aside {{ background: #fbfcfe; padding: 18px; border-color: var(--line); }}
    nav {{ border-right: 1px solid var(--line); }}
    aside {{ border-left: 1px solid var(--line); overflow: auto; }}
    main {{ padding: 18px; min-width: 0; }}
    h1 {{ font-size: 19px; line-height: 1.2; margin: 0 0 6px; }}
    h2 {{ font-size: 12px; text-transform: uppercase; color: var(--muted); margin: 22px 0 8px; }}
    h3 {{ font-size: 15px; margin: 0 0 10px; }}
    h4 {{ font-size: 13px; margin: 0 0 6px; }}
    p {{ color: var(--muted); line-height: 1.45; margin: 0 0 12px; }}
    button {{ font: inherit; }}
    .nav, .record {{
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      background: var(--paper);
      border-radius: 6px;
      padding: 9px 10px;
      margin-bottom: 8px;
      text-align: left;
      cursor: pointer;
    }}
    .nav.active, .record.active {{ border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }}
    .panel {{ background: var(--paper); border: 1px solid var(--line); border-radius: 8px; padding: 14px; min-width: 0; }}
    .brief {{ background: var(--paper); border: 1px solid #b8caf0; border-radius: 8px; padding: 18px; min-width: 0; }}
    .brief-title {{ font-size: 26px; line-height: 1.15; margin: 0 0 8px; }}
    .brief-lede {{ color: #33425b; font-size: 15px; max-width: 820px; }}
    .note {{ background: var(--accent-soft); border: 1px solid #c7d7fb; border-radius: 8px; padding: 12px; color: #24395f; }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .two {{ display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); gap: 12px; }}
    .stack {{ display: grid; gap: 12px; }}
    .list {{ margin: 0; padding-left: 18px; color: #33425b; line-height: 1.5; }}
    .list li {{ margin-bottom: 6px; }}
    .step {{ display: grid; grid-template-columns: minmax(0, 1fr) auto; gap: 12px; align-items: center; padding: 8px 0; border-bottom: 1px solid var(--line); }}
    .status {{ display: inline-flex; min-height: 22px; align-items: center; border: 1px solid var(--line); border-radius: 999px; padding: 2px 8px; font-size: 12px; color: var(--muted); }}
    .status.pass, .status.accepted, .status.emitted {{ color: var(--ok); border-color: #afd8c4; background: #effaf5; }}
    .status.not-applied {{ color: var(--warn); border-color: #dfcb91; background: #fff9e8; }}
    .status.blocked {{ color: var(--blocked); border-color: #e2b7af; background: #fff2f0; }}
    .metric {{ font-size: 24px; font-weight: 650; margin-bottom: 3px; }}
    img {{ width: 100%; max-height: 430px; object-fit: contain; border: 1px solid var(--line); border-radius: 8px; background: #111827; }}
    code, pre {{ font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 12px; color: #223044; }}
    pre {{ margin: 0; white-space: pre-wrap; word-break: break-word; background: #f1f3f6; border: 1px solid var(--line); border-radius: 6px; padding: 10px; max-height: 54vh; overflow: auto; }}
    @media (max-width: 1080px) {{
      .layout {{ grid-template-columns: 1fr; }}
      nav, aside {{ border-left: 0; border-right: 0; border-bottom: 1px solid var(--line); }}
      .grid, .two {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="layout">
    <nav>
      <h1>Static Workbench Export</h1>
      <p>Review dashboard for one proposed WindowsUtility IntentGraph workflow. It is not the WindowsUtility app.</p>
      <h2>Sections</h2>
      <button class="nav active" data-section="start">Start Here</button>
      <button class="nav" data-section="overview">Overview</button>
      <button class="nav" data-section="timeline">Timeline</button>
      <button class="nav" data-section="evidence">Evidence</button>
      <button class="nav" data-section="screenshot">Screenshot</button>
      <button class="nav" data-section="authority">Authority</button>
      <button class="nav" data-section="artifacts">Artifacts</button>
    </nav>
    <main id="section"></main>
    <aside>
      <h2>Selectable Records</h2>
      <div id="records"></div>
      <h2>Details</h2>
      <pre id="details"></pre>
    </aside>
  </div>
  <script id="workbench-export-data" type="application/json">{data}</script>
  <script>
    const projection = JSON.parse(document.getElementById('workbench-export-data').textContent);
    const section = document.getElementById('section');
    const records = document.getElementById('records');
    const details = document.getElementById('details');
    function html(value) {{ return String(value ?? '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch])); }}
    function badge(value) {{ const text = String(value ?? 'unknown'); return `<span class="status ${{html(text)}}">${{html(text)}}</span>`; }}
    function metric(label, value) {{ return `<div class="panel"><div class="metric">${{html(value)}}</div><p>${{html(label)}}</p></div>`; }}
    function start() {{
      const guide = projection.reviewGuide || {{}};
      section.innerHTML = `<div class="brief"><h3 class="brief-title">Before reading the records</h3><p class="brief-lede">${{html(guide.plainLanguageSummary || guide.oneLine || '')}}</p><div class="note"><strong>What you are reviewing:</strong> whether this static IntentGraph workbench clearly explains the WindowsUtility shell/workspace mapping, evidence, and blocked authority boundaries.</div></div><h2>What This Represents</h2><div class="grid">${{(guide.represents || []).map(item => `<div class="panel"><h4>${{html(item.label)}}</h4><p>${{html(item.meaning)}}</p></div>`).join('')}}</div><h2>What To Look At</h2><div class="two"><div class="panel"><h3>Review checklist</h3><ol class="list">${{(guide.reviewChecklist || []).map(item => `<li>${{html(item)}}</li>`).join('')}}</ol></div><div class="panel"><h3>What this is not</h3><ul class="list">${{(guide.notThis || []).map(item => `<li>${{html(item)}}</li>`).join('')}}</ul></div></div>`;
    }}
    function overview() {{
      section.innerHTML = `<div class="panel"><h3>${{html(projection.workItem)}}</h3><p>${{html(projection.proposal.summary)}}</p><div class="grid">${{metric('Timeline', projection.summary.timelineStepCount)}}${{metric('Evidence', projection.summary.evidenceCardCount)}}${{metric('Artifacts', projection.summary.sourceArtifactCount)}}</div></div><h2>Target and Claims</h2><div class="two"><div class="panel"><h3>Target</h3><pre>${{html(JSON.stringify(projection.target, null, 2))}}</pre></div><div class="panel"><h3>Claim scope</h3><pre>${{html(JSON.stringify(projection.claimScope, null, 2))}}</pre></div></div>`;
    }}
    function timeline() {{ section.innerHTML = `<div class="panel"><h3>Timeline</h3>${{projection.workflowTimeline.map(step => `<div class="step"><div><strong>${{html(step.label)}}</strong><br><code>${{html(step.artifact)}}</code></div>${{badge(step.status)}}</div>`).join('')}}</div>`; }}
    function evidence() {{ section.innerHTML = `<div class="grid">${{projection.evidence.map(card => `<div class="panel"><h3>${{html(card.kind)}}</h3>${{badge(card.result)}}<pre>${{html(JSON.stringify(card, null, 2))}}</pre></div>`).join('')}}</div>`; }}
    function screenshot() {{ const shot = projection.evidence.find(card => card.kind === 'sandboxed-screenshot') || {{}}; section.innerHTML = `<div class="panel"><h3>Sandboxed Screenshot</h3><p>${{html(shot.width)}} x ${{html(shot.height)}} / ${{html(shot.byteLength)}} bytes</p><img src="assets/screenshot.png" alt="WindowsUtility sandboxed shell screenshot"><h2>Evidence</h2><pre>${{html(JSON.stringify(shot, null, 2))}}</pre></div>`; }}
    function authority() {{ section.innerHTML = `<div class="panel"><h3>Authority False Flags</h3><p>This export is not proposal application, source write authority, hardware authority, packaging, release, or productization.</p><pre>${{html(JSON.stringify(projection.authorityBoundary, null, 2))}}</pre></div>`; }}
    function artifacts() {{ section.innerHTML = `<div class="panel"><h3>Source Artifact Links</h3>${{projection.sourceArtifacts.map(item => `<div class="step"><div><strong>${{html(item.path)}}</strong><br><code>${{html(item.sha256)}}</code></div>${{badge(item.status || item.result || 'recorded')}}</div>`).join('')}}</div>`; }}
    const render = {{ start, overview, timeline, evidence, screenshot, authority, artifacts }};
    document.querySelectorAll('.nav').forEach(button => button.addEventListener('click', () => {{ document.querySelectorAll('.nav').forEach(item => item.classList.remove('active')); button.classList.add('active'); render[button.dataset.section](); }}));
    projection.selectionRecords.forEach((record, index) => {{ const button = document.createElement('button'); button.className = 'record' + (index === 0 ? ' active' : ''); button.textContent = `${{record.kind}} - ${{record.id}}`; button.addEventListener('click', () => {{ document.querySelectorAll('.record').forEach(item => item.classList.remove('active')); button.classList.add('active'); details.textContent = JSON.stringify(record, null, 2); }}); records.appendChild(button); }});
    start();
    details.textContent = JSON.stringify(projection.selectionRecords[0] || projection, null, 2);
  </script>
</body>
</html>
"""


def build_manifest(
    projection: dict[str, Any],
    source_paths: list[Path],
    exported_files: list[Path],
    out_dir: Path,
    boundary_report: Path,
    export_version: str,
) -> dict[str, Any]:
    source_artifacts = [file_summary(path) for path in source_paths]
    exported = [file_summary(path) for path in exported_files]
    return {
        "artifactRole": "intentgraph-static-local-workbench-export-manifest",
        "status": "intentgraph-static-local-workbench-export-manifest-emitted",
        "scope": projection["scope"],
        "workItem": projection["workItem"],
        "exportVersion": export_version,
        "outputRoot": out_dir.as_posix(),
        "sourceArtifacts": source_artifacts,
        "exportedFiles": exported,
        "boundaryReport": file_summary(boundary_report),
        "targetBaseline": projection.get("target", {}),
        "authorityBoundary": {
            "sourceEditsAuthorized": False,
            "proposalApplicationAuthorized": False,
            "targetWritesAuthorized": False,
            "newSandboxRunAuthorized": False,
            "newUiLaunchAuthorized": False,
            "newScreenshotCaptureAuthorized": False,
            "aiAuthorityPromoted": False,
            "hardwareActionsAuthorized": False,
            "packagingAuthorized": False,
            "releaseAuthorized": False,
            "productizationAuthorized": False,
        },
        "generatedAtPolicy": "deterministic-no-runtime-timestamp",
        "determinism": {
            "noNondeterministicTimestamp": True,
            "sourceDigestBound": True,
            "localFilesOnly": True,
            "networkRequired": False,
        },
        "integrity": {
            "indexPath": "index.html",
            "projectionPath": "projection.json",
            "screenshotPath": "assets/screenshot.png",
        },
    }


def validate_export(
    export_dir: Path,
    target_root: Path,
    scope: str = VALIDATION_SCOPE,
    work_item: str = WORK_ITEM,
    require_orientation_markers: bool = False,
) -> dict[str, Any]:
    errors: list[str] = []
    index_path = export_dir / "index.html"
    projection_path = export_dir / "projection.json"
    manifest_path = export_dir / "manifest.json"
    screenshot_path = export_dir / "assets" / "screenshot.png"

    for path in [index_path, projection_path, manifest_path, screenshot_path]:
        if not path.exists():
            errors.append(f"missing required file: {path.relative_to(export_dir).as_posix()}")

    manifest: dict[str, Any] = {}
    projection: dict[str, Any] = {}
    if manifest_path.exists():
        try:
            manifest = read_json(manifest_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"manifest JSON parse failed: {exc}")
    if projection_path.exists():
        try:
            projection = read_json(projection_path)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"projection JSON parse failed: {exc}")

    if manifest:
        if manifest.get("artifactRole") != "intentgraph-static-local-workbench-export-manifest":
            errors.append("manifest artifactRole mismatch")
        if manifest.get("status") != "intentgraph-static-local-workbench-export-manifest-emitted":
            errors.append("manifest status mismatch")
        for field in [
            "exportVersion",
            "sourceArtifacts",
            "targetBaseline",
            "authorityBoundary",
            "generatedAtPolicy",
            "determinism",
            "integrity",
        ]:
            if field not in manifest:
                errors.append(f"manifest missing field: {field}")
        for artifact in manifest.get("sourceArtifacts", []):
            path = Path(str(artifact.get("path", "")))
            if not path.exists():
                errors.append(f"manifest source missing: {path.as_posix()}")
                continue
            actual = file_summary(path)
            if artifact.get("sha256") != actual["sha256"]:
                errors.append(f"manifest source digest mismatch: {path.as_posix()}")
        for file_record in manifest.get("exportedFiles", []):
            path = Path(str(file_record.get("path", "")))
            if not path.exists():
                errors.append(f"manifest export missing: {path.as_posix()}")
                continue
            actual = file_summary(path)
            if file_record.get("sha256") != actual["sha256"]:
                errors.append(f"manifest export digest mismatch: {path.as_posix()}")
        for key, value in manifest.get("authorityBoundary", {}).items():
            if value is not False:
                errors.append(f"manifest authorityBoundary.{key} must be false")
        if manifest.get("determinism", {}).get("networkRequired") is not False:
            errors.append("manifest determinism.networkRequired must be false")

    if projection:
        if projection.get("artifactRole") != "intentgraph-static-local-workbench-export-projection":
            errors.append("projection artifactRole mismatch")
        if projection.get("proposal", {}).get("applicationStatus") != "not-applied":
            errors.append("projection proposal must remain not-applied")
        for key, value in projection.get("authorityBoundary", {}).items():
            if value is not False:
                errors.append(f"projection authorityBoundary.{key} must be false")
        for key in [
            "sourceMutated",
            "targetMutated",
            "patchApplied",
            "proposalAcceptedByProjection",
            "newEvidenceCollected",
            "aiAuthorityGranted",
            "hardwareActionClaimed",
            "productizationClaimed",
            "packagingClaimed",
            "releaseClaimed",
            "networkRequired",
        ]:
            if projection.get("claimScope", {}).get(key) is not False:
                errors.append(f"projection claimScope.{key} must be false")
        if len(projection.get("selectionRecords", [])) < 5:
            errors.append("projection selection records missing")
        current = projection.get("target", {}).get("current", {})
        if current.get("status") != "## main...origin/main":
            errors.append("projection target current status must be clean/aligned")
        if current.get("head") != current.get("originMain"):
            errors.append("projection target current HEAD must match origin/main")

    if index_path.exists():
        html = index_path.read_text(encoding="utf-8")
        for marker in [
            "Static Workbench Export",
            "workbench-export-data",
            "Authority False Flags",
            "assets/screenshot.png",
            "Source Artifact Links",
        ]:
            if marker not in html:
                errors.append(f"index missing marker: {marker}")
        if require_orientation_markers:
            for marker in [
                "Before reading the records",
                "What This Represents",
                "What To Look At",
                "What this is not",
            ]:
                if marker not in html:
                    errors.append(f"index missing orientation marker: {marker}")
        for forbidden in ["https://", "http://", "fetch(", "XMLHttpRequest", "import("]:
            if forbidden in html:
                errors.append(f"index must not require network or dynamic imports: {forbidden}")

    if screenshot_path.exists():
        raw = screenshot_path.read_bytes()
        if not raw.startswith(b"\x89PNG\r\n\x1a\n"):
            errors.append("screenshot asset is not a PNG")

    try:
        target = git_state(target_root)
        if target["status"] != "## main...origin/main":
            errors.append("WindowsUtility target must remain clean/aligned")
        if target["head"] != target["originMain"]:
            errors.append("WindowsUtility target HEAD must match origin/main")
    except Exception as exc:  # noqa: BLE001
        errors.append(f"WindowsUtility target state check failed: {exc}")

    return {
        "artifactRole": "intentgraph-static-local-workbench-export-validation-report",
        "status": "intentgraph-static-local-workbench-export-validation-passed" if not errors else "intentgraph-static-local-workbench-export-validation-failed",
        "scope": scope,
        "workItem": work_item,
        "result": "pass" if not errors else "fail",
        "exportDir": export_dir.as_posix(),
        "summary": {
            "indexExists": index_path.exists(),
            "projectionExists": projection_path.exists(),
            "manifestExists": manifest_path.exists(),
            "screenshotExists": screenshot_path.exists(),
            "selectionRecordCount": len(projection.get("selectionRecords", [])) if projection else 0,
            "sourceArtifactCount": len(manifest.get("sourceArtifacts", [])) if manifest else 0,
            "exportedFileCount": len(manifest.get("exportedFiles", [])) if manifest else 0,
            "errorCount": len(errors),
        },
        "authorizations": {
            "sourceEditsAuthorized": False,
            "proposalApplicationAuthorized": False,
            "targetWritesAuthorized": False,
            "aiAuthorityPromoted": False,
            "hardwareActionsAuthorized": False,
            "packagingAuthorized": False,
            "releaseAuthorized": False,
            "productizationAuthorized": False,
        },
        "errors": errors,
    }


def emit_export(args: argparse.Namespace) -> dict[str, Any]:
    source_projection = read_json(args.projection)
    projection = build_projection(source_projection, args.scope, args.work_item, args.export_version)
    current_target = git_state(args.target_root)
    projection.setdefault("target", {})["current"] = current_target

    args.out_dir.mkdir(parents=True, exist_ok=True)
    assets_dir = args.out_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)

    screenshot_out = assets_dir / "screenshot.png"
    shutil.copyfile(args.screenshot, screenshot_out)

    projection_out = args.out_dir / "projection.json"
    write_json(projection_out, projection)

    index_out = args.out_dir / "index.html"
    index_out.write_text(render_html(projection), encoding="utf-8")

    source_paths = [args.boundary_report, args.projection, args.source_html, args.screenshot]
    exported_paths = [index_out, projection_out, screenshot_out]
    manifest = build_manifest(projection, source_paths, exported_paths, args.out_dir, args.boundary_report, args.export_version)
    manifest_out = args.out_dir / "manifest.json"
    write_json(manifest_out, manifest)

    validation = validate_export(
        args.out_dir,
        args.target_root,
        args.validation_scope,
        args.work_item,
        args.require_orientation_markers,
    )
    write_json(args.validation_out, validation)
    return validation


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a static local WindowsUtility workbench export.")
    parser.add_argument("--boundary-report", required=True, type=Path)
    parser.add_argument("--projection", required=True, type=Path)
    parser.add_argument("--source-html", required=True, type=Path)
    parser.add_argument("--screenshot", required=True, type=Path)
    parser.add_argument("--target-root", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--validation-out", required=True, type=Path)
    parser.add_argument("--scope", default=EXPORT_SCOPE)
    parser.add_argument("--validation-scope", default=VALIDATION_SCOPE)
    parser.add_argument("--work-item", default=WORK_ITEM)
    parser.add_argument("--export-version", default=EXPORT_VERSION)
    parser.add_argument("--require-orientation-markers", action="store_true")
    args = parser.parse_args()

    validation = emit_export(args)
    return 0 if validation["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
