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

## M0 Initial Decisions

### 001 - Language Workbench And GraphIR Boundary

Capability: IntentGraph source language and canonical GraphIR boundary
Date: 2026-07-09
Status: accepted for M0

Problem:
IntentGraph needs a source representation, but mature systems already provide broad language workbench and metamodeling infrastructure.

Strongest known existing systems:
JetBrains MPS, Eclipse EMF, Xtext, Spoofax, MontiCore, Rascal, MetaEdit+.

Comparison:
These systems are stronger at general DSL authoring, projectional editing, parser/editor generation, metamodeling, and ecosystem tooling. IntentGraph's Phase 0 need is smaller: one canonical graph representation that can support compiler, reconstructor, verifier, evidence, authority, and history fields for a tiny benchmark.

Decision: build minimal boundary; learn from prior art.

Reason:
Adopting a full language workbench before proving the round-trip thesis would bury the unique question. M1 should define only the smallest language/GraphIR surface required for the first benchmark.

Benchmark required:
The first benchmark graph must be expressible without hidden implementation rules and must include nodes for intent, code projection, preservation metadata, evidence, authority, and change history.

Impact on roadmap:
M1 remains definition-only unless explicitly authorized.

Review trigger:
If M1 starts requiring general editor, parser, or metamodeling infrastructure, rerun the prior-art gate.

### 002 - Model-To-Code Generation

Capability: deterministic graph-to-source compiler
Date: 2026-07-09
Status: accepted for M0

Problem:
IntentGraph needs `Native(G)`, but model-to-text generation is mature prior art.

Strongest known existing systems:
Acceleo, OMG MOFM2T, JetBrains MPS generators, MetaEdit+, EMF.Codegen.

Comparison:
Existing systems already generate source code from structured models. IntentGraph must prove deterministic generation plus preservation metadata that supports graph reconstruction and equality.

Decision: build tiny IntentGraph-specific compiler boundary; learn from generators.

Reason:
The unique slice is not generic code generation. It is generation that carries enough metadata for `Retrofit(Native(G)) = G`.

Benchmark required:
Generate one tiny Python CLI calculator from a declared graph and stable metadata. The same graph must produce byte-stable generated files under the same generator version.

Impact on roadmap:
M2 may implement only the tiny deterministic path after M1 passes.

Review trigger:
If generation scope expands beyond the tiny benchmark, compare again with Acceleo/MPS/MetaEdit+.

### 003 - Round-Trip And Bidirectional Semantics

Capability: reconstruction equality, projection, and consistency rules
Date: 2026-07-09
Status: accepted for M0

Problem:
IntentGraph needs a verifier, but bidirectional transformation systems already address model consistency.

Strongest known existing systems:
Triple Graph Grammars, eMoflon::IBeX, QVT Relations.

Comparison:
TGG/QVT systems are stronger at model/model consistency theory. IntentGraph's first loop is narrower: graph source to generated source code plus metadata, then reconstructed graph, then equality/projection report.

Decision: build minimal equality/projection contract; learn from TGG/QVT.

Reason:
The first benchmark needs explicit equality and loss rules. A full bidirectional transformation engine is not justified in Phase 0.

Benchmark required:
For the tiny benchmark, verifier must prove `Retrofit(Native(G)) = G` with metadata and must separately report the lossy `RetrofitCodeOnly(C) ~= ProjectionCode(G)` result.

Impact on roadmap:
M3/M4 must document reconstruction loss and equality rules before claiming round-trip success.

Review trigger:
If a stronger active TGG/QVT implementation can directly satisfy the tiny benchmark, apply the late prior-art protocol before continuing custom verifier work.

### 004 - Code Graph Extraction

Capability: extracting code facts for reconstruction and comparison
Date: 2026-07-09
Status: accepted for M0

Problem:
IntentGraph needs code-to-graph reconstruction, but broad code extraction and static analysis are mature.

Strongest known existing systems:
Joern/Code Property Graph, CodeQL, Tree-sitter, SCIP, Kythe, Glean, LSIF, SemanticDB, Sourcegraph.

Comparison:
These systems are stronger at language parsing, code facts, symbol references, navigation, static analysis, and scalable code intelligence. IntentGraph only needs generated-code reconstruction for a tiny metadata-bearing benchmark in Phase 0.

Decision: borrow/compare before building; build only tiny generated-code reconstructor.

Reason:
Building a general code extractor first would violate the prior-art gate. M3 may use standard language parsers or the host language AST where practical.

Benchmark required:
The generated Python calculator must be reconstructable from generated source plus sidecar metadata. Code-only reconstruction must be explicitly marked as a lossy projection.

Impact on roadmap:
General repository extraction is out of Phase 0 unless a milestone review changes direction.

Review trigger:
If M3 requires arbitrary source-code extraction, compare against Tree-sitter, Kythe, SCIP, Glean, Joern, and CodeQL before implementation.

### 005 - Generated-Code Preservation Metadata

Capability: mapping graph nodes to generated source and back
Date: 2026-07-09
Status: accepted for M0

Problem:
Generated code must preserve enough source graph identity to reconstruct non-code graph meaning.

Strongest known existing systems:
Kythe generated-code indexing, Source Maps, compiler debug metadata, Acceleo protected areas.

Comparison:
Kythe is the strongest explicit generated-code source mapping comparator. IntentGraph needs a smaller metadata contract that maps source graph nodes, generated source ranges, evidence links, authority records, and change history links.

Decision: build minimal metadata contract; learn from Kythe.

Reason:
Preservation metadata is central to the round-trip thesis.

Benchmark required:
Every generated code unit in the first benchmark must be linked to graph node IDs and generator version. Reconstructor must fail loudly if required metadata is missing or inconsistent.

Impact on roadmap:
M1 must include metadata fields; M2/M3 must preserve and consume them.

Review trigger:
If metadata becomes a full cross-language indexing scheme, compare again with Kythe/SCIP/Glean.

### 006 - Evidence And Provenance Binding

Capability: evidence attached to graph/code/reconstruction claims
Date: 2026-07-09
Status: accepted for M0

Problem:
IntentGraph treats evidence as first-class, but provenance and evidence standards already exist.

Strongest known existing systems:
W3C PROV, OpenLineage, SLSA, in-toto, SPDX, GUAC.

Comparison:
These systems are stronger at generic provenance vocabularies, lineage events, supply-chain attestations, and artifact metadata. IntentGraph's unique work is binding evidence to graph nodes, generated code, reconstruction results, verifier claims, and accepted deltas.

Decision: build IntentGraph binding; learn and borrow formats where appropriate.

Reason:
Phase 0 should avoid inventing generic provenance while still preserving the thesis-critical evidence path.

Benchmark required:
The first benchmark must include at least one evidence record linked to a graph node and verifier output.

Impact on roadmap:
M5 must preserve evidence through the loop.

Review trigger:
If evidence design turns into supply-chain attestation, rerun prior-art against SLSA/in-toto/SPDX/GUAC.

### 007 - Authority And Policy Boundary

Capability: deciding whether proposed graph/code deltas are accepted
Date: 2026-07-09
Status: accepted for M0

Problem:
AI proposals must not become authority, but custom policy engines are risky to invent.

Strongest known existing systems:
Open Policy Agent, GitHub CODEOWNERS, branch protection, in-toto layouts, TUF role metadata.

Comparison:
OPA is stronger for policy-as-code over structured data. CODEOWNERS and branch protection are practical review authority models. in-toto and TUF provide strong role/step authority analogies.

Decision: build minimal authority envelope; benchmark or integrate OPA before custom policy logic.

Reason:
IntentGraph needs explicit authority records, not a new policy language in Phase 0.

Benchmark required:
The first benchmark must distinguish proposer, validator, reviewer/authority, decision, and accepted state.

Impact on roadmap:
M5/M6 must preserve authority records and keep AI as proposal-only.

Review trigger:
If M6 needs nontrivial policy evaluation, compare OPA/Rego before building.

### 008 - Change History

Capability: preserving change history through graph/code/reconstruction
Date: 2026-07-09
Status: accepted for M0

Problem:
IntentGraph needs semantic graph history, but Git already owns chronological content history.

Strongest known existing systems:
Git commit graph, Git notes, code review history.

Comparison:
Git is stronger as a version-control substrate. It does not know graph-node semantic deltas, authority status, or verifier equality claims.

Decision: borrow Git; build graph semantic delta history linked to Git commits.

Reason:
Replacing Git would be scope expansion. IntentGraph should add meaning, not duplicate VCS storage.

Benchmark required:
The first benchmark must model a graph semantic delta and link it to a commit placeholder or commit ID once implementation begins.

Impact on roadmap:
M5 must preserve semantic history fields through the loop.

Review trigger:
If history storage becomes VCS-like, stop and narrow.

### 009 - Visualization And Workbench

Capability: visualizing graph, code projection, evidence, authority, and round-trip state
Date: 2026-07-09
Status: accepted for M0

Problem:
Visualization is useful, but graph/workbench tools are mature and UI before semantics would distract.

Strongest known existing systems:
Sirius, Cytoscape.js, Graphviz, D3, Mermaid, Sourcegraph.

Comparison:
Existing tools are stronger at graph rendering, layouts, modeling workbenches, and code navigation UI. IntentGraph first needs verified core semantics.

Decision: integrate or learn later; no UI before round-trip core.

Reason:
The roadmap explicitly defers workbench/visualization to M7.

Benchmark required:
M7 must compare visualization needs against existing graph visualization tools.

Impact on roadmap:
M7 remains boundary/prototype only after M4, preferably M5.

Review trigger:
If UI appears before M4 passes, stop and return to core round-trip work.

### 010 - AI Proposal Workflow

Capability: AI-generated graph/code deltas
Date: 2026-07-09
Status: accepted for M0

Problem:
AI repository graph tools can improve context, but AI output must not be authority.

Strongest known existing systems:
Graphify, RepoGraph, Sourcegraph/Cody-style context systems, code graph model research.

Comparison:
These systems are stronger at context retrieval and proposal support. They do not make an intent graph the primary source or prove round-trip consistency with authority and evidence.

Decision: differentiate; possibly integrate context tools later.

Reason:
IntentGraph's AI boundary is proposal-only. Deterministic validation and explicit authority decide acceptance.

Benchmark required:
M6 must represent an AI proposal as a delta and reject or accept it only through deterministic validation and authority records.

Impact on roadmap:
No AI runtime before M6.

Review trigger:
If AI output is treated as accepted evidence or authority, stop and fix the design.
