"""Emit a WindowsUtility shell/workspace evidence workbench projection."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


REPORT_VERSION = "0.1.0"
WORK_ITEM = "P8.21 Shell Workspace Evidence Workbench Projection"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def artifact_summary(path: Path) -> dict[str, Any]:
    raw = path.read_bytes()
    summary: dict[str, Any] = {
        "path": path.as_posix(),
        "exists": path.exists(),
        "byteLength": len(raw),
        "sha256": digest_bytes(raw),
    }
    if path.suffix.lower() == ".json":
        data = read_json(path)
        for key in ["artifactRole", "status", "scope", "result", "decision", "workItem", "proposalId"]:
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


def as_status(value: Any) -> str:
    if value is True:
        return "pass"
    if value is False:
        return "fail"
    if value is None:
        return "unknown"
    return str(value)


def build_projection(args: argparse.Namespace, current_target: dict[str, str]) -> dict[str, Any]:
    accepted_mapping = read_json(args.accepted_mapping)
    accepted_mapping_verification = read_json(args.accepted_mapping_verification)
    accepted_mapping_negative = read_json(args.accepted_mapping_negative_probes)
    proposal = read_json(args.proposal)
    proposal_validation = read_json(args.proposal_validation)
    proposal_negative = read_json(args.proposal_negative_probes)
    build_evidence = read_json(args.build_evidence)
    ui_launch = read_json(args.ui_launch_evidence)
    screenshot = read_json(args.screenshot_evidence)

    mapping = accepted_mapping.get("acceptedMapping", {})
    target = accepted_mapping.get("target", {})
    proposal_delta = proposal.get("proposedCodeDelta", {})
    screenshot_evidence = screenshot.get("screenshotEvidence", {})
    ui_observation = screenshot.get("uiLaunch", {}).get("processObservation", {})

    source_paths = [
        args.accepted_mapping,
        args.accepted_mapping_verification,
        args.accepted_mapping_negative_probes,
        args.proposal,
        args.proposal_validation,
        args.proposal_negative_probes,
        args.build_evidence,
        args.ui_launch_evidence,
        args.screenshot_evidence,
        args.screenshot_png,
    ]

    source_artifacts = [artifact_summary(path) for path in source_paths]

    authority_boundary = {
        "sourceEditsAuthorized": False,
        "proposalApplicationAuthorized": False,
        "targetWritesAuthorized": False,
        "aiAuthorityPromoted": False,
        "hardwareActionsAuthorized": False,
        "productizationAuthorized": False,
        "newEvidenceCollectionAuthorized": False,
        "newUiLaunchAuthorized": False,
        "newScreenshotCaptureAuthorized": False,
    }

    workflow_timeline = [
        {
            "id": "p8.9-accepted-mapping",
            "label": "Accepted mapping",
            "status": mapping.get("mappingStatus", accepted_mapping.get("status")),
            "artifact": args.accepted_mapping.as_posix(),
        },
        {
            "id": "p8.10-accepted-mapping-negative-probes",
            "label": "Mapping negative probes",
            "status": accepted_mapping_negative.get("result", accepted_mapping_negative.get("status")),
            "artifact": args.accepted_mapping_negative_probes.as_posix(),
        },
        {
            "id": "p8.12-non-applied-proposal",
            "label": "Non-applied evidence proposal",
            "status": proposal.get("applicationStatus"),
            "artifact": args.proposal.as_posix(),
        },
        {
            "id": "p8.13-proposal-negative-probes",
            "label": "Proposal negative probes",
            "status": proposal_negative.get("result", proposal_negative.get("status")),
            "artifact": args.proposal_negative_probes.as_posix(),
        },
        {
            "id": "p8.15-sandboxed-build",
            "label": "Sandboxed build evidence",
            "status": build_evidence.get("result"),
            "artifact": args.build_evidence.as_posix(),
        },
        {
            "id": "p8.17-sandboxed-ui-launch",
            "label": "Sandboxed UI launch evidence",
            "status": ui_launch.get("result"),
            "artifact": args.ui_launch_evidence.as_posix(),
        },
        {
            "id": "p8.19-sandboxed-screenshot",
            "label": "Sandboxed screenshot evidence",
            "status": screenshot.get("result"),
            "artifact": args.screenshot_evidence.as_posix(),
        },
        {
            "id": "p8.21-workbench-projection",
            "label": "Workbench projection",
            "status": "emitted",
            "artifact": args.projection_out.as_posix(),
        },
    ]

    evidence_cards = [
        {
            "id": "evidence.p8.15-sandboxed-build",
            "kind": "sandboxed-build",
            "result": build_evidence.get("result"),
            "exitCode": build_evidence.get("build", {}).get("exitCode"),
            "warningCount": build_evidence.get("build", {}).get("warningCount"),
            "errorCount": build_evidence.get("build", {}).get("errorCount"),
            "log": build_evidence.get("build", {}).get("log"),
            "targetBefore": build_evidence.get("targetBefore"),
            "targetAfter": build_evidence.get("targetAfter"),
        },
        {
            "id": "evidence.p8.17-sandboxed-ui-launch",
            "kind": "sandboxed-ui-launch",
            "result": ui_launch.get("result"),
            "mainWindowTitle": ui_launch.get("uiLaunch", {}).get("processObservation", {}).get("mainWindowTitle"),
            "processResponding": ui_launch.get("uiLaunch", {}).get("processObservation", {}).get("responding"),
            "termination": ui_launch.get("uiLaunch", {}).get("termination"),
            "targetBefore": ui_launch.get("targetBefore"),
            "targetAfter": ui_launch.get("targetAfter"),
        },
        {
            "id": "evidence.p8.19-sandboxed-screenshot",
            "kind": "sandboxed-screenshot",
            "result": screenshot.get("result"),
            "mainWindowTitle": ui_observation.get("mainWindowTitle"),
            "screenshotPath": args.screenshot_png.as_posix(),
            "width": screenshot_evidence.get("width"),
            "height": screenshot_evidence.get("height"),
            "byteLength": screenshot_evidence.get("byteLength"),
            "sha256": screenshot_evidence.get("sha256"),
            "validPng": screenshot_evidence.get("validPng"),
            "targetBefore": screenshot.get("targetBefore"),
            "targetAfter": screenshot.get("targetAfter"),
        },
    ]

    selection_records = [
        {
            "id": mapping.get("id"),
            "kind": "accepted-mapping",
            "title": "Shell/workspace accepted mapping",
            "status": mapping.get("mappingStatus"),
            "details": {
                "intentUnitId": mapping.get("intentUnitId"),
                "codeSurfaceRefs": mapping.get("codeSurfaceRefs", []),
                "evidenceRequirements": mapping.get("evidenceRequirements", []),
                "authorityRequirements": mapping.get("authorityRequirements", []),
            },
        },
        {
            "id": proposal.get("proposalId"),
            "kind": "non-applied-proposal",
            "title": "Shell/workspace smoke evidence proposal",
            "status": proposal.get("applicationStatus"),
            "details": {
                "proposalMode": proposal.get("proposalMode"),
                "summary": proposal.get("summary"),
                "sourcePatchExpected": proposal_delta.get("sourcePatchExpected"),
                "plannedSourceChangeCount": len(proposal_delta.get("plannedSourceChanges", [])),
            },
        },
        *[
            {
                "id": card["id"],
                "kind": card["kind"],
                "title": card["kind"].replace("-", " ").title(),
                "status": as_status(card.get("result")),
                "details": card,
            }
            for card in evidence_cards
        ],
        {
            "id": "authority.boundary.p8.21",
            "kind": "authority-boundary",
            "title": "No write, apply, AI, hardware, or productization authority",
            "status": "blocked",
            "details": authority_boundary,
        },
    ]

    return {
        "artifactRole": "intentgraph-windowsutility-workbench-projection",
        "status": "intentgraph-windowsutility-workbench-projection-emitted",
        "scope": "p8.21-shell-workspace-evidence-workbench-static-preview",
        "reportVersion": REPORT_VERSION,
        "workItem": WORK_ITEM,
        "target": {
            "id": target.get("id"),
            "path": target.get("path"),
            "baselineHead": target.get("head"),
            "baselineOriginMain": target.get("originMain"),
            "baselineStatus": target.get("baselineStatus"),
            "current": current_target,
        },
        "mapping": {
            "id": mapping.get("id"),
            "intentUnitId": mapping.get("intentUnitId"),
            "status": mapping.get("mappingStatus"),
            "accepted": mapping.get("accepted"),
            "codeSurfaceRefs": mapping.get("codeSurfaceRefs", []),
            "ambiguityDisposition": mapping.get("ambiguityDisposition", []),
            "evidenceRequirements": mapping.get("evidenceRequirements", []),
            "authorityRequirements": mapping.get("authorityRequirements", []),
        },
        "proposal": {
            "id": proposal.get("proposalId"),
            "class": proposal.get("proposalClass"),
            "mode": proposal.get("proposalMode"),
            "applicationStatus": proposal.get("applicationStatus"),
            "summary": proposal.get("summary"),
            "sourcePatchExpected": proposal_delta.get("sourcePatchExpected"),
            "plannedSourceChangeCount": len(proposal_delta.get("plannedSourceChanges", [])),
            "requiredEvidenceCount": len(proposal.get("requiredEvidence", [])),
            "requiredAuthorityCount": len(proposal.get("requiredAuthority", [])),
            "validationResult": proposal_validation.get("result"),
        },
        "workflowTimeline": workflow_timeline,
        "evidence": evidence_cards,
        "authorityBoundary": authority_boundary,
        "sourceArtifacts": source_artifacts,
        "selectionRecords": selection_records,
        "summary": {
            "timelineStepCount": len(workflow_timeline),
            "evidenceCardCount": len(evidence_cards),
            "sourceArtifactCount": len(source_artifacts),
            "selectionRecordCount": len(selection_records),
            "acceptedCodeSurfaceRefCount": len(mapping.get("codeSurfaceRefs", [])),
            "allEvidencePassed": all(card.get("result") == "pass" for card in evidence_cards),
            "proposalNonApplied": proposal.get("applicationStatus") == "not-applied",
            "targetUnchangedInEvidence": screenshot.get("targetBefore") == screenshot.get("targetAfter"),
        },
        "claimScope": {
            "projectionOnly": True,
            "visualizationVerifiesCorrectness": False,
            "sourceMutated": False,
            "targetMutated": False,
            "patchApplied": False,
            "proposalAcceptedByProjection": False,
            "newEvidenceCollected": False,
            "aiAuthorityGranted": False,
            "hardwareActionClaimed": False,
            "productizationClaimed": False,
        },
    }


def escape_html(value: Any) -> str:
    text = str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def render_html(projection: dict[str, Any], screenshot_png: Path) -> str:
    data = json.dumps(projection, sort_keys=True, ensure_ascii=False).replace("</", "<\\/")
    screenshot_src = "../" + screenshot_png.name
    title = "WindowsUtility Evidence Workbench"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    :root {{
      --ink: #111827;
      --muted: #5f6b7a;
      --canvas: #f5f6f8;
      --surface: #ffffff;
      --surface-quiet: #fafbfc;
      --line: #d9dee7;
      --accent: #2563eb;
      --ok: #0f7a4f;
      --warn: #9a6700;
      --blocked: #8a2d22;
      --code: #24303c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ink);
      background: var(--canvas);
      letter-spacing: 0;
    }}
    .shell {{
      display: grid;
      grid-template-columns: 280px minmax(0, 1fr) 380px;
      min-height: 100vh;
    }}
    nav {{
      padding: 20px 16px;
      background: var(--surface-quiet);
      border-right: 1px solid var(--line);
    }}
    main {{
      padding: 20px;
      min-width: 0;
    }}
    aside {{
      padding: 20px;
      background: var(--surface-quiet);
      border-left: 1px solid var(--line);
      overflow: auto;
    }}
    h1 {{ font-size: 20px; line-height: 1.2; margin: 0 0 6px; }}
    h2 {{ font-size: 12px; text-transform: uppercase; color: var(--muted); margin: 24px 0 9px; }}
    h3 {{ font-size: 15px; margin: 0 0 10px; }}
    p {{ color: var(--muted); line-height: 1.45; margin: 0 0 12px; }}
    button {{
      font: inherit;
    }}
    .nav-item, .record {{
      width: 100%;
      min-height: 38px;
      border: 1px solid var(--line);
      background: var(--surface);
      color: var(--ink);
      border-radius: 6px;
      padding: 9px 10px;
      margin-bottom: 8px;
      text-align: left;
      cursor: pointer;
    }}
    .nav-item.active, .record.active {{
      border-color: var(--accent);
      box-shadow: inset 0 0 0 1px var(--accent);
    }}
    .panel {{
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      min-width: 0;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 12px;
    }}
    .two {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
      gap: 12px;
    }}
    .timeline {{
      display: grid;
      gap: 8px;
    }}
    .step {{
      display: grid;
      grid-template-columns: minmax(0, 1fr) auto;
      gap: 12px;
      align-items: center;
      padding: 8px 0;
      border-bottom: 1px solid var(--line);
    }}
    .status {{
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 8px;
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
      background: var(--surface);
    }}
    .status.pass, .status.accepted, .status.emitted, .status.recorded {{
      color: var(--ok);
      border-color: #b8dec9;
      background: #f0fbf5;
    }}
    .status.not-applied {{
      color: var(--warn);
      border-color: #e7d39b;
      background: #fff9e8;
    }}
    .status.blocked {{
      color: var(--blocked);
      border-color: #e3b9b4;
      background: #fff3f1;
    }}
    .metric {{
      font-size: 24px;
      font-weight: 650;
      margin-bottom: 3px;
    }}
    .shot {{
      width: 100%;
      max-height: 430px;
      object-fit: contain;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #111827;
    }}
    .artifact-list {{
      display: grid;
      gap: 8px;
    }}
    .artifact {{
      display: grid;
      gap: 4px;
      padding: 9px 0;
      border-bottom: 1px solid var(--line);
    }}
    code, pre {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      color: var(--code);
      font-size: 12px;
    }}
    pre {{
      margin: 0;
      white-space: pre-wrap;
      word-break: break-word;
      background: #f1f3f6;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 10px;
      max-height: 54vh;
      overflow: auto;
    }}
    @media (max-width: 1080px) {{
      .shell {{ grid-template-columns: 1fr; }}
      nav, aside {{ border-left: 0; border-right: 0; border-bottom: 1px solid var(--line); }}
      .grid, .two {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <nav>
      <h1>WindowsUtility Evidence Workbench</h1>
      <p>Projection-only view for the accepted shell/workspace mapping and sandbox evidence.</p>
      <h2>Sections</h2>
      <button class="nav-item active" data-section="overview">Overview</button>
      <button class="nav-item" data-section="timeline">Timeline</button>
      <button class="nav-item" data-section="evidence">Evidence</button>
      <button class="nav-item" data-section="screenshot">Screenshot</button>
      <button class="nav-item" data-section="authority">Authority</button>
      <button class="nav-item" data-section="artifacts">Artifacts</button>
    </nav>
    <main id="section"></main>
    <aside>
      <h2>Selection</h2>
      <div id="records"></div>
      <h2>Details</h2>
      <pre id="details"></pre>
    </aside>
  </div>
  <script id="workbench-data" type="application/json">{data}</script>
  <script>
    const projection = JSON.parse(document.getElementById('workbench-data').textContent);
    const section = document.getElementById('section');
    const records = document.getElementById('records');
    const details = document.getElementById('details');
    const screenshotSrc = "{escape_html(screenshot_src)}";

    function html(value) {{
      return String(value ?? '').replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
    }}
    function badge(value) {{
      const text = String(value ?? 'unknown');
      return `<span class="status ${{html(text)}}">${{html(text)}}</span>`;
    }}
    function metric(label, value) {{
      return `<div class="panel"><div class="metric">${{html(value)}}</div><p>${{html(label)}}</p></div>`;
    }}
    function renderOverview() {{
      section.innerHTML = `
        <div class="panel">
          <h3>${{html(projection.workItem)}}</h3>
          <p>${{html(projection.proposal.summary)}}</p>
          <div class="grid">
            ${{metric('Timeline steps', projection.summary.timelineStepCount)}}
            ${{metric('Evidence cards', projection.summary.evidenceCardCount)}}
            ${{metric('Artifacts linked', projection.summary.sourceArtifactCount)}}
          </div>
        </div>
        <h2>Current target</h2>
        <div class="two">
          <div class="panel"><h3>Baseline</h3><pre>${{html(JSON.stringify(projection.target, null, 2))}}</pre></div>
          <div class="panel"><h3>Claim scope</h3><pre>${{html(JSON.stringify(projection.claimScope, null, 2))}}</pre></div>
        </div>`;
    }}
    function renderTimeline() {{
      section.innerHTML = `<div class="panel"><h3>Workflow timeline</h3><div class="timeline">${{projection.workflowTimeline.map(step => `<div class="step"><div><strong>${{html(step.label)}}</strong><br><code>${{html(step.artifact)}}</code></div>${{badge(step.status)}}</div>`).join('')}}</div></div>`;
    }}
    function renderEvidence() {{
      section.innerHTML = `<div class="grid">${{projection.evidence.map(card => `<div class="panel"><h3>${{html(card.kind)}}</h3>${{badge(card.result)}}<pre>${{html(JSON.stringify(card, null, 2))}}</pre></div>`).join('')}}</div>`;
    }}
    function renderScreenshot() {{
      const shot = projection.evidence.find(card => card.kind === 'sandboxed-screenshot') || {{}};
      section.innerHTML = `<div class="panel"><h3>Sandboxed window screenshot</h3><p>${{html(shot.width)}} x ${{html(shot.height)}} / ${{html(shot.byteLength)}} bytes</p><img class="shot" src="${{screenshotSrc}}" alt="Sandboxed WindowsUtility shell screenshot"><h2>Screenshot evidence</h2><pre>${{html(JSON.stringify(shot, null, 2))}}</pre></div>`;
    }}
    function renderAuthority() {{
      section.innerHTML = `<div class="panel"><h3>Authority and safety boundary</h3><p>Projection state is not acceptance, write authority, hardware authority, or productization.</p><pre>${{html(JSON.stringify(projection.authorityBoundary, null, 2))}}</pre></div>`;
    }}
    function renderArtifacts() {{
      section.innerHTML = `<div class="panel"><h3>Source artifacts</h3><div class="artifact-list">${{projection.sourceArtifacts.map(item => `<div class="artifact"><strong>${{html(item.path)}}</strong><code>${{html(item.sha256)}}</code><span>${{html(item.status || item.result || item.artifactRole || 'artifact')}}</span></div>`).join('')}}</div></div>`;
    }}
    const renderers = {{
      overview: renderOverview,
      timeline: renderTimeline,
      evidence: renderEvidence,
      screenshot: renderScreenshot,
      authority: renderAuthority,
      artifacts: renderArtifacts
    }};
    document.querySelectorAll('.nav-item').forEach(button => {{
      button.addEventListener('click', () => {{
        document.querySelectorAll('.nav-item').forEach(item => item.classList.remove('active'));
        button.classList.add('active');
        renderers[button.dataset.section]();
      }});
    }});
    projection.selectionRecords.forEach((record, index) => {{
      const button = document.createElement('button');
      button.className = 'record' + (index === 0 ? ' active' : '');
      button.textContent = `${{record.kind}} - ${{record.id}}`;
      button.addEventListener('click', () => {{
        document.querySelectorAll('.record').forEach(item => item.classList.remove('active'));
        button.classList.add('active');
        details.textContent = JSON.stringify(record, null, 2);
      }});
      records.appendChild(button);
    }});
    renderOverview();
    details.textContent = JSON.stringify(projection.selectionRecords[0] || projection, null, 2);
  </script>
</body>
</html>
"""


def validate_projection(projection: dict[str, Any], html_path: Path, screenshot_png: Path) -> dict[str, Any]:
    errors: list[str] = []
    if projection.get("artifactRole") != "intentgraph-windowsutility-workbench-projection":
        errors.append("wrong projection artifactRole")
    if projection.get("status") != "intentgraph-windowsutility-workbench-projection-emitted":
        errors.append("wrong projection status")
    if projection.get("mapping", {}).get("accepted") is not True:
        errors.append("accepted mapping must be visible and accepted")
    if projection.get("proposal", {}).get("applicationStatus") != "not-applied":
        errors.append("proposal must remain not-applied")
    if not projection.get("summary", {}).get("allEvidencePassed"):
        errors.append("all linked evidence cards must pass")
    if not projection.get("summary", {}).get("targetUnchangedInEvidence"):
        errors.append("target evidence before/after must match")
    current = projection.get("target", {}).get("current", {})
    if current.get("status") != "## main...origin/main":
        errors.append("current WindowsUtility target must be clean/aligned")
    if current.get("head") != current.get("originMain"):
        errors.append("current WindowsUtility HEAD must match origin/main")
    for key, value in projection.get("authorityBoundary", {}).items():
        if value is not False:
            errors.append(f"authorityBoundary.{key} must be false")
    claim_scope = projection.get("claimScope", {})
    for key in [
        "visualizationVerifiesCorrectness",
        "sourceMutated",
        "targetMutated",
        "patchApplied",
        "proposalAcceptedByProjection",
        "newEvidenceCollected",
        "aiAuthorityGranted",
        "hardwareActionClaimed",
        "productizationClaimed",
    ]:
        if claim_scope.get(key) is not False:
            errors.append(f"claimScope.{key} must be false")
    if claim_scope.get("projectionOnly") is not True:
        errors.append("claimScope.projectionOnly must be true")
    if not screenshot_png.exists():
        errors.append("screenshot PNG missing")
    if not html_path.exists():
        errors.append("html preview missing")
        html_text = ""
    else:
        html_text = html_path.read_text(encoding="utf-8")
    for marker in [
        "WindowsUtility Evidence Workbench",
        "workbench-data",
        "Workflow timeline",
        "Authority and safety boundary",
        "Sandboxed window screenshot",
    ]:
        if marker not in html_text:
            errors.append(f"html preview missing marker {marker}")
    if len(projection.get("selectionRecords", [])) < 5:
        errors.append("projection must expose at least five selection records")
    return {
        "artifactRole": "intentgraph-windowsutility-workbench-validation-report",
        "status": "intentgraph-windowsutility-workbench-validation-passed" if not errors else "intentgraph-windowsutility-workbench-validation-failed",
        "scope": "p8.21-shell-workspace-evidence-workbench-validation",
        "workItem": WORK_ITEM,
        "result": "pass" if not errors else "fail",
        "summary": {
            "timelineStepCount": len(projection.get("workflowTimeline", [])),
            "evidenceCardCount": len(projection.get("evidence", [])),
            "sourceArtifactCount": len(projection.get("sourceArtifacts", [])),
            "selectionRecordCount": len(projection.get("selectionRecords", [])),
            "htmlExists": html_path.exists(),
            "screenshotExists": screenshot_png.exists(),
            "errorCount": len(errors),
        },
        "claimScope": claim_scope,
        "errors": errors,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit WindowsUtility evidence workbench projection and static HTML.")
    parser.add_argument("--accepted-mapping", required=True, type=Path)
    parser.add_argument("--accepted-mapping-verification", required=True, type=Path)
    parser.add_argument("--accepted-mapping-negative-probes", required=True, type=Path)
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--proposal-validation", required=True, type=Path)
    parser.add_argument("--proposal-negative-probes", required=True, type=Path)
    parser.add_argument("--build-evidence", required=True, type=Path)
    parser.add_argument("--ui-launch-evidence", required=True, type=Path)
    parser.add_argument("--screenshot-evidence", required=True, type=Path)
    parser.add_argument("--screenshot-png", required=True, type=Path)
    parser.add_argument("--target-root", required=True, type=Path)
    parser.add_argument("--projection-out", required=True, type=Path)
    parser.add_argument("--html-out", required=True, type=Path)
    parser.add_argument("--validation-out", required=True, type=Path)
    args = parser.parse_args()

    current_target = git_state(args.target_root)
    projection = build_projection(args, current_target)
    write_json(args.projection_out, projection)
    args.html_out.parent.mkdir(parents=True, exist_ok=True)
    args.html_out.write_text(render_html(projection, args.screenshot_png), encoding="utf-8")
    validation = validate_projection(projection, args.html_out, args.screenshot_png)
    write_json(args.validation_out, validation)
    return 0 if validation["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
