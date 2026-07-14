# Start Here

This repository began with a thesis and prior-art gate before broad implementation.

IntentGraph Development is a proposed software development method, semantic overlay graph, mapping boundary, consistency engine, and verification discipline over existing source code. Before broad implementation exists, the project needs a stable thesis, prior-art review, benchmark criteria, and milestone gates.

## Current Delivery Focus

The current product plan is [IGD Product Goal And Delivery Gates](roadmap/igd-product-delivery-gates.md).
P9.35 completed reviewed source refresh and revision preservation for the installable
local preview. G1/P9.36 completed the plan-only source-application contract. The next
gate is an isolated G2 single-file application proof; it does not authorize a real
target write. Do not treat prior non-applied proposal, renderer, or target-adoption
evidence as proof that the daily proposal-application loop is complete.

Use the accompanying [test and verification plan](testing/igd-product-delivery-gates-test-plan.md)
for gate-specific evidence requirements. Workbench visual acceptance is deferred until
direct user review, even when renderer or screenshot checks pass.

## Work Order

Follow this order:

1. Read the core thesis.
2. Read the [IntentGraph Formal Blueprint](design/intentgraph-formal-blueprint.md) for the current formal center of gravity.
3. Read the [IGD Product Goal And Delivery Gates](roadmap/igd-product-delivery-gates.md), then the [Product Capability Roadmap](roadmap/product-capability-roadmap.md) for historical phase gates.
4. Read the current milestone in [Milestones](roadmap/milestones.md).
5. Run the prior-art gate for the capability being considered.
6. Update the capability matrix.
7. Write a build/borrow/integrate decision.
8. Define a benchmark before implementation.
9. Start only the smallest vertical slice that can prove or disprove the thesis.
10. Review the slice against the milestone gate before continuing.

For a worker or new chat, follow the [Autonomous Work Loop](process/autonomous-work-loop.md).

## First Principle

Code remains the implementation source. IntentGraph is the development-semantic overlay that links intent, code facts, mapping obligations, evidence, authority, and semantic history.

## Primary Thesis

IntentGraph is a development-semantic overlay graph linked to source code artifacts. It does not replace source code or copy code text into the graph. Code nodes are stable references or facts for source artifacts, symbols, ranges, anchors, and extracted code facts.

## Formal Blueprint

The current formal center of gravity is [IntentGraph Formal Blueprint](design/intentgraph-formal-blueprint.md). It is being revised toward the overlay state model and must change when prior-art review, milestone review, or benchmark evidence contradicts it.

After Phase 0, the next structure center of gravity is the [Intent Unit Model](design/intent-unit-model.md). Do not expand to a larger benchmark until Intent Units are reconsidered as semantic overlay mapping units rather than graph-as-source capsules.

## Default Bias

Do not build what a stronger existing system already does well.

Prefer:

- integrate a strong existing engine
- learn from a mature design
- define the missing boundary between existing tools
- build only the part that is unique to IntentGraph

## Implementation Entry Criteria

Implementation may start only when these are written:

- core thesis for the slice
- prior-art notes
- capability comparison
- build/borrow/integrate decision
- benchmark target
- acceptance criteria
- late prior-art response plan

Phase 0 is complete as of 2026-07-09. Read the [Phase 0 Final Review](reviews/phase-0-final-review.md) before proposing any new work.

P1.R through P1.18 corrected the model and proved it on the tiny CF0 code-first fixture. CF0 is now saturated proof evidence, not general scalability evidence.

P1.19 selected `B1-typescript-rest-api` as the next benchmark shape. P2.0 created the first bounded B1 fixture, code fact schema, extractor, validator, and negative probes. P2.1 proved a one-file incremental code fact change. P2.2 opened Phase C only for a bounded static B1 mapping slice. P3.0 created the B1 Intent Unit mapping overlay and verifier. P3.1 proved stale mapping failure. P3.2 proved ambiguous mapping candidates remain unresolved. P3.3 reviewed the Phase C boundary. P4.0 created the first non-applied B1 change proposal schema, proposal artifact, validator, and negative probes. P4.1 reviewed the Phase D boundary. P5.0 added deterministic B1 proposal consistency verification. P5.1 opened Phase F. P6.0 added a deterministic B1 workbench projection and static HTML preview. P6.1 opened Phase G. P7.0 selected WindowsUtility as the first real-project target, read-only first. P7.1 emitted a read-only WindowsUtility inventory. P7.2 emitted read-only WindowsUtility mapping hypotheses. P7.3 found productization not ready. P8.0 converted that into a productization readiness gap report and stabilization plan. P8.1 recorded that WindowsUtility target state was unresolved. P8.2 defined the accepted mapping boundary. P8.3 selected shell-workspace as the first candidate. P8.4 created a shell-workspace mapping draft outside WindowsUtility without accepting it. P8.5 added repeatable mapping draft negative probes. P8.6 resolved WindowsUtility target state to clean/aligned. P8.7 says the mapping is ready to request human acceptance. P8.8 created the human acceptance request. P8.9 recorded the user's `accept` response and created the first accepted mapping. P8.10 added accepted mapping negative probes. P8.11 opened the non-applied proposal boundary. P8.12 created the first shell/workspace smoke evidence proposal. P8.13 added non-applied proposal negative probes. P8.14 required future smoke evidence to use a no-target-write sandbox strategy. P8.15 proved sandboxed build smoke evidence while the original target stayed unchanged. P8.16 opened only a sandboxed UI launch feasibility boundary. P8.17 proved sandboxed UI launch/window observation while the original target stayed unchanged. P8.18 opened only a sandboxed screenshot evidence boundary. P8.19 captured validated sandboxed screenshot evidence while the original target stayed unchanged. P8.20 defined the shell/workspace evidence workbench projection boundary. P8.21 emitted the first WindowsUtility shell/workspace evidence workbench projection and static HTML preview. P8.22 added repeatable projection negative probes. P8.23 defined the workbench usability dry-run boundary. P8.24 completed the self-conducted workbench-vs-raw-JSON dry run. P8.25 defined the user workflow benchmark boundary. P8.26 created the user workflow benchmark request. P8.27 recorded the user's compact `accept` response as proceed. P8.28 rechecked productization readiness and kept productization blocked pending product-surface and application gates. P8.29 selected static local workbench export as the first product surface boundary. P8.30 defined the static local export boundary. P8.31 emitted and validated the first static local WindowsUtility workbench export prototype. P8.32 reviewed the prototype as ready for user review but not productized. P8.33 created the static export user review request. P8.34 recorded the user's `revise` response because the export did not explain what it was or what to inspect. P8.35 emitted a revised export with reviewer orientation. P8.36 created the orientation review request. P8.37 recorded the user's `proceed` response. P8.38 rechecked productization and kept it blocked pending source application, packaging, and release gates. P8.39 planned the source application authority boundary. P8.40 recorded the non-mutating source application dry-run boundary. P8.41 emitted and validated the first non-mutating WindowsUtility source-application dry-run prototype while observing but not exercising the user's source-modification permission. P8.42 reviewed the permission and concluded that a minimal source edit proposal and patch preview are required before source application. P8.43 selected one low-risk test-automation source edit and emitted a patch preview without applying it. P8.44 applied and validated that WindowsUtility source edit. P8.45 reviewed the result and kept productization blocked pending source-application workbench refresh and packaging/release gates. P8.46 refreshed the static workbench so the source application and productization gate evidence are visible. P8.47 planned the packaging/release boundary. P8.48 recorded the non-mutating packaging/release dry-run boundary. P8.49 emitted and validated the non-mutating packaging/release dry-run prototype. P8.50 reviewed the dry-run result. P8.51 refreshed the workbench with packaging/release dry-run evidence. P8.52 rechecked productization readiness. P8.53 requested package artifact creation authorization. P8.54 recorded the user's `accept sandboxed package artifact creation` response. P8.55 created and validated a bounded sandboxed WindowsUtility package artifact. P8.56 recorded the packaged artifact verification boundary. P8.57 recorded that approval-stage workbenches must show Graphify-grade graph/delta inspectability, selected node/edge details, code diffs for code nodes, and graph diffs for changed existing nodes/edges. P8.58 turned that into a bounded graph-delta approval workbench plan. P8.59 emitted and validated the deterministic graph/delta/diff projection schema. P8.60 emitted and validated a static local Cytoscape graph workbench with node/edge selection, delta highlighting, pan/zoom controls, code diffs, and changed node/edge before/after graph diffs. P8.61 attempted browser visual/interaction verification but automated interaction was blocked by policy, so user-observed or otherwise allowed review is required before proceeding; the next step is controlled by the [Product Capability Roadmap](roadmap/product-capability-roadmap.md).

Do not open compiler, extractor, verifier, package setup, UI, or AI runtime implementation until the relevant later milestone is current and its entry criteria are met.

## Stop Criteria

Stop and reassess if:

- a stronger existing system is found
- the slice duplicates an existing tool without a decision record
- the benchmark cannot distinguish IntentGraph from a code graph viewer, DSL tool, or model generator
- AI output is being treated as authority rather than proposal
- the overlay cannot preserve behavior contracts, evidence, authority, semantic history, or mapping consistency
- graph-first generation is treated as the universal model instead of a limited generated-code mode
