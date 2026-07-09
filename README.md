# IntentGraph Development

IntentGraph Development is a graph-native software development methodology for AI-assisted development.

The central idea:

> Code is the output. Intent is the source.

IntentGraph Development treats the graph as the primary source artifact, compiles it into executable source code, reconstructs the graph from generated code, and makes round-trip consistency, evidence, authority, and change history first-class parts of the software development process.

## Current Status

Phase 0 is complete as of 2026-07-09. See the [Phase 0 Final Review](docs/reviews/phase-0-final-review.md).

No `M8` was opened automatically. The next authorized work is the Phase 1 entry revision: define Intent Units as the source-level development unit before expanding benchmarks or tooling. See the [Phase 1 Entry Plan](docs/roadmap/phase-1-entry-plan.md).

## Working Definition

IntentGraph is not just a code graph. It is a source graph that can contain:

- product intent and requirements
- code structure and symbols
- relationships between files, functions, classes, tests, and runtime behavior
- semantic graph deltas
- evidence, validation results, and change history
- authority, review, and provenance boundaries

The long-term source structure is not a flat bag of nodes. Phase 1 introduces [Intent Units](docs/design/intent-unit-model.md): stable, compilable, reconstructable development meaning units with internal graphs for contract, behavior, code realization, verification, evidence, authority, history, and projection.

## Initial Scope

This repository starts with process and design boundaries before implementation. The first goal is to avoid rebuilding existing stronger systems by accident.

Initial tracks:

1. Prior-art and benchmark gate
2. IntentGraph core language and canonical graph IR
3. Graph-to-code compiler boundary
4. Code-to-graph reconstructor boundary
5. Round-trip verifier
6. AI-assisted change proposal boundary

## Before Implementation

Start here:

- [Start Here](docs/START-HERE.md)
- [Core Thesis](docs/concept/core-thesis.md)
- [IntentGraph Formal Blueprint](docs/design/intentgraph-formal-blueprint.md)
- [Intent Unit Model](docs/design/intent-unit-model.md)
- [Evidence Model](docs/evidence/evidence-model.md)
- [Authority Model](docs/authority/authority-model.md)
- [Change History Model](docs/history/change-history-model.md)
- [AI Proposal Format](docs/ai/proposal-format.md)
- [Workbench Boundary](docs/workbench/workbench-boundary.md)
- [Phase 0 Final Review](docs/reviews/phase-0-final-review.md)
- [Glossary](docs/concept/glossary.md)
- [Non-Goals](docs/concept/non-goals.md)
- [Milestones](docs/roadmap/milestones.md)
- [Phase 1 Entry Plan](docs/roadmap/phase-1-entry-plan.md)

Every major implementation slice must pass:

- [Prior-Art Gate](docs/process/prior-art-gate.md)
- [Capability Matrix](docs/research/capability-matrix.md)
- [Build / Borrow / Integrate Decisions](docs/decisions/build-borrow-integrate-decisions.md)
- [Benchmark Plan](docs/research/benchmark-plan.md)
- [Milestone Review Gate](docs/process/milestone-review-gate.md)

Worker handoffs must follow:

- [Worker Handoff Protocol](docs/process/worker-handoff-protocol.md)
- [Autonomous Work Loop](docs/process/autonomous-work-loop.md)
- [Worker Completion Report Template](docs/templates/worker-completion-report-template.md)

## Non-Goals for the First Slice

- Do not clone DevView's report-only readiness surface.
- Do not build a full IDE first.
- Do not implement a large language ecosystem first.
- Do not duplicate existing code graph engines without a build/borrow/integrate decision.
- Do not treat AI output as authority without deterministic validation.

## Starting Documents

- [Start Here](docs/START-HERE.md)
- [Core Thesis](docs/concept/core-thesis.md)
- [Core Definition](docs/design/core-definition.md)
- [IntentGraph Formal Blueprint](docs/design/intentgraph-formal-blueprint.md)
- [Milestones](docs/roadmap/milestones.md)
- [Prior-Art Gate](docs/process/prior-art-gate.md)
- [Late Prior-Art Discovery Protocol](docs/process/late-prior-art-discovery.md)
- [Autonomous Work Loop](docs/process/autonomous-work-loop.md)
- [Prior-Art Map](docs/research/prior-art-map.md)
- [Capability Matrix](docs/research/capability-matrix.md)
- [Benchmark Plan](docs/research/benchmark-plan.md)
