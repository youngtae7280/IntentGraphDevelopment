# Milestones

This roadmap defines bounded work loops. Do not ask a worker to finish IntentGraph Development as a whole. Assign one milestone at a time.

## Current Authorized Milestone

Phase 0 is complete as of 2026-07-09. See the [Phase 0 Final Review](../reviews/phase-0-final-review.md).

No `M8` was opened automatically.

Most recent completed work:

```text
P7.2 WindowsUtility Read-Only Intent Mapping Hypothesis
```

This Phase G slice emitted read-only WindowsUtility mapping hypotheses outside the target repo. It does not authorize accepted mappings, source mutation, patch application, AI proposal authority, production UI, or productization. See [Product Capability Roadmap](product-capability-roadmap.md).

Long-range product capability roadmap:

- [Product Capability Roadmap](product-capability-roadmap.md)

That roadmap defines Phase A through Phase H, the phase gate rules, allowed work, non-goals, required outputs, verification gates, exit criteria, and stop conditions. It is the controlling roadmap for post-P1.18 planning, but it does not authorize all phases at once.

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

After M7, do not create M8 automatically. Phase 0 Quality Saturation Review is complete. Post-Phase-0 correction and CF0 proof-hardening slices are tracked as P1.R through P1.18 and remain bounded by explicit Coordinator approval.

Post-P1.18 work must follow the [Product Capability Roadmap](product-capability-roadmap.md). A later phase may start only when its phase gate is explicitly opened, its prior-art/build-borrow-integrate decision is current, and its verification criteria are written before implementation.

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

## P1.7: Tiny Code-First Behavior-Preserving Refactor Delta Probe

Goal: prove a tiny code-first refactor where `unit.behavior.mul` remains stable while implementation code facts migrate from `mul` to `multiply` and behavior remains unchanged.

Status: completed on 2026-07-09, with P1.7.R historical baseline correction. See [P1.7 Code-First Refactor Delta Review](../reviews/p1.7-code-first-refactor-delta-review.md).

## P1.7.R: Historical Delta Baseline Boundary Correction

Goal: ensure the P1.4 negative harness reruns the P1.3 additive delta against named historical P1.3 after-state facts, overlay, and source rather than current P1.7 refactor artifacts.

Status: completed on 2026-07-09. Review notes are recorded in the P1.4 and P1.7 reviews.

## P1.8: CF0 Historical State Index and Report Boundary

Goal: add a small deterministic CF0 historical state index that records P1.3 before/after states, the current P1.7 refactor state, artifact digests, and the delta transitions connecting them.

Status: completed on 2026-07-10. See [P1.8 CF0 Historical State Index Review](../reviews/p1.8-cf0-historical-state-index-review.md).

Non-goals:

- no new behavior delta
- no general history database
- no UI/workbench visualization
- no B0 generated-code pipeline changes
- no dependency addition

## P1.9: Tiny Code-First Overlay-Only Contract Delta Probe

Goal: model CF0's existing unsupported-operation fallback as an explicit IntentGraph contract, verification obligation, evidence record, authority record, and history transition without changing source behavior.

Status: completed on 2026-07-10. See [P1.9 Overlay-Only Contract Delta Review](../reviews/p1.9-overlay-only-contract-delta-review.md).

Non-goals:

- no broad planner
- no UI/workbench visualization
- no B0 generated-code pipeline changes
- no full semantic equivalence claim
- no source text equality requirement

## P1.10: Repeatable Overlay-Only Contract Delta Negative Probe Harness

Goal: add a deterministic CF0-specific harness proving P1.9 overlay-only contract delta failures are rejected for the intended reasons.

Status: completed on 2026-07-10. See [P1.10 Overlay Contract Negative Probes Review](../reviews/p1.10-overlay-contract-negative-probes-review.md).

Non-goals:

- no new behavior or contract unit
- no CF0 source behavior changes
- no general negative-probe framework
- no B0 generated-code pipeline changes
- no dependency addition

## P1.11: Tiny Code-First Overlay-Only Input Validation Contract Delta Probe

Goal: model CF0's existing invalid-integer input handling as an explicit IntentGraph contract, verification obligation, evidence record, authority record, and history transition without changing source behavior.

Status: completed on 2026-07-10. See [P1.11 Overlay-Only Invalid Integer Contract Review](../reviews/p1.11-overlay-invalid-integer-contract-review.md).

Non-goals:

- no CF0 source behavior changes
- no broad control-flow inference
- no UI/workbench visualization
- no B0 generated-code pipeline changes
- no P1.11 negative harness yet

## P1.12: Repeatable Input-Validation Overlay Contract Negative Probe Harness

Goal: add a deterministic CF0-specific harness proving P1.11 invalid-integer overlay-only contract delta failures are rejected for the intended reasons.

Status: completed on 2026-07-10. See [P1.12 Input Validation Negative Probes Review](../reviews/p1.12-input-validation-negative-probes-review.md).

Non-goals:

- no new behavior or contract unit
- no CF0 source behavior changes
- no generic negative-probe framework
- no B0 generated-code pipeline changes
- no dependency addition

## P1.13: Focused CF0 Negative Harness Pattern Consolidation

Goal: consolidate repeated CF0 negative-harness mechanics into a small CF0-local helper while preserving existing probe ids, counts, positive baselines, reports, and source behavior.

Status: completed on 2026-07-10. See [P1.13 CF0 Negative Harness Consolidation Review](../reviews/p1.13-cf0-negative-harness-consolidation-review.md).

Non-goals:

- no new behavior or contract unit
- no CF0 source behavior changes
- no overlay semantics changes
- no generic negative-probe framework
- no B0 generated-code pipeline changes
- no dependency addition

## P1.14: Tiny Code-First Overlay-Only Usage Arity Contract Delta Probe

Goal: model CF0's existing usage/arity handling as an explicit overlay-only contract with code facts, verification, evidence, authority, and history while preserving source bytes and historical baselines.

Status: completed on 2026-07-10. See [P1.14 Usage Arity Overlay Contract Review](../reviews/p1.14-usage-arity-overlay-contract-review.md).

Non-goals:

- no CF0 source behavior changes
- no broad control-flow inference
- no UI/workbench visualization
- no B0 generated-code pipeline changes
- no dependency addition
- no P1.14 negative harness yet

## P1.15: Repeatable Usage-Arity Overlay Contract Negative Probe Harness

Goal: add a deterministic CF0-specific harness proving P1.14 usage/arity overlay-only contract delta failures are rejected for intended reasons.

Status: completed on 2026-07-10. See [P1.15 Usage Arity Negative Probes Review](../reviews/p1.15-usage-arity-negative-probes-review.md).

Non-goals:

- no new behavior or contract unit
- no CF0 source behavior changes
- no B0 generated-code pipeline changes
- no dependency addition

## P1.16: CF0 Overlay Contract Harness Consolidation and Boundary Review

Goal: consolidate and review repeated CF0 overlay-contract negative harness mechanics while preserving explicit baseline scopes and CF0-specific boundaries.

Status: completed on 2026-07-10. See [P1.16 Overlay Contract Harness Consolidation Review](../reviews/p1.16-overlay-contract-harness-consolidation-review.md).

Non-goals:

- no new behavior or contract unit
- no CF0 source behavior changes
- no B0 generated-code pipeline changes
- no dependency addition
- no generic negative-probe framework claim
- no historical artifact removal

## P1.17: CF0 Code Fact Coverage and Overlay Completeness Report

Goal: emit a deterministic current-state report proving the CF0 overlay's code refs, code fact refs, mapping obligations, behavior verification, evidence, authority, and history resolve against extracted code facts.

Status: completed on 2026-07-10. See [P1.17 CF0 Overlay Coverage Review](../reviews/p1.17-cf0-overlay-coverage-review.md).

Non-goals:

- no new behavior or contract unit
- no CF0 source behavior changes
- no broad extractor or generic coverage framework
- no B0 generated-code pipeline changes
- no dependency addition

## P1.18: Phase One Direction and CF0 Specialization Review

Goal: review P1.R through P1.17 as a sequence, decide whether CF0 has become over-specialized, and select the next safe posture before adding more implementation scope.

Status: completed on 2026-07-10. See [P1.18 Phase One Direction and CF0 Specialization Review](../reviews/p1.18-phase-one-direction-specialization-review.md).

Decision:

- pause new CF0 semantic behavior/contract probes by default
- do not treat CF0 as proof of general scalability
- do not open a larger benchmark, broad extractor, or UI/workbench product automatically
- recommend `P1.19 Second Benchmark and Generalization Gate - Plan Only`

Non-goals:

- no new behavior or contract unit
- no CF0 source behavior changes
- no larger benchmark implementation
- no broad extractor or generic framework
- no B0 generated-code pipeline changes
- no dependency addition

## P1.19: Second Benchmark and Generalization Gate - Plan Only

Goal: select the next benchmark after saturated CF0 proof work, rerun the code-intelligence prior-art gate, define Phase B entry/pass/fail criteria, and recommend the next bounded implementation slice.

Status: completed on 2026-07-10. See [P1.19 Second Benchmark and Generalization Gate Review](../reviews/p1.19-second-benchmark-generalization-gate-review.md).

Decision:

- select `B1-typescript-rest-api`
- continue to `P2.0 B1 TypeScript REST Code Fact Schema and Static Fixture`
- build only an overlay-facing code fact contract first
- borrow or integrate mature code intelligence systems before broad extraction

Non-goals:

- no second benchmark implementation in P1.19
- no broad extractor
- no UI/workbench product
- no AI proposal generation
- no automatic authority
- no source code replacement claim

## P2.0: B1 TypeScript REST Code Fact Schema and Static Fixture

Goal: create the first non-CF0, multi-file B1 fixture and prove a deterministic code fact schema/report boundary for Phase B.

Status: completed on 2026-07-10. See [P2.0 B1 Code Fact Schema Static Fixture Review](../reviews/p2.0-b1-code-fact-schema-static-fixture-review.md).

Decision:

- B1 fixture exists
- code fact schema v0 exists
- B1 extractor is fixture-bounded and deterministic
- B1 validator and negative probes pass
- continue to `P2.1 B1 Incremental Code Fact Change Probe`

Non-goals:

- no broad TypeScript extractor
- no external code intelligence integration
- no Intent Unit mapping
- no AI proposal generation
- no UI/workbench product
- no real-project adoption

## P2.1: B1 Incremental Code Fact Change Probe

Goal: prove that a bounded one-file B1 source change produces expected added/changed facts and relations while unchanged files remain stable.

Status: completed on 2026-07-10. See [P2.1 B1 Incremental Code Fact Change Review](../reviews/p2.1-b1-incremental-code-fact-change-review.md).

Decision:

- before-state B1 facts and source captured
- one source file changed: `src/service/todoService.ts`
- `completeTodo` fact added
- expected relation delta verified
- negative probes pass
- continue to `P2.2 B1 Code Fact Boundary Review and Phase C Entry Plan`

Non-goals:

- no Intent Unit mapping
- no broad extractor
- no performance benchmark
- no UI/workbench product
- no AI proposal generation
- no real-project adoption

## P2.2: B1 Code Fact Boundary Review and Phase C Entry Plan

Goal: review P2.0 and P2.1 as Phase B evidence, decide whether B1 facts are stable enough for Phase C, and define the first mapping slice.

Status: completed on 2026-07-10. See [P2.2 B1 Code Fact Boundary Phase C Entry Review](../reviews/p2.2-b1-code-fact-boundary-phase-c-entry-review.md).

Decision:

- Phase B static and incremental B1 fact boundaries are sufficient to open bounded Phase C
- continue to `P3.0 B1 Intent Unit Mapping Schema and Static Overlay Fixture`

Non-goals:

- no mapping implementation in P2.2
- no code edits
- no broad extractor
- no UI/workbench product
- no AI proposal generation
- no productization

## P3.0: B1 Intent Unit Mapping Schema and Static Overlay Fixture

Goal: create the first static B1 Intent Unit overlay and deterministic mapping verifier over B1 code facts.

Status: completed on 2026-07-10. See [P3.0 B1 Intent Unit Mapping Review](../reviews/p3.0-b1-intent-unit-mapping-review.md).

Decision:

- B1 mapping schema v0 exists
- B1 static overlay exists
- mapping verifier and negative probes pass
- continue to `P3.1 B1 Stale Intent Mapping Change Probe`

Non-goals:

- no code edits
- no automatic mapping generation
- no natural-language request interpretation
- no broad planner
- no UI/workbench product
- no productization

## P3.1: B1 Stale Intent Mapping Change Probe

Goal: prove stale mappings fail deterministically when a mapped B1 code fact disappears.

Status: completed on 2026-07-10. See [P3.1 B1 Stale Intent Mapping Change Review](../reviews/p3.1-b1-stale-intent-mapping-change-review.md).

Decision:

- stale code fact report generated
- verifier fails on missing `fact.function.addtodo`
- stale mapping probe report passes
- continue to `P3.2 B1 Ambiguous Intent Mapping Candidate Probe`

Non-goals:

- no source edit
- no automatic mapping repair
- no AI mapping generation
- no code planning
- no UI/workbench product
- no productization

## P3.2: B1 Ambiguous Intent Mapping Candidate Probe

Goal: model an explicit ambiguous mapping candidate and verify it remains unresolved and outside the accepted overlay.

Status: completed on 2026-07-10. See [P3.2 B1 Ambiguous Mapping Candidate Review](../reviews/p3.2-b1-ambiguous-mapping-candidate-review.md).

Decision:

- ambiguous mapping candidate artifact exists
- candidate facts resolve
- candidate is not accepted
- negative probes pass
- continue to `P3.3 Phase C Mapping Boundary Review and Phase D Entry Plan`

Non-goals:

- no ambiguity resolution
- no code edit
- no automatic mapping generation
- no authority grant
- no code planning
- no UI/workbench product
- no productization

## P3.3: Phase C Mapping Boundary Review and Phase D Entry Plan

Goal: review P3.0 through P3.2 as Phase C evidence and decide whether bounded Phase D change planning can open.

Status: completed on 2026-07-10. See [P3.3 Phase C Mapping Boundary Phase D Entry Review](../reviews/p3.3-phase-c-mapping-boundary-phase-d-entry-review.md).

Decision:

- Phase C is sufficient to open the first bounded Phase D slice.
- Continue to `P4.0 B1 Change Proposal Schema and Non-Applied Plan`.
- Phase D starts proposal-only and non-applied.

Non-goals:

- no source mutation
- no patch application
- no automatic proposal acceptance
- no AI authority
- no automatic ambiguity resolution
- no broad planner
- no UI/workbench product
- no broadened extraction
- no productization

## P4.0: B1 Change Proposal Schema and Non-Applied Plan

Goal: define and validate the first B1 proposal-only change-planning artifact.

Status: completed on 2026-07-10. See [P4.0 B1 Change Proposal Non-Applied Plan Review](../reviews/p4.0-b1-change-proposal-non-applied-plan-review.md).

Decision:

- B1 change proposal schema exists.
- non-applied `complete todo route` proposal exists.
- proposal validator and negative probes pass.
- continue to `P4.1 Phase D Change Proposal Boundary Review and Phase E Entry Plan`.

Non-goals:

- no source mutation
- no patch application
- no automatic proposal acceptance
- no AI authority
- no automatic ambiguity resolution
- no broad planner
- no UI/workbench product
- no broadened extraction
- no productization

## P4.1: Phase D Change Proposal Boundary Review and Phase E Entry Plan

Goal: review P4.0 as Phase D evidence and decide whether bounded Phase E consistency verification can open.

Status: completed on 2026-07-10. See [P4.1 Phase D Change Proposal Boundary Phase E Entry Review](../reviews/p4.1-phase-d-change-proposal-boundary-phase-e-entry-review.md).

Decision:

- Phase D is sufficient to open the first bounded Phase E slice.
- Continue to `P5.0 B1 Proposal Consistency Verifier`.
- Phase E starts deterministic and non-applied.

Non-goals:

- no source mutation
- no patch application
- no proposal acceptance
- no AI judgment as verifier
- no full semantic equivalence claim
- no UI/workbench product
- no productization

## P5.0: B1 Proposal Consistency Verifier

Goal: verify consistency between the P4.0 non-applied proposal, proposal validation report, B1 code facts, and B1 overlay mappings.

Status: completed on 2026-07-10. See [P5.0 B1 Proposal Consistency Verifier Review](../reviews/p5.0-b1-proposal-consistency-verifier-review.md).

Decision:

- B1 proposal consistency verifier exists.
- positive consistency report passes.
- negative probes pass.
- continue to `P5.1 Phase E Consistency Verifier Boundary Review and Phase F Entry Plan`.

Non-goals:

- no source mutation
- no patch application
- no proposal acceptance
- no AI judgment as verifier
- no full semantic equivalence claim
- no UI/workbench product
- no productization

## P5.1: Phase E Consistency Verifier Boundary Review and Phase F Entry Plan

Goal: review P5.0 as Phase E evidence and decide whether bounded Phase F workbench projection can open.

Status: completed on 2026-07-10. See [P5.1 Phase E Consistency Boundary Phase F Entry Review](../reviews/p5.1-phase-e-consistency-boundary-phase-f-entry-review.md).

Decision:

- Phase E is sufficient to open the first bounded Phase F slice.
- Continue to `P6.0 B1 Workbench Projection Schema and Static HTML Preview`.
- Phase F starts as static projection and preview only.

Non-goals:

- no source mutation
- no patch application
- no proposal acceptance
- no production app
- no editor or GitHub integration
- no visualization-as-verifier claim
- no productization

## P6.0: B1 Workbench Projection Schema and Static HTML Preview

Goal: emit a deterministic B1 workbench projection and static HTML preview for the non-applied proposal workflow.

Status: completed on 2026-07-10. See [P6.0 B1 Workbench Projection Static HTML Review](../reviews/p6.0-b1-workbench-projection-static-html-review.md).

Decision:

- B1 workbench projection JSON exists.
- static HTML preview exists.
- projection validation report passes.
- continue to `P6.1 Phase F Workbench Boundary Review and Phase G Entry Plan`.

Non-goals:

- no source mutation
- no patch application
- no proposal acceptance
- no visualization-as-verifier claim
- no production app
- no editor or GitHub integration
- no productization

## P6.1: Phase F Workbench Boundary Review and Phase G Entry Plan

Goal: review P6.0 as Phase F evidence and decide whether a plan-only Phase G real-project adoption gate can open.

Status: completed on 2026-07-10. See [P6.1 Phase F Workbench Boundary Phase G Entry Review](../reviews/p6.1-phase-f-workbench-boundary-phase-g-entry-review.md).

Decision:

- Phase F is sufficient to open a plan-only real-project adoption gate.
- Continue to `P7.0 Real Project Adoption Target and Benchmark Plan`.
- Phase G starts plan-only.

Non-goals:

- no real-project source mutation
- no broad unbounded retrofit
- no AI-generated code application
- no product readiness claim
- no CLI/app/editor/GitHub productization

## P7.0: Real Project Adoption Target and Benchmark Plan

Goal: select the first real-project adoption target and define benchmark criteria before touching the target.

Status: completed on 2026-07-10. See [P7.0 Real Project Adoption Target Benchmark Plan Review](../reviews/p7.0-real-project-adoption-target-benchmark-plan-review.md).

Decision:

- select `C:\Users\ytkim\Desktop\kyt_work\WindowsUtility`
- start read-only because the target is ahead of origin and has untracked `.devview/`
- continue to `P7.1 WindowsUtility Read-Only Retrofit Inventory Plan and Source Snapshot`

Non-goals:

- no writing to WindowsUtility
- no real-project source mutation
- no unbounded retrofit
- no AI-generated code application
- no product readiness claim
- no productization

## P7.1: WindowsUtility Read-Only Retrofit Inventory Plan and Source Snapshot

Goal: inventory WindowsUtility from outside the target repository and prove the target stays unchanged.

Status: completed on 2026-07-10. See [P7.1 WindowsUtility Read-Only Inventory Review](../reviews/p7.1-windowsutility-readonly-inventory-review.md).

Decision:

- read-only inventory artifacts exist in this repository.
- WindowsUtility git status and selected file digests stayed unchanged.
- continue to `P7.2 WindowsUtility Read-Only Intent Mapping Hypothesis`.

Non-goals:

- no writing to WindowsUtility
- no real-project source mutation
- no unbounded retrofit
- no AI-generated code application
- no product readiness claim
- no productization

## P7.2: WindowsUtility Read-Only Intent Mapping Hypothesis

Goal: derive candidate Intent Units, code-surface mappings, evidence gaps, authority gaps, and ambiguity records from the WindowsUtility inventory without touching the target.

Status: completed on 2026-07-10. See [P7.2 WindowsUtility Read-Only Mapping Hypothesis Review](../reviews/p7.2-windowsutility-readonly-mapping-hypothesis-review.md).

Decision:

- read-only mapping hypothesis artifacts exist in this repository.
- WindowsUtility git status stayed unchanged.
- mappings remain hypotheses, not accepted mappings.
- continue to `P7.3 Real Project Adoption Boundary Review and Productization Readiness Gate`.

Non-goals:

- no writing to WindowsUtility
- no accepted mappings
- no real-project source mutation
- no unbounded retrofit
- no AI-generated code application
- no product readiness claim
- no productization

## P7.3: Real Project Adoption Boundary Review and Productization Readiness Gate

Goal: review P7.0 through P7.2 real-project adoption evidence and decide whether productization can open.

Status: completed on 2026-07-10. See [P7.3 Real Project Adoption Boundary Productization Readiness Review](../reviews/p7.3-real-project-adoption-boundary-productization-readiness-review.md).

Decision:

- productization is not ready.
- Phase H may open only for `P8.0 Productization Readiness Gap Report and Stabilization Plan`.
- package/release, editor integration, GitHub workflow integration, team workflow automation, and product readiness claims remain unauthorized.

Non-goals:

- no writing to WindowsUtility
- no accepted real-project mappings
- no real-project source mutation
- no proposal application
- no AI-generated code application
- no productization implementation
- no product readiness claim

## P8.0: Productization Readiness Gap Report and Stabilization Plan

Goal: convert productization blockers into a deterministic checklist and stabilization plan.

Status: completed on 2026-07-10. See [P8.0 Productization Readiness Gap Stabilization Review](../reviews/p8.0-productization-readiness-gap-stabilization-review.md).

Decision:

- productization is blocked.
- stabilization is required before any product implementation.
- next safe work must address real-project repository state, accepted mappings, real proposal/evidence/authority loops, real workbench projection, user workflow benchmarks, and product surface decisions.

Non-goals:

- no writing to WindowsUtility
- no accepted real-project mappings
- no real-project source mutation
- no proposal application
- no packaging or release
- no editor/GitHub/team workflow integration
- no AI authority promotion
- no product readiness claim

## P8.1: WindowsUtility Repository State Resolution Plan

Goal: record how the selected real-project target state must be resolved before target writes or accepted mappings.

Status: completed on 2026-07-10. See [P8.1 WindowsUtility Repository State Resolution Plan Review](../reviews/p8.1-windowsutility-repository-state-resolution-plan-review.md).

Decision:

- WindowsUtility target state is unresolved.
- target writes remain blocked.
- accepted mappings and productization remain blocked until state is resolved or explicitly scoped.

Non-goals:

- no writing to WindowsUtility
- no target cleanup
- no target commit/push
- no accepted real-project mappings
- no proposal application
- no productization implementation
- no product readiness claim
