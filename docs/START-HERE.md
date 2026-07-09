# Start Here

This repository must not begin with implementation.

IntentGraph Development is a proposed software development method, source layer, compiler boundary, reconstructor boundary, and verification discipline. Before code exists, the project needs a stable thesis, prior-art review, benchmark criteria, and milestone gates.

## Work Order

Follow this order:

1. Read the core thesis.
2. Run the prior-art gate for the capability being considered.
3. Update the capability matrix.
4. Write a build/borrow/integrate decision.
5. Define a benchmark before implementation.
6. Start only the smallest vertical slice that can prove or disprove the thesis.
7. Review the slice against the milestone gate before continuing.

## First Principle

Code is the output. Intent is the source.

## Primary Thesis

IntentGraph Development treats the graph as the primary source artifact, compiles it into executable source code, reconstructs the graph from generated code, and makes round-trip consistency, evidence, authority, and change history first-class parts of the software development process.

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

## Stop Criteria

Stop and reassess if:

- a stronger existing system is found
- the slice duplicates an existing tool without a decision record
- the benchmark cannot distinguish IntentGraph from a code graph viewer, DSL tool, or model generator
- AI output is being treated as authority rather than proposal
- source code generation cannot be round-trip checked
