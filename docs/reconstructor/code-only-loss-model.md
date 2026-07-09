# Code-Only Loss Model

Milestone: M3

This document records what can and cannot be reconstructed from generated Python source without preservation metadata.

## Claim

```text
RetrofitCodeOnly(C, config) -> (G_code, D)
```

`G_code` is a lossy projection of code facts. It is not the source intent graph.

## Recoverable From `calc.py`

For the B0 generated calculator, code-only reconstruction can recover:

- module-level source path when provided by the caller
- function names: `add`, `sub`, `main`
- function argument names
- simple return expressions for `add` and `sub`
- direct calls from `main` to `add` and `sub`
- some CLI operation constants, such as `add` and `sub`
- exit-code literals used in generated source

## Not Recoverable From `calc.py` Alone

Code-only reconstruction cannot recover:

- full product intent wording
- requirement priorities
- domain concept descriptions
- evidence records
- authority records
- semantic graph history
- Intent Unit contracts, admission status, refinement structure, or reconstruction expectations
- stable semantic graph IDs
- metadata source-map node IDs
- accepted change state
- verifier equality mode

## Required Boundary

Any M3 or M4 report must distinguish:

- metadata-backed reconstruction: may reconstruct `G'`
- code-only projection: may reconstruct `G_code`

It is invalid to report:

```text
RetrofitCodeOnly(C) = G
```

for the B0 graph.
