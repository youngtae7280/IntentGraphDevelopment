# IntentGraph Daily Open: P9.34

P9.34 is the first user-facing Windows-local preview that turns the proven C# workflow into one normal command.

## What To Run

After installing the portable bundle:

```powershell
igd doctor
igd open C:\src\MyCSharpProject
```

`igd open` performs four bounded actions:

1. reads C# files without modifying the source repository;
2. creates a validated local snapshot and semantic-overlay project on first use;
3. validates and resumes that same local project on later use;
4. starts the Workbench on an automatically selected loopback port and opens the default browser.

Source intake rejects symbolic links, directory junctions, and other reparse points. Every enumerated C# file is strictly resolved and must remain beneath the declared source root before it can be hashed or copied.

The browser is the daily product surface. It shows the complete code-fact graph, work requests, mappings, proposals, graph and code deltas, verification results, evidence decisions, authority, and history as those records are added.

## Where Data Lives

- runtime: `%LOCALAPPDATA%\Programs\IntentGraph`
- local review projects: `%LOCALAPPDATA%\IntentGraph\p\<source-identity-prefix>`
- target repository: read only

IntentGraph stores a hash of the resolved source identity, not its absolute path, in the launch record. Uninstall removes the runtime and preserves local review projects.

## Resume And Staleness

When C# file bytes are unchanged, reopening validates and resumes the existing project. File modification times and `bin`/`obj` changes do not make it stale.

When tracked C# bytes change, P9.34 fails closed before starting the server:

```text
source changed since the recorded snapshot; refresh is required before reopening
```

This is deliberate. P9.34 does not silently replace the snapshot because mappings, proposals, evidence, and history may need invalidation or migration. A reviewed `igd refresh` workflow is the next product slice.

## Useful Commands

```powershell
igd status C:\src\MyCSharpProject
igd prepare C:\src\MyCSharpProject
igd open C:\src\MyCSharpProject --no-browser
igd open C:\src\MyCSharpProject --port 8765
```

`prepare` creates or validates the local project without starting a server. `status` never creates a missing project. Explicit occupied ports fail instead of falling back silently. A stable per-project OS lock covers the first existence check, complete preparation, same-volume atomic commit, resume validation, and the full server lifetime. Concurrent first creation or serving therefore cannot prepare or commit a duplicate project.

Automatic browser launch is readiness gated and bounded to 50 loopback checks. If readiness is not observed or the default browser declines the request, `igd` emits warning evidence without treating a browser as opened.

## Current Boundary

This preview requires Python 3.11+ and a supported installed .NET SDK. It is installable and usable locally, but it is not signed, publicly released, self-contained, multi-user, or editor-integrated. It does not automatically refresh changed source, authenticate reviewers, apply source changes, or publish anything.
