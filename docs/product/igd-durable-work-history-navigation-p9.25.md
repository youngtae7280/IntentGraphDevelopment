# P9.25 Durable Work History Navigation

P9.25 defines one IGD request as one work item and makes every recorded work item
navigable from one project Workbench.

## Product Contract

- one user request is recorded as one stable `workItemId`
- one project Workbench lists every work item retained by that IGD project workspace
- previous/next controls move between work items without opening another HTML file
- a second previous/next control moves through the selected work item's ordered stages
- selecting a stage focuses the same unified graph on its additions, changes, context,
  relations, code diff records, verification, evidence, authority, and history
- new work lifecycle mutations append a durable `workStageRevisions[]` record with
  before/after work-history digests and referenced graph/code delta identifiers

The recorded stage sequence currently covers:

1. request recorded
2. mapping candidate recorded or expanded
3. graph/code change proposal recorded
4. verification and evidence requirements recorded
5. non-executing review receipt recorded

The proposal and requirement views share one revision because the current local
operation writes them atomically. The UI does not manufacture a second state
transition where none occurred.

## Live And Static Surfaces

The loopback Workbench is the current project view. It checks a small local
`/api/revision-head` resource and reloads only when the project-state version changes.
This means an IGD CLI mutation or a Workbench form mutation becomes visible in an
already open page without repeatedly downloading the full graph.

The exported static HTML is an immutable review snapshot. It never polls, never
overwrites itself, and is labeled `revision snapshot`. A new static export creates a
new review artifact rather than changing an old one.

## History Boundary

"All work" means all work items recorded in the selected IGD project workspace. Work
performed before IGD adoption is not silently invented. It must be imported through a
separate retrofit/history boundary if it should appear.

P9.25 records durable lifecycle digests and graph/code delta references. It does not
yet store a complete copy of the full 8,000-node graph at every stage. The Workbench
replays each stage as a focused delta over the validated current unified graph and
labels older P9.24-only records as `legacy record-derived`.

## Safety Boundary

P9.25 does not apply a graph delta, edit the target repository, execute a build or
test, collect runtime evidence, approve a proposal, or automate acceptance. Revision
authority flags for those actions remain false.
