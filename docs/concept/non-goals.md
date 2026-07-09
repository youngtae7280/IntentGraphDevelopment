# Non-Goals

IntentGraph Development must stay narrow at the beginning.

## Not a Sourcegraph Clone

This project is not a code search or code intelligence platform clone.

## Not a Graphify Clone

This project should not duplicate strong existing code graph extraction work. If code graph extraction is needed, compare and consider integration with mature systems before building.

## Not a DevView Port

DevView is useful as a prototype and source of lessons, but this repository should not inherit DevView's full readiness-report surface.

## Not an IDE First

Do not build the workbench or graph UI before the source model, compiler boundary, reconstructor boundary, and round-trip verifier are defined.

## Not AI-First Authority

The project is not a system where AI output is accepted because it is plausible. AI proposes; deterministic validation and explicit authority decide.

## Not All Languages First

The first implementation should target one small language and one small benchmark. Multi-language support comes after the round-trip thesis is proven.

## Not Manual Graph Editing as the Main UX

The goal is not to replace manual code editing with tedious manual graph editing. Human intent should be captured at a meaningful level, and graph/code deltas should be proposed, reviewed, and verified.
