# Preservation Metadata Contract

Milestone: M2, revised by P1.0 for Intent Units

This contract defines the shape of `mu` for the B0 generated calculator.

In P1.0, `G` is `G_unit`: the B0 graph includes first-class Intent Units. Preservation metadata therefore includes unit-level metadata in addition to node and edge maps.

## Formal Shape

```text
mu = (nodeMap, edgeMap, unitMap, graphDigest, projectionRules, hiddenState)
```

M2 serializes `mu` as `generated/b0-python-cli-calculator/calc.intentgraph.json`.

## Required Top-Level Fields

- `metadataVersion`
- `benchmarkId`
- `graphId`
- `graphDigest`
- `compilerContract`
- `generatedAt`
- `sourceGraph`
- `generatedArtifacts`
- `nodeMap`
- `edgeMap`
- `unitMap` for GraphIR v0.2 unit graphs
- `projectionRules`
- `hiddenState`
- `diagnostics`

`generatedAt` is a deterministic label, not wall-clock time.

## Graph Digest

`graphDigest` is the SHA-256 digest of the canonical source graph JSON used by the compiler.

`sourceGraph` records both:

- `canonicalPath`: the repository fixture path for the B0 benchmark
- `inputPath`: the path passed to the compiler CLI

Canonical graph JSON rules:

- sort object keys
- use compact separators
- preserve array order from the source fixture
- encode as UTF-8

## Node Map

Each `nodeMap` entry must include:

- `graphNodeId`
- `nodeKind`
- `targetFile`
- `targetName`
- `targetKind`
- `lineStart`
- `lineEnd`
- `requiredForRoundTrip`

M2 source ranges are line-based. M3 may tighten column-level ranges if needed.

## Edge Map

Each `edgeMap` entry must include:

- `graphEdgeId`
- `edgeKind`
- `from`
- `to`
- `preservation`

`preservation` is one of:

- `source`: represented directly in generated source
- `metadata`: preserved only in metadata
- `projection`: represented by generated behavior or source structure

## Projection Rules

Projection rules must distinguish:

- `emittedToSource`
- `metadataOnly`
- `projectionOnly`
- `unclassified`
- `codeOnlyLossModel`

Evidence, authority, and semantic history are metadata-only in M2.

Intent Units and unit edges are metadata-only in P1.0.

`unclassified` must be empty for M2 review to pass.

## Hidden State

M2 includes a full source graph snapshot in `hiddenState.sourceGraphSnapshot`.

This is deliberate for the first round-trip slice: evidence, authority, history, and exact graph identity are not recoverable from generated Python alone. M3 must treat this as preservation metadata, not as code-derived reconstruction.

P1.0 still uses `hiddenState.sourceGraphSnapshot` for exact reconstruction. This is a measured weakness, not a solved problem. P1.0 adds `hiddenState.snapshotDependence` with source snapshot usage, graph counts, unit counts, and a reduction strategy.

## Unit Map

`unitMap` preserves unit-level anchors:

```json
{
  "unitId": "unit.behavior.add",
  "unitKind": "behavior",
  "status": "accepted",
  "contractDigest": "sha256:...",
  "internalNodeIds": [],
  "internalEdgeIds": [],
  "sourceMapIds": [],
  "requiresMetadata": true,
  "codeOnlyClaim": "lossy-code-only-projection"
}
```

`unitMap` does not by itself recover the full graph. It exposes the intended strategy for reducing whole-snapshot dependence in later Phase 1 work.

If later milestones remove or reduce this hidden state, they must still prove exact round-trip or explicitly narrow the thesis.

## Invalid Claims

- `calc.py` alone reconstructs the full graph.
- `nodeMap` alone reconstructs evidence, authority, and history.
- runtime success proves round-trip consistency.
- metadata without a matching `graphDigest` is safe to consume silently.
