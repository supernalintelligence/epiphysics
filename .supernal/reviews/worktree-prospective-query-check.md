---
task: prospective-query-content-check
branch: worktree-prospective-query-check
reviewed_patch_id: 96a6ce7c971a90b813e63a1a1e81df8834ac9345
reviewer_model: "Codex collaborator; model identity not separately recorded"
reviewer_agent_id: /root/prospective_query_checker/query_check_critic
reviewer_output_sha256: 95300fdbc1b8fd45c2c901672124a1f11cea61e53bf0ff6d2b1350218f485d6a
author_session_id: ""
verdict: fixed
findings: {critical: 0, high: 0, medium: 1, low: 0}
resolved: {fixed: 1, skipped: 0}
skip_class: ""
skip_reason: ""
size: {files: 7, lines: 757}
---

## Conclusion
Ready to land: yes
The pure answer-content checker passed independent review after its Decimal operational-exception boundary was repaired. The first invented integration comparison is retained as evidence of candidate support gaps, not changed to make the components agree.

## Checks run
All 22 repaired checker tests passed, including frozen literal numeric-boundary cases on both public inputs. The independent critic rechecked original failure probes, a separate 54-call boundary matrix and the 22-test suite; all passed. All 193 repaired source/evidence pins were independently verified before and after recheck; root verified the 66 current source/dependency/review pins and exact owned/full diffs. Root also inspected retained decoded values/support and recomputed four saved-encoding hashes without executing the first comparison again. That original comparison recovered all six release and ten obligation values per form, with only 5/6 and 4/10 supported-content matches respectively. Missing question-contract references are preserved for a separate candidate repair. Source commit: fc5b4f163182022cf40c0a4a33261fcd9c09826a. Git whitespace and eight configured precommit checks passed. Builder test/comparison process time totaled 0.870791 seconds; reviewer check-process time totaled 1.417568 seconds, with nested durations not added. Tests used the pinned Anaconda Python 3.12.9 runtime without changing numeric globals.

## Not verified
The first comparison was not rerun against the repaired checker; original results retain their original implementation identity. No candidate, oracle or support-policy edit occurred. Two invented baseline fixtures and a shared query implementation do not establish prediction, generalization, independent form replications or business value. The checker verifies content, not runtime isolation, full preservation, forecast eligibility, registration, collection, source truth or outcomes. No original C12 replay, prospective study launch, whole-project suite, frontend build, browser check, push, remote CI or deployment occurred. Other five families, CPU/memory and total agent effort/cost remain unmeasured. Program network/model/spend was zero. Original numeric probes and reviewer invocation-path failure remain retained.

## Findings
- [medium] [fixed] Extreme-exponent JSON zero leaked Decimal operational exceptions past both public boundaries; the numeric parser now yields candidate numeric-limit diagnostics or oracle CheckerRefusal without mislabeling valid JSON syntax.

## Reviewer report
Independent numeric-repair recheck — P2 closed

Reviewer: /root/prospective_query_checker/query_check_critic
Worktree: /Users/ianderrington/git/ianderrington/epiphysics/.worktrees/prospective-query-check
Base: 82f0e993770ecbaf4201c6ddae193b64bf3d20cb
Repair freeze: /Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/prospective-query-check-v1/repair-freeze-v1

Exact repaired pins
pins.json SHA256: f95f56fe855e32b0be30c13b90039477d30b0c4d261c43c9b1d92c370670fbad
repair.diff SHA256: 76d0268c3c6cecc19ac54495fa84debeee4bf5898a80281def387a693fb70bf0
owned.diff SHA256: 9b2e83660b750bd05c2374c51b64b10573b9e1742a8a290348ef3eb78045ddd2
engine/epiphysics/prospective_query_check.py: 17214 bytes; SHA256 8b19f8e80a3334b631e3437af47d2effddf11ed68634dc6b6433e9977eb9a9c9
engine/tests/test_prospective_query_check.py: 21034 bytes; SHA256 927f1da8a67fbd7228e96d22ffda96b10eeb8ca2b93ad700309c33ea93050fab
All 66 source/dependency/review pins and 127 evidence pins (193 entries) verified before and after this recheck. The exact current five-file diff against the base equals the pinned owned.diff. Original failure evidence and first integration outputs remain pinned and unchanged.

Closure
The original P2 is fixed at engine/epiphysics/prospective_query_check.py lines 59–65: Decimal conversion/comparison exceptions are translated to ValueError('numeric_limit') and then follow the existing public error boundaries. Re-executing the original independent probe script against this repaired source produced unparseable candidate diagnostics and CheckerRefusal('oracle_or_plan_invalid: numeric_limit') for the positive-exponent zero, negative-exponent zero and decimal-zero cases that previously leaked decimal.InvalidOperation. The adjacent extreme nonzero case continued through the same intended numeric-limit path. No uncaught exception was observed.

A separate independent matrix used the critic's invented oracle/answer envelope and 27 literal tokens on both public input paths, 54 asserted calls. Eight numeric-limit cases cover extreme signed/decimal zero, extreme nonzero, overflow, underflow and overprecise finite decimals. Fifteen accepted cases cover integers, signed/decimal zero, zero with extreme-but-supported exponents, fractions and large/small finite nonzero values. These reached ordinary schema checks, preserved all six unaffected content matches on candidate input, and refused the deliberate extra oracle key by the ordinary schema error. Four malformed numeric tokens retained parsing failures. The original complete baseline, empty-opening and partially unknown-history controls still passed. The original script was reused unchanged; its prior failure stdout was not overwritten. The independent matrix also executes that script in-process to obtain only the critic-authored literal envelope; it imports no builder test fixtures or oracle/candidate implementation.

The repaired checker suite passed all 22 test methods. The narrow source delta and documentation were reviewed; no support-policy, scoring, declaration, candidate or oracle changes were introduced. No additional actionable finding was identified in this repaired scope. This closes the accepted numeric-exception P2 and does not expand the original review's assurance limits.

Checks and actual process time
- Before pins: 0.4039144580019638 seconds outer wall.
- Original independent probes against repaired source: 0.07225420902250335 seconds outer wall; 0.019296000013127923 seconds nested, not additive.
- Independent 54-call boundary matrix: 0.08200979104731232 seconds outer wall; 0.04600633302470669 seconds nested, not additive.
- All 22 checker test methods: 0.11236879200441763 seconds outer wall; unittest reported 0.016 seconds nested.
- After pins: 0.11236812500283122 seconds outer wall.
Recheck total: 0.7829153750790284 seconds. Original review total: 0.634653040964622 seconds. Cumulative reviewer check-process total: 1.4175684160436504 seconds of 90 seconds, leaving 88.58243158395635 seconds. No recheck failure occurred. Original first-failure receipts remain preserved.

Commands, cwd, stdout, stderr, exit status and process-wall receipts are under recheck-v1/critic-*. Checker execution used /Users/ianderrington/miniconda3/bin/python, Python 3.12.9, macOS 26.5.1 arm64, integer guard 4300 and recursion limit 1000. Nested timings overlap outer timings and are not summed. CPU, memory, agent effort and monetary cost remain unmeasured. Reading/review time is not check-process time.

Limits and preservation
This was the root-authorized read-only recheck of the frozen numeric repair. No reviewed source, root-owned file, prior report, fixture, declaration, policy or original receipt was modified; new scripts and receipts were confined to recheck-v1/. The original integration was not rerun, and remains attributed to its original checker source pin. No original study, live request, model/paid call, transaction, commit, landing or deployment occurred. The reported 5/6 release and 4/10 obligation support results are unchanged retained evidence, not a new integration result against the repaired checker. Runtime isolation, preservation and forecast eligibility remain outside this recheck.
