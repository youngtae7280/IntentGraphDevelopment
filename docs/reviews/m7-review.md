# M7 Milestone Review

Milestone: M7 - Workbench and Visualization Boundary
Date: 2026-07-09
Reviewer: IntentGraphDevelopment Roadmap Orchestrator

Declared quality target: Level 2 or higher

## Produced Artifacts

- `docs/workbench/workbench-boundary.md`
- `docs/workbench/visualization-requirements.md`
- `docs/workbench/graph-navigation-model.md`
- `tools/emit_workbench_projection.py`
- `generated/b0-python-cli-calculator/workbench-projection.json`
- `docs/reviews/m7-review.md`

## Benchmarks Run

Commands run:

```powershell
python tools/emit_workbench_projection.py --graph docs/examples/b0-python-cli-calculator.graph.json --roundtrip generated/b0-python-cli-calculator/roundtrip-report.json --proposals generated/b0-python-cli-calculator/proposal-validation-report.json --out generated/b0-python-cli-calculator/workbench-projection.json
python -m py_compile tools/emit_workbench_projection.py
python -m json.tool generated/b0-python-cli-calculator/workbench-projection.json > $null
```

Projection report summary:

```text
projectionKind = workbench-report
authorityDisclaimer = This projection is a report. It is not accepted graph authority.
roundTrip.result = pass
roundTrip.semanticValidation = pass
proposalValidation.result = pass
proposalValidation.aiOutputTreatedAsAuthority = false
proposalValidation.automaticApplication = false
diagram.authority = orientation-only
inputConsistency.result = pass
```

Negative visibility check:

- a tampered round-trip report with `result = fail` was emitted into the projection as failing, not hidden
- a tampered graph/report digest mismatch fails projection input consistency

## Prior-Art Comparison

M7 compared against:

- Eclipse Sirius
- Cytoscape.js
- Graphviz
- D3
- Mermaid
- React Flow
- Sourcegraph / SCIP / Kythe / Glean / LSIF / SemanticDB for code navigation pressure
- Graphify / RepoGraph for repository context visualization pressure

Decision:

- do not build a full IDE or modeling workbench in Phase 0
- learn from Sirius but avoid EMF/modeling-workbench scope
- integrate or borrow visualization libraries later if Phase 1 needs interaction
- use a static JSON projection report for Phase 0
- keep Mermaid-style diagram output orientation-only
- do not build code navigation or AI context visualization in Phase 0

## Result

Proved for the B0 slice:

- a workbench projection can summarize graph, round-trip, evidence, authority, history, and proposal state
- projection inputs are consistency-checked against graph digest and benchmark ID
- navigation indexes can be emitted without making UI state authoritative
- `edgesByKind` and node/edge navigation indexes are present
- the projection keeps code-only, AI proposal, and authority boundaries visible
- preservation metadata scope, code-only loss model, and domain-subgraph preservation state are visible
- the diagram is explicitly orientation-only and status labels are derived from reports
- failing verifier state is projected as failing rather than masked by the workbench report

Changed:

- M7 adds a bounded workbench projection artifact but no IDE
- M7 moves Phase 0 from milestone implementation to quality saturation review

## Round-Trip Status

The projection consumes the M5/M6 reports. It does not perform equality itself and does not replace the verifier.

## Evidence Status

Evidence state is displayed from the round-trip report:

- accepted evidence count
- accepted authority count
- accepted history count
- verified Git commit count
- current-milestone pending history count

The projection does not accept evidence.

## Authority Status

Authority state is displayed and disclaimed:

```text
This projection is a report. It is not accepted graph authority.
```

The projection does not grant authority and does not apply proposals.

## Issue Review

| ID | Severity | Issue | Resolution |
|---|---|---|---|
| M7-P2-001 | P2 | A workbench prototype could imply a premature IDE direction. | Resolved by emitting a static projection report only and documenting full IDE/workbench as out of Phase 0 scope. |
| M7-P2-002 | P2 | Visualization could be mistaken for authority. | Resolved with required authority disclaimer and `diagram.authority = orientation-only`. |
| M7-P2-003 | P2 | A projection could hide verifier failures behind summarized UI state. | Resolved by projecting raw pass/fail fields and validating a tampered failing report remains visible as failing. |
| M7-P1-001 | P1 | Projection could combine a tampered/stale graph with passing reports. | Resolved by enforcing graph/report digest and benchmark consistency before emitting the projection. |
| M7-P1-002 | P1 | Diagram labels hardcoded `pass` and could mask failure. | Resolved by deriving diagram labels from round-trip, semantic, proposal, and input consistency status. |
| M7-P1-003 | P1 | Required navigation index `edgesByKind` was missing. | Resolved by adding edge ID lists by kind. |
| M7-P1-004 | P1 | M7 promotion was premature while projection P1s existed. | Resolved by keeping M7 current until projection hardening and red-team probes passed. |
| M7-P2-004 | P2 | Preservation/code-only boundary was too thin in the projection. | Resolved by projecting M5 claim scope, metadata digest, code-only loss model, and domain-subgraph match state. |
| M7-P2-005 | P2 | Prior-art comparison was mostly a name list. | Resolved with a compact prior-art pressure matrix covering workbench, graph rendering, code navigation, status dashboards, and AI context visualization. |
| M7-P3-001 | P3 | Workbench action recurrence stopped before apply/typecheck/verify. | Resolved by extending the recurrence through `Apply(G, Delta) -> TypeCheck/Verify`. |

No unresolved P0/P1 issues remain. All P2 issues are resolved.

## Decision

Decision: continue to Phase 0 Quality Saturation Review

Achieved quality level: Level 2+.

M7 passes its declared quality bar.

## Required Changes Before Phase 0 Final Review

Phase 0 Quality Saturation Review must:

- re-check M0 through M7
- compare against prior art again
- rerun red-team critique
- identify weak assumptions
- fix deficiencies inside approved scope
- write Phase 0 Final Review with continue, pivot, narrow, or stop recommendation
