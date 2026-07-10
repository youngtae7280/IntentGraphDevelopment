# Phase 1 Entry Plan

Status: user-authorized correction phase, not broad Phase 1 authorization

Phase 0 passed the approved feasibility scope, but its graph-first framing must be narrowed. The next work must not add a larger benchmark or a richer UI. First, IntentGraph must be reframed as a development-semantic overlay over existing source code.

## Entry Thesis

Corrected state model:

```text
D = (I, C, X, M, E, A, H)
```

Where `I` is intent/behavior/verification graph, `C` is source code artifacts, `X` is extracted code fact graph, `M` is mapping between `I` and `X/C`, `E` is evidence, `A` is authority, and `H` is semantic history.

Default operation frame:

```text
Extract(C) -> X
Map(I, X) -> M
Plan(I, C, X, M, request) -> DeltaC, DeltaI, DeltaM
Verify(I, C', X', M', E, A) -> pass/fail
Record(H, accepted delta)
```

Graph-first generation remains a limited greenfield/generated-code mode:

```text
G -> Native(G) -> (C, mu) -> Retrofit(C, mu) -> G' -> Verify(G, G')
```

## Completed Slice: P1.R Reframe IntentGraph as Semantic Overlay

Goal: correct the repository framing so IntentGraph is defined as a semantic overlay and consistency/change orchestration engine, not a replacement source language or universal graph-to-code compiler.

Expected changes:

- define IntentGraph as a development-semantic overlay graph linked to source code artifacts
- define code nodes as stable references or facts, not code text
- reinterpret Phase 0 as a tiny metadata-backed generated-code experiment
- revise Intent Units as semantic work units with `codeRef`, `codeFactRef`, and mapping obligations
- keep evidence, authority, semantic history, AI proposal, and workbench projection boundaries intact

Non-goals:

- no new compiler
- no code extraction implementation
- no larger benchmark
- no UI
- no continuation of unit-structured compiler work until the reframing is reviewed
- no prior-art deep search without explicit approval

## Historical Slice: P1.0 Intent Unit Grammar Revision

Goal: revise the Phase 0 B0 graph from a flat GraphIR into a unit-structured GraphIR without weakening the generated-code round-trip, evidence, authority, history, AI proposal, or workbench boundaries.

Status: passed on 2026-07-09. See [P1.0 Intent Unit Grammar Review](../reviews/p1.0-intent-unit-grammar-review.md).

P1.0 must now be read through P1.R. It remains useful implementation evidence, but its graph-as-source/compiler language is superseded by the semantic-overlay framing.

## Completed Slice: P1.1 Intent Unit Overlay Mapping Revision

Goal: revise B0 Intent Units into semantic overlay mapping units with `codeRefs`, `codeFactRefs`, and `mappingObligations` while preserving the existing B0 generated-code experiment as one limited mode.

P1.1 resolves the naming ambiguity: `P1.0` is historical and `P1.1` is the overlay mapping revision.

## Completed Slice: P1.2 Tiny Code-First Maintenance Overlay Probe

Goal: add a tiny hand-written Python calculator source fixture, extract deterministic code facts from it, map Intent Units to those facts, and verify behavior/mapping/evidence/authority/history without requiring source text equality.

P1.2 is the first code-first maintenance proof. It must not generate source code from the graph and must not rely on a hidden generated-code snapshot.

## Completed Slice: P1.12 Repeatable Input-Validation Overlay Contract Negative Probe Harness

Goal: harden the P1.11 invalid-integer overlay-only contract delta with repeatable negative probes.

After P1.11, CF0 can model existing invalid-integer behavior as an overlay-only input-validation contract delta. P1.12 proves the verifier rejects bad input-validation deltas for source/overlay flag errors, missing contract coverage, missing stderr/exit-code verification, missing fact mappings, and missing evidence/authority/history records.

Status: completed on 2026-07-10. See [P1.12 Input Validation Negative Probes Review](../reviews/p1.12-input-validation-negative-probes-review.md).

## Completed Slice: P1.13 Focused CF0 Negative Harness Pattern Consolidation

Goal: reduce repeated CF0 negative-harness mechanics without changing CF0 behavior, overlay semantics, or probe expectations.

P1.13 is a quality cleanup slice. CF0 now has repeatable negative harnesses for the P1.4 additive delta, P1.10 unsupported-operation overlay contract, and P1.12 invalid-integer overlay contract. The harnesses should share small support code for path handling, JSON I/O, positive baseline reruns, verifier invocation, temporary probe setup, and expected-failure matching.

Status: completed on 2026-07-10. See [P1.13 CF0 Negative Harness Consolidation Review](../reviews/p1.13-cf0-negative-harness-consolidation-review.md).

## Completed Slice: P1.14 Tiny Code-First Overlay-Only Usage Arity Contract Delta Probe

Goal: model CF0's existing usage/arity handling as an explicit IntentGraph contract, verification obligation, evidence record, authority record, and history transition without changing source behavior.

P1.14 must first preserve the P1.11 after-state as historical artifacts so the P1.12 negative harness no longer depends on mutable current P1.14 facts or overlay. Then it may add a usage/arity unit, mapping obligations, behavior smoke check, delta artifact, report, and state-index transition.

Status: completed on 2026-07-10. See [P1.14 Usage Arity Overlay Contract Review](../reviews/p1.14-usage-arity-overlay-contract-review.md).

## Completed Slice: P1.15 Repeatable Usage-Arity Overlay Contract Negative Probe Harness

Goal: harden the P1.14 usage/arity overlay-only contract delta with repeatable negative probes.

P1.15 must not add semantic coverage. It should start from the committed good P1.14 inputs, mutate temporary copies, run `tools/verify_code_first_delta.py`, and pass only when each bad input fails for the expected reason.

Status: completed on 2026-07-10. See [P1.15 Usage Arity Negative Probes Review](../reviews/p1.15-usage-arity-negative-probes-review.md).

## Completed Slice: P1.16 CF0 Overlay Contract Harness Consolidation and Boundary Review

Goal: consolidate and review the repeated CF0 overlay-contract negative harness pattern now that P1.10, P1.12, and P1.15 exist.

P1.16 is a quality/hardening slice. It may move low-risk repeated report-building mechanics into `tools/cf0_probe_support.py`, but each harness must keep explicit baseline identity and phase-specific probes.

Do not open a larger benchmark, UI, AI runtime, broader compiler slice, broad extractor, or another semantic contract automatically.

Expected changes:

- update `tools/cf0_probe_support.py` if consolidation improves clarity
- update P1.10, P1.12, and P1.15 harnesses only as needed
- emit `generated/cf0-python-cli-calculator/p1.16-overlay-contract-harness-review-report.json`
- add P1.16 review notes
- keep P1.4, P1.7, P1.9, P1.10, P1.11, P1.12, P1.14, P1.15, and state-index regressions passing

Non-goals:

- no larger benchmark yet
- no broad language workbench
- no interactive IDE
- no arbitrary code extractor
- no Graphify/CodeQL/Joern replacement
- no claim that source code alone recovers full intent, evidence, authority, or history
- no automatic AI authority
- no new behavior unit for the implementation rename
- no source text equality requirement
- no new feature delta
- no general history engine
- no source behavior change
- no product behavior change
- no new behavior or contract unit
- no generic negative-probe framework claim

## Required Output For P1.16

P1.16 should produce:

- consolidated helper support or explicit no-refactor rationale
- `generated/cf0-python-cli-calculator/p1.16-overlay-contract-harness-review-report.json`
- P1.16 review notes
- updated validation rule for overlay-contract harness boundary review

## Acceptance Criteria

P1.16 passes only if:

1. P1.10, P1.12, and P1.15 harnesses still pass.
2. Baseline scopes remain explicit and correct.
3. The review report records probe counts, current/historical artifact use, expected failure status, and boundary flags.
4. P1.4, P1.7, P1.9, P1.11, P1.14, and state-index regressions still pass.
5. CF0 source bytes remain unchanged.
6. Any helper consolidation remains CF0-specific and does not claim a generic framework.

## Stop Conditions

Stop and report before broadening scope if:

- any harness positive baseline fails.
- a required bad case passes unexpectedly.
- a required bad case fails only because of an unrelated baseline problem.
- probe ids/counts drift without an explicit quality reason.
- P1.4 positive historical baseline does not pass.
- P1.7, P1.9, or P1.11 report stops passing.
- P1.10 or P1.12 stop using historical artifacts.
- P1.15 stops clearly declaring current P1.14 artifacts.
- CF0 source bytes change without an explicit stop-and-review decision.
- IntentGraph is described again as a universal source-code replacement.
- The project starts duplicating mature language workbench, code graph, or provenance systems without a build/borrow/integrate decision.

## Suggested Worker Task

Task name:

```text
P1.16 CF0 Overlay Contract Harness Consolidation and Boundary Review
```

Worker should start from:

- `docs/examples/cf0-python-cli-calculator/source/calc.py`
- `docs/examples/cf0-python-cli-calculator/intentgraph.overlay.json`
- `tools/verify_code_first_delta.py`
- `tools/run_cf0_delta_negative_probes.py`
- `tools/emit_cf0_historical_state_index.py`
- `docs/examples/cf0-python-cli-calculator/deltas/p1.9-overlay-unsupported-operation.delta.json`
- `tools/run_cf0_overlay_contract_negative_probes.py`
- `tools/run_cf0_input_validation_negative_probes.py`
- `docs/examples/cf0-python-cli-calculator/deltas/p1.11-overlay-invalid-integer.delta.json`
- `docs/examples/cf0-python-cli-calculator/deltas/p1.14-overlay-usage-arity.delta.json`
- `tools/cf0_probe_support.py`
- `tools/run_cf0_overlay_contract_negative_probes.py`
- `tools/run_cf0_input_validation_negative_probes.py`
- `tools/run_cf0_usage_arity_negative_probes.py`
- `generated/cf0-python-cli-calculator/p1.11-before-code-facts.json`
- `generated/cf0-python-cli-calculator/p1.11-before-overlay.json`
- `generated/cf0-python-cli-calculator/p1.14-before-code-facts.json`
- `generated/cf0-python-cli-calculator/p1.14-before-overlay.json`
- `generated/cf0-python-cli-calculator/p1.7-refactor-delta-report.json`
- `generated/cf0-python-cli-calculator/cf0-historical-state-index.json`

Status: completed on 2026-07-10. See [P1.16 Overlay Contract Harness Consolidation Review](../reviews/p1.16-overlay-contract-harness-consolidation-review.md).

## Completed Slice: P1.17 CF0 Code Fact Coverage and Overlay Completeness Report

Goal: emit a deterministic current-state coverage report for the CF0 code-first overlay.

P1.17 proves that the current overlay's `codeRefs`, `codeFactRefs`, mapping obligations, behavior verification, evidence, authority, and history resolve against current extracted code facts. It also makes the intentional boundary explicit: structural low-level code facts such as built-in parsing/printing calls do not automatically become standalone Intent Units.

Produced artifacts:

- `tools/emit_cf0_overlay_coverage_report.py`
- `generated/cf0-python-cli-calculator/p1.17-overlay-coverage-report.json`
- [P1.17 CF0 Overlay Coverage Review](../reviews/p1.17-cf0-overlay-coverage-review.md)

Acceptance summary:

- required behavior units present: add, sub, mul, unsupported-operation, invalid-integer-input, usage-arity
- unresolved overlay refs: 0
- unresolved mapping obligations: 0
- unclassified uncovered facts: 0
- source bytes unchanged
- source text equality not required
- hidden generated-code snapshot not used
- AI authority not promoted

No next Phase 1 slice is opened automatically. The next step should be selected by the Coordinator after reviewing whether to continue with CF0 workbench projection, another small semantic coverage probe, or a broader planning/research gate.

## Completed Slice: P1.18 Phase One Direction and CF0 Specialization Review

Goal: review P1.R through P1.17 as a sequence and decide whether more CF0 work would keep improving the architecture or overfit the tiny fixture.

Decision:

```text
pause-new-cf0-semantic-probes
```

Rationale:

- CF0 now proves the corrected semantic-overlay model on a tiny code-first fixture.
- CF0 has additive behavior, refactor, overlay-only contracts, negative harnesses, historical indexing, and coverage reporting.
- More CF0 behavior/contract slices would mostly improve one fixture rather than test generality.
- Broad Phase 1 remains unauthorized.

Produced artifacts:

- `generated/cf0-python-cli-calculator/p1.18-phase-one-direction-review-report.json`
- [P1.18 Phase One Direction and CF0 Specialization Review](../reviews/p1.18-phase-one-direction-specialization-review.md)

Recommended next slice:

```text
P1.19 Second Benchmark and Generalization Gate - Plan Only
```

The next slice should not implement a larger benchmark. It should select what limitation of CF0 must be tested next, rerun the prior-art/build-borrow-integrate gate, and define pass/fail criteria before implementation.

P1.19 must also align the next work with the [Product Capability Roadmap](product-capability-roadmap.md). In that roadmap, the next likely capability area is Phase B, Fast Retrofit and Code Facts. P1.19 is only the planning gate for that direction; it does not authorize the Phase B implementation.

Minimum P1.19 outputs:

- second benchmark candidate comparison
- selected CF0 limitation to test next
- prior-art/build-borrow-integrate decision for the selected direction
- Phase B entry criteria
- Phase B allowed work and non-goals
- deterministic validation plan
- pass/fail criteria
- worker handoff instructions

P1.19 must stop before implementation if these criteria are not clear.

## Completed Slice: P1.19 Second Benchmark and Generalization Gate - Plan Only

Goal: select the next benchmark shape, rerun the code-intelligence prior-art gate, and define Phase B entry criteria before implementation.

Decision:

```text
continue-to-p2.0-b1-typescript-rest-code-fact-schema
```

Selected benchmark:

```text
B1-typescript-rest-api
```

Rationale:

- CF0 is single-file Python and does not test cross-file mapping.
- B1 tests multi-file imports, route/service/model/test facts, and non-Python extraction pressure.
- A REST-style service avoids pulling UI/workbench concerns into Phase B too early.
- A desktop utility is deferred until the code fact contract is stable.

Produced artifacts:

- [P1.19 Second Benchmark and Generalization Gate Review](../reviews/p1.19-second-benchmark-generalization-gate-review.md)
- `generated/roadmap/p1.19-second-benchmark-generalization-report.json`
- build/borrow/integrate decision 011 in [Build / Borrow / Integrate Decisions](../decisions/build-borrow-integrate-decisions.md)

Recommended next slice:

```text
P2.0 B1 TypeScript REST Code Fact Schema and Static Fixture
```

P2.0 is the first Phase B implementation slice. It may create the tiny B1 fixture and code fact schema/report boundary, but it must not become a broad extractor, Graphify clone, UI/workbench product, or AI coding runtime.

## Completed Slice: P2.0 B1 TypeScript REST Code Fact Schema and Static Fixture

Goal: create the first bounded Phase B B1 fixture and deterministic code fact validation boundary.

Produced artifacts:

- `docs/examples/b1-typescript-rest-api/source/**`
- [Code Fact Schema v0](../language/code-fact-schema-v0.md)
- `tools/extract_b1_code_facts.py`
- `tools/validate_b1_code_facts.py`
- `tools/run_b1_code_fact_negative_probes.py`
- `generated/b1-typescript-rest-api/code-facts.json`
- `generated/b1-typescript-rest-api/code-facts-validation-report.json`
- `generated/b1-typescript-rest-api/p2.0-code-fact-negative-probes-report.json`
- [P2.0 B1 Code Fact Schema Static Fixture Review](../reviews/p2.0-b1-code-fact-schema-static-fixture-review.md)

Recommended next slice:

```text
P2.1 B1 Incremental Code Fact Change Probe
```

P2.1 should mutate exactly one B1 source file, compare before/after code facts, and verify expected fact changes without broad extraction, Intent mapping, UI/workbench, AI planning, or productization.

## Completed Slice: P2.1 B1 Incremental Code Fact Change Probe

Goal: prove that a one-file B1 source change creates a deterministic expected code fact and relation delta.

Produced artifacts:

- `generated/b1-typescript-rest-api/p2.1-before-code-facts.json`
- `generated/b1-typescript-rest-api/p2.1-before-source/src/service/todoService.ts`
- `generated/b1-typescript-rest-api/p2.1-after-code-facts.json`
- `docs/examples/b1-typescript-rest-api/deltas/p2.1-add-complete-todo.delta.json`
- `tools/verify_b1_incremental_change.py`
- `tools/run_b1_incremental_negative_probes.py`
- `generated/b1-typescript-rest-api/p2.1-incremental-change-report.json`
- `generated/b1-typescript-rest-api/p2.1-incremental-negative-probes-report.json`
- [P2.1 B1 Incremental Code Fact Change Review](../reviews/p2.1-b1-incremental-code-fact-change-review.md)

Recommended next slice:

```text
P2.2 B1 Code Fact Boundary Review and Phase C Entry Plan
```

P2.2 should review whether P2.0 and P2.1 are sufficient to begin Phase C Intent Mapping. It should define the first B1 mapping slice and pass/fail criteria before mapping implementation begins.

## Completed Slice: P2.2 B1 Code Fact Boundary Review and Phase C Entry Plan

Goal: review Phase B static and incremental B1 code fact evidence and decide whether Phase C can open.

Decision:

```text
open-p3.0-b1-intent-unit-mapping-schema-static-overlay-fixture
```

Produced artifacts:

- [P2.2 B1 Code Fact Boundary Phase C Entry Review](../reviews/p2.2-b1-code-fact-boundary-phase-c-entry-review.md)
- `generated/roadmap/p2.2-phase-c-entry-report.json`

Recommended next slice:

```text
P3.0 B1 Intent Unit Mapping Schema and Static Overlay Fixture
```

P3.0 may create a static B1 overlay mapping fixture and deterministic mapping verifier. It must not edit B1 source, generate AI mappings, build a broad planner, create a UI/workbench product, or broaden extraction.

## Completed Slice: P3.0 B1 Intent Unit Mapping Schema and Static Overlay Fixture

Goal: create a static B1 Intent Unit overlay and deterministic mapping verifier over B1 code facts.

Produced artifacts:

- [Intent Mapping Schema v0](../language/intent-mapping-schema-v0.md)
- `docs/examples/b1-typescript-rest-api/intentgraph.overlay.json`
- `tools/verify_b1_intent_mapping.py`
- `tools/run_b1_intent_mapping_negative_probes.py`
- `generated/b1-typescript-rest-api/p3.0-intent-mapping-report.json`
- `generated/b1-typescript-rest-api/p3.0-intent-mapping-negative-probes-report.json`
- [P3.0 B1 Intent Unit Mapping Review](../reviews/p3.0-b1-intent-unit-mapping-review.md)

Recommended next slice:

```text
P3.1 B1 Stale Intent Mapping Change Probe
```

P3.1 should prove stale mappings fail deterministically when mapped code facts change or disappear. It must not edit product behavior, generate AI mappings, start code planning, build a workbench, or broaden extraction.

## Completed Slice: P3.1 B1 Stale Intent Mapping Change Probe

Goal: prove accepted B1 mappings fail deterministically when a mapped code fact disappears from supplied facts.

Produced artifacts:

- `tools/run_b1_stale_mapping_probe.py`
- `generated/b1-typescript-rest-api/p3.1-stale-code-facts.json`
- `generated/b1-typescript-rest-api/p3.1-stale-mapping-verifier-report.json`
- `generated/b1-typescript-rest-api/p3.1-stale-mapping-probe-report.json`
- [P3.1 B1 Stale Intent Mapping Change Review](../reviews/p3.1-b1-stale-intent-mapping-change-review.md)

Recommended next slice:

```text
P3.2 B1 Ambiguous Intent Mapping Candidate Probe
```

P3.2 should model explicit ambiguity and prove ambiguous mappings remain unresolved until a later authority decision. It must not generate mappings automatically or start code planning.

## Completed Slice: P3.2 B1 Ambiguous Intent Mapping Candidate Probe

Goal: model explicit ambiguity as a visible unresolved mapping candidate.

Produced artifacts:

- [Mapping Candidate Schema v0](../language/mapping-candidate-schema-v0.md)
- `docs/examples/b1-typescript-rest-api/mapping-candidates/p3.2-ambiguous-mutate-todo.candidates.json`
- `tools/verify_b1_mapping_candidates.py`
- `tools/run_b1_mapping_candidate_negative_probes.py`
- `generated/b1-typescript-rest-api/p3.2-mapping-candidates-report.json`
- `generated/b1-typescript-rest-api/p3.2-mapping-candidate-negative-probes-report.json`
- [P3.2 B1 Ambiguous Mapping Candidate Review](../reviews/p3.2-b1-ambiguous-mapping-candidate-review.md)

Recommended next slice:

```text
P3.3 Phase C Mapping Boundary Review and Phase D Entry Plan
```

P3.3 should review P3.0 through P3.2 and decide whether Phase D change planning can open. It should not implement code planning yet.

## Completed Slice: P3.3 Phase C Mapping Boundary Review and Phase D Entry Plan

Goal: review the B1 Phase C mapping evidence and decide whether Phase D can open.

Produced artifacts:

- [P3.3 Phase C Mapping Boundary Phase D Entry Review](../reviews/p3.3-phase-c-mapping-boundary-phase-d-entry-review.md)
- `generated/roadmap/p3.3-phase-d-entry-report.json`

Decision:

```text
open-p4.0-b1-change-proposal-schema-and-non-applied-plan
```

Recommended next slice:

```text
P4.0 B1 Change Proposal Schema and Non-Applied Plan
```

P4.0 may define a proposal schema, a non-applied change proposal artifact, a proposal validator, and negative probes for unsafe proposals. It must not mutate source, apply patches, accept AI authority, resolve ambiguity automatically, build a broad planner, build UI/workbench, broaden extraction, or productize the workflow.

## Completed Slice: P4.0 B1 Change Proposal Schema and Non-Applied Plan

Goal: define and validate the first B1 proposal-only change-planning artifact.

Produced artifacts:

- [Change Proposal Schema v0](../language/change-proposal-schema-v0.md)
- `docs/examples/b1-typescript-rest-api/proposals/p4.0-complete-todo-route.proposal.json`
- `tools/validate_b1_change_proposal.py`
- `tools/run_b1_change_proposal_negative_probes.py`
- `generated/b1-typescript-rest-api/p4.0-change-proposal-validation-report.json`
- `generated/b1-typescript-rest-api/p4.0-change-proposal-negative-probes-report.json`
- [P4.0 B1 Change Proposal Non-Applied Plan Review](../reviews/p4.0-b1-change-proposal-non-applied-plan-review.md)

Recommended next slice:

```text
P4.1 Phase D Change Proposal Boundary Review and Phase E Entry Plan
```

P4.1 should review P4.0 and decide whether Phase E can open for deterministic consistency verification over proposal, source baseline, code facts, overlay mappings, tests, evidence, authority, and history. It must not apply the proposal yet.

## Completed Slice: P4.1 Phase D Change Proposal Boundary Review and Phase E Entry Plan

Goal: review B1 Phase D proposal evidence and decide whether Phase E can open.

Produced artifacts:

- [P4.1 Phase D Change Proposal Boundary Phase E Entry Review](../reviews/p4.1-phase-d-change-proposal-boundary-phase-e-entry-review.md)
- `generated/roadmap/p4.1-phase-e-entry-report.json`

Decision:

```text
open-p5.0-b1-proposal-consistency-verifier
```

Recommended next slice:

```text
P5.0 B1 Proposal Consistency Verifier
```

P5.0 may define a deterministic consistency verifier over the P4.0 proposal, B1 code facts, B1 overlay, proposal validation report, tests, evidence, authority, and non-applied claim scope. It must not mutate source, apply patches, accept the proposal, use AI judgment as verifier, build UI/workbench, or productize the workflow.

## Completed Slice: P5.0 B1 Proposal Consistency Verifier

Goal: verify consistency between the P4.0 non-applied proposal, proposal validation report, B1 code facts, and B1 overlay mappings.

Produced artifacts:

- `tools/verify_b1_proposal_consistency.py`
- `tools/run_b1_proposal_consistency_negative_probes.py`
- `generated/b1-typescript-rest-api/p5.0-proposal-consistency-report.json`
- `generated/b1-typescript-rest-api/p5.0-proposal-consistency-negative-probes-report.json`
- [P5.0 B1 Proposal Consistency Verifier Review](../reviews/p5.0-b1-proposal-consistency-verifier-review.md)

Recommended next slice:

```text
P5.1 Phase E Consistency Verifier Boundary Review and Phase F Entry Plan
```

P5.1 should review whether B1 proposal consistency reports are meaningful enough for a bounded workbench projection. It must define projection inputs, visible states, selection behavior, and screenshot validation before any UI implementation.

## Completed Slice: P5.1 Phase E Consistency Verifier Boundary Review and Phase F Entry Plan

Goal: review B1 Phase E consistency verifier evidence and decide whether Phase F can open.

Produced artifacts:

- [P5.1 Phase E Consistency Boundary Phase F Entry Review](../reviews/p5.1-phase-e-consistency-boundary-phase-f-entry-review.md)
- `generated/roadmap/p5.1-phase-f-entry-report.json`

Decision:

```text
open-p6.0-b1-workbench-projection-schema-static-html-preview
```

Recommended next slice:

```text
P6.0 B1 Workbench Projection Schema and Static HTML Preview
```

P6.0 may define a deterministic projection JSON and static HTML preview over B1 proposal, code facts, overlay, verifier, tests, evidence, authority, and history. It must not mutate source, apply or accept proposals, claim visualization verifies correctness, add external dependencies without decision, or productize the workflow.

## Completed Slice: P6.0 B1 Workbench Projection Schema and Static HTML Preview

Goal: emit a deterministic B1 workbench projection and static local HTML preview.

Produced artifacts:

- `tools/emit_b1_workbench_projection.py`
- `generated/b1-typescript-rest-api/workbench/p6.0-workbench-projection.json`
- `generated/b1-typescript-rest-api/workbench/p6.0-workbench-preview.html`
- `generated/b1-typescript-rest-api/workbench/p6.0-workbench-validation-report.json`
- [P6.0 B1 Workbench Projection Static HTML Review](../reviews/p6.0-b1-workbench-projection-static-html-review.md)

Recommended next slice:

```text
P6.1 Phase F Workbench Boundary Review and Phase G Entry Plan
```

P6.1 should review whether the B1 static preview is sufficient to plan real-project adoption. It must define adoption benchmark criteria before touching WindowsUtility or any other real project.

## Completed Slice: P6.1 Phase F Workbench Boundary Review and Phase G Entry Plan

Goal: review B1 Phase F workbench evidence and decide whether Phase G can open.

Produced artifacts:

- [P6.1 Phase F Workbench Boundary Phase G Entry Review](../reviews/p6.1-phase-f-workbench-boundary-phase-g-entry-review.md)
- `generated/roadmap/p6.1-phase-g-entry-report.json`

Decision:

```text
open-p7.0-real-project-adoption-target-benchmark-plan
```

Recommended next slice:

```text
P7.0 Real Project Adoption Target and Benchmark Plan
```

P7.0 must be plan-only. It may evaluate WindowsUtility or another target and define task class, performance benchmark, workflow benchmark, quality comparison, rollback, and stop conditions. It must not mutate a real project or run an unbounded retrofit.

## Completed Slice: P7.0 Real Project Adoption Target and Benchmark Plan

Goal: select the first real-project adoption target and define benchmark criteria.

Produced artifacts:

- [P7.0 Real Project Adoption Target Benchmark Plan Review](../reviews/p7.0-real-project-adoption-target-benchmark-plan-review.md)
- `generated/roadmap/p7.0-real-project-adoption-plan-report.json`

Decision:

```text
select-windowsutility-read-only-first
```

Recommended next slice:

```text
P7.1 WindowsUtility Read-Only Retrofit Inventory Plan and Source Snapshot
```

P7.1 must keep all artifacts inside IntentGraphDevelopment and verify WindowsUtility git status/source bytes are unchanged. It must not write to WindowsUtility unless a later approved slice explicitly authorizes target writes.

## Completed Slice: P7.1 WindowsUtility Read-Only Retrofit Inventory Plan and Source Snapshot

Goal: inventory WindowsUtility from outside the target repository and prove the target stays unchanged.

Produced artifacts:

- `tools/emit_windowsutility_readonly_inventory.py`
- `generated/windowsutility/p7.1-readonly-inventory.json`
- `generated/windowsutility/p7.1-readonly-inventory.md`
- [P7.1 WindowsUtility Read-Only Inventory Review](../reviews/p7.1-windowsutility-readonly-inventory-review.md)

Recommended next slice:

```text
P7.2 WindowsUtility Read-Only Intent Mapping Hypothesis
```

P7.2 should derive candidate Intent Units, code-surface mappings, evidence gaps, authority gaps, and ambiguity records from the read-only inventory. It must keep artifacts in IntentGraphDevelopment and must not write to WindowsUtility.

## Completed Slice: P7.2 WindowsUtility Read-Only Intent Mapping Hypothesis

Goal: derive candidate Intent Units, code-surface mappings, evidence gaps, authority gaps, and ambiguity records from the read-only inventory.

Produced artifacts:

- `tools/emit_windowsutility_mapping_hypothesis.py`
- `generated/windowsutility/p7.2-mapping-hypothesis.json`
- `generated/windowsutility/p7.2-mapping-hypothesis.md`
- [P7.2 WindowsUtility Read-Only Mapping Hypothesis Review](../reviews/p7.2-windowsutility-readonly-mapping-hypothesis-review.md)

Recommended next slice:

```text
P7.3 Real Project Adoption Boundary Review and Productization Readiness Gate
```

P7.3 should decide whether Phase H can open. Given current evidence, productization should remain blocked unless the review can justify that real-project adoption is sufficient despite read-only-only status.

## Completed Slice: P7.3 Real Project Adoption Boundary Review and Productization Readiness Gate

Goal: review Phase G real-project adoption evidence and decide whether productization can open.

Produced artifacts:

- [P7.3 Real Project Adoption Boundary Productization Readiness Review](../reviews/p7.3-real-project-adoption-boundary-productization-readiness-review.md)
- `generated/roadmap/p7.3-productization-readiness-gate-report.json`

Decision:

```text
productization-not-ready-open-readiness-gap-report-only
```

Recommended next slice:

```text
P8.0 Productization Readiness Gap Report and Stabilization Plan
```

P8.0 must be a readiness/gap artifact. It may define stabilization tasks and future acceptance criteria, but it must not package, release, integrate editors/GitHub/team workflow surfaces, mutate real-project source, apply proposals, or claim product readiness.

## Completed Slice: P8.0 Productization Readiness Gap Report and Stabilization Plan

Goal: convert the P7.3 blockers into a deterministic productization readiness checklist and stabilization plan.

Produced artifacts:

- [P8.0 Productization Readiness Gap Stabilization Review](../reviews/p8.0-productization-readiness-gap-stabilization-review.md)
- [Productization Stabilization Plan](productization-stabilization-plan.md)
- `generated/roadmap/p8.0-productization-readiness-gap-report.json`

Decision:

```text
productization-blocked-stabilization-required
```

Next safe work:

```text
P8.1 WindowsUtility Repository State Resolution Plan
P8.2 WindowsUtility Accepted Mapping Boundary Plan
```

Both are stabilization work. Neither may mutate WindowsUtility, apply proposals, package the product, or claim readiness unless the Coordinator explicitly opens that scope.

## Completed Slice: P8.1 WindowsUtility Repository State Resolution Plan

Goal: record target-state resolution options before accepted mapping or target-write work.

Produced artifacts:

- [P8.1 WindowsUtility Repository State Resolution Plan Review](../reviews/p8.1-windowsutility-repository-state-resolution-plan-review.md)
- `generated/roadmap/p8.1-windowsutility-repository-state-resolution-report.json`

Decision:

```text
target-state-unresolved-target-writes-blocked
```

Next safe work:

```text
P8.2 WindowsUtility Accepted Mapping Boundary Plan
```

P8.2 may define how hypotheses become accepted mappings, but it must not mutate WindowsUtility or treat the current unresolved repository state as accepted.

## Completed Slice: P8.2 WindowsUtility Accepted Mapping Boundary Plan

Goal: define accepted mapping requirements before accepting any WindowsUtility mapping hypothesis.

Produced artifacts:

- [P8.2 WindowsUtility Accepted Mapping Boundary Plan Review](../reviews/p8.2-windowsutility-accepted-mapping-boundary-plan-review.md)
- `generated/roadmap/p8.2-windowsutility-accepted-mapping-boundary-report.json`

Decision:

```text
accepted-mapping-not-created-boundary-defined
```

Next safe work:

```text
P8.3 WindowsUtility Accepted Mapping Candidate Selection
```

P8.3 must still remain outside WindowsUtility unless target writes are explicitly authorized. It may select one candidate and prepare a mapping artifact, but it must not apply proposals or claim productization readiness.

## Completed Slice: P8.3 WindowsUtility Accepted Mapping Candidate Selection

Goal: select one WindowsUtility mapping candidate for future accepted-mapping draft work.

Produced artifacts:

- [P8.3 WindowsUtility Accepted Mapping Candidate Selection Review](../reviews/p8.3-windowsutility-accepted-mapping-candidate-selection-review.md)
- `generated/roadmap/p8.3-windowsutility-mapping-candidate-selection-report.json`

Decision:

```text
select-shell-workspace-candidate-do-not-accept
```

Next safe work:

```text
P8.4 WindowsUtility Shell Workspace Accepted Mapping Draft
```

P8.4 may draft a mapping artifact outside WindowsUtility. It must still keep the mapping unaccepted unless target baseline, evidence, authority, and stale/missing mapping probes are complete.

## Completed Slice: P8.4 WindowsUtility Shell Workspace Accepted Mapping Draft

Goal: create a draft mapping artifact for the selected shell-workspace candidate without accepting it.

Produced artifacts:

- `generated/windowsutility/p8.4-shell-workspace-accepted-mapping-draft.json`
- [P8.4 WindowsUtility Shell Workspace Accepted Mapping Draft Review](../reviews/p8.4-windowsutility-shell-workspace-accepted-mapping-draft-review.md)
- `generated/roadmap/p8.4-shell-workspace-mapping-draft-report.json`

Decision:

```text
draft-created-mapping-not-accepted
```

Next safe work:

```text
P8.5 Shell Workspace Mapping Draft Negative Probes
```

P8.5 should prove stale digest and missing ref failures are deterministic. It must not accept the mapping or mutate WindowsUtility.

## Completed Slice: P8.5 Shell Workspace Mapping Draft Negative Probes

Goal: add repeatable positive verification and negative probes for the shell-workspace mapping draft.

Produced artifacts:

- `tools/verify_windowsutility_mapping_draft.py`
- `tools/run_windowsutility_mapping_draft_negative_probes.py`
- `generated/windowsutility/p8.5-shell-workspace-mapping-draft-verification-report.json`
- `generated/windowsutility/p8.5-shell-workspace-mapping-draft-negative-probes-report.json`
- [P8.5 Shell Workspace Mapping Draft Negative Probes Review](../reviews/p8.5-shell-workspace-mapping-draft-negative-probes-review.md)

Decision:

```text
mapping-draft-probes-pass-mapping-still-unaccepted
```

Current blocker:

```text
target baseline resolution or explicit dirty-baseline acceptance
```

Without that external decision, accepted mapping, proposal application, target writes, and productization remain blocked.

## Completed Slice: P8.6 WindowsUtility Target State Clean/Aligned Resolution

Goal: resolve the external WindowsUtility target-state blocker selected by the user.

Produced artifacts:

- [P8.6 WindowsUtility Target State Clean Aligned Review](../reviews/p8.6-windowsutility-target-state-clean-aligned-review.md)
- `generated/roadmap/p8.6-windowsutility-target-state-resolution-report.json`

Decision:

```text
target-state-clean-aligned
```

Next safe work:

```text
P8.7 Shell Workspace Mapping Acceptance Readiness Review
```

P8.7 may evaluate whether the shell-workspace draft can request user acceptance. It must not auto-accept the mapping, apply proposals, or claim productization readiness.

## Completed Slice: P8.7 Shell Workspace Mapping Acceptance Readiness Review

Goal: determine whether the shell-workspace draft can be presented for human acceptance.

Produced artifacts:

- [P8.7 Shell Workspace Mapping Acceptance Readiness Review](../reviews/p8.7-shell-workspace-mapping-acceptance-readiness-review.md)
- `generated/roadmap/p8.7-shell-workspace-mapping-acceptance-readiness-report.json`

Decision:

```text
ready-to-request-human-acceptance-mapping-not-accepted
```

Next safe work:

```text
P8.8 Shell Workspace Mapping Human Acceptance Request
```

P8.8 should create the acceptance request artifact and wait for explicit user/coordinator acceptance.

## Completed Slice: P8.8 Shell Workspace Mapping Human Acceptance Request

Goal: create an explicit human acceptance request for the shell-workspace mapping.

Produced artifacts:

- [P8.8 Shell Workspace Mapping Human Acceptance Request Review](../reviews/p8.8-shell-workspace-mapping-human-acceptance-request-review.md)
- `generated/roadmap/p8.8-shell-workspace-mapping-human-acceptance-request.json`

Decision:

```text
human-acceptance-requested-not-recorded
```

Current required decision:

```text
accept shell-workspace mapping
reject shell-workspace mapping
revise the mapping draft first
```

No accepted mapping artifact should be created before that explicit decision.
