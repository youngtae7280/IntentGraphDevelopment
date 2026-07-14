# P9.34.R4 Luminous Alloy Visibility and Edge Continuity

## Purpose

Correct two renderer defects reported during WindowsUtility review: nodes that merge
into the dark background and selected relations that appear fragmented at deep zoom.
This is a presentation-only slice. It does not change graph facts, relations, layout
coordinates, source state, workflow records, evidence, authority, history, graph
deltas, or code diffs.

## Visibility Contract

- ordinary code facts retain a restrained community color signal in the full graph;
- overview code facts use at least `3.8px` material size, `0.96` material opacity, and
  `0.30` renderer-body opacity;
- ordinary low-detail code facts retain at least `0.82` element opacity;
- code relations retain `0.30` base opacity before low-detail compensation;
- semantic nodes preserve their distinct category colors and faceted silhouettes;
- the active material is `cached-luminous-nebula-alloy-v9`;
- the material uses a dark alloy core, brighter asymmetric planes, a narrow spectral
  signal, and a thin diffraction rim rather than a broad glossy highlight;
- material rendering remains viewport-local and the sprite cache remains bounded to
  96 entries.

## Deep-Zoom Continuity Contract

- actual camera, logical, and effective geometry zoom reach `512x`;
- selected relations retain a continuous `0.65px` screen-space line at `0.30`
  opacity at maximum zoom;
- selected relations use a solid inspection line even when their ordinary relation
  style is dashed, and the browser gate exercises an `invokes-syntax` relation;
- precision node attachment geometry is scaled to `0.46` so relation endpoints meet
  the visible material body rather than an invisible sprite boundary;
- selected relation endpoint material remains within `22x22px`;
- at least one on-screen selected endpoint must be sampled and its rendered/body
  diameter difference must not exceed `1.5px`, accounting for renderer pixel
  quantization; direct canvas-pixel continuity remains the primary gate;
- a 13-point canvas corridor outside the selected endpoint must contain at most one
  missing edge sample and no missing run longer than one sample;
- no virtual geometry, graph, layout, or semantic mutation is permitted.

## Verification

The WindowsUtility projection must pass real Chromium observation, deterministic
Workbench validation, fail-closed observation mutation probes, and loopback server
smoke tests. The browser gate measures overview opaque/chromatic pixels and mean
luminance, maximum-zoom relation width and opacity, endpoint material detail and
bounds, attachment continuity, zoom/pan recovery, selection details, and runtime
errors.
