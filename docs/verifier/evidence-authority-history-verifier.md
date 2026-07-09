# Evidence, Authority, And History Verifier

Milestone: M5

This document extends the M4 round-trip verifier with semantic checks for evidence, authority, and change history.

It does not add a policy engine, provenance database, supply-chain attestation engine, or Git replacement.

## Inputs

```text
docs/examples/b0-python-cli-calculator.graph.json
generated/b0-python-cli-calculator/reconstructed.graph.json
generated/b0-python-cli-calculator/calc.intentgraph.json
generated/b0-python-cli-calculator/code-only-projection.json
```

## Output

```text
generated/b0-python-cli-calculator/roundtrip-report.json
```

## Contract

```text
VerifyM5(G, G', mu, config) -> Report
```

The M5 report uses verifier contract `roundtrip-b0-m5-eah-v0`.

M5 keeps the M4 equality requirement and adds:

```text
EvidenceSemantics(G) = pass
AuthoritySemantics(G) = pass
HistorySemantics(G) = pass
EvidenceSemantics(G') = pass
AuthoritySemantics(G') = pass
HistorySemantics(G') = pass
```

Because M4 exact normalized equality must also pass, the semantic checks are expected to match between `G` and `G'`.

## Required Report Fields

The report must include:

- M4 equality verdict
- evidence domain subgraph preservation verdict
- authority domain subgraph preservation verdict
- history domain subgraph preservation verdict
- evidence semantic validation
- authority semantic validation
- history semantic validation
- artifact reference checks for evidence records
- authority target-kind checks
- local Git commit existence checks
- accepted history sequence contiguity checks
- explicit statement that code-only projection is not used as evidence, authority, or history source

## Failure Conditions

The verifier must fail if:

- exact normalized graph equality fails
- evidence, authority, or history domain subgraph digests differ
- observed evidence is treated as accepted without authority
- accepted evidence lacks accepted authorizing authority
- observed evidence references a missing local artifact
- accepted evidence has `fail`, `blocked`, or `superseded` status
- accepted verifier-report evidence is not tied to a passing report
- accepted authority has AI as final decision authority
- accepted authority authorizes unsupported target kinds
- accepted history delta lacks changes or accepted authority
- accepted history sequences are not contiguous from `1..n`
- non-null Git commit linkage does not resolve locally
- missing Git linkage lacks an explicit current-milestone boundary
