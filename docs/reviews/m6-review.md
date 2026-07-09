# M6 Milestone Review

Milestone: M6 - AI Proposal Boundary
Date: 2026-07-09
Reviewer: IntentGraphDevelopment Roadmap Orchestrator

Declared quality target: Level 4

## Produced Artifacts

- `docs/ai/proposal-format.md`
- `docs/ai/proposal-validator-contract.md`
- `docs/proposals/b0-ai-add-invalid-operation-test.proposal.json`
- `docs/proposals/b0-ai-invalid-self-authorized.proposal.json`
- `tools/validate_proposal.py`
- `generated/b0-python-cli-calculator/proposal-validation-report.json`
- `docs/reviews/m6-review.md`

## Benchmarks Run

Commands run:

```powershell
python tools/validate_proposal.py --graph docs/examples/b0-python-cli-calculator.graph.json --proposal docs/proposals/b0-ai-add-invalid-operation-test.proposal.json --proposal docs/proposals/b0-ai-invalid-self-authorized.proposal.json --out generated/b0-python-cli-calculator/proposal-validation-report.json
python -m py_compile tools/validate_proposal.py
python -m json.tool docs/proposals/b0-ai-add-invalid-operation-test.proposal.json > $null
python -m json.tool docs/proposals/b0-ai-invalid-self-authorized.proposal.json > $null
```

Proposal report summary:

```text
result = pass
validatorContract = m6-proposal-validator-v0
proposalCount = 2
acceptedForApplication = 1
rejected = 1
aiOutputTreatedAsAuthority = false
automaticApplication = false
accepted.authorityGranted = true
accepted.proposalDigest = sha256:...
accepted.postDelta.graphirValid = true
accepted.postDelta.semanticValidation = pass
```

Negative checks:

- AI self-authorized accepted proposal is rejected
- duplicate node ID proposal is rejected
- accepted proposal missing deterministic checks is rejected
- accepted proposal missing accepted evidence reference is rejected
- accepted proposal with stale base graph digest is rejected
- accepted proposal that tries to add an authority record is rejected
- accepted proposal that corrupts evidence/authority/history semantics is rejected by post-delta validation

## Prior-Art Comparison

M6 stayed inside the M0 decision:

- Graphify and RepoGraph are treated as context/proposal pressure, not authority systems
- Codex-style review is treated as review/proposal/evidence input, not authority
- no AI runtime, repository graph retrieval engine, or broad agent framework was implemented
- no OPA/Rego policy engine was invented

Sources checked for M6 are recorded in `docs/ai/proposal-format.md`.

## Result

Proved for the B0 slice:

- AI-origin proposal data can be represented as a deterministic JSON artifact
- proposal validation checks base graph digest, structural apply-ability, required evidence, deterministic check list, and authority decision
- proposal validation requires `decision.authorityRecordId` to reference accepted non-AI graph authority
- required accepted evidence is treated as base-graph prerequisite evidence for M6, not proof that the proposed delta is already correct
- proposal validation simulates the post-delta graph and reruns bounded GraphIR plus M5 semantic checks
- proposal validation fails closed for M6 mutations outside `test.case` / `tested_by`
- an AI-origin proposal can be accepted for application only when final decision authority is non-AI
- an AI self-authorized proposal is rejected even when it declares `decisionStatus: "accepted"`
- proposal validation does not mutate the graph automatically

Changed:

- M6 adds a proposal boundary beside the M5 evidence/authority/history verifier
- accepted proposal status means accepted-for-application, not silently applied graph state

## Round-Trip Status

The M5 round-trip remains the current metadata-backed graph/code/reconstruction proof.

M6 does not change the graph or generated code. It validates proposal artifacts against the current B0 graph digest.

## Evidence Status

The accepted proposal requires an accepted evidence reference:

```text
evidence.record.roundtrip-report
```

The rejected proposal has no accepted evidence reference and fails validation.

## Authority Status

Authority is the central M6 result:

- accepted AI-origin proposal has `decidedByType: "human"`
- rejected AI-origin proposal has `decidedByType: "ai"`
- report states `aiOutputTreatedAsAuthority = false`
- report states `automaticApplication = false`

## History Status

M6 does not apply proposal deltas to graph history. That is deliberate: proposal validation and graph mutation are separate boundaries.

If a future milestone applies accepted proposals, it must create an accepted `history.delta` and rerun the M5/M6 authority checks.

## Issue Review

| ID | Severity | Issue | Resolution |
|---|---|---|---|
| M6-P1-001 | P1 | `CanApplyDelta` did not run GraphIR validation after applying the proposed delta. | Resolved by simulating the post-delta graph and running bounded GraphIR subset validation. |
| M6-P1-002 | P1 | `updateNodeAttributes` could corrupt evidence/authority/history semantics after pre-delta evidence checks. | Resolved by restricting M6 updates to `test.case` nodes and running M5 semantic validation on the post-delta graph. |
| M6-P1-003 | P1 | `RequiredAuthorityGranted` only checked proposal decision fields, not graph authority. | Resolved by requiring `decision.authorityRecordId` to reference an accepted non-AI `authority.record` with matching required authority. |
| M6-P1-004 | P1 | M6 promotion to M7 was premature while validator false acceptances existed. | Resolved by reverting promotion, fixing validator gaps, and only re-promoting after red-team probes passed. |
| M6-P2-001 | P2 | Accepted-for-application could be confused with already-applied graph state. | Resolved by documenting that the validator does not mutate the graph and by reporting `automaticApplication = false`. |
| M6-P2-002 | P2 | M6 could accidentally duplicate Graphify/RepoGraph context retrieval work. | Resolved by scoping M6 to proposal validation and recording prior-art pressure in the proposal format doc. |
| M6-P2-003 | P2 | The first validator shape could be read as allowing proposal mutation of authority/evidence/history records. | Resolved by failing closed outside `test.case` node and `tested_by` edge proposals for M6. |
| M6-P2-004 | P2 | Required evidence could be read as proposal-specific proof when it is currently base-graph prerequisite evidence. | Resolved by labeling required accepted evidence role as `base-graph-prerequisite`. |
| M6-P2-005 | P2 | Proposal report lacked per-proposal digests. | Resolved by adding canonical `proposalDigest` to each proposal result. |

No unresolved P0/P1 issues remain. All P2 issues are resolved.

## Decision

Decision: continue

Achieved quality level: Level 4.

M6 passes its declared quality bar.

## Required Changes Before Next Milestone

M7 must:

- define visualization/workbench boundaries after the proven core loop
- compare against existing visualization/workbench tools
- keep workbench state as projection/report, not authority
- avoid building a full IDE
- show graph, code projection, evidence, authority, round-trip, and proposal state only as a bounded prototype or boundary
