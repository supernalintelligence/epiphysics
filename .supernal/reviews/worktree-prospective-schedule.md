---
task: prospective-deterministic-calendar
branch: worktree-prospective-schedule
reviewed_patch_id: 4a08df07f3c49e508e7f364246859ee33a3030bc
reviewer_model: "Codex collaborator; model identity not separately recorded"
reviewer_agent_id: /root/prospective_schedule_builder/schedule_critic
reviewer_output_sha256: a6ba97b0fa70fdfa33a4aaf533687ec13d28f35e670ed87f526fd28a917cd63a
author_session_id: ""
verdict: pass
findings: {critical: 0, high: 0, medium: 0, low: 0}
resolved: {fixed: 0, skipped: 0}
skip_class: ""
skip_reason: ""
size: {files: 7, lines: 612}
---

## Conclusion
Ready to land: yes
The pure calendar component preserves the fixed relative schedule, all absolute endpoints and complete prior/opening membership. Independent review found no actionable findings; calculation and validation confer no registration or execution authority.

## Checks run
The builder passed 14 tests with zero failures/errors/skips, retaining twelve invented calendars and 649 expected refusals. Its outer subprocess took 1.500436708 seconds. A separate critic passed 45 independently authored controls, including 1,320 endpoint comparisons and 31 expected refusals, in 0.187769209 seconds. Both used Python 3.12.9. Root inspected the source and review, verified all 1,377 frozen file/evidence pins and the exact reviewed diff, and captured 97 unrelated shared files before landing. Git whitespace and all eight configured precommit checks passed. Source commit: a95e381e6263a64b1feebb5b1b04774c2d3b9778. These subprocess times exclude total agent effort and are not efficiency or cost estimates.

## Not verified
Tests require the exact private declaration through EPIPHYSICS_SCHEDULE_DECLARATION; default discovery without it skips the class and supplies no conformance evidence. Invented calendars establish no actual registration, external clock assurance, receipt integrity, durable binding, source selection, collection, runtime start-window compliance, producer delivery, forecast skill or five-family generalization. No original C12 or C17 experiment replay, actual study, source request, model call, scheduler, full project build, browser check, remote CI, push or deployment occurred. Whole-agent effort, cost, CPU and peak memory remain unmeasured. The source-freeze documents intentionally retain their historical review-pending wording; this record supplies subsequent acceptance.

## Findings

## Reviewer report
# Independent adversarial review — prospective schedule

No actionable findings were found in the reviewed change. This is a pass for the pure calendar component within the stated scope, subject to the supervisor's separate adjudication; it is not approval of a pilot, registration, collection, runtime, or landing operation.

## Reviewed identity

- Reviewer agent: `/root/prospective_schedule_builder/schedule_critic`.
- Worktree: `/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/prospective-schedule`.
- Base: `a24f61277178e649c27031804ac127db88390ab7`.
- Reviewed `git diff a24f61277178e649c27031804ac127db88390ab7` and `git diff --staged`; staged diff was empty.
- Working diff SHA256: `ffa1c8bba7bc7132c4a722798d4514a25d78987b3327062f614332bbba95563b`.
- Supplied review-freeze pins SHA256: `1639e948f0daf1491ffa17986408c99d81e83c216d262eeb0bf6779811e1e9b9`.
- Candidate source SHA256: `2d53ca07f55f2cd2eeed382e94d00556c01dda6f53982baaf0b9cf50d6e389c6`.
- Current diff and staged bytes matched the frozen artifacts before controls and after review. The twelve checked changed/dependency/declaration file pins matched. This did not revalidate every historical artifact listed in the larger freeze manifest.

## Blast radius and source evidence

The new API has no existing production caller: repository references are its own tests and documentation. No changed state is shared with an executor. The meaningful future consumers are a receipt/instance binder and the existing raw question-evidence contract.

- `engine/epiphysics/prospective_schedule.py:96-109` authenticates the exact bounded declaration bytes before parsing and converts only the declared offset fields, preserving other values. The hash pin makes this intentionally specific to one declaration rather than an incomplete general-purpose declaration validator.
- `engine/epiphysics/prospective_schedule.py:111-124` uses the complete declared HTTP inventory and each release opening time. Its 1/5/9/13 prior/opening sets include the preceding window's Pj.3. The downstream grammar at `engine/epiphysics/prospective_inputs.py:306-329` and `docs/planning/prospective-inputs.md:53` requires unique `id`/`nominal_at` slot records and complete prior/opening membership; the generated slot records meet that contract. A future binder must still map the outer `opening_poll_id` to the raw question evidence's `opening_slot_id` and bind actual receipts.
- `engine/epiphysics/prospective_schedule.py:125-145` preserves declared policy/budget data and returns explicit false registration/launch/execution flags. `docs/planning/prospective-schedule.md:34-36` accurately keeps actual receipt validation, durable binding, clock monitoring, and execution gates separate.
- `engine/epiphysics/prospective_schedule.py:148-156` compares canonical serialized typed values, so booleans cannot pass as integers and neither pruned membership nor altered authorization is accepted. JSON object order and whitespace are intentionally insignificant.
- `engine/epiphysics/prospective_schedule.py:66-86` bounds UTC spelling and uses exact integer-second arithmetic with explicit calendar-overflow refusal. Full-year-range origins are mathematical inputs only.
- `engine/tests/test_prospective_schedule.py:129-134` explicitly skips when the private normative declaration is absent. Thus default test discovery without that fixture is not conformance evidence. This is documented in the implementation record and was not treated as a new failure.

All paths above are relative to the worktree specified under Reviewed identity. The source and docs were read only; no fix, refactor, commit, or landing was performed.

## Independent controls actually executed

One independently authored retained control process ran once. It imported only the new calendar module; it did not import the builder test module, normalizer, oracle, representation candidates, or store. Expected endpoint tables were derived from separately written policy formulas and manual Gregorian day/month rollover arithmetic, without `datetime`, `timedelta`, epoch arithmetic, or production helpers. Those expected tables and the control/source/declaration hashes were retained before the first calendar call.

All **45 controls passed**, with **zero unexpected failures**:

- Eight invented calendars covering a year divisible by 400, a non-leap century, ordinary leap-year and month/year transitions, microsecond precision, year 1, and the final valid audit-horizon origin. Each checked all 164 record endpoints plus the audit deadline: **1,320 timestamp comparisons** total, with complete identities, unchanged non-time values/policies/budgets, membership, and false authority flags.
- Three accepted serialization cases: changed object order/whitespace, an escaped key, and valid JSON padded to exactly 131,072 bytes.
- Thirty-one expected refusals: twelve semantic changes (types, source policy, nullable field omission, array order, membership timing/loss/opening, canonical time spelling, producer deadline, authority, and budget); eight parser/boundary cases (131,073 bytes, escaped duplicate key, lone surrogate key, oversized integer lexeme, decimal zero, BOM, depth 3,000, UTF-16); seven invalid/overflow origins; and four exact-type/declaration-byte controls.
- Two equivalent-origin controls and one unchanged-runtime-settings/input control.

No failing first attempt exists to repair. Every input/result is retained with the original script and stdout/stderr. The builder's existing test suite was not rerun. Its retained receipt and stderr were inspected: 14 tests, zero failures/errors/skips, 649 refusal files and twelve calendar files agree with the new documentation. Those are attributed builder evidence, separate from the independent results above. `git diff --check a24f61277178e649c27031804ac127db88390ab7` passed.

## Timing, runtime, limits, and unverified scope

The independent test/control subprocess consumed **0.18776920897653326 seconds** total, measured with the outer runner's monotonic clock; its timeout was 30 seconds and the total reviewer allowance was 90 seconds. This was the only test/control subprocess. Read-only inspection and evidence writing are outside that subprocess measurement. No claim about whole-agent elapsed effort is inferred from it.

Runtime: `/Users/ianderrington/miniconda3/bin/python`, Anaconda Python 3.12.9, Clang 14.0.6, macOS 26.5.1 arm64. Integer digit guard remained 4,300 and recursion limit remained 1,000. The depth-3,000 input parsed on this interpreter and refused with `schedule_mismatch`; it does not establish a portable nesting maximum. Whole-agent effort, cost, CPU, and peak memory are unmeasured/null. Study-program network/model calls and spend were zero.

No actual study, C12 artifact execution, earlier comparison rerun, source collection, registration, network request, scheduler, producer, or representation candidate was run. No registration receipt, retained post-binding, real clock honesty, start-window compliance, execution authority, prediction, or scientific advantage was established. Other interpreters and concurrent-host behavior were not tested. The source code's bounded pure interface was reviewed, not a security boundary against arbitrary host compromise.

Reviewer receipt: `/Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/prospective-schedule-v1/independent-review-v1/reviewer-receipt.json`.
