# IntentGraph Development

IntentGraph Development is a semantic-overlay software development methodology for AI-assisted development.

The central idea:

> Code remains the implementation source. IntentGraph is the semantic overlay that keeps intent, code facts, evidence, authority, and change history aligned.

IntentGraph is a development-semantic overlay graph linked to source code artifacts. It does not replace source code. Code nodes are stable references or facts about files, symbols, ranges, anchors, and extracted code facts, not copies of code text.

## Current Status

Phase 0 is complete as of 2026-07-09. See the [Phase 0 Final Review](docs/reviews/phase-0-final-review.md).

No `M8` was opened automatically. P1.R through P1.18 reframed IntentGraph as a semantic overlay and proved the corrected model on a tiny CF0 code-first fixture. CF0 is now treated as saturated proof evidence, not proof of general scalability.

P1.19 selected `B1-typescript-rest-api` as the next benchmark shape. P2.0 created the first bounded B1 fixture, code fact schema, extractor, validator, and negative probes. P2.1 proved a one-file incremental code fact change. P2.2 opened Phase C only for a bounded static B1 mapping slice. P3.0 created the B1 Intent Unit mapping overlay and verifier. P3.1 proved stale mapping failure. P3.2 proved ambiguous mapping candidates remain unresolved. P3.3 reviewed the Phase C boundary. P4.0 created the first non-applied B1 change proposal schema, proposal artifact, validator, and negative probes. P4.1 reviewed the Phase D boundary. P5.0 added deterministic B1 proposal consistency verification. P5.1 opened Phase F. P6.0 added a deterministic B1 workbench projection and static HTML preview. P6.1 opened Phase G. P7.0 selected WindowsUtility as the first real-project target, read-only first. P7.1 emitted a read-only WindowsUtility inventory. P7.2 emitted read-only WindowsUtility mapping hypotheses. The next recommended work is `P7.3 Real Project Adoption Boundary Review and Productization Readiness Gate`. It must not mutate source, apply patches, become a production UI/workbench product, or AI coding runtime. See the [Product Capability Roadmap](docs/roadmap/product-capability-roadmap.md).

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
