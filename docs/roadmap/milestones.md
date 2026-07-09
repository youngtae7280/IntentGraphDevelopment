# Milestones

This roadmap defines bounded work loops. Do not ask a worker to finish IntentGraph Development as a whole. Assign one milestone at a time.

## Current Authorized Milestone

Phase 0 is complete as of 2026-07-09. See the [Phase 0 Final Review](../reviews/phase-0-final-review.md).

No `M8` or Phase 1 milestone is authorized automatically. Phase 1 requires explicit user approval.

## M0: Research and Thesis Foundation

Goal: make the concept, prior-art landscape, and first benchmark criteria stable enough to justify a first implementation slice.

Review: [M0 Milestone Review](../reviews/m0-review.md)

Allowed work:

- refine the core thesis
- expand the prior-art map
- update the capability matrix
- write initial build/borrow/integrate decisions
- define benchmark candidates
- write a milestone review

Non-goals:

- no compiler implementation
- no reconstructor implementation
- no graph schema implementation
- no package setup
- no UI
- no AI agent runtime

Done criteria:

- `docs/concept/core-thesis.md` is clear enough to compare against prior art
- `docs/research/prior-art-map.md` includes the strongest known systems by category
- `docs/research/capability-matrix.md` has notes sufficient to guide build/borrow/integrate decisions
- `docs/decisions/build-borrow-integrate-decisions.md` contains initial decisions for code graph extraction, language workbench ideas, round-trip semantics, visualization, and AI workflow
- `docs/research/benchmark-plan.md` identifies the first benchmark project and pass/fail criteria
- milestone review says `continue` or `improve`; if `improve`, the worker must improve before closing

Quality target: Level 2, Benchmarked Slice Preparation.

## M1: IntentGraph Language and GraphIR Boundary

Goal: define the smallest source graph language and canonical GraphIR that can describe a tiny program, generated source mapping metadata, evidence, authority, and change history.

Review: [M1 Milestone Review](../reviews/m1-review.md)

Entry criteria:

- M0 passed
- build/borrow/integrate decisions exist for language workbench and graph storage

Expected output:

- formal blueprint for the source graph, preservation metadata, pass pipeline, and contracts
- language principles
- minimal GraphIR shape
- validation rules
- example graph fixture
- no compiler yet unless explicitly authorized

Quality target: Level 2.

## M2: Native Compiler Boundary

Goal: define and then implement the smallest deterministic graph-to-code path for a tiny benchmark.

Review: [M2 Milestone Review](../reviews/m2-review.md)

Entry criteria:

- M1 passed
- first benchmark selected
- round-trip preservation metadata requirements documented

Expected output:

- graph-to-code compilation contract
- source metadata preservation contract
- tiny generated project

Quality target: Level 3, Round-Trip Slice after M3.

## M3: Retrofit Reconstructor Boundary

Goal: reconstruct the graph from generated source code and preservation metadata.

Review: [M3 Milestone Review](../reviews/m3-review.md)

Entry criteria:

- M2 generated source and metadata exist

Expected output:

- reconstruction contract
- reconstructed graph output
- documented loss model for code-only reconstruction

Quality target: Level 3.

## M4: Round-Trip Verifier

Goal: compare original graph and reconstructed graph under declared equality/projection rules.

Review: [M4 Milestone Review](../reviews/m4-review.md)

Entry criteria:

- M2 and M3 passed

Expected output:

- equality rules
- projection rules
- verifier report
- first `Retrofit(Native(G)) = G` proof for a tiny graph

Quality target: Level 3.

## M5: Evidence and Authority Slice

Goal: preserve evidence, authority, and change history through the graph/code/reconstruction loop.

Review: [M5 Milestone Review](../reviews/m5-review.md)

Entry criteria:

- M4 passed

Expected output:

- evidence model
- authority model
- change history model
- verifier coverage for those fields

Quality target: Level 4.

## M6: AI Proposal Boundary

Goal: allow AI to propose graph/code deltas while keeping acceptance deterministic.

Review: [M6 Milestone Review](../reviews/m6-review.md)

Entry criteria:

- M5 passed

Expected output:

- proposal format
- validator boundary
- human review boundary
- no automatic authority for AI output

Quality target: Level 4.

## M7: Workbench and Visualization Boundary

Goal: visualize graph, code projection, evidence, authority, and round-trip state.

Review: [M7 Milestone Review](../reviews/m7-review.md)

Entry criteria:

- M4 passed at minimum
- M5 preferred

Expected output:

- visualization requirements
- graph navigation model
- comparison with existing graph visualization tools

Quality target: Level 2 or higher.

## Promotion Rule

Do not open the next milestone until the current milestone has a written milestone review.

After M7, do not create M8 automatically. Phase 0 Quality Saturation Review is complete; wait for explicit user approval before opening Phase 1.
