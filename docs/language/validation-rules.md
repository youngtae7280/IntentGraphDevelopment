# GraphIR Validation Rules

M1 defined validation rules but did not implement them. P1.R reframes them around semantic overlay state: code nodes are references/facts, not code text, and generated-code rules apply only when a generated-code mode is declared.

## V500: B1 Code Fact Schema Validation

Status: added in P2.0.

B1 code fact reports must use exact role/status/scope values:

- `artifactRole: intentgraph-code-facts`
- `status: intentgraph-code-facts-extracted`
- `scope: b1-typescript-rest-api-code-facts`

Every fact must include source file, source digest, extractor id, extractor version, confidence, and source location or explicit source location status.

Allowed fact kinds are:

- `file`
- `module`
- `function`
- `type`
- `route`
- `test`
- `import`
- `call`

Allowed relation kinds are:

- `contains`
- `imports`
- `references`
- `calls`
- `handles_route`
- `tests`
- `depends_on`

Every relation endpoint must resolve to an endpoint fact. Source text must not be embedded as authority. The extractor must declare deterministic output and must not claim broad extraction.

Validation command:

```bash
python tools/validate_b1_code_facts.py --code-facts generated/b1-typescript-rest-api/code-facts.json --source-root docs/examples/b1-typescript-rest-api/source --out generated/b1-typescript-rest-api/code-facts-validation-report.json
```

## V501: B1 Code Fact Negative Probes

Status: added in P2.0.

B1 must maintain repeatable negative probes for wrong role, unknown fact kind, unknown relation kind, missing endpoint, missing provenance, stale source digest, source text leakage, broad extractor claims, missing location metadata, and nondeterministic extractor claims.

Validation command:

```bash
python tools/run_b1_code_fact_negative_probes.py --out generated/b1-typescript-rest-api/p2.0-code-fact-negative-probes-report.json
```

## V502: B1 Incremental Code Fact Change Verification

Status: added in P2.1.

B1 incremental code fact changes must declare:

- exact changed source files
- exact unchanged source files
- expected added/removed/changed fact ids
- expected added/removed/changed relation ids
- claim-scope flags proving no broad extractor, Intent mapping, workbench, or AI authority claim

The verifier must compare before/after code facts and fail if:

- the changed source file set differs
- more than one source file changes when exactly one is declared
- unchanged source file digests or file-local facts change
- added/removed/changed facts differ from the declaration
- added/removed/changed relations differ from the declaration
- forbidden claim-scope flags are true

Validation command:

```bash
python tools/verify_b1_incremental_change.py --delta docs/examples/b1-typescript-rest-api/deltas/p2.1-add-complete-todo.delta.json --before-code-facts generated/b1-typescript-rest-api/p2.1-before-code-facts.json --after-code-facts generated/b1-typescript-rest-api/p2.1-after-code-facts.json --out generated/b1-typescript-rest-api/p2.1-incremental-change-report.json
```

## V503: B1 Incremental Negative Probes

Status: added in P2.1.

B1 must maintain repeatable negative probes for wrong changed-source declaration, missing added fact, missing changed fact, unexpected removed fact, missing added relation, Intent mapping claim, and workbench claim.

Validation command:

```bash
python tools/run_b1_incremental_negative_probes.py --out generated/b1-typescript-rest-api/p2.1-incremental-negative-probes-report.json
```

## V600: B1 Intent Mapping Verification

Status: added in P3.0.

B1 Intent mapping overlays must use exact role/status/scope values:

- `artifactRole: intentgraph-b1-overlay`
- `status: intentgraph-b1-overlay-declared`
- `scope: b1-typescript-rest-api-intent-mapping`

Every resolved Intent Unit must include non-empty `codeRefs`, `codeFactRefs`, and `mappingObligations`. Code refs must be `reference-only`. Code fact refs must point to existing B1 code facts and match `expectedFactKind`. Mapping obligations must resolve code ref ids, code fact ref ids, verification ids, evidence ids, and authority ids.

The verifier must reject:

- source text contained in a unit
- source text equality requirements
- missing code facts
- wrong expected fact kind
- missing mapping obligation refs
- missing evidence, authority, or verification refs
- resolved units with ambiguity
- AI authority claims
- automatic mapping claims

Validation command:

```bash
python tools/verify_b1_intent_mapping.py --overlay docs/examples/b1-typescript-rest-api/intentgraph.overlay.json --code-facts generated/b1-typescript-rest-api/code-facts.json --out generated/b1-typescript-rest-api/p3.0-intent-mapping-report.json
```

## V601: B1 Intent Mapping Negative Probes

Status: added in P3.0.

B1 must maintain repeatable negative probes for missing code fact, wrong expected fact kind, missing obligation ref, missing evidence, missing authority, source text equality, code text containment, ambiguous resolved mapping, AI authority, and automatic mapping claims.

Validation command:

```bash
python tools/run_b1_intent_mapping_negative_probes.py --out generated/b1-typescript-rest-api/p3.0-intent-mapping-negative-probes-report.json
```

## V602: B1 Stale Intent Mapping Probe

Status: added in P3.1.

B1 must prove that accepted mappings fail deterministically when a mapped code fact disappears from the supplied code facts.

The stale probe removes `fact.function.addtodo` from a copied code fact report and verifies that mapping references from `unit.behavior.create-todo` and `unit.route.post-todos` fail.

Validation command:

```bash
python tools/run_b1_stale_mapping_probe.py --stale-code-facts generated/b1-typescript-rest-api/p3.1-stale-code-facts.json --stale-verifier-report generated/b1-typescript-rest-api/p3.1-stale-mapping-verifier-report.json --out generated/b1-typescript-rest-api/p3.1-stale-mapping-probe-report.json
```

## V603: B1 Ambiguous Mapping Candidate Verification

Status: added in P3.2.

B1 mapping candidates must remain separate from accepted overlay mappings until a later authority flow accepts or rejects them. In P3.2, ambiguous candidates must be visible and unresolved.

The verifier rejects:

- accepted candidates
- `accepted-by-authority` status
- missing ambiguity
- missing candidate facts
- AI-generated claims
- authority-granted claims
- accepted-into-overlay claims

Validation commands:

```bash
python tools/verify_b1_mapping_candidates.py --candidates docs/examples/b1-typescript-rest-api/mapping-candidates/p3.2-ambiguous-mutate-todo.candidates.json --code-facts generated/b1-typescript-rest-api/code-facts.json --out generated/b1-typescript-rest-api/p3.2-mapping-candidates-report.json
python tools/run_b1_mapping_candidate_negative_probes.py --out generated/b1-typescript-rest-api/p3.2-mapping-candidate-negative-probes-report.json
```

## V604: Phase C Boundary Review Before Change Planning

Status: added in P3.3.

Phase D change planning must not open until Phase C evidence has been reviewed in a written boundary report. The report must review static accepted mappings, stale mapping failure, ambiguous mapping candidates, AI-authority boundaries, and implementation non-goals.

The first Phase D slice must be proposal-only. It must define a change proposal schema, exact baseline binding, required tests, evidence, and authority, and negative probes for unsafe proposals before any source mutation or patch application is allowed.

## V700: B1 Non-Applied Change Proposal Validation

Status: added in P4.0.

B1 change proposals must use exact role/status/scope values:

- `artifactRole: intentgraph-b1-change-proposal`
- `status: intentgraph-b1-change-proposal-proposed`
- `scope: b1-typescript-rest-api-change-proposal-non-applied`
- `proposalMode: non-applied-plan`
- `applicationStatus: not-applied`

The proposal must bind to exact code fact and source baselines, keep planned source changes inside declared impact scope, declare planned `DeltaC`, `DeltaI`, and `DeltaM`, require tests/evidence/authority before acceptance, and keep source mutation, patch application, AI authority, self-authorization, broad planner, workbench, and productization claims false.

Validation commands:

```bash
python tools/validate_b1_change_proposal.py --proposal docs/examples/b1-typescript-rest-api/proposals/p4.0-complete-todo-route.proposal.json --code-facts generated/b1-typescript-rest-api/code-facts.json --overlay docs/examples/b1-typescript-rest-api/intentgraph.overlay.json --out generated/b1-typescript-rest-api/p4.0-change-proposal-validation-report.json
python tools/run_b1_change_proposal_negative_probes.py --out generated/b1-typescript-rest-api/p4.0-change-proposal-negative-probes-report.json
```

## V701: Phase D Boundary Review Before Consistency Verification

Status: added in P4.1.

Phase E consistency verification must not open until Phase D proposal evidence has been reviewed in a written boundary report. The report must review proposal schema, non-applied proposal artifact, baseline binding, declared `DeltaC`/`DeltaI`/`DeltaM`, required tests, required evidence, required authority, unsafe proposal negative probes, and implementation non-goals.

The first Phase E slice must be deterministic and non-applied. It may verify consistency of proposal artifacts, code facts, overlay mappings, evidence requirements, and authority requirements, but it must not mutate source, apply patches, accept proposals, or use AI judgment as verifier.

## V800: B1 Proposal Consistency Verification

Status: added in P5.0.

B1 proposal consistency reports must consume the non-applied proposal, the proposal validation report, B1 code facts, and B1 overlay. They must pass only when the proposal validation report passes, proposal ids match, baselines match current code facts, impacted existing Intent Units are resolved, planned changes stay non-applied and inside scope, mapping updates are declared, required tests/evidence/authority exist, and forbidden authority/application claims remain false.

Validation commands:

```bash
python tools/verify_b1_proposal_consistency.py --proposal docs/examples/b1-typescript-rest-api/proposals/p4.0-complete-todo-route.proposal.json --proposal-validation generated/b1-typescript-rest-api/p4.0-change-proposal-validation-report.json --code-facts generated/b1-typescript-rest-api/code-facts.json --overlay docs/examples/b1-typescript-rest-api/intentgraph.overlay.json --out generated/b1-typescript-rest-api/p5.0-proposal-consistency-report.json
python tools/run_b1_proposal_consistency_negative_probes.py --out generated/b1-typescript-rest-api/p5.0-proposal-consistency-negative-probes-report.json
```

## V801: Phase E Boundary Review Before Workbench Projection

Status: added in P5.1.

Phase F workbench work must not open until Phase E consistency evidence has been reviewed in a written boundary report. The report must state projection inputs, visible workflow state, selection expectations, screenshot or HTML validation expectations, and non-goals.

The first Phase F slice must make deterministic reports inspectable. It must not claim that visualization verifies correctness, and it must not mutate source, apply proposals, accept proposals, or productize the workflow.

## V900: B1 Workbench Projection Is Non-Authoritative

Status: added in P6.0.

B1 workbench projection must consume deterministic source artifacts and verifier reports. It may expose proposal state, impacted files, Intent Units, code facts, planned deltas, tests, evidence, authority, and verifier status, but it must not claim visualization verifies correctness.

Validation commands:

```bash
python tools/emit_b1_workbench_projection.py --proposal docs/examples/b1-typescript-rest-api/proposals/p4.0-complete-todo-route.proposal.json --proposal-validation generated/b1-typescript-rest-api/p4.0-change-proposal-validation-report.json --consistency generated/b1-typescript-rest-api/p5.0-proposal-consistency-report.json --code-facts generated/b1-typescript-rest-api/code-facts.json --overlay docs/examples/b1-typescript-rest-api/intentgraph.overlay.json --projection-out generated/b1-typescript-rest-api/workbench/p6.0-workbench-projection.json --html-out generated/b1-typescript-rest-api/workbench/p6.0-workbench-preview.html --validation-out generated/b1-typescript-rest-api/workbench/p6.0-workbench-validation-report.json
```

## V901: Phase F Boundary Review Before Real-Project Adoption

Status: added in P6.1.

Phase G real-project adoption must not open until Phase F workbench evidence has been reviewed in a written boundary report. The first Phase G slice must be plan-only and must define target, task class, retrofit scope, performance benchmark, workflow benchmark, quality comparison criteria, rollback, and stop conditions before any real-project mutation.

## V1000: Real-Project Adoption Starts Read-Only

Status: added in P7.0.

The first real-project adoption target must be selected through a plan-only report. If the target repository is dirty, ahead of origin, or contains untracked adoption artifacts, the next slice must remain read-only and emit artifacts outside the target repository unless the user explicitly authorizes target writes.

## V1001: WindowsUtility Read-Only Inventory Boundary

Status: added in P7.1.

WindowsUtility inventory must write artifacts outside the WindowsUtility target repository unless target writes are explicitly authorized. The inventory report must record target git status before and after, selected file digest stability, write authorization, whether artifacts were written inside the target, and whether target source mutation occurred.

## V1002: Read-Only Mapping Hypotheses Are Not Accepted Mappings

Status: added in P7.2.

WindowsUtility read-only mapping hypotheses must remain explicitly unaccepted. The report must include candidate units, ambiguity records, evidence gaps, authority gaps, target git status stability, and false claims for target mutation, AI authority, and product readiness.

## V1003: Productization Requires Real Adoption Evidence

Status: added in P7.3.

Phase H must not package or release the workflow unless real-project adoption evidence includes accepted mappings, a real proposal/application loop or a documented substitute, executed evidence/authority workflow, target repository readiness, user workflow benchmark, and product surface readiness. If those are absent, Phase H may open only for a readiness gap report.

## V1004: Productization Gap Reports Must Not Become Productization

Status: added in P8.0.

A productization readiness gap report may define checklists, blockers, stabilization tracks, and future entry criteria. It must not create installable packages, release artifacts, editor integrations, GitHub workflow integrations, team automation, target source mutations, AI authority, or product readiness claims. If any checklist item is absent, the report must keep `productizationAuthorized:false` or equivalent blocked status.

## V1005: Dirty Real-Project Targets Require Explicit Resolution

Status: added in P8.1.

If a selected real-project target is ahead of origin, dirty, or has untracked control artifacts, adoption must remain read-only until the state is explicitly resolved or scoped. The orchestrator must not clean, delete, commit, push, or treat the dirty state as baseline without an explicit resolution record. Accepted mappings, target writes, proposal application, and productization remain blocked until this boundary is satisfied.

## V1006: Accepted Real-Project Mappings Need Evidence And Authority Boundaries

Status: added in P8.2.

A real-project mapping hypothesis may become accepted only when the accepted mapping artifact records selected hypothesis id, Intent Unit id, source refs, source digest baseline, ambiguity disposition, evidence requirements, authority requirements, and deterministic stale/missing mapping failure probes. Accepted mappings must not imply target write authority, proposal application authority, AI authority, productization, source text equality, or hidden generated-code snapshots.

## V1007: Candidate Selection Is Not Mapping Acceptance

Status: added in P8.3.

Selecting a real-project mapping candidate must keep the mapping unaccepted unless an accepted-mapping artifact is explicitly emitted and validated. Candidate selection may record rationale, refs, evidence requirements, and authority requirements, but it must keep target writes, proposal application, AI authority, and productization false.

## V1008: Mapping Drafts Must Stay Outside Dirty Targets

Status: added in P8.4.

When a real-project target state is unresolved, a mapping draft may record read-only source refs and digests only if the artifact is written outside the target repository and keeps `accepted:false`, `baselineAccepted:false`, and target write authority false. The draft must list stale/missing mapping probes as required before acceptance.

## V1009: Mapping Draft Negative Probes Are Required Before Acceptance

Status: added in P8.5.

A real-project mapping draft must not become accepted until a repeatable verifier proves the positive baseline and deterministic negative failures for stale source digest, missing source ref, accidental acceptance, target write authority, and baseline acceptance. The negative-probe report must keep accepted mapping, target writes, proposal application, AI authority, and productization false.

## V1010: Target-State Cleanup Must Preserve Evidence

Status: added in P8.6.

When resolving a dirty real-project target, existing commits may be pushed only when that is the selected resolution path, and untracked control artifacts must be archived or otherwise preserved before removal. The final report must record final `HEAD`, `origin/main`, clean/aligned status, archive location or equivalent preservation record, and must not auto-create accepted mappings, proposal application authority, AI authority, or productization authority.

## V1011: Readiness To Request Acceptance Is Not Acceptance

Status: added in P8.7.

A mapping acceptance readiness report may state that a mapping is ready for human acceptance request only if the target baseline is clean/aligned or explicitly scoped, selected refs resolve, positive verification passes, negative probes pass, and evidence/authority requirements are declared. It must keep the mapping unaccepted and keep target writes, proposal application, AI authority, and productization false until explicit human acceptance is recorded in a later artifact.

## V1012: Human Acceptance Requests Are Not Human Acceptance

Status: added in P8.8.

A human acceptance request may ask the user/coordinator to accept a mapping, but it must keep `recorded:false` and `accepted:false` until the user explicitly answers. Even after acceptance, source edits, proposal application, target writes, AI authority, and productization remain separate authority decisions.

## V1013: Accepted Mappings Do Not Grant Write Authority

Status: added in P8.9.

An accepted real-project mapping may set mapping acceptance true only after explicit human acceptance is recorded. The accepted mapping verifier must re-check selected source refs and target baseline state. Accepted mapping creation must not grant target writes, proposal application, AI authority, or productization.

## V1014: Accepted Mapping Negative Probes Are Required Before Proposals

Status: added in P8.10.

Before an accepted real-project mapping can be used as the basis for non-applied proposal work, a repeatable negative-probe harness must prove deterministic failure for stale source digest, missing source ref, missing or rejected human acceptance, accidental unacceptance, target write authority, and productization authority. The harness must keep proposal application and AI authority false.

## V1015: Non-Applied Proposal Boundaries Must Keep Apply Authority False

Status: added in P8.11.

A real-project non-applied proposal boundary may define proposal shape, evidence requirements, authority requirements, rollback/stop conditions, and deterministic verification plans. It must keep source edits, target writes, apply authority, AI authority, and productization false unless a later explicit authority artifact grants a narrower permission.

## V1016: Real-Project Non-Applied Proposals Must Bind To Accepted Mapping Baselines

Status: added in P8.12.

A real-project non-applied proposal must bind to an accepted mapping artifact, the accepted mapping verification report, the target baseline HEAD/origin, and the accepted code-surface refs. It must keep planned source changes empty when the proposal class is evidence-only, declare required evidence and required authority, and fail if it claims source mutation, target writes, AI authority, hardware action authority, or productization.

## V1017: Non-Applied Proposal Validators Need Repeatable Negative Probes

Status: added in P8.13.

Before a real-project non-applied proposal can be used for evidence collection planning, a repeatable negative-probe harness must prove deterministic rejection for stale accepted mapping bindings, stale target baselines, non-empty source deltas, missing evidence, missing authority, target-mutating verification steps, target write authority, AI authority, hardware authority, productization authority, and self-authorization.

## V1018: Smoke Evidence Must Avoid Writes To The Original Target Repo

Status: added in P8.14.

Real-project smoke evidence collection must not run build, launch, or screenshot workflows in a way that writes generated files to the original target repo unless a later explicit authority artifact grants that narrow permission. When build/runtime output is needed, the preferred path is a disposable copy or equivalent sandbox outside the target repo, followed by a post-check proving the original target remains clean and aligned.

## V1019: Sandboxed Evidence Runs Must Prove Target Unchanged

Status: added in P8.15.

A sandboxed real-project evidence run must record target status, HEAD, and origin/main before and after the run, verify accepted source refs inside the sandbox, keep writes confined to the sandbox, and emit command logs. The run must fail if the original target status or refs change, if accepted refs do not match the baseline, or if the sandbox command fails.

## V1020: UI Evidence Requires A Separate Launch Boundary

Status: added in P8.16.

UI evidence for a real-project target must not be conflated with build evidence or productization. Before launching a UI, the boundary must require sandbox-only launch paths, clean process termination, no hardware/device actions, no original-target writes, optional screenshot capture with an explicit unavailable reason when skipped, and an original target post-check.

## V1021: Sandboxed UI Launch Probes Must Close Observed Processes

Status: added in P8.17.

A sandboxed UI launch probe must build and launch only from the sandbox, record process id, process/window observation, termination method, and original target before/after state. The probe must fail if the app exits before the observation window, if the process cannot be observed, if it cannot be closed or killed, if the sandbox refs are stale, or if the original target changes.

## V1022: Screenshot Evidence Must Target The Sandboxed App Window

Status: added in P8.18.

Screenshot evidence for a real-project UI must capture only the sandboxed app window, write artifacts outside the original target repo, validate that the screenshot is non-empty, terminate the app, and prove the original target repo is unchanged. If a screenshot cannot be captured safely, the report must record an explicit unavailable reason instead of silently passing.

## V1023: Screenshot Probe Reports Must Validate PNG Artifacts

Status: added in P8.19.

A screenshot evidence probe report must record screenshot path, byte length, dimensions, digest, process/window observation, process termination, and original target before/after state. The probe must fail if the PNG is missing, invalid, unexpectedly small, or if the original target changes.

## V1024: Real-Project Evidence Workbench Projection Needs A Boundary Plan

Status: added in P8.20.

A real-project evidence workbench projection must not be implemented until a boundary plan lists the required input artifacts, visible workflow sections, artifact link fields, safety flags, and future validation criteria. The plan must keep source edits, target writes, proposal application, new evidence collection, app launch, screenshot capture, AI authority, hardware authority, and productization unauthorized unless a later explicit authority artifact grants a narrower permission.

The projection must be report/projection state only. It must not hide missing evidence, convert visualization into accepted graph authority, or claim product readiness.

## V1025: Real-Project Evidence Workbench Projections Must Preserve Authority Boundaries

Status: added in P8.21.

A real-project evidence workbench projection must link accepted mapping, proposal, build evidence, UI launch evidence, screenshot evidence, source artifact digests, selection records, and authority/safety flags. It must validate that required artifacts exist, linked evidence passed, screenshot linkage is visible, the proposal remains non-applied, and the current target remains clean/aligned.

The projection and preview must keep visualization/report state separate from correctness, acceptance, source mutation, target mutation, proposal application, AI authority, hardware authority, new evidence collection, and productization. Browser validation must prove the static preview is nonblank, has navigation and selectable records, exposes authority flags, and renders the screenshot path when screenshot evidence is present.

## V1026: Workbench Projection Negative Probes Are Required Before Expansion

Status: added in P8.22.

A real-project workbench projection must have repeatable negative probes before the workbench expands to richer UI, new accepted mappings, productization, or user workflow benchmarks. The harness must rerun the positive projection baseline and then prove deterministic failures for unsafe authority flags, productization claims, source mutation claims, applied proposal claims, failed evidence, missing screenshot linkage, invalid screenshot evidence, dirty or stale target state, missing selection records, missing source artifacts, missing artifact digests, missing critical HTML markers, and missing screenshot files.

The harness must keep bad fixtures temporary and must not mutate the real-project target.

## V1027: Workbench Usability Needs A Review Boundary

Status: added in P8.23.

Before a real-project workbench expands into richer UI or productization, a usability boundary must define the review tasks, comparison baseline, metrics, pass criteria, and blockers. The evaluation must compare the workbench path against direct raw JSON inspection for the same questions and must not claim a human usability study unless a human reviewer actually participates.

The workbench may not pass this boundary if reviewers cannot find proposal application status, target unchanged state, screenshot evidence, safety false flags, artifact links, and recommended next action without falling back to the full raw artifact set.

## V1028: Workbench Usability Dry Runs Must Distinguish Self-Conducted Evidence

Status: added in P8.24.

A workbench usability dry run may be self-conducted only if it explicitly says no human usability study is claimed. It must evaluate the same review questions through the workbench path and the raw JSON path, record task correctness, missed safety-boundary count, artifact lookup counts, screenshot evidence discovery, target unchanged discovery, proposal non-applied discovery, and whether productization or mutation claims were introduced.

It may pass only when the workbench answers all required tasks, misses no safety false flags, finds screenshot and target/proposal state, uses fewer artifact lookups than raw JSON, and keeps source mutation, target mutation, proposal application, AI authority, hardware authority, and productization false.

## V1029: User Workflow Benchmarks Require A Request Boundary

Status: added in P8.25.

Before a real-project workflow benchmark is recorded as user evidence, a boundary plan must define participant, mode, benchmark materials, user tasks, metrics, pass criteria, stop conditions, and non-goals. The benchmark request must make clear that source edits, proposal application, target writes, hardware actions, AI authority, and productization are not authorized by the benchmark.

A self-conducted dry run cannot be upgraded into human workflow evidence without an explicit user/coordinator response.

## V1030: User Workflow Benchmark Requests Are Not Results

Status: added in P8.26.

A user workflow benchmark request may list materials, questions, allowed responses, and response-recording requirements, but it must not record a benchmark result until the user/coordinator explicitly responds. The request must keep source edits, proposal application, target writes, new evidence collection, AI authority, hardware authority, and productization unauthorized.

The next result artifact must cite the request artifact and the exact user/coordinator response.

## Rule Severity

| Severity | Meaning |
|---|---|
| P0 | invalid graph; cannot be mapped, verified, generated, reconstructed, or reviewed |
| P1 | major correctness gap; milestone cannot pass until fixed |
| P2 | meaningful quality issue; fix or write a defer decision |
| P3 | optional polish |

## Required M1 Rules

### V001 - Required Top-Level Fields

Severity: P0

GraphIR documents must include `graphirVersion`, `graphId`, `benchmarkId`, `title`, `status`, `nodes`, `edges`, and `projections`.

GraphIR v0.2 documents must also include `intentUnits` and `unitEdges`.

### V002 - Supported Version

Severity: P0

M1 supports `graphirVersion: "0.1.0"`.

P1.1 supports `graphirVersion: "0.2.0"` for the overlay-mapped B0 fixture.

### V010 - Unique IDs

Severity: P0

All node IDs must be unique. All edge IDs must be unique. A node and edge may not share an ID.

### V011 - Stable ID Format

Severity: P1

IDs should use lowercase dot-separated names with hyphens only inside a segment when needed. IDs must not depend on array position or generated timestamps.

### V020 - Known Node Kinds

Severity: P0

Every node kind must be one of the M1 node kinds declared in `docs/language/graphir-boundary.md`.

### V021 - Known Edge Kinds

Severity: P0

Every edge kind must be one of the M1 edge kinds declared in `docs/language/graphir-boundary.md`.

### V030 - Edge Endpoint Integrity

Severity: P0

Every edge `from` and `to` value must reference an existing node ID.

### V031 - Edge Domain Rules

Severity: P1

Edges must respect the from/to node kind rules declared in `docs/language/graphir-boundary.md`.

### V040 - Required Projection Target For Generated-Code Mode

Severity: P0

The Phase 0 generated-code benchmark graph must declare exactly one Python native projection target for generated source. Code-first maintenance fixtures should instead declare extraction and mapping expectations.

### V041 - Source Map Coverage For Generated-Code Mode

Severity: P0 for M2 and later, P1 in M1

Every generated-code projection node that is expected to round-trip must be covered by at least one `metadata.sourceMap` node.

### V042 - Relative Generated Paths

Severity: P1

Generated target paths and metadata paths must be relative paths. Absolute local paths must not appear in GraphIR.

### V043 - Source Map Required Attributes

Severity: P0

Every `metadata.sourceMap` node must include `targetFile`, `targetName`, `targetKind`, `compilerContract`, `graphNodeIds`, and `requiredForRoundTrip`.

### V044 - Source Map Graph Node Integrity

Severity: P0

Every ID in `metadata.sourceMap.attributes.graphNodeIds` must reference an existing graph node.

### V045 - Compiler Contract Is Not Implementation Claim

Severity: P1

M1 source maps must name a future generated-code contract, not claim that generated code or an implementation already exists.

### V050 - Evidence Linkage

Severity: P1

Every `evidence.record` must be linked from at least one graph node by an `evidenced_by` edge, or must be explicitly marked as milestone-level evidence.

### V051 - Evidence Status

Severity: P1

Evidence status must be one of `planned`, `pass`, `fail`, `blocked`, or `superseded`.

### V052 - Evidence Required Attributes

Severity: P0

Every `evidence.record` must include `evidenceType`, `status`, `summary`, and `recordedBy`.

### V053 - Evidence Observation And Acceptance

Severity: P0 in M5 and later

Every `evidence.record` must include `observationStatus`, `acceptanceStatus`, and `artifactRefs`. Accepted evidence must include `acceptedByAuthority`.

Observation does not imply acceptance.

Accepted evidence must not have `status: "fail"`, `status: "blocked"`, or `status: "superseded"`. Accepted verifier-report evidence must have `status: "pass"`. Accepted planned evidence must declare `claimScope: "plan-only"` and `runtimeProof: false`.

### V054 - Accepted Evidence Authority

Severity: P0 in M5 and later

Every accepted evidence record must reference an accepted `authority.record`, and that authority record must authorize the evidence record with an `authorizes` edge.

### V060 - Authority Linkage

Severity: P1

Every `authority.record` must authorize at least one history delta, projection target, or evidence record.

### V061 - AI Is Not Final Authority

Severity: P0

If an accepted authority decision has `proposerType: "ai"`, then `decidedByType` must not be `ai`.

### V062 - Authority Required Attributes

Severity: P0

Every `authority.record` must include `proposer`, `proposerType`, `requiredAuthority`, `validator`, `decidedBy`, `decidedByType`, `decision`, and `decisionStatus`.

### V063 - Accepted Authority Scope

Severity: P0 in M5 and later

Every accepted `authority.record` must authorize at least one evidence record, history delta, or projection target. An accepted authority record must not have `decidedByType: "ai"` under case-normalized actor type comparison. Unknown actor types are invalid.

### V070 - History Linkage

Severity: P1

Every `history.delta` must link to at least one changed node through a `changes` edge.

### V071 - Git Link Boundary

Severity: P2 in M1, P1 after generated artifacts exist

`history.delta.attributes.gitCommit` may be `null` only before implementation commits exist for generated artifacts.

### V072 - History Required Attributes

Severity: P0

Every `history.delta` must include `sequence`, `changeType`, `summary`, `status`, and `gitCommit`.

### V073 - Accepted History Authority And Git Boundary

Severity: P0 in M5 and later

Every accepted `history.delta` must be authorized by an accepted `authority.record` and must link to at least one changed node. Accepted history sequences must be contiguous from `1..n` in the B0 subset. Non-null `gitCommit` values must resolve to local commit objects. If `gitCommit` is `null`, the delta must include `gitCommitBoundary: "pending-current-milestone"` and a reason.

### V080 - Declared Code-Only Loss

Severity: P0

The document must declare a code-only loss model. It must include evidence, authority, and history as non-recoverable from ordinary source code alone.

### V081 - Verification Expectations

Severity: P1

The document must declare `verificationExpectations` with `expectedMode`, `canonicalization`, and `requiresMetadata`.

### V090 - No Hidden Tool Defaults

Severity: P1

The graph must include enough explicit intent, code reference, code fact, mapping, and generated-code projection information for a future tool contract to be written without relying on unstated behavior.

For `B0-python-cli-calculator`, this includes operation semantics, argument parsing, output formatting, success exit code, and invalid input behavior.

### V100 - No Implementation Claims

Severity: P0 in M1

M1 artifacts must not claim generated code, reconstruction, verifier output, or test execution exists.

## P1.1 Intent Unit Overlay Mapping Rules

### V200 - Intent Units Required

Severity: P0 in P1.1

GraphIR v0.2 documents must include a non-empty `intentUnits` array and a `unitEdges` array.

### V201 - B0 Required Units

Severity: P0 in P1.1

The B0 unit-structured fixture must include:

- `unit.product.calculator`
- `unit.behavior.add`
- `unit.behavior.sub`

### V202 - Unit Admission Fields

Severity: P0 in P1.1

Every accepted Intent Unit must include:

- stable ID
- kind
- accepted status
- contract
- internal graph membership
- code references, code fact references, or explicit non-realized status
- mapping obligations
- projection and reconstruction expectations when generated-code mode is declared
- verification expectations
- evidence references
- authority references
- history references
- admission fields

Admission fields must distinguish accepted Intent Units from raw utterances, notes, hypotheses, imported facts, and AI proposals.

### V203 - Unit Internal Graph Integrity

Severity: P0 in P1.1

Every `internalGraph.nodeIds` entry must reference an existing graph node. Every `internalGraph.edgeIds` entry must reference an existing graph edge.

### V204 - Unit Evidence Authority History Integrity

Severity: P0 in P1.1

Every unit evidence reference must target an `evidence.record`. Every authority reference must target an `authority.record`. Every history reference must target a `history.delta`.

### V205 - Unit Refinement Backbone

Severity: P0 in P1.1

B0 must include refinement unit edges:

```text
unit.product.calculator -> unit.behavior.add
unit.product.calculator -> unit.behavior.sub
```

### V206 - Unit Edge Class Separation

Severity: P1 in P1.1

Unit refinement relations must use `unitEdges.kind = "refines"`. Cross-unit relations must use a distinct kind such as `shares_concept` or `projects_with`.

### V207 - No Unit God Object

Severity: P1 in P1.1

Behavior units must remain focused on their behavior contract. Shared product, evidence, authority, and history records may be referenced, but a behavior unit must not own unrelated behavior internals.

### V208 - Unit Mapping And Generated-Code Expectation

Severity: P0 in P1.1

The graph must declare that code-only reconstruction remains lossy for Intent Unit contracts, refinement structure, admission state, evidence, authority, and history. If generated-code mode is declared, exact unit round-trip requires preservation metadata.

### V209 - Proposal Non-Authority For Unit Membership

Severity: P0 in P1.1

AI proposals may describe unit effects or propose new internal graph facts, but they must not silently mutate accepted unit membership. Unit membership changes require deterministic validation and accepted authority.

### V210 - Unit Code References Are Not Code Text

Severity: P0 in P1.1

Every accepted Intent Unit must declare non-empty `codeRefs`. Each `codeRef` must identify a graph node, reference kind, mode, and `ownership: "reference-only"`. A `codeRef` must not contain source code text.

### V211 - Unit Code Fact References Are Declared Facts

Severity: P0 in P1.1

Every accepted Intent Unit must declare non-empty `codeFactRefs`. Because P1.1 has no external extractor, each fact must be explicitly marked as `graph-fixture`, `generated-code-mode`, or `static-declared`.

### V212 - Mapping Obligations Are Explicit

Severity: P0 in P1.1

Every accepted Intent Unit must declare non-empty `mappingObligations`. Each obligation must link intent nodes, code refs, code fact refs, verification IDs, evidence IDs, and authority IDs. `sourceTextEqualityRequired` must be `false`.

## P1.2 Code-First Overlay Rules

### V300 - Hand-Written Source

Severity: P0 in P1.2

CF0 source artifacts must be marked as hand-written. The code-first verifier must not invoke graph-to-code generation.

### V301 - Extracted Code Facts

Severity: P0 in P1.2

Extractor output must include stable fact IDs, source artifact path, source digest, source mode, confidence, and source location where applicable.

### V302 - Code Fact Resolution

Severity: P0 in P1.2

Every CF0 `codeFactRef.factId` must resolve to an extracted code fact in `X`.

### V303 - No Source Text Equality Requirement

Severity: P0 in P1.2

CF0 verification must report behavior and mapping preservation. It must not require `C' == C` or source text equality.

### V304 - No Hidden Generated-Code Snapshot

Severity: P0 in P1.2

CF0 verification must not depend on `hiddenState.sourceGraphSnapshot` or generated-code preservation metadata.

## P1.3 Code-First Maintenance Delta Rules

### V400 - Before-State Captured

Severity: P0 in P1.3

Before-state source digest, code facts digest/count, overlay digest, and mapping obligation count must be captured before the source and overlay mutation.

### V401 - Delta Report Is Code-First

Severity: P0 in P1.3

The delta report must declare `mode: "code-first-maintenance-delta"`, `sourceTextEqualityRequired: false`, and `hiddenGeneratedCodeSnapshotUsed: false`.

### V402 - Existing Mappings Preserved

Severity: P0 in P1.3

Existing add/sub behavior mappings must remain resolved after the delta.

### V403 - New Behavior Mapped

Severity: P0 in P1.3

The new behavior unit must include code refs, code fact refs, and mapping obligations that resolve to after-state extracted facts.

### V404 - Before Overlay Verified Against Artifact

Severity: P0 in P1.3.R

A maintenance delta report that cites before overlay digest or mapping obligation count must verify those values against a preserved or reproducibly recovered before-overlay artifact.

### V405 - Delta Records Resolve

Severity: P0 in P1.3.R

Every evidence, authority, and history id declared by a maintenance delta must resolve to a record in the accepted after overlay.

### V406 - Delta Negative Probes Are Repeatable

Severity: P0 in P1.4

The CF0 delta verifier must have a committed harness that proves wrong before-state values, missing expected facts, missing delta records, source-text equality claims, and hidden generated-code snapshot claims fail deterministically.

### V407 - B0 Typed Preservation Domains Validate

Severity: P0 in P1.5

B0 generated-code metadata must preserve `intentUnits`, `unitEdges`, `evidence`, `authority`, and `history` as typed records with deterministic counts and digests. Retrofit must fail when those counts, digests, or records are stale.

### V408 - Snapshot Reduction Is Honest

Severity: P0 in P1.5

P1.5 reports may claim selected typed-domain preservation, but must still state that `hiddenState.sourceGraphSnapshot` remains present and that code-only reconstruction does not recover evidence, authority, history, or full Intent Units.

### V409 - B0 Typed Preservation Negative Probes Are Repeatable

Severity: P0 in P1.6

B0 typed preservation must have a committed harness that proves retrofit rejects missing typed metadata, false snapshot boundary claims, missing domains, stale digests, missing records, wrong counts, and unsorted records.

### V410 - Code-First Refactor Preserves Stable Intent

Severity: P0 in P1.7

A code-first refactor delta must preserve the accepted Intent Unit id while updating code refs, code fact refs, and mapping obligations to current extracted facts. Old implementation facts must be reported as removed or historical, not used as current mappings.

### V411 - Historical Delta Baselines Are Explicit

Severity: P0 in P1.7.R

Historical delta harnesses must use named historical after-state facts, overlays, and source roots. They must not silently mix historical delta expectations with the current source or current overlay.

### V412 - Historical State Index Boundaries

Severity: P0 in P1.8

CF0 historical/current state indexes must use unique state ids, unique transition ids, deterministic `sha256:` artifact digests, exactly one current state, and explicit historical/current markers. Historical states must not point to mutable current source, current code-facts, or current overlay artifacts. Transitions must reference existing states and must identify their delta and verification report artifacts.

The P1.3 after-state must remain distinguishable from the P1.7 refactor state and later current states: P1.3 historical facts contain the old `mul` implementation facts, while P1.7 refactor facts contain `multiply` implementation facts and do not use the old `mul` implementation facts as current mappings.

### V413 - Overlay-Only Contract Delta

Severity: P0 in P1.9

An overlay-only contract delta must declare `sourceChanged: false`, `overlayChanged: true`, `contractCoverageIncreased: true`, `sourceTextEqualityRequired: false`, and `hiddenGeneratedCodeSnapshotUsed: false`. It must add or update IntentGraph overlay coverage for behavior that already exists in source, preserve existing accepted behavior units, verify the new contract through behavior evidence, and resolve its evidence, authority, and history records.

If extractor coverage is expanded to support the new contract, the new code facts must remain deterministic and the delta report must distinguish source behavior changes from extractor/overlay coverage changes.

### V414 - Overlay-Only Contract Negative Probes Are Repeatable

Severity: P0 in P1.10

Overlay-only contract deltas must have a committed negative-probe harness that reruns the unmutated positive baseline before bad cases. The harness must prove deterministic failure for incorrect source/overlay change flags, missing contract coverage increase, missing added unit, missing required code fact, missing verification, missing or wrong stderr expectations, missing evidence/authority/history records, source-text equality claims, and hidden generated-code snapshot claims.

The harness must exit successfully only when every bad case fails for the expected reason and must not pass because the positive baseline is broken.

### V415 - Overlay-Only Input Validation Contract Delta

Severity: P0 in P1.11

An overlay-only input-validation contract delta must preserve source bytes, increase overlay contract coverage, preserve existing accepted behavior units, and add explicit code refs, code fact refs, mapping obligations, verification, evidence, authority, and history for the newly accepted input-validation behavior.

Historical harnesses for earlier overlay-only deltas must use named historical after-state artifacts before the current overlay changes. They must not silently use mutable current facts, overlays, or source roots from later contract-coverage slices.

### V416 - Input Validation Contract Negative Probes Are Repeatable

Severity: P0 in P1.12

Input-validation overlay-only contract deltas must have a committed negative-probe harness that reruns the unmutated positive baseline before bad cases. The harness must prove deterministic failure for incorrect source/overlay change flags, missing contract coverage increase, missing added unit, missing required code fact or mapping resolution, missing verification, missing or wrong stderr expectations, wrong exit code, missing evidence/authority/history records, source-text equality claims, and hidden generated-code snapshot claims.

### V417 - CF0 Negative Harness Consolidation Preserves Boundaries

Severity: P1 in P1.13

Shared support code for CF0 negative probes must remain CF0-specific and must not become a broad framework claim. Consolidation may move common mechanics such as JSON I/O, temporary probe setup, verifier invocation, positive baseline reruns, and expected-failure matching into a helper module, but the harnesses must continue to own their probe lists, baseline scopes, report boundaries, and semantic claims.

P1.4, P1.10, and P1.12 harnesses must still pass after consolidation. Probe ids/counts must remain stable unless a documented quality fix requires a change. Positive baseline reruns must remain visible, source text equality and hidden generated-code snapshot claims must remain rejected, and CF0 source bytes must remain unchanged.

### V418 - Usage Arity Overlay-Only Contract Delta

Severity: P0 in P1.14

A usage/arity overlay-only contract delta must preserve source bytes, increase overlay contract coverage, preserve existing accepted behavior units, and add explicit code refs, code fact refs, mapping obligations, verification, evidence, authority, and history for the usage/arity behavior already present in source.

Before the current overlay changes, the prior P1.11 after-state must be captured as historical source, code facts, and overlay artifacts. The P1.12 negative harness must use those historical artifacts and must not silently use mutable current facts, overlays, or source roots from P1.14 or later slices.

### V419 - Usage Arity Contract Negative Probes Are Repeatable

Severity: P0 in P1.15

Usage/arity overlay-only contract deltas must have a committed negative-probe harness that reruns the unmutated positive baseline before bad cases. The harness must prove deterministic failure for incorrect source/overlay change flags, missing contract coverage increase, missing added unit, missing usage/arity code fact or mapping resolution, missing verification, missing or wrong stderr expectations, wrong exit code, missing evidence/authority/history records, source-text equality claims, and hidden generated-code snapshot claims.

The harness must exit successfully only when every bad case fails for the expected reason and must not pass because the positive baseline is broken.

### V420 - Overlay Contract Harness Boundary Review

Severity: P1 in P1.16

When multiple CF0 overlay-contract negative harnesses exist, their shared mechanics may be consolidated only if baseline identity remains explicit. A consolidation must preserve each harness's `baselineScope`, current/historical artifact boundary, positive baseline rerun, probe ids, expected-error matching, source-unchanged boundary, source-text equality rejection, and hidden generated-code snapshot rejection.

The helper may remain CF0-specific. It must not claim to be a general negative-probe framework unless it actually supports all current harnesses without hidden special cases and a milestone review accepts that scope.

### V421 - CF0 Overlay Coverage Is Explicit

Severity: P1 in P1.17

The current CF0 code-first overlay must have a deterministic coverage report that compares extracted code facts with overlay `codeRefs`, `codeFactRefs`, mapping obligations, verification, evidence, authority, and history.

The report must pass only when required behavior units are present, all overlay refs and mapping obligations resolve, behavior verification coverage exists for add/sub/mul/unsupported-operation/invalid-integer/usage-arity, and evidence/authority/history coverage exists for each required behavior unit.

The report may classify low-level structural facts separately. It must not claim that every AST/code fact must become an Intent Unit. It must preserve the boundaries that CF0 source bytes are unchanged, source text equality is not required, no hidden generated-code snapshot is used, and AI authority is not promoted.

### V422 - CF0 Specialization Requires A Gate

Severity: P1 in P1.18

After CF0 has code-first maintenance deltas, overlay-only contract deltas, negative harnesses, historical state indexing, and current overlay coverage, additional CF0 semantic probes must be treated as specialization risk.

New CF0 behavior or contract units must not be added by default. The next implementation-expanding step must first pass a plan-only generalization or second-benchmark gate that states what CF0 cannot prove, which prior-art systems must be reconsidered, which abstractions are reusable, and what pass/fail criteria prevent fixture overfitting.

### V423 - Local Review Workspace Is Fail-Closed

Severity: P0 in P9.1

The B1 local-review workspace must declare one supported profile, a source digest, contained input paths, exact `artifacts/` outputs, and a local-only authority object. It must fail before review execution when the role, schema, profile, source provenance, input path, output path, or any mutation/code-application/network/provider/credential/hook/release flag is invalid.

The workspace positive baseline must pass extraction, code-fact validation, mapping verification, non-applied proposal validation, consistency verification, and workbench generation. Repeatable negative probes must rerun that baseline and prove expected failures.

### V424 - Logical Source Identity Is Portable and Bounded

Severity: P0 in P9.2

When a code-fact report declares `sourceRootKind: logical-id`, its `sourceRoot` must be an `intentgraph://` logical identifier without traversal or backslashes. A portable workspace profile must bind its proposal baseline to this logical code-fact identity rather than a physical workspace path.

The same profile and source bytes in two different workspace directories must produce byte-identical review artifacts. Existing physical-path B1 extraction without `sourceRootKind` must remain byte-identical. Invalid logical extractor inputs, invalid logical code-fact reports, wrong workspace logical IDs, and stale profile proposal baselines must fail deterministically.

### V425 - External Source Intake Is Read-Only and Profile-Bounded

Severity: P0 in P9.4

An external source intake command must create a new workspace from a declared profile and must not analyze or modify the external source in place. For the bounded B1 profile, the external tree must have the exact allowed TypeScript file set and digests before it may be copied.

The intake receipt must omit the external absolute path while recording the profile, logical source root, before/after/copy tree digests, sorted copied-file digests, and false mutation/network/code-application authority flags. The command must fail closed for missing or file source roots, workspace overlap, pre-existing workspaces, symlinks, unsupported files, source mismatch, source change during intake, and tampered receipts. A positive baseline must prove that the external source digest stays unchanged through import and review.

### V426 - C# Syntax-Only Feasibility Is Read-Only and Deterministic

Severity: P0 in P9.6

A C# feasibility probe over a declared target source root must use a logical `intentgraph://` source root, read only non-symlink `*.cs` files outside `bin` and `obj`, and export only relative source references, digest/range provenance, extractor metadata, and allowed fact/relation kinds. It must not export absolute target paths or source text.

The probe must parse syntax only: semantic resolution and source build flags remain false, and invocation facts remain `ambiguous` syntax observations rather than resolved call edges. A positive probe must prove two outputs are byte-identical, every fact/relation ID is unique, every relation endpoint resolves, and the target source snapshot plus clean/aligned target Git state are unchanged before and after extraction.

Repeatable negative probes must fail for bad logical roots, unsafe output location, malformed/empty/missing C# source, unsupported arguments, persisted source text, and missing parser assembly. The probe must not build, restore, launch, mutate, package, or access hardware in the target repository, nor claim reusable profile, dependency packaging, or productization authority.

### V427 - Experimental Host-SDK C# Availability Is Not Product Support

Severity: P0 in P9.7/P9.8

A host-SDK C# profile availability result must be explicitly experimental and environment-specific. It may establish only that a declared local SDK exposes the required Roslyn binaries. It must not claim portable dependency packaging, broad C# support, semantic resolution, target extraction, target mutation, package restore/install, or IGD product readiness.

Before any reusable C# extraction or package dependency work, the project must record an explicit dependency decision covering versioning, compatibility, licensing, security updates, offline/clean-install behavior, upgrade/rollback, and release authority.

### V428 - Host-SDK Preflight Is Environment-Only and Fail-Closed

Severity: P0 in P9.8

An experimental host-SDK preflight must validate the profile's exact experimental, host-specific, non-portable, not-product-ready, and zero-authority declaration before SDK discovery. It may inspect only local SDK metadata and the declared Roslyn binary files. It must never read target source, execute target extraction/build/restore/launch, add/restore/install packages, or persist absolute SDK paths.

For a stable local environment, repeated preflight reports must be byte-identical. The report must identify selected SDK version and required binary digests. Repeatable negative probes must cover unsafe profile claims, unsupported SDK selection, an actually missing host binary, and profile-output overwrite.

### V429 - Experimental C# Workspace Is Snapshot-First and Fact-Only

Severity: P0 in P9.9/P9.10

An experimental C# workspace may open only after the declared host-SDK preflight passes. It must intake a non-symlink C# source subset into a new non-overlapping workspace, prove external source before/after equality, and persist only a logical source root plus path-free receipt/digest evidence. It must never extract from or write to the external source after intake.

Facts must be generated solely from the workspace snapshot and preserve the P9.6 syntax-only boundary. The workspace must explicitly remain fact-only: no Intent Unit mapping, proposal, acceptance, source application, or product workbench claim may be created. Any profile/preflight mismatch, unsafe source root, source mutation, path leak, absolute path, source text, semantic-resolution claim, authority promotion, output collision, or workspace escape must fail closed.

### V430 - Experimental C# Fact Workspace Has Reproducible Provenance

Severity: P0 in P9.10

`init-experimental-csharp` must require the one declared experimental profile and successful P9.8 preflight, then write a new local workspace only after intake guards pass. It may snapshot only non-symlink `*.cs` files outside `bin` and `obj`. Every persisted workspace artifact must use a logical source root and relative paths; no external absolute path or source text may persist.

The workspace must prove external source before/after/copy digest equality for its own intake event and extract facts from the copy only. Fixed source inputs must produce byte-identical workspace artifacts. If a live external source changes between separate runs, each valid workspace may represent its own receipt-bound snapshot; the system must not claim cross-snapshot equality. The workspace must remain fact-only and reject mapping, proposal, semantic-resolution, authority, output-path, or source provenance promotion.

### V431 - Experimental C# Fact Workbench Is Explicitly Incomplete

Severity: P0 in P9.11/P9.12

An experimental C# fact workbench may render only a validated P9.10 snapshot workspace and must preserve its exact profile, logical source identity, source/fact/extraction digests, syntax-only status, and fact-only authority. It must present code facts and syntax relations as inspectable graph elements with valid endpoints and inspector payloads, while keeping source references relative and digest-backed. Source text and external absolute source paths must not persist.

The workbench must explicitly distinguish recorded C# facts from not-recorded Intent mapping, change proposal, graph delta, code diff, verification, evidence, acceptance authority, and semantic history. Missing semantic/change records must never be rendered as successful verification, an empty project intent, resolved call semantics, or an actionable approval. Its HTML must be local-only, include a bundled graph runtime and required graph/search/filter/inspector/status/unavailable-state markers, and contain no network URL, mutation or approval control, source application, authority promotion, or generic C# product claim.

Fixed inputs must yield byte-identical projection and HTML artifacts. Negative probes must reject invalid workspace pairing, stale provenance, malformed facts/relations, unresolved endpoints or inspectors, source/path leakage, semantic/authority promotion, missing unavailable-state metadata, external runtime references, UI mutation/approval controls, and unsafe output paths. Browser evidence must prove a nonblank graph, pan/zoom, node and edge inspection, and visible unavailable code-diff state.

### V432 - External Verifier Results Are Typed Observations, Not Acceptance

Severity: P0 in P9.29

An imported verifier result must bind one exact proposal verification/evidence
requirement pair declared compatible with its verifier kind. It must preserve source
and proposal digests, use a monotonic attempt, declare typed checks and metrics, and
bind the required external artifact kind by digest, byte length, media type, and
logical name. A passing test observation must include at least one passed test.

The `deterministic` field is a declaration supplied by the external result. Intake
validation must not describe it as independently proven or authenticated.

The Workbench may hash local artifact bytes but must not upload them, execute or
authenticate the verifier, accept evidence, approve the proposal, apply a graph delta,
or edit source. Pass, fail, and blocked observations remain `verification-observed`
with acceptance pending. Writes must be serialized, compare the expected project
state, commit state last, reject duplicate attempts, preserve receipt/result ordering,
and create exactly one durable revision per result. Malformed, stale, incompatible,
authority-promoted, or projection-inconsistent input must fail zero-write.

### V433 - Local Evidence Decisions Require Explicit Human Authority

Severity: P0 in P9.30

An evidence decision must reference one current verifier result and preserve its exact
proposal, verification requirement, evidence requirement, result digest, evidence
digest, source digest, and proposal digest. Only `accepted` and `rejected` decisions are
allowed. `accepted` requires a passing verifier result; a fail or blocked result may
only be rejected. Superseded, unknown, duplicate, stale, or authority-promoted decisions
must fail zero-write.

The reviewer must declare `actorType: human`, one of `maintainer`, `quality-reviewer`,
or `security-reviewer`, the matching `evidence.accept` or `evidence.reject` permission,
and `authorityScope: local-project-workspace`. The record must state that authentication
is local-session and not cryptographically verified. AI actors, wrong roles, wrong
permissions, wider scopes, and cryptographic-authentication claims must fail closed.

Rejecting a current result blocks the work item. Deciding only part of the current
required pairs leaves it `verification-observed`. Only when every current required pair
has a passing accepted result may the work item become `verified`. A decision must create
exactly one durable timeline revision and explicit decision, authority, and evidence
graph records. It must not approve or apply the proposal, upload evidence bytes, execute
verification, mutate graph/source/snapshot/target state, or grant network, provider, or
credential authority. Concurrent duplicate decisions must have one winner, and
cross-operation writes must preserve both accepted records without lost updates.

Decision-derived verification, evidence, and history records must equal records derived
from the accepted decision artifact; matching identifiers alone are insufficient.
Projection validation must re-derive coverage, work readiness, and all six decision
relations rather than accept self-consistent counters or partial topology. Every legal
JSON value, including nested arrays and objects in enum fields, must produce a controlled
validation failure and zero writes instead of an uncaught type error.

### V434 - Precision Rendering Is Screen-Bounded and Semantically Inert

Severity: P1 in P9.31

The project Workbench must expose an effective logical zoom of `100` while keeping the
graph renderer at or below `24` and expressing the remaining scale through deterministic
virtual geometry. At maximum zoom, a selected relation must render at `0.065` screen
pixels with `0.34` opacity. Precision node material must remain screen-bounded rather
than grow with logical geometry.

The active cached node material must be identifiable as `cached-spectral-titanium-v2`.
Its gradients, grain, etching, and spectral rim are constructed only when a bounded
sprite-cache entry is missing; viewport rendering reuses the cached sprite. Distant
overview culling may skip expensive material sprites for ordinary code facts, but it
must not remove those code facts from the Cytoscape graph.

Rendering refinement must not change graph nodes, graph relations, layout coordinates,
workflow records, snapshot facts, authority, source state, graph deltas, or code diffs.
Static emission and validation, byte-identical repeated output, loopback server smoke,
negative probes, and a real-browser observation with zero console errors are required.

### V435 - Browser Rendering Evidence Must Be Repeatable and Fail Closed

Severity: P1 in P9.32

The static project Workbench must expose a query-activated, read-only runtime probe that
is inert during ordinary use. In probe mode it must report the loaded node and relation
counts, single graph instance, nonblank graph and material canvases, active material
profile, effective and renderer zoom, virtual geometry scale, selected-edge screen
width and opacity, actual selected-endpoint model-space expansion, populated selection
inspector, and runtime script errors.

A standard-library runner must serve only the supplied static Workbench over loopback,
launch an installed Edge or Chrome browser in headless mode, parse the page-produced
observation, and capture a PNG from the same browser process. The report must bind the
input HTML, projection, manifest, validation report, browser executable, and browser
version by digest or exact version metadata. It must validate both semantic measurements
and nonblank pixel evidence. The runner must not require Selenium, Playwright, Puppeteer, an external
network, provider API, credential, target launch, graph mutation, source mutation,
snapshot mutation, or target-repository mutation.

Repeatable negative probes must reject wrong graph counts, failed page checks, blank
graph or material canvases, wrong effective zoom, oversized selected relations, wrong
material identity, missing selection detail, runtime script errors, and invalid
screenshot evidence. Browser evidence remains observational and must not be promoted to
semantic, review, evidence-acceptance, proposal-approval, or application authority.
The validator must require every declared P9.32 page-check ID exactly once; missing or
duplicate checks fail closed rather than silently narrowing coverage.
Report and screenshot outputs must be distinct and outside the input Workbench; an
invalid output path must fail before deleting or writing any input artifact.

### V436 - Maximum Zoom Must Be an Actual Camera Zoom

Severity: P1 in P9.33

The project Workbench camera, logical zoom, and effective geometry zoom must each reach
`100`. Virtual geometry scale must remain `1` at maximum zoom. The renderer must not
claim `100x` by stopping the camera at a lower ceiling and rewriting node coordinates.

At maximum zoom, a selected relation must render at `0.55` screen pixels with `0.68`
opacity. Unrelated semantic-overview and stage-delta emphasis must be removed while a
node or relation is selected and restored when selection clears. The selection inspector must remain the
authoritative detail surface even when screen-space line emphasis is deliberately quiet.

The active cached material must be `cached-astral-forged-glass-v3`. Material sprites
must use kind-aware faceted silhouettes, a dark core, bounded specular/facet detail,
thin rims, and a bounded halo. Sprites must remain cached and viewport-local. Node
material and relation width must remain screen-bounded rather than grow with camera
zoom.

The sprite cache must enforce a 96-entry cap and deep-zoom redraw must select candidates
through a spatial viewport index rather than scan every graph node. A selected endpoint
crop must meet opaque, chromatic, quantized color-bucket, and luminance-range thresholds.

Static and real-browser verification must prove actual renderer zoom `100`, virtual
scale `1`, selected relation width/opacity, node-centered material complexity, material identity,
populated relation inspection, and zero runtime errors. Graph, layout, source, workflow,
evidence, authority, delta, and code-diff domains must remain unchanged.

### V437 - Deep Zoom Must Stay Anchored And Screen-Bounded

Severity: P1 in P9.34.R2

The Workbench must expose actual camera zoom through at least `100x`; the current ceiling
is `256x`. A direct deep-zoom action must center a selected graph element. With no
selection, it must choose the visible node nearest the viewport center instead of
magnifying an empty coordinate. If a selected node or relation becomes hidden by a
lens or filter, it must fall back to a visible node instead of retaining the hidden
coordinate as its anchor.

At `256x`, a selected relation must render at `0.18` screen pixels and `0.34` opacity.
The active cached node material must be `cached-stellar-vitreous-v5`, use kind-aware
faceted silhouettes, and remain bounded to a 96-entry viewport-local sprite cache.
Browser verification must prove nonblank graph/material pixels, detailed selected-node
pixels, populated relation inspection, camera pan and zoom-out recovery, completed
render frames, an externally bounded whole-capture wall clock, and no runtime errors.
Virtual-time interaction diagnostics must be finite but must not be presented as
individual wall-clock budgets. No graph, source, workflow, evidence, authority, history,
delta, or code-diff mutation is permitted.

### V438 - Deep Zoom Material Must Remain Refined Under Selection

Severity: P1 in P9.34.R3

This is the historical R3 evidence boundary and is superseded for the current
Workbench by V439.

The Workbench camera, logical zoom, and effective geometry zoom must reach `512` while
preserving direct `100x` and `256x` controls. At maximum zoom, a selected relation must
render at `0.08` screen pixels with `0.12` opacity. Its endpoints must use a compact
endpoint-specific treatment rather than the full selected-node halo.

The active cached material must be `cached-nebula-black-metal-v7`. It must use a
near-black alloy core, asymmetric facet planes, sparse grain, etched contours, and a
thin diffraction rim. Its visible-body crop must preserve those facets at ordinary
screen-scale rendering while relation endpoints retain their compact crop. Stacked
glossy borders, broad radial highlights, and the prior
`cached-stellar-vitreous-v5` identity must not remain active. Precision views must
suppress the rectangular grid. The sprite cache remains bounded to 96 entries and
material candidate rendering remains viewport-local.

Browser verification must prove exact `100x` and `512x` camera values, exact maximum
selected-relation width and opacity, bounded endpoint material pixels, nonblank graph
and material canvases, endpoint opaque bounds no larger than `22x22` screen pixels,
finite zoom/navigation observations, pan and zoom-out recovery, populated relation
inspection, and zero runtime errors. The graph, layout, source, workflow, evidence,
authority, history, delta, and code-diff domains must remain unchanged.

### V439 - Overview Visibility and Deep-Zoom Edge Continuity Must Fail Closed

Severity: P1 in P9.34.R4

The full graph must preserve a readable color and luminance signal for ordinary code
facts without changing graph topology or loading fewer facts. The active
`cached-luminous-nebula-alloy-v9` material must retain dark faceted construction while
exposing brighter hierarchy planes and a narrow spectral signal. Overview code
material must use at least `3.8px` and `0.96` opacity, while the renderer body and code
relations retain `0.30` opacity contracts. Ordinary low-detail code facts must retain
at least `0.82` element opacity and be sampled independently of landmark material.

At maximum zoom a selected relation must render as a continuous `0.65px` screen-space
line at `0.30` opacity. Selection must override ordinary dashed relation styling with
a solid inspection line, and the browser gate must exercise an `invokes-syntax`
relation. Precision attachment geometry must use the `0.46` body scale.
At least one on-screen relation endpoint must be sampled, every sampled endpoint must
remain within `22x22px`, and the rendered geometry-to-visible-body difference must not
exceed `1.5px` under renderer pixel quantization. A canvas-pixel corridor extending from the sampled endpoint along the
selected relation must contain exactly 13 samples, 12 or 13 observed samples, and no
missing run longer than one sample. Observed samples must never exceed total samples.
Overview material evidence must include at least 400 opaque samples, 280 chromatic
samples, and mean opaque luminance of at least 34.

Browser and negative-probe verification must reject low-contrast overview material,
dim ordinary code facts, fragmented relation pixels,
disconnected selected relations, oversized endpoint material, wrong material
identity, non-finite zoom observations, unbounded material work, and runtime errors.
No graph, source, workflow, evidence, authority, history, delta, or code-diff mutation
is permitted.

### V440 - Graphify-Style Single-Renderer Graph Must Fail Closed

Severity: P1 in P9.34.R5

V440 supersedes V439 for the current Workbench renderer. The runtime must use circular
nodes, the ten-color Graphify categorical palette for code communities,
degree-weighted node size, hub-only default labels, and confidence-aware relation
styles. The former material canvas must not exist in the runtime DOM. Graph rendering
must remain in one Cytoscape coordinate system. Unsupported or missing relation
confidence values must fail closed to the conservative `unknown` style.

At `512x`, selected relations must render as solid `2px` lines at `0.90` opacity with
no target arrow. Precision node diameter must remain between `6px` and `24.1px`, and
the settled precision size target must reserve enough margin that the bounded viewport
style-refresh tolerance cannot escape that range. The `511x` to `512x` endpoint-size
transition must remain within one screen pixel. The whole visible relation segment must
be sampled at intervals no larger than one pixel with at least `0.99` coverage and no
missing run longer than one sample. A browser-side hidden-line control must produce no
more than `0.10` coverage before presentation style restoration. Reported sample counts,
observed counts, coverage, and longest-missing-run summaries must agree arithmetically.
Browser checks must reject
insufficient community colors, excessive default labels, dim code nodes, non-dot
shapes, a second renderer, relation arrows, fragmented relation pixels, unbounded
endpoint nodes, invalid virtual-time diagnostics, and runtime errors. In-page virtual
time is not a latency claim; the full capture has a `45s` wall-clock gate.

No graph semantic, source, workflow, evidence, authority, history, delta, or code-diff
mutation is permitted. Presentation coordinates may change only deterministically and
must be documented as presentation spacing.

### V441 - Reviewed Source Refresh Must Preserve Revision Authority

Severity: P1 in P9.35

When an external C# source digest differs from the active local snapshot, `prepare`
and `open` must fail closed. `refresh` may create only a deterministic, non-applied
candidate and review plan. Planning must leave the target source, active workspace,
launch record, and active revision pointer byte-stable.

Mappings may remain current only when all referenced code facts still exist and their
canonical fact records are unchanged. Every other mapping is stale. Proposals, review
receipts, verifier results, and evidence decisions from the prior snapshot are always
historical after refresh and must not remain active. Prior evidence, authority, and
history must remain available in the immutable predecessor workspace.

Activation requires the exact pending plan id plus unchanged source, active workspace,
candidate workspace, launch record, and revision chain. Revision workspaces must not
be swapped or rewritten during activation. The sole authority commit is one atomic
replacement of the launch record's active revision pointer. A failure before that
commit leaves the predecessor active; completion of that commit makes the candidate
active. Revision ids must be contiguous, and active and historical workspaces must
validate independently.

Each accepted revision must retain the exact canonical plan. Ordinary launch/status
validation must recompute candidate state, source/fact/relation deltas, invalidation,
and preservation from the predecessor and accepted workspaces, then require the plan,
receipt, launch provenance, and recomputed semantics to agree. Joint mutation of
digest-bearing metadata is not sufficient evidence.

Source mutation, automatic mapping, proposal migration, approval automation, target
build/restore/launch, provider/network access, credentials, and AI authority are
forbidden. Any silent stale-record carryover, non-atomic multi-file authority commit,
source mutation, drift acceptance, invalid historical revision, or nondeterministic
plan is a P1 failure.

## M1 Fixture Review Checklist

For `docs/examples/b0-python-cli-calculator.graph.json`, a reviewer should check:

- JSON parses successfully
- IDs are stable and unique
- node and edge kinds are known
- all edge endpoints exist
- product intent is represented
- add and subtract behavior are represented
- Python module/function/CLI projections are represented
- source map metadata nodes exist for generated-code projections
- code nodes are references/facts rather than code text copies
- tests are represented as expectations, not executed results
- evidence and authority are present and linked
- history delta is present and linked
- code-only loss model is explicit
