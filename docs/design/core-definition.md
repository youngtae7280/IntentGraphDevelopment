# IntentGraph Core Definition

## Thesis

IntentGraph Development creates a higher source layer above traditional source code.

Traditional pipeline:

```text
source code -> compiler -> machine code -> executable program
```

IntentGraph pipeline:

```text
intent graph -> intent graph compiler -> source code + metadata -> existing compiler -> executable program
```

Reverse pipeline:

```text
source code + metadata -> intent graph reconstructor -> intent graph
```

## Core Principle

The graph is the primary source artifact. Source code is an executable projection.

## Round-Trip Target

Full round-trip with metadata:

```text
Retrofit(Native(G)) = G
```

Code-only reconstruction is lossy:

```text
RetrofitCodeOnly(Native(G)) ~= ProjectionCode(G)
```

Where:

- `G` is the source intent graph.
- `Native` compiles an intent graph to source code plus preservation metadata.
- `Retrofit` reconstructs an intent graph from source code plus preservation metadata.
- `ProjectionCode` is the portion of the graph expressible in source code alone.

## Required Graph Domains

An IntentGraph may include:

- intent and requirements
- domain concepts
- architecture and module boundaries
- code symbols and code relationships
- tests and verification contracts
- evidence and observations
- authority and permission boundaries
- decisions and change history
- generated source mapping metadata

## Compiler Rule

AI may propose graph or code changes, but deterministic validation owns acceptance.

AI is a proposer, not authority.
