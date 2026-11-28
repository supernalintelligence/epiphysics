---
task: evidence-navigation-first-trial
branch: worktree-evidence-navigation
reviewed_patch_id: 01c7aa0548b26e39e995d3142b8479498a50314f
reviewer_model: "Codex collaborator; model identity not separately recorded"
reviewer_agent_id: /root/navigation_repair_critic
reviewer_output_sha256: d80f7d11ff2e7d238cf40b47776850dd161f67c2ee67fa1597a67deaf3cc1cea
author_session_id: ""
verdict: fixed
findings: {critical: 0, high: 3, medium: 6, low: 0}
resolved: {fixed: 9, skipped: 0}
skip_class: ""
skip_reason: ""
size: {files: 24, lines: 3688}
---

## Conclusion
Ready to land: yes
The prospective navigation protocol, preserved first trial and disclosed failure diagnosis are independently reviewed. This landing preserves the negative research record and does not accept the provisional score or claim improved accuracy.

## Checks run
Core v3 passed 136 controls; v4 bootstrap-specific controls and separate complete invented command-chain checks closed later findings. The final core source identities match those reviewed versions. Candidate controls passed 29 owned and 13 independent invented cases with narrowed support explicitly disclosed. One combined site build passed in 62.685773 seconds: 67 content records, 17 static pages and 1,001 unchanged source identities. Independent retained-build verification passed all three homepage evidence anchors. Two draft-only checkpoint updates were subsequently reviewed without findings; they are excluded from published content. Actual C12 ran six first attempts once; the final acceptance process was interrupted. Two independent audits supported one failure-only recovery preserving the original 1,335 events; event 1,336 queues diagnosis with no accepted score and no unfinished claim. No study stage was replayed.

## Not verified
No browser, human-use, predictive-advantage, graph-versus-text, live deployment, remote CI or whole-project compiler result is claimed. The private caller-recovery version is a separate development artifact outside this patch and its reviews are retained separately. Time and identity assurance remain trusted-local. The actual supervisor process-inventory stall is retained as an observed failure, not explained away by passing synthetic checks. The original reference-policy ambiguity remains disclosed rather than retroactively changing the key.

## Findings
- [high] [fixed] C12 closure did not enforce the original total deadline through capture and final controller completion; locked completion now checks it and records late closure as failure.
- [medium] [fixed] Enclosing runner timeout could be swallowed after retaining child facts; propagation now prevents later acting stages.
- [medium] [fixed] Failed evaluator final validation could retain provisional success scores; negative output clears them.
- [high] [fixed] Interrupted evaluator publication could leave successful-looking bytes eligible for acceptance; a separately observed successful process outcome is now required.
- [medium] [fixed] Deadline interruption during runner cleanup could skip runtime facts and leave failure persistence without its reserve alarm; bounded finalization retains facts and preserves the original reserve.
- [medium] [fixed] Ordinary process cleanup errors could skip raw receipt retention; each cleanup stage is retained and prevents later candidate attempts as appropriate.
- [high] [fixed] Fixed runpy bootstrap left the acceptance CLI without its module identity; shared bootstrap now uses alter_sys and the exact command chain was independently exercised.
- [medium] [fixed] Candidate accepted denied or nonasserted scope restrictions; the whole statement must now match one of the explicitly narrowed forms.
- [medium] [fixed] Candidate accepted unrelated broad/general physical descriptions as scope limits; closed property vocabulary now abstains on those cases.

## Reviewer report
# Final unguided diff review

No actionable findings in the reviewed final repository changes. This is a review conclusion, not a certification of an accepted study score, production behavior, or the private caller-recovery work.

Reviewed `/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/evidence-navigation` against HEAD `c82d28d2127e00501c774ccb9a5ed9b61643ccf1`: the full tracked diff and every untracked source/document reported by Git. The final scope is **6 tracked modifications and 18 untracked files**. `public/content-data.json` appeared modified during the active build, then the owning helper restored its prior bytes; it is clean in the final diff. Applicable repository instructions were observed. No source edits, builds, study executions, ledger mutations, or new toy executions were performed in this final review.

The exact reviewed diff is retained as `reviewed.diff`, SHA-256 `3d7fe194e1b67d2f14a6786540e9d812ac23b5402d9bbcc5ac40ff97f94685ef`. `source-pins.json` enumerates the final 24 files with byte lengths and SHA-256 identities, including the untracked files that an ordinary Git diff omits.

## Changed consumers

| Changed files | Consumer and reviewed effect |
| --- | --- |
| `engine/epiphysics/decision_assessment.py`, `engine/epiphysics/improvement.py` | Existing decision-study preparation/check/assessment routing and implementation pins now include navigation. The controller validates queue lineage, phase/contract identity, retained timing, selected successor, and the final locked completion boundary. Failed closure preserves a negative outcome without accepted scores or retry authority. |
| `engine/epiphysics/navigation_contracts.py` | Public schema, bounded JSON/text/input/output rules, fixed budgets and evaluator command identity consumed by the runner, evaluator and retained assessor. |
| `engine/epiphysics/navigation_runner.py` | External runner consumes accepted preparation and the public task/map inputs, executes first attempts, retains bounded raw facts and seals the result; it does not receive the private answer key. |
| `engine/epiphysics/navigation_evaluation.py` | Separate post-seal evaluator consumes retained attempts and the key, creating a provisional report. Acceptance additionally requires the independently observed evaluator outcome. |
| `engine/epiphysics/navigation_assessment.py` | Preparation and retained checking integrate with the existing decision controller, including source/input/authorship pins, lineage, independently observed evaluation completion and original deadline closure. |
| `engine/epiphysics/navigation_candidate.py` | Standalone standard-library stdin/stdout baseline, launched as copied source by the external runner rather than imported by the controller. Its conservative scope grammar and exact-reference behavior remain the frozen measured baseline. |
| `engine/tests/test_navigation_{contracts,runner,evaluation,assessment,controller,candidate}.py` | Owned synthetic contract, subprocess, retained evidence, controller and standalone reader controls; no actual cohort/key material is used by these test fixtures. |
| `engine/examples/navigation/{README.md,contract.json,controller-policy.json}`, `engine/README.md` | Explicit usage/protocol and preparation/controller configuration. The navigation policy allocates 60 seconds inside the unchanged outer budgets; the legacy policy is unchanged. |
| `docs/experiments/evidence-navigation.md`, `docs/experiments/results/2026-11-26-first-evidence-reader.md` | Published protocol/result feed the content preprocessor and document routes. The result distinguishes five answers with required evidence plus valid excluded references, the scope abstention, provisional strict scoring, interrupted acceptance and failure-only reconciliation. |
| `src/components/home/research-progress.json` | Consumed by `ResearchHome.tsx` and checked by `scripts/verify-research-progress.mjs`; its three evidence links resolve to the published result and distinguish completed observations from the planned follow-up. |
| `DAILY_LOOP.md`, `TODO.md`, `docs/planning/runs/2026-11-26-{evidence-navigation,supervisor-status}.md` | Maintainer/run-state consumers: original single trial, failed acceptance, event 1336 failure-only closure, no accepted score or replay. Both new planning records are drafts and absent from retained published content. |

The downstream content loader is `src/lib/content/index.ts`; the build prehook generates its `public/content-data.json` input. The public-map assessor's historical source pins are retained evidence and do not authorize rebuilding the earlier accepted map for this trial. The new private `caller-recovery-v1` is outside this diff and was not reviewed.

## Checks and evidence

- `git rev-parse HEAD`, `git status --short`, `git diff HEAD`, and `git ls-files --others --exclude-standard` established the exact base/scope. Every final changed/untracked Python file was parsed with `python3.14`/`ast.parse`: **13 files passed**, without imports or execution.
- SHA-256 comparison against `core-repair-freeze-v4.json`: **all 13 core files match** the previously independently reviewed freeze. The candidate source matches `ecf78fc4321fbb4f4b5b536e1d1cf1eb9039031942ec63bcc84733ae1e78fd2f`. Candidate source and its full synthetic test file were statically reviewed in this final scope.
- Direct `node scripts/verify-research-progress.mjs` initially returned exit 1 because the restored source cache lacks the new published result. This is retained as an observed cache/build-artifact distinction, not suppressed as a pass. The owning build's `final.json` explicitly records `generated_content_restored: true` and `owned_next_removed: true`.
- Independently invoked the exported `verifyResearchProgress` function with current homepage/source Markdown and **retained `build/content-after.json`**, using `node --input-type=module`. Exit 0: **3 published links, required claims and planned follow-up status passed**. JSON inspection confirms the new protocol and result are published and both new draft run records are excluded.
- Read the existing combined build receipt rather than rerunning it: npm build exit 0, 62.6857729589683 seconds, 67 content items and 17 static pages. Its before/after source manifests compare equal. `build/final.json` SHA-256 is `07e9463b7ab97fa2af3f2bc4a6d6a37abf971104510eafd35dac2f5a4d8177c0`; retained generated-content SHA-256 is `fde456fe98eeb1bfa537fab75713580e48d22661284d3dc9c76830a515ceaa92`; both source-manifest files hash to `10d8edf97d39724d68e1b1447196dc6d9b22c0fe8d2204f451c764144aa6b747`.
- Historical controls remain historical: core v3's 136 checks (46 navigation, 70 adjacent, 20 overflow repetitions), the v4 affected controls, and the full owned exact-command integration documented in `core-review/closure-unguided/report.json`. They were not rerun here. That closure report's SHA-256 is `0b22789140df046f4de3a1bff1dc1e2c82feb07976dd92bba0a2e9591ee7876c`.
- Public factual claims were checked against the prior retained interruption audit and current `public-result-review/report.md`. The new report does not turn provisional scores into an accepted accuracy result. A separately observed process-inventory timeout explains the caller interruption; its underlying stall cause remains unknown. The original scoring convention limitation is disclosed without rewriting the key or first attempts.

## Coverage limits

This final pass is static review plus parsing, source-pin checks and read-only verification of retained build content. It does not independently repeat the actual study, test browser hydration/usability, verify a deployment, or establish general reader accuracy or a graph advantage. Earlier repaired core findings were rechecked through unchanged source identities and retained control evidence rather than redundant execution. No new private caller-recovery implementation was inspected. No remaining actionable repository-diff defect was identified within these limits.

## Addendum: 22:40 UTC checkpoint

No actionable findings in the two later draft-record updates. Hash comparison confirms they are the only changes since the initial review; all code, tests, examples, public content and homepage files remain unchanged. The changed consumers remain the maintainer chronology/status records, both marked `draft: true`. The source scope remains 24 files against the same HEAD.

Reviewed the full refreshed supervisor status and the appended final paragraph of the trial chronology. The retained recovery control receipt reports exit 0 in 3.954460790962912 seconds; its stderr records 21 tests passing. Its manifest records zero actual-study invocations and zero actual-store writes. These support the checkpoint's builder/control claims, not an independent correctness verdict on the private recovery implementation. The two independent reviewer assignments are consistent with the checkpoint; reviewer activity is time-specific, and the safety reviewer has subsequently completed. No private recovery code was reviewed here.

The retained combined build and generated-content checks support the 62.685773-second, 67-record, 17-static-page, 1,001-unchanged-source claims, including deliberate restoration of the old generated cache. SCI acknowledgment `TGyujGGa3feZB_RIsVqmp`, retained at `.supernal-local/coordination/c12-trial-diagnosis-ack.json`, is timestamped 22:37:31.293 UTC and explicitly states no ownership overlap and no independent checking of results or commits. It is an unsigned received coordination record, not a release approval or independent result validation. The checkpoint preserves those limits. No tests, builds, actual-study stages or ledger operations were rerun for this addendum.

| Updated draft | Refreshed SHA-256 |
| --- | --- |
| `docs/planning/runs/2026-11-26-evidence-navigation.md` | `673390ccbfd0cd9b61b2c8b6f81796354557e8b81da15adf59ebbf3dc8aed117` |
| `docs/planning/runs/2026-11-26-supervisor-status.md` | `4f657a056f50a590fd1703b6cc488b3dc1f8baaef9bd9490ea14ee5fa076616b` |

`report.md` remains unchanged (SHA-256 `eaa027863486e4ce2702a9bff99fddd58fbb17f9e83de809220bc94d8df746cc`). The initial pins/diff are preserved as `source-pins-before-checkpoint.json` and `reviewed-before-checkpoint.diff`; current identities are in refreshed `source-pins.json`. Refreshed `reviewed.diff` is byte-identical because both updates are to untracked documents. Receipt paths and hashes are retained in `checkpoint-receipts.json`. This addendum supplements the original review and its coverage limits.
