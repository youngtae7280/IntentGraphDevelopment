# Change History Model

Milestone: M5

This model defines the smallest semantic history slice for Phase 0. It does not replace Git.

Git records file history. IntentGraph records semantic graph history: which graph claims, evidence records, authority records, projections, or history nodes changed and why.

## Core Recurrence

```text
G_0 = initial intent graph
G_{t+1} = Apply(G_t, Delta_t)
```

`Delta_t` is represented by a `history.delta` node.

## B0 Delta Shape

Every `history.delta` in the B0 M5 subset must include:

- `sequence`
- `changeType`
- `summary`
- `status`
- `gitCommit`

Accepted deltas must:

- have a positive unique `sequence`
- have accepted sequence values contiguous from `1..n` in the B0 subset
- link to at least one changed node through a `changes` edge
- be authorized by an accepted `authority.record`
- preserve graph typecheck after application

## Git Boundary

`gitCommit` links semantic graph history to file history when a stable commit ID is available.

The M5 verifier checks that non-null Git commit IDs resolve to local commit objects. A syntactically valid hash is not enough.

An in-flight milestone delta cannot embed the commit hash that will be created by committing that same graph content without changing the graph digest. For this case only, B0 permits:

```json
{
  "gitCommit": null,
  "gitCommitBoundary": "pending-current-milestone"
}
```

The milestone review records the final commit hash after commit. Later graph updates should link to already-known commits where practical.

## Self-Referential Finalization Defer Decision

Phase 0 keeps one accepted B0 history delta with `gitCommit: null` and `gitCommitBoundary: "pending-current-milestone"`. This is an explicit defer decision, not a silent pass: writing the final commit hash into the graph changes the graph digest and requires either another semantic delta or an external finalization ledger.

Phase 1 must decide one of these strategies before broadening semantic history:

- keep the explicit pending boundary for self-referential in-repo graph edits
- move final commit linkage to an external append-only review ledger
- add a two-step finalization delta model that can close prior deltas without pretending the closing commit was known earlier

## M5 B0 History

B0 carries:

- `history.delta.initial-graph`, linked to the M1 graph creation commit
- `history.delta.m5-evidence-authority-history`, an accepted in-flight semantic delta for the M5 evidence, authority, and history refinement

## Verifier Expectations

The M5 verifier must fail if:

- history sequences are missing, duplicated, or non-positive
- accepted history sequences are not contiguous from `1..n`
- an accepted history delta has no `changes` edge
- an accepted history delta has no accepted authority
- a non-null `gitCommit` does not resolve to a local commit object
- a missing `gitCommit` lacks an explicit `pending-current-milestone` boundary
- semantic history is treated as equivalent to Git file history
