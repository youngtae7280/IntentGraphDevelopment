# P9.27 Diff-Backed Guided Code Change Proposals

P9.27 closes the largest gap in the normal local Workbench flow: a user no longer
needs to prepare and import a full proposal JSON document to review an actual code
change. The existing `Draft code change` form accepts one or more hunk-only unified
diffs for code facts already linked to the selected work item.

The resulting artifact remains a non-applied proposal. It changes the local IGD
project workspace only; it does not edit the nested source snapshot or the target
repository.

## Daily Workflow

```text
work request
  -> declared code mapping
  -> select mapped code facts
  -> enter unified diff hunks
  -> deterministic snapshot validation
  -> graph and code delta proposal
  -> human review / later verification and evidence
```

The form shows every mapped code fact with its symbol label, source file, kind, and
source range. The user selects only the facts that a proposed patch changes. Unselected
mapped facts remain impact context and are not falsely marked as changed.

After recording, the same Workbench exposes:

- the changed graph nodes and proposal relations;
- one code-diff fragment on each changed code fact;
- verification and evidence requirements;
- the non-applying authority boundary; and
- the durable request, mapping, proposal, and requirement stages.

## Deterministic Diff Boundary

Each guided diff contains only:

```json
{
  "codeFactId": "mapped-code-fact-id",
  "unifiedDiff": "@@ -old,count +new,count @@\n..."
}
```

The server derives the diff identifier, source file, and before-source digest. It
rejects a diff unless:

- the code fact belongs to the selected work mapping;
- each fact appears at most once;
- the nested snapshot file still matches the extracted fact digest;
- every hunk header and old/new line count is valid;
- context and removed lines match the immutable snapshot exactly;
- hunks are ordered and non-overlapping;
- at least one real source change exists; and
- at least one hunk overlaps the mapped code fact range.

The validator reads the nested immutable snapshot only. No target path, credential,
provider, build, test, launch, or network access is involved.

## WindowsUtility Demonstration

The P9.27 generated Workbench records a real review candidate over the copied
WindowsUtility snapshot: preserve the current CSD selection when folder browsing is
cancelled. The proposal maps and changes three facts:

- `ICsdBrowseService.BrowseFolder`;
- `CsdBrowseService.BrowseFolder`; and
- `SimpleInfoViewModel.BrowseFolder`.

It carries three snapshot-checked diffs, four durable work stages, 8,189 graph nodes,
and 7,996 relations. Selecting the proposal stage focuses eight relevant nodes and
eleven relations. Selecting a changed code node shows its source range, digest, delta
state, and exact unified diff in the inspector.

## Non-Goals

- no AI patch synthesis;
- no source or snapshot mutation;
- no diff application or graph-delta application;
- no build, test, launch, or evidence execution;
- no proposal approval or automatic authority; and
- no network, provider API, credential, editor, or team-service integration.

The next product slice should consume typed verifier results so a proposed change can
move from authored diff to trustworthy, inspectable verification evidence without
manual JSON assembly.
