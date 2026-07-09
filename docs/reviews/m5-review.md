# M5 Milestone Review

Milestone: M5 - Evidence and Authority Slice
Date: 2026-07-09
Reviewer: IntentGraphDevelopment Roadmap Orchestrator

Declared quality target: Level 4

## Produced Artifacts

- `docs/evidence/evidence-model.md`
- `docs/authority/authority-model.md`
- `docs/history/change-history-model.md`
- `docs/verifier/evidence-authority-history-verifier.md`
- updated `docs/examples/b0-python-cli-calculator.graph.json`
- updated `tools/verify_roundtrip.py`
- regenerated B0 generated source, preservation metadata, reconstruction output, code-only projection, diagnostics, and verifier report
- `docs/reviews/m5-review.md`

## Benchmarks Run

Commands run:

```powershell
python tools/native_compile.py --graph docs/examples/b0-python-cli-calculator.graph.json --out generated/b0-python-cli-calculator
python -m py_compile generated/b0-python-cli-calculator/calc.py
python generated/b0-python-cli-calculator/calc.py add 2 3
python generated/b0-python-cli-calculator/calc.py sub 5 2
python tools/retrofit_reconstruct.py --source generated/b0-python-cli-calculator/calc.py --metadata generated/b0-python-cli-calculator/calc.intentgraph.json --out generated/b0-python-cli-calculator
python tools/verify_roundtrip.py --original docs/examples/b0-python-cli-calculator.graph.json --reconstructed generated/b0-python-cli-calculator/reconstructed.graph.json --metadata generated/b0-python-cli-calculator/calc.intentgraph.json --code-only generated/b0-python-cli-calculator/code-only-projection.json --out generated/b0-python-cli-calculator/roundtrip-report.json
python -m py_compile tools/native_compile.py tools/retrofit_reconstruct.py tools/verify_roundtrip.py generated/b0-python-cli-calculator/calc.py
```

Expected runtime checks passed:

- `add 2 3` prints `5`
- `sub 5 2` prints `3`
- invalid operation exits with code `2`
- invalid integer exits with code `2`

Semantic report summary:

```text
result = pass
graphEqual = true
verifierContract = roundtrip-b0-m5-eah-v0
semanticValidation.result = pass
evidence.recordCount = 3
evidence.observedCount = 3
evidence.acceptedCount = 3
authority.recordCount = 2
authority.acceptedCount = 2
authority.aiFinalAuthorityCount = 0
history.recordCount = 2
history.acceptedCount = 2
history.gitLinkedCount = 1
history.gitVerifiedCount = 1
history.acceptedSequenceContiguous = true
history.pendingCurrentMilestoneCount = 1
m5ClaimScope.level4Claim = metadata-backed preservation with semantic validation
m5ClaimScope.codeDerivedRecovery = false
```

Negative semantic checks:

- accepted verifier evidence with `status: "fail"` fails
- accepted authority that authorizes only an unsupported target kind fails
- accepted authority with `decidedByType: "AI"` fails after actor-type normalization
- accepted history with fake Git commit `deadbeef` fails
- accepted history sequence gap fails
- accepted evidence with missing authority fails
- accepted history delta with missing pending Git boundary fails
- observed evidence with a missing local artifact ref fails

## Prior-Art Comparison

M5 stayed inside the M0 decisions:

- learned from PROV/OpenLineage vocabulary pressure but did not build a provenance database
- learned from SLSA, in-toto, SPDX, and GUAC pressure but did not expand into supply-chain attestation
- learned from OPA, CODEOWNERS, protected branches, in-toto layouts, and TUF roles but did not build a policy language
- borrowed Git as the file-history substrate and added only semantic graph delta meaning
- kept generated code and imported/code-only facts out of authority

## Result

Proved for `B0-python-cli-calculator`:

- evidence records survive `G -> Native(G) -> Retrofit(C, mu) -> G'`
- authority records survive the same loop
- semantic history records survive the same loop
- preservation is not only count-based; domain subgraph digests match for evidence, authority, and history
- accepted evidence requires compatible status, observed evidence, local artifact refs, an accepted authority record, and an `authorizes` edge
- accepted verifier-report evidence requires `status: "pass"` and the current or a passing verifier report
- accepted planned evidence must be explicitly plan-only and not runtime proof
- accepted authority cannot use AI as final decision authority under case-normalized actor type comparison
- accepted authority can authorize only allowed target kinds in the B0 subset
- accepted history deltas require changed graph targets, accepted authority, contiguous sequence, and valid Git linkage or explicit current-milestone boundary
- code-only projection is not used as evidence, authority, or history source
- Level 4 is metadata-backed preservation with semantic validation, not code-derived recovery of non-code graph meaning

Changed:

- the B0 graph now has three evidence records, including the verifier report
- the B0 graph now has two authority records
- the initial history delta links to the M1 graph creation commit
- the M5 semantic delta records the in-flight current-milestone Git boundary explicitly
- the verifier report contract is now `roundtrip-b0-m5-eah-v0`

## Round-Trip Status

Current status:

```text
Native(G) -> (C, mu, D1)      implemented in M2
Retrofit(C, mu) -> (G', D2)   implemented in M3
Verify(G, G')                 implemented in M4
VerifyM5(G, G')               implemented in M5
```

The M5 report preserves the M4 exact normalized graph equality claim and adds semantic validation for evidence, authority, and history.

This remains a metadata-backed round trip. Evidence, authority, and history are reconstructed from preservation metadata, including `hiddenState.sourceGraphSnapshot`; they are not recovered from generated Python source alone.

## Evidence Status

Evidence is Level 4 for the B0 slice:

- observed evidence and accepted evidence are separate fields
- accepted evidence status must be compatible with the evidence type
- accepted evidence requires `acceptedByAuthority`
- local artifact refs are checked
- accepted verifier-report evidence requires a passing verifier report
- accepted planned evidence is explicitly marked as plan-only, not runtime proof
- code-only projection is explicitly not used as evidence source

## Authority Status

Authority is Level 4 for the B0 slice:

- accepted authority records must have explicit allowed target kinds
- AI cannot be final authority for accepted records under case-normalized actor type comparison
- unknown actor types fail validation
- accepted evidence and accepted history must be backed by accepted authority
- the model remains an envelope rather than a policy engine

## History Status

Semantic history is Level 4 for the B0 slice:

- history deltas have positive unique sequence values
- accepted history sequence values are contiguous from `1..n`
- accepted deltas link to changed nodes
- accepted deltas are authorized
- one historical delta links to a verified local M1 Git commit
- the current M5 in-flight delta uses an explicit `pending-current-milestone` boundary rather than pretending the graph can know its own future commit hash

## Red-Team Review

The M5 critic plus local review found three P1 blockers, four P2 issues, and two P3 issues before review closure:

- accepted failing evidence could still pass
- accepted authority scope was too weak
- AI final authority comparison was spelling-fragile
- Git linkage was syntactic only
- accepted history sequence gaps could pass
- Level 4 wording could imply stronger code-derived recovery than the implementation proves
- evidence artifact refs were typed but not checked for existence
- fixture round-trip expectation wording was stale
- the M5 verifier report initially reused the M4 contract label

All P1/P2 issues were fixed before review closure.

## Issue Review

| ID | Severity | Issue | Resolution |
|---|---|---|---|
| M5-P1-001 | P1 | Accepted evidence could have `status: "fail"` and still pass semantic validation. | Resolved by adding accepted-evidence status compatibility rules, verifier-report `pass` requirements, and plan-only scope requirements for accepted planned evidence. |
| M5-P1-002 | P1 | Accepted authority only needed any target, including unsupported graph target kinds. | Resolved by validating authorized target existence and allowed target kinds: `evidence.record`, `history.delta`, and `projection.target`. |
| M5-P1-003 | P1 | AI final authority rejection only checked exact lowercase `ai`. | Resolved by normalizing actor type enums and rejecting accepted AI final authority regardless of casing. |
| M5-P2-001 | P2 | Evidence `artifactRefs` were only checked as strings, weakening the observed-evidence claim. | Resolved by verifying local artifact refs and allowing the current verifier report path as `current-report-output`. |
| M5-P2-002 | P2 | Non-null `gitCommit` values were regex-checked but not verified as local commits. | Resolved by checking `git cat-file -e <sha>^{commit}` for non-null Git commits. |
| M5-P2-003 | P2 | Accepted history sequence gaps could pass. | Resolved by requiring accepted B0 history sequence values to be contiguous from `1..n`. |
| M5-P2-004 | P2 | M5 review/report wording could imply code-derived evidence, authority, and history recovery. | Resolved by explicitly scoping Level 4 to metadata-backed preservation with semantic validation. |
| M5-P3-001 | P3 | Fixture expectation wording still said the round-trip would exist once M2-M4 implementations exist. | Resolved by updating the B0 fixture expectation to the implemented M4/M5 metadata-backed verifier. |
| M5-P3-002 | P3 | The M5 verifier report initially reused the M4 verifier contract label. | Resolved by changing the report contract to `roundtrip-b0-m5-eah-v0` and report version to `0.2.0`. |

No unresolved P0/P1 issues remain. All P2 issues are resolved.

## Decision

Decision: continue

Achieved quality level: Level 4.

M5 passes its declared quality bar.

## Required Changes Before Next Milestone

M6 must:

- represent AI output as proposal data, not accepted graph state
- define a proposal delta format
- run deterministic validation before acceptance
- require explicit authority before applying accepted deltas
- prove rejection of at least one invalid or unauthorized proposal
