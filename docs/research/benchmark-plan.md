# Benchmark Plan

Benchmarks must exist before implementation claims.

Primary source sweep date: 2026-07-09.

## First Benchmark Selection

Benchmark ID: `B0-python-cli-calculator`

Project:
A tiny Python standard-library CLI calculator with deterministic generated source.

Why this benchmark:

- small enough to inspect manually
- does not require package setup or external services
- can exercise functions, CLI argument parsing, tests, evidence, authority, and history fields
- Python has a standard `ast` module for code-only projection checks
- complex enough to distinguish semantic overlay consistency from ordinary code generation or code graph viewing

Initial product behavior:

```text
calc add 2 3 -> 5
calc sub 5 2 -> 3
```

## Required Phase 0 Benchmark Artifacts

The implementation milestones must eventually produce:

- source intent graph `G`
- canonical GraphIR serialization
- generated Python source
- generated preservation metadata
- generated or declared tests
- reconstructed graph `G'`
- verifier report for `Retrofit(Native(G)) = G`
- code-only reconstruction/projection report
- evidence record linked to graph nodes and verifier output
- authority record showing proposer, validator, reviewer/authority, decision, and accepted state
- graph semantic delta history linked to Git commit identity when available

## Prior-Art Comparator Questions

| Comparator lane | What it can likely do for the benchmark | What IntentGraph must still prove |
|---|---|---|
| MPS / EMF / Acceleo / MetaEdit+ | model-to-code generation and model persistence | generated-code mode remains limited and metadata-backed |
| Xtext / Spoofax / MontiCore | textual DSL parsing, editor/compiler infrastructure | overlay schema boundary without building a broad language workbench |
| QVT / TGG | model/model consistency and synchronization theory | declared consistency rules for overlay mappings and generated-code experiments |
| Joern / CodeQL | code-derived facts and static analysis | non-code intent, evidence, authority, and history survive reconstruction |
| SCIP / Kythe / Glean / LSIF / SemanticDB | symbol/reference indexes and generated-code mapping concepts | code facts and anchors support mapping without copying code text |
| Graphify / RepoGraph | AI context and repository graph retrieval | AI proposals remain non-authoritative and verifier/authority decides acceptance |
| PROV / OpenLineage / SLSA / in-toto | provenance/evidence vocabulary and production-chain metadata | evidence is bound to graph nodes, deltas, code references, mappings, and verifier claims |
| Git / CODEOWNERS / OPA | history, ownership, review, and policy mechanisms | graph semantic deltas and authority decisions are preserved through round-trip |
| Cytoscape.js / Graphviz / Sirius | graph visualization and workbench patterns | no visualization claim until core round-trip behavior exists |

## Pass Criteria For First Round-Trip Slice

The first implementation slice passes only if:

```text
Retrofit(Native(G)) = G
```

for the declared tiny graph and preservation metadata.

The verifier must check:

- graph node IDs are stable
- generated source maps back to graph nodes
- generated metadata maps back to graph nodes
- reconstructed graph matches the original under declared equality rules
- code-only reconstruction is reported as a lossy projection
- missing metadata produces a clear failure, not a silent partial pass
- evidence records are preserved
- authority records are preserved
- semantic change history records are preserved

## Fail Criteria

The benchmark fails if any of these happen:

- generated code works but cannot be reconstructed into the graph
- reconstruction depends on AI judgment
- equality rules are implicit
- code-only reconstruction is claimed to recover full intent
- evidence, authority, or history are stored as opaque blobs with no verifier coverage
- a custom broad code extractor is built before comparing stronger tools
- the result is only a code graph viewer, DSL compiler, or prompt-context graph

## Measurements

For each benchmark loop, record:

- generated files and hashes
- metadata files and hashes
- verifier command and result
- original graph node count by node type
- reconstructed graph node count by node type
- equality projection used
- code-only projection loss list
- evidence records preserved
- authority records preserved
- history records preserved
- prior-art comparator notes

## M1 Entry Criteria From This Plan

M1 may start when M0 review passes and the following are stable:

- first benchmark is `B0-python-cli-calculator`
- first implementation language is Python unless M1 review changes it
- no broad language workbench is planned
- no broad code extractor is planned
- metadata is required for full reconstruction
- code-only reconstruction is lossy by design
- AI is proposal-only

## Later Benchmark Candidates

These remain future candidates and are not authorized before the tiny benchmark proves the core loop:

1. Todo web app
2. Small REST API
3. Small desktop utility

Each later benchmark must rerun the prior-art gate before implementation.
