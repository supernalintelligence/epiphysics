---
title: "Collection dependency type repair"
description: "Direct type-check closeout for the collection heading repairs."
date: 2026-11-25
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

The site-navigation repair landed locally at `5b0618b94966ecc8cf8b67a98068bde4a7dc5d22`. Its shared postmerge compiler timed out twice without a verdict. A direct check of the four changed TypeScript entries and their imports then reported three pre-existing errors: two missing post-only filter narrowings and the existing server cache API absent from the installed stable React declarations.

This change adds an explicit `Post` predicate to the existing filter and imports the installed React canary declarations as types only. Next 15.5.29 supplies its compiled React 19.2 canary server runtime, whose cache export was inspected locally. The content caching implementation and filter condition are unchanged; no dependency upgrade or cache replacement is involved.

The same direct four-entry check with repository compiler options now passes with zero diagnostics in 4.409474 seconds. Both edited source hashes were unchanged across that check. Scoped ESLint and `git diff --check` passed. Emitted JavaScript for the content module is byte-identical after comments are removed. The wrapper differs only by parentheses around the single arrow parameter; the original and emitted files are retained for inspection. The initial strict byte-equality check correctly reported that difference rather than a false identical-code claim.

Evidence is retained in `.supernal-local/collection-types-v1/`. No new runtime test or full build was added for these type-only changes. The immediately preceding site-navigation build passed; that build predates this patch. This is a focused compiler result, not a clean whole-project TypeScript, browser, live deployment or shared-daemon claim. Independent review and postmerge closeout remain pending. Actual execution used UTC 2026-11-26; frontmatter follows the client date.
