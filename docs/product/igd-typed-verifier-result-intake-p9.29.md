# P9.29 Typed External Verifier Result Intake

P9.29 closes the next normal-workflow gap after a code-bearing proposal. The local
Workbench can now record what an external build, test, runtime-smoke, or static-analysis
verifier reported through a result carrying declared-deterministic metadata and bind that
observation to one exact proposal verification/evidence requirement pair.

The intake is deliberately an observation boundary. IntentGraph does not execute the
verifier, upload the selected evidence file, authenticate the producer, accept the
evidence, approve the proposal, apply a graph delta, or edit source code.

## Daily Workflow

```text
work request
  -> code mapping
  -> non-applied proposal and code diff
  -> declared verification/evidence pair
  -> external verifier runs outside IGD and declares deterministic metadata
  -> local evidence bytes are hashed in the browser
  -> typed observation is imported
  -> requirement coverage and acceptance-pending state are inspectable
```

The guided Workbench dialog derives the proposal, requirement IDs, next attempt,
allowed verifier kind, required artifact kind, source digest, and proposal digest from
the current project state. The user supplies the observed outcome, verifier identity,
checks, typed metrics, and a local evidence artifact. Only the artifact's digest,
length, kind, media type, and logical name are submitted; its bytes remain local.

## Typed Contract

The supported verifier kinds are:

- `build`
- `test`
- `runtime-smoke`
- `static-analysis`

Each result must bind one explicitly compatible verification/evidence requirement
pair. Typed metrics and required artifact kinds vary by verifier kind. A passing test
result must report at least one passed test; an all-skipped test run cannot become a
passing observation.

IntentGraph validates the declaration and typed envelope; it does not independently
prove verifier determinism. Results have stable IDs and monotonic attempts. A later attempt may supersede the
current result without deleting history. Pass, fail, and blocked observations all keep
the work item in `verification-observed`; the detailed result is visible, but evidence
acceptance remains `pending`.

## Persistence and Concurrency

Verifier-result writes are serialized by a workspace lock and use compare-and-swap
against the project state. Artifact and project files are atomically replaced, with
the project state committed last. A matching orphan artifact from an interrupted
artifact-first write can be recovered; incompatible or stale state fails closed.

The same proposal pair and attempt cannot be recorded twice. Concurrent writers for
the same attempt produce exactly one winner and one deterministic rejection. Every
accepted observation creates exactly one durable work-stage revision.

All project-state writers use the same lock and atomic state-last commit boundary, so
a verifier result cannot overwrite a concurrently recorded request, mapping, proposal,
or receipt. The cross-operation regression starts both writers behind a held workspace
lock before releasing them into contention. Pair-scoped result-ID prefixes also keep
multiple verifier bindings on one proposal independently addressable.

## Workbench Visibility

The unified graph, timeline, verification tray, and inspector expose:

- current and superseded verifier-result nodes;
- pass, fail, blocked, and missing pair counts;
- verifier identity, version, attempt, checks, and typed metrics;
- evidence artifact identity, digest, kind, media type, and byte length;
- per-proposal requirement coverage;
- one durable `Verifier result imported` stage; and
- `observed` plus `acceptance pending` authority state.

The generated WindowsUtility demonstration contains 8,203 nodes, 8,014 relations,
four typed requirement pairs, and one current passing test observation.

## Non-Goals

- no verifier execution by IntentGraph;
- no evidence upload or evidence acceptance;
- no producer authentication or cryptographic attestation;
- no source, snapshot, or target repository mutation;
- no graph-delta or code-diff application;
- no proposal approval or automatic work completion; and
- no network, provider API, credential, build, test, or launch authority.

The next product boundary is explicit evidence acceptance and authority decision
recording. It must consume observed results without treating them as self-authenticating
or self-approving.
