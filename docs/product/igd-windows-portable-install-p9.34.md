# IntentGraph Windows Portable Distribution and Install: P9.34

P9.34 packages the local IntentGraph C# review workflow as a deterministic Windows-local directory and ZIP bundle. The bundle contains the `igd` launcher, `igd doctor/status/prepare/open` runtime modules, the existing minimal C# probe projects and profile, and the local Cytoscape Workbench assets.

The validated preview artifact is `generated/product-bundles/intentgraph-0.1.0-preview-windows.zip` with SHA-256 `844069c46a592a1e36769067aa6296b036758e405a1dbb2611c30648df7c69c7`. It is unsigned and unpublished.

This is a portable local distribution, not a self-contained native executable. The host must provide Python 3.11 or newer. The C# workflow also requires a supported locally installed .NET SDK. Building, validating, installing, and uninstalling the bundle performs no download, network call, signing, provider operation, or release publication.

## Build and validate

Run from the repository root:

```powershell
python tools/build_igd_windows_bundle.py build `
  --output .tmp/p9.34/igd-windows `
  --archive .tmp/p9.34/igd-windows.zip

python tools/build_igd_windows_bundle.py validate `
  --bundle .tmp/p9.34/igd-windows

python tools/build_igd_windows_bundle.py validate `
  --bundle .tmp/p9.34/igd-windows.zip
```

The output and archive paths must not already exist. This prevents a build from silently overwriting a prior distribution or a repository source path. Build into a fresh path for every run.

The manifest at `igd-bundle-manifest.json` records every payload file in sorted order with its relative path, SHA-256 digest, and byte length. Validation requires an exact match between that inventory and the directory or ZIP: missing files, extra files, stale bytes, duplicate or escaping paths, unsupported executable payloads, promoted authority flags, and unsafe installer instructions are rejected.

## Install

Extract `igd-windows.zip`, enter the extracted directory, and choose one of the following commands.

Install to an explicit location without changing the user PATH:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1 `
  -InstallRoot C:\Tools\IntentGraph `
  -NoPathUpdate
```

Run that installation:

```powershell
C:\Tools\IntentGraph\igd.cmd doctor
C:\Tools\IntentGraph\igd.cmd prepare C:\src\MyCSharpProject
C:\Tools\IntentGraph\igd.cmd status C:\src\MyCSharpProject
C:\Tools\IntentGraph\igd.cmd open C:\src\MyCSharpProject
```

Install at the default per-user location and add it to the user PATH:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\install.ps1
```

The default runtime root is `%LOCALAPPDATA%\Programs\IntentGraph`. User project data stays separately under `%LOCALAPPDATA%\IntentGraph`, so a normal uninstall does not remove review workspaces. Open a new terminal after PATH installation, then run:

```powershell
igd doctor
igd open C:\src\MyCSharpProject
```

The installer validates an exact, reparse-free source inventory against the manifest, copies into a sibling staging directory, validates the staged installation, and only then moves it into the requested install root. It refuses to overwrite an existing directory.

For a PATH-enabled install, the installer rejects any `igd` command already visible from another PATH directory, including higher-precedence `PATHEXT` forms such as `igd.exe` or `igd.bat`. It places the new entry first in the user PATH, updates the current process PATH consistently, and verifies that the default `igd` command resolves to the installed launcher. Use `-NoPathUpdate` when an existing launcher is intentional.

Installed `igd.cmd` sets `PYTHONDONTWRITEBYTECODE=1` and redirects any explicit Python cache prefix beneath `%TEMP%\IntentGraph`. Roslyn probe copies, package caches, and build outputs use system temporary storage. Normal `doctor`, `prepare`, and `open` execution therefore does not add files beneath the runtime installation.

## Uninstall

Remove an explicit no-PATH installation:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File C:\Tools\IntentGraph\uninstall.ps1 `
  -InstallRoot C:\Tools\IntentGraph `
  -NoPathUpdate
```

Remove the default installation and its user PATH entry:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass `
  -File "$env:LOCALAPPDATA\Programs\IntentGraph\uninstall.ps1" `
  -InstallRoot "$env:LOCALAPPDATA\Programs\IntentGraph"
```

The uninstaller refuses filesystem roots, reparse-point roots, invalid manifests, missing or modified manifest files, unknown files or directories, and any reparse point anywhere in the install tree. After exact inventory validation, it rechecks and removes only recorded files, then only known empty directories and the empty install root. `%LOCALAPPDATA%\IntentGraph` review workspaces are preserved.

## Repeatable safety probes

```powershell
python tools/run_igd_windows_bundle_negative_probes.py `
  --out .tmp/p9.34/negative-probes.json

python tools/run_igd_windows_install_smoke.py `
  --out .tmp/p9.34/install-smoke.json

python tools/run_igd_daily_negative_probes.py `
  --out .tmp/p9.34/daily-negative-probes.json

python tools/run_igd_daily_server_smoke.py `
  --out .tmp/p9.34/daily-server-smoke.json
```

The bundle harness runs 13 isolated probes covering missing, extra, stale, unsafe, existing-output, and protected-output states. The installed-runtime smoke runs 21 checks, including default PATH resolution, PATH shadow rejection, immutable runtime execution, bytecode absence, exact-inventory uninstall refusal, reparse-target preservation, and successful final uninstall. Daily negative probes cover first-create locking, source reparse rejection, and exact file-fact cardinality. Browser readiness success and both failure paths are observed with injected fakes, so no real browser is visibly opened by the smoke.

## Boundary

P9.34 only distributes the existing local product runtime. It does not mutate a reviewed target repository, run a target build, restore target packages, apply a code proposal, access credentials, install hooks, sign an artifact, publish a release, or claim that the preview C# profile is a broad production extractor.
