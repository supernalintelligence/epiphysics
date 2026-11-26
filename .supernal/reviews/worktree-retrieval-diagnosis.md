---
task: retrieval-diagnosis
branch: worktree-retrieval-diagnosis
reviewed_patch_id: 4c9917d6090421255169245e2357b4b184bb8c1f
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/c5_critic
reviewer_output_sha256: b91833a3e91037a886958655071d32c16b09acfb62a9ed478515ba8c8d767f46
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 3, low: 0 }
resolved: { fixed: 3, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 16, lines: 1336 }
---

## Conclusion
Ready to land: yes
The final implementation and actual retained-evidence diagnosis passed independent review. One fixed worker consumed the exact C4 predecessor and atomically selected bounded follow-up preparation, preserving original quality and source bytes. All accepted findings are fixed; the follow-up experiment has not run.

## Reviewer report
### Unguided review: /root/c5_critic

Approved after one fixed finding; no remaining actionable findings.

The diagnosis adapter previously accepted reformatted cohort bytes despite the frozen binding. Its new hash checks reject altered cohort, protocol and review files while preserving unchanged inputs.

Seven focused controls passed, covering interval arithmetic, alternative bundles, deferred failures, unresolved judgments, captured-only replay, forged origins and the repaired byte binding. `git diff --check` passed.

Reviewed SHA-256:

- Helper: `ab63a147f0874716c3a5de249c30f9ec21907e378c37cfa44e1250bd8fd2cc5e`
- Adapter: `7b029abd09f5c2b9505a9633e6cdc8b626f6f74a5dd4f7938c97f5f50237c909`
- Controller: `e4643e9201ca109d538b06f93e250c4fb32a511951e617008b7427337f1d48b9`

No edits, full-suite run, private evidence access or actual research execution. Stored assessment timing excludes completion-time revalidation; report outer timings separately.

### Final narrow controller repair

Approved the narrow repair; no new findings.

Live-ledger verification now occurs outside the supplied-origin error handler, so corruption refuses the claim. Invalid supplied evidence still follows the intended durable failure path.

Builder’s four focused controls passed in 26.042 seconds; I inspected the repair and controls without duplicating execution.

Final controller SHA-256: `efd48fb24c8a28c1fbf7896608ba70c70c997157462dee140080f8d11788a0e2`. Other reviewed production hashes remain unchanged.

### Guided review: /root/c4_safety

Guided code review accepted at helper ab63a147f0874716c3a5de249c30f9ec21907e378c37cfa44e1250bd8fd2cc5e, adapter 7b029abd09f5c2b9505a9633e6cdc8b626f6f74a5dd4f7938c97f5f50237c909, controller efd48fb24c8a28c1fbf7896608ba70c70c997157462dee140080f8d11788a0e2. Exact frozen-byte finding is closed by the three-role digest check and c5_critic's focused dynamic verification. Live integrity verification now sits outside supplied-origin error handling under claim, preserving refusal before append. No additional actionable findings. Preview core and windows match prior audit; preparing the authorized attributed review now, with retrieval_gap and explicit causal/answer-generation limits.

### Caller review: /root/c4_safety

Accepted the revised caller; the persistence finding is closed.

Verified hash: `3a690c2200f2d1516d7492c8ce97c6b431e5b5bc21816e95081cc0d82ac78e79`.

- Twelve existing-file/symlink controls refused before launch.
- Ten mocked execution and write-failure controls passed.
- Postflight checks ran despite receipt-write failures.
- Failed cases saved no transition; retries were refused.
- Pinned `-s` invocation confirmed.

No remaining wrapper findings. No real processes, store access, or source edits.

### Actual evidence audit: /root/c4_safety

C5 actual evidence audit by /root/c4_safety

Decision: clear; no discrepancies found.

The live controller has 406 verified events, head b6a9f2cbe8962859c0d9330e1cd3687246833d45138c2f3d052070d2667f9565, 12 completed assessments, and no unfinished assessments. The latest authoritative event is improvement:support-diagnosis-20261126:complete. Its complete body equals transition.json and the assessment returned in dispatch-output.json. The queue is support-diagnosis-20261126:next, action prepare_focused_support_followup, with null metric, observed value, target, success probability and estimated cost; scale change is false. The prior action outcome remains unmeasured. No actual_retrieval report or new retrieval quality metrics appear in this assessment.

Exactly one recorded dispatch uses run key support-diagnosis-20261126: dispatch 24ebeeb6eb0b4475a54f54cc171b6ffb. The controller extension is exactly 74 events: one claim at sequence 333, 72 captured observations, and one completion at sequence 406. Claim worker dispatch ID and PID match the process receipt; the claimed step equals the authoritative original C4 successor. There are no retrieval execution events in this extension. The original C4 completion remains event 332 and equals the captured origin export in full.

I verified every captured observation's blob digest and byte length. All 47 transported input artifacts match the preflight prepared manifest and their captured controller observations, totaling 1,768,816 bytes. The complete captured diagnosis report is byte-for-byte equal to the canonical saved dry assessment: 17,586 bytes, SHA-256 a746aab7f7569cbcb77cefcbccc28adccc6bf9d6c6b978ea79deddc660e41304. The full 48-artifact assessment bundle totals 1,786,402 bytes. Its captured evidence prefix equals the current original 152-event C4 source prefix, not merely its declared head.

Findings core remains cd29d5da638b6f1fe50b757aec3b5a9fa2ab3686c2baae1004734dbb07f3016c. Semantic review remains b947c30d5428099489fe1144593115a05448a66f42f75cb9e25aa4ba6b40a0af, attributed to /root/c4_safety separately from investigator /root/c2_critic. The sole focused and failed case is coverage-05-supported, category retrieval_gap, with no deferred cases. The original measurement identity and both original evaluation identities remain provenance of the diagnosis, not a newly measured retrieval result.

All 28 frozen code/fixture files, 18 local review/input artifacts, and three external C4 inputs still match gate 3898e8a6d1544d4d82976561de68de32b7d79d1d7e6c1b681f67f7493fe408b6. The C4 evidence store remains 152 verified events, head 292648c3d0c61932d90b44e48c42f1e16b3e689d5664d79f5b48231b3d1557df, and all 45 gated data/blob files retain exact bytes, sizes and modification times. Evidence and controller data/blob inventories also remained unchanged across this audit's read-only opens; SQLite shared-memory coordination files are outside that data inventory.

The dispatch start and finish receipts, authoritative completion, archived worker output, wrapper output and wrapper hashes agree. Worker output is 107,328 bytes; wrapper output is 114,822 bytes. Both processes returned zero; no timeout, recovery, delivery error or stderr was recorded. Postflight recorded all three checks successful and no errors; its controller state equals the independently read current controller.

Recorded assessment time is 8.978123750 seconds before locked completion revalidation; dispatch time is 10.411141083 seconds, and caller time is 10.885172583 seconds. These timings have different scopes and are not interchangeable. They are below the pinned 30-second assessment, 60-second dispatch and 75-second outer caller limits. Recorded model calls and external spend are zero.

Audit method: direct file/hash/manifest comparisons and exact Python 3.14 Ledger.open_readonly integrity/event/status checks. No dispatch, supervisor execution, retrieval, indexing, scoring, or edits to source/store/existing artifacts occurred. Only this new note was written. These are local retained receipts and integrity checks, not an independent execution witness or external timestamp.

Verified file SHA-256 values:
summary.json: 6b2c7f70227f38f6b0fe38f20ce592aaf2057505ae971123185cea1b028c9757
transition.json: ddd04459e376a5b5ee8689176073b906ac3a360efdd8c1edc629d348912c793b
dispatch-output.json: af3cd669081ed8e4649dba971b2ba08e26713c39d43a914d9ad52f8f74e66335
dispatch-caller.json: 962b5832e4cd17e4b7848647f28d5ec60c7a4f53111fadf7a606724e2de6fe71
dispatch-postflight.json: bc1a0d5c873e7e4246f2fd0b0f353ba9712d7292cc246b79888d025b23c4de5b
dispatch-start.json: bd0c9ca0fbd0c59be2219fb3662ad575abb79e193042d44b0d7ecc77cd8b87d3
semantic-review.json: b947c30d5428099489fe1144593115a05448a66f42f75cb9e25aa4ba6b40a0af
dry-assessment.json: 06af0096bd87059bf1d86bcc3a2f565834877dc9382e486097a0fc68639422dc

### Publication review: /root/c5_critic

Ready for publication. No actionable findings.

The public record accurately distinguishes the completed C5 diagnosis from the unexecuted follow-up, preserves the unchanged quality score, and explains the larger proposed retrieval budget. Counts, timings, hashes, and controller outcome reconcile with the saved evidence.

No private quotations or absolute private paths found. Graph relationships are consistent. The CI timeout change is justified without changing experiment budgets.

Confirmed 574 passing tests in 563.611 seconds and all 28 frozen input hashes unchanged. This review used files only; build and graph compilation results are parent-verified.

## Checks run, and what each covered
- Final engine suite:574 tests passed in563.611seconds with Python3.14.8/SQLite3.53.4; all26 production files unchanged from the recorded freeze. The existing CI job cap increases10→15minutes because the suite alone took9.4minutes; experimental30-second assessment/60-second dispatcher limits remain unchanged. No remoteCI claim.
- Helper14 targeted controls pass across initial13 successes and a corrected test-only TimeoutError expectation. Integration14 initial,9 post-byte-binding repair,4 legacy controls and4 final claim-integrity controls passed. These include a real fixed child dispatch/replay, captured-only execution, forged-origin failure, concurrent claims and live corruption rollback. Independent unguided review exercised7 focused controls without repeating the fullsuite.
- Reviewed caller passed12 prelaunch file/symlink collision controls and10 mocked execution/write-failure controls. Source3a690c2200f2d1516d7492c8ce97c6b431e5b5bc21816e95081cc0d82ac78e79; pinned-s invocation, postflight checks and no blind retries verified.
- Independent semantic review reconciled13 investigation-bound files,4 source blobs,82 raw projection rows,5 returned windows,4 unique support spans and2 alternative bundles. Discovery0/115 bytes is absent from returned windows but fully represented. Review attributes retrieval_gap without a ranking-cause, decomposition-benefit or answer-generation claim.
- Actual dispatch24ebeeb6eb0b4475a54f54cc171b6ffb completed support-diagnosis-20261126 once. Controller406events/12 completed/no unfinished; exact extension claim333+72captures+completion406. Current successorprepare_focused_support_followup has null metric/observed/target/probability/cost and scale false; prior quality remainsunmeasured.
- Captured47 input artifacts total1,768,816bytes;48 including report total1,786,402bytes. Original152-event source prefix and45 gated data/blob files remain unchanged. Captured17,586-byte report exactly matches canonical dry assessment, hash a746aab7f7569cbcb77cefcbccc28adccc6bf9d6c6b978ea79deddc660e41304. All28 code/fixture,18 local artifact and3 external input hashes match the pre-run gate. Independent actual audit verified authoritative events and receipts read-only, without retrieval/index/scoring.
- Recorded inner assessment8.978123750seconds excludes locked revalidation; dispatch10.411141083seconds and outer caller10.885172583seconds include wider nested scopes. Completion revalidation stayed within the30-second acceptance budget. Fixedprogramcalls/spendzero; builder/reviewer and full-step cost unknown.
- Final local site build passed43→66 content records with no removedslugs and bothnewpages present. Exactartifactb14df014dfd9e63d7f8ffe0d82db72a0f69e0ace73e8d4497bdc6e29e9844e50 retained/restored. ExistingbuildskipsTS/lint; noTypeScriptchanged. No browser/rendered/deployment claim.
- Knowledge compilation from committeddeb7a9a passed118nodes139edges22committeddocuments32bibliographicsources; payloadcc22f88a66fe75ca4701114298802f2338425401454ac4622a8ec31e5ecd3f99 retained. Graph records the observed diagnosis separately from proposed follow-up work.
- Managed secret/branch/metadata/date/documentation hooks and whitespace checks passed. Foreign root changes and SCI's canonical mathematics note remain untouched. Contingent next-probe protocol/design is retained privately; no new retrieval or falsely completed queue transition.

## Not verified
No protected cohort, independent timestamp/execution witness, causal ranking mechanism, general query-decomposition advantage, calibrated abstention, generated-answer quality, universal entity coverage, full-step monetary cost, deployment or scale promotion. Local source guards and process controls are trusted validation, not security isolation. Reviewer labels are attributed local attestations. The existing C4 freeze contract still limits captured studies; generic interval arithmetic does not relax it. Bibliographic graph sources remain metadata, not archived external content. No remoteCI, push or browser claim.

## Findings
- [medium] [fixed] Diagnosis accepted reformatted frozen cohort bytes because it checked parsed equality only; compare exact cohort/protocol/review digests with frozen bindings and test unchanged and reformatted originals.
- [medium] [fixed] Locked live-ledger verification could be caught as invalid supplied-origin evidence; verify integrity outside that handler, with rollback/no-new-event corruption control and preserved ordinary bad-input failure.
- [medium] [fixed] Caller output persistence could skip authoritative postflight after a collision or write failure; refuse all existing output artifacts before launch and always run postflight in an independent finally block.
