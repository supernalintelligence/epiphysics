---
task: C11-public-research-map
branch: worktree-public-research-map
reviewed_patch_id: 4e5f90f771c2ab8a93a0f2275132603c12bcf11b
reviewer_model: "Codex collaborator; model identity not separately recorded"
reviewer_agent_id: /root/c8_accept_review
reviewer_output_sha256: 7fe2f2300175d09260c418bb570ca0aab23d05bf7327ad8061bd14647b06a3e0
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 7, low: 2 }
resolved: { fixed: 9, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 29, lines: 3870 }
---

## Conclusion
Ready to land: yes
The independent final review clears the exact source patch, retained real validation and accepted controller result for local integration.

## Checks run
270 affected-path tests and six selected legacy controls passed before the final narrow adapter repairs; 25 focused controls passed afterward. Actual six-category validation passed once. Independent validation and acceptance audits passed 32 and 31 grouped checks respectively. Exact scopes, timings and source continuity are retained in the report. One private-caller defect and one private-plan defect were also repaired and reviewed separately; the finding counts here cover the seven committed implementation defects and two final copy defects.

## Not verified
No real-browser visual/accessibility test, human navigation, deployment, engagement, predictive improvement, external timestamp witness or complete repository suite result. Separate date and CI repairs are outside this patch.

## Findings
- [medium] [fixed] Enforce the complete serialized dataset size before output.
- [medium] [fixed] Refuse output symlink redirection and require exact-byte replacement authority.
- [medium] [fixed] Preserve focus after related-claim navigation and invalid-link recovery.
- [medium] [fixed] Independently validate retained document publication metadata.
- [medium] [fixed] Refuse unchanged failed attempts with equivalent provenance-only rebinding.
- [medium] [fixed] Treat a comment-only title as empty publication metadata.
- [medium] [fixed] Permit correction of an invalid derived integrity binding.
- [low] [fixed] Correct README wording about valid integrity repairs.
- [low] [fixed] Make completed typecheck and acceptance history explicit in the run record.

## Reviewer report
# C11 final independent integration review

Reviewer: `/root/c8_accept_review`. Date: 2026-11-26. Worktree: `/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/public-research-map`.

## Exact reviewed patch

Base `56899eef99972284e4dc933e99ed8de118d4ca83`; final head **`994ae5918fdc8d5d6d2fb4fdfd45e0d872eede03`**. The requested initial head `5e51c1fd62f4bc77f3926ad49b6b7f1a337a32f7` was reviewed first; final commit 994ae59 contains only the two requested documentation corrections. Aggregate scope: **29 files, 3,854 insertions, 16 deletions**.

Using the managed workflow's full-index binary diff arguments and whitespace-sensitive `git patch-id --verbatim`, the final reviewed patch ID is **`4e5f90f771c2ab8a93a0f2275132603c12bcf11b`**. Exact diff SHA-256: `9c8075800a44270a8c4693e942d61bc533635eeb23933133c9b1a03e867fa874`.

## Reviewer report

**Ready for local integration. No unresolved actionable finding.** Final disposition: zero open P0, P1, P2 or P3 findings. This is not deployment, browser usability, scientific validation or viral-growth approval.

The patch adds a deliberately selected public claim map, readable directed relationships, optional diagram, explicit publication exporter/verifier, selected frontend checks, and a retained-evidence controller phase with a finite successor. Home/research links and the public protocol describe the same bounded behavior. Public data does not include private planning text, code or ledger contents. The site distinguishes hypotheses, reported results, proposed work and bibliographic references. Graph position is not presented as confidence, importance or authority.

Controller integration preserves semantic task ownership, the accepted C10 origin, capture checkpoint, exact input identities and the measured-negative versus malformed-envelope distinction. Failed processes may lack a success report; malformed artifacts remain negative evidence under a valid envelope. Equivalent provenance rebinding cannot advance an unchanged failed task, while correcting an invalid integrity binding can. Generic fixture assessments cannot consume the map/navigation task. The selected next step is concrete textual evidence-navigation preparation, not an open-ended execution permission.

### Finding accounting and disposition

- **Seven prior P2 implementation findings, all closed:** complete serialized-size cap; output symlink redirection; related-claim/empty-recovery focus loss; missing independent publication-metadata validation; provenance-only unchanged retry; comment-only title acceptance; and rejection of genuine invalid-derived-hash correction. The last four comprise the adapter's two original findings and two distinct repair-boundary findings. Exporter/UI and adapter repair reports preserve their original reproductions and exact fixes.
- **One separate private-caller P2, closed:** root discovered npm's duplicate user/global `/dev/null` configuration failure. The repair uses distinct exclusive empty files and checks their contents. It was independently rechecked and a retained real version probe passed. This private program is not one of the 29 committed files.
- **Two P3 wording findings in this final pass, closed by 994ae59:** the README's overbroad statement that derived-digest-only repair never qualifies now distinguishes equivalent valid rebinding from invalid-to-valid integrity correction; the run record's pending typecheck/acceptance wording now accurately records completion/history. No implementation or public dataset changed for these corrections.
- **One earlier acceptance-plan P2, separately closed before implementation:** a real failed process need not produce success-shaped verifier JSON. This plan finding is not counted as a production-code defect.

Retained initial failed typecheck/test-fixture runs and the first-export `before`/`observedAfter` receipt correction remain disclosed. They are not added again to the reviewer-defect counts above. No private export, actual retry of a failed C11 acceptance or repeated actual dataset export/build is inferred from development failures.

## Source continuity and checks performed

I inspected the exact final diff, relevant page/model/graph/build/dispatcher consumers, publication and run wording, repository instructions, retained test receipts and the prior independent reviews/audits. The full final diff passes whitespace checks. All seven newly added relative Markdown links resolve. This was a scoped added-link check, not a claim that every pre-existing repository link works.

Eleven critical code/contract/data hashes were independently compared to the cleared revisions. In particular:

| Artifact | SHA-256 |
| --- | --- |
| Retained-map adapter | `b50017efd222b77faaff57613f10dd7dda3b22f692df4c5a7ed5ccddea0549b8` |
| Adapter tests | `29c23ce33bb59d128abc984a9bfbd72b1f18f18e17be9ab403d907d271c5c535` |
| Fixed contract JSON | `db11cf29d0786391e04835b2ad5c54a1e69262b7dc143a97e35dc1dc583666d6` |
| Export/projection module | `efa5d4c35340ce4915df2125afeb2a928c9f3cfaf0ac5d7ff273f855cc546626` |
| ResearchMap component | `17ca34a7a31f6218f867968deae63479b006cf7a51010c47e5d6ab74ea681a8f` |
| Saved public dataset | `7608ebe0f4627481cd8befc9f9561c58958e6317f1270e329d4cc59050b9abd9` |

The actual validated UI/build revision was `ce83f453768666ddbd83a84695350d011897966d`. Only `DAILY_LOOP.md`, `TODO.md`, the internal run record and `engine/README.md` differ after that revision. No executing source, selected public document/data or public-facing implementation changed after the accepted validation. No repeated build was needed for these internal documentation corrections.

The public protocol SHA-256 is `185a9cbcc0ab32e043a5139840b38ad32e637c405998bf59cecb873e2c2a1f20`; final internal run record `d626b571fc95df738dad439f6a9e26f963c9c09f88745de961154da50749f66b`; final engine README `6610b26fd5cbc32c8ccf989261fb0681b6a4624c875b02c9f4b8c6981479292f`.

Tracked worktree bytes match the committed review. Untracked generated `.cache/` and `doc-validation.log` were visible and are outside the reviewed patch; root reports retaining them privately. I neither deleted nor claimed these as reviewed source changes.

## Validation evidence and its exact scope

The retained broader affected-path run passed 270 tests and six selected legacy controls on adapter revision `d7810f47…`; both receipts preserve unchanged before/after source maps. After the two narrow parser/relevance repairs, 25 focused core/controller controls passed on final `b50017ef…` (15.754 seconds, 16.0055 enclosing). I inspected these receipts and logs. The broad runs were not rerun on the final narrow revision and are not represented as such. This is not a complete repository suite claim. My separate four-case repair control confirmed all four adapter findings' closure. The private caller has its separate 25 owned controls and nine independent controls.

The first actual six-category frontend validation ran once and passed: 17 exact exporter tests, 13 exact UI tests across two suites, the eight-entry/11-reported-file typecheck, scoped lint, production build and final saved-map verifier. Its enclosing runtime was 62.298144166 seconds. My `actual-validation-audit.json` independently passed 32 checks across 521 files, SHA-256 `b35d4f4b3da400439c5f2f56336b4806c6429b4766f89918422ca56986da6c48`.

Next explicitly skipped global type and lint validation; the separate selected checks are what passed. The multiple-lockfile inferred-root warning remains retained. The build generated 65 content records and 17 static pages; all 12 selected document routes were present. Thirteen selected emitted artifacts were retained and hash-checked, including map HTML; this is not the complete build tree or browser inspection.

One capture retained 65 individual observations through sequence 950. One controller assessment then accepted event **1121**, `improvement:public-research-map-preparation-20261126:complete`, hash **`8cb76d1bfcfb6e172568246997e9c0168c6adbe246a094b61109eb87722a282d`**. Its authoritative report, retained result, source/input manifests and returned output agree. My separate acceptance audit passed 31 checks across 362 files, SHA-256 `902a1369fc23d83903f243b01e52d11809ba640f93dd806a99dfd3fb2a280e71`. That snapshot had 20 completed assessments, no unfinished claim and no C10 rerun. The queued action is `prepare_evidence_navigation_evaluation` with scale change disallowed.

Accepted map counts remain 61 nodes, 70 directed relationships, 20 claims, 12 public documents and 16 bibliographic sources. These are snapshot counts, not success-rate or predictive denominators. Assessment timings are nested: outer caller 12.480889 seconds, dispatcher subprocess 11.781651, assessment 10.984737, first retained-only check 0.113166; completion revalidation is outside that last interval. They are not added together or presented as full supervisor effort.

## Limits and task boundaries

I edited no repository source, ran no new frontend/build/test suite or actual research task during this final pass, and did not replay C10/C11 or consume the live successor. Prior independently executed controls were owned fixtures only; actual audits were read-only.

Public data is a curated pinned subset, with local Git and process attribution. It is not a complete historical corpus, external timestamp witness, hostile-host guarantee or exhaustive installed-dependency proof. No browser accessibility/visual inspection, human navigation, deployment, engagement, predictive advantage or virality result was measured. The SCI-reported date-hydration and CI-timeout work is explicitly separate from this frozen patch and is not claimed repaired here. Final local integration may proceed with these scopes preserved.
