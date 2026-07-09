# Phase 0 Final Review

Date: 2026-07-09
Reviewer: IntentGraphDevelopment Roadmap Orchestrator

Scope: `M0` through `M7`, regenerated B0 artifacts, prior-art pressure, red-team findings, and final saturation corrections.

Recommendation: continue to Phase 1.

Phase 1 is not automatically authorized by this review. Do not create `M8`. Start Phase 1 only after explicit user approval.

## Thesis Verdict

Phase 0 strengthens a limited generated-code feasibility slice:

```text
G -> Native(G) -> (C, mu) -> Retrofit(C, mu) -> G' -> Verify(G, G')
```

For `B0-python-cli-calculator`, the repository contains a graph, deterministic generated Python source, preservation metadata, reconstructed graph, round-trip verifier report, evidence/authority/history semantic validation, AI proposal validation, and a non-authoritative workbench projection.

P1.R further narrows the honest claim:

- exact reconstruction is metadata-backed and currently uses `mu.hiddenState.sourceGraphSnapshot`
- code-only reconstruction is lossy and is not used for exact equality
- generated code is not proof
- AI output is proposal data, not authority
- workbench visualization is a report/projection, not authority
- Git remains file history; IntentGraph adds semantic graph history
- source code remains the implementation source
- IntentGraph is a semantic overlay over code artifacts, not a source-code replacement
- graph-first generation is a limited mode, not the universal model

Result: the generated-code experiment is feasible for B0, but the broader thesis must be evaluated as overlay/code consistency and change orchestration for existing codebases.

## Acceptance Checklist

| Criterion | Result | Evidence |
|---|---|---|
| M0 through M7 have written reviews | Pass | [M0](m0-review.md), [M1](m1-review.md), [M2](m2-review.md), [M3](m3-review.md), [M4](m4-review.md), [M5](m5-review.md), [M6](m6-review.md), [M7](m7-review.md) |
| All milestone criteria passed | Pass | Reviews above plus regenerated B0 artifacts |
| No unresolved P0/P1 issues | Pass | Final red-team issues resolved or documented below |
| No P2 without decision | Pass | One new P2 defer is recorded in this review and [Change History Model](../history/change-history-model.md) |
| Benchmarks documented | Pass | [Benchmark Plan](../research/benchmark-plan.md), generated reports, and validation log below |
| Prior art re-checked | Pass | Prior-art pressure table below |
| Final review recommends continue, pivot, narrow, or stop | Pass | Recommendation: continue to Phase 1 |

## Fresh Validation

Commands rerun during final saturation:

```powershell
python tools\native_compile.py --graph docs\examples\b0-python-cli-calculator.graph.json --out generated\b0-python-cli-calculator
python tools\retrofit_reconstruct.py --source generated\b0-python-cli-calculator\calc.py --metadata generated\b0-python-cli-calculator\calc.intentgraph.json --out generated\b0-python-cli-calculator
python tools\verify_roundtrip.py --original docs\examples\b0-python-cli-calculator.graph.json --reconstructed generated\b0-python-cli-calculator\reconstructed.graph.json --metadata generated\b0-python-cli-calculator\calc.intentgraph.json --code-only generated\b0-python-cli-calculator\code-only-projection.json --out generated\b0-python-cli-calculator\roundtrip-report.json
python tools\validate_proposal.py --graph docs\examples\b0-python-cli-calculator.graph.json --proposal docs\proposals\b0-ai-add-invalid-operation-test.proposal.json --proposal docs\proposals\b0-ai-invalid-self-authorized.proposal.json --out generated\b0-python-cli-calculator\proposal-validation-report.json
python tools\emit_workbench_projection.py --graph docs\examples\b0-python-cli-calculator.graph.json --roundtrip generated\b0-python-cli-calculator\roundtrip-report.json --proposals generated\b0-python-cli-calculator\proposal-validation-report.json --out generated\b0-python-cli-calculator\workbench-projection.json
```

Additional validation:

- JSON parsing passed for graph, proposals, preservation metadata, reconstructed graph, diagnostics, verifier report, proposal report, and workbench projection.
- `py_compile` passed for all Phase 0 Python tools and generated `calc.py`.
- Runtime checks passed: `add 2 3 -> 5`, `sub 5 2 -> 3`, invalid operation exits `2`, invalid integer exits `2`.
- Report assertions passed: round-trip result `pass`, `graphEqual = true`, semantic validation `pass`, evidence accepted count `3`, AI final authority count `0`, Git verified count `1`, proposal validation `pass`, workbench input consistency `pass`.
- Declared-output determinism passed: rerunning the full pipeline at the declared generated paths produced identical tracked artifacts.
- Temp-output byte identity is not claimed; some reports intentionally embed output/input paths and current-run evidence resolution.
- Negative probes passed for tampered source, failing evidence, AI final authority, unsupported authority target, fake Git commit, history sequence gap, missing artifact reference, stale proposal digest, missing proposal authority record, stale workbench graph/report pairing, and failing verifier visibility in the workbench diagram.
- Documentation hygiene passed: `git diff --check`, tracked placeholder/broken-character scan, tracked non-ASCII scan, and local Markdown link check.

## Prior-Art Re-Check

No late prior-art discovery replaces the combined Phase 0 slice. Stronger systems still dominate individual lanes:

| Lane | Current pressure | Phase 0 decision |
|---|---|---|
| Language/workbench | [JetBrains MPS](https://www.jetbrains.com/mps/) and [Eclipse EMF](https://projects.eclipse.org/projects/modeling.emf) are stronger general language/modeling platforms. | Do not build a broad language workbench; keep GraphIR tiny. |
| Model/code generation | EMF/MDE and generator ecosystems pressure model-to-code claims. | Treat graph-first generation as a limited mode and avoid source-language overclaiming. |
| Bidirectional semantics | [Eclipse QVT Operational](https://projects.eclipse.org/projects/modeling.qvt-oml) and [eMoflon IBeX/TGG](https://emoflon.org/ibex/) pressure consistency semantics. | Keep explicit B0 equality/projection verifier; do not claim general BX. |
| Code facts | [CodeQL](https://codeql.github.com/docs/), [Joern](https://docs.joern.io/code-property-graph/), [Kythe](https://kythe.io/docs/schema/indexing-generated-code.html), and [Glean](https://glean.software/) are stronger extraction/indexing systems. | Treat code nodes as pointers/facts; borrow or compare before building extraction. |
| AI context graphs | [Graphify](https://graphify.net/) and [RepoGraph](https://arxiv.org/abs/2410.14684) pressure repository-context claims. | Treat AI context as proposal support, not authority. |
| Evidence/authority/history | [W3C PROV](https://www.w3.org/TR/prov-dm/), [OPA](https://openpolicyagent.org/docs), [SLSA](https://slsa.dev/), and [in-toto](https://in-toto.io/) are stronger generic provenance/policy/supply-chain systems. | Keep minimal IntentGraph binding; integrate or benchmark before broad policy/provenance work. |
| Visualization | [Sirius](https://eclipse.dev/sirius/doc/), [Cytoscape.js](https://js.cytoscape.org/), [Graphviz](https://graphviz.org/), [Mermaid](https://mermaid.js.org/), and [React Flow](https://reactflow.dev/) are stronger UI/graph tools. | Keep M7 as static projection report; no full IDE. |

## Red-Team Findings

| ID | Severity | Finding | Resolution |
|---|---|---|---|
| PHASE0-FINAL-P1-001 | P1 | Phase 0 Final Review was missing. | Resolved by this document. |
| PHASE0-FINAL-P1-002 | P1 | M3/M4 review wording overclaimed temp-output byte identity. | Resolved by clarifying declared-output determinism and temp path-bearing report limits in [M3](m3-review.md) and [M4](m4-review.md). |
| PHASE0-FINAL-P2-001 | P2 | B0 still has one accepted `pending-current-milestone` semantic history delta. | Explicitly deferred: self-referential commit finalization requires a Phase 1 strategy. The verifier reports the boundary and does not hide it. |

No unresolved P0/P1 issues remain. No P2 issue remains without a written resolution or defer decision.

## Deferred P2 Decisions

- `PHASE0-FINAL-P2-001`: Self-referential semantic-history finalization is deferred to Phase 1 entry. Reason: placing the closing commit hash inside the graph changes the graph digest, so Phase 0 would need either an external ledger or a two-step finalization model. The current boundary is explicit and verifier-visible.
- M0 license/integration review remains deferred until an actual external integration candidate is selected.
- Deeper academic comparison remains capability-gated; Phase 0 used enough prior-art pressure to avoid duplicate implementation in the approved slice.

## Weak Assumptions

- `hiddenState.sourceGraphSnapshot` is doing heavy work. Phase 1 should reduce or justify this dependency before expanding benchmarks.
- B0 is one tiny Python CLI benchmark. It does not prove scale, multi-file generation, edits to generated code, cross-language behavior, or code-first maintenance over existing projects.
- Evidence and authority are minimal graph envelopes, not PROV/OPA/SLSA replacements.
- AI proposal validation uses synthetic fixtures, not a live AI proposal stream.
- The workbench boundary is a JSON projection, not an interactive application.
- Temp-output reports are semantically stable but not byte-identical because path fields are meaningful report data.

## Pivot Or Narrow Triggers

Phase 1 should narrow or pivot if any of these occur:

- exact reconstruction is claimed without preservation metadata
- code-only facts are claimed to recover full intent, evidence, authority, or history
- IntentGraph is claimed to replace source code as a universal source language
- AI proposal output is treated as final authority
- generated code is treated as proof without verifier evidence
- evidence/authority/history cannot round-trip beyond B0 without opaque hidden snapshots
- Graphify/RepoGraph-style context, Joern/CodeQL/Kythe/Glean-style extraction, Sirius/workbench tooling, or OPA/PROV/SLSA/in-toto capabilities are duplicated instead of integrated or explicitly differentiated
- the next benchmark cannot distinguish IntentGraph from an ordinary DSL generator plus code graph viewer

## Phase 1 Entry Conditions

Recommended first Phase 1 focus after P1.R review:

- revise Intent Units as semantic overlay mapping units
- define `codeRef`, `codeFactRef`, and mapping obligation rules
- reduce the dependence on `hiddenState.sourceGraphSnapshot` inside generated-code mode
- define a commit-finalization strategy for semantic graph history
- add an executable test harness around the B0 pipeline and negative probes
- choose one slightly larger benchmark only after rerunning the prior-art gate
- keep AI and workbench expansion behind deterministic validation and authority gates

Final decision: Phase 0 passes the approved feasibility and core thesis validation scope. Continue to Phase 1 only with explicit user authorization and the scope guards above.
