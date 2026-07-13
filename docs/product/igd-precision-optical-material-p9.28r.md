# P9.28.R Precision Optical Material Correction

P9.28.R corrects the maximum-zoom relation emphasis and node material of the
unified IntentGraph Workbench. It changes only the renderer contract. Graph nodes,
relations, layouts, mappings, work history, proposals, source facts, and authority
records remain unchanged.

## Renderer-Safe 100x Lens

The user-facing lens reaches a logical maximum of `100x`. Cytoscape renders the
precision range with a bounded internal maximum of `24x`:

```text
logical 0.10x .. 18x  -> renderer 0.10x .. 18x
logical 18x .. 100x  -> renderer 18x .. 24x
```

This mapping is required because Cytoscape expands each node bounding box by one
model unit on every side. A literal renderer zoom of 100 would turn that fixed
margin into roughly 200 screen pixels per node and destabilize an 8,000-node canvas.
The virtual precision band preserves the requested inspection depth while keeping
renderer bounds and redraw work bounded.

At logical `100x`:

- the selected relation is `0.24` rendered pixels;
- neighboring highlighted relations are `0.14` rendered pixels;
- structural endpoints remain approximately 15 to 19 rendered pixels;
- labels, borders, outlines, and offsets are screen compensated; and
- the precision renderer uses ellipse paths to avoid the tiny round-hexagon path
  defect that previously produced a full-canvas colored field.

## Optical Material

Semantic, capsule, file, namespace, and type landmarks use a renderer-safe optical
material composed of an almost-black obsidian core, a category-colored spectral
rim, a faint secondary outline, and a restrained underlay at normal zoom. It uses
no bitmap texture and no native gradient, both of which produced unstable canvas
behavior in the target Cytoscape renderer.

Ordinary code facts retain small community-colored points. This keeps source
topology legible and inexpensive while preventing the important semantic landmarks
from reading as pastel or plastic blocks. Precision zoom removes broad underlays and
keeps only the compact optical boundary.

## Preserved Boundary

- graph structure changed: false
- graph delta applied: false
- source or snapshot mutation: false
- target repository mutation: false
- automatic mapping or code application: false
- verification or evidence execution: false
- network, provider, credential, release, or productization action: false

This correction improves rendering only. It does not claim Graphify parity or
IntentGraphDevelopment product completion. Typed verifier-result intake remains the
next normal-workflow capability gap.
