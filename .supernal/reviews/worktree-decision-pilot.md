---
task: decision-pilot
branch: worktree-decision-pilot
reviewed_patch_id: ff40435d873af1406afb677a6e38aed2bd9c347c
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/decision_final_critic
reviewer_output_sha256: 8e4b6d251d5d71898377ffe3239c89424d4a53205bc3de1653784afe06ff30ab
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

Reviewer: `/root/decision_final_critic`. **Verdict: fixed. Three medium findings fixed; zero open and zero skipped.**

## Exact scope

Reviewed all **33 owned files, 7,727 insertions and 40 deletions (7,767 changed lines)** from baseline `240763e52c49ddca0a121fc526f0f29da948320a` to feature commit `5091d2b304cd4b7c36c90458b44125e499f33961` in `/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/decision-pilot`.

Managed landing `reviewed_patch_id`: `ff40435d873af1406afb677a6e38aed2bd9c347c` (author-supplied tool identity). Independently verified binary-diff SHA-256: `203e1d1bad814cc72b92f1b5552fcea02487960e7f362e1e94395fb65018290d`; stable Git patch ID: `57409b8cf033e3718f9e211944932d820b705c02`. The committed diff equals the audited working diff.

Scope includes the five decision modules, improvement integration, coverage-freeze repair, six decision test modules and affected legacy tests, owned examples/contracts/results, public protocol/result/homepage, internal run record, metrics/plans, TODO, DAILY_LOOP, and registry. Generated content was restored and is excluded. This review excludes subsequent changes and its own later landing record.

## Findings and repairs

1. **Medium, fixed — omitted decision evidence could consume a decision queue step.** The controller now requires evidence before claiming preparation, repair, or fresh-comparison actions. Missing evidence preserves the queue and events; locked origin errors also fail before evaluation. Temporary-ledger controls cover all three actions and valid completion/replay.
2. **Medium, fixed — a new request's manifest mismatch lost durable failure capture.** The early expected-request hash check now applies to prior completed-request replay. New requests retain the post-capture check within the durable failure path. Actual subprocess mismatch and completed decision replay controls pass.
3. **Medium, fixed — coverage-freeze preflight could combine two ledger versions.** Initial preflight now shares one read transaction, closed before writes; append-lock validation remains. The new deterministic two-connection regression forces the original interleaving and requires one equal freeze, three captures, and a valid chain. The original concurrency test also passes.

The queue/selector test isolation preserves real temporary ledgers, concurrent workers, successful-baseline assertions, and selection checks. Separate unstubbed pipeline and probe-failure coverage remains. No additional specific affected check is missing.

Final source SHA-256: `improvement.py` = `4bc7b1fb53959061d2ef9414baf8745152db282bb6717b9b3c4b4ca20037ffba`; `retrieval_coverage.py` = `e59de88086f8dfbeb81b1c671d6e98a06264183189a4c8ec80e04f67d0950cbd`. Detailed repair review: `/tmp/epiphysics-c7-final-repair-review.md`, SHA-256 `6c426c8009ce3c892eac339eb8e4e12fba997b92bc8cd29a438d7bc8e1bb3d77`.

## Validation and acceptance

The completed broad run is **not green: 708 tests, one error and one failure**, in 1,365.996 seconds (receipt wall time 1,366.4598824169952). All 75 source/test files stayed unchanged during that run. Its two failures exposed findings 2 and 3. Following those repairs, four focused controls passed in 6.231 seconds, and the **final 125 targeted tests passed in 85.474 seconds** (85.74504958401667 wall seconds), with all 75 final manifest hashes matching. That selection covers all six new decision test modules, whole coverage preparation, repaired subprocess/replay paths, unstubbed atomic completion, concurrency, and selectors. This does not establish a green full-suite rerun.

Final validation receipt SHA-256: `ec54e33a136acd47c751416cf722bc770e4039da5296d3dc3f4fc3727f4b79ee`; log SHA-256: `8cb29af62e30d8bf92f50e4c8c0dbd0815b2358bec53a0260391284d63767cd3`. Private-fork readiness passed in 15.414602875011042 seconds without changing the authoritative store.

Independently inspected the original frozen experiment under `.supernal-local/control-exchange/decision-pilot-v1`: all 11 frozen files match, and retained evidence contains the one registered 12-case/four-arm comparison, 48 attempts and 98 journal records. The public projection matches retained rows, summaries, and metadata. Both compact arms achieve 4/5 valid observable opportunities and 4/7 world opportunities; both lossless arms achieve 5/5 and 5/7. Each arm has one unsafe proposal; the common guard prevents duplicate or unauthorized effects. Exact dev01/dev02 input/view/proposal hashes match within each arm despite different world authority, supporting the bounded public information-limit claim.

Read-only ledger inspection independently verified **556 valid events, 14 completed assessments, no unfinished assessment**, and accepted dispatch `7b7dd01eb1b044aa8c6a2cdbfa8d7d43`. Head: `7e8eb852b23c2d65d337450b5e8b9d77bbf6129c1d29b2eab3491e746a5f37ba`. The successor is queued as `decision-development-20261126:next` / `prepare_fresh_decision_comparison`, with scaling disabled. The accepted result matches the completion event and dispatch record; 37 captured manifest roles/blobs and all 88 acceptance-gate files match. Acceptance consumed retained evidence without candidate execution. Gate/result/postflight SHA-256 values are respectively `84c9cabfe996c8350bb7a2091e6136dc811fd44d7148d2d8605be8251d6af0d6`, `1707a8fcc1c78d862ef4567a296fe1b7ec6c81ca823150cad60fe5dba68a77d7`, and `8a57a24517f4006f25c50dd50bacef3138599a4aa159a05d2422c986b3a6f9ca`.

Public and internal documents consistently distinguish accepted C7 from planned C8. Site-build receipts/logs support a passing build with 57 public records, including protocol/result and excluding the draft run note; retained content SHA-256 is `4378058a0d5f9f91cde18521ba3f682c7eff03d2c08e0bbde4e6f6e5c071ce55`. No browser or deployment verification is claimed. The author additionally reports all eight commit hooks passed and knowledge compilation passed from the feature commit with 129 nodes, 156 edges, 27 documents and 32 sources; these last checks were not independently rerun.

## Conclusion and limits

No material correctness, evidence-integrity, lifecycle, or public-claim finding remains. The patch is ready for local landing under normal repository checks. Evidence supports bounded synthetic development results and durable retained-evidence acceptance, not broader performance or hostile same-user isolation.

The reviewer did not author the fixes. This final audit used source and artifact inspection plus read-only ledger verification; it ran no assessor, dispatcher, candidate, cohort, experiment, or heavy test suite, and made no repository or real-ledger writes. Only this temporary report was written. Earlier small owned controls are recorded in the repair review. This review does not authorize a push, deployment, live effect, or fresh cohort.

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
