---
task: retrieval-coverage
branch: worktree-retrieval-coverage
reviewed_patch_id: 3a84c755239d3818cc31ab3b26364e040f6ba562
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/c4_critic
reviewer_output_sha256: a9aea8dff159390c1248d67aa961ed1c9df89a0839196cb32f0e9fecbe18c115
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 6, low: 0 }
resolved: { fixed: 6, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 22, lines: 3146 }
---

## Conclusion
Ready to land: yes
The frozen cohort and executable preparation/evaluation path passed independent reviews and actual retained-evidence verification. Both raw runs reproduced, the sole complete-support failure remains visible, and the controller atomically selected its investigation without changing the baseline or raising budgets.

## Reviewer report
### Unguided code review: /root/c4_critic

No remaining actionable findings. Both prior findings are resolved. The run-key and capacity repairs also look sound.

Five focused Python 3.14 tests passed, covering query limits, result depth, run-key grammar, exact capture capacity, and concurrent capacity consumption. Example schemas, cohort/query hashes, and inventory agree. Source-span semantics were not rechecked against private evidence.

Reviewed SHA-256 hashes:

```text
improvement.py
aac2078c67f0e98d1b0dbdb8e0f8a9287d00e30078a25e2ca9cd9c0cc85b32d1

retrieval_assessment.py
17056efa7f915c25630e236f388af9648666258e06090b19e1d883bcde05d3e5

retrieval_coverage.py
6c3260f30c3ca354d3af3656b4fe67cb0ca6de5810feaf1c25ed4a901bb5990a

retrieval_evaluation.py
c926953d4d5b69ed0b3e6e3b92bd4f9d20c4724ffe681db18ee441f736b6560b

control-fresh-coverage.json
f85a843b068d59f2eca09697dffb1ae64fcd988a142cda46c91e941520e39855

coverage-protocol.json
301eb07f60a66b987364e534565d20b5334071ac77e00d3dc59456523269c3e1
```

No edits or actual research execution.

### Guided code and supervisor review: /root/c4_safety

Accepted: all prior findings are closed; no new actionable findings.

- Eight focused readiness/capacity tests passed in 10.820 seconds.
- Seven mocked supervisor failure controls passed with its hash verified before and after.
- Caps remain unchanged; historical replay adds nothing. Evaluator identity remains separate from candidate/helper code.
- Capacity preflight covers both input-capture phases; report sizes retain their completion checks.

Verified SHA-256:

- Helper: `6c3260f30c3ca354d3af3656b4fe67cb0ca6de5810feaf1c25ed4a901bb5990a`
- Adapter: `17056efa7f915c25630e236f388af9648666258e06090b19e1d883bcde05d3e5`
- Supervisor: `15cbb38aa6ebac6cf24cb36eea7f1d17451e78b7bd2ed70fd8cd92b24e7f7cdd`

No source edits, private-store execution, or full-suite duplication.

### Actual evidence review: /root/c4_safety

Actual C4 audit passed with no discrepancies.

- C3 remains physically unchanged: **112 events**, head `fa7c829132b559726f50db2a7c122d02ca152c95b03945c79739678a92f52f61`.
- C4 preserves that prefix exactly: **152 events**, head `292648c3d0c61932d90b44e48c42f1e16b3e689d5664d79f5b48231b3d1557df`.
- Verified order: freeze **118** → start **119** → terminal **135** → start **136** → terminal **152**.
- Both retained runs reproduce exactly. Complete support is **5/6** at cutoffs 1, 3, and 5; unsupported hits **6/6**. Sole support gap: `coverage-05-supported`.
- Preparation contains no quality claim. Its measurement identity matches evaluation.
- Controller: **332 events**, no unfinished assessments; next action is `inspect_fresh_support_failures`.
- Final adapter artifacts: preparation **43 / 1,426,756 bytes**; evaluation **46 / 1,746,014 bytes**. All unchanged capture limits pass.
- Assessments took **8.678s / 8.873s** against 30s; dispatches **8.966s / 9.262s** against 60s. Recorded model calls and external spend are zero.

Gate, source/artifact hashes, saved reports, dispatch outputs, and authoritative transitions agree. Only read-only ledger access and rescoring occurred; no search/index execution or store changes.

### Final publication review: /root/c4_critic

Approved for landing. No actionable findings.

- Scores, identities, event ordering, costs, and controller handoff match the saved C4 summary and receipts.
- Public cohort/protocol files exactly match the frozen originals.
- Publication preserves the C4 cutoff; later C5 work is not presented as a C4 result.
- No private source text or absolute private paths appear in the new public records.
- Graph node types, claim statuses, and relationships follow the existing schema.
- Production source hashes remain unchanged from my accepted review.

File-only review; no ledger access, tests, retrieval execution, or edits.

## Checks run, and what each covered
- Final engine suite: 544 tests passed in 378.622 seconds under Python 3.14.8 / SQLite 3.53.4. Frozen production hashes remained unchanged. Initial 536 tests passed before readiness repairs; the final run supersedes that check.
- Final changed CI smoke passed using owned synthetic evidence, fresh subprocesses, preparation, evaluation and persistent continuation. Final builder controls covered 19 preparation and 39 compatibility tests; independent reviewers exercised five and eight focused cases plus seven mocked supervisor failures.
- Both actual retrieval runs reproduce the ordered results and raw projection. Complete support is 5/6 at cutoffs 1,3,5; complete source sets 6/6; unsupported any-hit 6/6; empty, failed and missing queries zero. Six matched pairs cover four sources; there are two alternative-bundle cases and one joint case, with no multi-source case.
- Actual C4 ledger verifies 152 events and exact inherited C3 prefix. Freeze118 precedes start119/terminal135 and start136/terminal152. Original C3 bytes and modification times remain unchanged. Independent rescoring agreed with saved reports without retrieval/index execution.
- Preparation and evaluation share measurement b1e5cb28327a490fa2454f3fcb446c906ef43de6c3b2456de069669ecfc0556e. The preparation report contains no quality score. Authoritative controller status verifies 332 events,11 completed assessments,no unfinished claims, and successor coverage-evaluation-20261126:next selecting inspect_fresh_support_failures.
- All execution/capture budgets remained unchanged. Two retrieval callers total0.394085958seconds. Preparation/evaluation assessments took8.677852959/8.872798959seconds; dispatches8.966236208/9.261825667seconds. Fixed program model calls and external spend zero; total builder/reviewer cost unmeasured.
- Final local site build passed with64 content records versus43 original and no removed slugs. Exact generated artifact archived/restored. Existing build skips TypeScript/lint; no TypeScript changed. No browser/rendered verification.
- Knowledge compilation at committed73c1830 passed114nodes/134edges/20documents/32bibliographic sources. Graph payload ff28000787df82c46e3501050b8d1670673603f9de59f558de1dcb00ca0a7352 retained outside worktree.
- Public cohort/protocol match frozen originals. Public records contain authored questions, references, metrics and hashes; private source excerpts remain local. Final publication review preserves the C4 cutoff. C5 read-only diagnosis has since been independently checked; its executable handoff is next work, not a C4 result.
- Managed commit hooks and whitespace checks passed. Foreign root files and SCI's canonical mathematics note remain untouched.

## Not verified
No sealed holdout, calibrated abstention, answer-generation accuracy, cross-cohort improvement, causal ranking mechanism, universal entity coverage, independent timestamp/execution witness, whole-step return on effort, deployment or scale promotion. Local source guards are not security isolation. Retrieval of text for unsupported questions is not an answer hallucination measurement. Historical preparation replay checks its original prefix; future unrelated growth is not reserved. No remote CI, push or browser claim.

## Findings
- [medium] [fixed] Preparation could report readiness below the evaluator's required result depth; reject top_k below five before captures and test supported depths.
- [medium] [fixed] Preparation accepted a65-term query rejected by the fixed runner; validate the same compiler and preserve the64-term positive boundary.
- [medium] [fixed] Preparation accepted run keys outside the runner grammar; apply its bounded exact grammar before freezes and test valid limits.
- [medium] [fixed] Preparation could consume capture capacity needed for the two future runs; bounded preflight covers inputs and future events under lock, with exact-capacity and race tests.
- [medium] [fixed] Supervisor failures could skip postflight evidence; preserve timeout/nonzero/OS-error callers and always inspect authoritative status and partial run inventory.
- [medium] [fixed] Curated joint-support gold omitted a sufficient alternative; add the independently checked three-span bundle before freezing or retrieval and retain earlier drafts.
