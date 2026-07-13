# P9.34.R Deep Inspection Rendering

P9.34.R refines only the local Workbench renderer. It does not change graph facts,
relations, revisions, evidence, authority, history, or source snapshots.

## Camera Boundary

- The `100x` inspection shortcut remains available.
- The real Cytoscape camera and effective geometry ceiling are `256x`.
- The maximum button zooms around the current selection, or around the viewport center
  when nothing is selected.
- Node and ordinary relation sizes remain screen-bounded while graph geometry continues
  to separate at deep zoom.

## Selected Relation Boundary

Selected relation emphasis tapers with zoom. At `256x` the selected relation is rendered
at `0.30px` and `0.42` opacity. Connected, non-selected relations are quieter still.
Selection overlays and underlays remain disabled so clicking a relation cannot create a
large screen-space halo.

## Celestial Ceramic Material

The cached node material uses a near-black ceramic core, an asymmetric cool specular
response, a restrained cyan/category rim, a secondary magenta spectral arc, deterministic
micro-etching, and sparse mineral-like highlights. The material is cached by shape,
category color, selection state, and accent state.

The renderer keeps the existing performance boundary:

- at most 96 material sprites are cached;
- only viewport-local candidates are considered at deep zoom;
- ordinary code material is culled from the far overview without removing graph nodes;
- the material canvas remains pointer-transparent;
- graph interaction does not rebuild or mutate the graph.

## Verification

The browser probe requires real renderer and effective geometry zoom `256`, virtual
geometry scale `1`, selected relation width `0.30px`, selected relation opacity `0.42`,
nonblank graph and material canvases, bounded viewport candidates, a populated selection
inspector, and detailed selected-endpoint material pixels. The external runner separately
enforces a 45-second whole-capture wall-clock ceiling and caps deep-zoom material
candidates at the larger of 256 nodes or 10 percent of the graph.
