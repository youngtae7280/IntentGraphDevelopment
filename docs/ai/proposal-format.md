# AI Proposal Format

Milestone: M6

This format defines the smallest Phase 0 boundary for AI-proposed graph/code deltas. It is not an AI runtime, agent framework, repository context graph, or policy engine.

## Prior-Art Pressure

Graphify and RepoGraph strengthen the case for graph-shaped AI context, but they remain context/proposal systems for IntentGraph purposes. Codex-style code review can provide high-signal review observations, but review output is still proposal/evidence input, not authority.

Sources checked for M6:

- Graphify official site: <https://graphifylabs.ai/>
- Graphify project page: <https://graphify.net/>
- RepoGraph paper: <https://arxiv.org/abs/2410.14684>
- RepoGraph repository: <https://github.com/ozyyshr/RepoGraph>
- OpenAI Codex GitHub review docs: <https://developers.openai.com/codex/integrations/github>

Decision pressure remains the M0 decision: differentiate. IntentGraph may later integrate context tools, but Phase 0 only defines proposal validation and authority boundaries.

## Core Rule

```text
AI(Context(G, q)) -> Proposal
```

The proposal is not accepted graph state.

```text
Accept(Proposal, G) <=>
  ProposalWellFormed(Proposal)
  and BaseGraphDigestMatches(Proposal, G)
  and CanApply(G, Proposal.delta)
  and DeterministicChecksPass(Proposal.delta, G)
  and RequiredEvidenceAccepted(Proposal.delta)
  and RequiredAuthorityGranted(Proposal.delta)
```

AI confidence, fluency, or apparent correctness is never authority.

In GraphIR v0.2, AI proposal output is also not an Intent Unit. A proposal may suggest new internal graph facts or future unit membership, but accepted unit membership requires a deterministic graph delta and explicit authority.

## Proposal Shape

```json
{
  "proposalVersion": "0.1.0",
  "proposalId": "ai.proposal.b0.example",
  "benchmarkId": "B0-python-cli-calculator",
  "source": {
    "kind": "ai",
    "system": "synthetic-m6-boundary-fixture"
  },
  "target": {
    "graphId": "ig.bench.b0.python-cli-calculator",
    "baseGraphDigest": "sha256:..."
  },
  "intent": {
    "summary": "Short explanation of the proposed graph delta."
  },
  "delta": [
    {
      "op": "addNode",
      "node": {}
    },
    {
      "op": "addEdge",
      "edge": {}
    }
  ],
  "requiredAcceptedEvidence": ["evidence.record.roundtrip-report"],
  "deterministicChecks": [
    "ProposalWellFormed",
    "BaseGraphDigestMatches",
    "CanApplyDelta",
    "AuthorityGranted"
  ],
  "decision": {
    "decisionStatus": "accepted",
    "authorityRecordId": "authority.record.m5-human-review",
    "requiredAuthority": "roadmap-orchestrator",
    "validator": "m6-proposal-validator",
    "decidedBy": "IntentGraphDevelopment Roadmap Orchestrator",
    "decidedByType": "human"
  },
  "expectedValidation": "accepted"
}
```

## Supported M6 Delta Ops

The M6 validator supports only:

- `addNode`
- `addEdge`
- `updateNodeAttributes`

The B0 accepted fixture uses `addNode` and `addEdge` only.

The M6 B0 validator fails closed for graph-domain mutation outside the accepted fixture lane:

- proposed node kind must be `test.case`
- proposed edge kind must be `tested_by`
- `updateNodeAttributes` may update only `test.case` nodes

Unsupported operations fail closed.

## Human Review Boundary

An accepted AI proposal must have:

- `source.kind: "ai"`
- deterministic checks listed
- required accepted evidence references
- a required accepted evidence role of base-graph prerequisite unless proposal-specific evidence exists
- `decision.decisionStatus: "accepted"`
- `decision.authorityRecordId` referencing an accepted non-AI authority record in the graph
- `decision.decidedByType` normalized to a non-AI actor type
- `decision.requiredAuthority`
- `decision.validator`

If the deciding actor is AI, the proposal is rejected even if the delta is structurally valid.

For M6, accepted proposal deltas are simulated and validated after application. The validator runs a bounded GraphIR subset check and the M5 evidence/authority/history semantic checks against the simulated post-delta graph before returning accepted-for-application.

## M6 Fixture Proposals

- `docs/proposals/b0-ai-add-invalid-operation-test.proposal.json` is expected to validate as accepted-for-application.
- `docs/proposals/b0-ai-invalid-self-authorized.proposal.json` is expected to validate as rejected.

Neither proposal is applied silently by the validator. Application remains a separate accepted graph delta operation.
