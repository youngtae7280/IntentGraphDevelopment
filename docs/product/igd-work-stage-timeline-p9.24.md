# P9.24 Work Stage Timeline

## Purpose

P9.24 makes one recorded user request inspectable as an ordered work lifecycle in
the same relation-aware project graph.

```text
request
  -> candidate code mapping
  -> review-required graph/code proposal
  -> verification and evidence requirements
  -> optional human review receipt
```

The timeline is a read-only projection over already recorded local workspace facts.
It does not create a graph revision, source edit, test result, approval, or runtime
evidence by selecting a stage.

## Per-stage Contract

Each `workStageTimeline[]` record declares:

- a stable work item and ordered stage identifier
- related recorded history, verification, and evidence identifiers
- the stage subgraph: node, edge, and code-fact context identifiers
- graph additions and changes separately
- related code-diff fragments where a non-applied proposal recorded them
- a `revisionKind` that makes the non-applying authority boundary explicit

The Workbench renders stage controls in the left rail. Selecting one focuses the
associated subgraph, highlights stage additions in teal and changed nodes in amber,
and shows counts, record links, authority boundary, and code diff fragments in the
inspector.

## Current WindowsUtility Demonstration

The current local workspace contains one work item with four visible stages:

1. request recorded
2. candidate mapping recorded
3. graph and code delta proposed
4. verification and evidence requirements recorded

The proposal stage exposes two graph additions, three changed C# code facts, six
stage edges, and three review-only unified diff fragments. It remains
`not-applied-review-required`.

## Boundary

P9.24 derives the lifecycle from immutable workspace records. It is not yet a
durable before/after graph-revision store. A future revision-history boundary must
write immutable stage snapshots at record time and compare them directly. Until then,
the timeline accurately exposes recorded graph delta references but does not claim
that every historical complete graph can be reconstructed independently.

```text
targetRepositoryMutation: false
automaticCodeApplication: false
verificationExecution: false
runtimeEvidenceCollection: false
approvalAutomation: false
```
