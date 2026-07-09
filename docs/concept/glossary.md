# Glossary

## Intent Graph

A development-semantic overlay graph linked to source code artifacts. It represents product intent, behavior, verification, code references, extracted code facts, mappings, evidence, authority, decisions, and semantic change history.

## IntentGraph Development

A semantic-overlay software development method where ordinary source code remains the implementation source and IntentGraph records the intent/code/evidence/authority/history relationships that must stay consistent.

## IntentGraph Overlay Schema

The future formal schema used to write, validate, and exchange overlay graph state.

## Intent Unit

A stable semantic work unit. It is not merely a requirement node. An Intent Unit groups a contract, internal graph facts, code references, code fact references, mapping obligations, verification, evidence, authority, and semantic history.

An Intent Unit does not contain code text. It links to implementation through `codeRef`, `codeFactRef`, and mapping obligation records.

Raw utterances, notes, hypotheses, and unconfirmed ideas may exist in the graph, but they are not accepted Intent Units until they become development commitments with verification and authority boundaries.

## GraphIR

The canonical internal representation used by overlay validators, mapping passes, generated-code mode tools, proposal validators, and analysis passes.

## Code Node

A stable pointer, reference, or fact for a source artifact, symbol, range, anchor, generated artifact, or extracted code fact.

```text
code node != code text
```

## Extract

The operation that derives code facts from source code artifacts.

```text
Extract(C) -> X
```

## Map

The operation that relates intent/behavior/verification graph facts to extracted code facts and source artifacts.

```text
Map(I, X) -> M
```

## Plan

The operation that proposes coordinated code, intent, and mapping deltas.

```text
Plan(I, C, X, M, request) -> DeltaC, DeltaI, DeltaM
```

## Graph-First Generation Mode

A limited mode for greenfield or generated-code regions.

```text
G -> Native(G) -> (C, mu) -> Retrofit(C, mu) -> G'
```

This is not the universal IntentGraph model.

## Code-First Maintenance Mode

The default frame for existing projects.

```text
C -> X -> M/I -> C'
```

Expected preservation is behavior, contract, mapping, evidence, and authority consistency, not source text equality.

## Preservation Metadata

Generated metadata embedded in or shipped beside generated source code so that non-code graph information can be reconstructed in graph-first generation mode.

## Evidence

Validation artifacts that support whether a graph change, code change, mapping change, or generated-code change is acceptable.

## Authority

The explicit boundary for who or what may approve, apply, or trust a change. AI proposals are not authority by default.

## Graph Delta

A proposed or accepted change to an intent graph.

## Mapping Obligation

A declared expectation that a contract, behavior, verification claim, or evidence record is linked to specific code references or code facts.
