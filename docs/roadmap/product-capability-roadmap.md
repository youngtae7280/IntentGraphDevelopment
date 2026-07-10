# Product Capability Roadmap

Status: controlling roadmap for post-P1.18 planning.

This document defines the long-range capability roadmap for IntentGraph Development. It does not authorize all phases at once. Each phase must be opened by the Coordinator, executed in bounded slices, reviewed, and either improved or closed before the next phase begins.

The current authorized posture is:

```text
P8.4 completed.
Selected next benchmark: B1-typescript-rest-api.
Productization readiness is blocked.
Next safe work must stabilize real-project adoption before product implementation.
Phase G has only read-only WindowsUtility inventory and mapping hypotheses. P8.0 converted the productization blockers into a checklist and stabilization plan. P8.1 recorded that the WindowsUtility target state is unresolved. P8.2 defined how mappings may be accepted. P8.3 selected shell-workspace as the first candidate. P8.4 created a draft mapping outside WindowsUtility without accepting it. Source mutation, patch application, broad extraction, production UI/workbench product, AI coding runtime, packaging, release, and productization remain unauthorized.
```

## Core Definition

IntentGraph is a development-semantic overlay over source code. Source code remains the implementation source.

Corrected state model:

```text
D = (I, C, X, M, E, A, H)
```

Where:

- `I` is the intent, behavior, verification, and contract graph.
- `C` is the source code artifact set.
- `X` is the extracted code fact graph.
- `M` is the mapping between `I` and `X/C`.
- `E` is evidence.
- `A` is authority.
- `H` is semantic history.

Default code-first operation frame:

```text
Extract(C) -> X
Map(I, X) -> M
Plan(I, C, X, M, request) -> (DeltaC, DeltaI, DeltaM, required E, required A)
Verify(I', C', X', M', E', A', H') -> pass/fail
Record(H, accepted delta)
```

Graph-first generation remains a limited mode, not the general architecture:

```text
G -> Native(G) -> (C, metadata)
Retrofit(C, metadata) -> G'
Verify(G, G') -> pass/fail
```

## Roadmap Control Rules

1. One bounded slice at a time.
2. Every phase starts with a plan-only gate unless the Coordinator explicitly waives it.
3. Every new external capability must pass a prior-art and build/borrow/integrate review before implementation.
4. If a slice fails its quality bar, the worker must analyze and improve it before moving forward.
5. AI output is proposal-only unless a later authority model explicitly grants bounded acceptance power.
6. Source code is not replaced by IntentGraph.
7. Code nodes are stable references, anchors, ranges, symbols, or extracted facts, not copies of code text.
8. Verification must be deterministic. AI judgment cannot be the verifier.
9. Historical artifacts must remain explicit when reports depend on historical states.
10. A phase may not claim product readiness until it passes real-project and usability gates.

## Current Position

Phase A is substantially complete. P1.R through P1.18 corrected the project from graph-as-source/compiler-first framing into a semantic-overlay architecture and proved the model on the small CF0 fixture.

CF0 is now a saturated proof fixture. It proves viability, not scalability.

P1.19 completed the plan-only generalization gate:

```text
B1-typescript-rest-api selected.
```

P2.0 completed the first bounded Phase B implementation slice:

```text
B1 TypeScript REST Code Fact Schema and Static Fixture
```

P7.2 completed:

```text
WindowsUtility Read-Only Intent Mapping Hypothesis
```

P7.2 emitted read-only WindowsUtility Intent Unit hypotheses, evidence gaps, authority gaps, and ambiguity records.

P7.3 completed:

```text
Productization is not ready.
```

P7.3 reviewed Phase G evidence and opened only a readiness/gap report path for Phase H. It did not authorize product packaging, release, editor integration, GitHub workflow integration, team workflow automation, or product readiness claims.

P8.0 completed:

```text
Productization Readiness Gap Report and Stabilization Plan
```

P8.0 turned the productization blockers into a deterministic checklist and stabilization plan. It did not implement productization.

P8.1 completed:

```text
WindowsUtility repository state remains unresolved.
```

P8.1 recorded the target status and kept target writes blocked.

P8.2 completed:

```text
Accepted mapping boundary defined; no mapping accepted.
```

P8.3 completed:

```text
shell-workspace selected as first accepted-mapping candidate; no mapping accepted.
```

P8.4 completed:

```text
shell-workspace mapping draft created; still unaccepted.
```

The next safe work must resolve or plan real-project adoption blockers before product implementation. Reasonable next slices are:

```text
P8.5 Shell Workspace Mapping Draft Negative Probes
external target-state resolution
```

## Phase Overview

| Phase | Name | Purpose | Current state |
|---|---|---|---|
| A | Model Correction | Define IntentGraph as semantic overlay and correct the state model. | Mostly complete through P1.18. |
| B | Fast Retrofit and Code Facts | Convert existing codebases into deterministic code facts quickly. | P2.0 static facts, P2.1 incremental facts, and P2.2 boundary review completed for B1. |
| C | Intent Mapping | Map natural-language or declared intent to code facts, refs, ambiguity, and obligations. | P3.0 static mapping, P3.1 stale failure, P3.2 ambiguity candidate, and P3.3 boundary review completed. |
| D | Native / Change Planning | Produce bounded code, mapping, test, evidence, and authority proposals from intent deltas. | P4.0 proposal validation and P4.1 boundary review completed for B1. |
| E | Consistency Verifier | Generalize deterministic verification across intent, code facts, mappings, tests, evidence, authority, and history. | P5.0 verifier and P5.1 boundary review completed for B1. |
| F | Workbench | Visualize graph, code facts, deltas, evidence, authority, and history as an inspectable workflow. | P6.0 preview and P6.1 boundary review completed for B1. |
| G | Real Project Adoption | Apply the loop to realistic repositories such as WindowsUtility and compare quality. | P7.0-P7.3 completed as read-only WindowsUtility adoption and productization gate evidence. |
| H | Productization | Package CLI/local app/editor/GitHub/team workflow surfaces. | Blocked by P8.0 readiness report; product implementation waits for real-project stabilization evidence. |

## Phase A: Model Correction

Goal:

Correct the project identity and state model so all later work builds on the semantic-overlay thesis.

Allowed work:

- define `D = (I, C, X, M, E, A, H)`
- define Intent Units as semantic work units
- define code nodes as references/facts
- distinguish code-first maintenance from limited graph-first generation
- document evidence, authority, and semantic history boundaries
- add tiny proof fixtures and correction reviews

Non-goals:

- no broad extractor
- no product UI
- no real-project adoption claim
- no graph-as-source replacement claim
- no automatic AI authority

Required outputs:

- corrected README and concept docs
- formal blueprint using the semantic-overlay model
- Intent Unit mapping docs
- validation rules
- review docs proving old graph-as-source language is historical or removed

Verification:

- deprecated framing scan passes
- tiny generated-code and code-first fixture regressions pass
- source-text equality is not required for code-first maintenance
- hidden generated-code snapshots are not used by code-first maintenance proofs
- AI proposal outputs remain non-authoritative

Exit criteria:

- reviewers can explain the architecture without saying source code is replaced
- code nodes are consistently defined as refs/facts
- P1.18 or later review says additional CF0 work is no longer the highest-value path

Stop conditions:

- any doc reintroduces universal graph-to-code compiler framing
- code-first work starts depending on hidden generated-code snapshots
- CF0 fixture work continues without a generalization reason

Status:

Substantially complete through P1.18.

## Phase B: Fast Retrofit and Code Fact Foundation

Goal:

Make existing codebases produce deterministic code facts quickly enough to support mapping and review.

Allowed work:

- choose the second benchmark through a plan-only gate
- define the code fact schema for files, symbols, ranges, anchors, imports, calls, references, and tests
- integrate or adapt existing code intelligence systems when they are stronger than local extraction
- record source digests, source ranges, anchor stability, extractor versions, and confidence
- implement bounded incremental extraction
- measure extraction speed and stability
- document code-only loss boundaries

Non-goals:

- no AI-generated mapping acceptance
- no product UI beyond diagnostic reports
- no broad all-language extractor unless prior-art review justifies it
- no source-code replacement claim
- no arbitrary provider/network dependency without explicit decision

Required outputs:

- selected second benchmark with rationale
- code fact schema and validation rules
- extractor or adapter decision record
- deterministic code-fact output
- incremental extraction report
- fixture and negative tests for stale facts, missing anchors, invalid ranges, and unknown relation types

Verification:

- repeated extraction on unchanged source produces identical facts and digests
- a one-file source change updates only the expected fact subset
- all facts carry source file, source digest, range or anchor status, extractor identity, and confidence
- extracted relations have valid endpoints
- performance is measured on the benchmark and recorded
- prior-art comparison explains what is built, borrowed, or integrated

Exit criteria:

- the next benchmark can produce stable `X` from `C`
- mappings can reference code facts without copying code text
- incremental update behavior is measured and deterministic
- unsupported languages or relation types fail clearly

Stop conditions:

- extraction becomes an unbounded Graphify/CodeQL/Joern replacement attempt without a decision
- generated facts are nondeterministic
- code facts contain source text as the authority source instead of refs/digests/ranges
- performance is too slow for the selected benchmark and no remediation plan exists

## Phase C: Intent Mapping

Goal:

Map user requests and declared intent to code facts, code refs, mapping obligations, ambiguity records, and verification needs.

Allowed work:

- define request and intent hypothesis records
- define mapping confidence and ambiguity states
- map Intent Units to code facts and code refs
- identify unmapped or overmapped intent
- require human or policy confirmation for ambiguous mappings
- create negative cases for wrong, missing, stale, or ambiguous mappings

Non-goals:

- no automatic AI authority
- no code edits yet unless part of a separate Phase D slice
- no claim that natural language can deterministically recover full intent
- no broad planning engine

Required outputs:

- intent mapping schema
- ambiguity model
- mapping verifier
- report format for mapped, unmapped, ambiguous, stale, and overbroad mappings
- second-benchmark mapping examples

Verification:

- all accepted Intent Units have resolvable code refs or explicit no-code status
- ambiguous mappings remain marked ambiguous and cannot be silently accepted
- stale code refs fail after source changes
- AI-generated mapping candidates are recorded as proposals, not authority
- negative fixtures prove bad mappings fail for the intended reason

Exit criteria:

- a realistic request can become an inspectable intent/mapping hypothesis
- unresolved ambiguity is visible in reports
- accepted mappings survive deterministic verification

Stop conditions:

- AI mapping output is treated as verified truth
- unresolved ambiguity is hidden
- mapping claims cannot be traced to code facts or source refs

## Phase D: Native / Change Planning

Goal:

Turn an accepted or proposed intent delta into bounded code-edit, mapping-update, test, evidence, and authority proposals.

Allowed work:

- define change proposal format
- generate or hand-author small bounded proposals
- propose `DeltaC`, `DeltaI`, `DeltaM`, required tests, required evidence, and required authority
- compare multiple implementation candidates
- keep application separate from proposal

Non-goals:

- no silent code mutation
- no automatic acceptance
- no broad AI coding agent runtime
- no product-wide refactor planner without benchmark evidence

Required outputs:

- change planning contract
- proposal validator
- patch preview or code-diff artifact
- mapping update proposal
- test/evidence/authority requirement proposal
- negative probes for overbroad edits, missing tests, stale mappings, and self-authorized proposals

Verification:

- proposal applies to the expected source baseline only
- proposed code diff is bounded to mapped impact scope unless explicitly escalated
- tests and evidence requirements are generated or declared
- authority requirements are present before acceptance
- rejected proposals produce deterministic failure reports

Exit criteria:

- at least one realistic second-benchmark change produces inspectable proposal artifacts
- proposal acceptance is gated by Phase E verification
- the system can explain why a proposal is unsafe or incomplete

Stop conditions:

- a proposal mutates code without review
- AI self-authorizes
- impact scope is larger than declared and not escalated
- tests/evidence are optional for behavior-changing deltas

## Phase E: Consistency Verifier

Goal:

Generalize deterministic verification over source, code facts, mappings, tests, evidence, authority, and semantic history.

Allowed work:

- verify code refs and code facts
- verify mapping obligations
- verify behavior or test obligations
- verify evidence completeness
- verify authority completeness
- verify semantic history and historical baselines
- emit deterministic pass/fail reports

Non-goals:

- no AI judgment as verifier
- no full semantic equivalence claim without bounded proof
- no production security or compliance claim without external audit

Required outputs:

- verifier contract
- report schema
- reusable negative harness pattern
- historical-state validation
- benchmark-specific and cross-benchmark assertions

Verification:

- every pass condition has a corresponding negative case where practical
- missing evidence, authority, tests, code facts, and history fail deterministically
- historical reports do not depend on mutable current artifacts
- verifier output includes claim scope and known losses
- all validation commands are documented and rerunnable

Exit criteria:

- verifier catches the main bad states for at least two benchmark shapes
- reports are understandable enough for workbench visualization
- quality review says the verifier is broader than CF0-specific checks

Stop conditions:

- failures are nondeterministic
- reports omit claim scope
- historical artifacts drift
- fixture-specific logic is presented as general

## Phase F: Workbench

Goal:

Give humans a usable visual surface for request, intent graph, code facts, mappings, deltas, evidence, authority, and history.

Allowed work:

- HTML or local app workbench projection
- graph view
- task/stage timeline
- code diff view
- evidence and authority panel
- mapping ambiguity display
- verifier report display
- screenshot-based UI validation

Non-goals:

- no production SaaS
- no team workflow automation yet
- no editor integration yet
- no decorative graph-only viewer that hides verification state

Required outputs:

- workbench projection schema
- interactive prototype
- visual regression screenshots
- usability checklist
- clear current/historical state navigation

Verification:

- graph nodes and edges are visible and selectable
- selecting a node or edge shows its code refs, facts, evidence, authority, and history when available
- deltas visually highlight affected graph and code areas
- verifier failures are visible without reading raw JSON
- browser screenshots prove the UI is nonblank, readable, and interactive
- no misleading claim that visualization itself verifies correctness

Exit criteria:

- a user can inspect a completed benchmark loop through the workbench without opening every JSON file
- graph, code diff, evidence, authority, and history are connected in the UI
- usability review identifies no blocking comprehension failures

Stop conditions:

- the workbench becomes only a pretty graph viewer
- selection or filtering does not affect visible state
- UI hides verifier failures
- evidence/authority/history are absent from the main workflow

## Phase G: Real Project Adoption

Goal:

Apply IntentGraph to a realistic repository and measure whether it improves AI-assisted development quality.

Allowed work:

- select real repository and task class
- run retrofit over the real codebase
- define intent/mapping/evidence/authority workflow
- compare against ordinary AI coding baseline
- measure speed, correctness, review effort, and regression rate
- run workflow on WindowsUtility or another approved project

Non-goals:

- no team-wide rollout before repeatable local evidence
- no broad language/platform claim from one project
- no production automation without rollback plan

Required outputs:

- real-project adoption plan
- baseline comparison method
- performance benchmark
- user workflow benchmark
- quality comparison report
- failure log and improvement plan

Verification:

- retrofit completes within an acceptable time budget
- mappings are useful for actual change review
- verifier catches at least one realistic bad state or proves important completeness
- workbench improves inspectability compared with raw files
- normal AI coding baseline is compared honestly

Exit criteria:

- at least one realistic change is completed through the IntentGraph workflow
- user can review graph delta, code delta, evidence, authority, and history in one loop
- adoption review says whether to continue, pivot, or stop

Stop conditions:

- real-project workflow is slower without quality gain
- graph/mapping noise overwhelms review
- retrofit is too slow or unstable
- users cannot understand the workbench output

## Phase H: Productization

Goal:

Turn the proven workflow into installable and maintainable product surfaces.

Allowed work:

- CLI packaging
- local app packaging
- editor integration
- GitHub workflow integration
- team policy configuration
- documentation and onboarding
- release testing

Non-goals:

- no product claims unsupported by Phase G
- no remote service dependency unless explicitly chosen
- no unsafe automatic merge/deploy authority

Required outputs:

- installable CLI or app
- configuration format
- onboarding docs
- sample project workflow
- release checklist
- compatibility matrix
- security and privacy boundary docs

Verification:

- clean install works on a fresh machine or clean environment
- sample workflow passes from request to reviewed delta
- editor/GitHub integrations preserve authority boundaries
- telemetry, privacy, and local data handling are documented
- rollback and uninstall paths are tested

Exit criteria:

- a new user can run the workflow on a supported project without repository-specific handholding
- product surfaces preserve the semantic-overlay model
- release review approves public or team usage

Stop conditions:

- installation is fragile
- product hides verification/evidence/authority state
- integration grants authority beyond the declared policy
- documentation teaches users the wrong mental model

## Cross-Phase Quality Bar

Every implementation slice must report:

- commit hash and push status
- final `HEAD == origin/main` status
- final clean worktree status
- changed files
- exact validation commands and results
- generated artifact paths
- known gaps and risks
- explicit non-goals preserved
- recommendation for the next bounded slice

Every phase review must answer:

- What did this phase prove?
- What did it not prove?
- Which prior-art systems were considered?
- Which parts were built, borrowed, or integrated?
- Which failures are now deterministic?
- Which failures remain possible?
- What benchmark evidence exists?
- What user-facing value has been demonstrated?
- Should the next phase open, pause, or improve the current phase?

## P8.0 Result And Productization Blocker Boundary

P1.19 completed the plan-only generalization gate.

P1.19 produced:

- second benchmark candidate comparison
- selected limitation of CF0 to test next
- prior-art/build-borrow-integrate review for the selected direction
- Phase B entry criteria
- Phase B non-goals
- Phase B pass/fail criteria
- validation command plan
- worker handoff instructions

Selected next benchmark:

```text
B1-typescript-rest-api
```

P2.0 result:

```text
B1 static fixture, schema, extractor, validator, and negative probes pass.
```

P7.2 result:

```text
WindowsUtility read-only mapping hypothesis passes.
```

P7.3 result:

```text
Productization readiness gate completed.
Decision: productization-not-ready-open-readiness-gap-report-only.
```

P7.3 produced:

- [P7.3 Real Project Adoption Boundary Productization Readiness Review](../reviews/p7.3-real-project-adoption-boundary-productization-readiness-review.md)
- `generated/roadmap/p7.3-productization-readiness-gate-report.json`

P8.0 result:

```text
Productization readiness gap report completed.
Decision: productization-blocked-stabilization-required.
```

P8.0 produced:

- [P8.0 Productization Readiness Gap Stabilization Review](../reviews/p8.0-productization-readiness-gap-stabilization-review.md)
- [Productization Stabilization Plan](productization-stabilization-plan.md)
- `generated/roadmap/p8.0-productization-readiness-gap-report.json`

Productization remains blocked until:

- WindowsUtility repository state is acceptable.
- accepted real-project mappings exist.
- one real-project proposal/evidence/authority loop passes deterministic verification.
- a real-project workbench projection exists.
- a user workflow benchmark exists.
- the first product surface has a decision record.

Next safe work must not:

- mutate real-project source code
- run broad unbounded retrofit
- grant AI authority
- apply AI-generated code
- claim product readiness
- build packaging or release artifacts
- build editor/GitHub/team workflow integration
- build a broad extractor
- add dependencies without decision record
- claim general scalability

## P8.1 Result And Target-State Boundary

P8.1 result:

```text
WindowsUtility repository state resolution plan completed.
Decision: target-state-unresolved-target-writes-blocked.
```

P8.1 produced:

- [P8.1 WindowsUtility Repository State Resolution Plan Review](../reviews/p8.1-windowsutility-repository-state-resolution-plan-review.md)
- `generated/roadmap/p8.1-windowsutility-repository-state-resolution-report.json`

Target writes, accepted mappings, proposal application, and productization remain blocked until the target repository state is explicitly resolved or scoped.

## P8.2 Result And Accepted-Mapping Boundary

P8.2 result:

```text
Accepted mapping boundary completed.
Decision: accepted-mapping-not-created-boundary-defined.
```

P8.2 produced:

- [P8.2 WindowsUtility Accepted Mapping Boundary Plan Review](../reviews/p8.2-windowsutility-accepted-mapping-boundary-plan-review.md)
- `generated/roadmap/p8.2-windowsutility-accepted-mapping-boundary-report.json`

WindowsUtility mappings remain hypotheses until a later slice selects a candidate, records baseline state, resolves ambiguity, defines evidence and authority requirements, and runs stale/missing mapping probes.

## P8.3 Result And Mapping Candidate Selection

P8.3 result:

```text
shell-workspace candidate selected.
Decision: select-shell-workspace-candidate-do-not-accept.
```

P8.3 produced:

- [P8.3 WindowsUtility Accepted Mapping Candidate Selection Review](../reviews/p8.3-windowsutility-accepted-mapping-candidate-selection-review.md)
- `generated/roadmap/p8.3-windowsutility-mapping-candidate-selection-report.json`

The selected candidate is still unaccepted. Target writes, proposal application, AI authority, and productization remain blocked.

## P8.4 Result And Mapping Draft

P8.4 result:

```text
shell-workspace mapping draft created.
Decision: draft-created-mapping-not-accepted.
```

P8.4 produced:

- `generated/windowsutility/p8.4-shell-workspace-accepted-mapping-draft.json`
- [P8.4 WindowsUtility Shell Workspace Accepted Mapping Draft Review](../reviews/p8.4-windowsutility-shell-workspace-accepted-mapping-draft-review.md)
- `generated/roadmap/p8.4-shell-workspace-mapping-draft-report.json`

The draft records read-only source digests and keeps `accepted:false`, `baselineAccepted:false`, target writes false, AI authority false, and productization false.
