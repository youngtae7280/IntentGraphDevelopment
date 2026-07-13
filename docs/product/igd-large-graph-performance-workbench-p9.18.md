# P9.18 Large-Graph Navigation and Performance Workbench

P9.18 hardens the interactive WindowsUtility Workbench after a direct usability finding: a complete graph is only useful when it remains responsive and its source communities read as an understandable topology rather than a rectangular wall of syntax dots.

## Rendering Model

The Workbench still loads one complete projected graph. No code facts or relations are removed from the default Full graph lens.

- modules are ordered by observed code-fact volume, then placed by a deterministic golden-angle community layout;
- files use local source-community spirals and symbols use smaller local spirals around their file anchor;
- project semantics remain near the project core;
- layout is preset and deterministic. The browser does not run a force or physics layout;
- code labels and raw syntax relations remain progressive zoom detail rather than a first-frame burden; at overview zoom, raw code-relation edges are not painted, while semantic, capsule, mapping, and delta relations remain visible.

The result is a stable module constellation: large source areas receive visible, separated communities while smaller modules remain discoverable around them. It is not a claim that syntax-only extraction proves semantic architecture.

## Interaction Budget

The page owns one Cytoscape graph instance for the loaded projection.

- changing a graph lens or category/relation filter updates only records whose visibility actually changed;
- the complete node/edge identity sets and the semantic-edge set are precomputed once, so Full and Semantic lens changes do not rebuild 8,188-element visibility sets;
- the Semantic overview keeps the complete graph loaded and highlights the semantic foundation, work, Intent, mapping, proposal, verification, evidence, authority, history, and code-capsule records instead of destroying and rebuilding a smaller graph;
- text search highlights matching code or semantic nodes in place. It does not hide thousands of unrelated records while a user types;
- selection highlights only the selected record and its direct relations. It no longer dims and restyles every node and edge;
- ordinary lens and filter changes preserve the current viewport instead of automatically framing the entire graph; `Fit` remains an explicit command;
- panel resizing is frame-limited and preserves the current viewport. A user may explicitly use `Fit` when a new framing is desired;
- automated fitting uses the deterministic stored positions rather than asking the graph runtime to scan every visible element.

This is deliberately a local single-user performance contract, not a universal graph-rendering benchmark. The product must remeasure it for each supported project-size band and browser/runtime combination.

## Review Flow

1. Start the loopback Workbench for a local project workspace.
2. Inspect the Full graph and pan/zoom among source communities.
3. Use Semantic overview to emphasize the project overlay without losing code topology.
4. Search to locate and highlight a code fact, then select it for source provenance and any proposal code diff.
5. Use category, relation, work, delta, and focus lenses when a narrower inspection is necessary.

The page can record a local work request and a declared mapping candidate. It still cannot modify the target repository, accept a mapping or proposal, apply a code change, create evidence by execution, or grant authority.

## Boundary

- no target repository mutation, build, restore, launch, package action, provider call, credential access, or network service;
- no automatic Intent creation, semantic inference, mapping acceptance, proposal acceptance, code application, or approval automation;
- source code remains external implementation material represented by extracted facts and provenance, not copied graph authority;
- static export remains a portable review snapshot. The loopback page is the intended large-project interactive surface because it defers the projection payload until its shell is ready.
