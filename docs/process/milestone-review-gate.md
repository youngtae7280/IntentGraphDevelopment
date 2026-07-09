# Milestone Review Gate

Use this gate at the end of every milestone before starting the next one.

## Review Questions

1. What was the intended thesis for this milestone?
2. What artifact was produced?
3. Which benchmark was run?
4. What existing systems were compared?
5. Did the result prove, weaken, or change the thesis?
6. Did we discover a stronger prior-art system?
7. Should existing work be promoted, demoted, adapted, or deleted?
8. What must change before the next milestone?

## Quality Levels

### Level 0: Activity

Files changed, but no thesis was tested.

Do not continue.

### Level 1: Local Prototype

A small prototype exists, but it is not compared against prior art and has no benchmark.

Do not use as product evidence.

### Level 2: Benchmarked Slice

A small slice works and has been compared against relevant existing systems.

Allowed to continue if gaps are understood.

### Level 3: Round-Trip Slice

The slice proves a graph-to-code-to-graph loop under declared assumptions.

This is the first level that counts as real IntentGraph progress.

### Level 4: Evidence-Bearing Slice

The slice preserves evidence, authority, and change history through the development loop.

This is the target quality bar for core architecture.

## Stop Rule

If a milestone does not reach its declared quality level, do not proceed to the next milestone. Diagnose and either improve, reduce scope, or change direction.
