"""Emit a B1 workbench projection JSON and static HTML preview."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


BENCHMARK_ID = "B1-typescript-rest-api"
REPORT_VERSION = "0.1.0"


def canonical_pretty(data: Any) -> str:
    return json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def read_json(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return data


def index_by_id(items: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(items, list):
        return {}
    return {item["id"]: item for item in items if isinstance(item, dict) and isinstance(item.get("id"), str)}


def build_projection(
    proposal: dict[str, Any],
    proposal_validation: dict[str, Any],
    consistency: dict[str, Any],
    code_facts: dict[str, Any],
    overlay: dict[str, Any],
) -> dict[str, Any]:
    units = overlay.get("intentUnits", [])
    facts = code_facts.get("facts", [])
    impact_files = proposal.get("impactScope", {}).get("allowedSourceFiles", [])
    existing_units = proposal.get("impactScope", {}).get("existingIntentUnitIds", [])
    proposed_units = proposal.get("deltaI", {}).get("proposedIntentUnits", [])
    planned_changes = proposal.get("deltaC", {}).get("plannedSourceChanges", [])
    mapping_updates = proposal.get("deltaM", {}).get("mappingUpdates", [])
    required_tests = proposal.get("requiredTests", [])
    required_evidence = proposal.get("requiredEvidence", [])
    required_authority = proposal.get("requiredAuthority", [])

    fact_index = index_by_id(facts)
    unit_index = index_by_id(units)
    impacted_fact_ids = sorted(
        {
            fact_id
            for update in mapping_updates
            for fact_id in update.get("existingCodeFactIds", [])
            if fact_id in fact_index
        }
    )

    selection_records: list[dict[str, Any]] = []
    for unit_id in existing_units:
        unit = unit_index.get(unit_id, {})
        selection_records.append(
            {
                "id": unit_id,
                "kind": "existing-intent-unit",
                "title": unit.get("title", unit_id),
                "status": unit.get("mappingStatus", "unknown"),
                "details": {
                    "codeRefs": len(unit.get("codeRefs", [])),
                    "codeFactRefs": len(unit.get("codeFactRefs", [])),
                    "mappingObligations": len(unit.get("mappingObligations", [])),
                },
            }
        )
    for unit in proposed_units:
        selection_records.append(
            {
                "id": unit.get("id"),
                "kind": "proposed-intent-unit",
                "title": unit.get("title"),
                "status": unit.get("mappingStatus"),
                "details": {"accepted": unit.get("accepted")},
            }
        )
    for fact_id in impacted_fact_ids:
        fact = fact_index[fact_id]
        selection_records.append(
            {
                "id": fact_id,
                "kind": f"code-fact:{fact.get('kind')}",
                "title": fact.get("symbol") or fact.get("id"),
                "status": "existing",
                "details": {
                    "sourceFile": fact.get("sourceFile"),
                    "confidence": fact.get("confidence"),
                    "sourceDigest": fact.get("sourceDigest"),
                },
            }
        )
    for change in planned_changes:
        selection_records.append(
            {
                "id": change.get("id"),
                "kind": "planned-source-change",
                "title": change.get("operation"),
                "status": "not-applied" if change.get("applied") is False else "unknown",
                "details": {key: value for key, value in change.items() if key != "id"},
            }
        )

    return {
        "artifactRole": "intentgraph-b1-workbench-projection",
        "status": "intentgraph-b1-workbench-projection-emitted",
        "scope": "b1-typescript-rest-api-workbench-projection-static-preview",
        "reportVersion": REPORT_VERSION,
        "benchmarkId": BENCHMARK_ID,
        "proposal": {
            "id": proposal.get("proposalId"),
            "summary": proposal.get("summary"),
            "mode": proposal.get("proposalMode"),
            "applicationStatus": proposal.get("applicationStatus"),
        },
        "workflowTimeline": [
            {"id": "baseline", "label": "Baseline", "status": "bound"},
            {"id": "mapping", "label": "Intent mapping", "status": "verified"},
            {"id": "proposal", "label": "Proposal", "status": proposal.get("applicationStatus")},
            {"id": "proposal-validation", "label": "Proposal validation", "status": proposal_validation.get("result")},
            {"id": "consistency", "label": "Consistency verifier", "status": consistency.get("result")},
        ],
        "impact": {
            "sourceFiles": impact_files,
            "existingIntentUnitIds": existing_units,
            "proposedIntentUnitIds": [unit.get("id") for unit in proposed_units],
            "existingCodeFactIds": impacted_fact_ids,
        },
        "plannedDeltas": {
            "deltaC": planned_changes,
            "deltaI": proposed_units,
            "deltaM": mapping_updates,
        },
        "requirements": {
            "tests": required_tests,
            "evidence": required_evidence,
            "authority": required_authority,
        },
        "verifierStatus": {
            "proposalValidation": proposal_validation.get("result"),
            "proposalConsistency": consistency.get("result"),
            "proposalValidationErrors": proposal_validation.get("errors", []),
            "proposalConsistencyErrors": consistency.get("errors", []),
        },
        "selectionRecords": selection_records,
        "summary": {
            "intentUnitCount": len(units),
            "codeFactCount": len(facts),
            "selectionRecordCount": len(selection_records),
            "plannedSourceChangeCount": len(planned_changes),
            "requiredTestCount": len(required_tests),
            "requiredEvidenceCount": len(required_evidence),
            "requiredAuthorityCount": len(required_authority),
        },
        "claimScope": {
            "staticPreviewOnly": True,
            "visualizationVerifiesCorrectness": False,
            "sourceMutated": False,
            "patchApplied": False,
            "proposalAccepted": False,
            "productized": False,
        },
    }


def render_html(projection: dict[str, Any]) -> str:
    data = json.dumps(projection, sort_keys=True, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>B1 IntentGraph Workbench Preview</title>
  <style>
    :root {{
      --ig-ink: #17202a;
      --ig-muted: #5f6c7b;
      --ig-canvas: #f6f7f9;
      --ig-panel: #ffffff;
      --ig-line: #d9dee7;
      --ig-accent: #2563eb;
      --ig-success: #16794c;
      --ig-warning: #996d00;
      --ig-danger: #b42318;
      --ig-code: #263238;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      color: var(--ig-ink);
      background: var(--ig-canvas);
      letter-spacing: 0;
    }}
    .shell {{
      display: grid;
      grid-template-columns: 260px minmax(0, 1fr) 360px;
      min-height: 100vh;
    }}
    nav {{
      border-right: 1px solid var(--ig-line);
      background: #f9fafb;
      padding: 20px 16px;
    }}
    main {{ padding: 22px; min-width: 0; }}
    aside {{
      border-left: 1px solid var(--ig-line);
      background: #fbfcfd;
      padding: 20px;
      overflow: auto;
    }}
    h1 {{ font-size: 20px; line-height: 1.2; margin: 0 0 6px; }}
    h2 {{ font-size: 13px; text-transform: uppercase; color: var(--ig-muted); margin: 26px 0 10px; }}
    h3 {{ font-size: 15px; margin: 0 0 10px; }}
    p {{ color: var(--ig-muted); line-height: 1.45; }}
    .nav-item, .record {{
      width: 100%;
      text-align: left;
      border: 1px solid var(--ig-line);
      background: var(--ig-panel);
      color: var(--ig-ink);
      border-radius: 6px;
      padding: 10px 11px;
      margin-bottom: 8px;
      cursor: pointer;
      font: inherit;
    }}
    .nav-item.active, .record.active {{ border-color: var(--ig-accent); box-shadow: inset 0 0 0 1px var(--ig-accent); }}
    .grid {{ display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }}
    .panel {{
      background: var(--ig-panel);
      border: 1px solid var(--ig-line);
      border-radius: 8px;
      padding: 14px;
      min-width: 0;
    }}
    .status {{
      display: inline-flex;
      align-items: center;
      min-height: 22px;
      border-radius: 999px;
      padding: 2px 8px;
      font-size: 12px;
      border: 1px solid var(--ig-line);
      color: var(--ig-muted);
      background: #fff;
    }}
    .status.pass, .status.verified, .status.bound {{ color: var(--ig-success); border-color: #b7dfca; background: #f0fbf5; }}
    .status.not-applied, .status.planned {{ color: var(--ig-warning); border-color: #ead59a; background: #fff9e6; }}
    .metric {{ font-size: 24px; font-weight: 650; margin: 4px 0; }}
    .list {{ display: grid; gap: 8px; }}
    code, pre {{
      font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
      color: var(--ig-code);
      font-size: 12px;
    }}
    pre {{
      white-space: pre-wrap;
      word-break: break-word;
      background: #f3f5f7;
      border: 1px solid var(--ig-line);
      border-radius: 6px;
      padding: 10px;
      max-height: 48vh;
      overflow: auto;
    }}
    .timeline {{ display: grid; gap: 10px; }}
    .timeline-step {{ display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--ig-line); padding-bottom: 8px; }}
    @media (max-width: 980px) {{
      .shell {{ grid-template-columns: 1fr; }}
      nav, aside {{ border: 0; border-bottom: 1px solid var(--ig-line); }}
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <div class="shell">
    <nav>
      <h1>IntentGraph B1</h1>
      <p>Static workbench preview for a non-applied change proposal.</p>
      <h2>Sections</h2>
      <button class="nav-item active" data-section="overview">Overview</button>
      <button class="nav-item" data-section="impact">Impact</button>
      <button class="nav-item" data-section="deltas">Planned Deltas</button>
      <button class="nav-item" data-section="requirements">Requirements</button>
      <button class="nav-item" data-section="verifier">Verifier</button>
    </nav>
    <main>
      <section id="section"></section>
    </main>
    <aside>
      <h2>Selection</h2>
      <div id="records" class="list"></div>
      <h2>Details</h2>
      <pre id="details"></pre>
    </aside>
  </div>
  <script id="workbench-data" type="application/json">{data}</script>
  <script>
    const projection = JSON.parse(document.getElementById('workbench-data').textContent);
    const sectionEl = document.getElementById('section');
    const recordsEl = document.getElementById('records');
    const detailsEl = document.getElementById('details');

    function status(value) {{
      const text = String(value ?? 'unknown');
      return `<span class="status ${{text}}">${{text}}</span>`;
    }}
    function renderOverview() {{
      sectionEl.innerHTML = `
        <div class="panel">
          <h3>${{projection.proposal.id}}</h3>
          <p>${{projection.proposal.summary}}</p>
          <div class="timeline">${{projection.workflowTimeline.map(step => `<div class="timeline-step"><strong>${{step.label}}</strong>${{status(step.status)}}</div>`).join('')}}</div>
        </div>
        <h2>Counts</h2>
        <div class="grid">
          ${{metric('Intent units', projection.summary.intentUnitCount)}}
          ${{metric('Code facts', projection.summary.codeFactCount)}}
          ${{metric('Selectable records', projection.summary.selectionRecordCount)}}
        </div>`;
    }}
    function metric(label, value) {{
      return `<div class="panel"><div class="metric">${{value}}</div><p>${{label}}</p></div>`;
    }}
    function renderJson(title, data) {{
      sectionEl.innerHTML = `<div class="panel"><h3>${{title}}</h3><pre>${{escapeHtml(JSON.stringify(data, null, 2))}}</pre></div>`;
    }}
    function escapeHtml(value) {{
      return String(value).replace(/[&<>"']/g, ch => ({{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[ch]));
    }}
    const renderers = {{
      overview: renderOverview,
      impact: () => renderJson('Impact', projection.impact),
      deltas: () => renderJson('Planned Deltas', projection.plannedDeltas),
      requirements: () => renderJson('Requirements', projection.requirements),
      verifier: () => renderJson('Verifier Status', projection.verifierStatus)
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
      button.textContent = `${{record.kind}} · ${{record.id}}`;
      button.addEventListener('click', () => {{
        document.querySelectorAll('.record').forEach(item => item.classList.remove('active'));
        button.classList.add('active');
        detailsEl.textContent = JSON.stringify(record, null, 2);
      }});
      recordsEl.appendChild(button);
    }});
    renderOverview();
    detailsEl.textContent = JSON.stringify(projection.selectionRecords[0] || projection, null, 2);
  </script>
</body>
</html>
"""


def validate_projection(projection: dict[str, Any], html_path: Path) -> dict[str, Any]:
    errors: list[str] = []
    if projection.get("artifactRole") != "intentgraph-b1-workbench-projection":
        errors.append("wrong projection artifactRole")
    if projection.get("status") != "intentgraph-b1-workbench-projection-emitted":
        errors.append("wrong projection status")
    if not projection.get("selectionRecords"):
        errors.append("projection must contain selection records")
    if projection.get("verifierStatus", {}).get("proposalConsistency") != "pass":
        errors.append("proposal consistency must pass")
    claim_scope = projection.get("claimScope", {})
    if claim_scope.get("visualizationVerifiesCorrectness") is not False:
        errors.append("visualization must not claim correctness authority")
    if claim_scope.get("sourceMutated") is not False or claim_scope.get("patchApplied") is not False:
        errors.append("projection must not claim source mutation or patch application")
    if not html_path.exists():
        errors.append("html preview file missing")
        html_text = ""
    else:
        html_text = html_path.read_text(encoding="utf-8")
    for marker in ["IntentGraph B1", "workbench-data", "Selection", "Verifier"]:
        if marker not in html_text:
            errors.append(f"html preview missing marker {marker}")
    return {
        "artifactRole": "intentgraph-b1-workbench-validation-report",
        "status": "intentgraph-b1-workbench-validation-passed" if not errors else "intentgraph-b1-workbench-validation-failed",
        "scope": "b1-typescript-rest-api-workbench-validation",
        "benchmarkId": BENCHMARK_ID,
        "result": "pass" if not errors else "fail",
        "summary": {
            "selectionRecordCount": len(projection.get("selectionRecords", [])),
            "timelineStepCount": len(projection.get("workflowTimeline", [])),
            "htmlExists": html_path.exists(),
            "errorCount": len(errors),
        },
        "claimScope": projection.get("claimScope", {}),
        "errors": errors,
    }


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_pretty(data), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit B1 workbench projection and static HTML.")
    parser.add_argument("--proposal", required=True, type=Path)
    parser.add_argument("--proposal-validation", required=True, type=Path)
    parser.add_argument("--consistency", required=True, type=Path)
    parser.add_argument("--code-facts", required=True, type=Path)
    parser.add_argument("--overlay", required=True, type=Path)
    parser.add_argument("--projection-out", required=True, type=Path)
    parser.add_argument("--html-out", required=True, type=Path)
    parser.add_argument("--validation-out", required=True, type=Path)
    args = parser.parse_args()

    projection = build_projection(
        read_json(args.proposal),
        read_json(args.proposal_validation),
        read_json(args.consistency),
        read_json(args.code_facts),
        read_json(args.overlay),
    )
    write_json(args.projection_out, projection)
    args.html_out.parent.mkdir(parents=True, exist_ok=True)
    args.html_out.write_text(render_html(projection), encoding="utf-8")
    validation = validate_projection(projection, args.html_out)
    write_json(args.validation_out, validation)
    return 0 if validation["result"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
