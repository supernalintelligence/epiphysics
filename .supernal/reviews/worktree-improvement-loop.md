---
task: improvement-loop
branch: worktree-improvement-loop
reviewed_patch_id: a13817d511cfa2859634816108a33950a396d33d
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/loop_safety
reviewer_output_sha256: c00f95ebd65d635440987b097109a97cca5922f5cea94be82ca363c52223abd6
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 2, low: 1 }
resolved: { fixed: 3, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 14, lines: 2461 }
---

## Conclusion
Ready to land: yes
Two independent reviews were performed. All three distinct findings were fixed, with independent regression verification; the duplicated comparability finding is counted once.

## Reviewer report
### Unguided review: /root/loop_critic

One actionable finding:

- **P2 — Compare outcomes only under unchanged metric contracts.** [improvement.py:116](/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/improvement-loop/engine/epiphysics/improvement.py:116) computes a measured change and `target_met` without checking previous suite/evaluator identity. Removing one failing check from a 30-check suite produced a reported provenance improvement of `+0.0333`, `target_met=true`, and a source-span successor although no candidate capability improved. Mark changed contracts incomparable and omit the delta/target assessment. Parent has confirmed and is arranging this fix.

All **34 focused tests passed**. Reviewed the evaluator, controller, ledger integration, examples, workflow, and documentation; found no other actionable defects. Malformed JSON dispatched through the real worker retains failure receipts even though validation occurs before a ledger claim. No files were edited.

### Guided review and fix verification: /root/loop_safety

All three original findings are resolved. No review edits were made.

- **P2, contract comparability — resolved.** [improvement.py:116](/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/improvement-loop/engine/epiphysics/improvement.py:116) now marks changed suite, evaluator, or policy hashes `incomparable_contract_change`, without reporting improvement or target attainment. The original seven-deleted-check reproduction passes.
- **P2, completed assessment versus failed delivery — resolved.** [improvement.py:246](/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/improvement-loop/engine/epiphysics/improvement.py:246) and [improvement.py:395](/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/improvement-loop/engine/epiphysics/improvement.py:395) expose a bounded authoritative completion reference and `assessment_completed_delivery_failed`. Exact oversized replays identify the same completion; changed candidates or completion descriptions cannot claim it.
- **P3, concurrent run-key reuse — resolved.** [improvement.py:175](/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/improvement-loop/engine/epiphysics/improvement.py:175) rechecks run-key use under the write lock. The original controlled interleaving now refuses the second claim and preserves the queued successor.

Six targeted tests passed. An independent 253,995-byte suite with 3,000 checks confirmed fresh and replayed capped delivery produce approximately 2 KB receipts, retain the 1 MB output bound, and leave exactly one completion, no failure transition, an unchanged successor, and a valid ledger. No original findings remain open.

## Checks run, and what each covered
- Full engine suite: 75 tests passed; /tmp/epiphysics-improvement-loop-tests.log.
- Site production build passed; /tmp/epiphysics-improvement-loop-build.log. Existing build configuration skips TypeScript and lint; no TypeScript source changed.
- CI control assertions, real subprocess/status smoke and synthetic ledger demo ran locally. No remote CI result is claimed.
- Two real program subprocesses exercised the negative/reference controls and consumed the recorded successor ID. Persistent ledger verified 14 events, two completions, no unfinished runs, with source-span assertions queued.
- Existing heartbeat updated through the app tool and saved configuration verified active/hourly. Its prompt supervises scoped builders and fixed programs, with bounded immediate follow-up.
- Reviewer independently reproduced contract-change, capped-output/replay and concurrent claim cases. Public run note records the bootstrap limitations.
- Pre-commit secret scan, branch/metadata/date/document checks and git whitespace checks passed.

## Not verified
- No learned model, prospective scientific improvement, business outcome, external witness or live deployment was validated.
- Future heartbeat execution depends on host/session availability. Queue creation alone does not run a builder.
- Local process supervision is not an operating-system security boundary. Worker output and local clocks are not independent attestations.
- Source-span resolution, protected final cohorts, learned action selection and higher-scale operation remain next work; null probability/cost estimates are intentional.

## Findings
- [medium] [fixed] Gate previous-action comparisons on unchanged suite/evaluator/policy hashes; changed contracts yield no improvement claim.
- [medium] [fixed] Preserve and expose authoritative completion separately from capped output delivery, including matching replays; mismatched requests cannot claim it.
- [low] [fixed] Recheck run-key uniqueness under the write lock so a stale worker cannot consume the next step with an existing run key.
