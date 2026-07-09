# Evidence Model

Milestone: M5

This model defines the smallest evidence slice for Phase 0. It is not a replacement for W3C PROV, OpenLineage, SLSA, in-toto, SPDX, or GUAC.

IntentGraph builds only the binding layer that attaches evidence records to graph claims, generated artifacts, verifier reports, authority decisions, and semantic deltas.

## Core Rule

```text
EvidenceObserved(e) != EvidenceAccepted(e)
```

Observation means an artifact, note, report, test plan, or result exists and was recorded.

Acceptance means an authority record allows that evidence to support a graph claim.

An observed verifier report is not accepted evidence until an accepted authority record authorizes the evidence record.

## B0 Evidence Shape

Every `evidence.record` in the B0 M5 subset must include:

- `evidenceType`
- `status`
- `summary`
- `recordedBy`
- `observationStatus`
- `acceptanceStatus`
- `artifactRefs`

If `acceptanceStatus` is `accepted`, it must also include:

- `acceptedByAuthority`

The referenced authority node must exist, have `decisionStatus: "accepted"`, and authorize the evidence node with an `authorizes` edge.

For local repository artifact refs, the M5 verifier checks that each referenced path exists. The verifier report may reference its own output path; that path is resolved as `current-report-output` rather than by reading a stale previous report.

Accepted evidence must not have `status: "fail"`, `status: "blocked"`, or `status: "superseded"`. Accepted verifier-report evidence must have `status: "pass"` and must reference the current verifier report output or a local JSON report whose `result` is `pass`.

Accepted planned evidence is allowed only when it is explicit plan evidence, not runtime proof:

```json
{
  "claimScope": "plan-only",
  "runtimeProof": false
}
```

## Status Meanings

`status` records the evidence claim state:

- `planned`: the evidence describes a planned check or expected validation.
- `pass`: the evidence records a passing validation or accepted supporting fact.
- `fail`: the evidence records a failed validation.
- `blocked`: the evidence could not be produced.
- `superseded`: a later evidence record replaces this one.

`observationStatus` records whether the evidence artifact was seen:

- `planned`
- `observed`
- `missing`

`acceptanceStatus` records whether the graph can rely on the evidence:

- `accepted`
- `rejected`
- `pending`
- `superseded`

## M5 B0 Records

The B0 graph carries:

- the benchmark requirement note as observed and accepted evidence
- the calculator test plan as observed and accepted evidence for the plan, not as runtime proof
- the round-trip verifier report as observed and accepted evidence for the metadata-backed round-trip and M5 semantic validation claims

The generated Python program working is supporting evidence only when represented as an evidence record and accepted by authority. Generated code alone is not proof.

## Verifier Expectations

The M5 verifier must fail if:

- an accepted evidence record has no `acceptedByAuthority`
- the referenced authority node is missing or not accepted
- the authority node does not authorize the evidence record
- a local artifact ref on observed evidence is missing
- accepted evidence has a failing, blocked, or superseded status
- accepted planned evidence is not explicitly plan-only
- accepted verifier-report evidence is not tied to a passing report
- observed evidence is silently treated as accepted
- evidence records are not preserved through the round-trip domain subgraph
