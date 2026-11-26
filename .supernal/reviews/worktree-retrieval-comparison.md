---
task: retrieval-comparison
branch: worktree-retrieval-comparison
reviewed_patch_id: 7c4dd25ffdc93f08da99703cfe086692461707df
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/c3_safety
reviewer_output_sha256: 20292da24aca7e82715fff014cda56ecc31fdbf5f0ec16ce4a738bf5ae8b4c4f
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 5, low: 0 }
resolved: { fixed: 5, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 28, lines: 4305 }
---

## Conclusion
Ready to land: yes
The fixed comparison passed its exact-runtime checks, independent code and actual-evidence reviews, and persistent coverage handoff. It retained the negative/mixed result and raw baseline. Four local-supervisor issues and one graph metadata issue were fixed and verified before acceptance.

## Reviewer report
### Unguided final evidence review: /root/c2_critic

Approved for landing; no actionable findings.

Reconciled final documentation, plans, README, TODO and registry with retained evaluations, summaries, caller records, freeze and refusal records. Metrics, per-query changes, timings, identities and coverage handoff agree. All 24 frozen source hashes remain unchanged. The archived final build contains 62 records versus 43 previously, with no removed slugs.

Final 28-file snapshot manifest SHA-256: `af538435aa0addbef1b6e32154db386c9c7a61a8d19f3cd9ad9c22aa8d8ca6aa`

Manifest uses sorted `<file SHA-256>  <repository-relative path>\n` entries against base `eedcb85866f76a1bdd9ec156bb790e9d9dd7bbab`.

Read-only artifact reconciliation only: no databases opened, files changed, tests rerun or searches executed.

### Final typed-graph correction: /root/c2_critic

Approved the correction at `fab6cb67eb4a9c69162c127f43c36c16d5626eeb`. Exactly two relationships changed from `cites` to `depends_on`; no other content changed.

Independent read-only compilation passed: **109 nodes, 127 edges, 18 committed documents and 32 bibliographic sources**. No remaining endpoint issues.

Count this as **one fixed metadata-validation finding**: the earlier review checked endpoint existence but missed relationship-kind constraints.

Registry SHA-256: `2dfb658bb57a537967c380c816b00a4280fc218fa35df928833d3e11d2505de4`

Graph payload hash: `851784d4a5fad047988c402a0c1c0239687dd109fa84dbf46679bcb78198e21e`

### Guided integrated review: /root/c3_safety

No actionable findings in the guided integrated review against `eedcb85866f76a1bdd9ec156bb790e9d9dd7bbab`.

Inspected receipt migration, selected-source projection, maps/entities, empty FTS rows, locked recomputation, exclusive claims, source identity guards, measurement separation, bounded artifact capture, comparison order and successor selection.

**15 focused owned-fixture tests passed in 7.563 seconds.** They covered legacy replay, chunk preflight/reassembly, unselected-source exclusion, commit-time corruption, revalidation deadlines, recipe concurrency, decoder incompatibility, entity provenance, empty-row statistics, execution order, reproduction failure without deltas, coverage continuation and durable protocol mismatch. `git diff --check` passed.

The adapter’s protocol bytes are an opaque retained binding; historical bridge and pre-execution protocol enforcement remain supervisor responsibilities. Historical receipt validation is not independent execution proof, and in-process guards are not a security boundary.

Reviewed production SHA-256 identities:

```text
retrieval.py
9d1e0ee4121e7a7e6a6498696fbbcdac88a47640ea4c60b8f2e3cd417a7444c1
retrieval_contracts.py
38b062a814cfdd53b02691349705755eaebc826e8f27b331b706eca468c9b9c9
retrieval_indexing.py
97b8289ad50626ab5d05dc9fc2fcf814f57acf5a0be15a712670ebebaf06b569
retrieval_evaluation.py
8a00abf4cb6a225e65c9828e2aae874d6456115523b26c1687f76910617fc39c
retrieval_assessment.py
7dafcdfb7821c7f8e15677da6800238c241e8561c6fe7c81d323ec9579ddabf5
improvement.py
1a03821c0b84d1347a8d80bc7492047e1e57b12b350522acd0560a93351ddff9
```

No edits, installations, full-suite run, private-wrapper review or original evidence access.

### Actual evidence verification: /root/c3_safety

No actionable discrepancy in the completed C3 evidence.

Independently opened all three ledgers **read-only**, validated all four receipts and rescored them under the exact C1 interpreter. Saved evaluations matched completely. Verified:

- Original 40-event history equals the experiment’s inherited prefix; original database, WAL and freshly enumerated blob hashes/mtimes match the freeze.
- Protocol, freeze, supervisor hashes and all 24 production-file hashes match. Eleven static input fields agree across the protocol and every report.
- Claims/terminals are ordered `45→61`, `62→78`, `79→95`, `96→112`; protocol/freeze/supervisors precede them at events 41–44.
- Both pairs reproduce their results, projections and scores. Raw also matches historical C1 results and numerical scores.
- HTML ties span recall, reduces source recall@1 from 8/8 to 7/8, and worsens both reciprocal-rank metrics. Seven queries change ranked windows.
- Raw remains the baseline; adoption is `not_authorized`. C2→C3 is correctly `incomparable_contract_change`.
- Improvement history verifies **193 events, nine completed assessments, no unfinished claims**, with successor `retrieval-comparison-20261126:next` selecting fresh coverage.

Verified identities:

```text
Common measurement:
d00059031feb4fdb74ed3e5ed46ca5b655927ccdec3ab5ecac377ba8b1df8787
Execution freeze file:
770c2c4dd8fc1c54af44b52b741ef42bbbea48e013f9e1aec24b72991f0ab052
Summary file:
98fb28990a4563ae9d3e5be5769ef73befd44b9902bcf592c2f60e75094b94e3
Final verification file:
57ee9f4574ea120ddd1028ce30fd8a6f2fd9c0737c73f73a55ff39e01994457f
Experiment head:
fa7c829132b559726f50db2a7c122d02ca152c95b03945c79739678a92f52f61
Improvement head:
2446a79acc1af8aee00ef5325205bdd261116e848a0aeb508effb50ada0b9949
```

The refused initial runtime freeze is retained and linked; protocol bytes were unchanged. Caller records identify the required interpreter and separate inner/caller timing. These remain local retrospective records, without independent timestamp/execution assurance or holdout generalization.

No search execution, writes, full-suite rerun, browser use or deployment performed during this review.

### Local supervisor repair verification: /root/retrieval_safety

All four repairs independently verified; no outstanding findings in this review.

- Optimized execution preserves the gates.
- Temporary-store WAL changes and added blobs are detected.
- All 11 frozen input fields reject mismatches.
- Simulated timeout preserves partial output, status and elapsed time before stopping.
- Documentation correctly assigns protocol interpretation and historical bridge checks to the supervisor.

Verified wrapper hashes: run `bb53af36…57e935`; assessment `7154f031…6de2da`.

No actual modes, child processes or real stores executed; no edits.

All narrow wrapper controls passed using **Python 3.14.8 / SQLite 3.53.4** at the exact C1 executable.

Confirmed optimized gates, all 11 lineage checks, WAL/blob change detection, stable closed-store checks, and timeout evidence preservation. Wrapper hashes remain unchanged.

No real modes, real stores, child processes, or edits.

## Checks run, and what each covered
- Exact C1 runtime: 487 engine tests passed in 349.479 seconds, Python 3.14.8 / SQLite 3.53.4. Initial Conda 3.12 validation passed 485 plus two later cases; the historical runtime gate refused the first freeze before any fork/search, and that refusal is retained.
- Core integration: 123 runner/indexer/contracts/evaluator/CLI/read-only checks. Final adapter/controller ownership: 25 adapter and 20 integration cases plus source-boundary controls. Independent partial, unguided and guided reviews exercised mapping, legacy behavior, source/bytecode identity, commit mutation, bounds, comparison order, failure reporting and coverage continuation.
- Changed CI passed under both runtimes: four fresh processes on owned HTML, separate scoring and an actual fixed controller dispatch. It is not a real-corpus quality claim.
- Original C1 read-only bridge preserved counts, metrics and per-case fields. Original database, WAL/blob inventory and logical head remained unchanged; exact 40-event prefix inherited into owned experiment store.
- Actual raw A/B result hash equals C1; actual HTML A/B results and projections reproduce. Both methods retain all82 windows and all12 questions; three Markdown projections stay exact raw text. HTML ties support recall but regresses source@1 and both MRR measures. Raw remains baseline; no post-output recipe/gold/query changes.
- Four actual retrieval callers total1.044194542seconds; dispatcher9.092801959seconds, outer assessment9.328843292seconds. Program model calls/external spend zero; agent effort unmeasured. Costs retain scope and all four individual receipts.
- Actual assessment3df58467e3564a448f82590d3a264f55 completes as retrieval-comparison-20261126, captures35artifacts/1,508,406bytes, verifies193 improvement events/9 completed assessments/no unfinished claims and atomically selects fresh coverage. Experiment store112events verified. Original and assessment evidence remain unchanged by scoring.
- Final local site build passed; generated content43→62 records with no removed slugs, exact artifact archived/restored. Existing build skips TS/lint; no TypeScript changed. No browser/rendered verification.
- Knowledge compiler caught two invalid relationship kinds; corrected only those edges to existing depends_on. Independent and author compilation now pass109nodes/127edges/18 committed docs/32 bibliographic sources at fab6cb6; exact artifact retained outside worktree.
- Managed secret/branch/metadata/date/doc hooks and whitespace checks passed. Foreign root files/SCI notes preserved. C4 design is active and being independently tightened before scoped implementation; it is not falsely reported as an executed evaluation.

## Not verified
No independent timestamp/execution witness, sealed cohort, answer-generation accuracy, calibrated abstention, universal entity coverage, predictive advantage, learned action policy, whole-step return on effort, deployment or scale promotion. Protocol semantics and historical bridge are supervised gates outside the adapter's opaque byte binding. Local Python source guards and process timeouts are trusted controls, not security isolation. No remote CI, push or browser claim. The graph remains a curated map; bibliographic metadata is not archived external source content.

## Findings
- [medium] [fixed] Local supervisor assertions could disappear under optimization; replaced every gate with explicit exceptions and independently checked optimized valid/invalid paths.
- [medium] [fixed] Local evidence checks omitted WAL changes and newly added blobs; compare live logical head/count plus a freshly enumerated physical inventory, with stable positive controls.
- [medium] [fixed] Local assessment derived static declarations from observed reports; populate all eleven input identities from the frozen protocol and reject each mismatching report before handoff.
- [medium] [fixed] Local assessment timeout could skip caller evidence; preserve partial stdout/stderr, timeout status and elapsed time before refusing continuation and inspecting authoritative state.
- [medium] [fixed] Two new graph relationships violated typed cites endpoints; changed exactly those links to existing depends_on and verified actual compilation without schema relaxation.
