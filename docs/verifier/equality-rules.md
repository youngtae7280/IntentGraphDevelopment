# Round-Trip Equality Rules

Milestone: M4

This document defines the B0 equality and projection rules for the first verifier proof.

## Equality Claim

M4 verifies:

```text
Retrofit(Native(G)) = G
```

for `B0-python-cli-calculator` under declared normalization rules.

## Canonicalization

```text
Canon(G) = stable serialization of Normalize(G)
```

Normalization for B0:

- remove top-level lifecycle field `status`
- sort top-level `nodes` by `id`
- sort top-level `edges` by `id`
- sort object keys during JSON serialization
- use compact JSON separators
- preserve all node attributes, edge attributes, evidence, authority, history, projections, and verification expectations

The only allowed difference between the original M1 graph and the M3 reconstructed graph is top-level lifecycle `status`:

- original status: `m1-fixture`
- reconstructed status: `m3-reconstructed`

The verifier must assert this exact raw status pair before applying status normalization.

If any node, edge, attribute, evidence record, authority record, history record, projection, or verification expectation differs after normalization, exact equality fails.

## Exact Equality

```text
GraphEqual(G, G') <=> Canon(G) == Canon(G')
```

M4 uses `GraphEqual` for metadata-backed reconstruction.

## Projection Equality

```text
ProjectionEqual(G, G', P) <=> Canon(Project(G, P)) == Canon(Project(G', P))
```

M4 does not need projection equality for the B0 metadata-backed proof because exact normalized graph equality is expected to pass.

Projection equality remains reserved for future partial/lossy comparisons.

## Code-Only Boundary

`code-only-projection.json` is not an exact graph reconstruction input for M4.

It may be reported as supporting evidence for the loss model, but it must not be used to claim:

```text
RetrofitCodeOnly(C) = G
```

The verifier must keep these claims separate:

- metadata-backed graph equality
- code-only lossy projection facts

## Required Report Fields

The M4 verifier report must include:

- original graph path and digest
- reconstructed graph path and digest
- normalized original digest
- normalized reconstructed digest
- equality result
- normalization rules applied
- preserved node counts by kind
- preserved edge counts by kind
- evidence/authority/history preservation status
- evidence/authority/history domain subgraph digests and matched node IDs
- code-only projection claim
- diagnostics
