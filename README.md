# IntentGraph Development

IntentGraph Development is a semantic-overlay software development methodology for AI-assisted development.

The central idea:

> Code remains the implementation source. IntentGraph is the semantic overlay that keeps intent, code facts, evidence, authority, and change history aligned.

IntentGraph is a development-semantic overlay graph linked to source code artifacts. It does not replace source code. Code nodes are stable references or facts about files, symbols, ranges, anchors, and extracted code facts, not copies of code text.

## Current Status

**Current delivery plan:** [IGD Product Goal And Delivery Gates](docs/roadmap/igd-product-delivery-gates.md).

IGD is an installable local preview, not yet a daily-use completed product. P9.35
completed reviewed source refresh and immutable local revision preservation. The next
implementation prerequisite is G1/P9.36: define the authority, preimage, atomic
application, verification, and rollback contract for applying one reviewed proposal.
Workbench visual acceptance remains deferred and unresolved; renderer telemetry is not
a substitute for user approval. See the accompanying
[test and verification plan](docs/testing/igd-product-delivery-gates-test-plan.md).

Phase 0 is complete as of 2026-07-09. See the [Phase 0 Final Review](docs/reviews/phase-0-final-review.md).

No `M8` was opened automatically. P1.R through P1.18 reframed IntentGraph as a semantic overlay and proved the corrected model on a tiny CF0 code-first fixture. CF0 is now treated as saturated proof evidence, not proof of general scalability.

P1.19 selected `B1-typescript-rest-api` as the next benchmark shape. P2.0 created the first bounded B1 fixture, code fact schema, extractor, validator, and negative probes. P2.1 proved a one-file incremental code fact change. P2.2 opened Phase C only for a bounded static B1 mapping slice. P3.0 created the B1 Intent Unit mapping overlay and verifier. P3.1 proved stale mapping failure. P3.2 proved ambiguous mapping candidates remain unresolved. P3.3 reviewed the Phase C boundary. P4.0 created the first non-applied B1 change proposal schema, proposal artifact, validator, and negative probes. P4.1 reviewed the Phase D boundary. P5.0 added deterministic B1 proposal consistency verification. P5.1 opened Phase F. P6.0 added a deterministic B1 workbench projection and static HTML preview. P6.1 opened Phase G. P7.0 selected WindowsUtility as the first real-project adoption target, read-only first. P7.1 emitted a read-only WindowsUtility inventory. P7.2 emitted read-only WindowsUtility mapping hypotheses. P8 then proved bounded mapping, change, package, launch, and UI evidence against that target. P8.124 corrects an earlier scope error: WindowsUtility is adoption evidence, not the IntentGraphDevelopment product candidate. P9.0 defines the first IGD product build path as the local-first IntentGraph Local Review Kit. P9.1 adds its first local command/workspace workflow for the bounded B1 sample. P9.2 makes that B1 workspace portable across filesystem locations with a logical source identity. P9.3 defines a safe B1-equivalent external source intake boundary, and P9.4 proves it with a read-only snapshot import. P9.5/P9.6 prove a read-only C# syntax probe, P9.7/P9.8 expose its local SDK prerequisite, P9.9/P9.10 create a fact-only C# snapshot workspace route, and P9.11/P9.12 provide the separate C# fact-only HTML inspector. P9.13/P9.14 add project state, graph delta, and code-diff review. P9.15 adds a loopback-only interactive Workbench with a semantic-first default graph and local work-request intake. At that milestone IGD was neither installable nor released; P9.34 now provides an installable local preview. See the [Product Capability Roadmap](docs/roadmap/product-capability-roadmap.md).

P9.17 supersedes the P9.15 semantic-only default: the WindowsUtility Workbench now loads the complete graph with progressive detail, retains a declared project semantic foundation, and supports local work-to-code mapping candidates without source mutation.

P9.27 closes the JSON-only code-change gap in the normal Workbench path. A user can select mapped code facts, enter hunk-only unified diffs, and record a snapshot-checked, non-applied proposal whose graph delta and code diffs are immediately inspectable. The target repository remains unchanged. P9.29 later closes typed result intake; application authority, distribution, and broader product hardening remain open.

P9.28 hardens the same unified graph for visual inspection: a direct 100x precision lens keeps selected relations at 0.42 rendered pixels, bounds nodes and borders in screen space, refreshes only the nearby graph after pan, and replaces saturated plastic surfaces with a shared dark spectral-obsidian material. This is a rendering-only change; graph structure and source state are unchanged.

P9.28.R2 makes that precision lens spatially effective rather than display-only: renderer-safe `24x` geometry expands around the active anchor to an effective `100x`, selected relations taper to `0.10px`, and cached viewport-local spectral-alloy sprites replace the remaining flat plastic node bodies. Graph structure, source state, workflow history, graph delta, and code diff remain unchanged.

P9.29 adds guided typed external verifier-result intake. Build, test, runtime-smoke, and static-analysis observations can be bound to exact proposal verification/evidence pairs with client-side artifact hashing, attempt/supersession history, requirement coverage, and durable timeline visibility. IntentGraph records the observation but does not execute the verifier, upload artifact bytes, authenticate the producer, accept evidence, approve the proposal, or apply source or graph changes.

P9.30 adds local evidence acceptance and rejection for the current verifier result. A
declared human reviewer with the `maintainer`, `quality-reviewer`, or
`security-reviewer` role must hold the matching `evidence.accept` or
`evidence.reject` permission inside `local-project-workspace`. This local reviewer
identity is not cryptographically authenticated. Rejection blocks the work item,
partial acceptance remains `verification-observed`, and only all current required
pairs accepted with passing results move the work item to `verified`. The proposal
remains unapproved and unapplied, and source and snapshot state remain immutable.

The same slice refines only graph rendering: effective `100x` is composed from renderer
`24x` and virtual geometry `4.1667`; a selected edge tapers to `0.065px` at `0.34`
opacity; and cached viewport-local etched obsidian/titanium material replaces the
remaining plastic appearance. At distant overview scales, ordinary code facts retain
their Cytoscape nodes while the heavier material pass is reserved for structural,
selected, changed, and searched landmarks. Graph structure is unchanged.

P9.31 sharpens that rendering-only boundary. Cached node sprites now use a dark brushed
spectral-titanium surface with asymmetric cyan, magenta, and warm-metal rim segments,
micro-etching, and a thin selected-state Fresnel ring. The precision material core is
held near 20 screen pixels, so it remains legible without growing with `100x` geometry. The
`0.065px` selected-edge taper, graph contents, layout coordinates, workflow records,
source state, and authority remain unchanged.

P9.32 replaces the remaining manual-only rendering check with a repeatable real-browser
regression. A query-activated read-only page probe and a dependency-free headless
Edge/Chrome runner verify all 8,208 nodes and 8,023 relations, effective `100x`, the
`0.065px` selected relation, actual 4.1667 endpoint-distance expansion, cached material
pixels, populated edge inspection, and a nonblank 1440 by 1000 screenshot from the same
browser run. Eighteen fail-closed probes prove that stale counts, missing checks, blank canvases,
wrong zoom/material, unapplied geometry, oversized selection emphasis, script errors,
invalid screenshots, and input-output collisions are rejected. Input and browser
binary digests bind the evidence. The probe does not change graph or source state.

P9.33 corrects the remaining maximum-zoom and material defects reported through visual
review. The Cytoscape camera now reaches an actual `100x` with virtual geometry held at
`1`. Maximum-zoom relation selection stays thin but visible at `0.55px` and `0.68`
opacity and suppresses unrelated semantic and stage-delta emphasis while selected.
Cached `astral-forged-glass-v3` sprites use
faceted silhouettes, a near-black forged core, restrained ion color, asymmetric
specular detail, and thin dual rims instead of circular plastic tokens. Graph, workflow,
snapshot, source, evidence, and authority state remain unchanged. Viewport spatial
buckets avoid full-node scans during deep-zoom pan, the material cache is capped at 96
entries, and node-centered optical-complexity evidence replaces a nonblank-only check.

P9.34 closes the first installation and daily-launch gap. A deterministic Windows-local
bundle installs an `igd` command, and `igd open <C# source root>` creates or resumes the
local semantic-overlay project, selects a loopback port, waits for readiness, and opens
the Workbench. Runtime and user project data are separated, uninstall preserves review
projects, concurrent project sessions are blocked, and stale source fails closed. The
preview is installable but not signed or publicly released; source refresh, upgrade,
self-contained runtime, editor integration, and team operation remain product work.

P9.34.R refines only the Workbench renderer after live WindowsUtility review. The real
camera now reaches `256x` while retaining a one-click `100x` level, selected relations
taper to `0.30px`/`0.42` opacity at maximum zoom, and cached celestial-ceramic sprites
replace the previous glass finish. The graph, source snapshot, workflow, evidence,
authority, and history domains are unchanged.

P9.34.R5 supersedes the R through R4 visual-material experiments. The current
Workbench follows the inspected Graphify presentation mechanics: circular nodes,
categorical code-community colors, degree-weighted size, hub-only default labels, and
confidence-aware relations. The second material canvas is gone, selected relations
remain continuous at `512x`, and the unified IntentGraph graph plus its work, delta,
code-diff, evidence, and authority surfaces are unchanged.

## Working Definition

IntentGraph is not just a code graph. It is an overlay graph over an existing codebase that can contain:

- product intent and requirements
- stable code references and extracted code facts
- relationships between files, functions, classes, tests, and runtime behavior
- semantic graph deltas
- evidence, validation results, and change history
- authority, review, and provenance boundaries

The long-term overlay structure is not a flat bag of nodes. Phase 1 revises [Intent Units](docs/design/intent-unit-model.md): stable semantic work units with contracts, behavior claims, verification obligations, evidence, authority, history, and mapping obligations to `codeRef` and `codeFactRef` records.

## Initial Scope

This repository starts with process and design boundaries before implementation. The first goal is to avoid rebuilding existing stronger systems by accident.

Initial tracks:

1. Prior-art and benchmark gate
2. IntentGraph core overlay schema and mapping boundary
3. Code fact extraction and mapping boundary
4. Consistency/change orchestration boundary
5. Limited metadata-backed generation experiment boundary
6. AI-assisted change proposal boundary

## Before Implementation

Start here:

- [Start Here](docs/START-HERE.md)
- [Core Thesis](docs/concept/core-thesis.md)
- [IntentGraph Formal Blueprint](docs/design/intentgraph-formal-blueprint.md)
- [Intent Unit Model](docs/design/intent-unit-model.md)
- [Evidence Model](docs/evidence/evidence-model.md)
- [Authority Model](docs/authority/authority-model.md)
- [Change History Model](docs/history/change-history-model.md)
- [AI Proposal Format](docs/ai/proposal-format.md)
- [Workbench Boundary](docs/workbench/workbench-boundary.md)
- [Phase 0 Final Review](docs/reviews/phase-0-final-review.md)
- [Glossary](docs/concept/glossary.md)
- [Non-Goals](docs/concept/non-goals.md)
- [Milestones](docs/roadmap/milestones.md)
- [Phase 1 Entry Plan](docs/roadmap/phase-1-entry-plan.md)
- [Product Capability Roadmap](docs/roadmap/product-capability-roadmap.md)

Every major implementation slice must pass:

- [Prior-Art Gate](docs/process/prior-art-gate.md)
- [Capability Matrix](docs/research/capability-matrix.md)
- [Build / Borrow / Integrate Decisions](docs/decisions/build-borrow-integrate-decisions.md)
- [Benchmark Plan](docs/research/benchmark-plan.md)
- [Milestone Review Gate](docs/process/milestone-review-gate.md)

Worker handoffs must follow:

- [Worker Handoff Protocol](docs/process/worker-handoff-protocol.md)
- [Autonomous Work Loop](docs/process/autonomous-work-loop.md)
- [Worker Completion Report Template](docs/templates/worker-completion-report-template.md)

## Non-Goals for the First Slice

- Do not clone DevView's report-only readiness surface.
- Do not build a full IDE first.
- Do not implement a large language ecosystem first.
- Do not duplicate existing code graph engines without a build/borrow/integrate decision.
- Do not treat AI output as authority without deterministic validation.

## Starting Documents

- [Start Here](docs/START-HERE.md)
- [Core Thesis](docs/concept/core-thesis.md)
- [Core Definition](docs/design/core-definition.md)
- [IntentGraph Formal Blueprint](docs/design/intentgraph-formal-blueprint.md)
- [Milestones](docs/roadmap/milestones.md)
- [Prior-Art Gate](docs/process/prior-art-gate.md)
- [Late Prior-Art Discovery Protocol](docs/process/late-prior-art-discovery.md)
- [Autonomous Work Loop](docs/process/autonomous-work-loop.md)
- [Prior-Art Map](docs/research/prior-art-map.md)
- [Capability Matrix](docs/research/capability-matrix.md)
- [Benchmark Plan](docs/research/benchmark-plan.md)
