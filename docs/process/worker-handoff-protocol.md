# Worker Handoff Protocol

Use this protocol when assigning work to another agent or worker.

## Required Context

Every handoff must include:

- the core thesis
- the exact capability being worked on
- the current prior-art decision
- what must not be implemented
- benchmark and acceptance criteria
- expected output artifacts
- review gate to run afterward

## Handoff Shape

```text
Task:

Why this matters:

Core thesis connection:

Inputs:

Required reading:

Allowed work:

Explicit non-goals:

Prior-art constraints:

Benchmark:

Acceptance criteria:

Validation commands or review steps:

Completion report requirements:
```

## Anti-Drift Rules

- Do not ask a worker to implement a broad system.
- Do not combine prior-art research and implementation in the same slice unless the research is already complete.
- Do not let a worker preserve weak custom work when a stronger existing system should be integrated.
- Do not accept "it works" without benchmark and review notes.

## Completion Report Requirements

A worker completion report must include:

- changed files
- decision records touched
- prior-art updates
- benchmark results
- known gaps
- whether the milestone gate passed
- recommended next slice
