# Native Compiler Contract

Milestone: M2

This contract defines the smallest deterministic `Native` path for `B0-python-cli-calculator`. It is not a general compiler architecture.

## Scope

Input:

```text
docs/examples/b0-python-cli-calculator.graph.json
```

Output:

```text
generated/b0-python-cli-calculator/calc.py
generated/b0-python-cli-calculator/calc.intentgraph.json
generated/b0-python-cli-calculator/native-diagnostics.json
```

Compiler command:

```powershell
python tools/native_compile.py --graph docs/examples/b0-python-cli-calculator.graph.json --out generated/b0-python-cli-calculator
```

## Contract

```text
Native(G, target, config) -> (C, mu, D)
```

For M2:

- `G` is the B0 GraphIR JSON fixture.
- `target` is `python`.
- `config` is embedded in the compiler diagnostics as `native-python-b0-v0`.
- `C` is `calc.py`.
- `mu` is `calc.intentgraph.json`.
- `D` is `native-diagnostics.json`.

## Preconditions

- `graphirVersion` is `0.1.0`.
- `benchmarkId` is `B0-python-cli-calculator`.
- exactly one native projection target exists and its language is `python`.
- required M1 nodes exist for module, CLI, `add`, `sub`, and `main`.
- required source-map nodes exist for module, CLI, `add`, `sub`, and `main`.
- test cases exist for add and subtract.
- authority, evidence, and history nodes exist.
- graph IDs and edge IDs are unique.
- edge endpoints resolve.

## Postconditions

- generated source is deterministic for the same canonical graph and compiler version.
- generated source uses only the Python standard library.
- generated source implements:
  - `python calc.py add 2 3` -> stdout `5\n`, exit code `0`
  - `python calc.py sub 5 2` -> stdout `3\n`, exit code `0`
- invalid operation or invalid integer input exits with code `2`.
- metadata includes:
  - graph digest
  - compiler contract
  - node map
  - edge map
  - projection rules
  - hidden state needed for exact round-trip
  - generated file hashes
- diagnostics include validation status, generated artifact paths, and warnings.

## Exact Validation Commands

Run these commands for M2 validation:

```powershell
python tools/native_compile.py --graph docs/examples/b0-python-cli-calculator.graph.json --out generated/b0-python-cli-calculator
python -m py_compile generated/b0-python-cli-calculator/calc.py
python generated/b0-python-cli-calculator/calc.py add 2 3
python generated/b0-python-cli-calculator/calc.py sub 5 2
```

Expected command outputs:

```text
python generated/b0-python-cli-calculator/calc.py add 2 3
5

python generated/b0-python-cli-calculator/calc.py sub 5 2
3
```

Determinism check:

```powershell
$tmp = Join-Path $env:TEMP "intentgraph-b0-native-check"
Remove-Item -Recurse -Force $tmp -ErrorAction SilentlyContinue
python tools/native_compile.py --graph docs/examples/b0-python-cli-calculator.graph.json --out $tmp
Compare-Object (Get-Content generated/b0-python-cli-calculator/calc.py) (Get-Content (Join-Path $tmp "calc.py"))
Compare-Object (Get-Content generated/b0-python-cli-calculator/calc.intentgraph.json) (Get-Content (Join-Path $tmp "calc.intentgraph.json"))
Compare-Object (Get-Content generated/b0-python-cli-calculator/native-diagnostics.json) (Get-Content (Join-Path $tmp "native-diagnostics.json"))
```

The `Compare-Object` commands should emit no differences.

## Non-Goals

M2 does not implement:

- retrofit reconstruction
- round-trip verifier
- broad GraphIR validation
- arbitrary Python generation
- package setup
- language workbench behavior
- AI proposal workflow

## M3 Dependency

M3 must be able to consume `calc.py` and `calc.intentgraph.json` without relying on hidden compiler memory.
