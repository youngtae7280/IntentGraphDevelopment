# Productization Stabilization Plan

Status: created in P8.0; rechecked in P8.28.

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
