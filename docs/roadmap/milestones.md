# Milestones

This roadmap defines bounded work loops. Do not ask a worker to finish IntentGraph Development as a whole. Assign one milestone at a time.

## Current Authorized Milestone

Phase 0 is complete as of 2026-07-09. See the [Phase 0 Final Review](../reviews/phase-0-final-review.md).

No `M8` was opened automatically.

Current authorized work:

```text
P1.6 Repeatable B0 Typed Preservation Negative Probe Harness
```

This is a focused B0 typed-preservation negative-probe harness only, not broad Phase 1 authorization. See [Phase 1 Entry Plan](phase-1-entry-plan.md).

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

Goal: define the smallest graph/schema boundary that can describe intent, code references, generated-code mapping metadata for the Phase 0 experiment, evidence, authority, and change history.

Review: [M1 Milestone Review](../reviews/m1-review.md)

Entry criteria:

- M0 passed
- build/borrow/integrate decisions exist for language workbench and graph storage

Expected output:

- formal blueprint for the overlay graph, preservation metadata for generated-code mode, pass pipeline, and contracts
- language principles
- minimal GraphIR shape
- validation rules
- example graph fixture
- no compiler yet unless explicitly authorized

Quality target: Level 2.

## M2: Native Compiler Boundary

Goal: define and then implement the smallest deterministic graph-to-code path for a tiny generated-code benchmark.

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

Goal: reconstruct the graph from generated source code and preservation metadata for the generated-code experiment.

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

After M7, do not create M8 automatically. Phase 0 Quality Saturation Review is complete. The next approved step is P1.3 only.

## P1.R: Reframe IntentGraph as Semantic Overlay

Goal: revise the project framing from graph-as-source/compiler-first language to development-semantic overlay over existing source code.

Entry criteria:

- Phase 0 Final Review passed
- user approved the concept correction
- [Intent Unit Model](../design/intent-unit-model.md) exists
- [Phase 1 Entry Plan](phase-1-entry-plan.md) exists

Expected output:

- README, Start Here, Core Definition, Formal Blueprint, Intent Unit Model, roadmap, glossary, Phase 0 final review, prior-art map, and capability matrix updated to semantic-overlay framing
- explicit distinction between graph-first generation mode and code-first maintenance mode
- code node definition as reference/fact, not code text
- Intent Unit correction around `codeRef`, `codeFactRef`, and mapping obligations
- completion report for P1.R

Quality target: Level 4, Framing Correction Slice.

Non-goals:

- no larger benchmark yet
- no full language workbench
- no interactive IDE
- no broad code extractor
- no code-only exact reconstruction claim
- no automatic AI authority
- no continuation beyond P1.1 overlay mapping work until P1.1 is reviewed

## P1.0: Intent Unit Grammar Revision

Goal: historical generated-code experiment revision that converted B0 from flat GraphIR into explicit Intent Units.

Status: completed on 2026-07-09. See [P1.0 Intent Unit Grammar Review](../reviews/p1.0-intent-unit-grammar-review.md). P1.R supersedes its graph-as-source framing.

## P1.1: Intent Unit Overlay Mapping Revision

Goal: revise the Phase 0 flat GraphIR shape into Intent Unit centered overlay mappings without losing the B0 generated-code experiment, evidence, authority, history, AI proposal, and workbench boundaries.

Status: completed on 2026-07-09. See [P1.1 Intent Unit Overlay Mapping Review](../reviews/p1.1-intent-unit-overlay-mapping-review.md).

## P1.2: Tiny Code-First Maintenance Overlay Probe

Goal: prove the corrected semantic-overlay architecture on a tiny hand-written Python source fixture by extracting code facts, mapping Intent Units to those facts, and verifying behavior/mapping/evidence/authority/history without source text equality or hidden generated-code snapshots.

Status: completed on 2026-07-09. See [P1.2 Code-First Maintenance Overlay Review](../reviews/p1.2-code-first-maintenance-overlay-review.md).

## P1.3: Tiny Code-First Maintenance Delta Probe

Goal: prove the smallest code-first maintenance delta by adding `mul` behavior to CF0, capturing before/after code facts and overlay digests, updating Intent Units and semantic history, and verifying preservation plus new behavior without source text equality.

Status: completed after P1.3.R hardening on 2026-07-09. See [P1.3 Code-First Maintenance Delta Review](../reviews/p1.3-code-first-maintenance-delta-review.md).

## P1.4: Repeatable Code-First Delta Negative Probe Harness

Goal: commit a deterministic harness that proves the CF0 P1.3 delta verifier fails for wrong before-state digests/counts, missing expected facts, missing delta records, source-text equality, and hidden generated-code snapshot claims.

Status: completed on 2026-07-09. See [P1.4 Code-First Delta Negative Probes Review](../reviews/p1.4-code-first-delta-negative-probes-review.md).

## P1.5: B0 Typed Preservation Metadata Snapshot Reduction

Goal: reduce B0 generated-code full-snapshot dependence by preserving intent units, unit edges, evidence, authority, and history as typed metadata records with deterministic counts and digests while still acknowledging that full graph equality uses `hiddenState.sourceGraphSnapshot`.

Status: completed on 2026-07-09. See [P1.5 B0 Typed Preservation Review](../reviews/p1.5-b0-typed-preservation-review.md).

## P1.6: Repeatable B0 Typed Preservation Negative Probe Harness

Goal: commit a deterministic harness that proves B0 retrofit rejects missing, stale, unsorted, or boundary-violating typed preservation metadata.

Status: completed on 2026-07-09. See [P1.6 B0 Typed Preservation Negative Probes Review](../reviews/p1.6-b0-typed-preservation-negative-probes-review.md).
