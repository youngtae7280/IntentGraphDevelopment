# GraphIR Validation Rules

M1 defined validation rules but did not implement them. P1.R reframes them around semantic overlay state: code nodes are references/facts, not code text, and generated-code rules apply only when a generated-code mode is declared.

## Rule Severity

| Severity | Meaning |
|---|---|
| P0 | invalid graph; cannot be mapped, verified, generated, reconstructed, or reviewed |
| P1 | major correctness gap; milestone cannot pass until fixed |
| P2 | meaningful quality issue; fix or write a defer decision |
| P3 | optional polish |

## Required M1 Rules

### V001 - Required Top-Level Fields

Severity: P0

GraphIR documents must include `graphirVersion`, `graphId`, `benchmarkId`, `title`, `status`, `nodes`, `edges`, and `projections`.

GraphIR v0.2 documents must also include `intentUnits` and `unitEdges`.

### V002 - Supported Version

Severity: P0

M1 supports `graphirVersion: "0.1.0"`.

P1.1 supports `graphirVersion: "0.2.0"` for the overlay-mapped B0 fixture.

### V010 - Unique IDs

Severity: P0

All node IDs must be unique. All edge IDs must be unique. A node and edge may not share an ID.

### V011 - Stable ID Format

Severity: P1

IDs should use lowercase dot-separated names with hyphens only inside a segment when needed. IDs must not depend on array position or generated timestamps.

### V020 - Known Node Kinds

Severity: P0

Every node kind must be one of the M1 node kinds declared in `docs/language/graphir-boundary.md`.

### V021 - Known Edge Kinds

Severity: P0

Every edge kind must be one of the M1 edge kinds declared in `docs/language/graphir-boundary.md`.

### V030 - Edge Endpoint Integrity

Severity: P0

Every edge `from` and `to` value must reference an existing node ID.

### V031 - Edge Domain Rules

Severity: P1

Edges must respect the from/to node kind rules declared in `docs/language/graphir-boundary.md`.

### V040 - Required Projection Target For Generated-Code Mode

Severity: P0

The Phase 0 generated-code benchmark graph must declare exactly one Python native projection target for generated source. Code-first maintenance fixtures should instead declare extraction and mapping expectations.

### V041 - Source Map Coverage For Generated-Code Mode

Severity: P0 for M2 and later, P1 in M1

Every generated-code projection node that is expected to round-trip must be covered by at least one `metadata.sourceMap` node.

### V042 - Relative Generated Paths

Severity: P1

Generated target paths and metadata paths must be relative paths. Absolute local paths must not appear in GraphIR.

### V043 - Source Map Required Attributes

Severity: P0

Every `metadata.sourceMap` node must include `targetFile`, `targetName`, `targetKind`, `compilerContract`, `graphNodeIds`, and `requiredForRoundTrip`.

### V044 - Source Map Graph Node Integrity

Severity: P0

Every ID in `metadata.sourceMap.attributes.graphNodeIds` must reference an existing graph node.

### V045 - Compiler Contract Is Not Implementation Claim

Severity: P1

M1 source maps must name a future generated-code contract, not claim that generated code or an implementation already exists.

### V050 - Evidence Linkage

Severity: P1

Every `evidence.record` must be linked from at least one graph node by an `evidenced_by` edge, or must be explicitly marked as milestone-level evidence.

### V051 - Evidence Status

Severity: P1

Evidence status must be one of `planned`, `pass`, `fail`, `blocked`, or `superseded`.

### V052 - Evidence Required Attributes

Severity: P0

Every `evidence.record` must include `evidenceType`, `status`, `summary`, and `recordedBy`.

### V053 - Evidence Observation And Acceptance

Severity: P0 in M5 and later

Every `evidence.record` must include `observationStatus`, `acceptanceStatus`, and `artifactRefs`. Accepted evidence must include `acceptedByAuthority`.

Observation does not imply acceptance.

Accepted evidence must not have `status: "fail"`, `status: "blocked"`, or `status: "superseded"`. Accepted verifier-report evidence must have `status: "pass"`. Accepted planned evidence must declare `claimScope: "plan-only"` and `runtimeProof: false`.

### V054 - Accepted Evidence Authority

Severity: P0 in M5 and later

Every accepted evidence record must reference an accepted `authority.record`, and that authority record must authorize the evidence record with an `authorizes` edge.

### V060 - Authority Linkage

Severity: P1

Every `authority.record` must authorize at least one history delta, projection target, or evidence record.

### V061 - AI Is Not Final Authority

Severity: P0

If an accepted authority decision has `proposerType: "ai"`, then `decidedByType` must not be `ai`.

### V062 - Authority Required Attributes

Severity: P0

Every `authority.record` must include `proposer`, `proposerType`, `requiredAuthority`, `validator`, `decidedBy`, `decidedByType`, `decision`, and `decisionStatus`.

### V063 - Accepted Authority Scope

Severity: P0 in M5 and later

Every accepted `authority.record` must authorize at least one evidence record, history delta, or projection target. An accepted authority record must not have `decidedByType: "ai"` under case-normalized actor type comparison. Unknown actor types are invalid.

### V070 - History Linkage

Severity: P1

Every `history.delta` must link to at least one changed node through a `changes` edge.

### V071 - Git Link Boundary

Severity: P2 in M1, P1 after generated artifacts exist

`history.delta.attributes.gitCommit` may be `null` only before implementation commits exist for generated artifacts.

### V072 - History Required Attributes

Severity: P0

Every `history.delta` must include `sequence`, `changeType`, `summary`, `status`, and `gitCommit`.

### V073 - Accepted History Authority And Git Boundary

Severity: P0 in M5 and later

Every accepted `history.delta` must be authorized by an accepted `authority.record` and must link to at least one changed node. Accepted history sequences must be contiguous from `1..n` in the B0 subset. Non-null `gitCommit` values must resolve to local commit objects. If `gitCommit` is `null`, the delta must include `gitCommitBoundary: "pending-current-milestone"` and a reason.

### V080 - Declared Code-Only Loss

Severity: P0

The document must declare a code-only loss model. It must include evidence, authority, and history as non-recoverable from ordinary source code alone.

### V081 - Verification Expectations

Severity: P1

The document must declare `verificationExpectations` with `expectedMode`, `canonicalization`, and `requiresMetadata`.

### V090 - No Hidden Tool Defaults

Severity: P1

The graph must include enough explicit intent, code reference, code fact, mapping, and generated-code projection information for a future tool contract to be written without relying on unstated behavior.

For `B0-python-cli-calculator`, this includes operation semantics, argument parsing, output formatting, success exit code, and invalid input behavior.

### V100 - No Implementation Claims

Severity: P0 in M1

M1 artifacts must not claim generated code, reconstruction, verifier output, or test execution exists.

## P1.1 Intent Unit Overlay Mapping Rules

### V200 - Intent Units Required

Severity: P0 in P1.1

GraphIR v0.2 documents must include a non-empty `intentUnits` array and a `unitEdges` array.

### V201 - B0 Required Units

Severity: P0 in P1.1

The B0 unit-structured fixture must include:

- `unit.product.calculator`
- `unit.behavior.add`
- `unit.behavior.sub`

### V202 - Unit Admission Fields

Severity: P0 in P1.1

Every accepted Intent Unit must include:

- stable ID
- kind
- accepted status
- contract
- internal graph membership
- code references, code fact references, or explicit non-realized status
- mapping obligations
- projection and reconstruction expectations when generated-code mode is declared
- verification expectations
- evidence references
- authority references
- history references
- admission fields

Admission fields must distinguish accepted Intent Units from raw utterances, notes, hypotheses, imported facts, and AI proposals.

### V203 - Unit Internal Graph Integrity

Severity: P0 in P1.1

Every `internalGraph.nodeIds` entry must reference an existing graph node. Every `internalGraph.edgeIds` entry must reference an existing graph edge.

### V204 - Unit Evidence Authority History Integrity

Severity: P0 in P1.1

Every unit evidence reference must target an `evidence.record`. Every authority reference must target an `authority.record`. Every history reference must target a `history.delta`.

### V205 - Unit Refinement Backbone

Severity: P0 in P1.1

B0 must include refinement unit edges:

```text
unit.product.calculator -> unit.behavior.add
unit.product.calculator -> unit.behavior.sub
```

### V206 - Unit Edge Class Separation

Severity: P1 in P1.1

Unit refinement relations must use `unitEdges.kind = "refines"`. Cross-unit relations must use a distinct kind such as `shares_concept` or `projects_with`.

### V207 - No Unit God Object

Severity: P1 in P1.1

Behavior units must remain focused on their behavior contract. Shared product, evidence, authority, and history records may be referenced, but a behavior unit must not own unrelated behavior internals.

### V208 - Unit Mapping And Generated-Code Expectation

Severity: P0 in P1.1

The graph must declare that code-only reconstruction remains lossy for Intent Unit contracts, refinement structure, admission state, evidence, authority, and history. If generated-code mode is declared, exact unit round-trip requires preservation metadata.

### V209 - Proposal Non-Authority For Unit Membership

Severity: P0 in P1.1

AI proposals may describe unit effects or propose new internal graph facts, but they must not silently mutate accepted unit membership. Unit membership changes require deterministic validation and accepted authority.

### V210 - Unit Code References Are Not Code Text

Severity: P0 in P1.1

Every accepted Intent Unit must declare non-empty `codeRefs`. Each `codeRef` must identify a graph node, reference kind, mode, and `ownership: "reference-only"`. A `codeRef` must not contain source code text.

### V211 - Unit Code Fact References Are Declared Facts

Severity: P0 in P1.1

Every accepted Intent Unit must declare non-empty `codeFactRefs`. Because P1.1 has no external extractor, each fact must be explicitly marked as `graph-fixture`, `generated-code-mode`, or `static-declared`.

### V212 - Mapping Obligations Are Explicit

Severity: P0 in P1.1

Every accepted Intent Unit must declare non-empty `mappingObligations`. Each obligation must link intent nodes, code refs, code fact refs, verification IDs, evidence IDs, and authority IDs. `sourceTextEqualityRequired` must be `false`.

## P1.2 Code-First Overlay Rules

### V300 - Hand-Written Source

Severity: P0 in P1.2

CF0 source artifacts must be marked as hand-written. The code-first verifier must not invoke graph-to-code generation.

### V301 - Extracted Code Facts

Severity: P0 in P1.2

Extractor output must include stable fact IDs, source artifact path, source digest, source mode, confidence, and source location where applicable.

### V302 - Code Fact Resolution

Severity: P0 in P1.2

Every CF0 `codeFactRef.factId` must resolve to an extracted code fact in `X`.

### V303 - No Source Text Equality Requirement

Severity: P0 in P1.2

CF0 verification must report behavior and mapping preservation. It must not require `C' == C` or source text equality.

### V304 - No Hidden Generated-Code Snapshot

Severity: P0 in P1.2

CF0 verification must not depend on `hiddenState.sourceGraphSnapshot` or generated-code preservation metadata.

## P1.3 Code-First Maintenance Delta Rules

### V400 - Before-State Captured

Severity: P0 in P1.3

Before-state source digest, code facts digest/count, overlay digest, and mapping obligation count must be captured before the source and overlay mutation.

### V401 - Delta Report Is Code-First

Severity: P0 in P1.3

The delta report must declare `mode: "code-first-maintenance-delta"`, `sourceTextEqualityRequired: false`, and `hiddenGeneratedCodeSnapshotUsed: false`.

### V402 - Existing Mappings Preserved

Severity: P0 in P1.3

Existing add/sub behavior mappings must remain resolved after the delta.

### V403 - New Behavior Mapped

Severity: P0 in P1.3

The new behavior unit must include code refs, code fact refs, and mapping obligations that resolve to after-state extracted facts.

### V404 - Before Overlay Verified Against Artifact

Severity: P0 in P1.3.R

A maintenance delta report that cites before overlay digest or mapping obligation count must verify those values against a preserved or reproducibly recovered before-overlay artifact.

### V405 - Delta Records Resolve

Severity: P0 in P1.3.R

Every evidence, authority, and history id declared by a maintenance delta must resolve to a record in the accepted after overlay.

## M1 Fixture Review Checklist

For `docs/examples/b0-python-cli-calculator.graph.json`, a reviewer should check:

- JSON parses successfully
- IDs are stable and unique
- node and edge kinds are known
- all edge endpoints exist
- product intent is represented
- add and subtract behavior are represented
- Python module/function/CLI projections are represented
- source map metadata nodes exist for generated-code projections
- code nodes are references/facts rather than code text copies
- tests are represented as expectations, not executed results
- evidence and authority are present and linked
- history delta is present and linked
- code-only loss model is explicit
