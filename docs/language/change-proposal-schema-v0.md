# Change Proposal Schema v0

Status: introduced in P4.0 for the B1 proposal-only Phase D slice.

This schema describes non-applied change proposals. A proposal is not a patch, not an accepted plan, and not authority to mutate source code.

## Required Top-Level Shape

```json
{
  "artifactRole": "intentgraph-b1-change-proposal",
  "status": "intentgraph-b1-change-proposal-proposed",
  "scope": "b1-typescript-rest-api-change-proposal-non-applied",
  "proposalMode": "non-applied-plan",
  "applicationStatus": "not-applied"
}
```

## Required Sections

- `baseline`: exact source and code-fact baseline binding.
- `impactScope`: allowed source files and referenced existing Intent Units.
- `deltaC`: planned source changes, with `applied:false`.
- `deltaI`: planned intent graph additions or changes.
- `deltaM`: planned mapping updates.
- `requiredTests`: test obligations before acceptance.
- `requiredEvidence`: evidence obligations before acceptance.
- `requiredAuthority`: authority obligations before acceptance.
- `claimScope`: explicit false flags for application, source mutation, AI authority, self-authorization, workbench, productization, and broad planning.

## Non-Applied Boundary

The proposal must not contain source text, patches, replacement text, or applied diff hunks. It may describe intended operations as structured metadata, but actual source changes belong to a later apply slice after deterministic verification and authority review.

## Baseline Boundary

The proposal must bind to:

- a code facts path
- a canonical code facts digest
- source file digests
- the accepted overlay path
- referenced existing Intent Unit ids

The validator must reject stale code facts, stale source digests, unknown source files, unknown existing Intent Units, and proposed edits outside `impactScope.allowedSourceFiles`.

## Authority Boundary

AI may propose, but cannot accept. P4.0 requires human authority records for review and explicit false flags for:

- `aiAuthorityGranted`
- `selfAuthorized`
- `automaticAcceptanceClaimed`
- `patchApplied`
- `sourceMutated`
