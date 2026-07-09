# Capability Matrix

This matrix starts as a living research artifact. Fill it before major implementation.

| Capability | MPS | EMF/Xtext | eMoflon/TGG | Joern/CPG | CodeQL | Graphify | Sourcegraph | IntentGraph target |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| graph/model as primary source | high | high | medium | low | low | low | low | target |
| graph/model to source code | high | high | medium | none | none | none | none | target |
| source code to graph/model | low | medium | high | high | high | high | high | target |
| round-trip consistency | limited | limited | high | none | none | none | none | target |
| code symbol graph | medium | medium | medium | high | high | high | high | target |
| AI coding context | low | low | low | medium | medium | high | high | target |
| evidence as first-class source | low | low | low | low | low | low | low | target |
| authority and provenance boundary | low | low | low | medium | medium | low | medium | target |
| change history as graph source | low | low | medium | low | low | low | medium | target |

## Notes

The target is not to beat every existing system at its own specialty. The target is to connect source graph, generated code, reconstruction, round-trip verification, evidence, authority, and AI-assisted change control into one development method.
