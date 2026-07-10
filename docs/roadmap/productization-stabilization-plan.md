# Productization Stabilization Plan

Status: created in P8.0; rechecked through P8.59.

IntentGraph is not ready for productization. The current evidence proves a semantic overlay model, deterministic toy and B1 fixtures, a static workbench preview, and read-only WindowsUtility adoption artifacts. It does not yet prove a safe user-facing product.

## Non-Negotiable Boundary

Productization must remain blocked until real-project adoption evidence exists.

Blocked work:

- package or release a CLI/app as production-ready
- editor integration
- GitHub workflow integration
- team workflow automation
- AI code application authority
- broad source mutation workflows
- product readiness claims

Allowed work:

- readiness reports
- stabilization plans
- read-only inventories
- mapping acceptance boundaries
- non-applied proposal validation
- deterministic verifier and workbench projections

## Stabilization Tracks

### Track 1: Real-Project State

Goal: make the selected target safe to reason about.

Required evidence:

- target repository state is acceptable
- target state is recorded before and after each adoption slice
- target writes are not performed without explicit approval

### Track 2: Accepted Mapping

Goal: move from hypotheses to accepted mappings.

Required evidence:

- at least one WindowsUtility Intent Unit mapping is accepted
- all code refs and code fact refs resolve
- ambiguity remains explicit where unresolved
- stale/missing mapping failures are deterministic

### Track 3: Real Change Loop

Goal: prove the workflow on one real maintenance task.

Required evidence:

- non-applied proposal exists
- mapping and code fact consistency passes
- evidence requirements are explicit
- authority requirements are explicit
- rollback/stop conditions are explicit

### Track 4: Workbench

Goal: make the real-project process visible.

Required evidence:

- WindowsUtility projection exists
- projection includes graph, code facts, mappings, ambiguity, proposal, evidence, authority, and history
- users can inspect why a change is blocked or acceptable

### Track 5: Product Surface

Goal: decide the first shippable surface after adoption evidence exists.

Candidate order:

1. CLI report commands
2. static local workbench export
3. local app
4. editor integration
5. GitHub workflow integration
6. team workflow automation

Each step needs a separate build/borrow/integrate review.

## Phase H Entry Criteria

Phase H implementation can open only when:

- real-project repository state is acceptable
- accepted mapping evidence exists
- one real-project proposal loop passes deterministic verification
- evidence and authority records are complete
- real-project workbench projection exists
- user workflow benchmark has a baseline
- product surface decision record exists

Until then, Phase H is restricted to readiness and stabilization artifacts only.

## P8.28 Recheck

P8.28 found that several P8.0 blockers are now resolved or improved:

- WindowsUtility target state is clean/aligned.
- one shell/workspace mapping is accepted and verified.
- a non-applied shell/workspace proposal exists and validates.
- sandboxed build, UI launch, and screenshot evidence exist.
- a static WindowsUtility workbench projection exists.
- the user/coordinator compact `accept` response is recorded.

Productization remains blocked because:

- no real proposal application loop has passed.
- no first product surface decision exists.
- no packaging/release boundary exists.
- the workflow response is compact, not a detailed usability study.
- only the shell/workspace mapping is accepted.

The next safe stabilization slice is:

```text
P8.29 First Product Surface Decision Boundary Plan
```

## P8.29 Surface Decision

P8.29 selected the first product surface boundary:

```text
surface.static-local-workbench-export
```

This is selected before CLI/app/editor/GitHub/team workflow surfaces because it is local, browser-inspectable, already supported by P8.21-P8.24 evidence, and does not require install, remote execution, target writes, proposal application, AI authority, hardware authority, packaging, or release.

The next safe stabilization slice is:

```text
P8.30 Static Local Workbench Export Boundary
```

## P8.30 Static Export Boundary

P8.30 defined the first static local export boundary. The next prototype must produce:

- `index.html`
- `projection.json`
- `manifest.json`
- `assets/screenshot.png`

The prototype must validate local browser loading, screenshot rendering, source artifact digests, visible authority false flags, no network dependency, and unchanged WindowsUtility target state.

The next safe stabilization slice is:

```text
P8.31 Static Local Workbench Export Prototype
```

## P8.31 Static Export Prototype

P8.31 emitted the first static local workbench export prototype under:

```text
generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.31
```

The prototype includes `index.html`, `projection.json`, `manifest.json`, and `assets/screenshot.png`. Validation, negative probes, and headless browser checks passed.

The prototype is still not a package, release, editor integration, GitHub integration, or product readiness claim.

The next safe stabilization slice is:

```text
P8.32 Static Local Workbench Export Productization Gate Review
```

## P8.32 Productization Gate Review

P8.32 found the P8.31 static export ready for user/coordinator review, but not productized.

Still blocked:

- packaging
- release
- editor integration
- GitHub workflow integration
- team workflow automation
- source writes
- proposal application
- product readiness claims

The next safe stabilization slice is:

```text
P8.33 Static Local Workbench Export User Review Request
```

## P8.33 Static Export User Review Request

P8.33 created the explicit user/coordinator review request for the P8.31 static local workbench export.

Review target:

```text
generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.31/index.html
```

No result is recorded yet. Continue only after the user/coordinator answers whether to proceed, revise, or pause.

Still blocked:

- packaging
- release
- editor integration
- GitHub workflow integration
- team workflow automation
- source writes
- proposal application
- product readiness claims

The next safe stabilization slice is:

```text
P8.34 Static Local Workbench Export User Review Result Record
```

## P8.34 Static Export User Review Result

The user/coordinator response was:

```text
revise: 일단 이게 뭔지 잘 모르겠어. 뭘 나타내는거야? 내가 뭘 봐야해?
```

The static export must be revised before another review request. The next revision must make the page self-explanatory:

- what the page is
- what it represents
- what the user should inspect
- what remains unauthorized

The next safe stabilization slice is:

```text
P8.35 Static Local Workbench Export Reviewer Orientation Revision
```

## P8.35 Static Export Reviewer Orientation Revision

P8.35 created a revised static local workbench export under:

```text
generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.35
```

The first screen now explains:

- what the page is
- what it represents
- what the user should inspect
- what it is not

The revised export passed validation, negative probes, and headless browser validation.

Still blocked:

- packaging
- release
- editor integration
- GitHub workflow integration
- team workflow automation
- source writes
- proposal application
- product readiness claims

The next safe stabilization slice is:

```text
P8.36 Static Local Workbench Export Orientation Review Request
```

## P8.36 Static Export Orientation Review Request

P8.36 created the explicit user/coordinator review request for the revised p8.35 static local workbench export.

Review target:

```text
generated/product-surfaces/windowsutility-shell-workspace-static-workbench/p8.35/index.html
```

No result is recorded yet. Continue only after the user/coordinator answers whether to proceed, revise again, or pause.

Still blocked:

- packaging
- release
- editor integration
- GitHub workflow integration
- team workflow automation
- source writes
- proposal application
- product readiness claims

The next safe stabilization slice is:

```text
P8.37 Static Local Workbench Export Orientation Review Result Record
```

## P8.37 Static Export Orientation Review Result

The user/coordinator response was:

```text
proceed
```

The revised p8.35 static export can be treated as a reviewed product surface candidate for the next bounded iteration.

This does not authorize:

- source writes
- proposal application
- hardware actions
- packaging
- release
- productization

The next safe stabilization slice is:

```text
P8.38 Static Local Workbench Export Productization Readiness Recheck
```

## P8.38 Productization Readiness Recheck

P8.38 found:

- static local workbench product surface is accepted for the next iteration.
- productization is still blocked.
- source application loop is absent.
- packaging/release boundary is absent.

Still blocked:

- source writes
- proposal application
- hardware actions
- packaging
- release
- productization

The next safe stabilization slice is:

```text
P8.39 Source Application Authority Boundary Plan
```

## P8.39 Source Application Authority Boundary Plan

P8.39 defined the report-only authority boundary required before future source application or dry-run work.

The next safe mode is:

```text
non-mutating-source-application-dry-run
```

Still blocked:

- source writes
- proposal application
- target writes
- WindowsUtility commit
- WindowsUtility push
- hardware actions
- packaging
- release
- productization

The next safe stabilization slice is:

```text
P8.40 Non-Mutating Source Application Dry-Run Boundary
```

## P8.40 Non-Mutating Source Application Dry-Run Boundary

P8.40 defined the boundary for future non-mutating source application dry-runs.

Allowed only:

- generated IntentGraphDevelopment reports
- patch/change-set preview
- touched-file expectation report
- evidence plan
- rollback plan
- authority requirement report
- negative probe report

Still blocked:

- WindowsUtility source writes
- WindowsUtility generated writes
- git index mutation
- commit
- push
- hardware invocation
- packaging
- release

The next safe stabilization slice is:

```text
P8.41 Non-Mutating Source Application Dry-Run Prototype
```

## P8.41 Non-Mutating Source Application Dry-Run Prototype

P8.41 emitted the first source-application dry-run bundle under:

```text
generated/windowsutility/source-application-dry-run/p8.41
```

The bundle includes a dry-run request, change-set preview, touched-file expectation report, evidence plan, rollback plan, authority report, validation report, and negative probe report.

The user has allowed future WindowsUtility source modification, but P8.41 did not exercise that permission. Source edits, proposal application, target writes, WindowsUtility generated writes, git index mutation, commit, push, AI authority, hardware actions, packaging, release, and productization remain blocked until the next explicit source application gate.

P8.41 validation passed and 12 negative probes passed.

The next safe stabilization slice is:

```text
P8.42 Source Application Authorization Review / Minimal Source Application Gate
```

## P8.42 Source Application Authorization Review

P8.42 reviewed the user source-modification permission against the P8.41 dry-run evidence.

Result:

```text
minimal-source-edit-proposal-required-before-application
```

The permission is observed, but the existing P8.12 proposal has no source patch, planned source change, or patch operation. No WindowsUtility source files were modified in P8.42.

The next safe stabilization slice is:

```text
P8.43 Minimal WindowsUtility Source Edit Proposal and Patch Preview
```

## P8.43 Minimal WindowsUtility Source Edit Proposal

P8.43 selected one low-risk test-automation source edit and emitted a patch preview:

```text
tests/RegressionSmoke/Invoke-IntentGraphShellWorkspacePreflight.ps1
```

The patch was not applied in P8.43. The selected file avoids product runtime paths, Utility_Windows reference source, Native interop, hardware paths, firmware/printer writes, packaging, and release paths.

The next safe stabilization slice is:

```text
P8.44 Minimal WindowsUtility Source Edit Application
```

## P8.44 Minimal WindowsUtility Source Edit Application

P8.44 applied the first real WindowsUtility source edit:

```text
tests/RegressionSmoke/Invoke-IntentGraphShellWorkspacePreflight.ps1
```

The first preflight run exposed a default-path bug in the previewed script. The correction stayed inside the same selected file, then final preflight and `dotnet build .\WindowsUtility.sln` passed.

WindowsUtility was committed and pushed at:

```text
ac5b2204442cde751f625a9979a4fdb437d468a8
```

Still blocked:

- AI authority promotion
- hardware actions
- packaging
- release
- productization

The next safe stabilization slice is:

```text
P8.45 Source Application Result Review / Next Productization Gate
```

## P8.45 Source Application Result Review

P8.45 found that the first real source application loop passed for one low-risk test-automation source edit.

Resolved:

- real source application loop absent

Still blocked:

- workbench/product surface has not been refreshed with the P8.44 source application evidence
- product runtime readiness is not proven by this test-automation helper edit
- packaging/release boundary is absent
- productization authority is absent

The next safe stabilization slice is:

```text
P8.46 WindowsUtility Source Application Workbench Refresh
```

## P8.46 WindowsUtility Source Application Workbench Refresh

P8.46 refreshed the static WindowsUtility workbench export with the P8.44 source application and P8.45 productization gate evidence.

Resolved:

- source application evidence is visible in the workbench/product surface

Still blocked:

- product runtime readiness is not proven by the test-automation helper edit
- packaging/release boundary is absent
- productization authority is absent

The next safe stabilization slice is:

```text
P8.47 Productization Packaging/Release Boundary Plan
```

## P8.47 Productization Packaging/Release Boundary Plan

P8.47 planned the report-only safety boundary required before any future packaging, release, or productization action.

Resolved:

- packaging and release boundary requirements are explicit

Still blocked:

- package artifacts are not authorized
- artifact signing is not authorized
- credential access is not authorized
- release publishing is not authorized
- productization authority is absent

The next safe stabilization slice is:

```text
P8.48 Non-Mutating Packaging/Release Dry-Run Boundary
```

## P8.48 Non-Mutating Packaging/Release Dry-Run Boundary

P8.48 recorded what a future non-mutating packaging/release dry-run may produce and validate.

Resolved:

- dry-run allowed outputs are explicit
- zero-write rules for packaging/release dry-run are explicit
- future negative-probe requirements are explicit

Still blocked:

- package artifacts are not authorized
- installers are not authorized
- artifact signing is not authorized
- credential access is not authorized
- provider API calls are not authorized
- release publishing is not authorized
- productization authority is absent

The next safe stabilization slice is:

```text
P8.49 Non-Mutating Packaging/Release Dry-Run Prototype
```

## P8.49 Non-Mutating Packaging/Release Dry-Run Prototype

P8.49 emitted and validated a non-mutating packaging/release dry-run prototype.

Resolved:

- packaging/release dry-run prototype exists
- package manifest preview is deterministic
- build/test evidence plan is present without execution
- release notes and publish-destination plans are previews only
- 14 packaging/release authority negative probes pass

Still blocked:

- package artifacts are not authorized
- installers are not authorized
- artifact signing is not authorized
- credential access is not authorized
- provider API calls are not authorized
- release tags are not authorized
- release publishing is not authorized
- productization authority is absent

The next safe stabilization slice is:

```text
P8.50 Packaging/Release Dry-Run Result Review / Next Productization Gate
```

## P8.50 Packaging/Release Dry-Run Result Review

P8.50 found that the non-mutating packaging/release dry-run loop passed, but productization is still blocked.

Resolved:

- non-mutating packaging/release dry-run prototype absent
- packaging/release authority negative probes absent

Still blocked:

- workbench/product surface has not been refreshed with P8.49 packaging/release dry-run evidence
- package artifacts are not authorized
- installers are not authorized
- artifact signing is not authorized
- credential access is not authorized
- provider API calls are not authorized
- release tags are not authorized
- release publishing is not authorized
- productization authority is absent

The next safe stabilization slice is:

```text
P8.51 Packaging/Release Dry-Run Workbench Refresh
```

## P8.51 Packaging/Release Dry-Run Workbench Refresh

P8.51 refreshed the static WindowsUtility workbench export with packaging/release dry-run evidence.

Resolved:

- packaging/release dry-run evidence is visible in the workbench/product surface

Still blocked:

- package artifacts are not authorized
- installers are not authorized
- artifact signing is not authorized
- credential access is not authorized
- provider API calls are not authorized
- release tags are not authorized
- release publishing is not authorized
- productization authority is absent

The next safe stabilization slice is:

```text
P8.52 Productization Readiness Recheck After Packaging/Release Dry-Run
```

## P8.52 Productization Readiness Recheck After Packaging/Release Dry-Run

P8.52 found that productization readiness improved, but productization remains blocked.

Resolved:

- accepted mapping absent
- sandboxed evidence absent
- static workbench product surface absent
- first source application loop absent
- packaging/release dry-run absent
- packaging/release dry-run evidence absent from workbench

Still blocked:

- package artifacts are not authorized
- installers are not authorized
- artifact signing is not authorized
- credential access is not authorized
- provider API calls are not authorized
- release tags are not authorized
- release publishing is not authorized
- packaged artifact install/run verification is absent
- user acceptance of a product candidate is absent
- productization authority is absent

The next safe stabilization slice is:

```text
P8.53 Package Artifact Creation Authorization Request
```

## P8.53 Package Artifact Creation Authorization Request

P8.53 requested explicit user/coordinator authorization for bounded sandboxed package artifact creation.

Current state:

- package artifact creation authorization is requested but not recorded
- package artifacts are not authorized
- installers are not authorized
- artifact signing is not authorized
- credential access is not authorized
- provider API calls are not authorized
- release tags are not authorized
- release publishing is not authorized
- productization authority is absent

Required next action:

```text
Wait for user/coordinator response, then record P8.54 Package Artifact Creation Authorization Result.
```

## P8.54 Package Artifact Creation Authorization Result Record

P8.54 recorded the user's explicit response:

```text
accept sandboxed package artifact creation
```

Current state:

- bounded sandboxed package artifact creation is authorized for local validation only
- sandboxed build or publish is authorized only inside a sandbox copy
- generated-output package artifact and manifest recording are authorized
- WindowsUtility source edits are not authorized by this record
- WindowsUtility commits and pushes are not authorized by this record
- installers are not authorized
- artifact signing is not authorized
- credential access is not authorized
- provider API calls are not authorized
- release tags are not authorized
- release publishing is not authorized
- productization authority is absent

The next safe stabilization slice is:

```text
P8.55 Sandboxed Package Artifact Creation Probe
```

## P8.55 Sandboxed Package Artifact Creation Probe

P8.55 exercised the P8.54 authorization and created a bounded local package artifact from a sandbox copy.

Resolved:

- package artifact creation authorization absent
- package artifact absent
- package manifest/checksum absent
- package artifact readability unverified

Current state:

- sandboxed `dotnet publish` passed
- generated-output package artifact exists
- zip readability verification passed
- package contains `WindowsUtility.App.exe`, `WindowsUtility.App.dll`, and `SmartComm2.dll`
- WindowsUtility target repository stayed clean/aligned

Still blocked:

- packaged artifact verification beyond zip readability
- installers are not authorized
- artifact signing is not authorized
- credential access is not authorized
- provider API calls are not authorized
- release tags are not authorized
- release publishing is not authorized
- user acceptance of a package candidate is absent
- productization authority is absent

The next safe stabilization slice is:

```text
P8.56 Packaged Artifact Verification Boundary
```

## P8.56 Packaged Artifact Verification Boundary

P8.56 recorded the boundary for future package verification.

Current state:

- package metadata replay is allowed
- checksum recomputation is allowed
- zip inventory inspection is allowed
- sandbox extraction is not yet authorized
- packaged executable launch is not yet authorized
- packaged UI screenshot capture is not yet authorized

Still blocked:

- packaged artifact extraction/run verification
- installers are not authorized
- artifact signing is not authorized
- credential access is not authorized
- provider API calls are not authorized
- release tags are not authorized
- release publishing is not authorized
- user acceptance of a package candidate is absent
- productization authority is absent

The next safe stabilization slice is:

```text
P8.57 Packaged Artifact Verification Authorization Request
```

## P8.57 Approval Workbench Graph Delta Visualization Requirement Record

P8.57 records that the current approval workbench direction is not sufficient unless it can visualize graph state, graph delta, selected element details, and diffs.

New requirement:

- approval surfaces must show an interactive graph
- graph delta must be visible
- nodes and edges must be selectable
- selected node/edge information must appear in a panel
- selected code nodes and code-affecting deltas must show code diffs
- changed existing nodes and edges must show before/after graph diffs
- missing required diff data must block approval

Impact:

- package verification authorization is deferred
- a graph delta approval workbench boundary must come next

The next safe stabilization slice is:

```text
P8.58 Graph Delta Approval Workbench Boundary Plan
```

## P8.58 Graph Delta Approval Workbench Boundary Plan

P8.58 defined the implementable boundary for a graph/delta/diff approval workbench.

Resolved:

- approval workbench requirement was recorded but not shaped into implementation slices

Current state:

- graph/delta projection schema is the next implementation target
- static HTML graph workbench is planned after projection schema
- negative probes and Graphify-grade usability dry run are required after prototype

Still blocked:

- graph delta approval workbench is not implemented yet
- package verification authorization is deferred
- packaged artifact extraction/run verification is absent
- user acceptance of a package candidate is absent
- productization authority is absent

The next safe stabilization slice is:

```text
P8.59 Graph Delta Approval Workbench Projection Schema
```

## P8.59 Graph Delta Approval Workbench Projection Schema

P8.59 emitted and validated the projection schema for the graph delta approval workbench.

Resolved:

- graph delta approval workbench boundary lacked a deterministic projection artifact

Current state:

- projection JSON exists
- projection validation passed
- graph nodes/edges and delta steps are present
- code diff and changed graph node/edge diffs are present

Still blocked:

- static graph delta approval workbench HTML is not implemented yet
- negative probes for the graph workbench are absent
- Graphify-grade usability dry run is absent
- package verification authorization is deferred
- productization authority is absent

The next safe stabilization slice is:

```text
P8.60 Static Graph Delta Approval Workbench Prototype
```

## P8.60 Static Graph Delta Approval Workbench Prototype

P8.60 emitted and validated the first static graph delta approval workbench prototype.

Resolved:

- the P8.59 projection now has a static local HTML surface.
- Cytoscape.js is bundled locally with no CDN dependency.
- graph nodes and graph edges are selectable.
- delta steps highlight affected graph elements.
- graph movement, zoom-in, zoom-out, fit, and semantic zoom support are structurally present.
- selected code nodes and code-affecting deltas expose code diffs.
- changed existing nodes expose before/after graph node diffs.
- changed existing edges expose before/after graph edge diffs.

Still blocked:

- browser visual/interaction dry-run evidence is absent.
- Graphify-grade inspectability has not yet been visually confirmed by an interaction dry run.
- user approval review of the graph workbench is absent.
- package verification authorization is deferred.
- packaged artifact extraction/run verification is absent.
- user acceptance of a package candidate is absent.
- productization authority is absent.

The next safe stabilization slice is:

```text
P8.61 Static Graph Delta Approval Workbench Visual/Interaction Dry Run
```

## P8.61 Static Graph Delta Approval Workbench Visual/Interaction Dry Run Attempt

P8.61 attempted to verify the graph workbench through a local browser route.

Current state:

- local HTTP loading worked enough to observe the page title, graph canvas, node count, edge count, and initial inspector.
- browser automation was blocked before interaction checks could complete.
- no alternate browser-control workaround was used.

Still blocked:

- graph pan/zoom/fit visual evidence.
- selected node inspector visual evidence.
- selected edge inspector visual evidence.
- selected code node code-diff evidence.
- changed node before/after graph diff evidence.
- changed edge before/after graph diff evidence.
- Graphify-grade inspectability confirmation.
- package verification authorization.
- packaged artifact extraction/run verification.
- user acceptance of a package candidate.
- productization authority.

The next safe stabilization slice is:

```text
P8.62 User-Observed Graph Delta Approval Workbench Review Request
```
