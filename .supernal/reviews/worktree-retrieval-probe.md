---
task: retrieval-probe
branch: worktree-retrieval-probe
reviewed_patch_id: 2143a83745a7981ded5ad19b3a6f70955495d659
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/c5_critic
reviewer_output_sha256: d9ffebf8a53f07ccd3d5d55b476c8e93919a3ef7a85370196b5870b3ae48d9ac
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 3, low: 0 }
resolved: { fixed: 3, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 17, lines: 1789 }
---

## Conclusion
Ready to land: yes
The fixed two-clause pair and one actual acceptance completed with independently verified evidence and a durable decision-pilot successor. The post-execution transport repair preserved the unchanged measurement core without rerunning retrieval. All findings are resolved, and the final site integrates SCI's release-preparation changes while keeping homepage evidence public.

## Reviewer report
### Initial unguided code review and repair verification

# Independent unguided fixed-clause probe review

Reviewer: `/root/c5_critic`. Review date: 2026-11-26.

Scope: working-tree diff from HEAD in `.worktrees/retrieval-probe`, including the new helper and three new probe test modules. No production edits, private experiment execution, full-suite run, or browser use. The reproduction below used only repository-owned synthetic fixture text in a temporary directory, which was removed afterwards.

## Finding: P2 — Bind the inherited-prefix boundary to accepted C5 evidence

Location: `engine/epiphysics/retrieval_probe.py:350–353`; affected exclusion check: lines 374–376.

The inherited boundary is checked against a hash supplied by the same new protocol, but is not matched to the evidence head retained in the accepted C5 diagnosis. The later prohibition on unplanned execution only scans events after that caller-selected boundary. A caller can run an extra copy of the eventual clause queries after C5, declare that extra run to be inherited history, and then run the two declared repetitions. The validator accepts three actual post-C5 retrievals as the fixed two-run diagnostic. This permits prior exposure and unreported repeat selection despite `additional_repeats_or_queries: 0`.

Affected consumers: `check_support_probe`, and the real captured transport through `prepare_retrieval_study` / `assess_prepared_retrieval_study`. The resulting completed report is eligible for the controller's `prepare_control_exchange_decision_pilot` successor. This review reproduced helper and adapter acceptance; it did not execute a private or full controller transition.

Observed owned reproduction:

```text
accepted_c4_head_seq: 61
extra_terminal_seq: 78
supplied_inherited_prefix: 78
helper_reproducibility: 1
adapter_status: completed
adapter_phase: support_probe
total_probe_retrievals_after_c4: 3
```

An initial variant used a new query and the adapter refused because its unique query blob was not among captured artifacts. The confirmed variant repeats the eventual two clauses: their blobs are also captured by the declared runs, so both helper and adapter accept. The finding therefore does not depend on disabling blob integrity, mutating production validators, or forging receipt hashes.

Narrow repair: require the boundary event's complete `{seq, id, hash}` to equal `origin_transition.body.report.support_diagnosis.input_bindings.prefix_head`, in addition to matching the declared inherited count/hash. Retain the current full-tip and extra-execution checks. Add a positive normal-ancestry control and a negative case with an extra same-query retrieval hidden before the declared boundary. Fixtures that synthesize C5 origin reports need the actual captured prefix binding.

## Reproduction

Run from the reviewed worktree using `PYTHONPATH=engine:engine/tests python3.14 -s`. The fixture runs use owned data and deliberately exercise the accepted receipt path; they make no private-source or network calls.

```python
from pathlib import Path
import tempfile
from epiphysics import retrieval, retrieval_diagnosis as diagnosis
from epiphysics import retrieval_probe as probe, retrieval_assessment as assessment
from epiphysics.store import Ledger
from test_retrieval_diagnosis import make_diagnosis_fixture, bind_diagnosis
from test_retrieval_probe import make_probe_fixture

with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    evidence = Ledger(root / "evidence")
    origin_ledger = Ledger(root / "owned-origin")
    try:
        data = make_diagnosis_fixture(root, evidence)
        _, request, contract, _ = bind_diagnosis(data, evidence, data["origin"])
        core = diagnosis.check_support_diagnosis(
            evidence, cohort=data["cohort"], freeze_event_id=data["freeze"]["id"],
            run_terminal_ids=request["run_terminal_ids"],
            origin_transition=data["origin"], declared_contract=contract,
            diagnosis_raw=Path(request["diagnosis_file"]).read_bytes(),
            review_raw=Path(request["diagnosis_review_file"]).read_bytes())
        original_head = evidence.events()[-1]
        origin = origin_ledger.append("improvement_completed", {
            "run_key": "owned-c5", "result": "assessed",
            "report": {"support_diagnosis": {
                "schema_version": 3, "phase": "support_diagnosis", "status": "checked",
                "study_id": data["cohort"]["cohort_id"],
                "diagnosis_id": contract["diagnosis_id"], **core}},
            "next_step": {"id": "owned-c5:next", "state": "queued",
                "action": "prepare_focused_support_followup", "scale_change_allowed": False}},
            "improvement:owned-c5:complete")
        extra = retrieval.run_lexical_retrieval(evidence, corpus_id="corpus",
            queries=[{"query_id": "clause-a", "query": "Delta invoice"},
                     {"query_id": "clause-b", "query": "Delta quantity"}],
            run_key="unplanned-before-freeze", indexing_recipe="raw-window-text-v1")
        fixture = make_probe_fixture(root, evidence, origin=origin, data=data,
                                     subprocess_runs=False)
        report = probe.check_support_probe(evidence, **fixture["core_args"])
        prepared = assessment.prepare_retrieval_study(fixture["request_path"],
                                                       declared_contract=fixture["contract"])
        accepted = assessment.assess_prepared_retrieval_study(prepared)["report"]
        print({"accepted_c4_head_seq": original_head["seq"],
               "extra_terminal_seq": extra["seq"],
               "supplied_inherited_prefix": fixture["probe_protocol"]["evidence_preservation"]["inherited_prefix"]["events"],
               "helper_reproducibility": report["reproducibility"]["value"],
               "adapter_status": accepted["status"], "adapter_phase": accepted["phase"],
               "total_probe_retrievals": len([e for e in evidence.events()
                   if e["kind"] == "retrieval_completed" and e["seq"] > original_head["seq"]])})
    finally:
        origin_ledger.close()
        evidence.close()
```

## Reviewed identities and disposition

- `retrieval_probe.py`: `591d9e618f1e438447129906060d509ac40b540e1efaa6c37043ac5efcd95ef7`
- `retrieval_assessment.py`: `da2b1a695d9352cdf7ccaef8e0a243a40284250046c3df258fef05c03164b493`
- `improvement.py`: `59da79b86c0583f4eb781f44fdef2b0f0720ec405c1f91e9a08e0aab8ac8c189`

`git diff --check` passed. One actionable finding; no other independent findings. Root and the implementation owner were notified. At this initial review, acceptance required the narrow fix and its regression evidence; the disposition below supersedes that pending verdict without replacing the original finding or reproduction.

## Repair verification — cleared

Independently inspected the repair at `retrieval_probe.py:354–357`. It compares the complete boundary event `{seq, id, hash}` to the prefix head retained in the accepted C5 diagnosis. The existing declared count/hash check, complete captured-tip check and exclusion of extra execution remain in place. This closes the reported boundary substitution.

Independently executed the following two owned tests under Python 3.14; both passed in **9.617 seconds**:

- `RetrievalProbeTests.test_inherited_boundary_cannot_hide_an_extra_clause_trial`: performs an actual additional same-clause retrieval before the declared envelope, then verifies rejection by both the helper and the real captured adapter specifically for the accepted-diagnosis boundary mismatch.
- `RetrievalProbeTests.test_two_real_fresh_processes_reproduce_and_preserve_original_evidence`: verifies the ordinary two-process positive path, repeatability and unchanged evidence during checking.

Also inspected the narrow early-nonzero-exit repair at lines 109–114 and 430–434. An attempted rejected process can retain a genuine start, or no start, without inventing a terminal. Caller/stdout/stderr references remain mandatory; absent event references are checked against actual absence, real terminal references still require their actual rejected terminal, and nonzero exit is required. Incomplete execution still refuses completion. The two added capture controls retain opaque output bytes and any existing start, then exercise repeatable incomplete refusal. These failure controls were inspected rather than redundantly rerun; the builder separately reported their successful targeted execution.

Final reviewed helper: `0869e0b6860430c63aa7666341c0ab891076bc1090b062058f630f17b143f364`.

Final reviewed probe tests: `5f94076c10f0f402f33f645cad9d6c885fae9d45e8f535e3258f6723a19fc5fa`.

Adapter and controller hashes remain those listed above. Final `git diff --check` passed. **Unguided review cleared; no outstanding findings.** This is approval for the parent to proceed with its full-suite gate, not evidence that the full suite or private probe has run. No production source edits or private research execution occurred during this verification.

### Guided code review

Independent guided C6 production review by /root/c4_safety

Decision: approved after the two narrow repairs below; no remaining actionable findings in the reviewed code. This reviews the fixed two-clause, two-process diagnostic and existing controller integration. The exact execution/assessment freeze and actual outcomes require their separate checks.

Closed findings:
- A nonzero process exit before a terminal could fail the capture shape and omit its actual caller/output evidence from the durable assessment input. Rejected attempted slots now allow the actual start and terminal to be absent, while caller/stdout/stderr remain mandatory. Completed slots still require both event references; orphan terminals, hidden actual events and continuation after a failed first slot remain refused. Without an actual terminal, nonzero stdout stays opaque. The adapter retains partial bytes before the deterministic incomplete-result refusal.
- A caller-selected inherited boundary could hide an extra clause trial. The exact boundary event seq/id/hash must now equal input_bindings.prefix_head in the accepted C5 diagnosis report. Existing full-chain validation, authoritative live-origin matching and complete-current-tip checks preserve this binding. This was independently identified by both reviewers and counts as one shared finding.

Reviewed safeguards:
- The captured origin self-hash alone is insufficient: the controller matches its complete canonical event to the latest authoritative completion and current queued predecessor. Exact terminal replay precedes current ownership checks. Claim and completion recheck the live origin under the existing append locks; live ledger corruption is not converted into a supplied-input failure.
- Preparation captures bounded external bytes, the complete bounded prefix and required blobs. Assessment reconstructs only those bytes in an owned temporary store, so later original-path removal cannot change replay. Completion revalidates captured inputs, implementation identity and deterministic report within the original time budget.
- Original C4 cohort/protocol/review bytes, measurement, frozen candidate, corpus identity and original result receipts remain bound through accepted C5 provenance. Probe request/candidate checks apply to each actual receipt, so two equally wrong requests do not establish valid reproducibility.
- Exact protocol/review/request/supervisor observations precede the deterministic envelope observation, which precedes both execution starts. Second execution follows a valid first completion. No undeclared post-boundary run is permitted. Failure and unstarted slots retain their real evidence without inventing a successful pair.
- Source bytes, loaded bytecode, callable identities and validation dependencies remain guarded. Existing limits remain 256 events, 4,000,000 prefix bytes, 128 artifacts and 16,000,000 aggregate artifact bytes; individual external probe artifacts are capped at 1,000,000 bytes and the report at 256 KiB.
- The helper performs retained interval analysis and neutral receipt validation, with no retrieval, indexing or scorer execution. Per-clause alternatives remain separate; repeats are not pooled. Valid disagreement preserves both executions and suppresses a combined support conclusion.
- The report stays under support_probe; no original quality score is replaced and prior outcome remains unmeasured. Existing integrity/conformance priority is preserved. Valid reproducibility selects pilot preparation only, valid disagreement selects reproducibility repair, and incomplete evidence follows existing durable assessment failure. No scale or adoption is authorized.

Focused verification: independently exercised two permitted partial-nonzero shapes, four malformed-shape refusals and the live source/bytecode guard on the exact final helper; all passed. Inspected the two new owned adapter-capture controls for pre-start/post-start nonzero exits and repeated captured assessment without ledger changes, and the helper/adapter hidden-extra-run regression. Builder reports five focused repair/positive controls passing in 27.038 seconds. The independent unguided reviewer separately reports the hidden-extra-run negative and normal two-process positive passing (two tests, 9.617 seconds). Those dynamic controls were not duplicated. git diff --check is clean. No full suite, real-store execution, search, indexing, scoring, browser or production edits were performed by this review.

Reviewed SHA-256 values:
- engine/epiphysics/retrieval_probe.py: 0869e0b6860430c63aa7666341c0ab891076bc1090b062058f630f17b143f364
- engine/epiphysics/retrieval_assessment.py: da2b1a695d9352cdf7ccaef8e0a243a40284250046c3df258fef05c03164b493
- engine/epiphysics/improvement.py: 59da79b86c0583f4eb781f44fdef2b0f0720ec405c1f91e9a08e0aab8ac8c189
- engine/tests/test_retrieval_probe.py: 5f94076c10f0f402f33f645cad9d6c885fae9d45e8f535e3258f6723a19fc5fa
- engine/tests/test_retrieval_probe_assessment.py: 2e6e1c562de5305afd345568c85019480c3d14cbe203d38c372e75bdf1926f27
- engine/tests/test_retrieval_probe_improvement.py: 09e9a631f1910d467a364dc05ffc274add5cc5ad22cc09887660cbc60a9605e8

The separate supervisor and dispatcher reviews are saved beside this note. Their approval does not substitute for checking the final manifests and authoritative live predecessor before actual work.

### Transport repair: unguided review

# Independent support-probe transport review

Reviewer: `/root/c5_critic`, 2026-11-26.

**Verdict: no actionable findings. The narrow transport repair is ready for the parent's validation gate.**

Reviewed the exact difference between retained `execution-adapter.py` and working-tree `engine/epiphysics/retrieval_assessment.py`, plus the frozen `engine/tests/test_retrieval_probe_assessment.py`. No production edits, retrieval execution, controller dispatch, test execution or private-store reads occurred in this review. Existing review files were left unchanged.

## Change and affected consumer

At `retrieval_assessment.py:499–505`, the support-probe capture now includes observation blobs from every event in the captured prefix, rather than only observations after the inherited boundary. That matches `retrieval_probe._check` calling whole-prefix `Ledger.verify`, which requires each retained observation's content to be available. A valid unrelated historical observation must not become a missing-content error merely because transport retained its event but omitted its blob.

The expansion remains inside the support-probe branch. It neither changes the prefix nor selects more retrieval results. The checked complete-tip constraint, inherited boundary binding, source/event identities and exclusion of undeclared executions remain intact. The shared loop still verifies regular files, content hashes and sizes, deduplicates by content hash, and enforces the same per-blob, artifact-count and aggregate-byte limits. Larger histories can therefore refuse at the existing limits; this change does not silently raise them. Captured assessment remains detached from original source paths.

## Regression coverage inspected

The new test at `test_retrieval_probe_assessment.py:32–65` creates an unrelated historical observation before the fixture history, establishes its presence before the exact accepted C5 prefix boundary, and proves it is outside the selected corpus sources. It then requires successful captured assessment, exact blob bytes, and the original observation in the captured event prefix.

Its negative control removes only that blob and its transport manifest entry while preserving the event prefix and rehashing the prepared manifest; the helper must reject whole-prefix integrity. Thus the control exercises the actual consumer requirement rather than merely checking that a collection loop changed. Event equality and source-file hash/mtime equality guard against writes. The existing tests continue to cover source-path removal, exact bounded regular inputs, source-guard changes, and refusal to truncate later events.

The builder reported this new test passed in 8.085 seconds. That execution was not repeated here. Additional builder controls and the parent's full-suite or actual-assessment gates are separate from this source review. `git diff --check` passed during review.

## Reviewed hashes

- Retained execution adapter: `da2b1a695d9352cdf7ccaef8e0a243a40284250046c3df258fef05c03164b493`.
- Repaired working-tree adapter: `ab43729d4f0795283daeff0454992ea9178d17b8e2482c861dd2fd135174e1a4`.
- Probe assessment tests: `2024d21dc426671afd5dff8c81afb089ffcd839a4780f3764d505e259c67f9af`.

This verdict applies to the transport delta and inspected regression only; it makes no claim about private experiment acceptance or scientific results.

### Transport repair: guided review

Independent guided C6 transport-repair review by /root/c4_safety

Decision: approved. No remaining actionable finding in the single adapter repair, fixed read-only preparation utility or separate acceptance-freeze utility. Actual repaired preparation and final acceptance inputs remain subject to the next independent saved-output review.

The original frozen adapter omitted unrelated inherited observation blobs while retaining their events; the unchanged helper verifies the entire captured prefix. Comparing the retained execution-adapter.py directly to the repaired source shows exactly one behavioral change: support_probe capture enumerates observations in all events instead of events[inherited_count:]. The accompanying comment explains why. Each reference still passes existing identity/byte checks and deduplication, with all artifact/prefix limits unchanged. Other phases are unaffected. No helper, scorer, retrieval runner, corpus, protocol, request, result or controller semantics changed.

Verified the retained original adapter digest is da2b1a695d9352cdf7ccaef8e0a243a40284250046c3df258fef05c03164b493. Among the original 29 production/fixture pins, the adapter is the sole changed file. Helper 0869e0b6 and controller 59da79b8 remain as reviewed. Original gate 74088bb9, all eleven original private input pins and the five explicitly pinned repair inputs match. Both successful execution slots' external caller/stdout/stderr files equal the originally captured blob bytes; current blob content agrees with successful execution postflight. Original C4 archive hashes and modification times still match the immutable gate.

The preparation utility explicitly permits only the repaired adapter hash, keeps the original adapter and failure evidence, requires the original successful execution/prefix and authoritative queue, and profiles out retrieval/index/scoring calls. It captures the same saved study, then requires every key of the pinned pre-repair helper core to match. Output names are new and exclusive. Independent postflight rechecks frozen repair inputs and complete physical working evidence even after failure. The original execution gate and earlier preparation failure are left intact.

Six owned mocked utility controls passed: same-core success, changed-core refusal, forbidden-search refusal, changed-evidence refusal, postflight-source failure and report-write failure. Each attempted mock capture/assessment once and performed both postchecks; failures preserved error postflight and refused success. No actual capture, helper assessment, retrieval, ledger operation, dispatch or source check was invoked by those mocks.

Inspected the new owned historical-observation regression: it first proves the observation precedes the accepted C5 boundary and is outside selected corpus sources; repaired capture succeeds, an exact omitted-blob mutant fails integrity, and source files/events remain unchanged. The saved affected log shows all seven tests passed in 52.247 seconds; the saved legacy log shows four tests passed in 11.673 seconds. Root also reports the retained old adapter's expected failing red control. These tests were not duplicated. The 607-test pre-execution suite remains evidence for the original source, not a claim of a post-repair full-suite run.

The acceptance-freeze utility checks clean read-only preparation, equality with the pinned original core, exact repaired source/test hash and passing focused logs. It includes the new reviews, original execution artifacts/failure/gate, repaired preview and manifest, retained suite evidence and external C4 inputs in a separate assessment-freeze.json. It binds current evidence and the same authoritative origin to the unchanged dispatcher and retains 30/60/75-second acceptance bounds, zero model calls and zero external spend. It does not change execution history or authorize another retrieval.

Reviewed SHA-256 values:
- /Users/ianderrington/git/ianderrington/epiphysics/.worktrees/retrieval-probe/engine/epiphysics/retrieval_assessment.py: ab43729d4f0795283daeff0454992ea9178d17b8e2482c861dd2fd135174e1a4
- /Users/ianderrington/git/ianderrington/epiphysics/.worktrees/retrieval-probe/engine/tests/test_retrieval_probe_assessment.py: 2024d21dc426671afd5dff8c81afb089ffcd839a4780f3764d505e259c67f9af
- /tmp/epiphysics-prepare-c6-transport-repair.py: efdc8ea2d608d646dd88f70daed8912fe8dea73ba0574476dcb555a7c176e371
- /tmp/epiphysics-freeze-c6-assessment.py: 983595d8099f2caabf911843d9859722e6aa4228df5f190fc4db223b4a98ddfb

Affected log SHA-256: 9936a39840a849b5f730ecb7ea18b443782201a633e192a6f3d2368bfc4ce593
Legacy log SHA-256: cb559d2ca7346c4759ce3570f5680d71c72813beee3ee9a86e13a0a7b65e7bbc

No actual repair preparation, acceptance freeze creation or dispatch was performed in this review. No pinned artifact or production source was edited; only this new review note was saved.

### Saved repaired assessment review

Independent C6 repaired-preparation acceptance review by /root/c4_safety

Decision: clear for creation of the separate assessment freeze and the already reviewed bounded acceptance dispatch. No new retrieval is authorized by this review. The original execution gate and failed preparation remain intact.

The saved report is schema 3/support_probe/completed, with two valid identical ordered-result/projection/diagnostic repeats. Its complete ten-key diagnostic core is canonically identical to direct-core-before-transport-repair.json (original file SHA-256 681543d1cffe2ac0eb83a8194b96155feb33e9623fde0d16c6dfb7758f6ea3ed). The canonical core hash is f8b99a3dd11497c883b9840e08896654d512381211b8eb0914a1e4ee0f2ba4be. Equality includes original lineage, raw result rows, span analysis, resource receipts, limitations and helper identity. The repaired adapter changes transport/assessment identity only.

Independently reconstructed all 82 captured input roles from saved request, declaration, current guarded source bytes, original C4 files, probe artifacts, actual blob bytes and the read-only complete event prefix. Every manifest digest matches. Every observation's blob is present, including unrelated inherited history. The exact input total is 2,343,807 bytes. Adding the canonical 32,760-byte report gives 83 artifacts and 2,376,567 bytes, below 128 artifacts/16,000,000 bytes. Canonical report SHA-256 is 6dc7c14adcad1e22384e973077375071c8bc94cf69ce9a9a99488177ebd1f52f.

Ledger.open_readonly verified 198 events, complete prefix 364,466 canonical bytes, head 2219c0ea1273d82788b11fce6bd3cf2b514aea50c57cb510523d46d037990dad; both remain below 256 events/4,000,000 bytes. Envelope sequence 158 precedes the first start 159/terminal 175 and second start 179/terminal 195. The saved execution head and report prefix binding match the actual tip. Before/after physical file hashes and modification times remain unchanged; no mutable real ledger was opened. Original C4 archive hashes/mtimes still match gate 74088bb9. The original failed preparation still records its integrity error, and the immutable execution gate retains its original exact digest.

The repair postflight records no errors, unchanged input evidence, no forbidden calls and zero new retrievals. Reported original caller durations are 0.382334875 and 0.323650834 seconds; inner retrieval durations are 0.137841167 and 0.096924042 seconds with their distinct recorded scopes. Model calls and external spend are zero. Whole-step builder/reviewer cost remains unmeasured.

The resulting diagnostic recovers discovery support within its top 5 and direct commitment support at rank 1; the union of the two separately ranked top 5 sets covers the original joint alternatives. This is a ten-window development diagnostic, not a replacement for the original joint-question score or a quality/adoption claim. Repeats are not pooled. The existing valid-reproducibility policy may queue pilot preparation only.

The authoritative controller is unchanged at 406 events/head b6a9f2cbe8962859c0d9330e1cd3687246833d45138c2f3d052070d2667f9565, with the retained origin equal to the actual event, no unfinished assessment and support-diagnosis-20261126:next still queued for prepare_focused_support_followup. No dispatch occurred during this review.

Reviewed saved-file SHA-256 values:
- transport-dry-assessment.json: d1fba34f71795023dd606b3e437b10b7b2044477291e5f4a3e5668a338df9f7d
- transport-prepared-manifest.json: f7c6869bd8417fbe00904a0945efbf8198976475bb64c253003fbadbe463a899
- transport-preparation-postflight.json: 4b93571b0527e0b2d1d8c024be4c6dc348ee485f30136c266db9856f3850f73a

No helper assessment, scoring, indexing, retrieval, acceptance dispatch or test suite was executed by this reviewer. The verification read saved bytes and ledgers only; this new note is the sole saved artifact of the acceptance review.

### Actual acceptance audit

Independent actual C6 acceptance audit by /root/c4_safety

Decision: clear; no discrepancies found. Acceptance completed exactly once and queued support-probe-20261126:next with action prepare_control_exchange_decision_pilot. This is preparation only; no quality improvement, adoption, payment, control action or scale change is asserted.

The authoritative controller, opened only with Ledger.open_readonly under the pinned interpreter, verifies at 516 events with head 591be146303bb407e78f0b6256405db0ca91987857d50f189d4bb57de0e2b124. It contains 13 completed assessments, no unfinished assessment, and exactly one start plus one completion for support-probe-20261126. The completion is improvement:support-probe-20261126:complete. The saved transition equals its complete authoritative body; dispatch output, delivery record and postflight agree with that event and current status.

Assessment freeze SHA-256: 3922a60d0d168c20ca0df86f19ddee8fe26601ede8a6e911d13f2237709eb312. All 30 code/test/fixture pins, 37 private artifact pins and 3 external C4 file pins match their actual bytes. The unchanged dispatcher matches its reviewed digest. The old execution gate, original adapter bytes, earlier failed preparation and separate transport reviews remain retained and pinned.

The entire accepted support_probe report is canonically identical to transport-dry-assessment.json, including the repaired assessment identity and original lineage. Its canonical report hash is 6dc7c14adcad1e22384e973077375071c8bc94cf69ce9a9a99488177ebd1f52f. Its ten-key diagnostic core remains exactly equal to the immutable pre-repair helper result. Each of the 82 prepared input roles was independently matched to the actual controller observation, stored blob digest and exact byte size. Reproducibility remains 1 for the two fixed repeats. No actual_retrieval score was added; prior_action_outcome is explicitly unmeasured for support-diagnosis-20261126:next, with null metric. The successor has no quality target and scale_change_allowed is false.

The working retrieval evidence remains 198 events/head 2219c0ea1273d82788b11fce6bd3cf2b514aea50c57cb510523d46d037990dad. Its entire recorded physical inventory, including byte hashes, sizes and modification times, equals the assessment freeze before and after this audit. Original C4 archive hashes and modification times still match the original execution gate. Acceptance did not append retrieval events or change the saved source data.

Dispatch ID: 9b01109eb03e47bd8343d4314ceb9a9d. The caller and dispatcher both report exit 0, no termination, delivered/completed assessment and zero stderr bytes; caller stdout hash/size match the exact saved dispatch output. Postflight has no errors and all checks true. Reported inner assessment time is 18.364754458 seconds, dispatch wall time 20.833989875 seconds and outer caller wall time 21.714997166 seconds. These are distinct scopes and are not added. They fit the declared 30/60/75-second bounds. Model calls and external spend are zero. Whole-step builder/reviewer cost remains unmeasured.

No assessment, retrieval, indexing, scoring, dispatch or test suite was rerun for this audit. Only saved artifacts and read-only ledgers were inspected. This new note is the only audit output; no pinned prior record was modified.

### Publication and merged-site review

# C6 publication review

Independent reviewer: `/root/c5_critic`, 2026-11-26.

**Ready for publication/landing. No actionable findings.** This verdict includes the final acceptance paragraph and reproduction identities, completed C6 / preparation-only C7 planning updates, result graph additions and homepage summary.

## Evidence reconciliation

Reviewed the new fixed-clause protocol and execution record, homepage data, TODO, meta-representation plan, stepwise loop, metric additions, engine/example READMEs, CI timeout and registry delta in `.worktrees/retrieval-probe`. Reconciled them with saved C6 reports, caller/dispatch receipts, postflight checks, suite log and independent repair reviews. This review did not open research ledgers, execute retrieval, dispatch the controller or modify production files.

The clause table matches the retained report: discovery incomplete at 1 and 3, complete at 5; commitment complete at all three cutoffs. The combined result has ten distinct windows, 20,480 summed bytes and 18,688 unique source bytes, against five / 10,240 / 9,728 for the original question. Repeats agree; they are not pooled. The public record and homepage state the changed selection/reading budget and retain the C4 5/6 score without a same-budget improvement, quality, adoption, prediction or business-benefit claim.

The saved repaired report matches every key of the original pre-repair diagnostic core. The transport record correctly retains the initial failure, explains the misleading early mutation flag, and distinguishes the one-file adapter repair from a rerun. Saved counts match 82 input artifacts / 83 including the report / 2,376,567 bytes, with unchanged input evidence and zero new retrievals. The original archive has 152 events; the working prefix has 198 with exactly the two declared starts and completions.

The 607-test / 951.108-second result is explicitly limited to pre-repair source. The seven affected tests / 52.247 seconds, four historical controls / 11.673 seconds and six mocked utility controls match retained review evidence. Increasing the CI job window to twenty minutes does not change experimental budgets. Retrieval caller times round to 0.382335 and 0.323651 seconds, total 0.705986; inner times round to 0.137841 and 0.096924. Their nested scopes and unmeasured whole-step costs are clear.

## Final acceptance

Saved dispatch output and `transition.json` agree. The worker `support-probe-20261126` completed and selected `prepare_control_exchange_decision_pilot`; postflight reports 516 verified controller events, thirteen completions and no unfinished claims. Prior quality remains unmeasured; successor metric, target, cost and success probability are null, and scale change is disabled. Postflight errors are empty and frozen-input, evidence and controller checks pass.

The final paragraph's 18.364754 / 20.833990 / 21.714997-second nested durations, UTC dispatch interval, zero return code and delivered-output status match their receipts. The four published identities match:

- Measurement core: `f8b99a3dd11497c883b9840e08896654d512381211b8eb0914a1e4ee0f2ba4be`.
- Probe contract: `2daf8ed99910bec98fe7cd0b3fa33ea5a7af0bea9013f859f6930def6674c6ba`.
- Captured assessment identity: `6682f712f02b5bd2fa9ea3ee135e86e04d4081fce2a5a4c4afbea491563effc5`.
- Controller event: `591be146303bb407e78f0b6256405db0ca91987857d50f189d4bb57de0e2b124`.

## Presentation, privacy and links

No raw third-party source quotations or absolute private filesystem paths appear in the reviewed public delta. Authored queries, aggregate outcomes and the relative local retention directory are appropriate. Local integrity is explicitly distinguished from independent timestamps/execution witnesses. The date convention is explained.

Homepage links, required evidence text and the displayed public-record date resolve correctly. Its larger-budget qualification is adjacent to the result, and the next simulation remains planned. Added graph nodes are unique; their edge endpoints and document paths resolve. The observed C6 claim cites its protocol and run record and motivates the proposed decision experiment. TODO and planning retain C7 as preparation without a final-case result or performance claim.

`git diff --check` passed. Parent reports the production site build and homepage guard passed, with 43→68 content entries, no removed slugs and both new documents present; the exact artifact was archived before restoring generated source output. Browser/render QA, deployment and committed graph compilation are not claimed by this review.

## Integration recheck at ce6955d — cleared

The merge retains both sides. C6's homepage component/data, protocol and execution record exactly match its owned parent `53ab092`; `/about` and the SCI configuration changes match parent `8da3027`. C4, C5 and C6 evidence remain public, while the internal plans are drafts. Every static homepage document/app link and each data-driven evidence link resolves to a public target.

Independently checked `/tmp/epiphysics-c6-merged-content-data.json`: 55 entries versus the prior build's 68; all thirteen removed entries are now intentionally marked draft. C4/C5/C6 records and the new protocol remain present. Artifact SHA-256: `cd62569b194da8deee19721014fbbd045723f604419051e4eacf4cd529b66a63`. The tracked generated artifact was restored by the parent after archiving; its older contents are not the merged-build evidence.

Parent reports the merged site build exited zero, graph compilation produced 123 nodes / 146 edges / 24 documents / 32 sources, and the managed workflow's reviewed patch ID remains `cd1fe7bdf991c878820e5a8c0954de1f7e94a778`. No experiment review was repeated. Integration review remains clear; no deployment or rendered-browser claim is made.

## Final public-result path — cleared

After SCI's publication-boundary clarification, the C6 result now lives at `docs/experiments/results/2026-11-26-retrieval-probe.md`, served as `/experiments/results/2026-11-26-retrieval-probe`. The prior planning-path source is removed; parent confirms it was never deployed. This path supersedes the historical path references in the earlier review sections.

Independently compared the moved file to the previously reviewed committed content: the only changes are its two relative Markdown link targets, both resolving to existing public documents. Scientific prose, numbers, limitations, acceptance details and hashes are byte-for-byte unchanged. TODO, the internal meta-plan, registry document path and homepage evidence URL all use the new location; no current reference to the old C6 path remains in the inspected source/docs/registry set. The new result retains `draft: false`, and homepage required evidence text still matches. `git diff --check` passed.

No actionable finding. The parent is rebuilding the site for this final path change; the prior successful build/artifact does not substitute for that rebuild. This check changed only this review note and did not rerun research, modify production or claim deployment.

## Checks run
- Pre-execution full engine suite:607 tests passed in951.108seconds under pinned Python3.14.8/SQLite3.53.4. This suite predates the adapter transport repair; it is not a full-suite claim for repaired source.
- Post-repair:7 affected assessment tests passed in52.247seconds and4 historical controls passed in11.673seconds. Exact retained old adapter reproduced the real failure on an owned history fixture; repaired positive passed. Six independent mocked preparation controls passed. All production files except the one reviewed adapter change match the pre-execution gate.
- Actual two retrieval processes executed once each. Direct unchanged-helper core before repair equals repaired captured core.82 input artifacts/2,343,807bytes;83 including report/2,376,567bytes.198-event working store and152-event archive unchanged during acceptance.
- Actual single acceptance:516 verified controller events,13 completions,no unfinished claim; support-probe-20261126:next selects prepare_control_exchange_decision_pilot. Separate independent audit verifies source/input hashes, full report equality, process receipts and original evidence.
- Production site build passed before and after merging current ian-dev release preparation. Final build-time evidence guard passed; generated55 public documents includeC4/C5/C6,13 intentionally hidden draft entries were removed from prior68. Final public-result relocation build also passed; homepage and graph use experiments/results. Final55-entry artifact archived at/tmp/epiphysics-c6-public-result-content-data.json and tracked generated file restored.
- Knowledge graph compiled at46dec53:123nodes146edges24 exact committed documents32 bibliographic sources; payloadc057f030a9244f986c76ade591489bc933f7771a5224594286960e1aec1d0238. This is a curated map, not empirical validation or timestamp evidence.
- git diff --check passed; explicit-path feature commit53ab092 passed managed hooks. Final owned reviewed patch ID comes from sc git worktree finish dry-run, not a whole-parent merge diff.

## Not verified
No browser/rendered inspection, deployment, remote CI, equal-budget improvement, general predictive/business advantage, external witness, total builder/reviewer monetary cost or always-on execution claim. The new decision pilot is preparation only. Original C4 scores remain unchanged. Program calls/spend remain zero; agent effort is separate and unmeasured.

## Findings
- [medium] [fixed] Bind the inherited prefix to the exact accepted C5 evidence head so a protocol cannot hide an extra trial.
- [medium] [fixed] Preserve actual caller/output evidence for nonzero child exits without inventing a terminal; incomplete executions still cannot pass.
- [medium] [fixed] Capture every observation blob in the bounded prefix so historical unrelated observations do not break whole-prefix verification; original failures and same-output repair evidence are retained.
