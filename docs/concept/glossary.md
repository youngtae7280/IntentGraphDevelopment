# Glossary

## Intent Graph

The primary source artifact in IntentGraph Development. It represents product intent, structure, code relationships, evidence, authority, decisions, and change history.

## IntentGraph Development

A graph-native software development method where intent graphs are treated as source, compiled to code, reconstructed from code, and verified through round-trip consistency.

## IntentGraph Language

The future formal language or schema used to write and validate intent graphs.

## GraphIR

The canonical internal representation used by compilers, reconstructors, validators, and analysis passes.

## Native

The graph-to-code direction.

```text
Native(G) = source code + metadata
```

## Retrofit

The code-to-graph direction.

```text
Retrofit(source code + metadata) = intent graph
```

## Round-Trip Consistency

The property that compiling a graph to code and reconstructing it returns the same graph or a declared projection of it.

## Preservation Metadata

Generated metadata embedded in or shipped beside source code so that non-code graph information can be reconstructed.

## Evidence

Validation artifacts that support whether a graph change or generated code change is acceptable.

## Authority

The explicit boundary for who or what may approve, apply, or trust a change. AI proposals are not authority by default.

## Graph Delta

A proposed or accepted change to an intent graph.

## Code Projection

The portion of an intent graph that can be represented directly as source code.
