# P9.34.R2 Stellar Vitreous Deep-Inspection Renderer

P9.34.R2 is a renderer-only correction driven by live user review. It does not change
the IntentGraph projection, graph topology, code facts, source snapshots, work history,
evidence, or authority records.

## Deep Zoom

- The real Cytoscape camera still reaches `256x`, exceeding the requested `100x` floor.
- Direct `100x` and `256x` controls center the selected node or selected relation source.
- Without a selection, direct deep zoom chooses the visible node nearest the viewport
  center instead of magnifying an empty graph coordinate.
- If a selected element is hidden by a lens or filter, deep zoom rejects that hidden
  anchor and falls back to the nearest visible node.
- Wheel zoom and pan remain available at every supported zoom level.

## Selection Scale

Selected relation emphasis is screen-space compensated. At `256x` it renders at
`0.18px` and `0.34` opacity. Non-selected connected relations are quieter. The
inspector, rather than an oversized line, remains the authoritative detail surface.

## Stellar Vitreous Material

`cached-stellar-vitreous-v5` replaces the circular ceramic highlight. Cached sprites
use kind-aware faceted silhouettes, an obsidian core, a broad prismatic rim, asymmetric
cyan/magenta refraction, a bounded star-grain field, and a restrained selected frame.
The optical strokes are deliberately broad in source space so the finish remains legible
at a bounded 18-32 screen-pixel footprint.

The renderer retains the 96-sprite cache cap, viewport spatial index, far-zoom ordinary
code-fact culling, and pointer-transparent material canvas.

## Evidence

- 27 real-browser runtime checks pass on the 8,194-node WindowsUtility projection.
- 28 fail-closed browser observation mutations pass, including independent anchor-
  distance and material-cache boundary checks.
- 30 loopback server and projection checks pass.
- The browser run reaches actual camera `256x`, keeps virtual geometry scale `1`,
  measures the selected relation at `0.18px`/`0.34`, and observes nonblank detailed
  material pixels with no runtime errors.

The headless browser's virtual-time interaction values are diagnostic only. Performance
is fail-closed through bounded viewport work, the sprite-cache ceiling, and the external
45-second whole-capture wall-clock gate.
