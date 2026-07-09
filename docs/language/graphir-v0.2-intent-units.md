# GraphIR v0.2 Intent Units

Status: P1.1 overlay mapping grammar

GraphIR v0.2 keeps the Phase 0 node and edge graph, but wraps accepted development meaning in first-class Intent Units. Under P1.1, these units are semantic overlay mapping units, not code-text capsules and not replacements for source files.

This is not a broad language workbench. It is the smallest B0-compatible overlay structure needed to preserve:

- accepted intent and behavior contracts
- code references and code fact references
- mapping obligations
- generated-code reconstruction anchors where generation is explicitly declared
- verification obligations
- evidence
- authority
- semantic history
- generated-code projection and code-only loss boundaries

## Top-Level Shape

GraphIR v0.2 adds two fields:

```json
{
  "graphirVersion": "0.2.0",
  "nodes": [],
  "edges": [],
  "intentUnits": [],
  "unitEdges": []
}
```

`nodes` and `edges` remain the internal fact graph. `intentUnits` define accepted development meaning units. `unitEdges` define relationships between units.

## Intent Unit Shape

```json
{
  "id": "unit.behavior.add",
  "kind": "behavior",
  "status": "accepted",
  "contract": {},
  "internalGraph": {
    "nodeIds": [],
    "edgeIds": []
  },
  "codeRefs": [],
  "codeFactRefs": [],
  "mappingObligations": [],
  "projection": {},
  "reconstruction": {},
  "verification": {},
  "evidence": [],
  "authority": [],
  "history": [],
  "admission": {}
}
```

Required fields:

- `id`: stable unit identity.
- `kind`: bounded unit role. P1.0 supports `product` and `behavior` for B0.
- `status`: unit lifecycle state. P1.0 accepted units must be `accepted`.
- `contract`: accepted development commitment for the unit.
- `internalGraph`: node and edge IDs that carry the unit's internal facts.
- `codeRefs`: stable references to files, symbols, ranges, anchors, or generated artifacts. They are reference-only and do not contain code text.
- `codeFactRefs`: references to extracted, declared, or generated-preservation-backed code facts. P1.1 uses static declared facts only; it does not implement an external extractor.
- `mappingObligations`: declared expectations tying behavior or verification claims to code refs/facts.
- `projection`: generated-code contribution and source-map expectations when generated-code mode is declared.
- `reconstruction`: metadata-backed reconstruction expectations and code-only loss claim when generated-code mode is declared.
- `verification`: test and verifier expectations.
- `evidence`: evidence record IDs relevant to unit acceptance.
- `authority`: authority record IDs relevant to unit acceptance or mutation.
- `history`: semantic history delta IDs relevant to the unit.
- `admission`: explicit admission flags proving the unit is not just a raw note or hypothesis.

## Unit Edges

`unitEdges` are separate from ordinary graph `edges`.

P1.0 distinguishes:

- refinement relations: `kind: "refines"`
- cross-unit relations: `kind: "shares_concept"` and `kind: "projects_with"`

The B0 required refinement backbone is:

```text
unit.product.calculator -> unit.behavior.add
unit.product.calculator -> unit.behavior.sub
```

The ordinary Phase 0 edges remain available inside units, for example:

```text
intent.behavior.add tested_by test.case.add
code.function.main calls code.function.add
metadata.source-map.add maps_from intent.behavior.add
```

## B0 Unit Set

P1.0 B0 has exactly the initial accepted unit set:

- `unit.product.calculator`
- `unit.behavior.add`
- `unit.behavior.sub`

The product unit is the parent contract for the calculator. The behavior units carry the accepted add/sub operation contracts.

P1.1 keeps the same unit set and adds overlay mapping fields to each unit.

## Admission Rules

An Intent Unit is admitted only when all of these are true:

- stable ID exists
- accepted development commitment exists
- realization path exists or an explicit non-realized state is declared
- verification obligation exists or an explicit verification-not-required state is declared
- evidence boundary exists
- authority boundary exists
- mapping boundary exists
- projection and reconstruction boundaries exist if generated-code mode is declared

Raw utterances, hypotheses, notes, imported code facts, and AI outputs may exist in the graph, but they are not accepted Intent Units unless these admission conditions are satisfied.

## Preservation Metadata

GraphIR v0.2 generated-code preservation metadata adds `unitMap`. P1.1 extends it with overlay mapping digests:

```json
{
  "unitMap": [
    {
      "unitId": "unit.behavior.add",
      "unitKind": "behavior",
      "internalNodeIds": [],
      "internalEdgeIds": [],
      "sourceMapIds": [],
      "codeRefIds": [],
      "codeFactRefIds": [],
      "mappingObligationIds": [],
      "codeRefsDigest": "sha256:...",
      "codeFactRefsDigest": "sha256:...",
      "mappingObligationsDigest": "sha256:...",
      "requiresMetadata": true,
      "codeOnlyClaim": "lossy-code-only-projection"
    }
  ]
}
```

`unitMap` measures and exposes unit-level preservation, but P1.0 still uses `hiddenState.sourceGraphSnapshot` for exact reconstruction.

This is an honest intermediate state:

- exact unit round-trip is metadata-backed
- code-only reconstruction remains lossy
- source-only recovery of unit contracts, evidence, authority, and history is not claimed
- code nodes remain references/facts, not code text
- mapping obligations are preserved through metadata in generated-code mode

## Workbench Projection

Workbench projections may display:

- unit counts
- units by kind
- unit edges by kind
- unit membership
- unit preservation report

Workbench output remains a report. It is not accepted authority.

## P1.0 Non-Goals

- no larger benchmark
- no broad language workbench
- no interactive IDE
- no arbitrary source-code extraction
- no code-only exact reconstruction
- no AI authority
