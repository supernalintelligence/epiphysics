---
task: site-chunks
branch: worktree-site-chunks
reviewed_patch_id: 41c52f2b199c9cb01dd898630bdacd1c8a0145eb
reviewer_model: inherited
reviewer_agent_id: /root/c8_accept_review
reviewer_output_sha256: 3ed962ca215b244d040edcdc11f5273f6289ebd389036f8fa8e65a31058d425e
author_session_id: ""
verdict: pass
findings: { critical: 0, high: 0, medium: 0, low: 0 }
resolved: { fixed: 0, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 1, lines: 20 }
---

## Conclusion

Ready to land: yes
The exact configuration deletion passed two clean production builds and independent source and artifact review. No component or dependency changes are included.

## Checks run

The author captured identical dependencies across both builds and measured asset sizes and references. The independent reviewer recomputed all reported asset hashes, raw and gzip sizes, route unions, emitted script/style groups, content identity and lazy-import availability. Root separately recomputed homepage gzip totals and checked the final config identity. Homepage emitted modern script artifacts fell from 1,755,438 to 151,903 gzip9 bytes.

## Not verified

No browser, visual, interaction, accessibility, network timing, TypeScript, lint or production verification. Compression totals describe retained build artifacts, not observed transfers. The existing build skips TypeScript and lint.

## Findings

## Reviewer report

# Independent review: site chunk configuration

Verdict: no actionable findings in the reviewed change.

## Frozen scope

- Worktree: `/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/site-chunks`.
- Base HEAD: `0e940daab1293437172327881ba5bbd9c0d1ae79`.
- Reviewed `git diff HEAD` and `git diff --staged` before the author committed; staged diff was empty and the working diff contained only a 20-line deletion in `next.config.js`, at the client optimization block formerly starting at line 158. The remaining callback is at lines 128-159.
- Author subsequently committed exactly that source as `0445eed2571898fb5f5b905ac4844c9170b96114`. Independently checked `git diff 0e940da..0445eed -- next.config.js` byte for byte against the reviewed patch: unchanged. The tracked worktree is clean; an untracked `doc-validation.log` was visible and is outside the committed scope.
- Final config SHA-256: `a5a795f5fbc2766dbc7b7bea7650ec4c59875acfcaf4c90220b75e9a4d1c306b`.
- Exact patch SHA-256: `326399c8bb62046d4e9e9a4b64bc8c35a76305cdb1e75d095cd321366a6d2432`; committed diff matches the retained `source.patch` byte for byte.
- Generated `public/content-data.json` was present during initial review/builds and has been restored; it is not in the final patch. Existing EOF bytes are preserved. `git diff --check` passed.

## Source review

The deleted override replaced Next's client splitChunks configuration with one named vendor group matching all dependency JavaScript, including asynchronous imports. Removing it leaves the installed Next 15.5.29 defaults intact. I inspected the installed implementation at `node_modules/next/dist/build/webpack-config.js:814-949`: production client defaults retain separate framework/library groups, exclude CSS from library grouping, and retain normal request and minimum-size controls. Server configuration and the existing client fs/path fallbacks remain unchanged (`next.config.js:136-155`).

Inspected the application consumers: root layout CSS/font imports (`src/app/layout.tsx:2-6`), client layout, home animation and dynamic Three/CausePlex imports (`src/components/home/AnimatedHero.tsx:9,35`), lazy Mermaid wrappers (`src/components/SafeHTML.tsx:10`, `src/components/SafeContent.tsx:9`) and Mermaid's client import (`src/components/MermaidDiagram.tsx:19`). Source/script searches found no hardcoded vendor chunk filename or `_next/static` dependency to update. No change to component behavior, import boundaries, package versions, or server externals is part of this patch.

## Evidence independently checked

Evidence directory: `/Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/site-chunks`.

- Read final baseline/comparison build logs and receipts. Both author-run builds returned 0, and both existing homepage evidence guards passed. Logged wall times were 22.027 and 18.554 seconds; these single observations do not establish a stable build-speed improvement.
- Read the measurement/capture code and independently recomputed raw sizes, per-file gzip level 9 sizes, and SHA-256 values for every reported asset: 25 baseline assets and 107 comparison assets.
- Rechecked all five retained manifest hashes in each output tree, all 10 recorded route unions (rootMain + ancestor layouts + page), and all seven static HTML hashes/script/stylesheet lists per tree. Referenced assets exist; emitted script references point to JavaScript and stylesheet references to CSS.
- Confirmed all seven static pages retain byte-identical CSS and legacy polyfill groups. All 59 recorded lazy diagram import entries remain; entries overlapping the homepage initial asset union fall from 57 to 0.
- Compared the retained input manifests: all 89,599 dependency entries are identical before baseline, after baseline, and after comparison. Across 934 tracked sources, only generated content changed during baseline; only config and generated content differ for comparison. All 59 generated content records and slugs are unchanged.
- Confirmed current config bytes equal final comparison config, not the separately archived intermediate EOF-newline variant.

Measured per-file gzip9 artifact totals:

| Scope | Baseline bytes | Comparison bytes |
| --- | ---: | ---: |
| Shared rootMain JavaScript | 1,735,352 | 103,947 |
| Homepage manifest initial JavaScript including layout | 1,753,832 | 150,278 |
| Homepage emitted modern script tags | 1,755,438 | 151,903 |

The last row is a 91.35% reduction in this emitted artifact measure. It is not observed transfer size, browser timing, or the narrower Next console value of 113 kB. These distinctions are correctly retained in the author's summary.

## Unresolved checks and review limits

This review was read-only apart from this report. I did not edit source, build, install, run a server, use a browser, execute UI interactions, or commit. The successful builds are author-run evidence; the asset/hash/manifest checks above were independently executed against their retained outputs.

Browser hydration, navigation, dynamic Mermaid/Three loading, visual appearance, accessibility, network timing, caching behavior, and deployment remain unverified here. The existing configuration skips TypeScript validation and lint during builds; no such validation is claimed. The unchanged workspace-root warning appears in both logs. No unsupported performance, visual-fix, or production-deployment claim should be inferred from this configuration review.
