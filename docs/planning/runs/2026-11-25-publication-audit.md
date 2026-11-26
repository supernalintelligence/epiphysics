---
title: "Publication dependency audit repair"
description: "A scoped repair of the moderate dependency audit roots, with a retained npm resolution."
date: 2026-11-25
draft: true
tts:
  enabled: false
feedback:
  enabled: false
---

The earlier site fixes and dependency work are already integrated on `ian-dev` at base `6773193`. A saved audit still reports 35 moderate and 11 low affected packages. SCI confirmed that it has no active package work and handed off this narrow repair. The existing moderate audit threshold remains unchanged. This work does not publish the site or establish rendered-layout verification.

## Scope and source checks

Official npm registry metadata and upstream advisories were checked on 26 November 2026 UTC before selecting these replacements:

| Dependency | Selected version | Evidence |
| --- | --- | --- |
| DOMPurify | 3.4.17 | [Registry](https://registry.npmjs.org/dompurify/3.4.17); the [moderate advisory](https://github.com/advisories/GHSA-55q2-fjhq-7xh7) is patched from 3.4.13, and the [upstream hook-detachment advisory](https://github.com/cure53/DOMPurify/security/advisories/GHSA-mrv2-3pqr-j5jr) identifies 3.4.17 as patched. |
| fflate | 0.8.3 | [Registry](https://registry.npmjs.org/fflate/0.8.3); [ZIP64 handling advisory](https://github.com/advisories/GHSA-px8p-9vwx-vf98). |
| glob | 14.0.6 | [Registry](https://registry.npmjs.org/glob/14.0.6); the [cancellation advisory](https://github.com/advisories/GHSA-3g3m-2fjr-6pw4) is patched from 14.0.2. |
| minimatch | 11.0.9 | [Registry](https://registry.npmjs.org/minimatch/11.0.9); the [pattern-amplification advisory](https://github.com/advisories/GHSA-g3hv-75wg-m249) is patched from 11.0.1. |

The direct glob dependency is pinned to 14.0.6. Consumer overrides point `@supernal/interface` and the direct rimraf 5 range to that same pin; npm 10.2.4 retained invalid nested versions when a broad affected-version override was applied to the inherited lock. Overrides for minimatch and fflate target their affected modern ranges. Legacy glob 7 consumers remain on their declared branches and resolve minimatch 3.1.5, preserving the callback and function APIs that the prior global minimatch 9 override displaced.

The prior global brace-expansion 2 override is limited to versions below 3 and retains the inherited 2.1.8 patch. Minimatch 11 imports the named `expand` API supplied by brace-expansion 5.1.0; legacy consumers retain the function API. The new packages' declared Node ranges accept the project's 22.19.0 floor. The npm lockfile is now tracked so the checked resolution can be reproduced.

The existing `@supernal/interface` 1.1.1 pin, zod 4, sharp 0.35, lighthouse 13, puppeteer 25, Node floor and Husky preparation are preserved. The lock resolves these to 1.1.1, 4.6.7, 0.35.5, 13.6.0 and 25.19.0 respectively. No alternate Next configuration or generated content is included.

## Resolution and validation

Validation used Node 24.3.0 and the declared npm 10.2.4. Only this managed worktree's initial `node_modules` symlink was removed; installation used a private dependency directory and `.supernal-local/npm-cache`. Puppeteer's download was disabled for installation; no browser was launched. Husky preparation ran normally.

The inherited, previously ignored lock had SHA-256 `43ea6e667704424e10d5e86c6a0e228181e46fd3757cc0a108a8ba8b2496ce06`. Scoped npm resolution replaced the affected branches, followed by a successful clean `npm ci --no-fund`. No audit autofix or force flag was used. Relative to that inherited resolution, 7 existing package paths change version, 6 paths are added and 29 are removed, all in the selected roots and their glob/matching dependencies. All retained package records have registry resolutions and integrity hashes. The reviewed lock is version 3, SHA-256 `4645337a56ada9c83c4e0046938af9b2145b687e712c068f3d484b858e229288`.

| Check | Observed result |
| --- | --- |
| `npm ci --no-fund` | Exit 0; 1,412 packages installed, Husky preparation completed. |
| `npm audit --audit-level=moderate --json` | Exit 0; 0 moderate, high or critical findings; 12 low affected packages. Threshold unchanged. |
| `npm ls --all --json` | Exit 0; no invalid or missing packages. npm nevertheless lists locked optional `@img/sharp-wasm32` 0.35.5 and `@emnapi/runtime` 1.11.3 as extraneous on this platform. This is not a completely clean diagnostic report. |
| Focused compatibility script | Exit 0: modern glob async/sync and brace patterns; actual interface/rimraf resolution; rimraf glob deletion of a temporary fixture; legacy glob callbacks; link checker and date scanner; DOMPurify formatting and unsafe-markup removal; ZIP round trip and malformed ZIP64 completion within a 2-second child-process bound; Mermaid parser import and diagram parsing. |
| `npm run vercel-build` | Exit 0; content processing, compilation in 17.7 seconds and all 15 static routes completed. Existing configuration skips type checking and lint during build. |
| `npm test -- --runInBand` | Exit 0 because `--passWithNoTests` is configured; no active tests found. This is not test coverage. |
| `npm run lint` | Exit 1 before linting: the nested worktree inherits the parent ESLint config, causing an `@next/next` plugin conflict. |
| Explicit worktree lint | `node node_modules/eslint/bin/eslint.js --no-eslintrc --config .eslintrc.json src --ext .js,.jsx,.ts,.tsx` exited 0 with no diagnostics, using the unchanged project config without ancestor discovery. |
| Scope check | `git diff --check` passed; only the four owned patch files remain changed. |

The build also warns that both the parent checkout and worktree contain lockfiles. This local nested-checkout warning is retained rather than changing Next configuration. Content processing produced 59 records from the current source versus 43 in the old generated artifact; `public/content-data.json` was restored byte-for-byte after inspection. Its original SHA-256 is `560f54a5446479772f3bd6ba80d99951ac0c91d02ff0894a38ffe6dece399b80`. The existing `test:content` entry references a missing `test/test-content.js` and was not counted as a check.

Detailed command logs, the final audit/tree JSON, resolution comparison and the compatibility script are retained locally under this worktree's `.supernal-local/`. The compatibility script SHA-256 is `1e0459605c9d29e3cef821f3f7bd201750388069911ff6e03553f86dfea71804`. Its ZIP64 check establishes bounded completion, not rejection: fflate returns one entry for that malformed fixture. These smoke checks do not establish exhaustive advisory regression coverage or visual correctness.

## Remaining audit roots

All remaining direct advisories are low severity:

| Root and locked version | Advisory | Affected package chain |
| --- | --- | --- |
| `@ai-sdk/provider-utils` 3.0.17 | [Resource consumption](https://github.com/advisories/GHSA-866g-f22w-33x8), affected below 3.0.28 | `@ai-sdk/mcp`, then the retained `@supernal/interface` 1.1.1. |
| `@babel/core` 7.29.0 | [Source-map file read](https://github.com/advisories/GHSA-4x5r-pxfx-6jf8), affected through 7.29.0 | `@babel/core`. |
| `katex` 0.16.47 | [Trust restriction bypass with existing prototype pollution](https://github.com/advisories/GHSA-238p-pmpm-9mq7), affected from 0.11.0 below 0.18.2 | `mermaid`, `@mermaid-js/layout-elk`, `@mermaid-js/layout-tidy-tree`, `@mermaid-js/mermaid-cli`, `micromark-extension-math`, `remark-math`, `rehype-katex`. |

The apparent increase from 11 to 12 low packages is `@supernal/interface` moving from moderate to low after its glob finding is removed, not a new advisory root. These findings remain for a separate compatible update; the publication gate permits low findings and was not weakened.

## Publication boundary

Independent review and normal integration precede any development push. Repository policy requires pull requests from `ian-dev` to `main`, then `main` to `production`; only production deploys. No push, deployment or browser inspection is part of this dependency patch, and the earlier browser restriction remains respected.
