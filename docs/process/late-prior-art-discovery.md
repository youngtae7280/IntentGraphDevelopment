# Late Prior-Art Discovery Protocol

Finding a stronger existing system during development is a normal event, not a failure.

## Immediate Action

Pause direction-setting work at the current boundary and classify the discovery.

## Record Format

```text
Name:
Link:
Capability:
Overlap with IntentGraph:
Where it is stronger:
Where IntentGraph remains different:
License and integration constraints:
Decision: replace | integrate | learn | differentiate
Roadmap impact:
```

## Classification Rules

- `replace`: stop building the duplicated capability and switch to the stronger system.
- `integrate`: keep IntentGraph as the semantic overlay and use the system as a backend, adapter, extractor, generated-code pass, or benchmark.
- `learn`: keep building, but update the design with the discovered pattern.
- `differentiate`: document why the overlap is superficial and continue.

## Existing Work Rule

Existing work must not be preserved by inertia.

Demote, adapt, or delete it:

- demote to fallback
- convert to adapter
- preserve only as benchmark fixture
- delete if it distracts from the stronger path

## Resume Rule

Resume implementation only after the roadmap and capability matrix are updated.
