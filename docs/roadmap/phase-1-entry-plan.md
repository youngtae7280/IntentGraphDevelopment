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

## Current Slice: P1.4 Repeatable Code-First Delta Negative Probe Harness

Goal: turn the P1.3.R temporary negative probes into a committed deterministic harness so future changes cannot weaken the CF0 code-first delta verifier silently.

P1.4 must start from the committed good CF0 delta inputs, create mutated copies in isolation, run the delta verifier, and pass only when every negative probe fails with the expected error.

Do not open a larger benchmark, UI, AI runtime, broader compiler slice, or broad extractor automatically.

Expected changes:

- add a small negative-probe harness such as `tools/run_cf0_delta_negative_probes.py`
- emit `generated/cf0-python-cli-calculator/p1.4-negative-probes-report.json`
- cover wrong before source digest, wrong before overlay digest/count, missing added fact, missing evidence/authority/history ids, source-text equality, and hidden snapshot claims
- keep the P1.3 positive delta report passing

Non-goals:

- no larger benchmark yet
- no broad language workbench
- no interactive IDE
- no arbitrary code extractor
- no Graphify/CodeQL/Joern replacement
- no claim that source code alone recovers full intent, evidence, authority, or history
- no automatic AI authority

## Required Output For P1.4

P1.4 should produce:

- committed negative-probe harness script
- deterministic negative-probes JSON report
- updated validation rules and review notes

## Acceptance Criteria

P1.4 passes only if:

1. The P1.3 positive delta verification still passes.
2. Every defined negative probe returns verifier failure.
3. The harness exits zero only when all probes fail with expected errors.
4. The harness report is deterministic and inspectable.
5. The report does not imply source text equality, hidden generated-code snapshot use, AI authority, broad extraction, or a general planner.

## Stop Conditions

Stop and report before broadening scope if:

- The harness passes when a negative probe unexpectedly succeeds.
- Negative probe failures are not tied to expected error messages.
- The harness requires committed bad fixtures without a clear reason.
- IntentGraph is described again as a universal source-code replacement.
- The project starts duplicating mature language workbench, code graph, or provenance systems without a build/borrow/integrate decision.

## Suggested Worker Task

Task name:

```text
P1.4 Repeatable Code-First Delta Negative Probe Harness
```

Worker should start from:

- `docs/design/intent-unit-model.md`
- `docs/design/intentgraph-formal-blueprint.md`
- `docs/language/graphir-boundary.md`
- `docs/examples/cf0-python-cli-calculator/deltas/p1.3-add-mul.delta.json`
- `generated/cf0-python-cli-calculator/p1.3-before-code-facts.json`
- `generated/cf0-python-cli-calculator/p1.3-before-overlay.json`
- `tools/verify_code_first_delta.py`

Worker should not start the next phase or a larger benchmark until P1.4 review passes and the Coordinator explicitly authorizes the next phase.
