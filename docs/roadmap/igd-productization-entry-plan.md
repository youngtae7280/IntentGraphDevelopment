# IntentGraphDevelopment Productization Entry Plan

Status: proposed by P8.124; not yet an implementation authorization.

## Purpose

Define productization for IntentGraphDevelopment itself, after separating it from the WindowsUtility adoption experiment.

IntentGraphDevelopment is a local-first semantic-overlay development system. Its future product surface must let a developer or team extract code facts, inspect intent/code mappings, review a graph delta with evidence and authority, and retain the resulting records. WindowsUtility remains a benchmark target that proves parts of that workflow; it is not the product to distribute from this repository.

## P9.0 Boundary

P9.0 is plan-only. It must identify one concrete IntentGraphDevelopment product candidate before creating installers, signing artifacts, accessing credentials, publishing a release, or claiming product readiness.

The candidate definition must state:

- the intended user and primary workflow
- the supported local inputs and outputs
- the command/workbench boundary
- the persistent artifact format and provenance rules
- the supported operating systems and runtime assumptions
- privacy, credential, and network behavior
- packaging, upgrade, rollback, and support expectations
- the acceptance evidence required before an IGD product-candidate decision

## Candidate Surface Principles

The first product must be useful without depending on WindowsUtility-specific files or paths. A reasonable candidate can combine:

1. deterministic local commands for extraction, mapping validation, proposal verification, and workbench projection
2. an interactive local workbench that makes graph, delta, code diff, evidence, authority, and history inspectable
3. a documented artifact contract that allows another project to reproduce the same review state

P9.0 may compare this bundle with narrower alternatives, but it must not silently treat a generated static WindowsUtility HTML export as the product.

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

## Exit Criteria

P9.0 passes only when it produces an inspectable product-candidate definition, an independent acceptance checklist, and a bounded next implementation slice. It must leave release and productization authority false.
