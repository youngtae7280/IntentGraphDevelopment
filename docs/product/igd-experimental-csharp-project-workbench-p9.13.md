# P9.13 Experimental C# Project Workbench

P9.13 turns a validated P9.10 C# fact snapshot into the first **local semantic-overlay project workspace**. It corrects the P9.12 limitation: P9.12 is a code-fact inspector, while P9.13 can display the project-work records that make those facts useful for daily IntentGraph work.

## Local Workflow

```powershell
python tools/intentgraph.py init-experimental-csharp-project `
  --snapshot-workspace <validated-p9.10-snapshot> `
  --workspace <new-local-project-workspace> `
  --project-id <stable-project-id> `
  --title <project-title>

python tools/intentgraph.py add-experimental-csharp-work-request `
  --workspace <project-workspace> `
  --work-id <stable-work-id> `
  --title <short-title> `
  --request <verbatim-user-request>

python tools/intentgraph.py add-experimental-csharp-mapping-candidate `
  --workspace <project-workspace> `
  --work-id <stable-work-id> `
  --code-fact <fact-id> `
  --rationale <why-this-fact-is-relevant>

python tools/intentgraph.py emit-experimental-csharp-project-workbench `
  --workspace <project-workspace> `
  --out <new-local-workbench-directory>
```

The project workspace owns semantic-overlay state only. It contains a copied, validated source snapshot beneath `snapshot/`, plus an `intentgraph.project.json` state document. It never writes to the external source project.

## What The Workbench Shows

- C# files, namespaces, types, members, imports, and syntax-level invocation facts
- user work requests and their Intent Units
- declared mapping candidates from an Intent Unit to selected code facts
- snapshot verification and evidence records
- authority boundary and semantic history records
- explicit change-review state: no proposal, graph delta, or code diff exists until a later deterministic proposal phase records one

The graph uses the same graph surface for code facts and semantic-overlay records. Code facts remain source pointers/facts with relative source provenance; they do not copy source content into the workbench.

## Boundary

P9.13 is a local project-workflow foundation, not a completed C# review product.

- mappings are declared candidates, not accepted truth
- C# extraction remains Roslyn syntax-only; invocation observations are not resolved calls
- the UI is a read-only projection and cannot edit the graph, apply code, or approve work
- no change proposal, graph delta, code diff, build/test/launch, package, network, credential, or release authority is created
- the nested snapshot and the external target repository remain unchanged while rendering

## WindowsUtility Demonstration

The generated WindowsUtility demonstration records one real setup work item: inspect the application startup surface and declare a mapping candidate to the extracted `App` type. It is intentionally a candidate, not an accepted source-change plan.

Its local workbench is:

```text
generated/windowsutility/experimental-csharp-project-workbench/p9.13/index.html
```

This is the first screen that combines a code graph with work, intent, mapping, verification, evidence, authority, and history. The final product must still add reviewed mapping acceptance, deterministic change proposals, graph/code diffs, richer verification, and a repeatable installer or local application route.
