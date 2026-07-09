# Autonomous Work Loop

Use this loop when assigning a worker or a new chat to continue work without constant supervision.

## Core Rule

Autonomous work must be bounded by one milestone.

Do not assign:

```text
Finish IntentGraph Development.
```

Assign:

```text
Complete M0 Research and Thesis Foundation according to docs/roadmap/milestones.md.
```

## Loop Steps

Each worker iteration must follow this loop:

1. Check repo state.
   - `git status --short`
   - confirm local branch tracks `origin/main`
2. Read required context.
   - `docs/START-HERE.md`
   - `docs/concept/core-thesis.md`
   - `docs/roadmap/milestones.md`
   - current milestone section
3. Select one unfinished item from the current milestone.
4. Check prior art before changing direction.
5. Update the smallest relevant document.
6. Run local validation appropriate to docs.
   - spell/placeholder scan when available
   - link/path sanity check when feasible
   - `git diff --check`
7. Review the change against milestone done criteria.
8. Commit with a concise message.
9. Push to `origin/main`.
10. Continue only if the milestone still has non-blocked unfinished items.

## Stop Conditions

Stop and report instead of continuing when:

- the repo is dirty with unrelated changes
- local branch and `origin/main` diverge
- a stronger existing system is discovered that may replace current work
- the milestone definition is unclear
- a decision requires user judgment
- implementation is tempting but the current milestone allows only research/design
- the milestone review says `improve` and the cause is not obvious
- credentials, provider calls, network activation, deployment, or external mutation would be needed

## Worker Scope Rules

- Do not jump milestones.
- Do not create implementation code during M0.
- Do not preserve weak custom work if prior art suggests replace or integrate.
- Do not change the core thesis silently; record the change.
- Do not treat AI output as accepted evidence.
- Do not claim round-trip success without a verifier or explicit manual review.

## Commit Rules

Every commit must represent one coherent step.

Recommended commit styles:

```text
Refine core thesis
Expand prior art map
Add initial build borrow integrate decisions
Define M0 benchmark criteria
Record M0 milestone review
```

## Completion Rule

When the current milestone appears complete, the worker must write or update a milestone review and then stop with a completion report.
