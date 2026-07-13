# P9.26 Dense Graph Visual Navigation

P9.26 improves the project Workbench rendering layer for dense real-project graphs
without changing the unified graph's nodes, edges, identifiers, provenance, or
authority records.

## Graph Rendering Contract

- the full graph remains the default view and loads every projected node and edge
- deterministic relation-aware positions are computed once and reused during pan,
  zoom, search, selection, work navigation, and stage navigation
- full-graph fit uses a compact module radius and reduced outer padding so the graph
  occupies the available canvas without overlapping communities
- zoom supports eleven progressive visual bands from `far` through `atomic`, with a
  maximum zoom of `240` and a visible zoom readout
- semantic nodes remain legible in the overview while code nodes grow progressively
  in `close`, `deep`, and `inspect` bands
- node body, border, label, glow padding, and relation width are compensated only
  when a zoom-band boundary is crossed
- semantic and capsule nodes use a low-opacity spectral-obsidian core, thin luminous
  category rim, restrained outer emission, and geometric silhouettes without the
  former glossy texture; this keeps them technical rather than toy-like
- ordinary code facts stay texture-free for scale; file landmarks alone reuse the
  shared texture, while code kind is communicated with stable geometry
- edge and selection-emphasis widths use screen-pixel compensation, so a selected
  edge remains at `0.95` rendered pixels while zooming and the previous relation is
  restored to its ordinary width when selection changes
- zoom buttons stay anchored to the selected graph element or project node, avoiding
  an empty viewport during deep inspection
- labels remain on demand for ordinary code facts so deep zoom does not turn into a
  wall of text
- zoom-band restyling waits for a 350 ms interaction-settle boundary, so rapid wheel
  or button zoom does not repeatedly restyle the complete 8,000-node collection

These are projection rules only. P9.26 does not add, remove, merge, or rewrite graph
records.

## Code Fact Type Hierarchy

`code` and `method` are not peer node categories. A method is represented by one
node with `category: code` and `kind: method`. The same rule applies to file,
namespace, type, field, property, constructor, and other extracted code-fact kinds.

`code-capsule` is a separate visual grouping record for a source community. It does
not duplicate the method or own its source text.

## Work History Scale

The same Workbench now provides work-id/title/request search, status filtering, and
a bounded render window. Every recorded work item remains navigable, but no more than
60 work cards are inserted into the DOM at once. Previous/next navigation follows the
active filtered sequence.

## Safety Boundary

P9.26 does not mutate the target repository, source snapshot, graph records, mapping
records, proposal records, review receipts, evidence, authority, or history. It does
not run a build, test, restore, launch, provider call, or automatic approval.
