---
task: site-navigation-and-diagram-repairs
branch: worktree-site-navigation-repairs
reviewed_patch_id: 6158f4b26b6f994a50e19678bcf4e65ca9b40d8a
reviewer_model: "Codex collaborator; model identity not separately recorded"
reviewer_agent_id: /root/site_repair_critic
reviewer_output_sha256: 29f89a121380ee2410407966b80c1241f833bf3faf3fa38525ccacf88181a603
author_session_id: ""
verdict: fixed
findings: {critical: 0, high: 0, medium: 0, low: 1}
resolved: {fixed: 1, skipped: 0}
skip_class: ""
skip_reason: ""
size: {files: 7, lines: 216}
---

## Conclusion
Ready to land: yes
Collection indexes receive a heading without duplicating authored headings, the invalid README link is removed, and diagram container cycles are repaired. Independent review verified the narrow wording correction and retained successful build evidence.

## Checks run
Fifteen component controls passed, including real SafeHTML behavior; six actual index sources produced one server-rendered metadata heading. Scoped lint passed. The full compiler baseline/current comparison retained the same 42 existing diagnostics, zero new or owned-file errors. Original Mermaid cycle failure and corrected simulated SVG were reproduced with explicit approximate measurements. One actual production build passed in 69.475131 seconds (outer 74.555209 seconds), with 17 static pages and 980 unchanged source pins. The corrected research wording was checked in generated content. Final diff check passed. Initial owned-cache preflight refusal and all earlier failed harnesses remain retained.

## Not verified
No browser, responsive visual, hydration, remote CI, deployment or human-use check. Mermaid's simulated SVG is not browser visual verification. The repository build skips global type/lint; a clean whole-repository compiler result is not claimed. Two selected dynamic article pages had no static HTML output. Existing multiple-lockfile warning remains.

## Findings
- [low] [fixed] Replacement prose incorrectly said all brainstorm notes were unpublished; removed the blanket claim after verifying an existing published brainstorm, without changing publication policy or exposing new notes.

## Reviewer report
Independent final site-navigation integration review

Reviewer: /root/site_repair_critic
Reviewed committed patch 1883963d6f3af8a0c57568e971cea813b5e49f9c..5fba582e9224f751d314a77f23920a9b6ade5884 in /Users/ianderrington/git/ianderrington/epiphysics/.worktrees/site-navigation-repairs, plus retained evidence under the persistent shared checkout's .supernal-local/site-navigation-repairs-v1/build/. The initial exact review remains preserved at independent-review.md.

Finding counts: critical 0, high 0, medium 0, low 1 historically identified and fixed; zero open findings and zero new findings. The final research-index sentence no longer asserts that all brainstorm notes are unpublished. It removes only the invalid README link while leaving the existing published brainstorm and publication policy unchanged. Inspected the newly retained generated research HTML: the corrected sentence is present, the blanket assertion and brainstorm link are absent, and the previously published brainstorm record remains generated. This closes the factual finding at docs/research/index.md:79.

Source scope: only docs/research/index.md and the run note changed after the initial review. Both components, both test files and the diagram document still match the original reviewed after-pins. Their caller/renderer analysis and retained 15 passing component tests, scoped lint result and unchanged 42-diagnostic TypeScript comparison remain relevant. The earlier six-index SSR receipt belongs to the pre-wording-correction snapshot; its exact research-sentence assertion is historical, not a newly rerun check. The new build's generated research content supplies direct evidence for the corrected sentence and removed link. No test or harness was replayed by this reviewer.

Build evidence: the retained npm process ran on the declared 1883963 base with the repaired working source, returned 0 with termination completed and no recorded failure, and took 69.475131 seconds (2026-11-26T21:01:56.539854Z through 21:03:06.014317Z). The outer runner returned 0 in 74.555209 seconds; final.json reports passed and no failures. Complete stdout/stderr files match receipt byte counts and hashes. Logs show successful compilation, 17/17 static pages, 65 generated content records, three checked homepage evidence links and public-map verification without regeneration. Global type/lint checking was skipped and the multiple-lockfile warning remains visible; a clean whole-repository typecheck or browser result is not inferred.

Source-before.json and source-after.json are byte-identical across 980 files, SHA-256 776625e2b27eac1399e2712c44c868d1afb4ee06204287c8768436dae0ea95d6. Current file contents match those captured bytes except the subsequent closeout note, whose prior version is retained and matches the build snapshot. All seven final files match their committed HEAD bytes. All ten non-null retained Next artifacts match artifacts.json; two selected dynamic article HTML outputs are explicitly absent. The generated 65-record content matches its artifact hash e36e77b87ac2ba33a7bd6757b784b49722c8c4372b999c37bff8c847491f27d0. The working generated cache matches the retained pre-build bytes, and the owned .next directory is absent after cleanup.

Preflight history: the first runner invocation returned 1 at the pre-existing-.next guard, before the execution claim or npm launch. Its receipt and stderr hashes verify. The private owned-lint-cache archive contains exactly one 1,984-byte ESLint cache with the recovery record's SHA-256 13139dce44bc77bd61afbbf08b085f185fe14bacafe5b70b5abc49d81f8e9a04. That refusal was retained, not presented as a build or replaced build result. After ownership was resolved, one actual npm build is recorded. The reused runner's function ASTs match the prior date-build helper and its bytes match the process receipt; only the declared worktree and owned paths differ.

The final note accurately records the fixed publication wording, distinct local checks, preflight refusal, actual build and remaining browser/visual limits. Mermaid remains supported by approximate jsdom layout evidence of the specific container-cycle repair, not browser typography or responsive inspection. The static build artifacts do not certify the dynamic collection pages or deployed behavior.

Final source pins (SHA-256):
- src/components/CollectionTTSContent.tsx: 43f1792139c6a6dc8735d79cee404f8ce4445f1c15d347aa00856e29fcd86df7
- src/components/CollectionDisplay.tsx: e9053c4f593717f3b4943fa11ba4c29b96274ec887ed9111506a98c1f54e6a15
- src/components/CollectionTTSContent.test.tsx: 79e37b045583de7fdf9925aa5e39af5235ab431094c30af4ebc8d04c269d6cce
- src/components/CollectionDisplay.test.tsx: eb0431e00ea33f9e6df2e6a460695aa9186f9765ca6b4358cb3d764b96791e04
- docs/research/index.md: f7f030e6102cf932f9957f166d6a25abdd1b3af3ac303ce4dedc24e7d3e155e1
- docs/theory/02_5_entity_interaction.md: 1ec21ee621c974edeb65bf11c4af539b89f8d8bee879fb0468cebab9e0e23641
- docs/planning/runs/2026-11-26-site-navigation-repairs.md: 68250ec8c7eccc877022a2f8dea55583669832ae57b3a2acbb8da92d8cebe8ee

Scoped committed patch: seven files, 191 additions and 25 deletions, 216 changed lines. Numstat: run note +55/-0; research index +1/-1; diagram +12/-7; CollectionDisplay tests +36/-0; CollectionDisplay +2/-2; CollectionTTSContent tests +57/-0; CollectionTTSContent +28/-15. git diff --check against the stated base passes. Untracked doc-validation.log is outside this committed patch.

Review limits: no edits, commits, test/build replay, browser/CUA, network, real study, ledger access, deployment or landing by this reviewer. Conclusions are source and retained local-evidence review, not independent execution or live-site visual certification. The historical low-priority finding is closed.
