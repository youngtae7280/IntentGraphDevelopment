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

## Current Slice: P1.8 CF0 Historical State Index and Report Boundary

Goal: add a small deterministic CF0 state index that makes historical/current report boundaries explicit.

After P1.7.R, CF0 has named P1.3 historical after-state artifacts and a repaired P1.4 harness. P1.8 records those boundaries as a generated index with state ids, transition ids, artifact paths, deterministic digests, and current/historical markers.

Do not open a larger benchmark, UI, AI runtime, broader compiler slice, or broad extractor automatically.

Expected changes:

- add a generated CF0 historical state index
- add a small emitter/validator if useful
- include P1.3 before-add-mul, P1.3 after-add-mul, and current P1.7 refactor states
- connect P1.3 and P1.7 transitions to their delta and report artifacts
- keep the repaired P1.4 historical harness and current P1.7 refactor report passing

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

## Required Output For P1.8

P1.8 should produce:

- `generated/cf0-python-cli-calculator/cf0-historical-state-index.json`
- a deterministic index emitter/validator if added
- an explicit P1.3 before-source historical copy if recovered cleanly
- P1.8 review notes
- updated validation rule for historical/current state index boundaries

## Acceptance Criteria

P1.8 passes only if:

1. The state index validates unique states/transitions and exactly one current state.
2. Every referenced artifact exists and has a deterministic `sha256:` digest.
3. P1.3 historical states do not point to mutable current source, current facts, or current overlay artifacts.
4. P1.3 after-state contains old `mul` implementation facts.
5. P1.7 current state contains `multiply` implementation facts and not old `mul` implementation facts.
6. P1.4 historical harness and P1.7 current refactor report still pass.

## Stop Conditions

Stop and report before broadening scope if:

- the index uses current P1.7 artifacts for a historical state.
- state or transition ids are ambiguous.
- referenced artifact digests cannot be computed deterministically.
- P1.4 positive historical baseline does not pass.
- P1.7 current refactor report stops passing.
- IntentGraph is described again as a universal source-code replacement.
- The project starts duplicating mature language workbench, code graph, or provenance systems without a build/borrow/integrate decision.

## Suggested Worker Task

Task name:

```text
P1.8 CF0 Historical State Index and Report Boundary
```

Worker should start from:

- `docs/examples/cf0-python-cli-calculator/source/calc.py`
- `docs/examples/cf0-python-cli-calculator/intentgraph.overlay.json`
- `tools/verify_code_first_delta.py`
- `tools/run_cf0_delta_negative_probes.py`
- `generated/cf0-python-cli-calculator/p1.3-after-code-facts.json`
- `generated/cf0-python-cli-calculator/p1.3-after-overlay.json`
- `generated/cf0-python-cli-calculator/p1.3-after-source/calc.py`
- `generated/cf0-python-cli-calculator/p1.7-refactor-delta-report.json`

Worker should not start the next phase or a larger benchmark until P1.8 review passes and the Coordinator explicitly authorizes the next phase.
