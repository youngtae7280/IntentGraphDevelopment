# P9.36 Reviewed Proposal Application Product Contract

Status: completed plan-only contract for G1.
Implementation status: not authorized by this document.

## Purpose

P9.35 can activate a reviewed immutable source snapshot after an external source
change. It cannot apply an accepted code proposal to source. P9.36 defines the
smallest product contract that can close that gap without turning IGD into a source
control system, arbitrary command runner, or AI authority.

The first implementation is intentionally a one-file C# application transaction. It
must prove a complete safe loop before multi-file, rename, binary, project-file, or
Git-integrated application is considered.

## Inputs Required Before Any Apply Plan

An apply plan may be created only when all inputs resolve against the active IGD
revision:

1. One current `not-applied-review-required` change proposal with a validated unified
   diff for exactly one mapped code fact in one existing `.cs` file.
2. A current passing verifier result and accepted human evidence decision for every
   proposal requirement pair. The supplied evidence must identify the proposal digest
   and the expected after-source digest from an isolated candidate source copy.
3. A current active revision whose source digest matches the live source root exactly.
4. A human-only application approval record for the exact application plan. Evidence
   acceptance does not imply proposal approval or source-application authority.
5. A source root and touched file that pass containment and reparse-point checks.

The first product scope rejects file creation, deletion, rename, binary patches, mode
changes, `.sln`, `.csproj`, `.git`, `.github`, `bin`, `obj`, scripts, links, junctions,
and paths outside the mapped C# source file.

## Apply Plan And Approval Records

The future G2 implementation must emit a deterministic non-applied record with:

```text
artifactRole: intentgraph-local-proposal-application-plan
status: intentgraph-local-proposal-application-review-required
scope: p9.36-reviewed-single-file-csharp-application
```

The plan binds:

- proposal ID and canonical digest;
- mapping, code-fact, unified-diff, and touched relative-path digests;
- before and expected-after file digests;
- before and expected-after aggregate source digests;
- active revision, workspace, and launch-record digests;
- accepted verifier-result and evidence-decision IDs and digests;
- a staged post-apply refresh candidate digest;
- rollback preimage digest, transaction-journal digest, and source containment facts;
- explicit non-goals and required human approval.

The future approval record is separate:

```text
artifactRole: intentgraph-local-proposal-application-approval
status: intentgraph-local-proposal-application-approved
permission: proposal.apply
actorType: human
role: maintainer
```

It must bind one plan ID and digest. It is local, declared, and not cryptographically
authenticated. It must never be synthesized from a verifier result, evidence decision,
AI response, or command-line default.

## Transaction Design For G2

G2 must use the following order. A plan or approval alone performs no target write.

1. Revalidate every plan, approval, proposal, evidence, source, workspace, launch,
   and containment digest under the project session lock.
2. Apply the exact unified diff to an isolated source copy and build the post-apply
   code-fact and refresh candidate before touching target source.
3. Persist an immutable local transaction journal and a preimage backup before the
   target write. The journal blocks further apply attempts until it is completed or
   explicitly recovered.
4. Write the candidate bytes to a sibling staging file and atomically replace the one
   existing target `.cs` file. The first G2 scope is one file because a filesystem
   offers no truthful all-or-nothing guarantee for an arbitrary multi-file change.
5. Re-read the live file and aggregate source digest. If either differs from the plan,
   restore the preimage and record recovery.
6. Atomically activate the already-staged local refresh candidate. It must identify
   the exact source after-digest and the application transaction.
7. Write an application receipt linking plan, approval, preimage, afterimage,
   verification evidence, refresh receipt, graph delta, code delta, and history.
8. Remove only verified temporary staging files. Preserve immutable receipt, journal,
   and recovery evidence.

If any step after the source replacement cannot prove completion, the product must
restore the exact preimage or leave a durable recovery-required journal. It must never
claim the prior overlay revision is current for changed source.

## Verification Boundary

G2 does not execute arbitrary commands in the target repository. The first product
apply accepts only already-recorded, accepted external verification evidence bound to
the proposal and isolated after-source candidate. Its own deterministic verification is
source preimage/afterimage, patch scope, transaction, refresh, receipt, and history
integrity.

G3 may decide how to collect build/test/runtime evidence for real tasks. Any command
execution, generated-file handling, or sandboxing must be its own authority boundary.

## Source-Control Decision

Git remains the source-history authority but is not part of the G2 write path.

- `git apply --check` is a useful comparison for read-only patch applicability, but
  G2 relies on the existing snapshot-backed diff validator so it works without a Git
  dependency.
- `git apply --index` and `git apply --3way` are excluded because they can alter the
  index and may leave conflicts for the user to resolve.
- `git worktree` is excluded because it changes repository administrative metadata.
- `git status` is not an IGD preflight because Git may refresh index stat information.
- IGD must not stage, commit, push, create branches, or modify `.git` during G2.

Relevant Git behavior is documented in the official
[git-apply](https://git-scm.com/docs/git-apply),
[git-worktree](https://git-scm.com/docs/git-worktree), and
[git-status](https://git-scm.com/docs/git-status) manuals.

## Workbench Requirements

Before an approval, the Workbench must show:

- exact file, source range, unified diff, before/after digests, and mapped Intent
  Units;
- the proposal, verifier results, evidence decisions, required `proposal.apply`
  approval, and all missing prerequisites;
- staged refresh impact: retained/stale mappings, proposals, evidence, authority, and
  history;
- rollback preimage and the one-file limitation.

After completion or recovery, it must show current source and graph deltas, transaction
state, receipt, refresh revision, and any recovery requirement. This is a G2 functional
requirement; visual polishing remains deferred to G6.

## Explicit Non-Goals

- no source write in P9.36;
- no automatic AI proposal approval or application;
- no multi-file transaction, rename, binary, project-file, or Git-index operation;
- no target build, restore, test, launch, package, provider, network, credential,
  signing, release, editor, or team operation;
- no cryptographic identity claim;
- no graph-delta application independent of the code and refresh transaction.

## G1 Exit Criteria

P9.36 completes only when this contract, the linked test plan, build/borrow/integrate
decision, P8.41-P8.46 comparison, and plan review are committed and validate cleanly.
It does not authorize G2 source writes.
