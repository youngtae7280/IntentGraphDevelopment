# M1 Milestone Review

Milestone: M1 - IntentGraph Language and GraphIR Boundary
Date: 2026-07-09
Reviewer: IntentGraphDevelopment Roadmap Orchestrator

Declared quality target: Level 2

## Produced Artifacts

- `docs/design/intentgraph-formal-blueprint.md`
- `docs/language/language-principles.md`
- `docs/language/graphir-boundary.md`
- `docs/language/validation-rules.md`
- `docs/examples/b0-python-cli-calculator.graph.json`
- `docs/reviews/m1-review.md`

## Benchmarks Run

No implementation benchmark was allowed in M1.

M1 produced the graph fixture for `B0-python-cli-calculator` and manually validated that it:

- parses as JSON
- uses unique node and edge IDs
- uses only declared M1 node and edge kinds
- has valid edge endpoints
- covers every code projection node with source-map metadata
- declares code-only loss for evidence, authority, history, and source-map identity
- declares verification expectations for exact round-trip with metadata

## Prior-Art Comparison

M1 remained inside the decisions from M0:

- did not build a language workbench despite MPS/Xtext/Spoofax/MontiCore pressure
- did not adopt a broad MDE stack despite EMF/Acceleo/MetaEdit+ pressure
- used formal round-trip contracts informed by QVT/TGG pressure without implementing a bidirectional engine
- did not build a broad code extractor despite Joern/CodeQL/SCIP/Kythe/Glean pressure
- represented evidence, authority, and history boundaries while avoiding custom policy/provenance engines

The formal blueprint now records those prior-art pressures directly.

## Result

Proved:

- The first benchmark can be represented as a small canonical JSON GraphIR fixture.
- M1 can define graph identity, code projection/reference nodes, preservation metadata placeholders, evidence, authority, history, and verification expectations without compiler implementation.
- The formal blueprint gives M2-M4 precise contracts for `Native`, `Retrofit`, `Verify`, `TypeCheck`, preservation metadata, and the Phase 0 pass pipeline.

Weakened:

- The initial M1 draft was under-specified for required attributes and CLI behavior.
- `maps_from` semantics needed clarification because code projection nodes are graph nodes about future generated code.

Changed:

- Added the formal blueprint as the M1 center of gravity.
- Added explicit required-attribute validation rules.
- Replaced fixture wording that sounded like an implemented generator with `compilerContract`.
- Added explicit CLI argument, output, and exit-code behavior to avoid hidden compiler defaults.
- Added `verificationExpectations` to the fixture and GraphIR boundary.

## Round-Trip Status

Not implemented in M1.

M1 defines the future target:

```text
G_b0
  -> Native(G_b0, python, config_b0)
  -> (calc.py, calc.intentgraph.json, D1)
  -> Retrofit(calc.py, calc.intentgraph.json, config_b0)
  -> (G'_b0, D2)
  -> Verify(G_b0, G'_b0, mu_b0, config_b0)
  -> pass
```

## Evidence Status

Evidence is represented as graph data in the B0 fixture, with planned records for the requirement note and test plan. M5 must preserve and verify evidence through the round-trip loop.

## Authority Status

Authority is represented as graph data in the B0 fixture. AI is not final authority. M5/M6 must preserve authority and enforce proposal-only AI boundaries.

## Unexpected Discoveries

- A formal blueprint is necessary to keep M1 from becoming only a schema sketch.
- The B0 fixture needed explicit CLI behavior so M2 will not invent hidden compiler defaults.
- Source-map metadata must cover code projection nodes as graph nodes, not emitted source text.

## Issue Review

| ID | Severity | Issue | Resolution |
|---|---|---|---|
| M1-P1-001 | P1 | Required attributes for metadata/evidence/authority/history were described but not validation rules. | Resolved with V043, V052, V062, and V072. |
| M1-P1-002 | P1 | `maps_from` semantics were ambiguous for code projection nodes. | Resolved by clarifying code projection nodes as semantic graph nodes and documenting `maps_from` accordingly. |
| M1-P1-003 | P1 | M2 compiler behavior could depend on hidden CLI defaults. | Resolved by adding explicit argument schema, operation kinds, stdout behavior, and exit-code behavior. |
| M1-P2-001 | P2 | Equality/projection expectations were mentioned but not represented. | Resolved with `verificationExpectations`. |
| M1-P2-002 | P2 | `generatedBy` wording could imply an implemented compiler. | Resolved by replacing it with `compilerContract`. |
| M1-P2-003 | P2 | Formal blueprint needed a concrete B0 example and failure/pivot criteria. | Resolved in `docs/design/intentgraph-formal-blueprint.md`. |
| M1-P3-001 | P3 | No executable validator exists yet. | Accepted for M1 because implementation is not allowed; M2 or M4 should introduce executable checks when relevant. |

No unresolved P0/P1 issues remain. All P2 issues are resolved.

## Decision

Decision: continue

Achieved quality level: Level 2

M1 passes its declared quality bar.

## Required Changes Before Next Milestone

Before M2 implementation:

- use `docs/examples/b0-python-cli-calculator.graph.json` as the graph fixture
- keep the first compiler target to Python standard-library source
- emit source and preservation metadata according to the formal blueprint
- do not build a broad language workbench or broad code extractor
- document exact test commands before coding
- make generated artifacts deterministic and inspectable
