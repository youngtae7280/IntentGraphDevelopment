# P9.14 Experimental C# Change Proposal and Delta Review

P9.14 adds the missing bridge from a mapped work request to a reviewable, non-applied change. It is deliberately a proposal boundary: the project workspace can record a graph delta, code-diff fragments, and required verification/evidence without writing to the source project.

## Proposal Workflow

```powershell
python tools/intentgraph.py add-experimental-csharp-change-proposal `
  --workspace <project-workspace> `
  --proposal <proposal-json>

python tools/intentgraph.py emit-experimental-csharp-project-workbench `
  --workspace <project-workspace> `
  --out <new-local-workbench-directory>
```

The proposal document must declare:

- one existing work item and its declared mapping candidate
- one or more changed graph node references
- zero or more added verification/evidence nodes and valid delta edges
- digest-backed code-diff fragments associated with changed C# facts
- verification and evidence requirements
- authority that remains non-applying, non-self-authorizing, and non-networked

The project workspace copies the validated proposal into its own `proposals/` directory. It records only `not-applied-review-required` proposals. No command in P9.14 accepts, applies, or self-authorizes a proposal.

## Workbench Behavior

When a proposal is present, the unified Workbench:

- adds a proposal node and proposed delta nodes/relations to the same graph as code facts and Intent Units
- gives changed existing code facts a proposal-delta border
- lists graph-delta steps; selecting one focuses and highlights the affected graph node
- shows the associated unified code diff in the inspector when the changed code fact is selected
- keeps proposal, graph delta, and code diff visibly review-only

## WindowsUtility Demonstration

The demonstration uses a non-applied SimpleInfo proposal: cancelling Browse Folder currently yields an empty list, which reaches `LoadDocuments` and clears the loaded CSD selection. The proposed interface, service, and view-model changes represent cancellation with `null`, while an explicitly selected empty folder remains an empty list.

The proposal has:

- 3 changed C# method facts and 3 code-diff fragments
- 1 proposed verification node and 1 verification relation
- safe regression-smoke and manual cancellation-observation requirements
- no source application, build, UI launch, printer operation, hardware action, approval, or release claim

The corresponding Workbench is:

```text
generated/windowsutility/experimental-csharp-project-workbench/p9.14/index.html
```

It is a review artifact, not proof that the WindowsUtility change has been accepted or applied.
