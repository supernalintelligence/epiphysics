---
task: retrieval-controller
branch: worktree-retrieval-controller
reviewed_patch_id: 5602afe43e6eccc079642aac3c33326e70115ce4
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/c2_safety
reviewer_output_sha256: f50f6a50a8ab7343cbb7f781f1f61bef4901a2e9d593637d335b2e701f533c68
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 3, low: 0 }
resolved: { fixed: 3, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 21, lines: 1896 }
---

## Conclusion
Ready to land: yes
Both independent reviewers verified all accepted repairs. The final full suite, actual retained-evidence handoff, changed CI and site build passed; the original evidence archive remained unchanged.

## Reviewer report
### Unguided full review: /root/c2_critic

No remaining actionable findings.

Reviewed `git diff HEAD`, staged changes and new files against `677319398e1b855c310493a158f70cd0ec01c22a` in `/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/retrieval-controller`. Coverage included controller selection/comparison, evidence capture and transport, read-only ledger behavior, retrieval/scorer dependencies, tests, CI, example policies, documentation and registry changes.

One P2 finding was fixed during review: `improvement.py:86` previously omitted SQLite exceptions, so corrupt evidence escaped before recording a diagnosis. Independent reproduction now confirms a durable failed assessment, queued diagnosis, unchanged evidence files, valid improvement ledger and exact replay without additional events.

Six focused tests passed, covering live WAL visibility, mutation refusal, valid differing results, comparison across fresh execution IDs, FIFO refusal and corrupt-database preservation. `git diff --check` passed. I made no edits and did not run the full suite or assess private production evidence.

Final reviewed production-source SHA-256 identities:

- `engine/epiphysics/improvement.py`: `97f5050c1bfd50ca33aa0a422786fe3cc87349a16ce267e909e340812bd893bd`
- `engine/epiphysics/retrieval_assessment.py`: `8fd5cb8f61bb30de5129ab29ec49047ad6c5fe750f159c48e1ac02e57f244e71`
- `engine/epiphysics/store.py`: `fda268dfa48beb28ee34a3bef714979f85e2e46db28bd7dc4cb1bc0395d6b0d1`

### Unguided final delta: /root/c2_critic

No remaining actionable findings in the final narrow delta.

Verified bounded controller/evaluator source reads and durable handling of rejected symlink-loop paths. Two focused source-bound tests passed. An independent dispatch using a real ancestor loop inside `evidence_store` recorded diagnosis, preserved source bytes, left no unfinished claim and retained a valid improvement ledger. `git diff --check` passed.

Reviewed final SHA-256 identities:

- `engine/epiphysics/improvement.py`: `ff214ae3850c70b176e5342f315ff6a2deb0342512f25f76f43ea9ec8c325551`
- `engine/epiphysics/retrieval_evaluation.py`: `fc521539c94c6e4347e00d1f55ab9960236c9c65e261bb211da952ac15cb79fc`

This supplements the earlier full-diff review against `677319398e1b855c310493a158f70cd0ec01c22a`. No edits made; full suite and private evidence assessment were outside this verification.

### Guided final verification: /root/c2_safety

Independent repair verification: **both P2 findings are resolved; no remaining actionable findings in the reviewed repair delta.**

- Repeated the original 32 MB evaluator-source reproduction through actual study preparation. It now rejects the changed source **without opening it**; peak measured allocation was 1,856,321 bytes. Evaluator and controller identity checks use bounded expected-length reads.
- Repeated the original self-referential study symlink reproduction. It now produces **one started event, one failed event, zero completed events**, and queues diagnosis.
- **Six focused regression tests passed**, including positive bounded reads, all pinned controller sources, self/ancestor symlinks through assessment and real dispatch, and embedded evidence-locator resolution failure. These controls reach their intended guards.

Review was read-only, used owned temporary evidence, and did not run the full suite or access original persistent stores.

Base commit: `677319398e1b855c310493a158f70cd0ec01c22a`.

Verified SHA-256 hashes:

```text
ff214ae3850c70b176e5342f315ff6a2deb0342512f25f76f43ea9ec8c325551  engine/epiphysics/improvement.py
fc521539c94c6e4347e00d1f55ab9960236c9c65e261bb211da952ac15cb79fc  engine/epiphysics/retrieval_evaluation.py
8fd5cb8f61bb30de5129ab29ec49047ad6c5fe750f159c48e1ac02e57f244e71  engine/epiphysics/retrieval_assessment.py
1be519adc085d7dbd5615c5066ca5e275be22240c484f6395b98ac0fba8225c3  engine/tests/test_improvement.py
5b6a7f5e80d0f8d1120cfe095847dbf38bafd47fb148ab2589790f1872ae8a7a  engine/tests/test_retrieval_assessment.py
7592ac81508477a28fc4520cd2ad28818ece7bfe934bfcfa2ad742e6111b04ee  engine/tests/test_retrieval_improvement.py
```

## Checks run, and what each covered
- Initial full engine suite: 411 tests passed in 266.276 seconds. Final full suite: 417 passed in 342.801 seconds, after six additional source-bound and path-loop regression controls; /tmp/epiphysics-retrieval-controller-tests-final.log.
- Read-only ledger: 109 focused store/capture/atomic/retrieval/evaluator/CLI tests, including nine new read-only cases. Adapter: sixteen initial focused cases, plus the later evaluator-source guard. Controller: actual two-run fixtures, input capture/transport, full base checks and priority preservation, real dispatch, replay, null targets, distinct fresh execution identity comparisons and durable failure controls.
- Root pre-review inspection tightened SQL field-size preflight, aggregate selected-source cap and adapter source-read bound. Controller fallback refuses FIFO/nonregular reads, and its assessment identity binds full inputs separately from the adapter report. Independent review then resolved the three findings below.
- Both reviewers reran their repaired paths. The 32 MB evaluator replacement is rejected before open; the guided reproduction measured peak allocation of 1,856,321 bytes. Actual self/ancestor-loop dispatches preserve source bytes and record diagnosis, with no unfinished claims or false quality reports.
- Final changed CI program passed: two fresh searches on owned synthetic source bytes, separate scoring, then a real controller child using captured input and a coverage-evaluation successor. No private third-party snapshots enter CI.
- Site build passed before and after completed-run documentation. Final generated content: 43 to 60 entries, no removed slugs; exact artifact archived and generated file restored. Existing build skips TypeScript/lint; this patch changes no TypeScript.
- Real read-only adapter preflight reproduced original C1 counts and quality in 0.209 seconds using 23 artifacts / 558,887 bytes; original DB/blob bytes and modification times unchanged.
- Reviewed real dispatch retrieval-assessment-20261126, receipt 2f8700b4c7af42049002e527b640bd43, passed in 12.705 seconds (12.906 outer caller). It retained original source recall@1 8/8, gold-span recall@1 3/8 and @5 7/8, unsupported retrieval 4/4; all twelve queries counted. No new search executed.
- Persistent improvement store verified 129 events, eight completed assessments, no unfinished claims; head db227fa3b727a3c8d186907d539871079648fd32e6783983b785398954b0ae4b. Completion atomically selected prepare_retrieval_representation_comparison with observed 0.875 and null target. Prior actual retrieval outcome remains unmeasured, not claimed improvement. Original source DB/blob bytes and mtimes unchanged.
- Research catalog validates at 100 nodes, 116 edges, 15 committed documents and 31 bibliographic sources against the C1 base. It adds the committed baseline record and qualified reproduction/support-gap claims, not inferred scientific truth.
- Whitespace, secret/branch/metadata/date/document hooks passed. Foreign root files and SCI-owned research notes preserved. SCI explicitly confirmed no active package work for a separate isolated publication-audit repair; it is not part of this patch.

## Not verified
- No independent timestamp/execution witness, sealed holdout, generalized representation advantage, generated-answer accuracy, calibrated abstention, forecasting or business/market lift is established.
- Retrieval receipt validation rescored two historical executions; it did not rerun search. Current validator identity differs from C1; candidate/indexing and measurement code are still coupled and therefore conservatively incomparable after coupled changes.
- Runtime/process limits are trusted local controls, not OS memory isolation. Input retention bounds are not a total process RSS limit. Whole builder/reviewer effort remains unmeasured; zero calls/spend describe the fixed programs only.
- No remote CI, rendered browser verification, push, promotion or deployment is claimed. The separate moderate-audit publication block remains under repair in another owned worktree.
- The C3 comparator is designed but not implemented or executed by this patch. Its next task must preserve source/gold/scoring contracts and then obtain fresh coverage evidence rather than tune indefinitely against visible development cases.

## Findings
- [medium] [fixed] Catch SQLite preparation errors so malformed evidence produces a durable failed assessment and diagnosis; retain the source bytes and avoid base-only success.
- [medium] [fixed] Bound evaluator and controller loaded-source validation to expected regular-file sizes and expected length plus one reads; the actual adapter path rejects a 32 MB changed evaluator before opening it.
- [medium] [fixed] Preserve rejected study locators lexically without resolving symlinks; self/ancestor request and evidence-path loops now become durable diagnoses through assess and dispatch.
