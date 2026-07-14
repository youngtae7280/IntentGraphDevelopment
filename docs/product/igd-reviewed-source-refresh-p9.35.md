# P9.35 Reviewed Source Refresh

## Purpose

P9.34 made an unchanged C# project resumable through `igd prepare`, `status`, and
`open`. P9.35 defines what happens after the source repository changes.

The refresh workflow must create a reviewable candidate revision before changing
the active IntentGraph workspace. It must preserve the previous revision, classify
snapshot-bound semantic records as retained or stale, and require acceptance of one
exact plan before activation.

This is a local semantic-overlay lifecycle operation. It is not source application,
automatic approval, automatic intent inference, or a target build.

## State Machine

```text
current
  -- source digest changed --> refresh-required
  -- igd refresh -----------> refresh-review-required
  -- discard exact plan ----> refresh-required
  -- accept exact plan -----> current at revision n + 1

refresh-review-required
  -- source/active/candidate drift --> blocked, no active change
  -- wrong plan id ----------------> blocked, no active change
```

`prepare` and `open` remain fail-closed while a refresh is required or awaiting
review. `status` reports the state and pending plan id without activating anything.

## Commands

```powershell
igd refresh <source-root> [--home <igd-home>]
igd refresh <source-root> --accept-plan <plan-id> [--home <igd-home>]
igd refresh <source-root> --discard-plan <plan-id> [--home <igd-home>]
```

The first command emits or reuses a deterministic pending plan. Acceptance and
discard both require the exact pending plan id.

## Artifact Boundary

For one project root under the per-user IGD home:

```text
workspace/                                      legacy/initial immutable revision
refresh/pending/refresh-plan.json               review contract
revisions/revision.rNNNN/workspace/             immutable candidate/accepted revision
revisions/revision.rNNNN/refresh-receipt.json   accepted transition receipt
revisions/revision.rNNNN/accepted-refresh-plan.json canonical accepted plan
intentgraph.launch.json                         atomic active-revision pointer and index
```

The plan records source, code-fact, and relation deltas; stale semantic records;
preservation counts/digests; candidate and active workspace digests; and a bounded
authority declaration. It never stores the source root path.

## Semantic Classification

Mappings are retained only when every referenced code fact still exists and its
canonical fact record is unchanged. All other mappings are stale.

Every proposal, review receipt, verifier result, and evidence decision is bound to
the prior snapshot and therefore becomes stale after a source refresh. These records
must remain available in the archived revision and must not remain active.

Work items remain, but their active workflow state is normalized:

- a work item with at least one retained mapping returns to `mapping-candidate`;
- a work item without retained mappings returns to `intake`;
- change and verification workflow claims are reset for the new snapshot.

Generic semantic foundation, evidence, authority, and history records may be carried
forward only when the candidate workspace validator accepts them. Snapshot-specific
records are replaced or archived. The accepted transition adds explicit refresh
verification, evidence, authority, and history records.

## Required Invariants

1. IGD never writes the target source repository during plan, accept, or discard.
2. Planning does not change the active workspace, launch record, or revision index.
3. A candidate must pass the normal project workspace validator before review.
4. Acceptance requires the exact plan id and unchanged source, active workspace,
   candidate workspace, launch record, and revision index.
5. Acceptance seals the prior full workspace before activating the candidate.
6. Both the archived and newly active workspaces remain independently valid.
7. Revision ids are contiguous and exactly one revision is active.
8. No stale mapping, proposal, receipt, verifier result, or evidence decision is
   silently presented as current.
9. Repeating the same plan input produces the same semantic plan and candidate.
10. Activation is one atomic launch-record replacement; revision workspaces are not
    renamed or swapped during acceptance.
11. Every accepted revision retains its canonical plan; launch, receipt, plan, and
    predecessor/current workspace semantics must agree under deterministic recomputation.
12. No AI judgment, network call, provider call, credential access, target build,
    target restore, target launch, or approval automation is required.

## Failure And Recovery

All validation failures are zero-active-write failures. A failed plan may remove only
its temporary staging directory. Before the launch pointer commit, a failed acceptance
leaves the prior revision active. After the atomic commit, the new revision is active.
There is no valid intermediate state that depends on rolling back a directory swap.

An accepted revision is never silently deleted or overwritten. A user may discard only
the exact pending plan, which leaves the active pointer unchanged.

## Explicit Non-Goals

- applying proposals or patches to target source;
- automatically migrating or reauthorizing stale proposals;
- automatic intent mapping or semantic equivalence inference;
- target build, restore, test, or launch;
- graph visualization or renderer refinement;
- cryptographic signing, remote identity, provider APIs, team synchronization;
- editor, GitHub, release, or installer integration.

## Exit Gate

P9.35 is complete only when the test plan in
`docs/testing/p9.35-reviewed-source-refresh-test-plan.md` passes, a deterministic
evidence report is committed, WindowsUtility-scale performance is measured, the
milestone review reaches Level 4, and the worktree is clean and synchronized with
`origin/main`.
