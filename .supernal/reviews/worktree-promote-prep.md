---
task: promote-prep
branch: worktree-promote-prep
reviewed_patch_id: 057ab408d718e2f75d60496b2f553f68a9e83b16
reviewer_model: "claude-sonnet-5-5"
reviewer_agent_id: "a57f0d20fc73dca29"
reviewer_output_sha256: fa6b4b36e330b2f3611b2f1d549655877bd6bb8ef8371d01551bf13de4fea678
author_session_id: ""
verdict: pass
findings: { critical: 0, high: 1, medium: 1, low: 1 }
resolved: { fixed: 1, skipped: 1 }
skip_class: ""
skip_reason: ""
size: { files: 20, lines: 66 }
---
# Adversarial review: worktree-promote-prep

## Conclusion
Ready to land: yes

## Reviewer report

- Range: a312f54..9a47819 (135a8e1, 9a47819).
- First round, on 135a8e1: FAIL. Seven links on five published pages pointed at pages the commit had drafted, and two planning records were still public.
- Second round, on 9a47819: PASS for landing on `ian-dev`, with one open exception to the owner's request.

This is not approval of the exception, and the owner has not approved it. **Tell the owner before promotion, not only after it.** On 2026-11-26 both excepted URLs, under `https://epiphysics.xyz`, returned 404 while the home page returned 200. A promotion of this tree is expected to publish them there.

### Judgment on the exception

Acceptable to land, not complete against the request. Both pages are homepage evidence, and `scripts/verify-research-progress.mjs` requires them to be published. By that script's assertion, drafting them alone would fail `vercel-build`. Both were `draft: false` at a312f54, so this range does not newly publish them in the repository. It hides the other planning pages and the pitch, as asked. Landing on `ian-dev` does not deploy, and the choice can still be changed.

The check does not settle the owner's choice. The options are: keep the two pages public; or move the two records out of `planning/` and update the homepage links and check; or hide them and change the homepage evidence section.

The implementer says the check was added after the owner was asked. Git shows it was added in 56e94d1 (2026-11-26 03:16 -0800). I did not verify when the owner was asked.

## Checks run, and what each covered
- `npm run vercel-build` (local npm script) on a `git archive` export of 9a47819: exit 0. The homepage evidence check passed with 3 links.
- Local `next start` on that build: all 53 published slugs return 200. `/about` returns 200 with title "About". `/ELEVATOR_PITCH` and the tested draft routes return 404. The two excepted pages return 200.
- Server HTML anchor crawl: only `/research/brainstorms` is broken, which was also broken at a312f54. This crawl missed article body links in round one, so a comparison of built-content `href` values with published slugs covers the `planning` and pitch links.
- Diff 135a8e1..9a47819: 5 documents, link markup removed, visible wording unchanged.
- Searched `engine`, `research`, `scripts`, `src` and `docs` for the earlier SHA-256 and blob IDs of the 5 edited documents: no match.
- Round one, for files unchanged since: `npm audit --audit-level=high` exited 0 with 12 low advisories. The installed `sc` hook runner uses the check's `command`. The `/about` pun is accurate.

## Not verified
- No browser or screenshot check of `/about`, including themes and phone width.
- The pre-push hook was not run end to end. Jest, engine tests and the knowledge compiler were not run.
- No Vercel build, push or deploy. The live check covered only the home page and, for 404s, selected paths.

## Findings
- [high] [fixed] 135a8e1 left 7 links on 5 published pages pointing at draft pages. 9a47819 turns them into plain text. In the rebuilt content, the 3 remaining internal `planning` links all resolve to published pages.
- [medium] [skipped] The owner answered "hide" for the planning pages. `planning/runs/2026-11-26-retrieval-coverage` and `-diagnosis` are still published, return 200 locally and are in the sitemap. No code change. Reason: the implementer decided to keep them as homepage evidence and to tell the owner. See the Reviewer report.
- [low] [open] The unlinked sentences still name documents that readers cannot open, such as "the C2 execution record" and "the companion build plan".
  Seen on a312f54 too, so not counted: `/research/brainstorms` is a broken link, and the committed `public/content-data.json` differs from the regenerated content that `vercel-build` produces.
