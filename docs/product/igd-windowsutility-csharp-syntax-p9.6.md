# P9.6 WindowsUtility C# Syntax-Only Feasibility Probe

P9.6 tests whether IntentGraphDevelopment can read a realistic C# source tree as provenance-backed code facts without building, modifying, or launching the target.

## Boundary

The target is WindowsUtility `src` at revision `ac5b2204442cde751f625a9979a4fdb437d468a8`.

The probe uses a disposable copy of `tools/csharp_syntax_probe` and local SDK Roslyn assemblies. It parses C# syntax only. It does not load an MSBuild workspace, restore or build WindowsUtility, bind types or assemblies, execute analyzers/generators, launch the application, access hardware, or write to the target repository.

Exported facts use the logical root:

```text
intentgraph://targets/windowsutility/src
```

No target absolute path or source-text field is exported. A fact has a relative file reference, byte digest, source range or file-level status, extractor provenance, and confidence.

## Result

Two independent runs over the unchanged target source produced byte-identical facts:

- 206 C# source files, excluding `bin` and `obj`
- 8,137 facts
- 7,931 relations
- syntax fact kinds: file, namespace, type, method, constructor, property, field, using, invocation
- relation kinds: contains, imports, invokes-syntax

Invocation records are deliberately `ambiguous`. They describe syntax-level invocation locations and shapes, not resolved call targets.

The source digest was unchanged before and after extraction. The target Git worktree was clean and aligned with `origin/main` both times.

## Safety Checks

`tools/run_windowsutility_csharp_syntax_negative_probes.py` reruns a positive disposable C# baseline before proving that nine unsafe or malformed cases fail: bad logical root, output inside source, malformed C#, empty/missing source, unexpected parser argument, persisted source text, persisted target syntax, and missing Roslyn assembly.

The initial parser exposed an ID-collision defect for nested invocation expressions sharing a span start. P9.6 corrected the deterministic fact identifier to include both syntax span start and span length, then reran the full target probe. The accepted output has unique fact and relation IDs.

## Non-Goals

- no reusable or packaged C# profile
- no arbitrary C# project support
- no semantic call graph, project-system loading, type binding, build, restore, or code generation
- no WindowsUtility code edit, commit, push, launch, package, or hardware access
- no network, provider, credential, hook, signing, release, or product-readiness authority

## Next Gate

P9.7 must be plan-only. It must decide whether the P9.6 adapter can become a reusable local C# profile, needs a different parser/distribution strategy, or remains a benchmark-only probe. Host-SDK Roslyn availability is not a packaging decision.
