# P9.22 Guided Local Review Receipts

## Purpose

P9.22 removes the JSON-only bottleneck from local review receipt recording. A user can choose an unreviewed verification/evidence requirement pair from a recorded proposal, state the review outcome, and record a non-executing review receipt in the loopback Workbench.

## Boundary

```text
recorded proposal + unreviewed requirement pair + user review result
  -> non-executing review receipt
  -> verification/evidence/history visibility in the project graph
```

The form resolves only requirement IDs that already exist in the selected proposal. It fixes the review scope to the proposal plus its verification and evidence requirement pair.

It does not run a test, build, smoke check, runtime observation, or evidence collector. It does not apply a code diff or graph delta, approve the proposal, generate a patch, or change C# source.

The JSON import remains an advanced path for a receipt that needs a more specialized declared review scope.

## Local API

`POST /api/draft-review-receipts` accepts exactly these user-entered strings:

- `receiptId`
- `proposalId`
- `verificationRequirementId`
- `evidenceRequirementId`
- `result`: `reviewed-pass`, `reviewed-fail`, or `review-blocked`
- `summary`

The server accepts the request only when the proposal and requirement pair are known, the pair does not already have a receipt, and all fields obey the local safe-persistence boundary.

## Graph Presentation

The full graph remains complete at every lens. Zoom changes the viewed graph-space area while the renderer compensates node, edge, and label size so they stay within a stable screen-scale range. Code facts are rendered as small, flat community-coloured points; code capsules are thin outlined community markers rather than filled blocks. The project marker remains labeled, while semantic records and code facts disclose labels through an impact/focus lens, selection, or search instead of filling the viewport at high zoom.

## Authority

The recorded receipt retains the existing non-executing, non-approving receipt authority:

```text
targetRepositoryMutation: false
verificationExecution: false
evidenceCollectionExecution: false
graphMutationApplied: false
approvalRecorded: false
networkRequired: false
credentialAccessAllowed: false
```

The loopback server writes only its own local project-state artifact. Static HTML exports remain read-only.

## Verification

- loopback server smoke covers request, mapping, guided proposal, guided receipt, projection reload, rejection, and snapshot provenance preservation
- guided receipt negative probes cover unsafe IDs and paths, unknown proposals, invalid requirement references, blank summaries, invalid outcomes, and duplicate requirement pairs
- the public CLI facade records the same receipt boundary in an isolated local workspace
- the full WindowsUtility workbench exposes every eligible requirement pair without submitting a receipt during browser inspection
