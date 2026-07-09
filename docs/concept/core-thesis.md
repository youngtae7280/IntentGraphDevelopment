# Core Thesis

## One Sentence

IntentGraph Development treats intent graphs as development-semantic overlays linked to existing source code artifacts, making mapping consistency, evidence, authority, and semantic change history first-class development concerns.

## Short Form

Code remains the implementation source. IntentGraph is the semantic overlay.

## Problem

AI-assisted development often starts from vague human intent and ends as source code. The middle of that process is under-specified:

- intent is not preserved as durable semantic state linked to code
- implementation changes are difficult to trace back to accepted intent, evidence, and authority
- evidence and validation are usually stored outside the source model
- authority and review boundaries are implicit
- later maintenance requires reconstructing context from code, commits, issue trackers, and chat history
- AI-generated changes may look plausible without being accepted by a deterministic authority boundary

## Hypothesis

If intent, behavior contracts, code references, extracted code facts, mappings, evidence, authority, and change history are represented in an overlay graph, then AI-assisted development can become more inspectable, repeatable, and verifiable than direct prompt-to-code workflows.

The thesis is not that model-to-code generation, graph-based code analysis, provenance, policy, or visualization are new. Mature systems already own large parts of those spaces. The thesis is that IntentGraph can add value by binding intent, extracted code facts, mapping obligations, evidence, authority, and semantic history into one consistency discipline over ordinary source code.

## Method Shape

Default operations:

```text
Extract(C) -> X
Map(I, X) -> M
Plan(I, C, X, M, request) -> DeltaC, DeltaI, DeltaM
Verify(I, C', X', M', E, A) -> pass/fail
Record(H, accepted delta)
```

Graph-first generation is a limited mode for greenfield or generated-code areas:

```text
G -> C -> G'
```

Code-first maintenance is the default frame for existing projects:

```text
C -> X -> M/I -> C'
```

Expected maintenance check:

```text
Behavior(C') ~= Behavior(C)
```

The goal is behavior, contract, mapping, evidence, and authority preservation, not textual source equality.

## What Makes It Different

IntentGraph is not only:

- a code graph
- a visual programming tool
- a replacement programming language
- a universal model-driven code generator
- a language workbench
- an AI coding assistant memory
- a requirements tracker
- a provenance or policy engine

The differentiation claim is the combined overlay discipline:

- semantic overlay over existing code
- code fact extraction and mapping boundary
- consistency/change orchestration boundary
- explicit preservation metadata
- declared behavior, contract, equality, and projection rules
- evidence attached to graph nodes, code references, mappings, and validation claims
- authority separated from AI proposal
- semantic change history linked to ordinary version control

## AI Boundary

AI may propose graph changes or code changes.

AI must not be the final authority.

Acceptance must come from deterministic checks, evidence, explicit review, policy where needed, and round-trip validation.

## Phase 0 Proof Shape

Phase 0 did not prove a full platform. It proved a tiny metadata-backed round-trip experiment:

```text
G -> Native(G) -> (C, mu) -> Retrofit(C, mu) -> G' -> Verify(G, G')
```

That experiment is useful as a generated-code feasibility slice, but it should not be overclaimed as the universal IntentGraph architecture. The next work must reframe the model around semantic overlay mapping for existing code.
