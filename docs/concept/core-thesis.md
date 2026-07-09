# Core Thesis

## One Sentence

IntentGraph Development treats intent graphs as primary source artifacts, compiles them into executable source code, reconstructs them back from generated code, and makes round-trip consistency, evidence, authority, and change history first-class development concerns.

## Short Form

Code is the output. Intent is the source.

## Problem

AI-assisted development often starts from vague human intent and ends as source code. The middle of that process is under-specified:

- intent is not preserved as a durable source artifact
- generated code is difficult to trace back to the original intent
- evidence and validation are usually stored outside the source model
- authority and review boundaries are implicit
- later maintenance requires reconstructing context from code, commits, issue trackers, and chat history
- AI-generated changes may look plausible without being accepted by a deterministic authority boundary

## Hypothesis

If intent, structure, code relationships, preservation metadata, evidence, authority, and change history are represented in a source graph, then AI-assisted development can become more inspectable, repeatable, and verifiable than direct prompt-to-code workflows.

The thesis is not that model-to-code generation, graph-based code analysis, provenance, policy, or visualization are new. Mature systems already own large parts of those spaces. The thesis is that IntentGraph can add value by making the graph the source of truth and requiring generated code, reconstructed graph state, evidence, authority, and history to be checked together.

## Method Shape

Forward:

```text
intent graph
  -> intent graph compiler
  -> source code + preservation metadata
  -> traditional compiler/runtime
```

Reverse:

```text
source code + preservation metadata
  -> intent graph reconstructor
  -> intent graph
```

Verification:

```text
Retrofit(Native(G)) = G
```

for complete graphs with preservation metadata.

For code-only reconstruction:

```text
RetrofitCodeOnly(C) ~= ProjectionCode(G)
```

Code-only reconstruction is expected to be lossy because requirements, evidence, authority, and change history are not fully expressible in ordinary source code.

## What Makes It Different

IntentGraph is not only:

- a code graph
- a visual programming tool
- a model-driven code generator
- a language workbench
- an AI coding assistant memory
- a requirements tracker
- a provenance or policy engine

The differentiation claim is the combined source-layer discipline:

- graph as primary source
- deterministic graph-to-code compiler boundary
- code-to-graph reconstructor boundary
- explicit preservation metadata
- declared equality and projection rules
- evidence attached to graph nodes, generated code, and validation claims
- authority separated from AI proposal
- semantic change history linked to ordinary version control

## AI Boundary

AI may propose graph changes or code changes.

AI must not be the final authority.

Acceptance must come from deterministic checks, evidence, explicit review, policy where needed, and round-trip validation.

## Phase 0 Proof Shape

Phase 0 should not prove a full platform. It should prove or weaken the thesis on one tiny benchmark:

```text
source intent graph G
  -> deterministic generated source + preservation metadata
  -> reconstructed graph G'
  -> verifier report that proves G' = G under declared rules
```

If that loop cannot preserve evidence, authority, and change history projections for a tiny benchmark, the thesis must narrow or pivot before larger implementation.
