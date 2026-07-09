# Graph Navigation Model

Milestone: M7

This model defines how a future workbench may navigate the B0 IntentGraph projection.

## Navigation Indexes

The projection must expose:

- `nodesByKind`
- `edgesByKind`
- `incomingEdgesByNode`
- `outgoingEdgesByNode`
- `evidenceByTarget`
- `authorityByTarget`
- `historyChangesByDelta`
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

## Diagram Projection

M7 may emit a simple Mermaid graph text block for documentation.

The diagram is intentionally lossy. It helps people orient themselves, but it must not be used for equality, authority, or acceptance decisions.
