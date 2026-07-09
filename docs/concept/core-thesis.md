# Core Thesis

## One Sentence

IntentGraph Development treats intent graphs as primary source artifacts, compiles them into executable source code, reconstructs them back from generated code, and makes round-trip consistency, evidence, authority, and change history first-class development concerns.

## Short Form

Code is the output. Intent is the source.

## Problem

AI-assisted development often starts from vague human intent and ends as source code. The middle of that process is under-specified:

- the intent is not preserved as a durable source artifact
- generated code is difficult to trace back to the original intent
- evidence and validation are often separate from the source model
- authority and review boundaries are implicit
- later maintenance requires reconstructing context from code, commits, and chat history

## Hypothesis

If intent, structure, code relationships, evidence, authority, and change history are represented in a source graph, then AI-assisted development can become more inspectable, repeatable, and verifiable than direct prompt-to-code workflows.

## Method Shape

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

## What Makes It Different

IntentGraph is not only:

- a code graph
- a visual programming tool
- a model-driven code generator
- a language workbench
- an AI coding assistant memory
- a requirements tracker

It combines those concerns into a source-layer method where generated code, reconstructed graph, evidence, authority, and history are checked together.

## AI Boundary

AI may propose graph changes or code changes.

AI must not be the final authority.

Acceptance must come from deterministic checks, evidence, explicit review, and round-trip validation.
