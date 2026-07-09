# Capability Matrix

This matrix is a prior-art pressure tool, not a product scorecard. A `high` score means the existing system is strong enough that IntentGraph should usually learn, borrow, or integrate rather than rebuild that capability.

Primary source sweep date: 2026-07-09.

| Capability | MPS | EMF / Acceleo | Xtext / Spoofax / MontiCore | QVT / TGG | Joern / CodeQL | SCIP / Kythe / Glean | Graphify / RepoGraph | PROV / OPA / Git | IntentGraph Phase 0 target |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| graph/model as primary source | high | high | medium | medium | low | low | low | low | target |
| graph/model to source code | high | high | high | medium | none | none | low | none | target |
| source code to graph/model facts | low | medium | medium | high if code is modeled | high | high | medium | low | target for generated code only |
| generated-code source mapping | medium | medium | low | medium | low | high in Kythe | low | medium in provenance tools | target |
| explicit preservation metadata | medium | medium | low | medium | low | medium | low | high for provenance/history | target |
| round-trip consistency | medium inside source model | limited | strong for DSL text | high | none | none | none | low | target |
| code symbol/reference graph | medium | medium | medium | medium | high | high | medium | low | limited target |
| static analysis/security query | low | low | low | low | high | medium | low | low | non-goal |
| AI coding context | low | low | low | low | medium | medium | high | low | proposal-only target |
| evidence as first-class source | low | low | low | low | low | low | medium | high for provenance/evidence | target |
| authority and policy acceptance | low | low | low | low | medium | medium | low | high | target |
| change history as semantic graph source | medium | medium | low | medium | low | medium | low | high in Git, low in semantic graph | target |
| graphical workbench / visualization | high | high via Sirius ecosystem | medium | low | low | medium via consumers | high reports/graphs | low | M7 boundary only |

## Notes By Lane

### Model and Language Workbench

MPS, EMF, Acceleo, Xtext, Spoofax, MontiCore, Rascal, MetaEdit+, and Sirius collectively cover most general language-workbench, metamodeling, model-to-code, and graphical workbench ideas. IntentGraph should not start by building a broad language workbench.

M1 should define only the smallest IntentGraph language and GraphIR boundary needed for the first benchmark.

### Bidirectional Transformation

QVT and Triple Graph Grammars are the strongest conceptual pressure on round-trip semantics. IntentGraph must learn from their model/model consistency ideas, but Phase 0 needs a narrower graph/source-code/preservation-metadata equality contract.

### Code Graph and Code Intelligence

Joern/CPG and CodeQL are much stronger than a new Phase 0 custom extractor for static analysis. SCIP, Kythe, Glean, LSIF, SemanticDB, and Sourcegraph are much stronger sources for symbol/reference indexing and generated-code source mapping ideas.

Phase 0 should build only a tiny generated-code reconstructor where metadata is available. General code extraction should be borrowed or compared later.

### AI Context

Graphify and RepoGraph show that repository graphs help AI coding. They do not make graph artifacts authoritative. IntentGraph must keep AI output as proposal data.

### Evidence, Authority, And History

W3C PROV, OpenLineage, SLSA, in-toto, Git, CODEOWNERS, branch protection, OPA, Reproducible Builds, Bazel, SPDX, and GUAC cover mature pieces of provenance, policy, authority, deterministic validation, and artifact metadata.

IntentGraph should build the binding layer that attaches these concerns to graph nodes, code projections, reconstruction claims, and accepted graph deltas.

## M0 Build / Borrow / Integrate Implications

| Track | M0 implication |
|---|---|
| language/workbench | learn; build only minimal IntentGraph language/GraphIR |
| code generation | learn; build deterministic tiny compiler boundary |
| bidirectional semantics | learn; build minimal equality/projection rules |
| code extraction | borrow/compare; do not build broad extractor |
| generated-code metadata | learn from Kythe; build minimal preservation metadata |
| evidence/provenance | learn from PROV/OpenLineage; build IntentGraph binding |
| authority/policy | benchmark OPA before custom policy engine |
| history | borrow Git; build graph semantic deltas |
| visualization | integrate/learn in M7 only |
| AI workflow | differentiate; AI proposes, validation/authority accepts |
