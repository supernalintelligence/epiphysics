---
task: deterministic-publication-dates
branch: worktree-date-rendering
reviewed_patch_id: f5fdad08dad9ea89281d108561b7913c4b5a34c5
reviewer_model: "Codex collaborator; model identity not separately recorded"
reviewer_agent_id: /root/site_repair_critic
reviewer_output_sha256: a8befc5d81e17e8733e9afee050e511da9114ea9d9a06deee3b8ec49401e92b7
author_session_id: ""
verdict: fixed
findings: {critical: 0, high: 0, medium: 1, low: 0}
resolved: {fixed: 1, skipped: 0}
skip_class: ""
skip_reason: ""
size: {files: 9, lines: 315}
---

## Conclusion
Ready to land: yes
The shared formatter and all changed consumers use a consistent UTC publication calendar. Independent review closed the filesystem Date-object regression and verified the successful combined build against unchanged source bytes.

## Checks run
The same 30 date/server-markup/parser controls passed in each of Los Angeles, UTC and UTC+14. Focused lint and non-emitting type checks passed. One combined production build returned zero in 36.548197 seconds (outer runner 40.054685 seconds), with 17 static pages and 976 source pins unchanged. Independent review verified retained receipts, complete streams, selected emitted artifacts and restored generated cache. Final diff check passed. Source commit: cb82e6b08d; the final review inspected identical source bytes before that commit.

## Not verified
No browser or live hydration verification, remote CI, release or deployment. SCI's reported live React 418 counts were not independently repeated. Global build type/lint checks are skipped; scoped checks supply separate evidence. The existing multiple-lockfile warning remains. SC reported a concurrent tool-repository writer and deferred its compiled-package rebuild; no toolchain freshness or guard bypass is claimed.

## Findings
- [medium] [fixed] The first formatter revision blanked valid Date objects returned by the filesystem frontmatter loader; restored explicit Date support with actual parser/card controls and an independent reproduction.

## Reviewer report
Independent final date-rendering integration review

Reviewer: /root/site_repair_critic
Reviewed git diff HEAD in /Users/ianderrington/git/ianderrington/epiphysics/.worktrees/date-rendering at base bf15fd8f0e8535859898116aca76865b799d89a3, plus untracked src/lib/utils/dates.test.ts and docs/planning/runs/2026-11-26-date-rendering.md. Reviewed retained combined-build evidence under the persistent shared checkout's .supernal-local/date-rendering-v1/build/. Prior review reports remain preserved.

Findings: no new or open findings. The historical medium/P2 Date-object regression remains fixed. All eight changed source/test files exactly match final-source-identities-v2.json and the prior closing review. The formatter still accepts valid filesystem-loader Date objects as UTC instants, shares rendering with parsed ISO strings, preserves invalid Date text, and does not mutate its input. Its consumers and both legacy re-exports are unchanged from the reviewed repair. The previously inspected 30-test timezone results and focused lint/type results remain applicable to these unchanged bytes; no tests were replayed.

Integration and build evidence: HEAD is the specified combined C11/CI-capacity base. The retained fast-forward record has identical before/after identities for all eight source/test files and the then-current note. The build claim, process receipt and final record bind that same base and source manifest. source-before.json and source-after.json are byte-identical, covering 976 files and 312,284,722 source bytes; their SHA-256 is aa0ff4e5fed08c56ab75de0e13126e839782c5064f81aee83999814b1d514b54. Current content matches every captured file except the deliberately updated closeout note. The archived run-note-before-closeout.md matches the note captured during the build.

The retained npm run build process returned 0, with termination completed and no recorded failure, from 2026-11-26T20:22:49.711984Z to 20:23:26.259976Z, elapsed 36.548197 seconds. The enclosing runner returned 0 in 40.054685 seconds; final.json records passed, no failures and successful cleanup. Both raw streams match their receipt hashes and byte counts and are marked complete. Their contents support the note: prebuild processed 65 records, checked three homepage evidence links and verified the public map without regeneration; Next compiled successfully in 23.1 seconds and reported 17/17 static pages. Global type/lint checking was skipped, and the multiple-lockfile warning was retained. The separate focused checks provide the stated type/lint evidence, not the production build.

Artifact and cleanup verification: every retained non-null selected artifact matches artifacts.json by byte count and SHA-256, including BUILD_ID, manifests, home, overview and research-map HTML. The two selected dynamic article HTML files are explicitly null, consistent with the note and dynamic route output; they are not treated as rendered-page checks. The archived generated content has 65 records and SHA-256 c3433a1ed3a2b294966a9536706c14537e41792008670b730414e500444b2fdb. The working generated content matches content-before.json after restoration, and the owned .next directory is absent. The retained runner bytes match the process receipt's runner hash.

The final run note was read in full and matches the retained observations, nested timing scopes, artifact absences, prior regression history and stated limits. Its final SHA-256 is 9d9586ea84e865d5ac9b41443f847b3123c7a7d9a83b4a8551f18631323b86a6. It correctly distinguishes source/server-markup/build checks from browser hydration, remote CI and deployed behavior, and leaves the reported live React 418 counts attributed to SCI. Final formatter SHA-256 is 49bfa071995c34ffa20c19f2f9f6034387f7a13eae445dc5b2143448cd6479a8; test SHA-256 is e32ea7e4798cf8a33b3601ae0a5f8b5bc1610c1a1c6cba807054204c1bf83d73.

Final checks performed by this reviewer were read-only diff/source inspection, retained receipt/stream/artifact identity checks and git diff --check, which passes. Including the two untracked additions, the patch is nine files, 246 additions and 69 deletions (315 changed lines). No source edits, test/build replay, browser, remote service, study, ledger access, commit, deployment or landing was performed by this reviewer. Local process records support the combined build result; they do not establish an external execution witness or resolution of every live hydration failure.
