# Prior-Art Map

This document records known related systems for Phase 0. It is a working map for build, borrow, integrate, learn, or differentiate decisions.

Primary source sweep date: 2026-07-09.

## Research Rule

Before implementing a capability, update this map with the strongest known systems for that capability and record a build/borrow/integrate decision.

## Strongest Systems By Capability

| Capability | Strongest known systems | M0/P1.R decision pressure |
|---|---|---|
| semantic overlay over code | Graphify, RepoGraph, Sourcegraph, SCIP, Kythe, Glean, PROV/Git integrations | define IntentGraph as consistency/change orchestration, not code replacement |
| model as source | OMG MDA, Eclipse EMF, JetBrains MPS, MetaEdit+ | do not claim model-as-source novelty; graph-first generation is a limited mode |
| textual language workbench | Xtext, Spoofax, MontiCore, Rascal | learn before building language infrastructure |
| projectional language workbench | JetBrains MPS | learn; avoid broad workbench duplication |
| model-to-text generation | Acceleo, OMG MOFM2T, MPS generators, MetaEdit+ | treat deterministic generation as a bounded experiment or generated-code mode |
| bidirectional model consistency | Triple Graph Grammars, eMoflon::IBeX, QVT Relations | learn round-trip semantics before custom verifier design |
| code graph/static analysis | Joern/Code Property Graph, CodeQL | do not build broad code analysis first |
| symbol/code intelligence index | SCIP, Kythe, Glean, LSIF, SemanticDB, Sourcegraph | borrow concepts and compare outputs |
| generated-code provenance | Kythe generated-code indexing | learn source-to-generated mapping patterns |
| AI repository context graphs | Graphify, RepoGraph, code graph model research | differentiate proposal/context from authority/source |
| graph visualization | Sirius, Cytoscape.js, Graphviz, D3, Mermaid | integrate or learn later; no M0/M1 UI |
| provenance/evidence | W3C PROV, OpenLineage, SLSA, in-toto, SPDX/GUAC | build IntentGraph binding, not generic provenance |
| authority/policy | GitHub CODEOWNERS, protected branches, Open Policy Agent, in-toto layouts, TUF roles | build minimal authority envelope; benchmark policy engines before inventing one |
| change history | Git commit graph | borrow Git; build semantic graph deltas only where Git lacks node meaning |
| deterministic validation | Reproducible Builds, Bazel hermeticity | learn stable input/output discipline |

## Model-Driven Engineering

### OMG Model Driven Architecture

Source: <https://www.omg.org/mda/>

MDA provides the standards-level precedent for structuring software specifications as models and separating platform-independent business/application logic from platform-specific technology. IntentGraph must not present model-to-code as novel.

Decision: learn and differentiate. IntentGraph focuses on overlay/code consistency, evidence, authority, mappings, and history rather than broad MDA platform abstraction.

### Eclipse EMF

Source: <https://eclipse.dev/emf/>

EMF is a mature modeling framework and code generation facility around structured models, Ecore, XMI persistence, reflective APIs, EMF.Edit, and EMF.Codegen.

Decision: learn. Consider integration only if later GraphIR storage or metamodeling needs outweigh the cost of adopting the EMF ecosystem.

### Acceleo and MOFM2T

Sources: <https://eclipse.dev/acceleo/>, <https://www.omg.org/spec/MOFM2T/1.0/About-MOFM2T>

Acceleo is an EMF-oriented model-to-text generator aligned with OMG model-to-text ideas. It includes protected areas for generated code that may be manually modified.

Decision: learn. IntentGraph must define a sharper preservation metadata and reconstruction contract than ordinary protected generated regions.

### MetaEdit+

Source: <https://www.metacase.com/products.html>

MetaEdit+ is mature commercial domain-specific modeling tooling with full code generation from models. It is a strong pressure against building a general DSM platform.

Decision: learn and differentiate. IntentGraph's Phase 0 graph/code/reconstruction loop is a generated-code experiment, not a DSM/workbench ambition.

## Language Workbenches

### JetBrains MPS

Sources: <https://www.jetbrains.com/mps/>, <https://www.jetbrains.com/help/mps/mps-faq.html>

MPS is the strongest projectional language workbench comparator. It directly edits and persists structured AST/abstract syntax graph nodes, supports custom notations, constraints, type systems, refactoring, and code generation.

Decision: learn. Do not rebuild a general projectional workbench in Phase 0.

### Xtext, Spoofax, MontiCore, and Rascal

Sources: <https://eclipse.dev/Xtext/>, <https://spoofax.dev/>, <https://monticore.github.io/monticore/>, <https://www.rascal-mpl.org/>

These systems cover language definition, parser/compiler/editor generation, language composition, transformation, source analysis, and DSL tooling.

Decision: learn. M1 may define a tiny IntentGraph overlay schema or data shape, but should not become a general language engineering project.

## Bidirectional Transformation

### QVT

Source: <https://www.omg.org/spec/QVT/1.3/About-QVT>

QVT defines model transformation languages, including Relations, Operational Mappings, and Core. It is a standards-level prior art for model/model transformation.

Decision: learn. IntentGraph's verifier must explain where declared equality/projection differs from QVT-style model transformation.

### Triple Graph Grammars and eMoflon::IBeX

Source: <https://emoflon.org/ibex/>

Triple Graph Grammars specify consistency relations between models and can derive translators, synchronizers, and consistency-restoring operations. eMoflon::IBeX is a strong conceptual comparator, but its site states that IBeX-TGG development was discontinued in 2024.

Decision: learn. TGGs are the strongest round-trip semantics pressure, but Phase 0 should build only the minimal IntentGraph-specific equality and preservation contract.

### ATL

Source: <https://eclipse.dev/atl/>

ATL is a model-to-model transformation technology. It is relevant for GraphIR transformations, but less directly for source-code reconstruction.

Decision: learn.

## Code Graph And Code Intelligence

### Joern / Code Property Graph

Source: <https://docs.joern.io/code-property-graph/>

Joern generates Code Property Graphs for static analysis. A CPG is a directed, edge-labeled, attributed multigraph that merges syntax, control flow, and data-flow views for querying.

Decision: learn. Do not build a broad static analysis graph in Phase 0.

### CodeQL

Source: <https://codeql.github.com/docs/codeql-overview/about-codeql/>

CodeQL is a language and toolchain for semantic code analysis. It lets users query code as data, especially for security analysis and variant discovery.

Decision: learn. CodeQL is a benchmark comparator, not an IntentGraph source model.

### Tree-sitter

Source: <https://tree-sitter.github.io/tree-sitter/>

Tree-sitter is a parser generator and incremental parsing library that builds concrete syntax trees and can update them efficiently as source changes.

Decision: borrow or integrate when a language parser is needed. M2/M3 should prefer standard parsers or Tree-sitter-style tooling over ad hoc parsing.

### SCIP, LSIF, Kythe, Glean, and SemanticDB

Sources: <https://scip-code.org/>, <https://microsoft.github.io/language-server-protocol/specifications/lsif/0.6.0/specification/>, <https://kythe.io/>, <https://kythe.io/docs/schema/indexing-generated-code.html>, <https://glean.software/>, <https://scalameta.org/docs/semanticdb/guide.html>

These systems cover language-agnostic code indexes, symbol/reference facts, persisted LSP-like data, generated-code source mappings, and queryable semantic fact databases.

Decision: borrow concepts and compare. Kythe is especially important for generated-code provenance. Glean is important for typed code facts at scale.

### Sourcegraph

Source: <https://sourcegraph.com/docs/code-navigation>

Sourcegraph provides search-based and precise code navigation, including cross-repository code intelligence.

Decision: learn for UX and code navigation expectations; do not clone.

## AI Repository Context Graphs

### Graphify

Sources: <https://graphify.net/>, <https://github.com/Graphify-Labs/graphify>

Graphify builds queryable knowledge graphs for AI coding assistants from code, docs, papers, and diagrams. It is strong context infrastructure, not an authoritative source graph.

Decision: differentiate. IntentGraph may use context graphs for proposals later, but AI context is not authority and does not replace accepted overlay mappings.

### RepoGraph and Adjacent Research

Sources: <https://arxiv.org/abs/2410.14684>, <https://github.com/ozyyshr/RepoGraph>

RepoGraph is a repository-level code graph module for AI software engineering and reports benchmark gains on SWE-bench-style workflows. Adjacent code graph model and repository planning graph research should be monitored during M6.

Decision: differentiate and monitor. These systems strengthen the case for graph context and code facts, but not for treating the graph as a source-code replacement.

## Visualization And Workbench

Sources: <https://eclipse.dev/sirius/overview.html>, <https://js.cytoscape.org/>, <https://graphviz.org/>, <https://d3js.org/>, <https://mermaid.js.org/>

Sirius, Cytoscape.js, Graphviz, D3, and Mermaid cover graphical modeling workbenches, graph/network visualization, layout, and documentation diagrams.

Decision: integrate or learn later. M7 may prototype visualization boundaries only after core round-trip behavior exists.

## Provenance, Evidence, Authority, And History

### W3C PROV and OpenLineage

Sources: <https://www.w3.org/TR/prov-overview/>, <https://www.w3.org/TR/prov-dm/>, <https://openlineage.io/docs/>

PROV models provenance around entities, activities, and agents. OpenLineage provides an extensible lineage model with facets.

Decision: learn. IntentGraph should align vocabulary with provenance concepts without requiring full RDF/OWL in Phase 0.

### SLSA, in-toto, SPDX, and GUAC

Sources: <https://slsa.dev/>, <https://in-toto.io/>, <https://spdx.dev/>, <https://docs.guac.sh/guac/>

These systems address artifact integrity, supply-chain steps, attestations, software bill of materials, and supply-chain graph aggregation.

Decision: learn and possibly integrate later for external artifact provenance. Do not expand M0 into supply-chain security.

### Git, CODEOWNERS, Branch Protection, and OPA

Sources: <https://git-scm.com/book/en/v2/Git-Internals-Git-Objects>, <https://docs.github.com/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners>, <https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches>, <https://www.openpolicyagent.org/docs>

Git is the change-history substrate. CODEOWNERS and branch protection are practical review-authority mechanisms. OPA is a mature policy-as-code engine over structured data.

Decision: borrow Git, learn from CODEOWNERS, and benchmark/integrate OPA before building custom policy logic.

## Current Differentiation Claim

IntentGraph's proposed differentiation is the combination of:

- semantic overlay over existing source code
- code fact extraction and intent/code mapping
- consistency and change orchestration
- generated-code round-trip verifier as a limited mode
- generated-code preservation metadata where generation is declared
- evidence and authority as overlay concerns
- semantic graph change history linked to version control
- AI-assisted graph/code delta proposal with deterministic acceptance

No single prior-art system reviewed so far replaces that combined overlay thesis, but many systems are stronger in individual lanes. Phase 0's generated-code experiment must therefore be treated as one feasibility slice, while Phase 1 work focuses on overlay mapping rather than rebuilding any one mature lane.

## P1.19 Code Fact Generalization Update

Date: 2026-07-10

Purpose:

Rerun the code-intelligence prior-art gate before opening Phase B fast retrofit/code facts.

Reviewed primary sources:

- Graphify: <https://github.com/Graphify-Labs/graphify>
- SCIP: <https://github.com/scip-code/scip>
- Kythe generated-code indexing: <https://kythe.io/docs/schema/indexing-generated-code.html>
- Kythe indexer writing guide: <https://kythe.io/docs/schema/writing-an-indexer.html>
- Glean: <https://github.com/facebookincubator/Glean>
- Tree-sitter: <https://github.com/tree-sitter/tree-sitter>
- CodeQL: <https://codeql.github.com/docs/>
- Joern: <https://github.com/joernio/joern>
- LSIF specification: <https://microsoft.github.io/language-server-protocol/specifications/lsif/0.4.0/specification/>

P1.19 finding:

The strongest existing systems already cover broad code parsing, symbol/reference indexes, call/reference graphs, code property graphs, static analysis, generated-code indexing, and AI context graphs. IntentGraph should not attempt a broad code graph engine in Phase B.

Phase B differentiation:

IntentGraph should define the overlay-facing fact contract:

- which code facts are accepted
- how source digests, ranges, anchors, confidence, extractor identity, and relation endpoints are validated
- how extracted facts map to Intent Units
- how stale or missing facts fail
- how evidence, authority, and semantic history bind to mappings

Decision pressure:

- Learn from Tree-sitter for incremental syntax extraction.
- Learn from SCIP, Kythe, and Glean for typed symbol/reference fact shape.
- Learn from Kythe for generated-code and source mapping provenance.
- Learn from Graphify and RepoGraph for AI context expectations, but do not treat context graphs as authority.
- Learn from CodeQL and Joern for static-analysis scope boundaries, but do not build a static-analysis engine.

Selected next benchmark:

```text
B1-typescript-rest-api
```

Reason:

B1 should test multi-file, non-Python, route/service/test code facts without mixing in UI workbench or Windows desktop adoption too early.
