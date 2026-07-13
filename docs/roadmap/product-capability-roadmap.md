# Product Capability Roadmap

Status: controlling roadmap for post-P1.18 planning.

This document defines the long-range capability roadmap for IntentGraph Development. It does not authorize all phases at once. Each phase must be opened by the Coordinator, executed in bounded slices, reviewed, and either improved or closed before the next phase begins.

The current authorized posture is:

```text
P9.27 completed.
Selected next benchmark: B1-typescript-rest-api.
IntentGraphDevelopment has a defined-but-not-built product candidate: IntentGraph Local Review Kit.
The experimental C# fact-only inspector is complete. P9.13 adds a separate local semantic-overlay project workspace and unified project workbench. P9.14 adds review-only change proposals with graph delta and code-diff fragments to that same C# project route. P9.15 corrects the raw-code-heavy default graph and adds a loopback-only interactive work-request intake surface. Visual interaction review remains a required user-facing quality gate.

P9.17 supersedes the P9.15 semantic-only default. The local Workbench loads the full graph through progressive detail and deterministic radial source communities, preserves one graph across lens changes, records local mapping candidates, and can record a declared semantic foundation from supplied project documents without automatically creating Intent Units. P9.18 then corrects large-graph navigation: module communities are weight-aware and organic, semantic overview and text search emphasize records in place, and visibility, selection, fitting, and panel resizing avoid full-graph restyling where possible. Its current visual system uses a dark neon/space palette and only labels core semantic nodes, code capsules, changed-code facts, selected code facts, and search matches; ordinary code facts remain inspectable by selection. P9.19 adds a loopback-only review-proposal intake dialog that uses the existing deterministic proposal validator and records only non-applied local project-state artifacts. P9.20 adds typed non-executing review receipts for individual proposal verification/evidence requirement pairs.
Phase G has only read-only WindowsUtility inventory and mapping hypotheses. P8.0 converted the productization blockers into a checklist and stabilization plan. P8.1 recorded that the WindowsUtility target state was unresolved. P8.2 defined how mappings may be accepted. P8.3 selected shell-workspace as the first candidate. P8.4 created a draft mapping outside WindowsUtility without accepting it. P8.5 added repeatable mapping draft negative probes. P8.6 resolved WindowsUtility target state to clean/aligned. P8.7 says the mapping is ready to request human acceptance. P8.8 created the human acceptance request. P8.9 recorded the user's `accept` response and created the first accepted mapping. P8.10 added accepted mapping negative probes. P8.11 opened the non-applied proposal boundary. P8.12 created the first shell/workspace smoke evidence proposal. P8.13 added proposal negative probes. P8.14 required future smoke evidence to use a no-target-write sandbox strategy. P8.15 proved sandboxed build smoke evidence while the original target stayed unchanged. P8.16 opened only a sandboxed UI launch feasibility boundary. P8.17 proved sandboxed UI launch/window observation while the original target stayed unchanged. P8.18 opened only a sandboxed screenshot evidence boundary. P8.19 captured validated sandboxed screenshot evidence while the original target stayed unchanged. P8.20 defined the shell/workspace evidence workbench projection boundary. P8.21 emitted a deterministic shell/workspace evidence workbench projection and static HTML preview. P8.22 added repeatable projection negative probes. P8.23 defined the workbench usability dry-run boundary. P8.24 completed the self-conducted workbench-vs-raw-JSON dry run. P8.25 defined the user workflow benchmark boundary. P8.26 created the benchmark request. P8.27 recorded the user's compact `accept` response as proceed. P8.28 rechecked productization and kept it blocked pending product-surface and application gates. P8.29 selected static local workbench export as the first product surface boundary. P8.30 defined the static export boundary. P8.31 emitted and validated the static local WindowsUtility workbench export prototype. P8.32 found the export ready for user review but not productized. P8.33 created the user review request. P8.34 recorded the user's `revise` response because the export did not explain what it is or what to inspect. P8.35 emitted a revised export with reviewer orientation. P8.36 created the orientation review request. P8.37 recorded the user's `proceed` response. P8.38 rechecked productization and kept it blocked pending source application, packaging, and release gates. P8.39 planned the source application authority boundary. P8.40 recorded the non-mutating source application dry-run boundary. P8.41 emitted and validated the first non-mutating source-application dry-run prototype while observing but not exercising the user source-modification permission. P8.42 reviewed that permission and found the existing P8.12 proposal has no source patch, so a minimal source edit proposal and patch preview are required before source application. P8.43 selected one test-automation source edit and emitted a patch preview without applying it. P8.44 applied the first WindowsUtility source edit, validated preflight/build, and pushed the target commit. P8.45 found productization still blocked pending refreshed source-application workbench visibility and packaging/release gates. P8.46 refreshed the static workbench with source application evidence. P8.47 planned the report-only packaging/release boundary. P8.48 recorded the non-mutating packaging/release dry-run boundary. P8.49 emitted and validated the non-mutating packaging/release dry-run prototype. P8.50 reviewed the dry-run result and kept productization blocked pending refreshed workbench visibility and explicit approval gates. P8.51 refreshed the static workbench with packaging/release dry-run evidence. P8.52 rechecked productization readiness and kept it blocked pending package artifact, release, packaged-artifact verification, user acceptance, and productization authority. P8.53 requested explicit package artifact creation authorization. P8.54 recorded the user's `accept sandboxed package artifact creation` response. P8.55 created and validated a bounded sandboxed WindowsUtility package artifact. P8.56 recorded the packaged artifact verification boundary. P8.57 recorded Graphify-grade graph/delta/diff approval-workbench requirements. P8.58 turned those requirements into a bounded implementation plan. P8.59 emitted and validated the deterministic graph/delta/diff projection schema. P8.60 emitted the first static local graph-delta approval workbench. P8.61 attempted browser visual QA but was blocked by browser policy. P8.62 requested user-observed review, recorded revise feedback, and added a review helper. P8.63 implemented the revise feedback with a dark graph workbench, resizable panels, and stricter validation. P8.64 accepted the revised surface for continuation under the current-goal response policy. P8.65 rechecked productization and kept it blocked pending packaged artifact verification, release, product candidate acceptance, and productization authority. P8.66 replayed package metadata and zip inventory without extraction or execution. P8.67 added repeatable negative probes for the metadata replay boundary. P8.68 requested explicit sandboxed package extraction inventory verification authority without recording that authority. P8.69 prepared and validated the sandbox extraction inventory verifier using only a synthetic package; the existing WindowsUtility package was not extracted. P8.70 added repeatable negative probes for missing authorization, stale metadata, unsafe zip entries, non-zip input, missing entries, and unsafe extraction roots. P8.71 recorded that explicit real-package extraction authorization is still absent. P8.72 rechecked productization and kept it blocked pending real package verification, release authority, product candidate acceptance, and productization authority. P8.73 recorded a clearer follow-up request and separated the user response string from the verifier token. P8.74 recorded the hold state and allowed only report-only future execution planning while extraction authority is absent. P8.75 recorded the future package extraction inventory execution sequence without executing it. P8.76 recorded the future packaged executable launch smoke boundary without executing it. P8.77 requested future launch smoke authorization but kept it not actionable until extraction inventory verification passes. P8.78 recorded the future packaged UI screenshot boundary without launching or capturing screenshots. P8.79 requested future screenshot capture authorization but kept it not actionable until extraction inventory verification and launch smoke pass. P8.80 recorded the screenshot hold state and allowed only report-only readiness/release boundary work while screenshot preconditions are absent. P8.81 rechecked productization and kept it blocked pending real verification, UI evidence, release authority, product candidate acceptance, and productization authority. P8.82 recorded the future installer creation boundary without creating an installer. P8.83 requested future installer creation authorization but kept it not actionable until package verification, launch smoke evidence if needed, and product candidate acceptance pass. P8.84 recorded the installer creation hold state and kept installer creation, global install, signing, release, and productization authority false. P8.85 rechecked productization after installer boundary planning and kept productization blocked pending installer, signing, release, product candidate, and productization authority gates. P8.86 recorded the artifact signing authority boundary without signing, key access, certificate access, timestamp authority calls, release publishing, or productization authority. P8.87 requested future artifact signing authorization but kept it not actionable until verified artifact evidence, signing policy, and key/certificate authority boundary exist. P8.88 recorded the artifact signing hold state and kept signing, key/certificate/token access, timestamp authority calls, release publishing, and productization authority false. P8.89 rechecked productization after signing boundary planning and kept productization blocked pending release and productization authority gates. P8.90 recorded the release authority boundary without release tags, provider/API calls, release publishing, credential access, or productization authority. P8.91 requested future release authorization but kept it not actionable until product candidate acceptance, verified release artifacts, release notes, and provider/credential authority exist. P8.92 recorded the release hold state and kept release tags, provider/API calls, credential access, release publishing, and productization authority false. P8.93 rechecked productization after release boundary planning and kept productization blocked pending final productization authority and all upstream evidence gates. P8.94 recorded the final productization authority boundary without accepting a product candidate or claiming productization readiness. P8.95 requested future productization authorization but kept it not actionable until all upstream evidence gates are complete. P8.96 recorded the final productization hold state and kept product candidate acceptance and productization readiness claim false. P8.97 summarized the completed productization authority boundary chain and kept readiness not-ready pending real executable evidence. P8.98 reviewed real evidence execution authority and kept package extraction held until the exact sandboxed package extraction acceptance is recorded. P8.99 refreshed the exact package extraction verification authorization request and kept authorization not granted. P8.100 refreshed the package extraction verification hold state and kept existing package extraction false. P8.101 rechecked real evidence readiness and selected productization authority chain workbench visibility refresh as the next safe non-execution slice. P8.102 emitted a dark, resizable, graph-based productization authority chain workbench and kept all extraction, launch, screenshot, installer, signing, release, and productization execution flags false. P8.103 accepted that workbench for continuation only and kept exact package extraction, launch, screenshot, installer, signing, release, and productization authority false. P8.104 rechecked productization readiness after the accepted workbench and kept readiness not-ready because real executable evidence and final authority gates remain absent. P8.105 summarized the repeated execution hold and found no further non-execution productization slice is useful before an exact package extraction authorization artifact exists. P8.106 recorded the exact sandboxed package extraction inventory verification authorization response. P8.107 extracted the existing package only in a `.tmp` sandbox, verified 39 ZIP and extracted 39 files, confirmed required entries, and kept launch, screenshot, installer, signing, release, product candidate acceptance, and productization authority false. P8.108 rechecked productization after extraction and kept it blocked pending launch smoke, UI screenshot evidence, installer, signing, release, product candidate acceptance, and productization authority. P8.109 rechecked launch smoke authorization and found exact authorization still absent. P8.110 refreshed the exact launch smoke authorization request. P8.111 recorded the launch smoke hold. P8.112 recorded productization execution hold after the launch request. P8.113 recorded the exact sandboxed packaged executable launch smoke authorization response. P8.114 ran sandboxed packaged executable launch smoke and observed the package window without screenshots. P8.115 rechecked productization and kept it blocked pending UI evidence and later gates. P8.116 rechecked packaged UI screenshot authorization and found it absent. P8.117 refreshed the exact packaged UI screenshot authorization request. P8.118 recorded the screenshot hold because exact screenshot authorization remained absent. P8.119 recorded the exact sandboxed packaged UI screenshot capture authorization response. P8.120 captured validated packaged UI screenshot evidence from a sandboxed package copy. P8.121 rechecked productization and kept it not-ready pending product candidate acceptance, installer, signing, release, and final authority gates. P8.122 requested exact product candidate acceptance. P8.123 recorded the product candidate acceptance hold while the exact response remains absent.

P9.27 adds the first normal-form path from a mapped work item to an actual code-bearing proposal. The Workbench derives diff provenance from the immutable snapshot, rejects stale or out-of-range hunks, and immediately exposes the resulting graph and code delta without applying it.
```

> **Scope correction, P8.124:** the WindowsUtility package and its verification artifacts are Phase G adoption evidence. WindowsUtility is not an IntentGraphDevelopment product candidate, and the historical P8.121-P8.123 candidate-acceptance gate does not block this roadmap. IntentGraphDevelopment productization begins only after its own product surface and distribution boundary are defined. See [P8.124 WindowsUtility Adoption / IGD Productization Scope Correction](../reviews/p8.124-windowsutility-adoption-igd-productization-scope-correction.md).

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

P8.5 completed:

```text
mapping draft positive verification and negative probes pass.
```

P8.6 completed:

```text
WindowsUtility target state clean/aligned.
```

P8.7 completed:

```text
shell-workspace mapping ready for human acceptance request; not accepted.
```

P8.8 completed:

```text
human acceptance requested; not recorded.
```

P8.9 completed:

```text
shell-workspace mapping accepted; write/productization authority still false.
```

P8.10 completed:

```text
accepted mapping negative probes pass.
```

The WindowsUtility adoption sequence is no longer gated on accepting WindowsUtility as an IntentGraphDevelopment product. The next safe work is to define the separate IntentGraphDevelopment productization boundary:

```text
P9.11 Experimental C# Fact Workspace Scope Review - Plan Only
```

Latest readiness note:

```text
P8.124 superseded the P8.121-P8.123 interpretation that WindowsUtility package evidence and a WindowsUtility candidate acceptance determine IntentGraphDevelopment productization. P9.0 selected `igd-local-review-kit` as the defined-but-not-built IGD product build path. P9.1 added a fail-closed B1 local command/workspace workflow. P9.2 made that B1 profile portable across workspace locations through a logical source identity. P9.3 defined B1-equivalent external source intake and P9.4 proved it without target mutation or source-path persistence. P9.5/P9.6 passed a read-only WindowsUtility C# syntax-only probe. P9.7/P9.8 made its environmental SDK dependency explicit without a source read, parser package, or reusable extraction claim. P9.9/P9.10 now add a fact-only C# snapshot workspace route. No WindowsUtility product-candidate response is required.
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
| G | Real Project Adoption | Apply the loop to realistic repositories such as WindowsUtility and compare quality. | Bounded WindowsUtility mapping, source-change, package, launch, and UI evidence exists. It is adoption evidence, not an IGD product release. |
| H | Productization | Package IntentGraphDevelopment CLI/local app/editor/GitHub/team workflow surfaces. | P9.0 defined `igd-local-review-kit`; P9.1 added a bounded B1 local command/workspace workflow; P9.2 removed its workspace-path coupling; P9.3 defined and P9.4 proved bounded external intake; P9.5/P9.6 passed a C# read-only probe. P9.7/P9.8 added an experimental host-SDK preflight. P9.9/P9.10 add a fact-only C# snapshot workspace. P9.11 must review scope before mappings or product support. |

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

## P8.5 Result And Mapping Draft Negative Probes

P8.5 result:

```text
shell-workspace mapping draft verifier and negative probes pass.
```

P8.5 produced:

- `tools/verify_windowsutility_mapping_draft.py`
- `tools/run_windowsutility_mapping_draft_negative_probes.py`
- `generated/windowsutility/p8.5-shell-workspace-mapping-draft-verification-report.json`
- `generated/windowsutility/p8.5-shell-workspace-mapping-draft-negative-probes-report.json`
- [P8.5 Shell Workspace Mapping Draft Negative Probes Review](../reviews/p8.5-shell-workspace-mapping-draft-negative-probes-review.md)

The next blocker is external: target baseline resolution or explicit dirty-baseline acceptance. Without it, the mapping draft must remain unaccepted and proposal application must remain blocked.

## P8.6 Result And Clean Target State

P8.6 result:

```text
WindowsUtility target state clean/aligned.
Decision: target-state-clean-aligned.
```

P8.6 produced:

- [P8.6 WindowsUtility Target State Clean Aligned Review](../reviews/p8.6-windowsutility-target-state-clean-aligned-review.md)
- `generated/roadmap/p8.6-windowsutility-target-state-resolution-report.json`

The prior untracked `.devview/` directory was archived outside the target repository before removal. Clean/aligned target state does not automatically authorize accepted mappings or productization.

## P8.7 Result And Acceptance Readiness

P8.7 result:

```text
shell-workspace mapping ready for human acceptance request.
Decision: ready-to-request-human-acceptance-mapping-not-accepted.
```

P8.7 produced:

- [P8.7 Shell Workspace Mapping Acceptance Readiness Review](../reviews/p8.7-shell-workspace-mapping-acceptance-readiness-review.md)
- `generated/roadmap/p8.7-shell-workspace-mapping-acceptance-readiness-report.json`

The mapping remains unaccepted until explicit human acceptance is recorded.

## P8.8 Result And Human Acceptance Request

P8.8 result:

```text
human acceptance requested.
Decision: human-acceptance-requested-not-recorded.
```

P8.8 produced:

- [P8.8 Shell Workspace Mapping Human Acceptance Request Review](../reviews/p8.8-shell-workspace-mapping-human-acceptance-request-review.md)
- `generated/roadmap/p8.8-shell-workspace-mapping-human-acceptance-request.json`

The next step requires an explicit user/coordinator decision: accept, reject, or revise the shell-workspace mapping.

## P8.9 Result And Accepted Mapping

P8.9 result:

```text
shell-workspace mapping accepted.
Decision: shell-workspace-mapping-accepted-no-write-authority.
```

P8.9 produced:

- `generated/windowsutility/p8.9-shell-workspace-accepted-mapping.json`
- `tools/verify_windowsutility_accepted_mapping.py`
- `generated/windowsutility/p8.9-shell-workspace-accepted-mapping-verification-report.json`
- [P8.9 Shell Workspace Accepted Mapping Record Review](../reviews/p8.9-shell-workspace-accepted-mapping-record-review.md)
- `generated/roadmap/p8.9-shell-workspace-accepted-mapping-report.json`

Accepted mapping does not grant target writes, proposal application, AI authority, or productization.

## P8.10 Result And Accepted Mapping Negative Probes

P8.10 result:

```text
accepted mapping negative probes pass.
Decision: accepted-mapping-negative-probes-pass.
```

P8.10 produced:

- `tools/run_windowsutility_accepted_mapping_negative_probes.py`
- `generated/windowsutility/p8.10-shell-workspace-accepted-mapping-negative-probes-report.json`
- [P8.10 Shell Workspace Accepted Mapping Negative Probes Review](../reviews/p8.10-shell-workspace-accepted-mapping-negative-probes-review.md)
- `generated/roadmap/p8.10-shell-workspace-accepted-mapping-negative-probes-report.json`

The accepted mapping may now be used as input to a non-applied proposal boundary. Source edits remain unauthorized.

## P8.11 Result And Non-Applied Proposal Boundary

P8.11 result:

```text
non-applied proposal boundary opened.
Decision: non-applied-proposal-boundary-open-source-edits-blocked.
```

P8.11 produced:

- [P8.11 Shell Workspace Non-Applied Proposal Boundary Plan](../reviews/p8.11-shell-workspace-non-applied-proposal-boundary-plan-review.md)
- `generated/roadmap/p8.11-shell-workspace-non-applied-proposal-boundary-report.json`

The next proposal may define evidence requirements and verification plans, but source edits, target writes, application authority, AI authority, hardware authority, and productization remain unauthorized.

## P8.12 Result And Smoke Evidence Proposal

P8.12 result:

```text
shell/workspace smoke evidence proposal created.
Decision: non-applied-smoke-evidence-proposal-created.
```

P8.12 produced:

- `generated/windowsutility/p8.12-shell-workspace-smoke-evidence-non-applied-proposal.json`
- `tools/validate_windowsutility_non_applied_proposal.py`
- `generated/windowsutility/p8.12-shell-workspace-smoke-evidence-non-applied-proposal-validation-report.json`
- [P8.12 Shell Workspace Smoke Evidence Non-Applied Proposal Review](../reviews/p8.12-shell-workspace-smoke-evidence-non-applied-proposal-review.md)
- `generated/roadmap/p8.12-shell-workspace-smoke-evidence-non-applied-proposal-report.json`

The proposal binds to the accepted mapping and target baseline. It plans future evidence collection only. Source edits, target writes, proposal application, AI authority, hardware authority, and productization remain unauthorized.

## P8.13 Result And Non-Applied Proposal Negative Probes

P8.13 result:

```text
non-applied proposal negative probes pass.
Decision: non-applied-proposal-negative-probes-pass.
```

P8.13 produced:

- `tools/run_windowsutility_non_applied_proposal_negative_probes.py`
- `generated/windowsutility/p8.13-shell-workspace-non-applied-proposal-negative-probes-report.json`
- [P8.13 Shell Workspace Non-Applied Proposal Negative Probes Review](../reviews/p8.13-shell-workspace-non-applied-proposal-negative-probes-review.md)
- `generated/roadmap/p8.13-shell-workspace-non-applied-proposal-negative-probes-report.json`

The positive proposal baseline reruns, and stale binding, stale baseline, non-empty source delta, missing evidence, missing authority, target-mutating verification, target write authority, AI authority, hardware authority, productization, and self-authorization probes fail deterministically.

## P8.14 Result And Smoke Evidence Collection Plan

P8.14 result:

```text
target-write-safe smoke evidence strategy selected.
Decision: sandboxed-temp-copy-smoke-evidence-dry-run-required.
```

P8.14 produced:

- [P8.14 Shell Workspace Smoke Evidence Collection Plan](../reviews/p8.14-shell-workspace-smoke-evidence-collection-plan-review.md)
- `generated/roadmap/p8.14-shell-workspace-smoke-evidence-collection-plan-report.json`

Future smoke evidence should run only in a disposable copy or equivalent sandbox outside the original WindowsUtility target repo unless a later authority artifact grants a narrower target-write permission.

## P8.15 Result And Sandboxed Smoke Evidence

P8.15 result:

```text
sandboxed build smoke evidence passed and original target stayed unchanged.
Decision: sandboxed-build-smoke-evidence-pass-target-unchanged.
```

P8.15 produced:

- `tools/run_windowsutility_sandboxed_smoke_evidence.py`
- `generated/windowsutility/p8.15-sandboxed-smoke-evidence-report.json`
- `generated/windowsutility/p8.15-sandboxed-smoke-evidence-build.log`
- [P8.15 Shell Workspace Sandboxed Smoke Evidence Dry Run Review](../reviews/p8.15-shell-workspace-sandboxed-smoke-evidence-dry-run-review.md)
- `generated/roadmap/p8.15-shell-workspace-sandboxed-smoke-evidence-dry-run-report.json`

The sandbox build passed with exit code 0, warning count 0, and error count 0. The original WindowsUtility target remained `## main...origin/main` before and after the run.

## P8.16 Result And UI Evidence Boundary

P8.16 result:

```text
UI evidence requires a separate sandboxed feasibility probe.
Decision: sandboxed-ui-launch-feasibility-probe-required.
```

P8.16 produced:

- [P8.16 Shell Workspace UI Evidence Boundary Plan](../reviews/p8.16-shell-workspace-ui-evidence-boundary-plan-review.md)
- `generated/roadmap/p8.16-shell-workspace-ui-evidence-boundary-plan-report.json`

UI launch and screenshot evidence remain uncollected. The next safe step may launch only the sandboxed app, must terminate it cleanly, and must prove the original WindowsUtility target remains unchanged.

## P8.17 Result And Sandboxed UI Launch Probe

P8.17 result:

```text
sandboxed UI launch feasibility passed and original target stayed unchanged.
Decision: sandboxed-ui-launch-feasibility-pass-target-unchanged.
```

P8.17 produced:

- `tools/run_windowsutility_sandboxed_ui_launch_probe.py`
- `generated/windowsutility/p8.17-sandboxed-ui-launch-probe-report.json`
- `generated/windowsutility/p8.17-sandboxed-ui-launch-build.log`
- [P8.17 Shell Workspace Sandboxed UI Launch Feasibility Probe Review](../reviews/p8.17-shell-workspace-sandboxed-ui-launch-feasibility-probe-review.md)
- `generated/roadmap/p8.17-shell-workspace-sandboxed-ui-launch-feasibility-probe-report.json`

The sandboxed app launched, exposed main window title `Card Printer Utility`, responded to process observation, and closed through `CloseMainWindow`. The original WindowsUtility target remained `## main...origin/main`.

## P8.18 Result And Screenshot Evidence Boundary

P8.18 result:

```text
screenshot evidence requires sandbox-window capture only.
Decision: sandboxed-window-screenshot-evidence-probe-required.
```

P8.18 produced:

- [P8.18 Shell Workspace Screenshot Evidence Boundary Plan](../reviews/p8.18-shell-workspace-screenshot-evidence-boundary-plan-review.md)
- `generated/roadmap/p8.18-shell-workspace-screenshot-evidence-boundary-plan-report.json`

Screenshot evidence remains uncollected. The next safe step may capture only the sandboxed app window and must prove the screenshot is non-empty and the original target remains unchanged.

## P8.19 Result And Sandboxed Screenshot Evidence

P8.19 result:

```text
sandboxed screenshot evidence passed and original target stayed unchanged.
Decision: sandboxed-screenshot-evidence-pass-target-unchanged.
```

P8.19 produced:

- `tools/run_windowsutility_sandboxed_screenshot_probe.py`
- `generated/windowsutility/p8.19-sandboxed-screenshot-probe-report.json`
- `generated/windowsutility/p8.19-sandboxed-screenshot-build.log`
- `generated/windowsutility/p8.19-shell-workspace-sandboxed-window.png`
- [P8.19 Shell Workspace Sandboxed Screenshot Evidence Probe Review](../reviews/p8.19-shell-workspace-sandboxed-screenshot-evidence-probe-review.md)
- `generated/roadmap/p8.19-shell-workspace-sandboxed-screenshot-evidence-probe-report.json`

The screenshot is a valid PNG, 1320 x 820, 38739 bytes, and captures the sandboxed `Card Printer Utility` shell window. The original WindowsUtility target remained `## main...origin/main`.

## P8.20 Result And Workbench Projection Boundary

P8.20 result:

```text
shell-workspace evidence workbench projection boundary completed.
Decision: shell-workspace-evidence-workbench-projection-required.
```

P8.20 produced:

- [P8.20 Shell Workspace Evidence Workbench Projection Plan](../reviews/p8.20-shell-workspace-evidence-workbench-projection-plan-review.md)
- `generated/roadmap/p8.20-shell-workspace-evidence-workbench-projection-plan-report.json`

The future projection must connect accepted mapping, proposal, build evidence, UI launch evidence, screenshot evidence, artifact links, and authority/safety flags. It must remain report/projection state only. Source edits, target writes, proposal application, new evidence collection, AI authority, hardware authority, and productization remain unauthorized.

## P8.21 Result And Workbench Projection

P8.21 result:

```text
shell-workspace evidence workbench projection completed.
Decision: shell-workspace-evidence-workbench-projection-pass.
```

P8.21 produced:

- `tools/emit_windowsutility_workbench_projection.py`
- `generated/windowsutility/workbench/p8.21-shell-workspace-evidence-workbench-projection.json`
- `generated/windowsutility/workbench/p8.21-shell-workspace-evidence-workbench.html`
- `generated/windowsutility/workbench/p8.21-shell-workspace-evidence-workbench-validation-report.json`
- [P8.21 Shell Workspace Evidence Workbench Projection Review](../reviews/p8.21-shell-workspace-evidence-workbench-projection-review.md)
- `generated/roadmap/p8.21-shell-workspace-evidence-workbench-projection-report.json`

The projection links 10 source artifacts, 8 timeline steps, 3 evidence cards, and 6 selectable records. The static HTML preview exposes timeline, evidence, screenshot, authority, and artifact sections. Browser validation confirmed the screenshot rendered and selection details updated. Source edits, target writes, proposal application, new evidence collection, AI authority, hardware authority, and productization remain unauthorized.

## P8.22 Result And Workbench Projection Negative Probes

P8.22 result:

```text
shell-workspace workbench projection negative probes completed.
Decision: shell-workspace-workbench-negative-probes-pass.
```

P8.22 produced:

- `tools/run_windowsutility_workbench_projection_negative_probes.py`
- `generated/windowsutility/workbench/p8.22-shell-workspace-workbench-negative-probes-report.json`
- [P8.22 Shell Workspace Workbench Projection Negative Probes Review](../reviews/p8.22-shell-workspace-workbench-projection-negative-probes-review.md)
- `generated/roadmap/p8.22-shell-workspace-workbench-negative-probes-report.json`

The harness reruns the P8.21 positive baseline and proves 15 unsafe or incomplete projection states fail for expected reasons. Source edits, target writes, proposal application, new evidence collection, AI authority, hardware authority, and productization remain unauthorized.

## P8.23 Result And Workbench Usability Boundary

P8.23 result:

```text
shell-workspace workbench usability boundary completed.
Decision: shell-workspace-workbench-usability-dry-run-required.
```

P8.23 produced:

- [P8.23 Shell Workspace Workbench Usability Boundary Plan](../reviews/p8.23-shell-workspace-workbench-usability-boundary-plan-review.md)
- `generated/roadmap/p8.23-shell-workspace-workbench-usability-boundary-plan-report.json`

The next dry run must compare workbench inspection against raw JSON inspection for the same review questions. It must not claim human usability evidence unless a human reviewer participates. Source edits, target writes, proposal application, new evidence collection, AI authority, hardware authority, and productization remain unauthorized.

## P8.24 Result And Workbench Usability Dry Run

P8.24 result:

```text
shell-workspace workbench usability dry run completed.
Decision: shell-workspace-workbench-usability-dry-run-pass.
```

P8.24 produced:

- `tools/run_windowsutility_workbench_usability_dry_run.py`
- `generated/windowsutility/workbench/p8.24-shell-workspace-workbench-usability-dry-run-report.json`
- [P8.24 Shell Workspace Workbench Usability Dry Run Review](../reviews/p8.24-shell-workspace-workbench-usability-dry-run-review.md)
- `generated/roadmap/p8.24-shell-workspace-workbench-usability-dry-run-report.json`

The self-conducted dry run answered 8 of 8 review tasks, missed 0 safety boundaries, and reduced artifact lookups from 17 raw JSON lookups to 9 workbench-path lookups. This is not a human usability study. Source edits, target writes, proposal application, new evidence collection, AI authority, hardware authority, and productization remain unauthorized.

## P8.25 Result And User Workflow Benchmark Boundary

P8.25 result:

```text
WindowsUtility user workflow benchmark boundary completed.
Decision: windowsutility-user-workflow-benchmark-request-required.
```

P8.25 produced:

- [P8.25 WindowsUtility User Workflow Benchmark Boundary Plan](../reviews/p8.25-windowsutility-user-workflow-benchmark-boundary-plan-review.md)
- `generated/roadmap/p8.25-windowsutility-user-workflow-benchmark-boundary-plan-report.json`

The next benchmark must ask the user/coordinator to inspect the generated workbench and answer explicit workflow questions. A self-conducted dry run cannot become human workflow evidence without a response. Source edits, target writes, proposal application, new evidence collection, AI authority, hardware authority, and productization remain unauthorized.

## P8.26 Result And User Workflow Benchmark Request

P8.26 result:

```text
WindowsUtility user workflow benchmark request completed.
Decision: user-workflow-benchmark-response-required.
```

P8.26 produced:

- `generated/roadmap/p8.26-windowsutility-user-workflow-benchmark-request.json`
- [P8.26 WindowsUtility User Workflow Benchmark Request Review](../reviews/p8.26-windowsutility-user-workflow-benchmark-request-review.md)
- `generated/roadmap/p8.26-windowsutility-user-workflow-benchmark-request-report.json`

The benchmark result is not recorded. The next result artifact requires explicit user/coordinator response. Source edits, target writes, proposal application, new evidence collection, AI authority, hardware authority, and productization remain unauthorized.

## P8.27 Result And User Workflow Benchmark Result Record

P8.27 result:

```text
WindowsUtility user workflow benchmark result recorded.
Decision: proceed-with-next-bounded-slice.
```

P8.27 produced:

- `generated/roadmap/p8.27-windowsutility-user-workflow-benchmark-result.json`
- [P8.27 WindowsUtility User Workflow Benchmark Result Record Review](../reviews/p8.27-windowsutility-user-workflow-benchmark-result-review.md)
- `generated/roadmap/p8.27-windowsutility-user-workflow-benchmark-result-report.json`

The user/coordinator response was compact: `accept`. It is recorded as permission to proceed to the next bounded readiness slice, not as source write authority, proposal application authority, AI authority, hardware authority, or productization readiness.

Next safe work:

```text
P8.28 WindowsUtility Productization Readiness Recheck
```

## P8.28 Result And Productization Readiness Recheck

P8.28 result:

```text
WindowsUtility productization readiness recheck completed.
Decision: productization-still-blocked-product-surface-and-application-gates-required.
```

P8.28 produced:

- `generated/roadmap/p8.28-windowsutility-productization-readiness-recheck-report.json`
- [P8.28 WindowsUtility Productization Readiness Recheck](../reviews/p8.28-windowsutility-productization-readiness-recheck-review.md)

Resolved or improved since P8.0:

- target repository state
- accepted shell/workspace mapping
- non-applied proposal validation
- sandboxed build/UI/screenshot evidence
- static real-project workbench
- compact user workflow response

Remaining blockers:

- no real proposal application loop
- no first product surface decision
- no packaging/release boundary
- no detailed usability study claim
- only shell/workspace is accepted, so broad product claims remain out of scope

Next safe work:

```text
P8.29 First Product Surface Decision Boundary Plan
```

## P8.29 Result And First Product Surface Decision Boundary

P8.29 result:

```text
First product surface decision boundary completed.
Decision: select-static-local-workbench-export-first.
```

P8.29 produced:

- `generated/roadmap/p8.29-first-product-surface-decision-boundary-plan-report.json`
- [P8.29 First Product Surface Decision Boundary Plan](../reviews/p8.29-first-product-surface-decision-boundary-plan-review.md)
- Decision 012 in [Build / Borrow / Integrate Decisions](../decisions/build-borrow-integrate-decisions.md)

Selected first surface:

```text
surface.static-local-workbench-export
```

CLI report commands, local app, editor integration, GitHub workflow integration, and team workflow automation are deferred. Productization implementation remains blocked.

Next safe work:

```text
P8.30 Static Local Workbench Export Boundary
```

## P8.30 Result And Static Local Workbench Export Boundary

P8.30 result:

```text
Static local workbench export boundary completed.
Decision: static-local-workbench-export-prototype-authorized-next-slice.
```

P8.30 produced:

- `generated/roadmap/p8.30-static-local-workbench-export-boundary-report.json`
- [P8.30 Static Local Workbench Export Boundary](../reviews/p8.30-static-local-workbench-export-boundary-review.md)

The next prototype must emit only local generated artifacts and must validate manifest, projection, HTML, screenshot asset, authority flags, source digests, no network dependency, and unchanged WindowsUtility target state.

Next safe work:

```text
P8.31 Static Local Workbench Export Prototype
```

## P8.31 Result And Static Local Workbench Export Prototype

P8.31 result:

```text
Static local workbench export prototype completed.
Decision: static-local-workbench-export-prototype-passed.
```

P8.31 produced:

- `tools/emit_windowsutility_static_workbench_export.py`
- `tools/run_windowsutility_static_workbench_export_negative_probes.py`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.31/index.html`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.31/projection.json`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.31/manifest.json`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.31/assets/screenshot.png`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.31/validation-report.json`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.31/negative-probes-report.json`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.31/browser-validation-report.json`
- [P8.31 Static Local Workbench Export Prototype](../reviews/p8.31-static-local-workbench-export-prototype-review.md)
- `generated/roadmap/p8.31-static-local-workbench-export-prototype-report.json`

The prototype passed export validation, 10 negative probes, and headless Chromium browser validation. It remains a generated local artifact, not a packaged product or release.

Next safe work:

```text
P8.32 Static Local Workbench Export Productization Gate Review
```

## P8.32 Result And Static Export Productization Gate Review

P8.32 result:

```text
Static local workbench export productization gate reviewed.
Decision: static-export-ready-for-user-review-not-productized.
```

P8.32 produced:

- `generated/roadmap/p8.32-static-local-workbench-export-productization-gate-review-report.json`
- [P8.32 Static Local Workbench Export Productization Gate Review](../reviews/p8.32-static-local-workbench-export-productization-gate-review.md)

The static export may be sent to user/coordinator review. It is not ready for packaging, release, editor/GitHub integration, or product readiness claims.

Next safe work:

```text
P8.33 Static Local Workbench Export User Review Request
```

## P8.33 Result And Static Export User Review Request

P8.33 result:

```text
Static local workbench export user review requested.
Decision: static-export-user-review-response-required.
```

P8.33 produced:

- `generated/roadmap/p8.33-static-local-workbench-export-user-review-request.json`
- [P8.33 Static Local Workbench Export User Review Request](../reviews/p8.33-static-local-workbench-export-user-review-request.md)

Next safe work:

```text
P8.34 Static Local Workbench Export User Review Result Record
```

only after explicit user/coordinator response.

## P8.34 Result And Static Export User Review Result Record

P8.34 result:

```text
Static local workbench export user review recorded.
Decision: revise-static-export-orientation-before-next-review.
```

P8.34 produced:

- `generated/roadmap/p8.34-static-local-workbench-export-user-review-result.json`
- [P8.34 Static Local Workbench Export User Review Result Record](../reviews/p8.34-static-local-workbench-export-user-review-result.md)

The static export failed the comprehension test. The next revision must explain what the page is, what it represents, and what the reviewer should inspect.

Next safe work:

```text
P8.35 Static Local Workbench Export Reviewer Orientation Revision
```

## P8.35 Result And Static Export Reviewer Orientation Revision

P8.35 result:

```text
Static local workbench export reviewer orientation revised.
Decision: static-export-reviewer-orientation-revised.
```

P8.35 produced:

- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.35/index.html`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.35/projection.json`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.35/manifest.json`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.35/assets/screenshot.png`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.35/validation-report.json`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.35/negative-probes-report.json`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.35/browser-validation-report.json`
- `generated/roadmap/p8.35-static-local-workbench-export-reviewer-orientation-revision-report.json`
- [P8.35 Static Local Workbench Export Reviewer Orientation Revision](../reviews/p8.35-static-local-workbench-export-reviewer-orientation-revision.md)

Next safe work:

```text
P8.36 Static Local Workbench Export Orientation Review Request
```

## P8.36 Result And Static Export Orientation Review Request

P8.36 result:

```text
Static local workbench export orientation review requested.
Decision: static-export-orientation-review-response-required.
```

P8.36 produced:

- `generated/roadmap/p8.36-static-local-workbench-export-orientation-review-request.json`
- [P8.36 Static Local Workbench Export Orientation Review Request](../reviews/p8.36-static-local-workbench-export-orientation-review-request.md)

Next safe work:

```text
P8.37 Static Local Workbench Export Orientation Review Result Record
```

only after explicit user/coordinator response.

## P8.37 Result And Static Export Orientation Review Result Record

P8.37 result:

```text
Static local workbench export orientation review recorded.
Decision: static-export-orientation-accepted-proceed.
```

P8.37 produced:

- `generated/roadmap/p8.37-static-local-workbench-export-orientation-review-result.json`
- [P8.37 Static Local Workbench Export Orientation Review Result Record](../reviews/p8.37-static-local-workbench-export-orientation-review-result.md)

The revised static export can be treated as a reviewed product surface candidate, but it is not packaging, release, source-write authority, or productization.

Next safe work:

```text
P8.38 Static Local Workbench Export Productization Readiness Recheck
```

## P8.38 Result And Static Export Productization Readiness Recheck

P8.38 result:

```text
Productization readiness rechecked.
Decision: productization-still-blocked-source-application-packaging-release-gates-required.
```

P8.38 produced:

- `generated/roadmap/p8.38-static-local-workbench-export-productization-readiness-recheck-report.json`
- [P8.38 Static Local Workbench Export Productization Readiness Recheck](../reviews/p8.38-static-local-workbench-export-productization-readiness-recheck.md)

Next safe work:

```text
P8.39 Source Application Authority Boundary Plan
```

## P8.39 Result And Source Application Authority Boundary Plan

P8.39 result:

```text
Source application authority boundary planned.
Decision: source-application-authority-boundary-planned-report-only.
```

P8.39 produced:

- `generated/roadmap/p8.39-source-application-authority-boundary-plan-report.json`
- [P8.39 Source Application Authority Boundary Plan](../reviews/p8.39-source-application-authority-boundary-plan.md)

Next safe work:

```text
P8.40 Non-Mutating Source Application Dry-Run Boundary
```

## P8.40 Result And Non-Mutating Source Application Dry-Run Boundary

P8.40 result:

```text
Non-mutating source application dry-run boundary recorded.
Decision: non-mutating-source-application-dry-run-boundary-recorded.
```

P8.40 produced:

- `generated/roadmap/p8.40-non-mutating-source-application-dry-run-boundary-report.json`
- [P8.40 Non-Mutating Source Application Dry-Run Boundary](../reviews/p8.40-non-mutating-source-application-dry-run-boundary.md)

Next safe work:

```text
P8.41 Non-Mutating Source Application Dry-Run Prototype
```

## P8.41 Result And Non-Mutating Source Application Dry-Run Prototype

P8.41 result:

```text
Non-mutating source application dry-run prototype passed.
Decision: non-mutating-source-application-dry-run-prototype-passed.
```

P8.41 produced:

- `tools/emit_windowsutility_source_application_dry_run.py`
- `tools/run_windowsutility_source_application_dry_run_negative_probes.py`
- `generated/windowsutility/source-application-dry-run/p8.41/dry-run-request.json`
- `generated/windowsutility/source-application-dry-run/p8.41/change-set-preview.json`
- `generated/windowsutility/source-application-dry-run/p8.41/touched-file-expectation-report.json`
- `generated/windowsutility/source-application-dry-run/p8.41/evidence-plan.json`
- `generated/windowsutility/source-application-dry-run/p8.41/rollback-plan.json`
- `generated/windowsutility/source-application-dry-run/p8.41/authority-requirement-report.json`
- `generated/windowsutility/source-application-dry-run/p8.41/validation-report.json`
- `generated/windowsutility/source-application-dry-run/p8.41/negative-probes-report.json`
- `generated/roadmap/p8.41-non-mutating-source-application-dry-run-prototype-report.json`
- [P8.41 Non-Mutating Source Application Dry-Run Prototype](../reviews/p8.41-non-mutating-source-application-dry-run-prototype.md)

The user has allowed future WindowsUtility source modification, but P8.41 did not exercise that permission. The target remained unchanged and clean/aligned.

Next safe work:

```text
P8.42 Source Application Authorization Review / Minimal Source Application Gate
```

## P8.42 Result And Source Application Authorization Review

P8.42 result:

```text
Source application authorization reviewed.
Decision: minimal-source-edit-proposal-required-before-application.
```

P8.42 produced:

- `generated/roadmap/p8.42-source-application-authorization-review-report.json`
- [P8.42 Source Application Authorization Review](../reviews/p8.42-source-application-authorization-review.md)

The user source-modification permission is observed, but the current P8.12 proposal has no source patch. No WindowsUtility source files were modified.

Next safe work:

```text
P8.43 Minimal WindowsUtility Source Edit Proposal and Patch Preview
```

## P8.43 Result And Minimal Source Edit Proposal

P8.43 result:

```text
Minimal WindowsUtility source edit proposal previewed.
Decision: minimal-source-edit-proposal-previewed-not-applied.
```

P8.43 produced:

- `generated/windowsutility/source-application-proposals/p8.43/minimal-source-edit-proposal.json`
- `generated/windowsutility/source-application-proposals/p8.43/patch-preview.diff`
- `generated/windowsutility/source-application-proposals/p8.43/validation-report.json`
- `generated/roadmap/p8.43-minimal-windowsutility-source-edit-proposal-report.json`
- [P8.43 Minimal WindowsUtility Source Edit Proposal](../reviews/p8.43-minimal-windowsutility-source-edit-proposal.md)

The patch was not applied. The next slice may apply only this previewed low-risk test-automation file if WindowsUtility is still clean/aligned.

Next safe work:

```text
P8.44 Minimal WindowsUtility Source Edit Application
```

## P8.44 Result And Minimal Source Edit Application

P8.44 result:

```text
Minimal WindowsUtility source edit applied and validated.
Decision: minimal-source-edit-applied-and-validated.
```

P8.44 produced:

- `generated/windowsutility/source-application-applications/p8.44/application-report.json`
- `generated/windowsutility/source-application-applications/p8.44/applied-Invoke-IntentGraphShellWorkspacePreflight.ps1`
- `generated/roadmap/p8.44-minimal-windowsutility-source-edit-application-report.json`
- [P8.44 Minimal WindowsUtility Source Edit Application](../reviews/p8.44-minimal-windowsutility-source-edit-application.md)

WindowsUtility commit:

```text
ac5b2204442cde751f625a9979a4fdb437d468a8
```

Next safe work:

```text
P8.45 Source Application Result Review / Next Productization Gate
```

## P8.45 Result And Source Application Productization Gate

P8.45 result:

```text
Source application loop passed; productization still blocked.
Decision: source-application-loop-passed-productization-still-blocked.
```

P8.45 produced:

- `generated/roadmap/p8.45-source-application-result-productization-gate-report.json`
- [P8.45 Source Application Result Productization Gate](../reviews/p8.45-source-application-result-productization-gate.md)

Next safe work:

```text
P8.46 WindowsUtility Source Application Workbench Refresh
```

## P8.46 Result And Source Application Workbench Refresh

P8.46 result:

```text
Source application workbench refresh passed.
Decision: source-application-workbench-refresh-passed.
```

P8.46 produced:

- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.46/index.html`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.46/projection.json`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.46/manifest.json`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.46/validation-report.json`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.46/negative-probes-report.json`
- `generated/roadmap/p8.46-windowsutility-source-application-workbench-refresh-report.json`
- [P8.46 WindowsUtility Source Application Workbench Refresh](../reviews/p8.46-windowsutility-source-application-workbench-refresh.md)

Next safe work:

```text
P8.47 Productization Packaging/Release Boundary Plan
```

## P8.47 Productization Packaging/Release Boundary Plan

P8.47 result:

```text
Packaging/release boundary planned.
Decision: productization-packaging-release-boundary-planned-report-only.
```

P8.47 produced:

- `generated/roadmap/p8.47-productization-packaging-release-boundary-plan-report.json`
- [P8.47 Productization Packaging/Release Boundary Plan](../reviews/p8.47-productization-packaging-release-boundary-plan.md)

Next safe work:

```text
P8.48 Non-Mutating Packaging/Release Dry-Run Boundary
```

## P8.48 Non-Mutating Packaging/Release Dry-Run Boundary

P8.48 result:

```text
Non-mutating packaging/release dry-run boundary recorded.
Decision: non-mutating-packaging-release-dry-run-boundary-recorded.
```

P8.48 produced:

- `generated/roadmap/p8.48-non-mutating-packaging-release-dry-run-boundary-report.json`
- [P8.48 Non-Mutating Packaging/Release Dry-Run Boundary](../reviews/p8.48-non-mutating-packaging-release-dry-run-boundary.md)

Next safe work:

```text
P8.49 Non-Mutating Packaging/Release Dry-Run Prototype
```

## P8.49 Non-Mutating Packaging/Release Dry-Run Prototype

P8.49 result:

```text
Non-mutating packaging/release dry-run prototype passed.
Decision: non-mutating-packaging-release-dry-run-prototype-passed.
```

P8.49 produced:

- `tools/emit_windowsutility_packaging_release_dry_run.py`
- `tools/run_windowsutility_packaging_release_dry_run_negative_probes.py`
- `generated/windowsutility/packaging-release-dry-run/p8.49/validation-report.json`
- `generated/windowsutility/packaging-release-dry-run/p8.49/negative-probes-report.json`
- `generated/roadmap/p8.49-non-mutating-packaging-release-dry-run-prototype-report.json`
- [P8.49 Non-Mutating Packaging/Release Dry-Run Prototype](../reviews/p8.49-non-mutating-packaging-release-dry-run-prototype.md)

Next safe work:

```text
P8.50 Packaging/Release Dry-Run Result Review / Next Productization Gate
```

## P8.50 Packaging/Release Dry-Run Result Review

P8.50 result:

```text
Packaging/release dry-run passed; productization still blocked.
Decision: packaging-release-dry-run-passed-productization-still-blocked.
```

P8.50 produced:

- `generated/roadmap/p8.50-packaging-release-dry-run-result-productization-gate-report.json`
- [P8.50 Packaging/Release Dry-Run Result Productization Gate](../reviews/p8.50-packaging-release-dry-run-result-productization-gate.md)

Next safe work:

```text
P8.51 Packaging/Release Dry-Run Workbench Refresh
```

## P8.51 Packaging/Release Dry-Run Workbench Refresh

P8.51 result:

```text
Packaging/release dry-run workbench refresh passed.
Decision: packaging-release-dry-run-workbench-refresh-passed.
```

P8.51 produced:

- `generated/windowsutility/workbench/p8.51-packaging-release-workbench-projection.json`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.51/index.html`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.51/validation-report.json`
- `generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.51/negative-probes-report.json`
- `generated/roadmap/p8.51-packaging-release-dry-run-workbench-refresh-report.json`
- [P8.51 Packaging/Release Dry-Run Workbench Refresh](../reviews/p8.51-packaging-release-dry-run-workbench-refresh.md)

Next safe work:

```text
P8.52 Productization Readiness Recheck After Packaging/Release Dry-Run
```

## P8.52 Productization Readiness Recheck After Packaging/Release Dry-Run

P8.52 result:

```text
Productization readiness improved; productization still blocked.
Decision: productization-still-blocked-package-release-authority-required.
```

P8.52 produced:

- `generated/roadmap/p8.52-productization-readiness-recheck-after-packaging-release-dry-run-report.json`
- [P8.52 Productization Readiness Recheck After Packaging/Release Dry-Run](../reviews/p8.52-productization-readiness-recheck-after-packaging-release-dry-run.md)

Next safe work:

```text
P8.53 Package Artifact Creation Authorization Request
```

## P8.53 Package Artifact Creation Authorization Request

P8.53 result:

```text
Package artifact creation authorization requested.
Decision: package-artifact-creation-authorization-requested-not-recorded.
```

P8.53 produced:

- `generated/roadmap/p8.53-package-artifact-creation-authorization-request.json`
- [P8.53 Package Artifact Creation Authorization Request](../reviews/p8.53-package-artifact-creation-authorization-request.md)

Next safe work:

```text
Wait for user/coordinator response, then record P8.54 Package Artifact Creation Authorization Result.
```

## P8.54 Package Artifact Creation Authorization Result Record

P8.54 result:

```text
Decision: sandboxed-package-artifact-creation-authorized-for-local-validation-only.
```

P8.54 produced:

- `generated/roadmap/p8.54-package-artifact-creation-authorization-result.json`
- [P8.54 Package Artifact Creation Authorization Result Record](../reviews/p8.54-package-artifact-creation-authorization-result.md)

Next safe work:

```text
P8.55 Sandboxed Package Artifact Creation Probe
```

Still blocked:

- WindowsUtility source mutation, commit, or push
- installer creation
- artifact signing
- credential access
- provider API calls
- release tag creation
- release publishing
- productization authority

## P8.55 Sandboxed Package Artifact Creation Probe

P8.55 result:

```text
Decision: sandboxed-package-artifact-created-and-validated-productization-still-blocked.
```

P8.55 produced:

- `generated/roadmap/p8.55-sandboxed-package-artifact-creation-probe-report.json`
- `generated/windowsutility/package-artifact/p8.55/package-artifact-probe-report.json`
- `generated/windowsutility/package-artifact/p8.55/validation-report.json`
- `generated/windowsutility/package-artifact/p8.55/negative-probes-report.json`
- `generated/windowsutility/package-artifact/p8.55/package-manifest.json`
- `generated/windowsutility/package-artifact/p8.55/windowsutility-shell-workspace-p8.55-sandbox-package.zip`
- [P8.55 Sandboxed Package Artifact Creation Probe](../reviews/p8.55-sandboxed-package-artifact-creation-probe.md)

Next safe work:

```text
P8.56 Packaged Artifact Verification Boundary
```

Still blocked:

- packaged artifact verification beyond zip readability
- installer creation
- artifact signing
- credential access
- provider API calls
- release tag creation
- release publishing
- user acceptance of package candidate
- productization authority

## P8.56 Packaged Artifact Verification Boundary

P8.56 result:

```text
Decision: packaged-artifact-verification-boundary-recorded-execution-not-authorized.
```

P8.56 produced:

- `generated/roadmap/p8.56-packaged-artifact-verification-boundary-report.json`
- [P8.56 Packaged Artifact Verification Boundary](../reviews/p8.56-packaged-artifact-verification-boundary.md)

## P8.57 Approval Workbench Graph Delta Visualization Requirement Record

P8.57 result:

```text
Decision: approval-workbench-must-show-interactive-graph-delta-and-diff-before-further-approval-gates.
```

P8.57 produced:

- `generated/roadmap/p8.57-approval-workbench-graph-delta-visualization-requirement-report.json`
- [P8.57 Approval Workbench Graph Delta Visualization Requirement Record](../reviews/p8.57-approval-workbench-graph-delta-visualization-requirement.md)

Next safe work:

```text
P8.58 Graph Delta Approval Workbench Boundary Plan
```

## P8.58 Graph Delta Approval Workbench Boundary Plan

P8.58 result:

```text
Decision: graph-delta-approval-workbench-boundary-ready-for-projection-schema.
```

P8.58 produced:

- `generated/roadmap/p8.58-graph-delta-approval-workbench-boundary-plan-report.json`
- [P8.58 Graph Delta Approval Workbench Boundary Plan](../reviews/p8.58-graph-delta-approval-workbench-boundary-plan.md)

Next safe work:

```text
P8.59 Graph Delta Approval Workbench Projection Schema
```

## P8.59 Graph Delta Approval Workbench Projection Schema

P8.59 result:

```text
Decision: graph-delta-approval-workbench-projection-schema-emitted-and-validated.
```

P8.59 produced:

- `tools/emit_graph_delta_approval_workbench_projection.py`
- `generated/windowsutility/graph-delta-approval-workbench/p8.59/projection.json`
- `generated/windowsutility/graph-delta-approval-workbench/p8.59/validation-report.json`
- `generated/roadmap/p8.59-graph-delta-approval-workbench-projection-schema-report.json`
- [P8.59 Graph Delta Approval Workbench Projection Schema](../reviews/p8.59-graph-delta-approval-workbench-projection-schema.md)

Next safe work:

```text
P8.60 Static Graph Delta Approval Workbench Prototype
```

## P8.60 Static Graph Delta Approval Workbench Prototype

P8.60 result:

```text
Decision: static-graph-delta-approval-workbench-prototype-emitted-and-validated.
```

P8.60 produced:

- `tools/emit_graph_delta_approval_workbench_static_html.py`
- `generated/product-surfaces/graph-delta-approval-workbench/p8.60/index.html`
- `generated/product-surfaces/graph-delta-approval-workbench/p8.60/projection.json`
- `generated/product-surfaces/graph-delta-approval-workbench/p8.60/manifest.json`
- `generated/product-surfaces/graph-delta-approval-workbench/p8.60/validation-report.json`
- `generated/roadmap/p8.60-static-graph-delta-approval-workbench-prototype-report.json`
- [P8.60 Static Graph Delta Approval Workbench Prototype](../reviews/p8.60-static-graph-delta-approval-workbench-prototype.md)

P8.60 includes structural support for graph movement, wheel zoom, toolbar zoom-in, toolbar zoom-out, fit, semantic zoom readability, selected node/edge inspection, selected code-node code diff, and changed node/edge graph diff inspection.

Next safe work:

```text
P8.61 Static Graph Delta Approval Workbench Visual/Interaction Dry Run
```

## P8.61 Static Graph Delta Approval Workbench Visual/Interaction Dry Run Attempt

P8.61 result:

```text
Decision: visual-interaction-dry-run-not-complete-user-observed-or-allowed-browser-review-required.
```

P8.61 produced:

- `generated/roadmap/p8.61-static-graph-delta-approval-workbench-visual-interaction-dry-run-attempt-report.json`
- [P8.61 Static Graph Delta Approval Workbench Visual/Interaction Dry Run Attempt](../reviews/p8.61-static-graph-delta-approval-workbench-visual-interaction-dry-run-attempt.md)

The graph page loaded through local HTTP, but browser policy blocked automated interaction before pan, zoom, selected node/edge inspector, code diff, changed graph diff, and Graphify-grade inspectability could be verified.

Next safe work:

```text
P8.62 User-Observed Graph Delta Approval Workbench Review Request
```

## P8.62 User-Observed Graph Delta Approval Workbench Review Request

P8.62 result:

```text
Decision: user-observed-graph-delta-approval-workbench-review-requested.
```

P8.62 produced:

- `generated/roadmap/p8.62-user-observed-graph-delta-approval-workbench-review-request.json`
- [P8.62 User-Observed Graph Delta Approval Workbench Review Request](../reviews/p8.62-user-observed-graph-delta-approval-workbench-review-request.md)

Next safe work:

```text
Wait for coordinator review response.
```
