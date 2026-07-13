# P9.34.R3 Nebula Black-Metal Renderer

## Purpose

Correct the remaining deep-zoom and toy-like material defects in the existing
IntentGraph Workbench renderer. This slice changes presentation only. It does not
change graph facts, relations, deterministic layout coordinates, source state,
workflow records, evidence, authority, history, graph deltas, or code diffs.

## Interaction Contract

- camera, logical, and effective geometry zoom reach `512x`;
- `100x`, `256x`, and `512x` selection-centered jumps remain directly available;
- at `512x`, a selected relation renders at `0.08px` and `0.12` opacity;
- relation endpoints use compact endpoint ticks instead of full selected-node halos;
- maximum-zoom endpoint material stays within a `22x22px` opaque screen-space bound;
- pan, zoom-out recovery, fit, and selection inspection remain available;
- deep precision views suppress the background grid so geometry remains legible.

## Material Contract

The active cached material is `cached-nebula-black-metal-v7`.

- near-black alloy core;
- asymmetric facet planes rather than radial plastic gloss;
- one thin diffraction rim and one restrained inner contour;
- a tighter visible-body crop so facet detail survives normal screen-scale rendering;
- sparse micro-grain and etched contour detail;
- stronger treatment only for explicitly selected nodes;
- compact endpoint treatment for selected relations;
- 96-entry sprite-cache bound and viewport-local candidate rendering.

The previous `cached-stellar-vitreous-v5` material remains a historical identity and
is not active.

## Verification

The WindowsUtility projection must pass:

- 30 loopback server/projection probes;
- 30 fail-closed browser observation mutations, including non-finite zoom and
  oversized-endpoint cases;
- the real headless browser runtime and PNG evidence gate;
- exact `100x` and `512x` camera observations;
- exact maximum selected-relation width/opacity observations;
- nonblank graph and material pixels;
- bounded sprite and viewport candidate counts;
- populated selected-relation inspection;
- zero runtime script errors.
