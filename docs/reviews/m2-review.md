# M2 Milestone Review

Milestone: M2 - Native Compiler Boundary
Date: 2026-07-09
Reviewer: IntentGraphDevelopment Roadmap Orchestrator

Declared quality target: Level 3, Round-Trip Slice after M3

## Produced Artifacts

- `docs/compiler/native-compiler-contract.md`
- `docs/compiler/preservation-metadata-contract.md`
- `tools/native_compile.py`
- `generated/b0-python-cli-calculator/calc.py`
- `generated/b0-python-cli-calculator/calc.intentgraph.json`
- `generated/b0-python-cli-calculator/native-diagnostics.json`
- `docs/reviews/m2-review.md`

## Benchmarks Run

Commands run:

```powershell
python tools/native_compile.py --graph docs/examples/b0-python-cli-calculator.graph.json --out generated/b0-python-cli-calculator
python -m py_compile tools/native_compile.py generated/b0-python-cli-calculator/calc.py
python generated/b0-python-cli-calculator/calc.py add 2 3
python generated/b0-python-cli-calculator/calc.py sub 5 2
python generated/b0-python-cli-calculator/calc.py mul 2 3
python generated/b0-python-cli-calculator/calc.py add x 3
```

Observed:

- `add 2 3` printed `5` and exited `0`
- `sub 5 2` printed `3` and exited `0`
- invalid operation exited `2`
- invalid integer exited `2`
- deterministic regeneration to a temp directory produced no diffs for source, metadata, or diagnostics

## Prior-Art Comparison

M2 stayed inside the M0/M1 build/borrow decisions:

- did not build a broad language workbench
- did not build a broad code extractor
- did not claim model-to-code generation as novel
- emitted preservation metadata inspired by generated-code mapping prior art, while keeping the B0 contract intentionally tiny
- kept evidence, authority, and semantic history as metadata-bearing graph state rather than source-code facts

## Result

Proved:

- The B0 source graph can deterministically generate a Python CLI calculator.
- Generated code is digest-tied to the canonical source graph.
- Preservation metadata includes node maps, edge maps, graph digest, projection rules, hidden state, generated artifact hashes, and diagnostics.
- The generated project is small enough for M3 to consume.

Weakened:

- Exact future round-trip currently depends on `hiddenState.sourceGraphSnapshot`.
- This is acceptable for the first slice but must be treated honestly in M3 as preservation metadata, not code-derived reconstruction.

Changed:

- Compiler validation now checks B0 test commands/stdout/exit codes and CLI exit-code consistency.
- Projection rules are exhaustive: `emittedToSource`, `metadataOnly`, `projectionOnly`, and empty `unclassified`.
- Metadata records both canonical fixture path and actual compiler input path.

## Round-Trip Status

Not implemented in M2.

M2 produced the `Native(G) -> (C, mu, D)` side of the loop. M3 must implement:

```text
Retrofit(C, mu, config) -> (G', D)
```

using `generated/b0-python-cli-calculator/calc.py` and `generated/b0-python-cli-calculator/calc.intentgraph.json`.

## Evidence Status

Evidence nodes are preserved in metadata through the hidden source graph snapshot and metadata-only projection classification. M5 must later verify evidence preservation explicitly.

## Authority Status

Authority nodes are preserved in metadata through the hidden source graph snapshot and metadata-only projection classification. AI remains proposal-only.

## Unexpected Discoveries

- Metadata projection classification needed to be exhaustive for M3 to avoid hidden assumptions.
- B0 compiler validation needed to enforce the test semantics it generates against.
- The first exact round-trip will rely on preservation metadata carrying graph state; code-only reconstruction remains intentionally lossy.

## Issue Review

| ID | Severity | Issue | Resolution |
|---|---|---|---|
| M2-P2-001 | P2 | `projectionRules` did not classify every graph node. | Resolved by adding `projectionOnly` and `unclassified`; `unclassified` is empty. |
| M2-P2-002 | P2 | Compiler validation was narrower than the contract. | Resolved by validating test case commands/stdout/exit codes and exit-code consistency. |
| M2-P3-001 | P3 | Source graph path was hard-coded. | Resolved by recording both `canonicalPath` and `inputPath`. |
| M2-P3-002 | P3 | Python cache files appeared after `py_compile`. | Resolved by adding Python cache patterns to `.gitignore` and removing caches. |

No unresolved P0/P1 issues remain. All P2 issues are resolved.

## Decision

Decision: continue

Achieved quality level: Level 2 now; Level 3 is pending M3/M4 round-trip completion as declared by the roadmap.

M2 passes its milestone boundary and may proceed to M3.

## Required Changes Before Next Milestone

M3 must:

- consume `calc.py` and `calc.intentgraph.json`
- reconstruct a graph without using hidden process memory
- fail loudly when metadata is missing or digest-incompatible
- document the code-only loss model separately
- avoid claiming round-trip equality until M4 verifier exists
