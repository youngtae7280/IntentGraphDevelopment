# Prior-Art Gate

Use this gate before implementing a major feature, new engine, new repository, compiler, reconstructor, graph extractor, visualization layer, or AI workflow.

## Purpose

Avoid rebuilding an existing stronger system by accident.

## Required Questions

Before implementation, answer:

1. What exact capability are we building?
2. Which existing products, open-source projects, standards, and papers already address it?
3. Which existing system is strongest on this capability?
4. Are we replacing, integrating, learning from, or differentiating from that system?
5. What benchmark proves that our direction is better for IntentGraph's purpose?

## Decision Categories

- `replace`: use the stronger existing system instead of building our own.
- `integrate`: consume the existing system through an adapter or import path.
- `learn`: adopt design ideas without depending on the system.
- `differentiate`: continue because our purpose is materially different.

## Minimum Artifact Set

For every major track, keep:

- prior-art map
- capability matrix
- benchmark plan
- build/borrow/integrate decision
- late prior-art discovery notes

## Merge Rule

Do not merge a major implementation before the prior-art gate has a written decision.
