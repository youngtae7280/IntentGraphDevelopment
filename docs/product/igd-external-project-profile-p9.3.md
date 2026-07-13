# IGD External Project Profile Intake: P9.3 Boundary

P9.3 defines how the IntentGraph Local Review Kit may later read an external project without turning the review tool into a target-mutation tool.

## Purpose

The bundled B1 sample proves a coherent local workflow, but it does not prove that a source tree outside the IntentGraphDevelopment repository can be safely admitted. P9.3 separates **intake** from **analysis**, and keeps both separate from code application.

## P9.4 Initial Scope

P9.4 may support only an external directory whose TypeScript source tree is byte-equivalent to the bounded B1 profile. It is a read-only snapshot/import proof, not arbitrary TypeScript or WindowsUtility support.

The command shape under consideration is:

```powershell
python tools/intentgraph.py import-b1-equivalent \
  --workspace <new-workspace> \
  --source-root <external-b1-equivalent-source>
```

The command must create a new workspace, copy only the allowed profile source files, validate source digests before and after copying, and then use the existing P9.2 logical B1 profile. It must not modify the external root.

## Intake Receipt

The persisted workspace receipt must include:

- `artifactRole: intentgraph-external-source-intake-receipt`
- `profileId: b1-typescript-rest-api-sample`
- `logicalSourceRoot: intentgraph://profiles/b1-typescript-rest-api-sample/source`
- source tree digest before and after intake
- copied file count and sorted relative file digests
- `externalSourceMutated: false`
- `sourcePathPersisted: false`
- `networkRequired: false`
- `automaticCodeApplication: false`

It must not retain the external absolute path in a reusable graph or workbench artifact. The path is an ephemeral command argument; the receipt records only the profile identity and source evidence.

## Required Validation

P9.4 must fail closed when:

- the source root is missing, non-directory, inside the new workspace, or a symlink
- the workspace already exists or is non-empty
- a copied file is a symlink, outside the external root, or has an unsupported extension
- the before/after external source digest changes
- the source file set or digest does not match the bounded B1 profile
- the output workspace cannot validate under the P9.2 logical profile
- a caller requests target mutation, code application, network, credential, provider, hook, release, or arbitrary profile behavior

## Explicit Non-Goals

- no arbitrary repository import
- no C#, WindowsUtility, Python, or general TypeScript extractor claim
- no target repository mutation, Git mutation, or code application
- no provider API, credentials, hooks, package creation, signing, or release
- no persistent external absolute paths in IntentGraph artifacts

## Next Gates

P9.4 may implement this B1-equivalent external snapshot/import proof. P9.5 must then plan a separate profile-authoring and language-expansion gate before a different source shape can be accepted.
