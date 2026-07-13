# P9.28.R2 Effective Precision Zoom and Spectral Alloy

P9.28.R2 is a rendering-only correction for the unified IntentGraph Workbench. It does not change graph records, node or edge identities, source facts, work history, proposals, evidence, or authority.

## Effective 100x Inspection

Cytoscape remains bounded at a stable renderer zoom of `24x`. Above the precision threshold, the Workbench expands preset graph coordinates around the active selection so the visible spatial magnification reaches the requested logical zoom:

```text
effective geometry zoom = renderer zoom * virtual geometry scale
100 = 24 * 4.1667
```

Nodes, labels, borders, and state accents remain screen-space bounded. At effective `100x`, a selected relation is limited to `0.10px` and a neighboring relation to `0.055px`.

## Spectral Alloy Material

A pointer-transparent canvas layer paints cached, viewport-local node sprites above the Cytoscape hit targets. The material uses a near-black mineral core, restrained spectral category rim, metallic highlight, inner reflection, and small state accents. Sprite variants are cached and only visible nodes are painted, avoiding per-frame gradient construction across the full graph.

## Boundary

- graph structure and layout source coordinates are unchanged
- source code and snapshot workspaces are unchanged
- work history, graph delta, code diff, evidence, and authority records are unchanged
- no proposal is applied and no verification command is executed by this rendering slice
- this does not claim Graphify parity or product completion
