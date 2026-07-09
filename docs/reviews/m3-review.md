# M3 Milestone Review

Milestone: M3 - Retrofit Reconstructor Boundary
Date: 2026-07-09
Reviewer: IntentGraphDevelopment Roadmap Orchestrator

Declared quality target: Level 3

## Produced Artifacts

- `docs/reconstructor/retrofit-reconstructor-contract.md`
- `docs/reconstructor/code-only-loss-model.md`
- `tools/retrofit_reconstruct.py`
- `generated/b0-python-cli-calculator/reconstructed.graph.json`
- `generated/b0-python-cli-calculator/retrofit-diagnostics.json`
- `generated/b0-python-cli-calculator/code-only-projection.json`
- `docs/reviews/m3-review.md`

## Benchmarks Run

Commands run:

```powershell
python tools/retrofit_reconstruct.py --source generated/b0-python-cli-calculator/calc.py --metadata generated/b0-python-cli-calculator/calc.intentgraph.json --out generated/b0-python-cli-calculator
python -m json.tool generated/b0-python-cli-calculator/reconstructed.graph.json
python -m json.tool generated/b0-python-cli-calculator/retrofit-diagnostics.json
python -m json.tool generated/b0-python-cli-calculator/code-only-projection.json
python -m py_compile tools/retrofit_reconstruct.py
```

Negative checks:

- tampered generated source fails
- missing metadata fails
- invalid metadata JSON fails through a controlled error path
- empty `nodeMap` fails
- empty `edgeMap` fails
- deterministic regeneration at the declared output path produced no diffs
- temp-directory regeneration remains semantically stable, but byte-for-byte comparison can differ in declared path-bearing report fields

## Prior-Art Comparison

M3 stayed inside the M0/M1 decisions:

- did not build a broad source-code extractor
- used Python AST only for the intentionally lossy code-only projection
- reconstructed the full graph from explicit preservation metadata, not AI or hidden process memory
- kept evidence, authority, and history as metadata-preserved graph state rather than code-derived facts

## Result

Proved:

- `Retrofit(C, mu, config) -> (G', D)` works for the B0 generated calculator.
- The reconstructor fails loudly when generated source and metadata are incompatible.
- The reconstructor validates substantive `nodeMap` and `edgeMap` coverage before accepting metadata-backed reconstruction.
- `RetrofitCodeOnly(C, config)` is documented and emitted as a lossy projection, not a full graph.

Weakened:

- Exact reconstruction depends on `hiddenState.sourceGraphSnapshot`.
- That remains acceptable for the first metadata-backed round-trip slice, but it is a design pressure point for future milestones.

Changed:

- Red-team feedback strengthened metadata validation for `nodeMap` and `edgeMap`.
- Invalid metadata JSON is handled as a controlled reconstructor failure.
- `reconstructed.graph.json` carries graph state only; reconstruction status stays in diagnostics so M4 can define equality rules cleanly.

## Round-Trip Status

M3 reconstructs `G'` but does not perform the M4 equality verdict.

Current status:

```text
Native(G) -> (C, mu, D1)      implemented in M2
Retrofit(C, mu) -> (G', D2)   implemented in M3
Verify(G, G')                 not yet implemented
```

## Evidence Status

Evidence records are present in the reconstructed graph through preservation metadata. M5 must later verify evidence semantics explicitly.

## Authority Status

Authority records are present in the reconstructed graph through preservation metadata. AI remains proposal-only.

## Unexpected Discoveries

- `nodeMap` and `edgeMap` validation must be substantive even when a full hidden graph snapshot exists.
- Keeping reconstruction diagnostics outside `G'` simplifies M4 equality design.
- Code-only projection can recover useful code facts, but not accepted authority, evidence, or history.
- Saturation review corrected the determinism claim: M3 output is byte-stable at the declared output path, while temp-output reports can intentionally record different paths.

## Issue Review

| ID | Severity | Issue | Resolution |
|---|---|---|---|
| M3-P2-001 | P2 | Metadata validation was too shallow; empty `nodeMap`/`edgeMap` could pass. | Resolved by validating non-empty maps, required fields, graph references, line ranges, source-map coverage, and complete edge coverage. |
| M3-P3-001 | P3 | Invalid metadata JSON could escape the controlled failure path. | Resolved by wrapping JSON decode errors as reconstructor failures. |
| M3-P3-002 | P3 | Adding reconstruction metadata inside `G'` would complicate M4 equality. | Resolved by keeping reconstruction status in diagnostics only. |

No unresolved P0/P1 issues remain. All P2 issues are resolved.

## Decision

Decision: continue

Achieved quality level: Level 3 for the reconstructed side of the round-trip slice. M4 must now provide the actual verifier proof.

M3 passes its declared quality bar.

## Required Changes Before Next Milestone

M4 must:

- define canonical equality rules
- compare original `G` and reconstructed `G'`
- treat `status` differences as a declared projection or normalization rule
- prove or reject `Retrofit(Native(G)) = G` for B0
- keep code-only projection separate from exact metadata-backed equality
