# M0 Milestone Review

Milestone: M0 - Research and Thesis Foundation
Date: 2026-07-09
Reviewer: IntentGraphDevelopment Roadmap Orchestrator

Declared quality target: Level 2, Benchmarked Slice Preparation

## Produced Artifacts

- `docs/concept/core-thesis.md`
- `docs/research/prior-art-map.md`
- `docs/research/capability-matrix.md`
- `docs/decisions/build-borrow-integrate-decisions.md`
- `docs/research/benchmark-plan.md`
- `docs/reviews/m0-review.md`

## Benchmarks Run

No implementation benchmark was allowed in M0.

M0 produced a paper benchmark plan for `B0-python-cli-calculator`, including pass/fail criteria for:

- deterministic graph-to-code generation
- generated-code preservation metadata
- reconstruction with metadata
- lossy code-only reconstruction
- equality verification
- evidence preservation
- authority preservation
- semantic history preservation

## Prior-Art Comparison

Compared lanes:

- model-driven engineering: OMG MDA, EMF, Acceleo, MetaEdit+
- language workbenches: MPS, Xtext, Spoofax, MontiCore, Rascal
- bidirectional transformation: QVT, Triple Graph Grammars, eMoflon::IBeX, ATL
- code graph/static analysis: Joern/CPG, CodeQL, Tree-sitter
- code intelligence indexes: SCIP, LSIF, Kythe, Glean, SemanticDB, Sourcegraph
- AI repository context graphs: Graphify, RepoGraph, adjacent code graph model research
- visualization/workbench: Sirius, Cytoscape.js, Graphviz, D3, Mermaid
- provenance/evidence/authority/history: W3C PROV, OpenLineage, SLSA, in-toto, SPDX/GUAC, Git, CODEOWNERS, branch protection, OPA, Reproducible Builds, Bazel

Strongest finding:
P1.R correction: this statement is now narrowed. Phase 0 built a generated-code experiment around deterministic generated code, preservation metadata, reconstruction, equality verification, evidence, authority, and history. IntentGraph is now framed as a semantic overlay over existing code, not graph as source.

## Result

Proved:

- M0 can state a differentiated thesis without claiming novelty in model-to-code, code graphs, provenance, policy, or visualization.
- The first benchmark can distinguish IntentGraph from ordinary DSL generation, code graph viewers, and AI context graphs.
- Initial build/borrow/integrate decisions are specific enough to prevent immediate duplication of stronger systems.

Weakened:

- The original M0 artifacts under-acknowledged Kythe, Glean, PROV/OPA, and TGG/QVT pressure.
- Evidence and authority were too broadly labeled as "build" before this review.

Changed:

- Evidence is now "build the IntentGraph binding; learn/borrow provenance formats."
- Authority is now "build the minimal envelope; benchmark/integrate OPA before custom policy logic."
- Code extraction is now limited to generated-code reconstruction for the first benchmark.
- The first benchmark is narrowed to `B0-python-cli-calculator`.

## Round-Trip Status

Not implemented in M0. M0 defines the required round-trip proof shape:

```text
Retrofit(Native(G)) = G
```

with preservation metadata, plus explicit lossy projection for code-only reconstruction.

## Evidence Status

Evidence is not implemented in M0. The M0 benchmark requires evidence records linked to graph nodes and verifier output in M5.

## Authority Status

Authority is not implemented in M0. The M0 benchmark requires proposer, validator, reviewer/authority, decision, and accepted state. AI output remains proposal-only.

## Unexpected Discoveries

- Kythe generated-code indexing is directly relevant to preservation metadata and must be learned from before metadata design hardens.
- Glean is a stronger scalable code facts comparator than the original map recorded.
- eMoflon::IBeX-TGG is a strong conceptual comparator, but the project site states IBeX-TGG development was discontinued in 2024.
- PROV/OPA/Git/CODEOWNERS significantly sharpen the evidence, authority, and history boundaries.

## Issue Review

| ID | Severity | Issue | Resolution |
|---|---|---|---|
| M0-P0-001 | P0 | M0 could duplicate MPS/EMF/MetaEdit+/Acceleo by treating model-to-code as novel. | Resolved by prior-art map and decisions 001-002. |
| M0-P0-002 | P0 | First benchmark could collapse into a code graph viewer or DSL generator. | Resolved by benchmark pass/fail criteria requiring reconstruction, metadata, equality, evidence, authority, and history. |
| M0-P0-003 | P0 | AI output could be treated as authority. | Resolved by core thesis and decisions 007/010. |
| M0-P1-001 | P1 | TGG/QVT pressure was too weak in the original docs. | Resolved by prior-art map, matrix, and decision 003. |
| M0-P1-002 | P1 | Kythe/Glean were missing from generated-code/code-facts comparison. | Resolved by prior-art map, matrix, and decisions 004-005. |
| M0-P1-003 | P1 | Evidence/authority/history were under-specified. | Resolved by decisions 006-008 and benchmark criteria. |
| M0-P2-001 | P2 | Full license review is not complete. | Deferred until an actual integration candidate is selected; M0 makes no dependency choice. |
| M0-P2-002 | P2 | Deep academic review of every BX and AI repo-graph paper is incomplete. | Deferred to capability-specific gates in M3/M4/M6; M0 used strongest known primary sources and papers sufficient for slice selection. |
| M0-P2-003 | P2 | No tool installation benchmark was run. | Deferred because M0 forbids implementation and no integration is selected. Paper benchmark is sufficient for Level 2 preparation. |
| M0-P3-001 | P3 | Later benchmark candidates remain broad. | Accepted as future planning; not blocking M1. |

No unresolved P0/P1 issues remain. All P2 issues have written defer decisions.

## Decision

Decision: continue

Achieved quality level: Level 2, Benchmarked Slice Preparation

M0 passes its declared quality bar.

## Required Changes Before Next Milestone

Before M1 work:

- keep implementation closed until M1 defines the smallest IntentGraph language and GraphIR boundary
- use `B0-python-cli-calculator` as the first benchmark unless M1 review changes it
- include preservation metadata, evidence, authority, and history fields in the M1 design surface
- keep broad workbench, broad code extraction, AI runtime, and visualization out of M1
