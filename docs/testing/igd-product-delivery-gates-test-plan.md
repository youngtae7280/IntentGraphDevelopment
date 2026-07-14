# IGD Product Delivery Gates Test And Verification Plan

Status: G0 completed planning artifact.
Applies to: the delivery gates in
[IGD Product Goal And Delivery Gates](../roadmap/igd-product-delivery-gates.md).

## Test Principle

Each gate must prove the claim it makes at the same scope. A deterministic fixture
check cannot prove a real-project, usability, or release claim by itself. Tests are
therefore organized by evidence type rather than one global pass count.

## Required Evidence By Gate

| Gate | Contract checks | Negative checks | Regression checks | Benchmark / user evidence |
|---|---|---|---|---|
| G0 | document links, status, scope, and phase wording | stale current-status wording | existing docs remain reachable | coordinator review |
| G1 | proposal/apply contract and authority model | missing preimage, missing rollback, unsafe scope | P9.35 refresh remains intact | P8 experiment comparison |
| G2 | exact apply, verification, refresh, rollback | stale, unauthorised, partial-write, drift, failed verification | prepare/open/status/refresh/install | bounded WindowsUtility apply |
| G3 | scenario records and metric schema | invalid baseline or misleading comparison | G2 flow per scenario | real-task vs ordinary AI baseline |
| G4 | adapter facts, relations, provenance, incremental update | unknown endpoints, unstable facts, unsupported claims | G2 source refresh | coverage/performance comparison |
| G5 | candidate provenance, ambiguity, scope, requirement records | self-acceptance, hidden ambiguity, overbroad proposal | G3 workflow | candidate quality comparison |
| G6 | selectable linked graph/diff/evidence/history UI | hidden failures, broken selection, blank or stale view | G2/G3 projection | user acceptance and measured responsiveness |
| G7 | install, upgrade, repair, rollback, uninstall, integrations | unsafe installer, authority escalation, data loss | all supported workflow tests | clean-environment onboarding |

## Mandatory G2 Source-Application Matrix

G2 cannot begin until G1 defines expected results for every row.

| Scenario | Required result |
|---|---|
| exact approved proposal | one bounded atomic apply, declared verification, refresh, history record |
| proposal or source drift | zero source write and clear stale report |
| unauthorised approval | zero source write |
| patch outside mapped scope | zero source write |
| interrupted write | original source or complete recoverable state, never ambiguous bytes |
| verification failure | explicit failure state plus preserved source or approved rollback evidence |
| refresh failure after apply | durable recovery record and no false active revision |
| concurrent apply | one winner or no write, never interleaved changes |
| rollback | exact approved revision restoration and new history/evidence record |

## Verification Order

1. Validate immutable inputs, authority, source containment, and preimage.
2. Run the smallest positive scenario in an isolated copy.
3. Run every negative probe with byte-level source observations.
4. Run prior P9.34/P9.35 product regressions whenever shared CLI, workspace, or
   revision code changes.
5. Run the approved real-project benchmark only after isolated proof passes.
6. Inspect Workbench output for the same operation; do not infer UI correctness from
   JSON alone.
7. Record a gate review with claim scope, failed cases, performance, and remaining
   gaps.

## Quality Thresholds

- No unapproved target write is acceptable.
- A source-application path must preserve a machine-checkable preimage and recovery
  route for every failed scenario.
- Any target mutation that is not represented by a matching proposal, authority
  decision, evidence record, refresh result, and history record is a P1 defect.
- A performance threshold must be measured on the declared supported project band;
  fixture-only speed is insufficient.
- A Workbench acceptance claim requires direct user review; renderer telemetry and
  screenshots are supporting evidence only.
- A daily-use or release claim requires a clean-environment install and an end-to-end
  request-to-reviewed-change demonstration.

## Stop Rules

- Stop before the next gate on any P1 source-integrity, authority, or history defect.
- Stop before real-project execution if isolated negative probes do not fail closed.
- Stop and redo the prior-art decision if an implementation begins duplicating a
  stronger code intelligence, policy, or visualization system without a documented
  reason.
- After two unsuccessful repair cycles for one gate, perform an architecture review
  and revise the gate rather than adding another narrow hardening slice.
