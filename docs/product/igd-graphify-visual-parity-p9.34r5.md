# P9.34.R5 Graphify Visual Parity and Deep-Zoom Continuity

## Purpose

P9.34.R5 replaces the rejected custom node-material renderer with the concrete
presentation rules used by the local Graphify reference. This is a presentation-only
correction. Graph facts, relation semantics, source state, work history, graph deltas,
code diffs, evidence, and authority do not change. Deterministic presentation
coordinates are intentionally respaced to reduce rectangular clustering.

## Rendering Contract

- all visible nodes use simple circular dots;
- code communities use Graphify's ten-color categorical palette;
- node diameter is degree-weighted;
- only the project and graph hubs receive labels by default;
- supporting labels appear on selection or focused inspection;
- extracted relations are solid and stronger, while inferred or ambiguous relations
  are thinner and dashed;
- unsupported or missing confidence values fail closed to the conservative unknown
  relation style;
- selected relations become a solid two-pixel line at `0.90` opacity;
- relation arrows are disabled because Cytoscape arrow geometry expands incorrectly
  at `512x` and the Graphify reference does not rely on large visible arrows;
- the graph uses one Cytoscape coordinate space. The former node-material canvas is
  not created.

## Deep-Zoom Contract

The actual camera, logical zoom, and effective geometry zoom all reach `512x`.
Screen-space compensation uses a settled `6.6..22` pixel target so the bounded style
refresh tolerance still keeps visible node diameter inside `6..24.1` pixels throughout
precision interaction. The `511x` and `512x` observations must differ by no more than
one screen pixel. A selected relation is sampled across its complete visible segment at
intervals no larger than one pixel. Coverage must be at least `0.99` and no missing run
may exceed one sample. The same browser probe temporarily hides that line and must then
observe no more than `0.10` coverage before restoring the presentation style.
Sample, observed, coverage, and longest-missing-run summaries must remain
arithmetically consistent in both observations.

## Performance Boundary

Viewport interaction keeps edges visible and moves nodes and relations in the same
renderer. The hidden material draw pass is absent from normal zoom and pan. In-page
durations collected under Chromium virtual time are diagnostics, not latency claims.
The complete headless browser capture is instead bounded by a measured `45s` wall-clock
limit, while live interaction quality remains a required human-review item.

## Non-Goals

This slice does not copy Graphify's graph schema, extraction engine, query model, or
semantic authority. It borrows presentation mechanics only. It does not mutate the
WindowsUtility repository or claim that visual taste can be fully machine-approved.
