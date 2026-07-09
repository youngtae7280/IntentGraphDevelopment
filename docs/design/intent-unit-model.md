# Intent Unit Model

Status: Phase 1 entry design revision

Phase 0 proved a tiny metadata-backed loop:

```text
G -> Native(G) -> (C, mu) -> Retrofit(C, mu) -> G' -> Verify(G, G')
```

That proof used a flat GraphIR document. This was useful for feasibility, but it is not the right long-term source structure. If every intent, code fact, test, evidence record, authority record, and history delta is only scattered across a flat graph, the graph becomes searchable but not developable.

Phase 1 must introduce `IntentUnit` as the source-level development unit.

## Core Claim

An Intent Unit is not merely a requirement node.

An Intent Unit is a stable, compilable, reconstructable development meaning unit. It groups the internal graph needed to move from intent to code and back while preserving verification, evidence, authority, and history.

```text
IntentGraph = Unit refinement structure
            + cross-unit relationship graph
            + internal graphs inside each Intent Unit
            + projection / reconstruction metadata
            + verifier rules
```

## Why The Unit Exists

The user does not give complete requirements. A user gives incomplete signals:

```text
raw utterance -> interpretation -> candidate intent -> accepted development commitment
```

The source graph must preserve this distinction. A raw utterance, note, hypothesis, or unconfirmed idea can be represented in the graph, but it is not automatically an Intent Unit.

An Intent Unit begins when a development commitment is stable enough to require:

- a contract
- implementation or implementation candidates
- verification obligations
- evidence requirements
- authority boundaries
- projection and reconstruction anchors
- semantic history

## Formal Shape

```text
G = (U, EU, IU, meta)
```

Where:

- `U`: finite set of Intent Units.
- `EU`: typed edges between Intent Units.
- `IU`: mapping from each unit `u` to an internal graph.
- `meta`: graph-level metadata, projection declarations, verification expectations, and versioning.

Each unit has:

```text
u = (
  id,
  kind,
  contract,
  internalGraph,
  projection,
  reconstruction,
  verification,
  evidence,
  authority,
  history,
  status
)
```

Definitions:

- `id`: durable source identity.
- `kind`: unit role, such as product, capability, behavior, change, integration, or policy. Phase 1 should keep the initial set small.
- `contract`: externally visible development promise.
- `internalGraph`: the code, behavior, test, evidence, authority, projection, and history nodes owned by or linked to the unit.
- `projection`: how this unit contributes to generated source code.
- `reconstruction`: how generated source and metadata recover this unit.
- `verification`: how this unit is checked.
- `evidence`: what observations or artifacts support acceptance.
- `authority`: who or what can accept changes affecting this unit.
- `history`: semantic deltas that created, changed, superseded, or accepted the unit.
- `status`: draft, proposed, accepted, superseded, rejected, or equivalent bounded states.

## Unit Refinement And Cross-Unit Graph

Intent Units need both hierarchy and graph relationships.

Refinement expresses decomposition:

```text
product unit -> capability unit -> behavior unit -> case unit
```

This relation should usually be a tree or DAG.

Cross-unit relations express real development coupling:

```text
depends_on
impacts
conflicts_with
shares_concept
shares_code
verifies
supersedes
projects_with
```

These relations form a general graph.

Therefore:

```text
IntentGraph is not only a tree.
IntentGraph is not only a flat graph.
IntentGraph is a unit graph with a refinement backbone.
```

## Internal Graph

Each Intent Unit contains or owns an internal graph. A small unit may contain only a few nodes. A large unit may contain nested or linked unit references, but it must not become an unbounded catch-all.

An internal graph may include:

- raw utterance references
- accepted intent commitments
- behavior contracts
- domain concepts
- code symbols and code relationships
- tests and verification contracts
- evidence records
- authority records
- semantic history deltas
- projection targets
- source maps and reconstruction anchors

The Phase 0 B0 fixture already contains most of these facts, but they are not yet organized around explicit units.

## Unit Admission Rules

A graph element should become an Intent Unit only if it satisfies the minimum source-unit contract:

1. It has a stable ID.
2. It has a contract or accepted development commitment.
3. It has at least one realization path or explicit non-realized status.
4. It has verification obligations or explicit verification-not-required status.
5. It has evidence requirements or evidence records appropriate to its status.
6. It has authority requirements for acceptance.
7. It has projection and reconstruction expectations.
8. It can participate in `G -> C -> G' -> Verify`.

If these are not true, the graph element may still exist, but it should remain a note, raw utterance, hypothesis, domain concept, code fact, evidence record, or history fact rather than an Intent Unit.

## B0 Mapping

The Phase 0 B0 graph can be reinterpreted as units:

```text
unit.product.calculator
  contract:
    Provide a deterministic Python CLI calculator.
  internal graph:
    intent.product.calculator
    code.module.calc
    code.cli.command
    projection.target.python-source
    evidence.record.requirement-note
    evidence.record.roundtrip-report
    authority records
    history deltas

unit.behavior.add
  contract:
    calc add LEFT RIGHT prints LEFT + RIGHT.
  internal graph:
    intent.behavior.add
    code.function.add
    test.case.add
    metadata.source-map.add

unit.behavior.sub
  contract:
    calc sub LEFT RIGHT prints LEFT - RIGHT.
  internal graph:
    intent.behavior.sub
    code.function.sub
    test.case.sub
    metadata.source-map.sub
```

Refinement:

```text
unit.product.calculator -> unit.behavior.add
unit.product.calculator -> unit.behavior.sub
```

Cross-unit and internal relationships still exist:

```text
code.function.main calls code.function.add
code.function.main calls code.function.sub
intent.behavior.add tested_by test.case.add
intent.behavior.sub tested_by test.case.sub
```

## Round-Trip Implication

The unit boundary must be preserved through metadata-backed compilation:

```text
Native(G_unit) -> (C, mu_unit)
Retrofit(C, mu_unit) -> G_unit'
Verify(G_unit, G_unit') -> pass
```

Phase 0 currently relies heavily on:

```text
mu.hiddenState.sourceGraphSnapshot
```

Phase 1 should not pretend this is solved. The next design pressure is to replace or reduce whole-graph snapshot dependence with unit-level source maps, stable anchors, and explicit metadata for the graph domains that cannot be recovered from source code alone.

## Quality Criteria

An Intent Unit design is acceptable only if:

- B0 can be rewritten as unit-structured GraphIR without losing Phase 0 claims.
- The compiler can still generate deterministic code.
- The reconstructor can recover unit identity and internal graph facts from generated source plus metadata.
- The verifier distinguishes exact unit-graph equality from lossy code-only projection.
- Evidence, authority, and history remain first-class graph facts.
- AI proposals remain proposals, not authority.
- Workbench state remains a projection, not accepted graph state.
- The unit does not become a God object that absorbs unrelated facts.

## Non-Goals

- Do not build a broad language workbench before the unit model is validated.
- Do not expand to a larger benchmark before B0 is unit-structured.
- Do not claim code-only reconstruction recovers full units.
- Do not remove metadata before an explicit replacement exists.
- Do not treat raw user utterances as accepted Intent Units.
