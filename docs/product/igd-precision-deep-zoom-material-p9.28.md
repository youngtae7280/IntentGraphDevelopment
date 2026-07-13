# P9.28 Precision Deep Zoom and Graph Material

P9.28 corrects the deep-zoom and material rendering boundary of the unified
IntentGraph Workbench. It does not change graph nodes, relations, mappings, work
history, proposals, source facts, or authority. The same graph projection is rendered
with a bounded 100x inspection lens.

## Interaction Contract

- the graph supports pan, wheel zoom, toolbar zoom, fit, and a direct `100x` command;
- 100x is the explicit maximum, avoiding unsupported renderer behavior beyond the
  product requirement;
- zoom is anchored to the selected node or selected relation source;
- selected relations remain 0.42 rendered pixels at every supported zoom level;
- neighboring relations remain 0.27 rendered pixels;
- code nodes remain approximately 15 to 21 rendered pixels in the precision lens;
- borders, text outlines, label offsets, and highlight widths are scale compensated;
- high-zoom underlays are disabled so labels and state classes cannot create oversized
  selection fields; and
- panning at precision zoom updates only the nearby graph subset after a short settle.

## Material Direction

The prior flat saturated surfaces are replaced with a shared low-cost obsidian
material texture. It uses a dark body, asymmetric cool specular response, restrained
cyan/magenta refraction, edge depth, and deterministic micrograin. Semantic and
structural landmarks receive the material while ordinary code facts keep a cheaper
dark fill and relation-colored rim.

The material is one shared bitmap generated in memory. It does not allocate a unique
texture or glow per node. The palette is deliberately desaturated so category color
acts as a rim and identity signal rather than a plastic body color.

## WindowsUtility Demonstration

The P9.28 static Workbench retains the P9.27 demonstration graph and workflow:

- 8,189 total graph nodes;
- 7,996 total relations;
- 678 nodes and 471 relations in the code-topology lens;
- four durable work items;
- two mappings; and
- three code diffs in the selected proposal workflow.

Browser QA selected a real extracted C# `contains` relation and jumped directly to
100x. The measured selected relation width was 0.420 pixels, both endpoint nodes were
15.2 pixels, their borders were 0.2 pixels, and the jump settled in approximately
1.5 seconds in the in-app browser automation path.

## Preserved Boundary

- no graph node or relation schema change;
- no graph delta application;
- no source or snapshot mutation;
- no build, restore, test, launch, or evidence execution;
- no automatic mapping, proposal approval, or code application; and
- no network, provider API, credential, installer, release, or productization action.

The next highest-value product gap remains typed verifier-result intake for binding
deterministic build, test, or runtime results to proposal requirements.
