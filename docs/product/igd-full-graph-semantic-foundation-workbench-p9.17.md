# P9.17 Full-Graph Semantic Foundation Workbench

P9.17 corrects two product defects exposed by the first WindowsUtility Workbench:

1. the full graph was replaced by a small semantic-only default, hiding most of the project topology;
2. the retrofit had only one recorded work request, so the visible semantic overlay was too thin to explain the codebase.

The Workbench now loads the full projected graph by default and keeps a truthful semantic foundation distinct from work-specific Intent Units.

## Full Graph Rendering

The default Full graph lens contains every projected node and relation. It does not remove code facts to make the first screen smaller.

- source modules are positioned as deterministic radial communities around the project semantic core
- files form local clusters within their source module
- code facts reveal labels and relation detail progressively as the user zooms
- the browser does not run a force or physics layout on load
- the Cytoscape graph is created once; lens and filter changes change visibility instead of rebuilding the entire graph
- viewport motion uses local texture and edge-detail optimizations

The Semantic overview, Active work, Code topology, and Focus selection lenses remain navigation filters over the same loaded graph. They are not separate graph copies.

## Semantic Foundation

The record-experimental-csharp-semantic-foundation command records a declared semantic baseline in the local project workspace. It does not create Intent Units automatically.

The input artifact may declare:

- source documents and their declared content digests
- project goals
- capabilities linked to code capsules
- project constraints
- verification requirements linked to code capsules

For WindowsUtility, the P9.17 fixture is grounded in existing roadmap, legacy-parity, UI-standard, and regression-smoke documents. Its projection adds:

- 4 source-document nodes
- 3 declared goal nodes
- 8 declared capability nodes
- 2 declared constraint nodes
- 1 declared verification-requirement node

An Intent Unit remains work-specific. The current WindowsUtility fixture therefore has one Intent because it has one explicit work request, not because the system silently invents requirements for every code symbol.

## Local Daily-Use Flow

    python tools/intentgraph.py serve-experimental-csharp-project-workbench \
      --workspace <local-project-workspace> \
      --host 127.0.0.1 \
      --port 8765

The loopback server opens a small page shell first and obtains the full local projection through its own /api/projection route. This avoids embedding the entire fact graph in the initial HTML response.

From the local Workbench, a user can:

1. inspect the entire code and semantic graph;
2. record a work request;
3. select a code fact and record a declared mapping candidate for that work request;
4. inspect a non-applied proposal, graph delta, code-diff fragment, evidence, authority, and history when present.

Mapping remains a candidate. No action records mapping acceptance, source mutation, automatic code application, or approval.

## Boundary

- no target repository mutation
- no source build, launch, provider call, credential access, or network service
- no automatic Intent creation, mapping, proposal acceptance, or code application
- source-document paths remain logical references; no physical target path is stored
- the semantic foundation is declared input with recorded provenance, not an unverified semantic extraction claim

The static HTML export remains a portable snapshot. The loopback server is the intended interactive surface for large projects because it can defer the large graph payload until the page shell is ready.
