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

P1.19 selected `B1-typescript-rest-api` as the next benchmark shape. P2.0 created the first bounded B1 fixture, code fact schema, extractor, validator, and negative probes. P2.1 proved a one-file incremental code fact change. P2.2 opened Phase C only for a bounded static B1 mapping slice. P3.0 created the B1 Intent Unit mapping overlay and verifier. P3.1 proved stale mapping failure. P3.2 proved ambiguous mapping candidates remain unresolved. P3.3 reviewed the Phase C boundary. P4.0 created the first non-applied B1 change proposal schema, proposal artifact, validator, and negative probes. P4.1 reviewed the Phase D boundary. P5.0 added deterministic B1 proposal consistency verification. P5.1 opened Phase F. P6.0 added a deterministic B1 workbench projection and static HTML preview. P6.1 opened Phase G. P7.0 selected WindowsUtility as the first real-project target, read-only first. P7.1 emitted a read-only WindowsUtility inventory. P7.2 emitted read-only WindowsUtility mapping hypotheses. P7.3 found productization not ready. P8.0 converted that into a productization readiness gap report and stabilization plan. P8.1 recorded that WindowsUtility target state was unresolved. P8.2 defined the accepted mapping boundary. P8.3 selected shell-workspace as the first candidate. P8.4 created a shell-workspace mapping draft outside WindowsUtility without accepting it. P8.5 added repeatable mapping draft negative probes. P8.6 resolved WindowsUtility target state to clean/aligned. P8.7 says the mapping is ready to request human acceptance, but still unaccepted, controlled by the [Product Capability Roadmap](roadmap/product-capability-roadmap.md).

Do not open compiler, extractor, verifier, package setup, UI, or AI runtime implementation until the relevant later milestone is current and its entry criteria are met.

## Stop Criteria

Stop and reassess if:

- a stronger existing system is found
- the slice duplicates an existing tool without a decision record
- the benchmark cannot distinguish IntentGraph from a code graph viewer, DSL tool, or model generator
- AI output is being treated as authority rather than proposal
- the overlay cannot preserve behavior contracts, evidence, authority, semantic history, or mapping consistency
- graph-first generation is treated as the universal model instead of a limited generated-code mode
