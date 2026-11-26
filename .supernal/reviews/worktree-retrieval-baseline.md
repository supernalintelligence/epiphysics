---
task: retrieval-baseline
branch: worktree-retrieval-baseline
reviewed_patch_id: 82d05ba7a1c435740b51c14efee36648feeaedfb
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/retrieval_safety
reviewer_output_sha256: 8994cdc6454c6a1b38e032e3f488b4ad9ae542e1731c932ac15ae7a3f7b9cc3b
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 1, low: 0 }
resolved: { fixed: 1, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 21, lines: 2688 }
---

## Conclusion
Ready to land: yes
Both independent reviewers verified the shared capture-bound repair; no actionable findings remain. The full suite, actual frozen-source reproduction and separate scoring passed, with quality limits recorded rather than treated as implementation failure.

## Reviewer report
### Unguided review: /root/retrieval_critic

No actionable correctness findings.

Reviewed `git diff HEAD`, the empty staged diff, and all nine untracked engine files against `a0e74cb12cbff0a3344f705c28fe18b87db98d19`. Also checked the corrected CLI corruption test.

Consumer map: CLI calls freeze/run/evaluate; evaluator validates completed receipts through `get_retrieval_run`; CI exercises fresh retrieval and separate scoring. The improvement controller remains intentionally unintegrated pending C2.

An independent synthetic check passed for fresh-run reproducibility, UTF-8 passage provenance, selected-source isolation, full-span recall, unsupported retrieval rate, empty-query handling, read-only evaluation, and ledger validity. No files edited; full suite left to root. Archived source content and real cohort judgments were outside this review.

Reviewed SHA-256 identities:

- Retriever: `4cf1766e007d47ea367b4dee7eb811ded9f7fb4c3fac3ea5ee68152da8fa1613`
- Evaluator: `89557682e7662296cb67521d1646348c3c1980aa85af19c2d634e77cc7702fcb`

### Unguided final delta: /root/retrieval_critic

The reported resource P2 is fixed. No unresolved actionable correctness findings.

Reviewed the frozen `store.py` delta and all ten new capture tests. Existing blobs now require a regular, non-symlink file and read at most `len(content) + 1` bytes before checking length/hash. Corruption remains untouched and prevents an observation append.

Independent retrieval-path reproduction passed: a 20 MB sparse config blob caused exactly one 236-byte read, preserved inode/size/modification time, appended no metadata observation, and produced a durable rejection.

Final store SHA-256: `bd1d79659c7ca97c987ed0cc8306d97b985928a42dd414f8795098a454de9208`.

The earlier retrieval/evaluator review remains applicable. No edits made; full-suite verification remains with root.

### Guided final verification: /root/retrieval_safety

Independent verification passed. **P2 is resolved; no remaining actionable findings.**

The original 20 MB corrupt metadata probe now reads exactly **236 bytes** for the expected 235-byte configuration, performs no unbounded read, preserves the file, and records a rejection that replays identically.

All **96 targeted tests passed**; `git diff --check` passed. The change affects existing-blob validation only, with no API, record-schema, or global size-limit changes.

Verified store SHA-256: `bd1d79659c7ca97c987ed0cc8306d97b985928a42dd414f8795098a454de9208`.

## Checks run, and what each covered
- Final full engine suite: 373 tests passed in 235.442 seconds; /tmp/epiphysics-retrieval-tests-final.log. Independent guided pass: 96 capture/retrieval/evaluator/CLI/atomic tests in 3.358 seconds.
- Retriever: 26 focused tests; evaluator: 26; CLI: 3. An initial 54/55 focused run had one fixture expectation failure: deliberately corrupted source bytes correctly failed whole-ledger verification. Test now checks failure, restores its own source, verifies the chain and all CLI tests pass.
- Ten new capture regressions and four existing reuse/group tests passed. Both reviewers reran the original 20 MB metadata reproduction and measured a single 236-byte read, preserved corruption and durable rejection/replay.
- Actual candidate tests cover pre-index eligibility and score isolation, UTF-8 spans, literal query syntax, deterministic ties, bounds, actual FTS errors/timeouts, claimed failures, concurrency, completion mutation and historical replay. Evaluator covers full interval union, macro means, complete denominators/nulls, selected-source gold, exact query matching and source/code/reload/stale-bytecode provenance.
- New CI step passed locally after final store repair: two fresh indexes on owned synthetic bytes, source-span resolution and separate evaluator. Production site build passed; /tmp/epiphysics-retrieval-build.log. Existing build skips TypeScript/lint, no TypeScript changed. Generated index 43 to 59 entries, no removed slugs; archived and restored.
- Independent cohort review verified four complete source blobs and all twelve gold spans/context. One GA-category wording clarification occurred before any baseline output; final cohort file hash72068c3b370deda3f1158116229f826f58e692b99361b975ae6bb68ecac357fd.
- Real study control-development-v1 retained pre-run cohort/evaluator/review/plan/runner artifacts, then two separate CLI executions over four sources (144,898 bytes; 82 passages). Both yielded e2b906b69f1dd285fb4968247b624034c542eb045a76a3d845bac6dcf6b1acf4. Source recall@1 8/8, gold-span recall@1 3/8 and@5 7/8, unsupported-query retrieval4/4; all twelve queries remain counted. Caller times0.303/0.142 seconds include locked revalidation/commit; internal elapsed scope excludes it explicitly.
- Post-hoc independent inspection verified all25 relevant hit spans: OTS top-five miss has no equivalent support; unsupported outputs contain related text only. Gold, queries and scores unchanged. Proposed HTML text-node comparator remains unexecuted.
- Evidence store verified39events at experiment completion and40 after retaining the separate diagnostic; current head aaebea818170f5ee7cd3c5a3c4a87923b652378c2bac0737bd79318e1636f519. Improvement store remains at seven assessments with the existing baseline action pending C2.
- Research catalog compiled97nodes,113edges,14committed documents and31bibliographic sources. Whitespace and pre-commit secret/branch/metadata/date/document checks passed.

## Not verified
- No answer generation, calibrated abstention, prediction, graph advantage, market/business lift, semantic truth or final-cohort generalization is established by this four-document development corpus.
- No external time/execution witness, whole builder/reviewer cost, deployment, remote CI or scale promotion is claimed. Programs make no model calls or payments; agent effort is separate.
- Source cutoff differs from later experiment code/query artifacts. This is retrospective development retrieval, not historical predictor availability.
- Runtime identity is recorded; cross-runtime equality is not guaranteed. Exact replay is historical metadata, not another search or a present-availability certificate.
- Existing candidate/search, passaging and validation code/config identities remain coupled. C2 must import actual evidence; C3 must establish the measurement/candidate boundary before comparable candidate changes. Neither is completed by this patch.
- Raw third-party source bytes and local caller receipts remain local. Existing audit/promotion restrictions and unrelated shared files were preserved.

## Findings
- [medium] [fixed] Bound existing metadata/source blob reuse in shared Ledger.capture to expected content length plus one byte, reject nonregular/symlink files before reading, verify length/hash, preserve corruption and refuse observation creation; cover the real retrieval path and ordinary reuse.
