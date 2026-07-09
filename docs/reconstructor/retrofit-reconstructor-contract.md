# Retrofit Reconstructor Contract

Milestone: M3, revised by P1.0 for unit-structured B0

This contract defines the smallest `Retrofit` path for `B0-python-cli-calculator`. It is not a general source-code extractor.

## Scope

Inputs:

```text
generated/b0-python-cli-calculator/calc.py
generated/b0-python-cli-calculator/calc.intentgraph.json
```

Outputs:

```text
generated/b0-python-cli-calculator/reconstructed.graph.json
generated/b0-python-cli-calculator/retrofit-diagnostics.json
generated/b0-python-cli-calculator/code-only-projection.json
```

Reconstructor command:

```powershell
python tools/retrofit_reconstruct.py --source generated/b0-python-cli-calculator/calc.py --metadata generated/b0-python-cli-calculator/calc.intentgraph.json --out generated/b0-python-cli-calculator
```

## Contract

```text
Retrofit(C, mu, config) -> (G', D)
RetrofitCodeOnly(C, config) -> (G_code, D)
```

For M3:

- `C` is generated `calc.py`.
- `mu` is generated `calc.intentgraph.json`.
- `G'` is `reconstructed.graph.json`. In P1.0 this is `G_unit'`.
- `D` is `retrofit-diagnostics.json`.
- `G_code` is `code-only-projection.json`.

## Preconditions

- generated source file exists
- preservation metadata file exists
- metadata has `metadataVersion`, `graphDigest`, `nodeMap`, `edgeMap`, `projectionRules`, and `hiddenState.sourceGraphSnapshot`
- GraphIR v0.2 metadata has `unitMap`
- generated source hash matches metadata `generatedArtifacts`
- `hiddenState.sourceGraphSnapshot` digest matches metadata `graphDigest`
- `projectionRules.unclassified` is empty
- `nodeMap` is non-empty and every entry references existing graph nodes
- `nodeMap` covers every graph node required by `metadata.sourceMap` records
- `edgeMap` is non-empty and covers every graph edge in the snapshot
- `unitMap` covers every Intent Unit in the snapshot when `intentUnits` exist
- `nodeMap` line ranges are valid for the generated source

## Postconditions

- `reconstructed.graph.json` is written from preservation metadata, not hidden process memory
- reconstructed graph has `status: "m3-reconstructed"`
- unit identity, unit edges, and unit internal graph membership are preserved from metadata
- reconstruction diagnostics state whether metadata-backed reconstruction passed
- diagnostics do not claim M4 round-trip verification
- code-only projection records only facts recoverable from generated Python source
- code-only projection explicitly lists lost graph domains

## Code-Only Loss Model

`RetrofitCodeOnly(C, config)` may extract:

- module path
- function names
- function arguments
- simple call names
- CLI operations seen in generated source constants

It must not claim to recover:

- full product intent wording
- evidence records
- authority records
- semantic history
- Intent Unit contracts and refinement structure
- stable graph IDs
- exact source mapping identity
- accepted/rejected change state

## Exact Validation Commands

```powershell
python tools/retrofit_reconstruct.py --source generated/b0-python-cli-calculator/calc.py --metadata generated/b0-python-cli-calculator/calc.intentgraph.json --out generated/b0-python-cli-calculator
python -m json.tool generated/b0-python-cli-calculator/reconstructed.graph.json > $null
python -m json.tool generated/b0-python-cli-calculator/retrofit-diagnostics.json > $null
python -m json.tool generated/b0-python-cli-calculator/code-only-projection.json > $null
```

M4 will perform equality verification. M3 only reconstructs and reports.

## Non-Goals

M3 does not implement:

- round-trip verifier
- arbitrary Python-to-IntentGraph extraction
- code-only exact reconstruction
- evidence acceptance
- authority policy evaluation
- AI proposal workflow

P1.0 still does not claim code-only unit reconstruction. Intent Units are recovered through preservation metadata.
