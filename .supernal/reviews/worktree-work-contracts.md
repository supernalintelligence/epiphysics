---
task: shared-retained-work-contracts
branch: worktree-work-contracts
reviewed_patch_id: 875e43b6e41ffa177c211e12a5d85cecd00fe092
reviewer_model: "Codex collaborators; model identity not separately recorded"
reviewer_agent_id: /root/work_contracts_critic
reviewer_output_sha256: 0e307c7ad27466c61f4a1ffcdac1a6a11c1aefe96f2a125485031b10f8dc01c1
author_session_id: ""
verdict: fixed
findings: {critical: 0, high: 2, medium: 0, low: 0}
resolved: {fixed: 2, skipped: 0}
skip_class: ""
skip_reason: ""
size: {files: 14, lines: 1373}
---

## Conclusion
Ready to land: yes
Both independently reproduced boundary findings are repaired and independently rechecked. This patch supports two retained-input fixture domains with shared supervision; it does not launch a prospective study or resume the original C12 trial.

## Checks run
The repaired version passed all 32 scoped tests in 20.932487 seconds of outer execution. Independent queue controls exercised absent, malformed and missing legacy decision inputs, the real supervised legacy refusal, and a two-run same-contract comparison in 3.261460 seconds. The safety recheck passed nine targeted controls plus the retained delayed-commit reproduction and a real-child CLI entry test in 21.026 seconds. Delayed completion, recovery, authoritative lookup and receipt persistence retain existing events while reporting failed timely delivery and disallowing automatic continuation. Runtime tests use newly owned invented fixtures; original failing attempts remain retained. Root verified all 14 final pins, parsed five changed document frontmatters, and confirmed the exact reviewed diff was unchanged after incorporating the unrelated mathematics commit 27c75f4. The source commit is c07ff51ec740ccc1c5dd767b04bf7a14df8b6b61. Its eight configured precommit checks passed. The project CLI reported a deferred rebuild of its own shared tooling because another writer held that tooling repository's lock; its existing compiled version ran these checks. This report does not claim that tooling was rebuilt.

## Not verified
No full project test/build, browser visual check, deployment, remote CI, actual C12 continuation, candidate execution, pilot registration/collection, external timestamp or prediction benefit was performed by this packet. Runtime checks are scoped to the affected fixture paths and targeted legacy controls. Postcommit checks observe late delivery; they cannot guarantee storage durability before an arbitrary deadline. Ledger status alone does not authorize continuation, and receipt-gated ownership is not implemented. The parent must survive and the caller must inspect its returned timing/delivery status. Identity/authorship strings are declarations, and two-domain conformance is not universal generalization. The prospective declaration and its separate review are outside this patch.

## Findings
- [high] [fixed] Malformed legacy decision input caught the work-family refusal and could append a legacy failure over the work successor; unconditional preclaim and locked checks now refuse without writes.
- [high] [fixed] A slow terminal commit could cross the original deadline and still return ordinary assessed success; post-operation observations now report deadline failure, retain durable history and disallow automatic continuation, with the attainable guarantee explicitly narrowed.

## Reviewer report
# Unguided reviewer: /root/work_contracts_critic

# Independent repair review

Outcome: original queue-isolation finding closed. No additional actionable findings in the repaired runtime, tests, and documentation within the limits below.

## Frozen identities

Base and reviewed worktree HEAD: 9d598f2301d9eafdb56e54a8862e1a14d73b3d61.
Manifest SHA256: 828989b016f8b5e433dacac38bcaa527067e0c1b1f5e324a927ea54ffa5d83ca.
Full 14-file review diff SHA256: 4fdb9f5396ebf8cd57e6d013e61c9a80bb9c7b159f6be97e8ad2e592b026be42.
Repair diff SHA256: e51ca8e96dae78c437f796387128b0bd4f3ea2a17c5e9d301e4d56407302b364.
All 14 file hashes plus these three artifact hashes matched before and after review; see pins-before.json and pins-after.json. Intent-to-add metadata changed during review, without source changes. The separately advanced shared branch has no overlapping file change and was not the test target.

## Independent evidence

checks.py reuses only the previous independent fixture constructors, authors new inputs, and creates fresh explicitly owned stores under this directory. No old store was reopened. The original failing reproduction and its complete outputs remain at ../../review-critic/ and were not overwritten; original-evidence-hashes.json records their current identities.

After a real work dispatch, legacy assess was called with no decision input, malformed invented JSON {}, and a missing decision input. All three raised the work-boundary refusal without changing the five existing events or the queued successor. The actual fixed legacy subprocess was then dispatched with invented policy/suite/supplied output bytes and the malformed decision input. It returned failure with no_owned_claim, no authoritative transition, and exactly the same five events. No candidate execution was used.

The independent two-run comparison control also passed: supplied abstention then a supplied conforming reference yielded numerators zero then one under the same measurement identity, with real supervised child execution and accepted transitions in a new owned fixture store.

Both checks passed. Outer execution time: 3.261460374982562 seconds of the 45-second allowance. Complete stdout, stderr, execution receipt, results, invented inputs, ledger states and dispatch receipts are retained here.

## Repair and blast radius assessed

_check_legacy_queue now hard-refuses outside the input-error catch before claiming and again in the locked validator. Malformed decision preparations cannot downgrade queue ownership refusal into a durable legacy failure. Legacy requests with their own queue retain the previous assessment flow; work preparation continues to reject legacy predecessors.

The repair adds observation checks after terminal commit, recovery, authoritative lookup and receipt persistence. It reports work_deadline_exceeded and disallows automatic continuation on detected overrun while preserving any committed transition; main returns a nonzero status for that result. The supporting docs explain administrative durability versus observed timely delivery, lack of arbitrary I/O bounds, and the future consumer's responsibility to enforce continuation eligibility. The review also read the supervisor-status and stepwise-loop additions; those are explicitly dated observations, not fresh research execution or deployment claims.

Coverage limits: this reviewer independently executed the queue regression and successful comparison chain only. Delayed-commit, delayed-recovery, delayed-lookup and delayed-receipt behavior was inspected in code/tests/retained validation claims, not independently rerun here; the parallel safety review owns that targeted behavioral check. No full-suite, site build, browser/deployment, actual study continuation, candidate/scheduler execution, hostile-host timing guarantee or network action was performed. No source changes or commits were made.

## Doc-only landing supplement

Reviewed the supervisor-status refresh against status-before-refresh.md and the prior reviewed state. No new actionable issue. The refresh accurately records the 32-test repaired validation, the independently closed queue and deadline findings, integration still pending, and the separate mathematics commit reported by the supervisor. It explicitly preserves the caller-responsibility and timing limits. The prospective declaration review is a supervisor-reported activity, not a claim that this reviewer independently audited that study or executed it.

Exact landing manifest SHA256: 68933059a19f51a4fe8d27df2967001d2740d7f5c023a2c9d2947867cf9a7ba3.
Exact landing full diff SHA256: 4121ec6e4510109209842ec2587db842c33d1f4781497305d9a0da8a063eef63.
Exact refreshed docs/planning/runs/2026-11-26-supervisor-status.md SHA256: b19dd080f125ac31a34320656cbc716bd11b5c15129e66fbb8641d56b3bd04c5.

All 14 landing file hashes and both landing artifact hashes match. Exactly that one status document changed; all other 13 file pins remain identical to the repaired review. The saved pre-refresh status matches its previous pin. The unmodified preceding review report is retained separately as review-before-status-refresh.md; the original failing test evidence remains intact. See landing-supplement-pins.json. No additional tests, runtime changes, actual stores, network access or commits were performed for this supplement.

# Safety reviewer: /root/navigation_repair_safety

# C13 boundary repair: independent safety recheck

No additional actionable runtime finding was identified in the reviewed repair under root's expressly narrowed contract: precommit validation plus postcommit timing observations, without a guarantee of deadline-bounded durability. The original strict-publication finding is addressed by honest late-delivery classification, not by making the impossible claim that a postcommit check can undo durable acceptance. Root remains the adjudicator.

## Evidence and result

Nine selected frozen tests passed (15.656 seconds unittest; 16.167131 seconds outer). Exact commands/environment and unabridged output are retained in `command.json`, `tests.stdout`, `tests.stderr` and `tests-result.json`; all invented fixture stores remain under `fixtures/`. Selection covered malformed legacy JSON queue isolation, completion commit, failure recovery commit, authoritative read, receipt publication, original elapsed deadline, postcommit lost delivery, an ordinary real CLI dispatch/duplicate refusal, and report publication failure.

The original independent `boundary_controls.py` was copied byte-for-byte into this new review directory; the earlier report, script, failed reproduction and fixture stores remain unchanged in the sibling original `review-safety/`. Exact source script hash and copy assertion are retained in `original-reproduction-command.json`. Its actual child emitting valid provisional JSON and then exiting 9 still produces only an owned failed transition and accepts no measurements. Its original delayed-terminal-commit reproduction now returns `work_deadline_exceeded` after 1.5660898340283893 seconds for `max_seconds=1`, with a 1.0580207500024699-second injected commit delay. One already durable `improvement_completed` and its accepted measurements remain intact; delivery is failed, continuation is disallowed, and no replay or second terminal event occurs. This is the intended changed result; durable completion is not relabeled as absent.

An additional independent CLI entry control (`cli_boundary.py`) invokes the actual `improvement.main` argument parser/entry and real fixed subprocess child on a fresh invented store. It delays the first finish-receipt write by 1.05 seconds under a one-second declaration. The first attempted receipt is `assessed`, then the correction is `work_deadline_exceeded`; the actual harness process exits 2, emits the structured late result, reports failed delivery and disallows continuation. Exactly one authoritative terminal event is retained. This exercises the CLI return mapping, not just a mocked dispatch result. The command, standard streams, process receipt, exact entry argv, write observations, events and store are retained under `cli-*` and `cli-late-receipt/`.

Aggregate test process time was 21.026213 seconds, below the authorized 45-second cap. Per-launch times: {"cli-receipt.json": 2.055828124983236, "original-reproduction-receipt.json": 2.8032537910039537, "tests-result.json": 16.167130834015552}. The CLI control's exit 2 is its expected negative-delivery result; the other launchers exited 0. No test failure was discarded or relabeled.

## Boundary review

- `work_runner.py:232-235` now observes the original deadline after the atomic context has committed. An expired result raises before ordinary return; the durable event remains available to authoritative inspection.
- `improvement.py:1234-1238` observes recovery publication after the existing helper returns. The later delivery observation also prevents a delayed authoritative lookup from restoring ordinary success.
- `improvement.py:1263-1287` classifies delivery immediately before and after receipt persistence. A detected crossing returns `work_deadline_exceeded`, `deadline_status: exceeded`, `publication_status: timely_delivery_not_established`, `delivery_status: failed`, `automatic_continuation_allowed: false` and `continuation_status: requires_inspection`. The correction preserves the original event, request, process facts and deadline rather than issuing a replacement terminal event or retry.
- `improvement.py:1337-1341` maps the explicit late result and caught publication errors to nonzero CLI status. Ordinary publication failure and already completed delivery failure remain visibly unsuccessful.
- `improvement.py:754` and `:782` now enforce work-family isolation outside the recoverable invalid-input catch, both before claim and under the claim lock. The selected malformed-input regression independently left every event and the queued successor unchanged, correcting the previously separately reported bypass.

The returned acceptance object can still contain accepted measurements or authoritative completion after a late read/write, because those are real retained facts. Successful parent delivery and timing fields are required for continuation; authoritative completion alone is intentionally insufficient. No new successor-gating schema or automated executor was added. This review does not claim the raw ledger prevents a caller from deliberately ignoring the delivery contract.

## Documentation and limits

The updated README, planning protocol, experiment record and stepwise-loop paragraph accurately disclose the narrowed guarantee: no arbitrary commit/disk latency guarantee; durable history remains; original budgets do not refresh; no automatic retry; saved receipt or ledger state alone is insufficient; future automatic consumers require their own gate. The planning protocol explicitly excludes later console/output stalls, host failure and failed receipt correction from proof of successful delivery. An error during correction may leave an older saved receipt; actual successful returned parent delivery is therefore required.

Documentation freshness observation, not a new runtime defect: `docs/planning/runs/2026-11-26-supervisor-status.md` is explicitly checkpointed at 23:29 UTC and still describes 27 builder tests with repair in progress. That is a truthful historical checkpoint but is stale relative to this frozen repair's 32-test builder run and completed review. Refresh it when reporting integration/current status; do not present the 23:29 worker table as a live worker inventory. The updated work-contract run record correctly distinguishes the earlier 27-test run and subsequent 32-test repair validation.

No actual improvement/C12 store, actual trial/candidate program, scheduler or network was accessed. No source edit, commit, migration, candidate retry or real study stage occurred. Test doubles model delayed operations; they do not establish real disk latency or hostile-host isolation. Existing direct-child supervision is not descendant containment. No broad unaffected suite or unrelated build was repeated, and no claim of prospective science, authenticated roles, new powers from data, or actual C12 continuation is made.

## Frozen identity

Worktree: `/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/work-contracts`; review base `9d598f2301d9eafdb56e54a8862e1a14d73b3d61`. Manifest SHA256 `828989b016f8b5e433dacac38bcaa527067e0c1b1f5e324a927ea54ffa5d83ca`; full review diff SHA256 `4fdb9f5396ebf8cd57e6d013e61c9a80bb9c7b159f6be97e8ad2e592b026be42`. All 14 frozen file pins matched before review controls and remained unchanged afterward. The unchanged `store`, `manifests` and `assertions` dependency bytes were also recorded and verified stable. Full hashes are in `pins-before.json` and `pins-after.json`. Applicable worktree CLAUDE.md was reread; no nested instructions were found in reviewed engine/docs paths. Shared-branch SCI activity was not part of this frozen review.

## Read-only status refresh acknowledgement

After the frozen runtime review above completed, root supplied a documentation-only supplement. I read the exact diff against retained `status-before-refresh.md` and verified all 14 landing pins. Only `docs/planning/runs/2026-11-26-supervisor-status.md` changed; the other 13 frozen files remain identical. The refreshed status SHA256 is `b19dd080f125ac31a34320656cbc716bd11b5c15129e66fbb8641d56b3bd04c5`; supplementary manifest SHA256 is `68933059a19f51a4fe8d27df2967001d2740d7f5c023a2c9d2947867cf9a7ba3`; supplementary full diff SHA256 is `4121ec6e4510109209842ec2587db842c33d1f4781497305d9a0da8a063eef63`.

This resolves the documentation freshness observation above: the 23:36 checkpoint now says 32 repaired builder tests, independently checked fixes and integration pending. It accurately states that observed late delivery disallows continuation while retaining durable history, with no receipt-gated ownership or arbitrary disk-latency guarantee. It also reports the prepared pilot declaration under separate review and the unrelated shared-branch mathematics commit, as root-supplied status; neither was independently investigated in this safety recheck. No runtime source changed and no additional test was needed or run. The original frozen scope/results and earlier reproduction remain preserved; `supplement-pins.json` records the exact acknowledgement.
