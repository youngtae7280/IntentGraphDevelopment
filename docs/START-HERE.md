# Start Here

This repository must not begin with implementation.

IntentGraph Development is a proposed software development method, source layer, compiler boundary, reconstructor boundary, and verification discipline. Before code exists, the project needs a stable thesis, prior-art review, benchmark criteria, and milestone gates.

## Work Order

Follow this order:

1. Read the core thesis.
2. Read the [IntentGraph Formal Blueprint](design/intentgraph-formal-blueprint.md) for the current formal center of gravity.
3. Read the current milestone in [Milestones](roadmap/milestones.md).
4. Run the prior-art gate for the capability being considered.
5. Update the capability matrix.
6. Write a build/borrow/integrate decision.
7. Define a benchmark before implementation.
8. Start only the smallest vertical slice that can prove or disprove the thesis.
9. Review the slice against the milestone gate before continuing.

For a worker or new chat, follow the [Autonomous Work Loop](process/autonomous-work-loop.md).

## First Principle

Code is the output. Intent is the source.

## Primary Thesis

IntentGraph Development treats the graph as the primary source artifact, compiles it into executable source code, reconstructs the graph from generated code, and makes round-trip consistency, evidence, authority, and change history first-class parts of the software development process.

## Formal Blueprint

The current formal center of gravity is [IntentGraph Formal Blueprint](design/intentgraph-formal-blueprint.md). It is a draft for M1, not final architecture, and must be revised when prior-art review, milestone review, or benchmark evidence contradicts it.

## Default Bias

Do not build what a stronger existing system already does well.

Prefer:

- integrate a strong existing engine
- learn from a mature design
- define the missing boundary between existing tools
- build only the part that is unique to IntentGraph

## Implementation Entry Criteria

Implementation may start only when these are written:

- core thesis for the slice
- prior-art notes
- capability comparison
- build/borrow/integrate decision
- benchmark target
- acceptance criteria
- late prior-art response plan

The current authorized milestone is `M2: Native Compiler Boundary`. `M0: Research and Thesis Foundation` and `M1: IntentGraph Language and GraphIR Boundary` passed their milestone reviews on 2026-07-09.

Do not open compiler, reconstructor, verifier, package setup, UI, or AI runtime implementation until the relevant later milestone is current and its entry criteria are met.

## Stop Criteria

Stop and reassess if:

- a stronger existing system is found
- the slice duplicates an existing tool without a decision record
- the benchmark cannot distinguish IntentGraph from a code graph viewer, DSL tool, or model generator
- AI output is being treated as authority rather than proposal
- source code generation cannot be round-trip checked
