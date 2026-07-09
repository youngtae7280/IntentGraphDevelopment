# Build / Borrow / Integrate Decisions

Record decisions here before implementing major capabilities.

## Decision Template

```text
Capability:
Date:
Status: proposed | accepted | revised | rejected

Problem:

Strongest known existing systems:

Comparison:

Decision: build | borrow | integrate | learn | differentiate

Reason:

Benchmark required:

Impact on roadmap:

Review trigger:
```

## Initial Decision Biases

These are biases, not final decisions.

### Code Graph Extraction

Bias: integrate or learn before building.

Reason: existing systems such as code property graphs, CodeQL-style databases, SCIP/LSIF, and Graphify-like tools already address source code relationship extraction.

### Graph Visualization

Bias: integrate before building.

Reason: visualization is important, but not unique to the first thesis.

### Graph Language and Round-Trip Semantics

Bias: build the IntentGraph-specific boundary, while learning from model-driven engineering and bidirectional transformation systems.

Reason: this is closest to the unique thesis.

### Evidence and Authority Model

Bias: build.

Reason: this is a key differentiator from ordinary code graph, low-code, and model generation tools.
