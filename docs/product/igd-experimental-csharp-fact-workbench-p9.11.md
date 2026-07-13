# P9.11 Experimental C# Fact Workspace Scope Review

P9.11 decides how a fact-only C# workspace may become inspectable in local HTML without claiming that it already contains an IntentGraph review state.

## Decision

Authorize one bounded implementation slice:

```text
P9.12 Experimental C# Fact-Only Workbench
```

The slice may render an experimental local HTML workbench from a validated P9.10 workspace. It must remain a code-fact inspection surface, not a generic IGD review workbench or a WindowsUtility productization surface.

## Why A Separate Workbench Contract Is Required

The existing B1 review workbench is for a complete local-review chain:

```text
code facts + Intent mapping + non-applied proposal + consistency verification
```

The P8.60 approval workbench additionally requires graph delta, code diff, graph-element diff, evidence, and authority links. P9.10 has none of those semantic/change artifacts. Reusing either contract would force fabricated availability or false blockers.

P9.12 must instead render this accurate state:

```text
validated C# snapshot + extracted code facts + syntax relations
mapping / proposal / graph delta / code diff / evidence / acceptance authority: unavailable
```

Unavailable means "not recorded in this workspace", not "the project has no intent, tests, history, or evidence".

## Source Data That P9.12 May Use

Only a workspace that passes `validate-experimental-csharp` may be rendered. The projection may use:

- workspace manifest and profile identity
- path-free source intake receipt and source digest
- C# code facts, relative source locations, source digests, confidence, and extractor metadata
- `contains`, `imports`, and ambiguous `invokes-syntax` relations
- extraction and workspace-validation report summaries
- the fact-only authority declaration

The projection must preserve the following limits:

- facts are Roslyn syntax-only; invocation edges are not resolved calls
- no source text or external absolute source path may enter the projection or HTML
- no project evaluation, build, test, launch, target mutation, package dependency, network, credential, provider, hook, code application, release, or productization claim is permitted
- local parser build-assets restore remains separately recorded as local/empty-source restore, not target or external package restore

## P9.12 Command And Artifacts

```powershell
python tools/intentgraph.py emit-experimental-csharp-fact-workbench \
  --workspace <validated-experimental-csharp-workspace>
  --out <new-local-workbench-output-directory>
```

The command must read the workspace without changing it and may write only these artifacts beneath the new output directory:

```text
projection.json
index.html
manifest.json
validation-report.json
assets/cytoscape.min.js
assets/cytoscape-license.txt
```

The emitter must reject an existing, overlapping, or unsafe output directory. It must not migrate the P9.10 manifest or silently treat that workspace as a complete review state.

The projection must declare:

- `mode: experimental-csharp-fact-only-workbench`
- exact input artifact digests and logical source identity
- graph records derived from code facts and syntax relations, plus stable indexes for search and focused subgraph inspection
- aggregate source/fact/relation counts by kind
- one inspector payload for every visible node and edge
- a complete explicit unavailable-state object for Intent mapping, proposal, graph delta, code diff, verification, evidence, acceptance authority, and semantic history
- fact-only/no-mutation/no-network authority flags

## HTML Review Contract

The local HTML must use a bundled local graph runtime, with its license and version recorded. No CDN, remote script, `fetch`, network URL, mutation control, approval control, or source-application control is allowed.

It must provide:

1. a dark, resizable, pannable, zoomable graph canvas
2. search and filters for fact kind, relation kind, and source file
3. a structural-overview default graph using file/namespace/type structure, with method and invocation detail available by filter or search
4. selectable nodes and edges with provenance, relative source location, confidence, relation interpretation, and ambiguity details in an inspector
5. a snapshot/status panel that distinguishes source receipt, extraction, validation, and fact-only authority
6. a visible unavailable-state panel. Selecting a code fact must show its source pointer and state that no proposed code diff exists; it must not invent a diff
7. concise orientation text that says what is displayed and what a reviewer can inspect

The default structural view must reduce the initial large-repository graph to a legible overview without discarding facts from the projection. A reviewer must be able to navigate to every fact through search, filter, or focused-neighbor inspection.

## P9.12 Validation And Negative Probes

The implementation must prove:

- exact P9.10 workspace/profile/scope/fact-only authority pairing
- all projected graph edge endpoints and inspector references resolve
- node/edge counts, kind counts, relation counts, and input digests agree with source artifacts
- every projected source reference is relative and digest-backed; source text and external absolute paths are absent
- all unavailable semantic/change states are explicit and false or not-recorded
- the HTML bundles its graph runtime locally and contains required canvas, search/filter, inspector, status, and unavailable-state markers
- no external URL, network call, mutation/approval control, or authority promotion exists
- repeated fixed-input projection and HTML are byte-identical
- a real WindowsUtility snapshot can render and validate without modifying that target
- browser evidence confirms the canvas is nonblank, pan/zoom works, a node click opens node details, an edge click opens edge details, and unavailable code-diff state is visible

Repeatable negative probes must cover wrong workspace role/profile/scope, stale digest, unknown fact or relation kind, missing edge endpoint, missing inspector payload, source-text or absolute-path leakage, semantic-resolution promotion, missing unavailable state, external runtime URL, mutation/approval UI controls, output escape, and stale or overwritten output artifacts.

## Explicit Deferrals

- no Intent Unit mapping or natural-language request interpretation
- no change proposal, graph delta, code diff, test/evidence claim, acceptance, or source application
- no resolved C# call graph, project-system evaluation, or portable C# dependency package
- no generic multi-profile workbench claim
- no WindowsUtility productization claim

## Exit Gate

P9.12 may begin only as the bounded fact-workbench implementation above. Its review must compare the emitted surface with this contract and choose the next safe direction: broaden fact quality, add a reviewed mapping boundary, or harden the local product workflow. It must not automatically promote C# extraction into supported general-project review.
