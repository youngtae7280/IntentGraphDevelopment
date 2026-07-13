# P9.23 Relation-Aware C# Graph Workbench

## Purpose

P9.23 corrects a visual quality limit in the full WindowsUtility graph. The previous
projection contained syntax containment and import facts, but it had no resolved
cross-module call, reference, construction, inheritance, or implementation links.
Without those links, a layout can only arrange disconnected source groups decoratively.

## Boundary

```text
immutable C# snapshot + syntax fact receipt
  -> local Roslyn symbol sidecar (read-only, no build)
  -> validated relation overlay record in the local project workspace
  -> full graph with relation-aware community placement
```

The sidecar accepts only local code facts from the validated snapshot and records only
these relation kinds:

- `calls`
- `references`
- `constructs`
- `inherits`
- `implements`

It is not a project build or a full MSBuild workspace. Compilation diagnostics remain
visible as diagnostic counts and the output claims only `resolved-local-symbol` scope.

## Rendering Contract

- Every graph node and edge remains loaded in the full-graph lens.
- Module centers use a deterministic, small force pass over recorded cross-module
  local-symbol links; the browser runs no physics layout at load time.
- File and symbol placement remains deterministic inside each module community.
- Zoom uses five fixed style bands. A full Cytoscape restyle can occur only when a
  band boundary is crossed, not on every wheel event.
- Low-detail code relations remain faintly visible instead of being removed.
- The inspector exposes the relation kind, endpoints, confidence, interpretation, and
  sidecar provenance when a relation is selected.

## Authority

```text
targetRepositoryMutation: false
targetBuildExecuted: false
targetRestoreExecuted: false
networkRequired: false
credentialAccessAllowed: false
graphMutationApplied: false
```

Recording the sidecar changes only the local IntentGraph project-state workspace. The
source snapshot is immutable and the target WindowsUtility repository is not read or
written by the record operation.

## Task-History Follow-up

P9.24 now groups recorded work lifecycle facts into selectable stages on this same
full graph. It is deliberately record-derived rather than a complete independent
historical graph-revision store. The next history boundary must persist immutable
before/after projection references when each stage is recorded.
