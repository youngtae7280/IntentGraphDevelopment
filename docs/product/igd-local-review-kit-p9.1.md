# IntentGraph Local Review Kit: P9.1 Contract

P9.1 introduces a bounded local command facade for the B1 TypeScript REST sample. It is a developer-preview workflow contract, not an installable product or a general extractor.

## Commands

```powershell
python tools/intentgraph.py init-sample --workspace .tmp/igd-b1-review
python tools/intentgraph.py validate --workspace .tmp/igd-b1-review
python tools/intentgraph.py review --workspace .tmp/igd-b1-review
```

`init-sample` creates a fresh local workspace from the repository's B1 fixture. `validate` checks the workspace contract without generating artifacts. `review` runs the deterministic code-fact, mapping, proposal, consistency, and workbench pipeline entirely inside that workspace.

P9.2 replaces P9.1's copied-path baseline materialization with the profile's stable `intentgraph://profiles/b1-typescript-rest-api-sample/source` logical source identity. The workspace copies a predeclared profile proposal whose code-fact baseline is independent of its physical workspace path. The original historical B1 proposal is never modified.

## Workspace Contract

The root file is `intentgraph.workspace.json`. It declares:

- the fixed `b1-typescript-rest-api-sample` profile
- a source tree digest and read-only source boundary
- the overlay and proposal input paths
- the exact output paths under `artifacts/`
- false authority flags for mutation, automatic code application, network, providers, credentials, hooks, and release publishing

The facade rejects path traversal, outputs outside `artifacts/`, stale source provenance, missing inputs, unsupported profiles, and any changed authority flag.

## Boundary

The command writes only to the declared workspace. It does not modify a target repository, apply a proposal, execute generated code, access credentials, use a provider API, install hooks, or publish anything.

The B1 sample is the only supported profile. P9.2 makes its aggregate code-fact baseline portable across workspace locations through a logical source identity. Broader language support, arbitrary-repository retrofit, installation, editor integration, and release are later work.
