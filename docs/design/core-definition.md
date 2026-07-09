# IntentGraph Core Definition

## Thesis

IntentGraph Development creates a development-semantic overlay graph over an existing codebase.

Traditional pipeline:

```text
source code -> compiler -> machine code -> executable program
```

Corrected IntentGraph state model:

```text
D = (I, C, X, M, E, A, H)
```

Where:

- `I`: intent, behavior, and verification graph.
- `C`: source code artifacts in ordinary programming language files.
- `X`: extracted code fact graph.
- `M`: mappings between `I`, `X`, and `C`.
- `E`: evidence.
- `A`: authority.
- `H`: semantic history.

## Core Principle

Source code remains the implementation source. IntentGraph is the semantic overlay that records intent, behavior, verification, code references, code facts, mappings, evidence, authority, and history.

The graph should not remain a flat bag of unrelated nodes. The long-term semantic unit is the Intent Unit: a stable development meaning unit for contract, behavior, verification, evidence, authority, history, and mapping obligations to code references and code facts.

## Engine Operations

IntentGraph Engine is not primarily a traditional compiler. Its default responsibility is overlay/code consistency, evidence, authority, and change orchestration:

```text
Extract(C) -> X
Map(I, X) -> M
Plan(I, C, X, M, request) -> DeltaC, DeltaI, DeltaM
Verify(I, C', X', M', E, A) -> pass/fail
Record(H, accepted delta)
```

## Round-Trip Distinction

Graph-first generation remains a limited mode for greenfield or generated-code areas:

```text
G -> C -> G'
```

Code-first maintenance is the default frame for existing projects:

```text
C -> X -> M/I -> C'
```

The expected maintenance result is behavior and contract preservation:

```text
Behavior(C') ~= Behavior(C)
```

It is not textual equality of source code.

## Required Graph Domains

An IntentGraph may include:

- intent and requirements
- domain concepts
- architecture and module boundaries
- code references, symbols, ranges, anchors, and extracted facts
- tests and verification contracts
- evidence and observations
- authority and permission boundaries
- decisions and change history
- mapping obligations and generated-code metadata where a generated-code mode is explicitly declared

These domains are organized around Intent Units in Phase 1 and later. Phase 0 used a flat metadata-backed round-trip experiment to prove one generated-code feasibility slice. It should not be overclaimed as the universal architecture.

## Authority Rule

AI may propose graph or code changes, but deterministic validation owns acceptance.

AI is a proposer, not authority.
