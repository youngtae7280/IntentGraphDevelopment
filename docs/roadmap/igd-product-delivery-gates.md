# IGD Product Goal And Delivery Gates

Status: controlling delivery plan; G0 and G1 completed.
Current execution gate: **G2 - isolated reviewed single-file application proof**.
Current implementation boundary: no real target source application is authorized until
the isolated G2 proof and a separate target authorization both pass.

## Product Goal

IntentGraph Development (IGD) is a local-first semantic-overlay product for
human-and-AI-assisted software development. Source code remains the implementation
authority. IGD records and connects intent (`I`), code (`C`), extracted code facts
(`X`), mappings (`M`), evidence (`E`), authority (`A`), and semantic history (`H`).

For an initially supported C# project, a user must be able to complete this bounded
development loop:

```text
record request
-> inspect code facts and mappings
-> review a bounded code and graph proposal
-> inspect verification, evidence, and authority requirements
-> explicitly approve one exact proposal
-> apply it safely to the expected source baseline
-> verify the result and record evidence
-> refresh the overlay and inspect the revision history in the Workbench
```

An AI may produce request, mapping, or change-proposal candidates. It may not accept
evidence, grant authority, approve a proposal, or apply source changes without an
explicit human decision and deterministic validation.

## Product Definition Of Done

IGD is not a daily-use product until all of the following have direct evidence:

1. A new user can install and open a supported local C# project without a repository
   checkout or project-specific handholding.
2. A real work request can become an inspectable intent/mapping/proposal record.
3. The Workbench connects the affected graph delta, code diff, verification status,
   evidence, authority, and history for that request.
4. An explicit human approval can apply one exact, bounded proposal only when its
   preimage, scope, and authority requirements still match.
5. Failed application, verification, or refresh leaves source and active revision in
   a recoverable, truthful state; an approved rollback is available.
6. At least one real-project benchmark shows an inspection or quality benefit over a
   stated ordinary AI-coding baseline, without concealing time or failure costs.
7. Code-fact coverage and graph navigation are benchmarked against stronger code
   intelligence tools; IGD integrates or adapts them where that is better than
   rebuilding them.
8. Workbench usability, graph readability, and performance are accepted through
   actual user review, not inferred from a nonblank screenshot or renderer telemetry.
9. Supported installation, upgrade, repair, uninstall, local-data, editor, GitHub,
   and team-policy boundaries have their own explicit release evidence before public
   or team-use claims.

## Current Truth

P9.35 is a Level 4 reviewed source-refresh slice. It can stage, review, accept, or
discard a new immutable source snapshot while preserving prior revisions and marking
snapshot-bound records stale. It does **not** apply a reviewed code proposal to the
target source. That missing application step is the highest-value non-visual daily-use
gap.

The WindowsUtility P8 source-application experiment is adoption evidence only. It
does not make the current IGD product capable of normal reviewed proposal application.

The current C# graph uses syntax facts plus a bounded local Roslyn relation sidecar.
It is not a claim of Graphify, SCIP, CodeQL, or full project-semantic parity. The
Workbench has functional graph, delta, diff, evidence, authority, and history
surfaces, but visual quality remains reopened until user acceptance is recorded.

## Delivery Gates

### G0 - Product Goal And Roadmap Correction

Purpose: make the current objective, completed evidence, deferred work, and phase
status unambiguous before more implementation.

Required outputs:

- this plan;
- a test and verification plan;
- current-status links in the README, Start Here, and product roadmap;
- an explicit distinction between bounded phase evidence and product completion.

Exit criteria:

- no controlling document names P9.34.R3 as the current state;
- P9.35 and its remaining source-application gap are discoverable from the entry
  documents;
- future work is ordered by delivery dependency rather than P-number momentum.

### G1 - Reviewed Proposal Application Product Gate (Plan Only)

Purpose: define the safe source-application contract before any product path writes
target source.

Required design decisions:

- exact proposal and preimage identity;
- explicit human approval record and authority scope;
- source containment, allowed patch scope, and atomic write strategy;
- backup or reversible preimage strategy;
- rollback semantics before and after verification;
- required build/test/static-analysis evidence and failure handling;
- refresh, revision, stale-record, and history semantics after application;
- conflict, drift, partial-write, and concurrent-writer behavior.

Exit criteria:

- product contract, test plan, negative-probe matrix, real-project benchmark plan,
  and review are committed;
- the P8.41-P8.46 experiment is compared rather than copied blindly;
- no target write is implemented or authorized by G1 alone.

### G2 - Safe Reviewed Proposal Application

Purpose: implement the smallest end-to-end product application path for one bounded
C# proposal shape.

Exit criteria:

- one approved proposal can pass preflight, apply atomically, run declared local
  verification, refresh the semantic overlay, and record one coherent revision;
- every unsafe, stale, overbroad, unauthorised, partially written, or failed-verifier
  case fails closed with source preservation or an explicit rollback record;
- the Workbench exposes before/after code and graph deltas, verification evidence,
  authority decision, and history.

### G3 - Real-Project Daily Loop Benchmark

Purpose: prove that the G2 loop is useful on more than one realistic WindowsUtility
change class.

Exit criteria:

- benchmark at least additive behavior, behavior-preserving refactor, and contract
  or validation change;
- compare time, review effort, regression detection, and impact-scope completeness
  with a declared ordinary AI-coding baseline;
- record failures and decide continue, redesign, or stop from the evidence.

### G4 - Code Intelligence Adapter And Graph Quality

Purpose: make code facts sufficiently useful for review without rebuilding a mature
code intelligence engine.

Exit criteria:

- document a build/borrow/integrate decision for Roslyn, Graphify, SCIP, Tree-sitter,
  or another chosen adapter;
- measure coverage, stability, incremental refresh, and query/navigation quality for
  files, symbols, calls, references, inheritance, implementations, tests, and
  supported cross-file relations;
- unsupported semantics remain explicit rather than being presented as facts.

### G5 - AI-Assisted Intent And Proposal Candidates

Purpose: let a natural-language request produce inspectable candidates without
promoting AI output to authority.

Exit criteria:

- candidate intent, mapping, ambiguity, impact, test, evidence, and authority
  requirements are inspectable and traceable to source facts;
- ambiguity, unsupported claims, and overbroad scope block automatic acceptance;
- benchmark measures whether assistance improves the G3 workflow.

### G6 - Workbench Acceptance And Performance

Purpose: make the complete daily loop understandable in one local interface.

Exit criteria:

- graph, code diff, graph delta, evidence, authority, and history are selectable and
  connected for current and historical work;
- performance budgets are measured for supported graph-size bands;
- user review accepts comprehension, navigation, deep inspection, and visual quality.

Visual renderer refinements remain deferred until this gate. A renderer benchmark or
headless screenshot cannot by itself close G6.

### G7 - Supported Product Distribution And Integration

Purpose: make the proven local loop maintainable by users beyond the development
repository.

Exit criteria:

- self-contained or explicitly supported runtime matrix;
- upgrade, repair, rollback, uninstall, and local-data preservation tests;
- onboarding and sample workflow from request to reviewed applied change;
- editor, GitHub, and team-policy integrations preserve the same authority boundary;
- release review approves the supported scope without claiming unsupported languages
  or team automation.

## Gate Discipline

Every implementation gate must create, before implementation:

1. a product contract;
2. a test and validation plan;
3. current prior-art and build/borrow/integrate decision;
4. benchmark inputs and pass/fail thresholds;
5. explicit authority and non-goal boundaries.

Every gate must then run deterministic positive, negative, regression, performance,
and real-user checks appropriate to its scope. A passing narrow harness does not prove
a broader product claim. A gate that misses its quality target is repaired or
redesigned before the next gate opens. After two failed repair cycles, the coordinator
must rerun the prior-art and architecture review rather than extend a micro-milestone
series indefinitely.

## Deferred Work

- renderer/material/layout polish until G6;
- public signing, release, provider APIs, and external deployment until G7;
- a new broad code-graph engine unless G4's adapter decision proves it necessary;
- automatic evidence acceptance, proposal approval, source application, or AI
  authority in every gate.
