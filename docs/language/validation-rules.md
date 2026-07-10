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
