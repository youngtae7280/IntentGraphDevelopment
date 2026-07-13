# P9.8 Experimental Host-SDK C# Profile Availability Preflight

P9.8 makes the P9.6 host dependency explicit without reading a target repository or running C# extraction.

## What It Checks

The profile at `docs/examples/profiles/experimental-host-sdk-csharp-syntax.profile.json` declares a syntax-only adapter with every execution and authority flag false. The preflight:

1. validates that declaration exactly
2. asks the local `dotnet` host for installed SDKs
3. selects the latest locally installed supported SDK
4. checks the two Roslyn assemblies in that SDK's `Roslyn/bincore` directory
5. records binary digest and byte-length evidence without persisting an absolute SDK path

On the current machine it selected SDK `9.0.100` and found both required assemblies. Two preflight runs were byte-identical.

## What It Does Not Do

- does not read WindowsUtility or any target source
- does not extract code facts or invoke the P9.6 parser
- does not build, restore, install, or package any dependency
- does not call a network, provider, or credential store
- does not create a portable or product-ready C# profile

The result means only: this local environment has the declared experimental prerequisite. It does not mean that another machine, a clean install, or a released IGD package will have it.

## Failure Boundary

The negative harness proves fail-closed behavior for wrong profile identity, target-read authority, network or source-extraction claims, unsupported SDK majors, invalid Roslyn assembly declaration, a portable-profile claim, an actual missing host binary, and profile overwrite.

## Next Gate

P9.9 must plan how an experimental C# profile could enter a local IGD workspace while preserving snapshot intake, path-free provenance, source-read-only behavior, and a clear distinction between code facts and accepted Intent Unit mappings. It must not assume that P9.8 authorizes reusable extraction or package distribution.
