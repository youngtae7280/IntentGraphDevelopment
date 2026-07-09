# M4 Milestone Review

Milestone: M4 - Round-Trip Verifier
Date: 2026-07-09
Reviewer: IntentGraphDevelopment Roadmap Orchestrator

Declared quality target: Level 3

## Produced Artifacts

- `docs/verifier/equality-rules.md`
- `docs/verifier/roundtrip-verifier-contract.md`
- `tools/verify_roundtrip.py`
- `generated/b0-python-cli-calculator/roundtrip-report.json`
- `docs/reviews/m4-review.md`

## Benchmarks Run

Commands run:

```powershell
python tools/verify_roundtrip.py --original docs/examples/b0-python-cli-calculator.graph.json --reconstructed generated/b0-python-cli-calculator/reconstructed.graph.json --metadata generated/b0-python-cli-calculator/calc.intentgraph.json --code-only generated/b0-python-cli-calculator/code-only-projection.json --out generated/b0-python-cli-calculator/roundtrip-report.json
python -m json.tool generated/b0-python-cli-calculator/roundtrip-report.json > $null
python -m py_compile tools/verify_roundtrip.py
```

Negative checks:

- tampered reconstructed graph content fails verification
- invalid original lifecycle status fails verification
- code-only projection is reported as lossy and is not used for exact equality
- deterministic regeneration at the declared report path produced no diffs
- temp-report generation remains semantically stable, but byte-for-byte comparison can differ because the report records input/output paths and current-run evidence resolution

Report summary:

```text
result = pass
graphEqual = true
equalityMode = GraphEqualAfterNormalization
```

## Prior-Art Comparison

M4 stayed inside the M0/M1 decisions:

- used explicit equality and normalization rules instead of claiming general bidirectional transformation semantics
- treated QVT, TGG, and eMoflon as pressure on round-trip rigor, not as systems to duplicate in Phase 0
- kept Joern, CodeQL, Graphify, SCIP, Kythe, and Glean in the code-fact lane rather than using code facts as graph authority
- kept code-only retrofit separate from metadata-backed exact equality
- treated evidence, authority, and history as source graph state to be preserved and checked, not as facts inferred from generated code

## Result

Proved for `B0-python-cli-calculator`:

```text
Retrofit(Native(G)) = G
```

under the declared M4 normalization rules:

- remove top-level lifecycle `status`
- sort nodes by `id`
- sort edges by `id`
- sort object keys during canonical JSON serialization

The verifier asserts the raw status pair before normalization:

```text
original = m1-fixture
reconstructed = m3-reconstructed
```

It also asserts that preservation metadata `graphDigest` matches the original graph and that the code-only projection declares the lossy claim.

## Round-Trip Status

Current status:

```text
Native(G) -> (C, mu, D1)      implemented in M2
Retrofit(C, mu) -> (G', D2)   implemented in M3
Verify(G, G')                 implemented in M4
```

M4 provides the first metadata-backed proof for the tiny graph. It does not claim code-only reconstruction can recover the full source graph.

## Evidence Status

Evidence nodes and their connected domain subgraph are preserved exactly under M4 canonicalization. The report includes matched evidence domain subgraph digests and matched evidence node IDs.

M5 must now move from preservation to explicit evidence semantics: observed evidence is not automatically accepted evidence.

## Authority Status

Authority nodes and their connected domain subgraph are preserved exactly under M4 canonicalization. The report includes matched authority domain subgraph digests and matched authority node IDs.

M5 must now define authority validity and acceptance rules. AI remains proposal-only.

## History Status

History nodes and their connected domain subgraph are preserved exactly under M4 canonicalization. The report includes matched history domain subgraph digests and matched history node IDs.

M5 must now define the minimal change-history model beyond graph preservation.

## Red-Team Review

The M4 critic found no P0/P1 blockers.

Issues raised:

- preservation booleans were too weak if read as proof of identity
- the verifier needed to assert and report the raw status pair

Both issues were fixed before review closure.

Saturation review corrected the determinism wording: M4 proves stable verifier semantics and declared-output byte stability, not path-independent byte identity for arbitrary temp report paths.

## Issue Review

| ID | Severity | Issue | Resolution |
|---|---|---|---|
| M4-P2-001 | P2 | Preservation reporting only showed nonzero evidence, authority, and history counts. | Resolved by adding matched domain subgraph digests and matched domain node IDs for evidence, authority, and history. |
| M4-P2-002 | P2 | Equality normalization removed `status`, but the allowed raw status pair needed to be asserted and visible. | Resolved by asserting original `m1-fixture`, reconstructed `m3-reconstructed`, and reporting both raw statuses. |

No unresolved P0/P1 issues remain. All P2 issues are resolved.

## Decision

Decision: continue

Achieved quality level: Level 3.

M4 passes its declared quality bar.

## Required Changes Before Next Milestone

M5 must:

- define observed evidence versus accepted evidence
- define minimal authority records and deterministic authority validation
- define minimal semantic change-history records
- extend verifier coverage so preservation and validity are both explicit
- keep AI output outside authority unless deterministic checks and explicit authority accept it
