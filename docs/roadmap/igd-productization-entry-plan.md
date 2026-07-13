# IntentGraphDevelopment Productization Entry Plan

Status: P9.0 plan, P9.1 bounded implementation, P9.2 logical source identity, P9.3 external intake planning, P9.4 bounded import, P9.5 C# profile planning, P9.6 C# syntax feasibility, P9.7 dependency/profile reuse planning, P9.8 host-SDK availability preflight, and P9.9 C# workspace integration planning completed; P9.10 fact-only snapshot workspace implementation is next.

## Purpose

Define productization for IntentGraphDevelopment itself, after separating it from the WindowsUtility adoption experiment.

IntentGraphDevelopment is a local-first semantic-overlay development system. Its future product surface must let a developer or team extract code facts, inspect intent/code mappings, review a graph delta with evidence and authority, and retain the resulting records. WindowsUtility remains a benchmark target that proves parts of that workflow; it is not the product to distribute from this repository.

## P9.0 Candidate Decision

P9.0 selects a build path, not a public release:

```text
candidateId: igd-local-review-kit
candidateName: IntentGraph Local Review Kit
candidateStage: defined-not-built
```

The candidate is a local-first developer tool composed of two coordinated surfaces:

1. an `intentgraph` command surface that creates and validates a workspace of code facts, mappings, proposals, consistency results, and provenance
2. an interactive local workbench that lets a reviewer inspect the graph, graph delta, code delta, evidence, authority, and history produced by that workspace

The candidate is not WindowsUtility, a WindowsUtility static export, a universal graph-to-code compiler, a remote service, or an automatic code-application agent.

## Current Capability Evidence

The repository currently has 64 Python tool files, 63 separate `argparse` entry points, and 9 HTML-emitting tools. It has no Python packaging manifest, no cohesive public command, no install contract, and no supported-project configuration format. Existing B1 and WindowsUtility workbenches prove narrow workflow slices, but they are generated fixtures rather than a reusable product entry point.

This evidence supports defining the candidate. It does not support an installation, release, compatibility, or public-product claim.

## P9.0 Boundary

P9.0 is plan-only. It identifies one concrete IntentGraphDevelopment product candidate before creating installers, signing artifacts, accessing credentials, publishing a release, or claiming product readiness.

The candidate definition must state:

- the intended user and primary workflow
- the supported local inputs and outputs
- the command/workbench boundary
- the persistent artifact format and provenance rules
- the supported operating systems and runtime assumptions
- privacy, credential, and network behavior
- packaging, upgrade, rollback, and support expectations
- the acceptance evidence required before an IGD product-candidate decision

## Candidate Workflow Contract

The first supported workflow is review-first and local-only:

```text
repository + declared project profile
  -> deterministic code facts
  -> declared Intent Unit overlay and mapping validation
  -> non-applied change proposal and consistency verification
  -> local review workbench
  -> human decision recorded outside automatic code application
```

The product must preserve the distinction between a proposed delta and an applied code change. It may create local artifacts in a declared workspace, but it must not modify a target repository, invoke provider APIs, access credentials, install hooks, or self-authorize a change.

## Candidate Surface Principles

The first product must be useful without depending on WindowsUtility-specific files or paths. A reasonable candidate can combine:

1. deterministic local commands for extraction, mapping validation, proposal verification, and workbench projection
2. an interactive local workbench that makes graph, delta, code diff, evidence, authority, and history inspectable
3. a documented artifact contract that allows another project to reproduce the same review state

P9.0 may compare this bundle with narrower alternatives, but it must not silently treat a generated static WindowsUtility HTML export as the product.

P9.1 is limited to the first half of this candidate: a single local command facade and declared workspace contract. It must not promise language-general extraction, code application, editor integration, packaging, or release.

## Entry Evidence

P9.0 must consume, but not overclaim from:

- B1 code-fact, mapping, proposal, and verifier evidence
- Phase F workbench evidence
- Phase G WindowsUtility adoption evidence
- P8.124 scope correction

## Non-Goals

- no WindowsUtility installer or release
- no IntentGraphDevelopment installer or release
- no signing, certificate, token, credential, provider API, or network call
- no product-candidate acceptance request before the candidate is defined
- no claim that WindowsUtility delivery evidence proves IntentGraphDevelopment product readiness

## P9.0 Exit Criteria

P9.0 passes only when it produces an inspectable product-candidate definition, an independent acceptance checklist, and a bounded next implementation slice. It must leave release and productization authority false.

Those criteria are met by this plan, the P9.0 review, and the P9.0 report.

## P9.1 Result

P9.1 created the first `intentgraph` local facade and a fail-closed B1 workspace contract. A fresh workspace produces code facts, mapping and proposal verification, consistency evidence, and a static review workbench without target-repository mutation. The candidate remains defined-but-not-built at a product level: P9.1 is neither an installable CLI nor arbitrary-repository support.

P9.1 originally materialized a copied proposal baseline because the historical B1 aggregate code-facts digest included a physical source-root value.

## P9.2 Result

P9.2 replaces that path-specific materialization for the local-review profile. The B1 workspace now uses the logical identity `intentgraph://profiles/b1-typescript-rest-api-sample/source` and a static profile proposal baseline. Two fresh workspaces in different directories produce byte-identical review artifacts while historical B1 physical-path extraction stays byte-identical.

The next slice is `P9.3 External Project Profile Intake and Workspace Import Boundary Plan`.

## P9.3 Result

P9.3 defines a read-only external source intake boundary. P9.4 may import only a TypeScript source tree that is byte-equivalent to the bounded B1 profile, snapshot it into a new workspace, and prove the external tree did not change. It must not claim arbitrary project, C#, or WindowsUtility support.

The next slice is `P9.4 B1-Equivalent External Source Snapshot Import`.

## P9.4 Result

P9.4 snapshots an external B1-equivalent source copy into a new workspace. It records only profile and source-digest evidence, not the external absolute path, and proves that the external tree stays unchanged through import and review. It remains a single-profile safety proof, not generic project support.

The next slice is `P9.5 Project Profile Authoring and Language Expansion Gate - Plan Only`.

## P9.5 Result

P9.5 selects WindowsUtility's `src` tree as the second profile-shape feasibility target. P9.6 then proved a disposable Roslyn syntax-only extraction over 206 C# source files. The target stayed clean and byte-identical; two fact runs matched byte-for-byte; 8,137 provenance-backed facts and 7,931 relations were emitted. Invocation observations remain ambiguous syntax records, not resolved calls. It is not yet a reusable or packaged C# profile.

The next slice is `P9.10 Experimental C# Snapshot Workspace and Fact Extraction Probe`.
