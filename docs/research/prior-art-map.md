# Prior-Art Map

This document records known related systems. It is a starting map, not a completed survey.

## Research Rule

Before implementing a capability, update this map with the strongest known systems for that capability.

## Categories

### Model-Driven Engineering

Examples:

- OMG Model Driven Architecture
- Eclipse EMF
- Acceleo
- Sirius
- MetaEdit+

Relevance:

- model as source
- code generation
- platform abstraction

Risk:

- IntentGraph may duplicate mature model/code generation ideas if it does not define a sharper graph-as-source thesis.

### Language Workbenches

Examples:

- JetBrains MPS
- Xtext
- Spoofax

Relevance:

- language definition
- structured editing
- generators
- type systems
- projectional editing

Risk:

- IntentGraph compiler and workbench work may overlap strongly with language workbenches.

### Bidirectional Transformation

Examples:

- Triple Graph Grammars
- eMoflon::IBeX
- QVT

Relevance:

- graph/model synchronization
- round-trip transformation
- consistency checking

Risk:

- Round-trip verifier and reconstructor design should learn from this category before inventing custom semantics.

### Code Graph and Static Analysis

Examples:

- Joern / Code Property Graph
- CodeQL
- SCIP / LSIF
- Graphify

Relevance:

- code-to-graph extraction
- symbol relationships
- call/import/reference graphs
- code navigation and impact analysis

Risk:

- IntentGraph should not build a weak code extractor when these systems already provide mature code graph ideas.

### AI Coding Context Graphs

Examples:

- Graphify
- RepoGraph-style research
- repository memory and code graph retrieval systems

Relevance:

- graph context for AI coding
- repository-level relationship retrieval

Risk:

- IntentGraph must distinguish source-of-truth graph development from graph-assisted prompt context.

### Low-Code and Visual Programming

Examples:

- Node-RED
- LabVIEW
- Mendix
- OutSystems

Relevance:

- visual model as development surface
- generated applications

Risk:

- IntentGraph should avoid becoming a domain-specific low-code builder unless that is an explicit decision.

## Current Differentiation Claim

IntentGraph's proposed differentiation is the combination of:

- graph as primary source
- graph-to-code compiler
- code-to-graph reconstructor
- round-trip verifier
- evidence and authority as source-level concerns
- AI-assisted graph/code delta proposal with deterministic acceptance
