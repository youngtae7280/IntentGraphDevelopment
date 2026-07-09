# GraphIR Validation Rules

M1 defines validation rules but does not implement them. M2 and later milestones must turn the relevant rules into executable checks before making implementation claims.

## Rule Severity

| Severity | Meaning |
|---|---|
| P0 | invalid graph; cannot be compiled, reconstructed, or reviewed |
| P1 | major correctness gap; milestone cannot pass until fixed |
| P2 | meaningful quality issue; fix or write a defer decision |
| P3 | optional polish |

## Required M1 Rules

### V001 - Required Top-Level Fields

Severity: P0

GraphIR documents must include `graphirVersion`, `graphId`, `benchmarkId`, `title`, `status`, `nodes`, `edges`, and `projections`.

### V002 - Supported Version

Severity: P0

M1 supports only `graphirVersion: "0.1.0"`.

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

### V040 - Required Projection Target

Severity: P0

The first benchmark graph must declare exactly one Python native projection target for generated source.

### V041 - Source Map Coverage

Severity: P0 for M2 and later, P1 in M1

Every code projection node that is expected to round-trip must be covered by at least one `metadata.sourceMap` node.

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

M1 source maps must name a future compiler contract, not claim that generated code or a compiler implementation already exists.

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

### V090 - No Hidden Compiler Defaults

Severity: P1

The graph must include enough explicit intent and code projection information for a future compiler contract to be written without relying on unstated behavior.

For `B0-python-cli-calculator`, this includes operation semantics, argument parsing, output formatting, success exit code, and invalid input behavior.

### V100 - No Implementation Claims

Severity: P0 in M1

M1 artifacts must not claim generated code, reconstruction, verifier output, or test execution exists.

## M1 Fixture Review Checklist

For `docs/examples/b0-python-cli-calculator.graph.json`, a reviewer should check:

- JSON parses successfully
- IDs are stable and unique
- node and edge kinds are known
- all edge endpoints exist
- product intent is represented
- add and subtract behavior are represented
- Python module/function/CLI projections are represented
- source map metadata nodes exist for generated code projections
- tests are represented as expectations, not executed results
- evidence and authority are present and linked
- history delta is present and linked
- code-only loss model is explicit
