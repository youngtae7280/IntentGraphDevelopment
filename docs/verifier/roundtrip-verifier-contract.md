# Round-Trip Verifier Contract

Milestone: M4, revised by P1.5 for typed preservation reporting

This contract defines the smallest verifier for the B0 round-trip slice.

## Scope

Inputs:

```text
docs/examples/b0-python-cli-calculator.graph.json
generated/b0-python-cli-calculator/reconstructed.graph.json
generated/b0-python-cli-calculator/calc.intentgraph.json
generated/b0-python-cli-calculator/code-only-projection.json
```

Output:

```text
generated/b0-python-cli-calculator/roundtrip-report.json
```

Verifier command:

```powershell
python tools/verify_roundtrip.py --original docs/examples/b0-python-cli-calculator.graph.json --reconstructed generated/b0-python-cli-calculator/reconstructed.graph.json --metadata generated/b0-python-cli-calculator/calc.intentgraph.json --code-only generated/b0-python-cli-calculator/code-only-projection.json --out generated/b0-python-cli-calculator/roundtrip-report.json
```

## Contract

```text
Verify(G, G', mu, config) -> Report
```

For M4:

- `G` is the original B0 GraphIR fixture. In P1.1 this is `G_unit` with overlay mapping fields.
- `G'` is the M3 reconstructed graph. In P1.1 this is `G_unit'`.
- `mu` is the M2 preservation metadata.
- `config` is the equality rule set in `docs/verifier/equality-rules.md`.

## Preconditions

- original graph JSON parses
- reconstructed graph JSON parses
- preservation metadata JSON parses
- code-only projection JSON parses
- metadata graph digest matches the original graph digest
- P1.5 metadata includes typed preservation domains for intent units, unit edges, evidence, authority, and history
- original graph status is `m1-fixture` for Phase 0, `p1-unit-fixture` for historical P1.0, or `p1-overlay-fixture` for P1.1
- reconstructed graph status is `m3-reconstructed`
- code-only projection claim is `lossy-code-only-projection`

## Postconditions

- report states `result: "pass"` only if normalized original and reconstructed graph digests match
- report lists normalization rules applied
- report lists node and edge counts by kind
- report confirms evidence, authority, and history preservation with domain subgraph digests and matched node IDs
- report confirms Intent Unit preservation with unit projection digests, unit counts, unit edge counts, unit admission validation, and mapping obligation preservation
- report exposes typed preservation status, domain counts, domain digests, and `snapshotStillPresent`
- report does not treat code-only projection as exact reconstruction
- report does not claim the full snapshot has been removed in P1.5
- diagnostics include any equality mismatches

## Exact Validation Commands

```powershell
python tools/verify_roundtrip.py --original docs/examples/b0-python-cli-calculator.graph.json --reconstructed generated/b0-python-cli-calculator/reconstructed.graph.json --metadata generated/b0-python-cli-calculator/calc.intentgraph.json --code-only generated/b0-python-cli-calculator/code-only-projection.json --out generated/b0-python-cli-calculator/roundtrip-report.json
python -m json.tool generated/b0-python-cli-calculator/roundtrip-report.json > $null
```

The report should state:

```text
result = pass
graphEqual = true
```

## Non-Goals

M4 does not implement:

- new compiler behavior
- new reconstructor behavior
- evidence acceptance policy
- authority policy engine
- AI proposal workflow
- visualization/workbench UI

P1.1 does not claim that code-only reconstruction can recover Intent Units or their overlay mappings.
