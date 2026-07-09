# Proposal Validator Contract

Milestone: M6

This contract defines the deterministic validator for M6 AI proposal fixtures.

## Scope

Inputs:

```text
docs/examples/b0-python-cli-calculator.graph.json
docs/proposals/b0-ai-add-invalid-operation-test.proposal.json
docs/proposals/b0-ai-invalid-self-authorized.proposal.json
```

Output:

```text
generated/b0-python-cli-calculator/proposal-validation-report.json
```

Command:

```powershell
python tools/validate_proposal.py --graph docs/examples/b0-python-cli-calculator.graph.json --proposal docs/proposals/b0-ai-add-invalid-operation-test.proposal.json --proposal docs/proposals/b0-ai-invalid-self-authorized.proposal.json --out generated/b0-python-cli-calculator/proposal-validation-report.json
```

## Contract

```text
ValidateProposal(G, Proposal) -> ProposalValidation
```

For M6:

- proposal parsing is deterministic
- base graph digest must match
- proposed IDs must be stable and non-conflicting
- proposed edges must have endpoints in the base graph or in added nodes
- proposed node and edge kinds must stay inside the B0 M6 fixture lane
- required evidence refs must point to accepted evidence records
- required accepted evidence is treated as base-graph prerequisite evidence in M6
- `decision.authorityRecordId` must reference an accepted non-AI authority record in the graph
- accepted AI proposals require non-AI decision authority
- unsupported operations fail closed
- simulated post-delta GraphIR and evidence/authority/history semantics must pass

The aggregate report passes only when each proposal result matches its `expectedValidation`, the fixture set includes at least one accepted proposal and one rejected proposal, and no accepted proposal treats AI as authority.

## Non-Goals

M6 does not implement:

- AI model calls
- context retrieval
- broad proposal search
- automatic graph mutation
- automatic authority
- OPA/Rego policy evaluation
- workbench UI
