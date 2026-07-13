# P9.30 Local Evidence Decision Authority

P9.30 turns a current typed verifier observation into an explicit local human decision
without turning that decision into proposal approval or code application. The local
Workbench can record `accepted` or `rejected` for one current verifier result and expose
the resulting evidence, authority, work readiness, graph, and timeline state.

## Daily Workflow

```text
non-applied proposal
  -> external verifier result imported as an observation
  -> current result selected for review
  -> human reviewer records accept or reject
  -> evidence and authority records become inspectable
  -> work readiness is recomputed
  -> proposal remains unapproved and unapplied
```

## Decision Contract

Every reviewer declares `actorType: human`. Allowed roles are:

- `maintainer`
- `quality-reviewer`
- `security-reviewer`

Acceptance requires `evidence.accept`; rejection requires `evidence.reject`. Both are
limited to `local-project-workspace`. The reviewer identity is a local session
declaration and is not cryptographically authenticated.

Only the current result for a declared proposal verification/evidence pair may be
decided. Acceptance is valid only for a passing result. A fail or blocked result cannot
be accepted. One verifier result has at most one decision, and stale or superseded
results fail zero-write.

## Work Readiness

The readiness transition is deliberately pair-aware:

- a rejected current result makes the work item `blocked`;
- some but not all required current pairs accepted remain `verification-observed`;
- every required current pair accepted with a passing result makes the work item
  `verified`; and
- a newly superseding result returns that pair to pending decision rather than inheriting
  an older decision.

The graph records separate decision, authority, and evidence nodes and relations. Every
decision creates exactly one durable work-stage revision. The proposal remains
unapproved and unapplied throughout.

## Concurrency and Immutability

Decision writes share the project workspace lock and state-last atomic commit boundary.
Concurrent duplicate decisions produce exactly one winner. Cross-operation contention
preserves both legitimate records without a lost update. Source, snapshot, and target
repository state remain immutable.

## Workbench Visibility

The Workbench exposes current decision eligibility, reviewer role and permission,
accepted/rejected state, evidence digest, authority record, work readiness, and the
durable stage revision. Static export remains read-only; guided decision intake is a
loopback local-workspace capability.

The same slice refines rendering without changing graph structure. Effective `100x`
combines renderer `24x` with virtual geometry `4.1667`. At maximum zoom a selected edge
uses `0.065px` rendered width and `0.34` opacity. Cached viewport-local etched
obsidian/titanium sprites use asymmetric spectral etching for a darker technical surface
without per-frame full-graph material work. Distant ordinary code facts remain present
in the graph but skip the expensive material pass until they become structural,
selected, changed, searched, or locally detailed.

Decision-derived verification, evidence, and history records are re-derived from the
decision artifact during validation. Coverage, work readiness, and all six
decision-authority relations are likewise re-derived for every projection; internally
consistent but fabricated counts or missing authority relations are blockers.

## Non-Goals

- no cryptographic reviewer authentication;
- no AI reviewer authority;
- no verifier execution or evidence-byte upload;
- no proposal approval or graph/code application;
- no source, snapshot, or target repository mutation;
- no network, provider API, credential, signing, or release authority; and
- no claim that local evidence acceptance is enterprise trust or productization
  authority.
