# P9.21 Guided Local Review Proposals

## Purpose

P9.21 removes the JSON-only bottleneck from the first local proposal path. A user can choose a previously recorded work item with a declared code mapping, describe the review, and state one verification and one evidence requirement from the loopback Workbench.

## Boundary

The guided form derives only stable references already present in the local project workspace:

```text
declared work item + declared mapping
  -> non-applied review proposal
  -> one verification requirement + one evidence requirement
  -> visible graph-delta review state
```

It records `codeDiffs: []`. It does not infer a patch, generate code, change C# source, apply a graph delta, run verification, collect evidence, or record approval.

The existing JSON import remains available for an advanced proposal that must carry a separately prepared, digest-backed code diff.

## Local API

`POST /api/draft-change-proposals` accepts exactly these strings:

- `proposalId`
- `workId`
- `title`
- `summary`
- `verificationKind`
- `verificationSummary`
- `evidenceKind`
- `evidenceSummary`

The server resolves the mapping ID and mapped code facts from local state. It accepts the request only when the work item exists, has one declared mapping candidate, and has no active proposal.

## Authority

The resulting proposal retains the existing P9.14 authority boundary:

```text
targetRepositoryMutation: false
automaticCodeApplication: false
graphMutationApplied: false
approvalRecorded: false
networkRequired: false
credentialAccessAllowed: false
```

The loopback server may write its own project-state artifact only. Static HTML exports remain read-only.

## Verification

- loopback server smoke covers request, mapping, guided proposal, receipt, rejection, and snapshot provenance preservation
- guided-proposal negative probes cover invalid IDs, unknown or unmapped work, blank input, physical-path persistence, invalid requirement kinds, and duplicate active proposals
- emitted static workbench validation remains deterministic and source-state preserving
