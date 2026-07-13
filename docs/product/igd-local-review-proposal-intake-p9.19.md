# P9.19 Local Review Proposal Intake

P9.19 turns the existing review-only change-proposal artifact boundary into a usable local Workbench step.

The daily workflow is now:

```text
record work request
-> record declared code mapping candidate
-> import validated review-only proposal
-> inspect graph delta, code-diff fragments, verification requirements, evidence requirements, authority, and history
```

The third step does not create code, apply a graph delta, approve a mapping, or modify the target repository. It records a proposal artifact only after the same deterministic validator used by the CLI accepts it.

## Loopback Workbench

The local Workbench includes an `Import review proposal` action. The dialog accepts one JSON object with the exact `intentgraph-experimental-csharp-change-proposal` contract.

- it must reference an existing local work request and declared mapping candidate;
- it must remain `not-applied-review-required`;
- every changed code fact and code-diff provenance record is verified against the snapshot;
- verification and evidence requirements must be explicit;
- authority flags must remain non-applying and non-self-authorizing.

The loopback server accepts only `POST /api/change-proposals` with an object shaped as `{ "proposal": { ... } }`. The bounded body limit is 128 KiB. This is a local project-state write, not a source-project write.

The static HTML export intentionally does not contain the proposal import control or an API client. It remains a portable review snapshot.

## Boundary

- no C# source modification, graph-delta application, mapping acceptance, proposal approval, build, launch, evidence execution, provider call, credential access, or remote service;
- no automatic proposal drafting, semantic inference, or code-diff synthesis;
- the browser performs only user-initiated local submission; the server reruns deterministic validation before writing the local workspace;
- invalid, stale, unsafe, applied, or duplicate proposals leave the local project workspace unchanged.

## Verification

The repeatable loopback smoke creates a temporary project workspace and verifies:

1. local work-request recording;
2. local mapping-candidate recording;
3. review-only proposal recording and projection reload;
4. rejection of an `applied` proposal claim;
5. snapshot provenance preservation and loopback-only host enforcement.

The existing P9.14 proposal negative probes still verify malformed roles, stale diff digests, unsafe authority claims, invalid diffs, unresolved graph-delta edges, and missing requirement records.
