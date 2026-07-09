# IntentGraph Formal Blueprint

Status: draft center of gravity for M1 plus Phase 1 Intent Unit revision note

This blueprint is not the final architecture. It is the M1 formal center of gravity: a compact design map that keeps the source graph language, GraphIR boundary, preservation metadata, compiler/reconstructor contracts, and verifier target aligned while Phase 0 remains intentionally tiny.

This document must be revised when prior-art review, milestone review, benchmark evidence, or round-trip results show that a definition is too weak, too broad, or wrong.

Phase 0 proved the tiny flat-GraphIR loop. Phase 1 must revise the source structure around Intent Units before larger benchmarks are added. See `docs/design/intent-unit-model.md`.

## Layer 1: Formal Definitions

### Core Loop

```text
G -> Native(G) -> (C, mu) -> Retrofit(C, mu) -> G' -> Verify(G, G')
```

Definitions:

- `G`: source intent graph. This is the primary source artifact.
- `Native`: graph-to-code compiler.
- `C`: generated source code. Code is output, not source authority.
- `mu`: preservation metadata emitted with generated source.
- `Retrofit`: code-to-graph reconstructor.
- `G'`: reconstructed graph.
- `Verify`: equality/projection checker.
- `D`: diagnostics emitted by passes. Diagnostics may include errors, warnings, trace facts, and review notes.

Phase 0 must prove or weaken this loop on one tiny benchmark before broader language, workbench, AI, or multi-language scope is added.

### IntentGraph Tuple

```text
G = (V, E, kindV, kindE, attr, prov, auth, hist, meta)
```

Definitions:

- `V`: finite set of graph nodes.
- `E`: finite set of directed graph edges.
- `kindV`: function assigning each node in `V` a supported node kind.
- `kindE`: function assigning each edge in `E` a supported edge kind.
- `attr`: attribute map for nodes and edges.
- `prov`: provenance and evidence model attached to graph claims, compiler activities, reconstructor activities, verifier results, and decisions.
- `auth`: authority model that records proposer, validator, required authority, reviewer or decision authority, decision, and accepted state.
- `hist`: semantic graph history, represented as proposed, accepted, rejected, or superseded graph deltas linked to ordinary version control when available.
- `meta`: graph-level metadata, including version, benchmark identity, projection declarations, preservation expectations, and verification expectations.

M1 does not define every possible node or edge kind. It defines layers and the tiny `B0-python-cli-calculator` subset in `docs/language/graphir-boundary.md` and `docs/examples/b0-python-cli-calculator.graph.json`.

### Phase 1 Intent Unit Shape

Phase 0 used a flat GraphIR document. That is not the intended long-term source shape.

The next revision treats Intent Units as the primary source-level development units:

```text
G_unit = (U, EU, IU, meta)
```

Where:

- `U`: finite set of Intent Units.
- `EU`: typed relationships between Intent Units.
- `IU`: mapping from each unit to its internal graph.
- `meta`: graph-level metadata, projection declarations, verification expectations, and versioning.

Each unit is a stable, compilable, reconstructable development meaning unit:

```text
u = (
  id,
  kind,
  contract,
  internalGraph,
  projection,
  reconstruction,
  verification,
  evidence,
  authority,
  history,
  status
)
```

Phase 1 must reinterpret the B0 flat graph as unit-structured source before broadening the benchmark. Phase 0 node and edge kinds may remain valid, but they should live inside or between Intent Units rather than forming an unbounded flat bag of facts.

### Preservation Metadata

```text
mu = (nodeMap, edgeMap, graphDigest, projectionRules, hiddenState)
```

Definitions:

- `nodeMap`: mapping from source graph node IDs to generated source artifacts, generated ranges, symbols, or projection IDs.
- `edgeMap`: mapping from source graph edge IDs to generated source artifacts, relationship facts, or projection IDs when an edge is emitted or preserved.
- `graphDigest`: canonical digest of the source graph or relevant projection used to detect stale metadata.
- `projectionRules`: declared rules for which graph parts are emitted, preserved only in metadata, or excluded from generated source.
- `hiddenState`: required non-code reconstruction state that cannot be recovered from `C` alone.

Exact round-trip is generally impossible without `mu`:

```text
Retrofit(C, mu) -> G'
RetrofitCodeOnly(C) -> G_code
G' may equal G
G_code can only approximate ProjectionCode(G)
```

Loss model without `mu`:

- product intent wording may be absent from generated source
- evidence records are not ordinary source-code facts
- authority decisions are not ordinary source-code facts
- semantic graph history is not ordinary source-code history
- stable graph IDs may be absent or ambiguous
- projection choices may be indistinguishable from hand-written code

## Layer 2: Invariants And Rules

### TypeCheck Invariant

```text
TypeCheck(G) <=>
  UniqueNodeIds(V)
  and UniqueEdgeIds(E)
  and EdgeEndpointsExist(E, V)
  and SupportedNodeKinds(kindV)
  and SupportedEdgeKinds(kindE)
  and EdgeEndpointKindsAllowed(kindE, kindV)
  and RequiredAttrsPresent(attr, kindV, kindE)
  and ProvenancePresent(prov)
  and AuthorityWellFormed(auth)
  and HistoryWellFormed(hist)
  and MetadataWellFormed(meta)
```

`TypeCheck(G)` means the graph is structurally well-formed for the declared IntentGraph version.

`TypeCheck(G)` does not mean:

- evidence is accepted
- authority is granted
- generated code exists
- runtime behavior is satisfied
- tests pass
- round-trip equality has been proven
- AI output is trusted

Those claims require separate evidence, authority, runtime, and verifier results.

### Stable Identity Rules

Stable identity is required because generated source, metadata, reconstructed graph state, evidence, authority, and history must all refer to the same graph facts.

Rules:

- node IDs are durable source identities, not array indexes
- edge IDs are durable relationship identities, not derived list positions
- generated code may carry graph IDs through `mu`, but generated code is not the source of those IDs
- canonicalization must ignore incidental ordering and formatting
- local absolute paths, timestamps, and machine-specific state must not affect `Canon(G)`

### Authority Rules

Authority records decide whether a proposed change or claim is accepted.

An authority record must distinguish:

- proposer
- proposer type
- required authority
- validator
- reviewer or decision authority
- decision
- decision status

Accepted changes must have an authority record. A future policy engine may help evaluate authority, but the graph must preserve the decision record.

### Evidence Rules

Evidence records support claims. They do not accept themselves.

```text
EvidenceObserved(e) != EvidenceAccepted(e)
```

Examples of evidence:

- requirement note
- test plan
- test result
- verifier report
- source mapping report
- prior-art decision
- manual review record

Acceptance requires authority and deterministic validation appropriate to the claim.

### AI Boundary Rule

AI output is proposal, not authority.

AI may propose graph changes, code changes, evidence candidates, or review observations. Those outputs become accepted graph state only after deterministic validation and required authority.

### Generated Code Rule

Generated code is not proof.

Working generated code may support evidence, but it does not prove the source graph, preservation metadata, reconstruction, or authority boundary. A generated program can run while round-trip consistency still fails.

### Workbench Projection Rule

A visualization or workbench is a report or projection of graph/compiler/reconstructor/verifier state.

It is not authority.

Workbench state must not silently change accepted graph state. Any graph change from a workbench action must become a delta and pass the same validation, evidence, and authority boundary as other changes.

### Imported Systems Rule

Existing tools may be imported as facts, not as accepted source graph truth.

```text
Import(X) -> SourceFacts
```

`SourceFacts` from code graph tools, language servers, static analyzers, provenance tools, or AI context systems may inform proposals, diagnostics, benchmarks, or evidence. They become accepted graph state only through deterministic validation and authority.

## Layer 3: Algorithms And Pass Pipeline

### Native Compiler Contract

```text
Native(G, target, config) -> (C, mu, D)
```

Where:

- `target`: declared generation target, such as `python`.
- `config`: deterministic compiler configuration.
- `D`: diagnostics, including warnings, errors, and trace notes.

Preconditions:

- `TypeCheck(G)` is true.
- `target` is declared in `G.meta` or `G.projections`.
- `config` is explicit and stable.
- all graph nodes required by the target have stable IDs.
- required preservation metadata fields are present or derivable by the compiler.
- no accepted AI proposal is applied without authority.

Postconditions:

- `C` is generated deterministically from `Canon(G)`, `target`, and `config`.
- `mu.nodeMap` covers every generated code projection node required for round-trip.
- `mu.edgeMap` covers every generated relationship required for round-trip, or records why it is projection-only.
- `mu.graphDigest` identifies the canonical input graph or declared projection.
- `mu.projectionRules` records emitted, metadata-only, and excluded graph parts.
- `mu.hiddenState` records non-code reconstruction state needed for exact round-trip.
- `D` reports all unsupported graph parts rather than silently dropping them.

M1 defines this contract but does not implement it. M2 is the first milestone allowed to implement the tiny `Native` path.

### Retrofit Reconstructor Contract

```text
Retrofit(C, mu, config) -> (G', D)
RetrofitCodeOnly(C, config) -> (G_code, D)
```

Preconditions for `Retrofit(C, mu, config)`:

- `C` is available.
- `mu` is available and well-formed.
- `mu.graphDigest` is compatible with the expected source graph or declared projection.
- `config` declares the target language and reconstruction rules.

Postconditions for `Retrofit(C, mu, config)`:

- `G'` contains reconstructed nodes, edges, attributes, provenance, authority, history, and metadata covered by `mu`.
- `D` reports stale, missing, contradictory, or unsupported metadata.
- reconstruction does not rely on AI judgment.

`RetrofitCodeOnly(C, config)` may produce only lossy, extracted, or inferred code facts:

- syntax facts
- symbol facts
- call/reference facts
- limited domain hints derived from names or comments

It must not claim full intent, evidence, authority, or semantic history recovery.

### Round-Trip Verifier Contract

```text
RoundTrip(G, target, config) =
  let (C, mu, D1) = Native(G, target, config)
  let (G', D2) = Retrofit(C, mu, config)
  Verify(G, G', mu, config)
```

Canonicalization:

```text
Canon(G) = stable serialization of G after normalization
```

`Canon(G)` must be independent of file ordering, incidental object ordering, local absolute paths, timestamps, and formatting.

Exact equality:

```text
GraphEqual(G, G') <=> Canon(G) == Canon(G')
```

Projection equality:

```text
ProjectionEqual(G, G', P) <=> Canon(Project(G, P)) == Canon(Project(G', P))
```

`Verify(G, G', mu, config)` must declare whether it is checking exact graph equality or projection equality. A partial or lossy comparison must never be reported as exact equality.

### AI Proposal Algorithm

```text
AI(Context(G, q)) -> Proposal
```

AI may produce a proposal from graph context and a question `q`.

```text
Accept(Proposal, G) <=>
  ProposalWellFormed(Proposal)
  and CanApply(G, Proposal.delta)
  and DeterministicChecksPass(Proposal.delta, G)
  and RequiredEvidenceAccepted(Proposal.delta)
  and RequiredAuthorityGranted(Proposal.delta)
```

AI proposal text, confidence, or plausibility is not enough for acceptance.

### Change Recurrence

```text
G_0 = initial intent graph
G_{t+1} = Apply(G_t, Delta_t)
```

`Delta_t` may be proposed, rejected, accepted, or superseded.

`CanApply(G_t, Delta_t)` requires:

- `TypeCheck(G_t)` is true
- delta references existing nodes or declares new stable IDs
- delta preconditions match the current graph version or digest
- required evidence is present for the delta type
- required authority is granted for accepted deltas
- applying the delta preserves `TypeCheck(G_{t+1})`
- diagnostics are emitted for conflicts or unsupported changes

### Phase 0 Minimal Pass Pipeline

```text
LoadGraphSource
  -> ParseGraph
  -> NormalizeGraph
  -> TypeCheckGraph
  -> CompileNative
  -> EmitSourceAndMetadata
  -> RetrofitGeneratedSource
  -> TypeCheckReconstructedGraph
  -> VerifyRoundTrip
  -> EmitDiagnosticsAndReport
```

Equivalent pass labels:

```text
Pass_0 LoadGraphSource
Pass_1 ParseGraph
Pass_2 NormalizeGraph
Pass_3 TypeCheckGraph
Pass_4 CompileNative
Pass_5 EmitSourceAndMetadata
Pass_6 RetrofitGeneratedSource
Pass_7 TypeCheckReconstructedGraph
Pass_8 VerifyRoundTrip
Pass_9 EmitDiagnosticsAndReport
```

M1 defines the source shape and typecheck expectations. M2 may implement passes through source and metadata emission for the tiny benchmark. M3 adds retrofit. M4 adds round-trip verification. M5 extends verifier coverage to evidence, authority, and history.

## Layer 4: Concrete B0 Fixture Example

Fixture:

```text
docs/examples/b0-python-cli-calculator.graph.json
```

M1 status:
The fixture is a source graph target, not a generated project. M1 does not generate source code, metadata files, reconstructed graphs, or verifier reports.

Future M2/M3/M4 target:

- `G`: B0 calculator intent graph from `docs/examples/b0-python-cli-calculator.graph.json`.
- `C`: future generated `calc.py`.
- `mu`: future generated `calc.intentgraph.json`.
- `G'`: future reconstructed graph from `Retrofit(C, mu, config)`.
- expected proof: `Verify(G, G') = pass`.

Expected Phase 0 B0 loop:

```text
G_b0
  -> Native(G_b0, python, config_b0)
  -> (calc.py, calc.intentgraph.json, D1)
  -> Retrofit(calc.py, calc.intentgraph.json, config_b0)
  -> (G'_b0, D2)
  -> Verify(G_b0, G'_b0, mu_b0, config_b0)
  -> pass
```

The B0 fixture currently declares:

- product intent for add and subtract behavior
- domain concepts for integer operands and calculator operations
- source graph code projection nodes for module, function, and CLI targets
- planned preservation metadata nodes using `compilerContract`
- planned test cases for add and subtract
- evidence records as planned evidence, not accepted runtime proof
- authority record for the M1 fixture decision
- semantic history delta for initial graph creation
- code-only loss model
- verification expectations for exact round-trip with metadata and lossy code-only projection

If M2, M3, or M4 changes any of these expectations, the fixture and this blueprint must be reviewed together.

## Layer 5: Failure And Pivot Criteria

The thesis should narrow or pivot if any of these happen inside the approved Phase 0 scope:

- B0 cannot preserve evidence, authority, and history through the metadata-backed round-trip.
- B0 requires broad language-workbench machinery before the tiny benchmark can be expressed.
- B0 requires a broad arbitrary source-code extractor before generated-code reconstruction is proven.
- `mu` is missing but exact reconstruction is still claimed.
- generated code alone is claimed to recover the full intent graph.
- generated code works but `Verify(G, G')` fails and the failure is dismissed as acceptable exact round-trip.
- AI proposal output is promoted to authority without deterministic checks and explicit decision records.
- imported facts from existing tools are treated as accepted graph truth without authority.
- evidence is observed but reported as accepted without authority.
- visualization or workbench state is treated as source authority.
- existing systems are stronger at an extraction, workbench, policy, provenance, or generation capability and the roadmap does not revise build/borrow/integrate decisions.

Invalid claims:

- `RetrofitCodeOnly(C) = G` for full graphs with evidence, authority, and history.
- `TypeCheck(G)` proves runtime behavior.
- generated code proves the thesis without reconstruction and verification.
- AI confidence proves a graph delta.
- a workbench view is the accepted graph.

## Prior-Art Pressure

M1 and later milestones must keep these pressure points visible:

- MPS and language workbenches pressure the language/workbench design. IntentGraph should not become a general projectional editor before round-trip semantics are proven.
- EMF, MDA, Acceleo, and model-driven engineering pressure model-to-code generation. IntentGraph must not claim ordinary model generation as new.
- QVT, Triple Graph Grammars, and eMoflon pressure round-trip and consistency semantics. IntentGraph must explain its equality, projection, and metadata rules clearly.
- Joern, CodeQL, Graphify, SCIP, Kythe, Glean, LSIF, SemanticDB, and Sourcegraph pressure code fact extraction and generated-code mapping. IntentGraph should borrow or compare before building broad extraction.
- PROV, OPA, Git, SLSA, in-toto, SPDX, GUAC, CODEOWNERS, and branch protection pressure evidence, authority, provenance, and history. IntentGraph should build the graph binding layer, not a weaker replacement for these systems.

## Minimal M1 / Phase 0 Subset

M1 defines layers and the tiny benchmark subset only.

It does not define every possible node kind, edge kind, policy rule, evidence type, code language, or visualization. The current subset is anchored by:

- formal blueprint: `docs/design/intentgraph-formal-blueprint.md`
- language principles: `docs/language/language-principles.md`
- GraphIR boundary: `docs/language/graphir-boundary.md`
- validation rules: `docs/language/validation-rules.md`
- fixture: `docs/examples/b0-python-cli-calculator.graph.json`

The fixture exists so M2 can implement a small compiler contract against a declared graph rather than inventing requirements during implementation.

## Blueprint Revision Rule

This blueprint must change when evidence says it should.

Revision triggers:

- prior-art discovery shows a stronger existing system should be integrated or learned from
- milestone review finds a P0/P1 issue
- a P2 issue is deferred and later becomes blocking
- benchmark results contradict the expected loop
- generated metadata cannot support exact round-trip
- verifier equality rules become misleading
- evidence, authority, or history cannot be preserved in the declared subset

Revisions must be recorded through the same milestone and decision process as other architecture changes.
