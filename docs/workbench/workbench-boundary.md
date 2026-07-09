# Workbench Boundary

Milestone: M7

This document defines the Phase 0 workbench boundary. It is not a full IDE, modeling workbench, graph database UI, or code navigation product.

## Core Rule

Workbench state is projection/report state, not authority.

```text
Workbench(G, Reports, Config) -> Projection
```

The workbench may display:

- source graph nodes and edges
- Intent Units and unit refinement/cross-unit relations
- generated code projection summaries
- preservation metadata status
- round-trip verifier status
- evidence, authority, and history status
- AI proposal validation status
- Intent Unit preservation status

The workbench must not silently mutate accepted graph state.

Any edit gesture must become:

```text
WorkbenchAction
  -> Proposal
  -> DeterministicValidation
  -> AuthorityDecision
  -> Delta
  -> Apply(G, Delta)
  -> TypeCheck/Verify
```

## Prior-Art Pressure

M7 compares against mature visualization and workbench systems:

- Eclipse Sirius: <https://eclipse.dev/sirius/doc/>
- Cytoscape.js: <https://js.cytoscape.org/>
- Graphviz: <https://graphviz.org/>
- D3: <https://d3js.org/>
- Mermaid: <https://mermaid.js.org/>
- React Flow: <https://reactflow.dev/>

Decision:

- learn from Sirius for modeling workbench concepts
- integrate or borrow visualization libraries later rather than building layout engines
- use Graphviz or Mermaid-style text output for documentation-friendly diagrams
- use Cytoscape.js, D3, or React Flow only if a later UI prototype needs interactive graph navigation

## M7 Boundary Claim

M7 may emit a static workbench projection artifact.

M7 must not:

- build a full IDE
- replace Sirius, Cytoscape.js, Graphviz, D3, Mermaid, or React Flow
- make visualization state authoritative
- apply AI proposals from the UI
- invent a graph layout engine
- hide verifier failures behind a pretty view

## Required Projection Domains

The B0 workbench projection must include:

- graph summary
- node kind counts
- edge kind counts
- round-trip status
- evidence status
- authority status
- history status
- proposal validation status
- Intent Unit counts and unit membership indexes
- code-only loss boundary
- a navigation model
- an authority disclaimer

## Authority Disclaimer

Every M7 workbench projection must include:

```text
This projection is a report. It is not accepted graph authority.
```

P1.0 extends the projection with Intent Unit fields. These fields remain report state and must not be treated as accepted graph mutation.

## Future Integration Decision

If Phase 1 needs an interactive workbench, start by integrating an existing visualization layer:

- React Flow for node-based editing UI
- Cytoscape.js for graph exploration and analysis
- Graphviz/Mermaid for generated documentation diagrams
- D3 for custom dashboards
- Sirius only if the project intentionally moves into EMF/modeling-workbench territory

That choice requires a new prior-art gate and benchmark.

## Prior-Art Pressure Matrix

| Capability | Stronger existing systems | M7 decision |
|---|---|---|
| graphical modeling workbench | Eclipse Sirius | learn only; do not adopt EMF/modeling-workbench scope in Phase 0 |
| interactive graph exploration | Cytoscape.js, React Flow | integrate later if an interactive UI is needed |
| static documentation diagrams | Graphviz, Mermaid | borrow textual diagram output for orientation only |
| custom dashboards | D3 | learn/integrate later; no custom dashboard framework in Phase 0 |
| code navigation | Sourcegraph, SCIP, Kythe, Glean, LSIF, SemanticDB | do not build code navigation; display generated-code projection summaries only |
| AI/repository context visualization | Graphify, RepoGraph | proposal/context display only; not source authority |
| status dashboard | existing dashboard frameworks plus generated JSON reports | emit static JSON projection first |
