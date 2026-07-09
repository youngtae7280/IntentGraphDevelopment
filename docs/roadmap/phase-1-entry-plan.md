# Phase 1 Entry Plan

Status: user-authorized correction phase, not broad Phase 1 authorization

Phase 0 passed the approved feasibility scope, but its graph-first framing must be narrowed. The next work must not add a larger benchmark or a richer UI. First, IntentGraph must be reframed as a development-semantic overlay over existing source code.

## Entry Thesis

Corrected state model:

```text
D = (I, C, X, M, E, A, H)
```

Where `I` is intent/behavior/verification graph, `C` is source code artifacts, `X` is extracted code fact graph, `M` is mapping between `I` and `X/C`, `E` is evidence, `A` is authority, and `H` is semantic history.

Default operation frame:

```text
Extract(C) -> X
Map(I, X) -> M
Plan(I, C, X, M, request) -> DeltaC, DeltaI, DeltaM
Verify(I, C', X', M', E, A) -> pass/fail
Record(H, accepted delta)
```

Graph-first generation remains a limited greenfield/generated-code mode:

```text
G -> Native(G) -> (C, mu) -> Retrofit(C, mu) -> G' -> Verify(G, G')
```

## Completed Slice: P1.R Reframe IntentGraph as Semantic Overlay

Goal: correct the repository framing so IntentGraph is defined as a semantic overlay and consistency/change orchestration engine, not a replacement source language or universal graph-to-code compiler.

Expected changes:

- define IntentGraph as a development-semantic overlay graph linked to source code artifacts
- define code nodes as stable references or facts, not code text
- reinterpret Phase 0 as a tiny metadata-backed generated-code experiment
- revise Intent Units as semantic work units with `codeRef`, `codeFactRef`, and mapping obligations
- keep evidence, authority, semantic history, AI proposal, and workbench projection boundaries intact

Non-goals:

- no new compiler
- no code extraction implementation
- no larger benchmark
- no UI
- no continuation of unit-structured compiler work until the reframing is reviewed
- no prior-art deep search without explicit approval

## Historical Slice: P1.0 Intent Unit Grammar Revision

Goal: revise the Phase 0 B0 graph from a flat GraphIR into a unit-structured GraphIR without weakening the generated-code round-trip, evidence, authority, history, AI proposal, or workbench boundaries.

Status: passed on 2026-07-09. See [P1.0 Intent Unit Grammar Review](../reviews/p1.0-intent-unit-grammar-review.md).

P1.0 must now be read through P1.R. It remains useful implementation evidence, but its graph-as-source/compiler language is superseded by the semantic-overlay framing.

## Current Slice: P1.1 Intent Unit Overlay Mapping Revision

Goal: revise B0 Intent Units into semantic overlay mapping units with `codeRefs`, `codeFactRefs`, and `mappingObligations` while preserving the existing B0 generated-code experiment as one limited mode.

P1.1 resolves the naming ambiguity: `P1.0` is historical and `P1.1` is the active overlay mapping revision.

Do not open a larger benchmark, UI, AI runtime, or broader compiler slice automatically.

Expected changes:

- introduce `IntentUnit` as a first-class semantic overlay construct
- define unit refinement and cross-unit relationship rules
- define how existing Phase 0 node kinds live inside units
- rewrite or supplement B0 as a unit-structured fixture
- update mapping, verifier, proposal, generated-code mode, and workbench contracts where necessary
- keep B0 deterministic and metadata-backed
- explicitly evaluate how much `hiddenState.sourceGraphSnapshot` remains necessary

Non-goals:

- no larger benchmark yet
- no broad language workbench
- no interactive IDE
- no arbitrary code extractor
- no Graphify/CodeQL/Joern replacement
- no claim that source code alone recovers full intent, evidence, authority, or history
- no automatic AI authority

## Required Output For P1.1

P1.1 should produce:

- updated GraphIR/overlay boundary or a `GraphIR v0.2` correction draft
- unit-structured B0 fixture or migration fixture that uses code refs/facts rather than code text
- updated validation rules for Intent Units
- updated mapping/verifier/generated-code-mode contracts
- regenerated B0 outputs if implementation is touched
- a written review explaining whether the unit model improved or weakened the architecture

## Acceptance Criteria

P1.1 passes only if:

1. B0 has explicit Intent Units.
2. The product/calculator unit refines into add and subtract behavior units.
3. Each unit has a contract, internal graph membership, `codeRefs`, `codeFactRefs`, `mappingObligations`, projection expectations, verification expectations, evidence/authority/history linkage, and reconstruction expectations.
4. Existing Phase 0 semantics remain preserved.
5. Generated-code mode remains passing for B0 or a written blocker explains why it cannot.
6. Code-first maintenance is not falsely judged by `C' == C`; expected preservation is behavior, contract, evidence, authority, and mapping consistency.
7. Code-only reconstruction remains explicitly lossy.
8. AI proposal output remains non-authoritative.
9. Workbench output remains projection/report only.
10. Whole-graph snapshot dependence is measured and either reduced or explicitly justified.
11. A milestone review recommends continue, improve, narrow, or pivot.

## Stop Conditions

Stop and report before broadening scope if:

- Intent Unit becomes a catch-all container with no validation value.
- B0 cannot be represented as units without losing clarity.
- Exact generated-code round-trip depends only on copying the whole graph snapshot and no better metadata strategy is proposed.
- The unit structure makes the compiler or reconstructor less deterministic.
- IntentGraph is described again as a universal source-code replacement.
- The project starts duplicating mature language workbench, code graph, or provenance systems without a build/borrow/integrate decision.

## Suggested Worker Task

Task name:

```text
P1.1 Intent Unit Overlay Mapping Revision
```

Worker should start from:

- `docs/design/intent-unit-model.md`
- `docs/design/intentgraph-formal-blueprint.md`
- `docs/language/graphir-boundary.md`
- `docs/examples/b0-python-cli-calculator.graph.json`
- `docs/reviews/phase-0-final-review.md`

Worker should not start a larger benchmark until P1.1 review passes and the Coordinator explicitly authorizes the next phase.
