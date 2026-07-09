# Phase 1 Entry Plan

Status: user-authorized entry revision, not broad Phase 1 authorization

Phase 0 passed the approved feasibility scope. The next work must not simply add a larger benchmark or a richer UI. First, the source graph structure must be corrected around Intent Units.

## Entry Thesis

Phase 0 proved a flat GraphIR loop for B0:

```text
G -> Native(G) -> (C, mu) -> Retrofit(C, mu) -> G' -> Verify(G, G')
```

Phase 1 entry must prove that this loop still works when the source graph is organized around Intent Units:

```text
G_unit -> Native(G_unit) -> (C, mu_unit) -> Retrofit(C, mu_unit) -> G_unit' -> Verify(G_unit, G_unit')
```

## First Phase 1 Slice: P1.0 Intent Unit Grammar Revision

Goal: revise the Phase 0 B0 source graph from a flat GraphIR into a unit-structured GraphIR without weakening the round-trip, evidence, authority, history, AI proposal, or workbench boundaries.

Expected changes:

- introduce `IntentUnit` as a first-class source construct
- define unit refinement and cross-unit relationship rules
- define how existing Phase 0 node kinds live inside units
- rewrite or supplement B0 as a unit-structured fixture
- update compiler, reconstructor, verifier, proposal, and workbench contracts where necessary
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

## Required Output

P1.0 should produce:

- updated GraphIR boundary or a `GraphIR v0.2` draft
- unit-structured B0 fixture or migration fixture
- updated validation rules for Intent Units
- updated compiler/reconstructor/verifier contracts
- regenerated B0 outputs if implementation is touched
- a written review explaining whether the unit model improved or weakened the architecture

## Acceptance Criteria

P1.0 passes only if:

1. B0 has explicit Intent Units.
2. The product/calculator unit refines into add and subtract behavior units.
3. Each unit has a contract, internal graph membership, projection expectations, verification expectations, evidence/authority/history linkage, and reconstruction expectations.
4. Existing Phase 0 semantics remain preserved.
5. `G_unit -> C -> G_unit' -> Verify` passes for B0 or a written blocker explains why it cannot.
6. Code-only reconstruction remains explicitly lossy.
7. AI proposal output remains non-authoritative.
8. Workbench output remains projection/report only.
9. Whole-graph snapshot dependence is measured and either reduced or explicitly justified.
10. A milestone review recommends continue, improve, narrow, or pivot.

## Stop Conditions

Stop and report before broadening scope if:

- Intent Unit becomes a catch-all container with no validation value.
- B0 cannot be represented as units without losing clarity.
- Exact round-trip depends only on copying the whole source graph snapshot and no better metadata strategy is proposed.
- The unit structure makes the compiler or reconstructor less deterministic.
- The project starts duplicating mature language workbench, code graph, or provenance systems without a build/borrow/integrate decision.

## Suggested Worker Task

Task name:

```text
P1.0 Intent Unit Grammar Revision
```

Worker should start from:

- `docs/design/intent-unit-model.md`
- `docs/design/intentgraph-formal-blueprint.md`
- `docs/language/graphir-boundary.md`
- `docs/examples/b0-python-cli-calculator.graph.json`
- `docs/reviews/phase-0-final-review.md`

Worker should not start a larger benchmark until P1.0 review passes.
