# P9.10 Experimental C# Snapshot Workspace and Fact Extraction Probe

P9.10 adds the first experimental C# route to the local IGD facade:

```powershell
python tools/intentgraph.py init-experimental-csharp \
  --workspace <new-workspace> \
  --source-root <external-csharp-source-root> \
  --profile docs/examples/profiles/experimental-host-sdk-csharp-syntax.profile.json
```

## What The Command Does

1. validates the one declared experimental host-SDK profile
2. runs the local host-SDK availability preflight
3. snapshots only non-symlink `*.cs` files outside `bin` and `obj` into a new workspace
4. verifies the external source digest did not change while the copy was made
5. builds the disposable parser outside the source workspace and extracts facts from the copy only
6. writes a path-free intake receipt, code facts, extraction report, and workspace validation report

`validate-experimental-csharp` revalidates the workspace without reading the original external source.

## Fact-Only Boundary

The workspace is intentionally not a B1 local-review workspace. It contains no Intent Unit mapping, change proposal, consistency result, accepted authority, code application, or workbench product claim.

Its declaration is explicit:

```text
mode: experimental-csharp-fact-only
mapping.status: fact-only-no-intent-mapping
```

The generated code facts remain Roslyn syntax-only records. Invocation observations are ambiguous syntax edges, not resolved calls.

## Real-Project Reproduction

A WindowsUtility source snapshot produced 206 source files, 8,137 facts, and 7,931 relations. The source workspace was changing independently during the broader reproduction window, so the evidence does not claim that two different external snapshots must match. Instead, each workspace verifies that its own before/after/copy digest is identical.

This is intentional: a developer can create a reviewable snapshot from an actively edited working tree without letting IGD modify that tree or silently mix two source states.

## Safety

- no external source write, Git write, target build/restore/launch, hardware access, package installation, network, provider, credential, hook, code application, release, or productization authority
- the disposable parser project performs a local build-assets restore with `NuGet.Config` package sources cleared; it does not restore an external/target package or add a dependency
- no external absolute path persisted in the manifest, receipt, preflight, fact, extraction, or validation artifact
- source snapshot failure removes the newly created workspace
- fixed-source positive workspaces are byte-identical
- ten repeatable negative probes cover source/workspace/profile guards, receipt/path leak, source text, semantic-resolution claim, output escape, and source mutation during intake

## Next Gate

P9.11 must review the fact-only workspace result before adding mappings, proposals, generic workbench support, or a broader C# profile claim.
