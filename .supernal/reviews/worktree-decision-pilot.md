---
task: decision-pilot
branch: worktree-decision-pilot
reviewed_patch_id: ff40435d873af1406afb677a6e38aed2bd9c347c
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/decision_final_critic
reviewer_output_sha256: 9d3941262c3fb866ea4941772a0636dffb3a905981e73f79ec140bc6e4cea382
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 3, low: 0 }
resolved: { fixed: 3, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 33, lines: 7767 }
---

## Conclusion
Ready to land: yes
The one exposed decision comparison is independently audited and its retained result is accepted in the authoritative queue. Three lifecycle/concurrency findings are fixed and reviewed. Final affected-path tests, the real handoff, site build and committed research-map compilation passed. Local landing preserves SCI's release ownership and unrelated checkout files.

## Checks run, and what each covered
- One registered development comparison: 12 cases across four arms, 48 attempts and 98 journal records; all six fixed checks passed. Independent audit and retained-result validation did not rerun the candidates.
- Complete broad regression: 708 tests in 1365.996 seconds, one failure and one error, both subsequently repaired. The failed run remains retained and is not relabeled green.
- Final affected-path validation: 125 tests passed in 85.474 seconds with all 75 source/test files unchanged. Coverage includes all decision modules, the complete coverage-preparation module, and real dispatcher/replay/atomic-completion/queue/selector controls. Independent reviewers judged this scope sufficient for the two narrow final repairs.
- Private-fork readiness passed without changing the authoritative queue. One actual retained-result acceptance then completed in 15.899 caller seconds, with all 88 frozen files unchanged. Ledger verifies 556 events, 14 completed assessments and no unfinished claim; successor is decision-development-20261126:next / prepare_fresh_decision_comparison.
- npm run build and homepage evidence guard passed. The retained 57-record content artifact includes the public protocol/result and excludes the draft run record; generated worktree output was restored.
- Committed catalog compilation from 5091d2b passed: 129 nodes, 156 edges, 27 documents and 32 bibliographic sources; graph payload hash 8519fcec4371eb2e8e7117227c69989c8f399ba066868c206631024e97bbcb1e.
- Managed feature commit passed all eight repository checks; git diff --check passed. SCI's actual acknowledgment confirms no overlapping engine work; its publication constraints remain in effect.

## Not verified
No second full broad suite after the two final narrow repairs; no browser inspection, remote CI execution of this patch, push or deployment. No final 24-case cohort, live settlement, learned selector, independent time/execution witness, general predictive advantage or increased authority. Program model calls/external spend are zero; agent/reviewer cost is separate and not fully measured.

## Findings
- [medium] [fixed] Generic assessment could consume a queued decision step without decision evidence; omission now refuses before claim for all decision actions.
- [medium] [fixed] New-request dispatcher manifest mismatch exited before durable failure; prior replay remains protected while new requests capture and record failure.
- [medium] [fixed] Coverage preflight mixed an earlier prefix boundary with newly committed captures; one read snapshot now covers the initial preflight, with locked final validation preserved.

## Reviewer report
# Independent C7 landing review

Reviewer: `/root/decision_final_critic`. Verdict: **fixed**. Findings: **3 medium, all fixed; 0 open; 0 skipped**. No critical, high, or low findings remain.

## Review scope and conclusion

Reviewed the complete owned diff in `/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/decision-pilot`, from `240763e52c49ddca0a121fc526f0f29da948320a` to `5091d2b304cd4b7c36c90458b44125e499f33961`: **33 files, 7,727 insertions and 40 deletions (7,767 changed lines)**. Scope includes the five decision modules, controller integration, narrow legacy coverage-freeze repair, six decision test modules and affected legacy tests, owned examples/contracts/results, public protocol/result and homepage data, internal run record, metrics/plans, TODO, DAILY_LOOP, and research registry. Generated `public/content-data.json` was restored and is not in this patch.

The reviewed `git diff 240763e HEAD --binary` SHA-256 is `203e1d1bad814cc72b92f1b5552fcea02487960e7f362e1e94395fb65018290d`, identical to the working diff audited before the author committed it. The independently computed stable Git patch ID is `57409b8cf033e3718f9e211944932d820b705c02`; this is distinct from the managed landing tool's own review identity. Exact file hashes are listed below. This report excludes later source changes and the subsequent review-record commit.

No material correctness, evidence-integrity, lifecycle, or public-claim finding remains. The bounded development comparison and retained-evidence acceptance are ready for local landing under the repository's normal checks. This does not authorize a push, deployment, live effect, or fresh-cohort execution. The supported result is limited synthetic development evidence, not general superiority or hostile same-user isolation.

## Findings

- **[medium] [fixed] Missing decision evidence could consume a decision queue step.** Generic assessment could mark decision preparation complete and fall back to retrieval-baseline work without a checked decision study. The controller now rejects omission before claiming preparation, repair, or fresh-comparison steps and preserves the queue. Isolated temporary-ledger controls cover all three actions, valid atomic completion/replay, and incorrect origin. The source and locked-origin checks remain in the final controller.
- **[medium] [fixed] New-request dispatcher mismatch lost its durable failure.** The early expected-request hash check originally exited before a new claim, leaving `assessment_status: not_confirmed`. It now protects prior completed-request replay only; new requests retain the post-capture check inside the durable failure path. The actual subprocess mismatch test and completed decision replay control pass with repaired source.
- **[medium] [fixed] Coverage-freeze preflight could combine two ledger versions.** A concurrent creator could commit deterministic captures after another creator selected its prefix boundary, causing a false capture-mismatch error. The initial preflight now shares one existing read transaction, closed before writes. Append-lock validation remains. A deterministic two-connection test forces the original interleaving and requires one identical freeze, three captures, and a valid ledger; the original concurrency control also passes.

The queue/selector test-only isolation change preserves real temporary ledgers, concurrent workers, successful-baseline assertions, and unchanged selection checks. Separate unstubbed pipeline and probe failure tests remain; the stated race/priority behavior was not weakened.

## Validation evidence

The completed broad run is explicitly **not green**: **708 tests in 1,365.996 seconds, one error and one failure**. Its receipt records 1,366.4598824169952 wall seconds and unchanged bytes for all 75 production/test files during that run. The two failures exposed the latter two defects above. Earlier stopped/time-limited runs and the isolated test-harness correction remain documented; none is represented as a successful full-suite run.

After repair, four direct affected controls passed in 6.231 seconds. Final affected-path validation then passed **125 tests in 85.474 seconds** (85.74504958401667 receipt wall seconds). Its selection includes all six decision test modules, the complete coverage-preparation module, actual dispatcher/replay checks, unstubbed atomic completion, queue race, and selector priority. This reviewer inspected the final log/receipt and independently checked all 75 manifest hashes against the final source/test bytes. This targeted pass does not turn the broad run green. No additional specific affected check is required for the reviewed narrow repairs.

A private-fork retained-result readiness dispatch passed in **15.414602875011042 seconds**, without executing a decision candidate or changing the authoritative 516-event source queue. The final acceptance gate binds this receipt, the passing targeted-test receipt, and independent reviews.

The local site-build log/receipt report success and the homepage evidence guard completed. This reviewer checked the retained generated artifact: **57 public records**, including the C7 protocol/result and excluding the draft internal run record. Its SHA-256 is `4378058a0d5f9f91cde18521ba3f682c7eff03d2c08e0bbde4e6f6e5c071ce55`. No browser inspection or deployment is claimed.

## Original experiment and public claims

All **11 originally frozen** source/test/input files still match their pre-execution manifest. The original development result remains SHA-256 `b4475ad656e3fa6224a1cfa43110b5635e64819876a8e06ffd5985624720d5f9`; its journal remains `78289a4abe277683998cd2a6804446756613c0204ca296f474c774eeace0ca40`. There are 12 exposed cases, four arms, 48 retained attempts, and 98 journal records. No original candidate execution was repeated for this review or acceptance audit.

The public summary matches every projected retained row, arm summary, and report metadata field. Both compact arms reached 4/5 observable and 4/7 world opportunities, with opposite storage-pressure failures. Both lossless controls reached 5/5 observable and 5/7 world opportunities. Each arm retains one unauthorized proposal from a late-observed revocation; the common stipulated-world guard refused it. Zero unauthorized/duplicate effects is guard conformance, not observer safety. No negative artifact outcome occurs in this development set, and the public text states that limitation.

For every arm, retained-byte inspection confirmed equal `dev-01`/`dev-02` input hashes, view hashes, exact view strings, and proposals, with different stipulated authorization. The public conditional information-limit statement is supported. Homepage wording restricts its denominator to valid opportunities justified by available evidence and its missing-information claim to decision time.

The protocol/result, metrics, plans, TODO, DAILY_LOOP and registry agree with accepted C7 and separately queued C8 preparation. The internal validation record is draft. The SCI acknowledgment supports the coordination summary; its release status remains identified as reported, not independently reverified. No document reviewed claims fresh-case execution, live transactions, browser verification, or deployment.

## Actual durable acceptance audit

This reviewer opened the authoritative store with `Ledger.open_readonly` and used verification/status/event reads only. Dispatch **`7b7dd01eb1b044aa8c6a2cdbfa8d7d43`** delivered `assessed`, return code zero, no termination, and authoritative completion **`improvement:decision-development-20261126:complete`**. Its delivered assessment exactly matches the ledger completion body. Saved output hash/size and finish receipt match the returned dispatch receipt.

The accepted assessment identity is `63982ce107f875a65dd9ad0bdde748182eb8d5cc5ef9457b66db8717111fd2cb`; its checked decision-study identity is `3cf4c36eff77965167e879ffa43134828b27459e64f6cd146389f67d550e46f6`. All **37 captured input-manifest roles** resolve to matching observation content hashes and retained blob bytes. Accepted decision arm summaries/checks/source identities match the original experiment. All **88 acceptance-frozen files** still match the gate.

The authoritative ledger independently verifies **556 events, 14 completed assessments, no unfinished runs**, and head `7e8eb852b23c2d65d337450b5e8b9d77bbf6129c1d29b2eab3491e746a5f37ba`. Its queued step is **`decision-development-20261126:next` / `prepare_fresh_decision_comparison`**, with no scale change. Completion and successor occupy one event. Caller time is 15.899196167010814 seconds through returned dispatch, excluding later caller persistence/inspection. Retained-result acceptance executed no decision candidate. These are local integrity/process receipts, not independent timestamps or proof against unrecorded execution.

Receipt SHA-256 identities checked:

| Artifact | SHA-256 |
| --- | --- |
| Acceptance gate | `84c9cabfe996c8350bb7a2091e6136dc811fd44d7148d2d8605be8251d6af0d6` |
| Acceptance result | `1707a8fcc1c78d862ef4567a296fe1b7ec6c81ca823150cad60fe5dba68a77d7` |
| Acceptance postflight | `8a57a24517f4006f25c50dd50bacef3138599a4aa159a05d2422c986b3a6f9ca` |
| Final 125-test receipt | `ec54e33a136acd47c751416cf722bc770e4039da5296d3dc3f4fc3727f4b79ee` |
| Final 125-test log | `8cb29af62e30d8bf92f50e4c8c0dbd0815b2358bec53a0260391284d63767cd3` |

## Reviewed file hashes

| File | SHA-256 |
| --- | --- |
| `DAILY_LOOP.md` | `1c0eb6ffc625d0e400afe5ff860aff259bdcda555d5953f540b722e4c372809b` |
| `TODO.md` | `87fd71195d8383f78a723c664b2dd38941923e34d624f917073f8924ac018264` |
| `docs/experiments/control-exchange-decision-pilot.md` | `2fdd7fc31466b722fe639aaae77284dd1f5f71d67d5dd73662d5fe9b64e1d62c` |
| `docs/experiments/representation-metrics.md` | `d21fa4607f3e6e42b1304a12309018495c2ac5c4947fe80dc217e0fa0f683fa8` |
| `docs/experiments/results/2026-11-26-decision-pilot.md` | `13242b1083a7ae94fb786f5af88137739b5e3f01ece87c3e5c90748f406f86dd` |
| `docs/planning/meta-representation-build.md` | `bf1f15d8c996798bb0448f88d66b92bb718e2eaab64cb941b5489b01a095693d` |
| `docs/planning/runs/2026-11-26-decision-pilot.md` | `18230070f7977abdc9667b4b16ca31e2e5bf1c6356c6e86d0214e20a665752ea` |
| `docs/planning/stepwise-improvement-loop.md` | `7b22618d75a4faa019d0477cb257de61114445d44d9aeea22050da3a25eaf7b7` |
| `engine/README.md` | `57f7c6e522a4d387784bd049a98911c0c32c341f34f3e90c5b0c17169e697223` |
| `engine/epiphysics/decision_assessment.py` | `3698f72d0718ed7f20f6975d2e9f9ad02987342fc8cffd0df1f928236d7b58da` |
| `engine/epiphysics/decision_evaluation.py` | `5a2a868e0520237b314366619361bb1bdb7f22fd52232a58e684cfc27ac9f198` |
| `engine/epiphysics/decision_pilot.py` | `fa066457406e999b7aec146e50fcb4ed7b18b8d96c78e923869133ef290de090` |
| `engine/epiphysics/decision_policy.py` | `57991e37af060391588dc983c06004240b6b68a620fc12b885bd436a9113a077` |
| `engine/epiphysics/decision_views.py` | `35649e1aa70fdc047eb1e9470289b9c90305aaba8c0405f98eb2da25ee561984` |
| `engine/epiphysics/improvement.py` | `4bc7b1fb53959061d2ef9414baf8745152db282bb6717b9b3c4b4ca20037ffba` |
| `engine/epiphysics/retrieval_coverage.py` | `e59de88086f8dfbeb81b1c671d6e98a06264183189a4c8ec80e04f67d0950cbd` |
| `engine/examples/control-exchange/README.md` | `0dfc28c86720321837c9a0b21c645e6a4c3a5866942e9503747183b70fa0b705` |
| `engine/examples/control-exchange/decision-contract.json` | `751931e3078beb8511c1d1a9eed29a5b324026d078b109fada7d70b47c4a1ee4` |
| `engine/examples/control-exchange/development-result-summary.json` | `f0683e1ae15b02871179e91858beb541c6f413271e631ab144177f0d6871de5b` |
| `engine/examples/control-exchange/development-traces.json` | `8d95509194307c86e154c871136b1d908aeb03a187745be49db02b0d65062b64` |
| `engine/examples/control-exchange/evaluation-contract.json` | `1efd3dc61e89e5d1d51a03892255da1ec3cb8b46b2c9c8ba75b0cdb00b1e94d2` |
| `engine/examples/control-exchange/preparation-byte-check.json` | `0ff91c49b7f1ae6016bf7d03b5886b6cff2ad73a8fc3085faa63fbdcc6540c49` |
| `engine/examples/control-exchange/preparation-byte-check.py` | `f5a363937a5d409e2e75c4a4ffb6c406688a4078dc4aae38dbc317b6cf333aa6` |
| `engine/tests/test_decision_assessment.py` | `feb32b6e7e6b424e8e1a021dfa7ecc46f1cdfc04ee9035ba95c6f38a4b4e41db` |
| `engine/tests/test_decision_controller.py` | `5e9168d048c63a268f1e3c6322db6b038bcafc8faf61fe136ba05c720c0836c9` |
| `engine/tests/test_decision_evaluation.py` | `3a9da2ce420087af8830512570a935698b1d394259a98d654c4e41d40938d0af` |
| `engine/tests/test_decision_pilot.py` | `422d2cb1508e16465a96698a60f9d803f40505c387efe8b8f4276e1b2a2e5d24` |
| `engine/tests/test_decision_policy.py` | `8190ea2261414f74a8a6802f58c173b52e21afbd19440237e5c57ba37331929f` |
| `engine/tests/test_decision_views.py` | `d5e391f5cf77e80321e4eef45d972b1f5599e55aeaadfcea15845aec9f84b91f` |
| `engine/tests/test_improvement.py` | `44ace2179b3e807152286d52125d0a44f0ae3240c0c06e71e647157d2e40268b` |
| `engine/tests/test_retrieval_coverage_preparation.py` | `87b012cbafb6d2d093fa9dc5e46f32764fe21c90b32752e5da357943a4faa52b` |
| `research/meta-representation/registry.json` | `a16ac698e705f55c210175b36fa1f006c9cac981558839a92cbc1333944b8dd5` |
| `src/components/home/research-progress.json` | `7b7a2d15cff2007e4fef068acbed06f38b684d01022f3543d5f976bc4900e58a` |

## Reviewer actions and limits

The reviewer performed source/diff inspection, independent read-only artifact comparisons, and small isolated owned controls as previously recorded. The final acceptance audit ran no tests, assessor, dispatcher, policy, candidate, cohort generator, or experiment. It made no repository edits or real-ledger event/blob writes; only this `/tmp` report was written. The reviewer did not author the production fixes. Broader capability, representative performance, total builder/reviewer cost, memory use, live authority, and distributed timing guarantees remain unmeasured.

# C7 final unguided review

No actionable findings.

Reviewed the current `git diff HEAD` for these five files in `/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/decision-pilot`:

- `engine/epiphysics/retrieval_coverage.py`
- `engine/tests/test_retrieval_coverage_preparation.py`
- `engine/epiphysics/improvement.py`
- `engine/tests/test_improvement.py`
- `engine/tests/test_decision_controller.py`

Review baseline: `240763e52c49ddca0a121fc526f0f29da948320a`.
SHA-256 of the exact requested diff: `60d49ba0c2757a31c85a55b11c8f4131f0a1504dd628932f0d14b8c1c3214b6a`.

The coverage preflight now reads its selected prefix and deterministic capture lookups inside one SQLite read snapshot (`retrieval_coverage.py:494–498`). It releases that snapshot before capture writes, and the existing append validator still rechecks the inputs and capacity under the write lock (`retrieval_coverage.py:502–517`). The added test forces the competing commit after the prefix boundary is selected and checks exact retry behavior, capture count, and ledger integrity (`test_retrieval_coverage_preparation.py:190–219`).

The controller checks the dispatcher request identity before returning an existing completed request (`improvement.py:558–566`) and retains the ordinary failure path for a new request whose inputs differ. The decision handoff checks queued origin, requires decision evidence for queued decision work, preserves failed captured inputs, and revalidates checked evidence before atomic completion. The new controller tests exercise these boundaries with explicit local wiring stubs.

The two existing queue/selector tests now stub only the unrelated capability probes and assert that setup assessment succeeded. The real ledger, concurrent claim logic, and selector remain exercised (`test_improvement.py:43–55`, `test_improvement.py:215`, `test_improvement.py:304`).

Read-only review of repository changes and necessary surrounding implementation, following the applicable repository instructions. No tests or experiments were executed, and no research stores or repository files were modified. The only written artifact is this requested review report. Runtime validation remains the responsibility of the separately managed test run.
