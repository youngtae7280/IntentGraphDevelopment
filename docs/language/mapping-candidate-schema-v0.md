# Mapping Candidate Schema v0

Status: P3.2 B1-bounded schema.

Mapping candidates represent possible intent-to-code mappings before they are accepted into the IntentGraph overlay. They are not authority. They must stay visible when ambiguous.

## Scope

Current benchmark:

```text
B1-typescript-rest-api
```

Current candidate artifact:

```text
docs/examples/b1-typescript-rest-api/mapping-candidates/p3.2-ambiguous-mutate-todo.candidates.json
```

## Candidate Artifact Requirements

Required top-level fields:

- `artifactRole: intentgraph-b1-mapping-candidates`
- `status: intentgraph-b1-mapping-candidates-declared`
- `scope: b1-typescript-rest-api-ambiguous-mapping-candidates`
- `benchmarkId: B1-typescript-rest-api`
- `candidates[]`

Every candidate must include:

- `id`
- `intentUnitId`
- `status`
- `accepted: false`
- `ambiguity`
- `candidateFactIds[]`
- `reason`

Allowed status values:

- `ambiguous-unresolved`
- `rejected`
- `accepted-by-authority`

In P3.2, `accepted-by-authority` is forbidden. Later phases may define authority-mediated acceptance.

## Validation

The verifier must fail when:

- role/status/scope is wrong
- a candidate is accepted
- a candidate status is `accepted-by-authority`
- ambiguity is missing
- candidate facts are missing
- candidate facts do not exist in supplied code facts
- AI authority is claimed

P3.2 proves only explicit ambiguous candidate visibility. It does not resolve ambiguity, edit code, repair mappings, or generate candidates automatically.
