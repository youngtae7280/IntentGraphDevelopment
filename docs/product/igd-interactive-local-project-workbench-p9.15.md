# P9.15 Interactive Local Project Workbench

P9.15 makes the C# project Workbench usable as a local daily-work surface instead of a report that can only be prepared through the command line.

## Start

```powershell
python tools/intentgraph.py serve-experimental-csharp-project-workbench `
  --workspace <local-project-workspace> `
  --host 127.0.0.1 `
  --port 8765
```

The service accepts only `127.0.0.1` or `::1`. It does not bind to a network interface.

## What A User Can Do

- open the unified project Workbench in a browser
- inspect the semantic overview, active-work impact graph, code topology, and all-record view
- select nodes and edges to inspect provenance, proposal status, graph delta, and code diff fragments
- record a new work request through the `New work request` form

The form writes only `intentgraph.project.json` in the local IntentGraph project workspace. It does not modify the nested snapshot or the external source repository.

## Layered Graph Views

The previous raw-code default was intentionally replaced with three levels:

1. **Project overview**: Intent, work, proposal, verification, evidence, authority, history, and derived code capsules for each source module.
2. **Active work impact**: the selected work's semantic records, mapped/changed facts, their containment parents, and affected code capsules.
3. **Code topology**: structural file, namespace, and type facts, plus code capsules.

`All matching` remains available for deep inspection, but it is not the default because a real repository can contain thousands of code facts.

## Boundary

- loopback server only; no provider, credential, or external network call
- no external source mutation, build, launch, package, release, or hardware action
- no automatic mapping, proposal acceptance, code application, or approval recording
- no source content is exposed except explicit code-diff fragments already present in a non-applied proposal

The server is a local usability step, not a released desktop application or team service. Packaging, persistence location policy, editor integration, multi-user concurrency, reviewed acceptance, and evidence execution remain product work.
