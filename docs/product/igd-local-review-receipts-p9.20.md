# P9.20 Local Review Receipts

P9.20 makes the verification and evidence requirements of a review-only C# change proposal inspectable and actionable without pretending that a build, test, runtime observation, source change, or approval occurred.

The local workflow is now:

```text
work request
-> declared code mapping candidate
-> non-applied change proposal
-> inspect graph delta and code diff
-> record a non-executing review receipt for one verification/evidence requirement pair
```

## Review Receipt Contract

The loopback Workbench and CLI accept exactly one
`intentgraph-experimental-csharp-review-receipt` document. It must reference:

- one existing non-applied proposal;
- one verification requirement and one evidence requirement declared by that proposal;
- one explicit review result: `reviewed-pass`, `reviewed-fail`, or `review-blocked`;
- a sorted review scope that includes the proposal itself; and
- the fixed non-executing, non-applying authority boundary.

A receipt is saved beneath the local project workspace only after deterministic validation. The Workbench then exposes the receipt through its verification/evidence/history records and marks the affected work item as `review-receipt-recorded`.

## What A Receipt Means

A receipt is a durable record that a person reviewed a declared requirement pair. It is not a test result and not evidence collection by itself. In particular, recording one never:

- modifies a C# source file or applies a graph delta;
- runs build, restore, launch, test, hardware, provider, or network operations;
- collects runtime evidence or claims that an execution requirement passed;
- accepts a mapping, approves a proposal, or authorizes source application.

The local server provides `POST /api/review-receipts` with exactly
`{ "receipt": { ... } }`. The static exported HTML intentionally remains read-only and contains no receipt API client.

## Verification

The repeatable local server smoke now records a work request, a mapping candidate, a review-only proposal, and one `reviewed-pass` receipt in a temporary project workspace. It proves that snapshot provenance is unchanged and rejects an executing receipt authority claim.

The P9.20 negative harness additionally rejects malformed roles, unknown proposal or requirement references, invalid result/scope, executing authority, forbidden source text, and duplicate requirement-pair receipts.
