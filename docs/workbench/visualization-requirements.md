# Visualization Requirements

Milestone: M7

M7 visualization exists to inspect the proven Phase 0 generated-code loop. It does not create authority.

## Required Views

### 1. Graph Overview

Shows:

- graph ID
- benchmark ID
- graph digest
- node count
- edge count
- counts by node kind and edge kind

### 2. Round-Trip Status

Shows:

- verifier result
- equality mode
- metadata-backed graph equality
- metadata graph digest status
- M5 metadata-backed claim scope
- evidence/authority/history semantic validation result
- code-only projection boundary
- code-only loss model
- evidence/authority/history domain-subgraph match status

### 3. Evidence / Authority / History

Shows:

- accepted evidence count
- accepted authority count
- accepted history count
- AI final authority count
- verified Git commit count
- current-milestone pending history count

### 4. Proposal Status

Shows:

- proposal count
- accepted-for-application count
- rejected count
- whether AI output was treated as authority
- whether automatic application occurred

### 5. Navigation

Supports conceptual navigation:

- node kind -> nodes
- node -> incoming/outgoing edges
- edge -> source/target nodes
- evidence -> accepted authority
- history delta -> changed nodes
- proposal -> proposed nodes/edges and validation result

## Non-Authority Requirements

The visualization must visibly report:

- workbench projection is not authority
- generated code is output, not source
- code-only projection is lossy
- AI proposals are not accepted unless deterministic validation and authority accept them

## Prototype Requirement

M7 prototype output is a JSON projection report:

```text
generated/b0-python-cli-calculator/workbench-projection.json
```

This keeps Phase 0 inspectable without creating a premature UI.

## Approval-Stage Graph And Delta Requirement

Status: added by the P8.57 approval-workbench requirement.

When a workbench is used for user/coordinator approval, a text/report-only surface is not sufficient. The approval surface must include an interactive graph and delta view good enough for a reviewer to inspect what is being accepted before answering.

Required graph capabilities:

- show nodes and edges as an actual graph, not only as cards or tables.
- support pan and zoom.
- keep node and edge visual sizes readable while zooming.
- support search and filtering by node kind, edge kind, status, and delta state.
- visually distinguish graph clusters or communities when layout data is available.
- visually distinguish accepted/current graph state from proposed or historical delta state.
- make every visible node selectable.
- make every visible edge selectable.
- show selected node details in an inspector panel.
- show selected edge details in an inspector panel.

Required node inspector fields:

- node ID
- node kind
- label
- lifecycle/status
- graph node diff when the selected existing node changed in the current delta
- source artifact or code reference
- code diff when the selected node is a code node or has code refs affected by the current delta
- linked evidence
- linked authority
- linked history/delta records
- incoming edge list
- outgoing edge list

Required edge inspector fields:

- edge ID
- edge kind/relation
- source node
- target node
- lifecycle/status
- graph edge diff when the selected existing edge changed in the current delta
- confidence or provenance when available
- source artifact
- linked evidence
- linked authority
- linked history/delta records

Required delta visualization:

- added nodes
- removed nodes
- changed nodes
- unchanged but impacted nodes
- added edges
- removed edges
- changed edges
- unchanged but impacted edges
- before/after summary counts
- selectable delta step list
- selecting a delta step highlights affected graph nodes and edges
- selecting a code node or code-affecting delta step shows the related source diff
- selecting a changed existing node shows the graph-node before/after diff
- selecting a changed existing edge shows the graph-edge before/after diff

Required code diff behavior:

- code nodes must link to source file/range or code fact references.
- if a selected code node is unchanged, the panel should show the stable source reference and state that no code diff exists for the current delta.
- if a selected code node is added, removed, changed, or impacted, the panel must show the relevant before/after diff hunk.
- diff hunks must preserve file path, before range, after range, and delta reason.
- graph delta and code diff must stay synchronized: selecting a graph delta step highlights affected code nodes, and selecting an affected code node reveals the corresponding diff.
- if source diff cannot be computed, the workbench must show an explicit blocker rather than silently hiding the missing diff.

Required graph node/edge diff behavior:

- added nodes and edges must show their full new payload.
- removed nodes and edges must show their full previous payload.
- changed existing nodes must show before/after changes for attributes, status, labels, source refs, evidence refs, authority refs, history refs, and delta refs.
- changed existing edges must show before/after changes for relation kind, source, target, status, confidence, provenance, evidence refs, authority refs, history refs, and delta refs.
- impacted-but-unchanged nodes and edges must say they are impacted but payload-stable, and must link to the delta step that caused the impact.
- if a node/edge is marked changed but has no before/after graph diff payload, the workbench must show an explicit blocker.

Quality bar:

- Graphify is the minimum usability pressure for graph exploration, click-to-inspect behavior, and visually understandable repository graph presentation.
- IntentGraph does not need to copy Graphify's exact graph shape, but the approval workbench must make the IntentGraph-specific overlay graph, deltas, and related code diffs comparably inspectable.

Non-authority rule:

- Graph layout state, selection state, filters, and visual positions are workbench projection state only.
- Approval must still be recorded through deterministic artifacts and authority records, not by graph UI state alone.
