# Graph Navigation Model

Milestone: M7

This model defines how a future workbench may navigate the B0 IntentGraph projection.

## Navigation Indexes

The projection must expose:

- `intentUnitsByKind`
- `unitEdgesByKind`
- `nodesByKind`
- `edgesByKind`
- `incomingEdgesByNode`
- `outgoingEdgesByNode`
- `evidenceByTarget`
- `authorityByTarget`
- `historyChangesByDelta`
- `unitMembership`
- `proposalResultsById`

## Node Drill-Down

For a selected node, a workbench may show:

- node ID
- node kind
- label
- attributes
- incoming edges
- outgoing edges
- linked evidence
- authorizing authority
- history deltas that changed the node

## Proposal Drill-Down

For a selected proposal, a workbench may show:

- proposal ID
- validation result
- accepted-for-application status
- proposed nodes
- proposed edges
- post-delta graph validation result
- errors
- authority record ID
- proposal digest

## Unit Drill-Down

For a selected Intent Unit, a workbench may show:

- unit ID
- unit kind
- contract summary
- refinement and cross-unit relationships
- internal graph node IDs
- internal graph edge IDs
- projection and reconstruction expectations
- evidence, authority, and history references

This drill-down is still a projection. It is not accepted authority.

## Diagram Projection

M7 may emit a simple Mermaid graph text block for documentation.

The diagram is intentionally lossy. It helps people orient themselves, but it must not be used for equality, authority, or acceptance decisions.

## Approval-Stage Selection Model

P8.57 requires selection-ready graph projections for approval-stage workbenches.

Every visible graph node must have a stable selection payload:

```text
SelectedNode = {
  id,
  kind,
  label,
  status,
  attributes,
  sourceRefs,
  graphDiffRef,
  codeDiffRefs,
  incomingEdges,
  outgoingEdges,
  evidenceRefs,
  authorityRefs,
  historyRefs,
  deltaRefs
}
```

Every visible graph edge must have a stable selection payload:

```text
SelectedEdge = {
  id,
  kind,
  source,
  target,
  status,
  attributes,
  graphDiffRef,
  confidence,
  provenance,
  evidenceRefs,
  authorityRefs,
  historyRefs,
  deltaRefs
}
```

## Approval-Stage Delta Model

Every approval-stage workbench projection must expose a delta view:

```text
GraphDeltaView = {
  beforeGraphRef,
  afterGraphRef,
  addedNodes,
  removedNodes,
  changedNodes,
  impactedNodes,
  addedEdges,
  removedEdges,
  changedEdges,
  impactedEdges,
  graphNodeDiffs,
  graphEdgeDiffs,
  codeDiffs,
  steps
}
```

Selecting a delta step must highlight the affected nodes and edges and update the detail panel with the evidence, authority, and history records that justify that step.

If the selected node is a code node, or if the selected delta step affects code refs, the workbench must also expose:

```text
CodeDiffView = {
  filePath,
  beforeRange,
  afterRange,
  changeKind,
  diffHunks,
  affectedNodeIds,
  affectedEdgeIds,
  deltaStepId,
  evidenceRefs,
  authorityRefs,
  blockerIfMissing
}
```

`blockerIfMissing` is required whenever a code-affecting graph delta has no corresponding source diff. The workbench must not let that absence look like a clean approval state.

For changed existing graph nodes and edges, the workbench must expose:

```text
GraphElementDiffView = {
  elementId,
  elementKind,
  changeKind,
  beforePayload,
  afterPayload,
  changedFields,
  addedRefs,
  removedRefs,
  changedRefs,
  affectedCodeDiffRefs,
  deltaStepId,
  evidenceRefs,
  authorityRefs,
  blockerIfMissing
}
```

`blockerIfMissing` is required whenever a node or edge is classified as changed but its before/after graph diff payload is absent.
