# IntentGraph Development

IntentGraph Development is a graph-native software development methodology for AI-assisted development.

The central idea:

> Code is the output. Intent is the source.

IntentGraph Development treats the graph as the primary source artifact, compiles it into executable source code, reconstructs the graph from generated code, and makes round-trip consistency, evidence, authority, and change history first-class parts of the software development process.

## Working Definition

IntentGraph is not just a code graph. It is a source graph that can contain:

- product intent and requirements
- code structure and symbols
- relationships between files, functions, classes, tests, and runtime behavior
- work contracts and graph deltas
- evidence, validation results, and change history
- authority, review, and provenance boundaries

## Initial Scope

This repository starts with process and design boundaries before implementation. The first goal is to avoid rebuilding existing stronger systems by accident.

Initial tracks:

1. Prior-art and benchmark gate
2. IntentGraph core language and canonical graph IR
3. Graph-to-code compiler boundary
4. Code-to-graph reconstructor boundary
5. Round-trip verifier
6. AI-assisted change proposal boundary

## Non-Goals for the First Slice

- Do not clone DevView's report-only readiness surface.
- Do not build a full IDE first.
- Do not implement a large language ecosystem first.
- Do not duplicate existing code graph engines without a build/borrow/integrate decision.
- Do not treat AI output as authority without deterministic validation.

## Starting Documents

- [Core Definition](docs/design/core-definition.md)
- [Prior-Art Gate](docs/process/prior-art-gate.md)
- [Late Prior-Art Discovery Protocol](docs/process/late-prior-art-discovery.md)
- [Capability Matrix](docs/research/capability-matrix.md)
- [Benchmark Plan](docs/research/benchmark-plan.md)
