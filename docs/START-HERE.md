# Start Here

This repository must not begin with implementation.

IntentGraph Development is a proposed software development method, semantic overlay graph, mapping boundary, consistency engine, and verification discipline over existing source code. Before broad implementation exists, the project needs a stable thesis, prior-art review, benchmark criteria, and milestone gates.

## Work Order

Follow this order:

1. Read the core thesis.
2. Read the [IntentGraph Formal Blueprint](design/intentgraph-formal-blueprint.md) for the current formal center of gravity.
3. Read the [Product Capability Roadmap](roadmap/product-capability-roadmap.md) for the long-range phase gates.
4. Read the current milestone in [Milestones](roadmap/milestones.md).
5. Run the prior-art gate for the capability being considered.
6. Update the capability matrix.
7. Write a build/borrow/integrate decision.
8. Define a benchmark before implementation.
9. Start only the smallest vertical slice that can prove or disprove the thesis.
10. Review the slice against the milestone gate before continuing.

For a worker or new chat, follow the [Autonomous Work Loop](process/autonomous-work-loop.md).

## First Principle

Code remains the implementation source. IntentGraph is the development-semantic overlay that links intent, code facts, mapping obligations, evidence, authority, and semantic history.

## Primary Thesis

IntentGraph is a development-semantic overlay graph linked to source code artifacts. It does not replace source code or copy code text into the graph. Code nodes are stable references or facts for source artifacts, symbols, ranges, anchors, and extracted code facts.

## Formal Blueprint

The current formal center of gravity is [IntentGraph Formal Blueprint](design/intentgraph-formal-blueprint.md). It is being revised toward the overlay state model and must change when prior-art review, milestone review, or benchmark evidence contradicts it.

After Phase 0, the next structure center of gravity is the [Intent Unit Model](design/intent-unit-model.md). Do not expand to a larger benchmark until Intent Units are reconsidered as semantic overlay mapping units rather than graph-as-source capsules.

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

Phase 0 is complete as of 2026-07-09. Read the [Phase 0 Final Review](reviews/phase-0-final-review.md) before proposing any new work.

P1.R through P1.18 corrected the model and proved it on the tiny CF0 code-first fixture. CF0 is now saturated proof evidence, not general scalability evidence.

P1.19 selected `B1-typescript-rest-api` as the next benchmark shape. The next recommended work is `P2.0 B1 TypeScript REST Code Fact Schema and Static Fixture`, described in [Phase 1 Entry Plan](roadmap/phase-1-entry-plan.md) and controlled by the [Product Capability Roadmap](roadmap/product-capability-roadmap.md). This is not authorization to build a broad extractor, UI/workbench product, or AI coding runtime.

Do not open compiler, extractor, verifier, package setup, UI, or AI runtime implementation until the relevant later milestone is current and its entry criteria are met.

## Stop Criteria

Stop and reassess if:

- a stronger existing system is found
- the slice duplicates an existing tool without a decision record
- the benchmark cannot distinguish IntentGraph from a code graph viewer, DSL tool, or model generator
- AI output is being treated as authority rather than proposal
- the overlay cannot preserve behavior contracts, evidence, authority, semantic history, or mapping consistency
- graph-first generation is treated as the universal model instead of a limited generated-code mode
