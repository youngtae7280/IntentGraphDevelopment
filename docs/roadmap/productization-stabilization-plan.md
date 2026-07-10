# Productization Stabilization Plan

Status: created in P8.0; rechecked in P8.28.

IntentGraph is not ready for productization. The current evidence proves a semantic overlay model, deterministic toy and B1 fixtures, a static workbench preview, and read-only WindowsUtility adoption artifacts. It does not yet prove a safe user-facing product.

## Non-Negotiable Boundary

Productization must remain blocked until real-project adoption evidence exists.

Blocked work:

- package or release a CLI/app as production-ready
- editor integration
- GitHub workflow integration
- team workflow automation
- AI code application authority
- broad source mutation workflows
- product readiness claims

Allowed work:

- readiness reports
- stabilization plans
- read-only inventories
- mapping acceptance boundaries
- non-applied proposal validation
- deterministic verifier and workbench projections

## Stabilization Tracks

### Track 1: Real-Project State

Goal: make the selected target safe to reason about.

Required evidence:

- target repository state is acceptable
- target state is recorded before and after each adoption slice
- target writes are not performed without explicit approval

### Track 2: Accepted Mapping

Goal: move from hypotheses to accepted mappings.

Required evidence:

- at least one WindowsUtility Intent Unit mapping is accepted
- all code refs and code fact refs resolve
- ambiguity remains explicit where unresolved
- stale/missing mapping failures are deterministic

### Track 3: Real Change Loop

Goal: prove the workflow on one real maintenance task.

Required evidence:

- non-applied proposal exists
- mapping and code fact consistency passes
- evidence requirements are explicit
- authority requirements are explicit
- rollback/stop conditions are explicit

### Track 4: Workbench

Goal: make the real-project process visible.

Required evidence:

- WindowsUtility projection exists
- projection includes graph, code facts, mappings, ambiguity, proposal, evidence, authority, and history
- users can inspect why a change is blocked or acceptable

### Track 5: Product Surface

Goal: decide the first shippable surface after adoption evidence exists.

Candidate order:

1. CLI report commands
2. static local workbench export
3. local app
4. editor integration
5. GitHub workflow integration
6. team workflow automation

Each step needs a separate build/borrow/integrate review.

## Phase H Entry Criteria

Phase H implementation can open only when:

- real-project repository state is acceptable
- accepted mapping evidence exists
- one real-project proposal loop passes deterministic verification
- evidence and authority records are complete
- real-project workbench projection exists
- user workflow benchmark has a baseline
- product surface decision record exists

Until then, Phase H is restricted to readiness and stabilization artifacts only.

## P8.28 Recheck

P8.28 found that several P8.0 blockers are now resolved or improved:

- WindowsUtility target state is clean/aligned.
- one shell/workspace mapping is accepted and verified.
- a non-applied shell/workspace proposal exists and validates.
- sandboxed build, UI launch, and screenshot evidence exist.
- a static WindowsUtility workbench projection exists.
- the user/coordinator compact `accept` response is recorded.

Productization remains blocked because:

- no real proposal application loop has passed.
- no first product surface decision exists.
- no packaging/release boundary exists.
- the workflow response is compact, not a detailed usability study.
- only the shell/workspace mapping is accepted.

The next safe stabilization slice is:

```text
P8.29 First Product Surface Decision Boundary Plan
```
