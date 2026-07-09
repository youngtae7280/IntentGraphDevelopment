# Authority Model

Milestone: M5

This model defines the smallest authority envelope for Phase 0. It is not a policy engine and does not replace Open Policy Agent, CODEOWNERS, protected branches, in-toto layouts, or TUF roles.

IntentGraph records who proposed a claim or delta, what deterministic validator was used, who or what decided, and whether the decision is accepted.

## Core Rule

AI may propose. AI must not be final authority for an accepted graph state.

```text
AIOutput = Proposal
AuthorityAccepted(a) requires decidedByType != "ai"
```

## B0 Authority Shape

Every `authority.record` in the B0 M5 subset must include:

- `proposer`
- `proposerType`
- `requiredAuthority`
- `validator`
- `decidedBy`
- `decidedByType`
- `decision`
- `decisionStatus`

If `decisionStatus` is `accepted`, the authority record must authorize at least one evidence record, history delta, or projection target through an `authorizes` edge.

For the M5 B0 subset, accepted authority may authorize only these target kinds:

- `evidence.record`
- `history.delta`
- `projection.target`

Actor type fields are normalized as lower-case enums. Unknown actor types fail validation. `AI`, `ai`, and other casing variants normalize to `ai` and cannot be final authority for an accepted record.

## Validator Boundary

`validator` names the deterministic check or review gate used for the decision. It is not authority by itself.

Examples for B0:

- `m1-manual-review`
- `m5-semantic-verifier`

## Acceptance Boundary

An accepted authority record means the named decision is accepted for its explicitly authorized targets.

It does not automatically accept:

- all evidence records
- all history deltas
- future AI proposals
- generated code
- workbench projections

Each accepted target must be connected by an `authorizes` edge.

## M5 Verifier Expectations

The M5 verifier must fail if:

- an accepted authority record has `decidedByType: "ai"`
- an accepted authority record authorizes no target
- an accepted authority record authorizes only unsupported target kinds
- an accepted authority record uses an unknown actor type
- an accepted evidence record references missing or unaccepted authority
- an accepted history delta has no accepted authorizing authority
- imported facts or generated code are treated as authority
