---
task: prospective-first-attempt-capture
branch: worktree-prospective-capture
reviewed_patch_id: aa48069fe1049cd60a832c5666c16a4572080216
reviewer_model: "Codex collaborator; model identity not separately recorded"
reviewer_agent_id: /root/submission_capture_builder/capture_critic
reviewer_output_sha256: f1f59fac4f5c1bfdff12eddb92e12dde55df7c7e4dbc9f64edfb01602efa9ab8
author_session_id: ""
verdict: fixed
findings: {critical: 0, high: 3, medium: 11, low: 0}
resolved: {fixed: 14, skipped: 0}
skip_class: ""
skip_reason: ""
size: {files: 7, lines: 3506}
---

## Conclusion
Ready to land: yes
Root accepted this exact patch for normal local integration after reading both final reports and verifying 31 critic and 40 guided-review artifacts. Nine independent review rounds resolved 14 deduplicated findings; neither final reviewer reports an open actionable finding. The original failing regression remains recorded below and is not relabelled green.

## Checks run
Source commit `04ee0651159a965c2139496707d7760d0db0ffa8` contains exactly the seven reviewed paths. Every committed and working-tree source hash matched the R8 freeze after the normal managed commit. Its eight configured pre-commit checks passed; the tool explicitly skipped worktree TS/build and Markdown-link checks. The generated doc-validation.log was copied into the private integration evidence and removed from the worktree. The normal finish dry run supplied patch ID `aa48069fe1049cd60a832c5666c16a4572080216`. No guard was bypassed and no producer/control cohort was repeated during integration.

R8 fresh controls passed 3/3 with actual fixed workers, positively observing and consuming a pending first self alarm and preserving its distinct phase through normal return, a first interruption, and a later final alarm. The original R8 full-module regression remains **90 pass / 1 error**: the old receipt-always-return fixture reached a final deadline, and its actual cleanup disposition was not instrumented. Root accepted a separate test-only correction at the unchanged 0.15-second execution / 0.5-second cleanup limits. Its distinct R8b focused run passed once on the returned-receipt branch, with exact child reaping, 26 tracked descriptor lifetimes retired, caller state restored and zero fixture recovery. The other 90 cases were not replayed. A final deadline may follow an actual terminal commit; the corrected test verifies any retained receipt and terminal event without inventing a returned publication observation.

Final independent critic controls passed 2/2 with real workers; final guided controls passed 3/3 with labelled fake children and real local signal/SQLite operations, including a terminal commit followed by final alarm. Both reviewers verified all 9,071 supplied pins and unchanged complete diff. Builder execution accounting, including freeze/hash intervals, is 92.131679790 / 180 seconds before integration commands; whole-agent time and cost remain unknown. All previous first failures, warnings, source snapshots, reports and adjudications are preserved in `.supernal-local/prospective-capture-v1/`.

The final freeze SHA-256 is `ef78f04074e477c4a16747821bec03d9f8ff3e8c17daea4e734f59589e7990e9`; full reviewed diff SHA-256 is `32aa238639b006a287f3a98da6de15e34e784348fa21e23dd2166e180fa745d2`. Root's `adjudication-r8.json` supplies the finding reconciliation: R1 SIGINT child ownership is part of the original constructor-ownership class; R6 final-dispatch interruption loss reopens the original R2 priority class. The regression test-design correction is a validation limitation, not an invented severity finding.

## Not verified
The original R8 full-module run is still a failed run; there is no claim that a final complete module rerun passed. R8b's real-worker final-deadline branch remains unexercised. Actual Python 3.10 execution is not established; the deterministic trace harness requires Python 3.11 or later. The trusted main-thread POSIX and single-connection assumptions do not establish hostile-code containment, descendant isolation, a nonreturning kernel-call bound, host-loss recovery, or exhaustive asynchronous safety. No production caller, real registration or acceptance, source selection, network/model call, historical queue/cohort replay, new quality/outcome evidence, continued automation authority, site build, browser validation, remote CI, push or deployment was introduced. This is local capture evidence and local Ledger/instance/channel firstness, not a complete prospective pilot or predictive/business result.

## Findings
- [high] [fixed] Constructor/spawn child ownership, including the later supported SIGINT manifestation; exact owned PID publication precedes unmasking.
- [medium] [fixed] Cumulative clock integrity preserves observed middle/EOF inconsistencies with bounded memory.
- [medium] [fixed] Wait-status certainty retains actual owned waitpid status and treats unavailable ownership/status as unknown.
- [medium] [fixed] Descriptor acquisition and retirement preserve exact ownership and do not blindly retry uncertain numeric FDs.
- [high] [fixed] Cleanup resumption continues only unfinished owned cleanup within the original reserve after supported admission or cleanup interruption.
- [medium] [fixed] Caller-interruption priority survives later final alarms and final dispatch, including the reopened R6 manifestation.
- [high] [fixed] Production exception handling no longer depends on an API absent from the declared Python 3.10 range; actual 3.10 execution remains unverified.
- [medium] [fixed] Signal handler installation and retirement preserve caller state and observed pending alarms.
- [medium] [fixed] Ambient caller exceptions are excluded from locally owned cancellation and remain unchanged.
- [medium] [fixed] Caller database busy-timeout ownership restores the exact observed timeout after supported interruption.
- [medium] [fixed] Cleanup-entry ownership is installed before acquisition and covers first retirement-instruction cancellation.
- [medium] [fixed] Local independent Ledger append recovery retires uncommitted transaction/flag state without undoing an actual commit.
- [medium] [fixed] Captured native-close uncertainty survives deadline/interrupt selection with bounded deduplicated metadata and explicit truncation.
- [medium] [fixed] A positively observed and consumed first pending alarm survives later interruption, with truthful phase and earlier-observation evidence.

## Guided reviewer report
Reviewer: `/root/submission_capture_builder/capture_safety`.
Exact report file SHA-256: `a109f075b2d89a98f06775465505df5e27454817b9b49c8d32169a945c5d2a04`. The unchanged report text follows in a fence so its internal headings cannot be confused with the author findings above.

```markdown
# C23 R8/R8b guided safety review

Reviewer `/root/submission_capture_builder/capture_safety`. **No actionable finding in the frozen R8/R8b patch.** The R7 consumed-pending-alarm finding closes. This conclusion retains the execution and coverage limits below; it does not authorize landing or prospective use.

## Full boundary and closure

Reviewed complete seven-path diff and empty staged diff against base `0bd9bb1d02fd4fd7efd0c8f05c756dc5a2154f25`, including root-owned DAILY_LOOP/TODO, all R8 production/test changes, prior reviewed boundary, and immediate Ledger/worker/readiness/exception consumers: **3505 insertions, one deletion**. Public capture API and shared Ledger remain unchanged; no production caller was found.

`enter_cleanup` now records the observed and consumed nonfinal alarm inside the existing handoff (`prospective_capture.py:414–416`). Fresh interruption **immediately after unmask, before admission returns**, preserves the identical first KeyboardInterrupt and exact `cleanup_admission/final=false` evidence. The exception receives a separate copy of the bounded first-pending snapshot.

The later-phase controls establish distinct facts:

- Pending consumption at handler retirement updates latest phase to **signal_retirement/final=true**, preserving the earlier **cleanup_admission/final=false** snapshot and the same first KeyboardInterrupt.
- A real self final alarm immediately after **actual SQLite terminal commit** yields **owned_alarm/final=true** with the earlier snapshot. Both committed events and exact receipt hash remain, with **no returned publication observation**, no later raw write/fsync, and null quality/outcome. This is a fake-child control with real database commit, not fresh real-worker coverage of the R8b branch.

All cases use exactly **one cleanup reserve**. Existing first-interruption priority, close uncertainty/deduplication/truncation, exact-frame/record provenance, normally completing helper behavior, PID/status/FD retirement, exclusive firstness, transaction recovery, clock accumulation and receipt-versus-publication boundaries remain intact in the inspected paths. No extra guard, producer restart, invented observation time or global cancellation state was introduced.

Caller-state inventory: exact SIGALRM handler, disabled owned timer, original signal mask including SIGUSR2, **7841 ms** busy timeout, idle transaction/append flag, unchanged ambient caller exception, and owned raw descriptors. All restore with zero fixture recovery. Native/kernel nonreturn, host failure, repeated forced interruption and descendant isolation remain unresolved limits.

## R8b test correction assessment

Read both [original adjudication](../r8-regression-adjudication.json) and [superseding design](../r8-regression-design-accepted.json), the original retained failure, corrected method and tracking helpers. The correction preserves the API's permitted receipt-or-final-deadline contract. It keeps **0.15 s execution / 0.5 s cleanup**, positively triggers the first alarm after owned spawn, and requires exact native PID/status, no child/FD recovery, restored caller state and no invented EOF on **both** branches. Unknown cleanup fails. A committed terminal event is verified against saved bytes even if return is lost; no returned publication is inferred.

The original full-module result remains **90 pass / 1 error**, **27.313479291973636 s**, 91 methods, 46 real workers/29 fake calls. Its final deadline occurred while receipt open unmasked an alarm. The old control retained no native wait/FD/caller-state trace, so its cleanup disposition and cause remain **unknown**; this review does not infer successful cleanup or host slowdown.

The separately renamed R8b focused method passed once in **0.2269522079732269 s**. Its retained branch is **returned_receipt**: PID **86694**, actual raw wait status **9**, **26** tracked FD lifetimes retired, caller state restored, no fixture recovery, and the saved receipt matches the actual terminal commit. **Its real-worker final-deadline branch remains unexercised.** The other 90 methods were not replayed. The repaired focused result does not relabel the original regression green.

## Fresh independent controls

All expectations, script, source and exact runtime pins froze before the sole execution. **3/3 passed**, three API calls, zero harness errors.

| Fresh identity | Inner seconds |
| --- | ---: |
| `pending_interrupt_at_admission_unmask` | 0.13540404196828604 |
| `pending_then_final_after_terminal_commit` | 0.10326579102547839 |
| `pending_then_interrupt_then_retirement_pending` | 0.14347404101863503 |

Three fake-native children; **zero real workers**. SQLite, files/pipes and seven exact-self signals (**two SIGINT, five SIGALRM**) were real. **82 tracked descriptor lifetimes** retired; zero FD/caller-state recovery and empty stderr. Controlled self-signal timing does not estimate spontaneous races or native timing bounds.

Outer subprocess **0.5239079589955509 s**, 30 s cap, exit 0. Inner total **0.38214387401239946 s** is not double-counted. Cumulative guided controls **3.903980832954403 s**; remaining original allowance **86.0960191670456 s**. No whole-agent cost/time claim.

Exact runtime: CPython **3.12.9**, `/Users/ianderrington/miniconda3/bin/python3.12`, SHA256 `cb308fc2b24b28768f0a9b486b8054b32db80f5a0d7fe86929f64f2b17130f26`; SQLite **3.45.3**, macOS **26.5.1 arm64**. Harness frame metadata requires 3.11+; **actual Python 3.10 execution remains unverified**. Builder R8's three fresh real-worker passes (**0.6929769999696873 s**) were inspected only. No historical cohort, regression method or original failure was rerun.

## Integrity and preserved history

Final audit verified **9071/9071 supplied and 30/30 independent pin records unchanged**, zero missing; **2.593712083005812 s** read-only audit, outside controls.

- Supplied freeze: `ef78f04074e477c4a16747821bec03d9f8ff3e8c17daea4e734f59589e7990e9`
- Full diff: `32aa238639b006a287f3a98da6de15e34e784348fa21e23dd2166e180fa745d2`
- Empty staged diff: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- Adapter: `3628b87cbe4234b806cae2bef82fd59dab7de3caee66ce797b7d20ca180d306d`
- Tests: `643356524c7aa7d57026743660987e812596d5129a0d83f31f331b15a22dc62e`
- Independent freeze: `70123b2d07ea94dacfd1a2a47329146f1fa363cf78be6c012c82f40e8d2df783`

[Receipt](first-process-receipt.json), [counts](summary.json), [audit](final-pin-audit.json), [expectations](expectations.json). Unchanged reports: [v1](../independent-safety-v1/report.md), [R1](../independent-safety-r1/report.md), [R2](../independent-safety-r2/report.md), [R3](../independent-safety-r3/report.md), [R4](../independent-safety-r4/report.md), [R5](../independent-safety-r5/report.md), [R6](../independent-safety-r6/report.md), [R7](../independent-safety-r7/report.md). All previous failures/harness errors remain intact. No source/docs/tests edits, network/model/pilot/queue action, commit or landing.
```

## Reviewer report
# C23 R8/R8b independent full-diff review

Reviewer: `/root/submission_capture_builder/capture_critic`. **Zero actionable findings: critical 0, high 0, medium 0, low 0.** The consumed-pending-alarm evidence omission is addressed at the reviewed boundaries. The original R8 software regression remains **90 passed / 1 error**; the later renamed test's pass does not replace that outcome. Root retains adjudication authority.

## Complete scope and integrity

Reviewed complete `git diff HEAD` and empty staged diff against `0bd9bb1d02fd4fd7efd0c8f05c756dc5a2154f25`: seven paths, 3,505 insertions and one deletion. Scope includes DAILY_LOOP/TODO, 252-line contract, 676-line run history, complete 790-line adapter, fixed 35-line worker, 1,748-line tests and immediate consumers. The entire adapter and contract, current additions/corrections, source dependencies and retained current results were read; previously reviewed unchanged sections were checked against retained complete diff bytes. Applicable CLAUDE.md and adversarial instructions were read. This was not restricted to earlier finding labels.

| Identity | SHA256 |
|---|---|
| Complete diff | `32aa238639b006a287f3a98da6de15e34e784348fa21e23dd2166e180fa745d2` |
| Empty staged diff | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| Original R8 freeze | `ef78f04074e477c4a16747821bec03d9f8ff3e8c17daea4e734f59589e7990e9` |
| Production adapter | `3628b87cbe4234b806cae2bef82fd59dab7de3caee66ce797b7d20ca180d306d` |
| Corrected tests | `643356524c7aa7d57026743660987e812596d5129a0d83f31f331b15a22dc62e` |

[Final integrity audit](/Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/prospective-capture-v1/independent-critic-r8/post-review-integrity.json): **9,071 original pins and 9,075 independent pre-execution pins unchanged**, zero mismatches, matching complete diff and empty staged diff. All earlier evidence and failures remain immutable; DAILY_LOOP/TODO identities remain unchanged from R7.

## Findings, closure, and blast radius

Review covered source/runtime/worker binding, input and output limits, exclusive claim admission, raw descriptor and native child ownership, wait-status truthfulness, bounded cancellation handling, exact signal-state restoration, SQLite append/timeout recovery, sticky clock observations, retention checks, and the distinction between durable receipt, terminal commit and returned publication observation.

At [cleanup admission](/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/prospective-capture/engine/epiphysics/prospective_capture.py:410), a positively observed pending SIGALRM is natively consumed and recorded within the existing mask before unmasking. The nonfinal deadline has the actual cleanup_admission phase; no fabricated observation time is introduced. At [handler retirement](/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/prospective-capture/engine/epiphysics/prospective_capture.py:430), a later pending alarm records signal_retirement while retaining the first snapshot. [Exception annotation](/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/prospective-capture/engine/epiphysics/prospective_capture.py:110) copies that bounded snapshot and reports the latest deadline phase separately. Earlier scope ownership checks, four retirement guards, no-retry native-close uncertainty, first-interruption priority and one cleanup reserve remain intact. Shared consumed evidence still does not cause a normally completing helper to throw.

The immediate consumers are escaping exception inspectors and future callers of capture_first_delivery. Repository search still finds only the focused test caller, with no production activation or new event consumer. The fixed producer/worker, shared Ledger implementation, score/resolution filters, generic event verification/export and historical dispatch/navigation remain unchanged. Append recovery is local to the supplied idle independent connection. Existing receipt semantics remain separate from quality, obligation outcome and continuation authority. No additional actionable defect was established across this boundary. Prior closure history remains in unchanged [R7 critic](/Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/prospective-capture-v1/independent-critic-r7/report.md) and [R7 safety](/Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/prospective-capture-v1/independent-safety-r7/report.md) reports.

## Retained regression evidence and correction

Read both [initial adjudication](/Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/prospective-capture-v1/r8-regression-adjudication.json) and [accepted design](/Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/prospective-capture-v1/r8-regression-design-accepted.json), first receipts/stderr, and current control facts directly. The accepted design supersedes the unused five-second proposal and retains original 0.15-second execution / 0.5-second cleanup timing.

- [R8 first cohort](/Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/prospective-capture-v1/builder-r8/first-process-receipt.json): three passed; three real workers, zero fake; **0.6929769999696873 s**. Positive pending/consumption observations, actual wait status zero, one reserve, original caller state and no recovery were retained.
- [Original repeated regression](/Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/prospective-capture-v1/repeated-regression-r8/first-process-receipt.json): **90 passed / 1 error**, 91 methods, 46 real / 29 fake worker invocations; **27.313479291973636 s**, exit 1. Final CaptureDeadline interrupted receipt-file open; one claim, empty streams and zero-byte receipt remained. Actual child reaping and caller/resource restoration were uninstrumented and remain unknown for that run. Neither host slowdown nor successful cleanup is inferred.
- [R8b focused correction](/Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/prospective-capture-v1/focused-regression-r8b/first-process-receipt.json): one renamed method passed, one real worker, **0.2269522079732269 s**. Actual branch: returned_receipt; PID 86694, raw wait status 9, 26 tracked descriptor lifetimes retired, matching committed receipt and no recovery. The alternative final-deadline branch was not exercised. Production bytes stayed unchanged, and the other 90 methods were not replayed.

The corrected [ownership test](/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/prospective-capture/engine/tests/test_prospective_capture.py:351) positively triggers its self-alarm after actual spawn and checks native wait/resource/caller-state evidence. It distinguishes a returned receipt from final-deadline loss and verifies any actual terminal commit without inventing returned publication. This fixes the old unconditional-receipt assumption; it does not convert the original error to a pass or establish both branches experimentally.

## Fresh independent execution and limits

Two distinct invented controls and literal artifact expectations were frozen before one execution. Script SHA256 `0e34f71e0e80c0af6e3854ffc02482aefe65cf29d2309804528a342c6863b3fb`; expectations `4a13b208fe4744321f0d8d05830ca87c159d20927868fcad98ea6b3c576af193`; pre-execution freeze `2eece43c562c8336f7afa4d48eccd3314500b4b7f7fae9620b12abfc1c581fae`.

[First results](/Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/prospective-capture-v1/independent-critic-r8/first-results.json): **two passed, zero failed; two real fixed workers, zero fake workers, zero no-worker controls**.

| Control | Actual observation | Nested seconds |
|---|---|---:|
| marcasite_pending_dual | Pending first alarm plus SIGINT at cleanup unmask: identical first KeyboardInterrupt, nonfinal cleanup_admission evidence, exact artifact, PID 76170 wait status 0, one claim/no receipt, 26 descriptor lifetimes retired | 0.07304145797388628 |
| celestite_retirement_after_pending | Earlier consumed alarm plus later pending final alarm/SIGINT at handler retirement: latest signal_retirement/final evidence, original cleanup_admission/nonfinal snapshot, PID 76175 wait status 0, matching committed receipt/two events but no returned result, 30 lifetimes retired | 0.05400770902633667 |

Five actual self-signals (three SIGALRM, two SIGINT), three native sigwait consumptions, no child signals or native-error injections. Each call armed exactly one execution timer and one reserve. Zero timeouts, unexpected harness errors, stderr warnings, child/FD/state recovery or remaining tracked owned descriptors; no tracked write/fsync after the final-pending hook. All new first outputs/exception traces remain retained; no reruns.

[Outer receipt](/Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/prospective-capture-v1/independent-critic-r8/first-process-receipt.json): **0.3714933330193162 s**, exit 0, 30-second cap. Cumulative critic control time **3.7466890400392003 / 90 s**; remaining **86.2533109599608 s**. Nested times count once. Builder and read/hash/report work are separate; whole-agent time/cost is unknown.

Runtime: Python **3.14.8**, `3.14.8 (main, Sep 30 2026, 17:55:09) [Clang 21.0.0 (clang-2100.3.34.2)]`, `/opt/homebrew/Cellar/python@3.14/3.14.8/Frameworks/Python.framework/Versions/3.14/bin/python3.14`, executable SHA256 `e401ac7a95cda75dee34a0cfe1e4faf0a6df1a501cf67887f177fb78cd4eb60a`. Builder uses 3.12.9. Harness use of co_qualname requires 3.11+; **no Python 3.10 execution is established**.

Deterministic controls do not establish race frequency, exhaustive asynchronous interleavings, uninterruptible kernel bounds or host-loss recovery. Explicit-resource tracking is not a census of SQLite/runtime internals. No original cohort/suite replay, source/test/repository-doc edits, real selection/registration/pilot, network/model call, historical queue consumption, foreign resource action, commit, landing or activation occurred. Review complete; idle for root adjudication.
