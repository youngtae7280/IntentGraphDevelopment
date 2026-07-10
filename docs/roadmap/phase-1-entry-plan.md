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

## Current Slice: P1.12 Repeatable Input-Validation Overlay Contract Negative Probe Harness

Goal: harden the P1.11 invalid-integer overlay-only contract delta with repeatable negative probes.

After P1.11, CF0 can model existing invalid-integer behavior as an overlay-only input-validation contract delta. P1.12 proves the verifier rejects bad input-validation deltas for source/overlay flag errors, missing contract coverage, missing stderr/exit-code verification, missing fact mappings, and missing evidence/authority/history records.

Do not open a larger benchmark, UI, AI runtime, broader compiler slice, or broad extractor automatically.

Expected changes:

- add `tools/run_cf0_input_validation_negative_probes.py`
- emit `generated/cf0-python-cli-calculator/p1.12-input-validation-negative-probes-report.json`
- keep P1.11 positive baseline passing before negative probes
- keep P1.4, P1.7, P1.9, P1.10, and state-index regressions passing

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
- no general negative-probe framework
- no new behavior unit

## Required Output For P1.12

P1.12 should produce:

- `tools/run_cf0_input_validation_negative_probes.py`
- `generated/cf0-python-cli-calculator/p1.12-input-validation-negative-probes-report.json`
- P1.12 review notes
- updated validation rule for repeatable input-validation negative probes

## Acceptance Criteria

P1.12 passes only if:

1. The P1.11 positive baseline reruns and passes before probes.
2. Every declared negative probe fails for its intended reason.
3. The harness report records baseline scope, probe ids, expected errors, actual errors, and boundary flags.
4. P1.4, P1.7, P1.9, P1.10, P1.11, and state-index regressions still pass.
5. CF0 source bytes remain unchanged.

## Stop Conditions

Stop and report before broadening scope if:

- the P1.11 positive baseline fails.
- a required bad case passes unexpectedly.
- a required bad case fails only because of an unrelated baseline problem.
- P1.4 positive historical baseline does not pass.
- P1.7 historical refactor report stops passing.
- IntentGraph is described again as a universal source-code replacement.
- The project starts duplicating mature language workbench, code graph, or provenance systems without a build/borrow/integrate decision.

## Suggested Worker Task

Task name:

```text
P1.12 Repeatable Input-Validation Overlay Contract Negative Probe Harness
```

Worker should start from:

- `docs/examples/cf0-python-cli-calculator/source/calc.py`
- `docs/examples/cf0-python-cli-calculator/intentgraph.overlay.json`
- `tools/verify_code_first_delta.py`
- `tools/run_cf0_delta_negative_probes.py`
- `tools/emit_cf0_historical_state_index.py`
- `docs/examples/cf0-python-cli-calculator/deltas/p1.9-overlay-unsupported-operation.delta.json`
- `tools/run_cf0_overlay_contract_negative_probes.py`
- `docs/examples/cf0-python-cli-calculator/deltas/p1.11-overlay-invalid-integer.delta.json`
- `generated/cf0-python-cli-calculator/p1.7-refactor-delta-report.json`
- `generated/cf0-python-cli-calculator/cf0-historical-state-index.json`

Worker should not start the next phase or a larger benchmark until P1.12 review passes and the Coordinator explicitly authorizes the next phase.
