# P9.9 Experimental C# Local Workspace Integration Boundary

P9.9 plans the first workspace-shaped use of the experimental C# host-SDK capability. It does not implement extraction or add a supported project profile.

## Purpose

P9.6 proves a read-only C# syntax extractor. P9.8 proves that the local host has the required experimental parser prerequisite. Neither result says how source evidence should enter the IntentGraph Local Review Kit.

The next slice must preserve the semantic-overlay architecture:

```text
external C# source snapshot -> local workspace source copy -> code facts
```

The original project remains outside the workspace and is never modified. Code facts describe the workspace snapshot through a logical source identity, not the external absolute path.

## Proposed P9.10 Command

```powershell
python tools/intentgraph.py init-experimental-csharp \
  --workspace <new-workspace> \
  --source-root <external-csharp-source-root> \
  --profile docs/examples/profiles/experimental-host-sdk-csharp-syntax.profile.json
```

P9.10 may add this command only if it creates a new workspace and fails closed before writing when the profile preflight, source snapshot, or output guard fails.

## Workspace Contract

The workspace must declare:

- a distinct experimental C# workspace role and schema version
- profile id and profile byte digest
- a fixed logical source root such as `intentgraph://profiles/experimental-csharp-host-sdk-syntax-only/source`
- a source intake receipt containing before/after/copy tree digests and sorted relative C# file digests
- `externalSourcePathPersisted: false`
- `sourceRole: snapshot-copy-not-target`
- code facts generated only from the workspace copy
- `mappingStatus: fact-only-no-intent-mapping`
- false authority for target write, target build/restore/launch, package operation, network, provider, credentials, hook, code application, release, and productization

The workspace source scope is non-symlink `*.cs` files excluding `bin` and `obj`. It intentionally does not copy project files, assets, binaries, packages, or generated artifacts because P9.10 does not evaluate or build the project.

## Required P9.10 Validation

- P9.8 preflight passes before snapshot intake starts.
- The external C# tree is unchanged before/after intake and the snapshot copy digest matches it.
- The new workspace is absent before intake and does not overlap the external source root.
- Every generated fact resolves to a workspace-relative source file and digest.
- The C# fact report uses the logical source root and retains syntax-only/ambiguous invocation boundaries.
- External absolute paths do not appear in persisted workspace, receipt, fact, or report artifacts.
- A second run against the same immutable source and fresh workspace is byte-identical where physical workspace identity is excluded by the contract.
- No Intent Unit mapping, change proposal, authority acceptance, workbench product claim, or source application is created.

## Required P9.10 Negative Probes

- preflight report/profile mismatch or unavailable local host
- missing/file/symlink C# source root
- zero C# files or an unsupported persisted source file
- source/workspace overlap or pre-existing workspace
- source change during snapshot or stale/tampered intake receipt
- source-text, absolute-path, semantic-resolution, target-build, or target-write claim in workspace/fact artifacts
- output collision or workspace path escape

## Explicit Non-Goals

- no WindowsUtility edit, build, launch, commit, or push
- no general C# project support
- no project-system evaluation, semantic call graph, mapping, proposal, verifier, or workbench extension
- no package pinning, installer, signing, release, or product readiness

## Decision

P9.10 may implement this fact-only snapshot workspace probe. It must remain an experimental, host-specific local path and may not silently promote the profile into the general B1 local-review workflow.
