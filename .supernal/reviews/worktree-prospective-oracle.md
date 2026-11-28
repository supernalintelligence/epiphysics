---
task: prospective-independent-oracle
branch: worktree-prospective-oracle
reviewed_patch_id: 8e486eb75882d6559d18be7d344bda30857a8880
reviewer_model: "Codex collaborator; model identity not separately recorded"
reviewer_agent_id: /root/prospective_oracle_builder/oracle_critic
reviewer_output_sha256: c513ea05cee6a4dc0caba95743b78230e453e234c837863d1f7785dae47c3dd6
author_session_id: ""
verdict: fixed
findings: {critical: 0, high: 0, medium: 1, low: 0}
resolved: {fixed: 1, skipped: 0}
skip_class: ""
skip_reason: ""
size: {files: 7, lines: 1382}
---

## Conclusion
Ready to land: yes
The independently authored raw-source query oracle passed scoped review after the known-ineligible-prior ordering defect was repaired. Its explicit support convention was fixed before oracle execution or candidate comparison; no prior study, candidate or scoring key was changed.

## Checks run
The repaired builder suite passed 35 tests across 180 retained invented cases. All 47 independent recheck controls passed: 35 unchanged adjudicable original controls plus 12 adjacent cases. Original product and test-harness failures remain retained, including the superseded depth assumptions. Cumulative builder test-process time was 3.030424 seconds and cumulative independent test-process time 0.442366 seconds under their respective 180/90-second caps. The measured runtime was Anaconda Python 3.12.9 with integer guard 4300; nested timings are not added. Root read the initial and closure reports, inspected the actual release-validation order and verified all eleven frozen source/contract/dependency pins. The exact reviewed diff remained unchanged after incorporating separate nonoverlapping theory commits already on ian-dev. Git whitespace and eight configured precommit checks passed. Source commit: 1bade0b03fa0d99b55206ae5cac56dfa5b4cc42c. The source and tests use the public contract and stdlib, with no candidate/normalizer implementation or expected-output imports; literal raw expectations were frozen before execution.

## Not verified
No candidate comparison, preservation score, shared runtime connection, independently authenticated collection, source selection, registration, forecast issuance, delivery quality, future outcome resolution or live pilot was performed. No original C12 replay, broad project suite, frontend build, browser check, push, remote CI or deployment occurred. New documents remain drafts. Supplied receipts and clocks remain caller claims. Review and explicit data-flow boundaries do not prove hostile-host isolation. Other five entity families, predictive advantage, total agent effort/cost and CPU/peak memory remain unmeasured. Study-program network/model/spend were zero; a private initial reviewer metadata helper attempted a subprocess that its audit hook blocked, preserved separately as a harness failure.

## Findings
- [medium] [fixed] Operational header decoding failure discarded an already established prior-body exclusion and falsely made snapshot membership unknown. Independent body/clock/window exclusions now take precedence, while potentially eligible unreadable history remains unavailable.

## Reviewer report
# Independent R1 repair recheck

Reviewer: `/root/prospective_oracle_builder/oracle_critic`. **R1 is verified fixed in the repaired freeze. No new actionable finding was established in this scoped recheck.** Source remained read-only; the root supervisor retains the integration decision. This closes the initial known-ineligible-prior ordering finding, not any candidate-conformance or study gate.

## Reviewed identity and scope

- Worktree: `/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/prospective-oracle`.
- Base: `909ae65daca4a4507bd10d07b8c29e520952e42f`.
- Repair manifest SHA256: `5884c0488e7c22706c394b827ab26bcedba9a29a2f35c6e6bf8cc42d540b7dae`.
- Repaired oracle SHA256: `df7d2d07cb394ce311bf1a490f9fb8de6535a60b6004a8b3dced0b1396c0dd9e`.
- Full diff SHA256: `cd65c0e43f22f8e371e830289c9786f33b736d0ffc52710bd2398d2672bc9a28`.
- Repair-only diff SHA256: `032e256f0716f5611a9998faf989cbe74277709092f39ee67efb07e80ebe470b`.

The narrow source change establishes body, clock and request-window exclusions before decoding headers. Header rejection still precedes body JSON parsing. The repair-only source/test/document diff was inspected, including its recorded limits and still-unfinished comparison/runtime gates. No builder fixture helper was imported or copied. Candidate normalizer/views/helpers/tests/outputs, store utilities and prior-study evidence were not accessed. No source retrieval, candidate comparison or study execution occurred.

## Results

All **47 controls passed** in the first recheck process: the unchanged 35 adjudicable original controls, including R1 and its paired uncertainty control, plus 12 independently chosen neighboring cases. The earlier mistaken fixed-depth expectation was not rerun and remains unchanged in the initial review with its original adjudication.

The exact original R1 raw input now returns `status: available`, `seen_id_set: [7,9]`, snapshot members `["O","Q"]`, and the unchanged opening map. P is `excluded` with `reasons: ["body_incomplete"]`. Its numeric header inability no longer erases the known exclusion. The original potentially eligible prior with the same bound numeric header still returns `unavailable`, null seen IDs, and P `unavailable` with `runtime_decimal_unavailable`. Those original literal expectations were neither edited nor regenerated from repaired output.

Neighbor controls cover inclusive request-start, body-completion-duration and retention/cutoff boundaries versus one microsecond beyond each boundary. At the exact otherwise eligible boundaries, unreadable prior headers still leave membership unknown; just beyond the boundaries, conclusive exclusions survive. Additional controls cover body hash rejection, missing body, unsupported time basis, epoch mismatch, header-hash rejection before a runtime-unreadable body, and an incomplete opening with runtime-unreadable headers. The invalid opening still makes the snapshot unavailable and retains `body_incomplete` rather than becoming usable.

All returned bytes were checked for canonical serialization and inputs for immutability. Raw outputs, exceptions and per-control results are under `run-01/results/`. `run-01/first-failures.json` is an empty list. No new control or harness failure occurred.

## Timing, runtime and preservation

The recheck outer test-process wall duration was **0.155283167026937 seconds**. Nested total process-body duration was 0.1158264169935137 seconds; nested oracle-call plus output duration was 0.018769337853882462 seconds. These nested intervals are included in the outer interval and are not added.

Including the initial review's 0.2870827500009909 seconds, cumulative reviewer test-process wall is **0.44236591702792794 seconds of the 90-second cap**. Recheck authoring and inspection time are outside that test-process measurement. Actual runtime remained `/Users/ianderrington/miniconda3/bin/python`, Anaconda Python 3.12.9, Clang 14.0.6, Darwin 25.5.0 arm64, integer digit setting 4,300 and Python recursion setting 1,000; no limits changed. All frozen runtime file hashes matched. Program network calls, model calls and spend were zero. No network or nested-subprocess audit event was attempted during recheck. Total agent effort/cost remain null; CPU and peak memory were not measured.

The 440 initially pinned review files were verified unchanged before and after recheck. Every copied original control file matched its initial bytes, and all repair-frozen worktree files matched their pins at opening and closing verification. The initial source freeze, failed outputs, reviewer harness failure, mistaken depth expectation and original report remain separate historical artifacts.

`controls-before-execution-pins.json` binds all recheck raw inputs and literal expectations before execution. `opening-verification.json` and `closing-verification.json` preserve the source/runtime/original-evidence comparisons. `run-01/outer-receipt.json`, `nested-receipt.json`, stdout, stderr, raw outputs and exact exceptions retain execution evidence. `artifact-pins.json` hashes this closure report and all recheck files. All new artifacts are private under `.supernal-local/prospective-oracle-v1/recheck-v1/`.

This result establishes the scoped R1 repair under the pinned runtime and invented inputs. Independent collection, selection, timing assurance, candidate comparisons, delivery quality, outcome resolution and launch review remain outside this recheck.
