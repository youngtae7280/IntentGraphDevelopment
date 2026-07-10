# Intent Mapping Schema v0

Status: P3.0 B1-bounded schema.

Intent mapping connects accepted Intent Units to code references and extracted code facts. It does not copy code text into the graph and does not let AI-generated mapping candidates become authority.

## Scope

Current benchmark:

```text
B1-typescript-rest-api
```

Current overlay:

```text
docs/examples/b1-typescript-rest-api/intentgraph.overlay.json
```

Current verifier:

```text
tools/verify_b1_intent_mapping.py
```

## Overlay Requirements

Required top-level fields:

- `artifactRole: intentgraph-b1-overlay`
- `status: intentgraph-b1-overlay-declared`
- `scope: b1-typescript-rest-api-intent-mapping`
- `benchmarkId: B1-typescript-rest-api`
- `intentUnits[]`
- `verification[]`
- `evidence[]`
- `authority[]`
- `history[]`

## Intent Unit Requirements

Every Intent Unit must include:

- `id`
- `kind`
- `title`
- `mappingStatus`
- `codeTextContained: false`
- `codeRefs[]`
- `codeFactRefs[]`
- `mappingObligations[]`

Allowed `mappingStatus` values:

- `resolved`
- `ambiguous`
- `unmapped-explicit`

If `mappingStatus` is `resolved`, all mapping obligations must resolve.

## Code References

Every `codeRef` must:

- have an `id`
- reference a `factId`
- declare `ownership: reference-only`

The referenced fact must exist in the supplied code facts.

## Code Fact References

Every `codeFactRef` must:

- have an `id`
- reference a `factId`
- declare `expectedFactKind`

The referenced fact must exist and match the expected kind.

## Mapping Obligations

Every mapping obligation must include:

- `id`
- `codeRefIds[]`
- `codeFactRefIds[]`
- `verificationIds[]`
- `evidenceIds[]`
- `authorityIds[]`
- `sourceTextEqualityRequired: false`

Obligation references must resolve within the overlay.

## Validation

The verifier must fail when:

- role/status/scope is wrong
- an Intent Unit contains code text
- a code ref is not `reference-only`
- a code ref points to a missing fact
- a code fact ref points to a missing fact
- a code fact ref expected kind mismatches the actual fact kind
- a mapping obligation references missing code refs, code fact refs, evidence, authority, or verification
- a resolved unit declares ambiguity
- source text equality is required
- AI authority is claimed

P3.0 proves only static B1 mapping verification. It does not prove natural-language request interpretation, automatic AI mapping, code planning, workbench usability, or real-project adoption.
