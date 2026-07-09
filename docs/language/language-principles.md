# IntentGraph Language Principles

M1 defined the smallest overlay schema and canonical GraphIR boundary needed for the first benchmark. It does not define a general language workbench, custom editor, parser generator, compiler, reconstructor, verifier, UI, or AI runtime.

The formal center of gravity for this milestone is `docs/design/intentgraph-formal-blueprint.md`.

## M1 Language Choice

For Phase 0, the IntentGraph exchange format is canonical JSON that directly serializes GraphIR.

This is intentionally conservative:

- JSON avoids building a parser before the thesis needs one.
- JSON can be validated with ordinary tooling.
- JSON keeps graph identity explicit through stable IDs.
- JSON makes generated preservation metadata easy to compare.
- JSON keeps M1 focused on semantic meaning rather than authoring ergonomics.

Future milestones may add an authoring syntax or workbench, but only after overlay mapping and generated-code experiment boundaries are clear.

## Overlay And GraphIR Relationship

In M1, the hand-authored overlay document and GraphIR use the same semantic shape.

```text
IntentGraph JSON = canonical GraphIR serialization
```

Later versions may distinguish authoring syntax from canonical GraphIR. Until then, no behavior may depend on hidden parser defaults, tool memory, chat history, or file layout outside the graph document.

## Core Principles

1. Every meaningful item has a stable ID.
2. Nodes represent semantic things or code references/facts; edges represent semantic, mapping, or code-fact relationships.
3. Code nodes are pointers or facts, not code text.
4. Generated source mapping metadata is part of the generated-code boundary, not an optional debug artifact.
5. Evidence is represented as graph data linked to the claim it supports.
6. Authority is represented as graph data linked to the change or acceptance decision it governs.
7. Change history is semantic graph history linked to Git, not a replacement for Git.
8. AI may be recorded as proposer, but not as final authority.
9. Code-only reconstruction is a declared lossy projection.
10. Validation failures must be explicit and deterministic.

## Minimum Expressive Surface

The M1 language must describe:

- product intent for the benchmark
- domain concepts used by that intent
- code reference/projection nodes for generated Python source
- generated source mapping metadata
- tests or verification expectations
- evidence records
- authority records
- semantic change history
- equality/projection expectations for later verification

Anything outside that surface is deferred.

## Non-Goals

M1 does not provide:

- user-friendly syntax
- graphical editing
- schema evolution machinery
- package layout
- compiler implementation
- source reconstruction implementation
- verifier implementation
- policy engine implementation
- AI proposal runtime

## Canonical Document Expectations

An M1 graph document must:

- use UTF-8 JSON
- use explicit top-level version fields
- sort node and edge arrays by `id` when practical
- avoid absolute filesystem paths
- use stable IDs rather than generated array positions
- make all non-code meaning explicit in graph nodes, edges, mapping obligations, or generated-code metadata
- preserve enough metadata for a later reconstructor to fail loudly when data is missing
- declare round-trip and projection expectations explicitly

## First Fixture

The first M1 fixture is:

```text
docs/examples/b0-python-cli-calculator.graph.json
```

That fixture is the hand-authored graph used by the Phase 0 generated-code experiment.
