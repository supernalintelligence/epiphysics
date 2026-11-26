---
task: research-status-home
branch: worktree-research-status-home
reviewed_patch_id: 8e4458ace315e5cf8d69276718dab927d81640dc
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/c4_safety
reviewer_output_sha256: 182ee1e46fe9448f52f8b538e200fbceaced4195bb11dd09d311681b46e8ecc1
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 1, low: 0 }
resolved: { fixed: 1, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 5, lines: 192 }
---

## Conclusion
Ready to land: yes
The homepage now shows the checked coverage and diagnosis results, their limits and the planned follow-up. The build checks its evidence links and selected status claims; independent review cleared the repaired missing-link control.

## Reviewer report
Independent homepage diff review by /root/c4_safety

Decision: clear after one repaired finding; no remaining actionable findings.

Reviewed git diff HEAD at base 59bb70454b67c2fd1d8fa2faad7b59e65569d5f1 plus both untracked progress files. The displayed coverage result, diagnosed gap, limitations, publication date and planned follow-up agree with the three linked public records. The page keeps measured results separate from future work and explicitly discloses the changed selection budget. Build wiring runs the evidence check after content preprocessing for normal and Vercel builds.

Closed finding: the verifier previously checked that next.evidenceId was named protocol but did not require that entry to exist. Removing the protocol evidence row passed verification while the homepage resolved its follow-up href to undefined. Root added the missing evidence-map membership assertion. Independent final controls confirm the unchanged snapshot passes against /tmp/epiphysics-research-status-home-content-data.json and the missing-protocol variant now refuses. Earlier focused controls also rejected a missing built route, altered evidence claim, draft diagnosis record, completed follow-up status and mismatched publication date. git diff --check passes.

The initial direct script invocation refused this worktree's stale generated content-data.json; the archived output of the completed build contains the required routes and passes the same validator. No production/source edits, content regeneration, full build, browser, or visual verification were performed by this reviewer. Root's completed build was not repeated for the single-assertion repair.

Final reviewed file SHA-256 values:
package.json: e29758269cc923916c3ed564e3ab3eeb9cb60881bc26ae3eb66c130d8c96e76a
src/components/home/ResearchHome.tsx: 2fdec93d829a860bc4bd3262da17723efddd4465b7799e0bb0061b7e20c19cb7
src/components/home/ResearchExperience.module.css: 7efc2940ed4c65e355e18bc784b95d854727944e5f85531dbb80913d28b1effa
src/components/home/research-progress.json: 7dbd6bfdc4b36a9cb05516f669d0fea3e5be1691b14b8094fefa8d5d1899ce71
scripts/verify-research-progress.mjs: d275d174be140514a949eb224989ceb9344134a1500796b57931f6f8deb5a8d2

## Checks run, and what each covered
- Production build passed, including content generation and the new homepage evidence guard. Generated content retained all existing slugs, 43 to 66 entries. Output archived outside the checkout and restored before commit.
- Builder's focused TypeScript check and generated homepage content/link inspection passed; lattice, pause and reduced-motion code are unchanged.
- Builder's six inconsistent-snapshot rejection controls plus valid snapshot and editorial-change controls passed. Independent review repeated valid and missing-protocol controls after the one-assertion repair, and inspected the five reviewed file hashes.
- Whitespace and managed pre-commit checks passed. The repair affects the evidence guard only; the production build was not repeated after the independently checked assertion.

## Not verified
No browser or rendered screenshot verification; no deployment, remote CI, external timestamp or independent execution witness. The summary is a reviewed snapshot: the guard detects selected contradictions and missing evidence links, but does not generate scientific conclusions or promote planned experiments automatically.

## Findings
- [medium] [fixed] The follow-up protocol ID could be absent from the evidence map while its named ID passed verification, producing an undefined link; require actual evidence-map membership and verify the missing-row case refuses.
