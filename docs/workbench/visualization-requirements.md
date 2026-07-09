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
