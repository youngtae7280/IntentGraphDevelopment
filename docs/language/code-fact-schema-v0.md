# Code Fact Schema v0

Status: P2.0 B1-bounded schema.

This schema defines the first IntentGraph code fact boundary for Phase B. It is intentionally small and benchmark-bounded. It is not a broad language index, static analysis graph, or code navigation database.

## Scope

Current benchmark:

```text
B1-typescript-rest-api
```

Current extractor:

```text
tools/extract_b1_code_facts.py
```

The extractor is fixture-bounded and must declare:

```json
{
  "deterministic": true,
  "broadExtractor": false
}
```

## Code Fact Report

Required top-level fields:

- `artifactRole: intentgraph-code-facts`
- `status: intentgraph-code-facts-extracted`
- `scope: b1-typescript-rest-api-code-facts`
- `benchmarkId: B1-typescript-rest-api`
- `codeFactsVersion`
- `sourceRoot`
- `extractor`
- `sourceDigests`
- `facts[]`
- `relations[]`

## Fact Requirements

Every fact must include:

- `id`
- `kind`
- `sourceFile`
- `sourceDigest`
- `extractor`
- `extractorVersion`
- `confidence`
- `sourceLocation` or `sourceLocationStatus`

Allowed fact kinds in v0:

- `file`
- `module`
- `function`
- `type`
- `route`
- `test`
- `import`
- `call`

Allowed confidence values:

- `extracted`
- `inferred`
- `ambiguous`

Source text must not be copied into facts as authority. Facts point to source files, digests, and locations.

## Relation Requirements

Every relation must include:

- `id`
- `kind`
- `from`
- `to`

Allowed relation kinds in v0:

- `contains`
- `imports`
- `references`
- `calls`
- `handles_route`
- `tests`
- `depends_on`

`from` and `to` must resolve to endpoint facts. Endpoint fact kinds are:

- `file`
- `module`
- `function`
- `type`
- `route`
- `test`

## Validation

The validator is:

```text
tools/validate_b1_code_facts.py
```

It must fail when:

- role, status, scope, or benchmark is wrong
- extractor is not deterministic
- extractor claims broad extraction
- a fact kind is unknown
- a relation kind is unknown
- a relation endpoint is missing
- required provenance is missing
- source digest is stale
- source text is embedded
- source location or range status is missing

The repeatable negative harness is:

```text
tools/run_b1_code_fact_negative_probes.py
```

P2.0 proves only the B1 bounded code fact contract. It does not prove general TypeScript support, broad extraction, semantic type checking, static analysis, workbench usability, AI proposal quality, or real-project adoption.
