# Benchmark Plan

Benchmarks must exist before implementation claims.

## Benchmark Projects

Start with small, repeatable projects:

1. CLI calculator
2. Todo web app
3. Small REST API
4. Small desktop utility

## Required Measurements

For each benchmark, measure:

- can an intent graph describe the product intent?
- can it describe code symbols and relationships?
- can source code be generated deterministically from the graph?
- can generated source code be reconstructed into the graph?
- what information is lost without metadata?
- are tests and evidence linked to graph nodes?
- are authority and change history preserved?
- can an AI proposal be represented as a graph delta?

## Reference Tools

Compare against relevant existing systems by capability:

- language workbench: MPS, Xtext
- model/code generation: EMF, Acceleo
- bidirectional transformation: eMoflon/TGG, QVT
- code graph extraction: Joern/CPG, CodeQL, Graphify, SCIP
- code intelligence: Sourcegraph

## Pass Criteria for First Vertical Slice

The first implementation should pass:

```text
G -> Native(G) -> Retrofit(Native(G)) = G
```

for a small deterministic graph with generated source metadata.
