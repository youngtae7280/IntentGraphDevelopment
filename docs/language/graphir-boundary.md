# GraphIR Boundary

GraphIR is the canonical internal representation used by future compilers, reconstructors, validators, and analysis passes. M1 defines the shape only; it does not implement those passes.

The formal model for this boundary is defined in `docs/design/intentgraph-formal-blueprint.md`.

Version: `0.1.0`

## Boundary Claim

GraphIR v0.1 is intentionally small. It must be able to describe the `B0-python-cli-calculator` benchmark and no more.

GraphIR v0.1 includes:

- graph identity
- benchmark identity
- source nodes
- typed edges
- native projection target declaration
- round-trip and projection expectations
- code-only loss model
- evidence records
- authority records
- semantic history records
- preservation metadata nodes

GraphIR v0.1 excludes:

- executable compiler behavior
- arbitrary code extraction
- editor/workbench state
- model repository storage
- policy engine syntax
- AI prompt or conversation memory

## Top-Level Shape

```json
{
  "graphirVersion": "0.1.0",
  "graphId": "ig.bench.b0.python-cli-calculator",
  "benchmarkId": "B0-python-cli-calculator",
  "title": "B0 Python CLI Calculator",
  "status": "m1-fixture",
  "nodes": [],
  "edges": [],
  "projections": {
    "native": {
      "language": "python",
      "targetFiles": [],
      "metadataFile": "calc.intentgraph.json"
    },
    "codeOnlyLossModel": []
  },
  "verificationExpectations": {
    "expectedMode": "exact-with-metadata",
    "canonicalization": "graphir-v0.1",
    "requiresMetadata": true
  }
}
```

## Node Shape

Every node has:

```json
{
  "id": "stable.node.id",
  "kind": "node.kind",
  "label": "Human readable label",
  "attributes": {}
}
```

`id` is the durable identity used by compiler metadata, reconstructor output, equality checks, evidence, authority, and history.

`kind` selects validation rules.

`attributes` is a JSON object. It may contain structured data, but M1 avoids implicit semantics that only a future compiler would know.

## M1 Node Kinds

| Kind | Purpose |
|---|---|
| `intent.requirement` | product or behavior requirement |
| `domain.concept` | domain term used by intent or code |
| `code.module` | source graph projection node for a generated module |
| `code.function` | source graph projection node for a generated function |
| `code.cli` | source graph projection node for a generated CLI command |
| `test.case` | expected test or verification case |
| `projection.target` | generated artifact target |
| `metadata.sourceMap` | preservation metadata linking graph nodes to generated source |
| `evidence.record` | evidence supporting a graph node, validation claim, or decision |
| `authority.record` | proposer/reviewer/decision record |
| `history.delta` | semantic graph change record |

## Edge Shape

Every edge has:

```json
{
  "id": "stable.edge.id",
  "kind": "edge.kind",
  "from": "source.node.id",
  "to": "target.node.id",
  "attributes": {}
}
```

Edges are directed and typed. Edge IDs are stable because the verifier may need to report relationship-level differences.

## M1 Edge Kinds

| Kind | From | To | Meaning |
|---|---|---|---|
| `decomposes_to` | `intent.requirement` | `intent.requirement` | parent intent decomposes into child intent |
| `uses_concept` | intent/code node | `domain.concept` | node uses a domain concept |
| `projects_to` | intent/domain/code node | code/projection node | source graph meaning or code projection is projected to a generated target |
| `contains` | `code.module` | code node | module contains generated code item |
| `calls` | `code.function` | `code.function` | generated function calls another generated function |
| `handled_by` | `code.cli` | `code.function` | CLI command is handled by a function |
| `tested_by` | intent/code node | `test.case` | node is covered by a test expectation |
| `evidenced_by` | any node | `evidence.record` | evidence supports the node or claim |
| `authorizes` | `authority.record` | history/projection/evidence node | authority record governs the target |
| `changes` | `history.delta` | any node | semantic delta changes the target node |
| `maps_from` | `metadata.sourceMap` | semantic graph node | metadata entry maps from an IntentGraph node, including code projection nodes |
| `maps_to` | `metadata.sourceMap` | code/projection node | metadata entry maps to generated target |

## Preservation Metadata Boundary

`metadata.sourceMap` nodes are required for full reconstruction of generated code projections.

Required attributes:

- `targetFile`
- `targetName`
- `targetKind`
- `compilerContract`
- `graphNodeIds`
- `requiredForRoundTrip`

Optional M2/M3 attributes:

- `startLine`
- `endLine`
- `startColumn`
- `endColumn`
- `contentHash`

M1 allows missing line ranges because source code has not been generated yet. M2 must decide how generated ranges are represented.

## Evidence Boundary

`evidence.record` nodes are not generic notes. They must have:

- `evidenceType`
- `status`
- `summary`
- `recordedBy`
- `observationStatus` in M5 and later
- `acceptanceStatus` in M5 and later
- `artifactRefs` in M5 and later

Evidence records become verifier-relevant in M5. Before M5, their presence and linkage are still part of the graph boundary.

Accepted evidence in M5 and later must name `acceptedByAuthority` and must be authorized by the referenced `authority.record`.

Accepted evidence must also have status compatible with its evidence type. Accepted verifier reports must be `pass`; accepted planned evidence must declare `claimScope: "plan-only"` and `runtimeProof: false`.

## Authority Boundary

`authority.record` nodes must distinguish:

- proposer
- proposer type
- required authority
- validator
- reviewer or decision authority
- decision
- decision status

AI may appear as proposer. AI must not appear as final decision authority for accepted changes.

In M5 and later, an accepted authority record must authorize at least one evidence record, history delta, or projection target with an `authorizes` edge.

Accepted authority targets are restricted to explicit authority-bearing target kinds in the B0 subset: `evidence.record`, `history.delta`, and `projection.target`.

## History Boundary

`history.delta` nodes record graph-semantic history.

Required attributes:

- `sequence`
- `changeType`
- `summary`
- `status`
- `gitCommit`

`gitCommit` may be `null` in an M1 fixture. Once implementation commits exist for generated artifacts, history records should link to real commit IDs where practical.

In M5 and later, a `null` `gitCommit` is allowed only for an in-flight current-milestone delta with `gitCommitBoundary: "pending-current-milestone"`.

Non-null `gitCommit` values must resolve to local Git commit objects where practical. Accepted history sequence values are contiguous from `1..n` in the B0 subset.

## Code-Only Loss Model

The top-level `projections.codeOnlyLossModel` declares what cannot be reconstructed from code alone.

At minimum for B0:

- product intent wording
- evidence records
- authority records
- semantic history records
- some source mapping identity

This prevents a future reconstructor from claiming full recovery from ordinary source code.
