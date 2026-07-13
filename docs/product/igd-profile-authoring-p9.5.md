# IGD Project Profile Authoring and Language Expansion: P9.5 Gate

P9.5 determines the next language/profile expansion after the bounded B1 TypeScript workflow. It authorizes planning only; it does not add a C# extractor or read WindowsUtility through the new profile.

## Decision

The next bounded profile is a **WindowsUtility C# syntax-only read-only probe**.

It targets `WindowsUtility/src` only. The current target has 17 C# projects and 206 `.cs` files after excluding `bin` and `obj`. This is a realistic second profile shape: multi-project, WPF/MVVM, Core/Services/Native/Modules/Shell layers, and no need to invoke hardware paths for source analysis.

## Extraction Choice

P9.6 may use Roslyn `Microsoft.CodeAnalysis.CSharp` through a disposable local probe. The installed .NET SDK exposes Roslyn assemblies, but P9.5 does not treat their host paths as an IGD packaging solution.

The initial extractor must use syntax parsing only:

- no MSBuild workspace loading
- no solution build, restore, source generation, analyzer execution, or project evaluation
- no assembly loading or type binding
- no target-repository write

This permits deterministic extraction of file, namespace, type, interface, enum, method, constructor, property, field, using/import, containment, and syntax-level invocation facts. Invocation targets that cannot be resolved syntactically must remain `ambiguous` or `inferred`, never be claimed as semantic binding.

## Proposed C# Profile Grammar

```json
{
  "artifactRole": "intentgraph-readonly-csharp-profile",
  "status": "intentgraph-readonly-csharp-profile-declared",
  "profileVersion": "0.1.0",
  "language": "csharp",
  "extractor": {
    "adapter": "roslyn-syntax-only",
    "semanticResolution": false,
    "sourceBuildAllowed": false,
    "networkRequired": false
  },
  "sourceScope": {
    "root": "src",
    "includeExtensions": [".cs"],
    "excludeDirectories": ["bin", "obj"]
  },
  "authority": {
    "targetRepositoryMutation": false,
    "automaticCodeApplication": false,
    "providerApiAllowed": false,
    "credentialAccessAllowed": false,
    "hookInstallationAllowed": false,
    "releasePublishingAllowed": false
  }
}
```

The actual P9.6 profile must carry a stable logical source root and must not embed the target absolute path in exported code facts or reports.

## P9.6 Acceptance Criteria

- source state/digest recorded before and after the probe and remains unchanged
- only `src/**/*.cs` outside `bin`/`obj` is read
- two runs produce byte-identical code facts and summary reports
- facts have source file, range/status, digest, extractor, and confidence provenance
- all relation endpoints resolve
- syntax-only calls are labeled according to evidence strength
- no build, restore, network, provider, credentials, hooks, hardware action, source mutation, or product claim occurs
- failing source scope, unsafe profile flag, missing Roslyn assembly, malformed C#, and output path escape probes are repeatable

## Explicit Non-Goals

- no WindowsUtility code edit, commit, push, build, launch, or hardware access
- no arbitrary C# project support
- no semantic compilation or project-system resolution
- no Roslyn dependency packaging decision
- no editor integration, installer, signing, release, or productization claim

## Next Gates

P9.6 may create a disposable C# syntax-only feasibility probe. P9.7 must review whether to package a pinned Roslyn adapter, use a different parser, or stop before a reusable C# profile is introduced.
