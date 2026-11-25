# Adversarial review: worktree-deps-security

- Commit: d1bbf7a (base 7df9093). Only `package.json` changes.
- Verdict: **PASS**. No build, runtime or site regression found. Findings below do not block.

## What was run

All installs and builds ran in `git archive` copies under the session scratchpad.

| Check | Result |
|---|---|
| Fresh install, Node 24.3.0 / npm 11.8.0 | head and base exit 0 |
| Fresh install, npm 10.2.4 (the `packageManager` pin), then build | pass |
| Upgrade of the base `node_modules` to head, with and without its lockfile, then build | pass |
| Lock-only resolve of head over a copy of the old local lockfile | resolves the new versions, no ERESOLVE |
| `npm run vercel-build`, head and base | pass, same route table, 12/12 static pages |
| `next start`, 58 paths (sitemap, pages, API GET) | same status on all (54 x 200, 2 x 404, 2 x 405). Visible text differs only in sitemap `lastmod` times |
| HTML outside `<script>` on sampled pages | one whitespace character differs. Script payloads were not diffed |
| POST `/api/chat`, `/api/chat-mock`, `/api/story-graph/analyze` | same status. `/api/chat` returns 500 on both (no API key) |
| Built CSS | 2186 rules, identical |
| `tsc --noEmit` | 45 errors on each side, same list (the commit message says 43) |
| Headless Chrome, 12 pages, external requests blocked | no difference attributable to the commit (see below) |
| `npm audit` | head 43 (0 critical, 0 high). Base fresh resolve 92 (0 critical, 24 high) |
| `npm ls --all` | no invalid or missing entries |
| zod use (`src/lib/content/markdown.ts:509-514`, `687-725`) | calls used are valid in zod 4. Compiles, rendered text unchanged |
| `@supernal/interface` 1.1.1 | build and tsc match base (1.1.2). 1.1.2 does add `@copilotkit/runtime` |
| `toml` 5 under `remark-mdx-frontmatter` | ESM named import, `parse`, and `bundleMDX` work |
| `mmdc`, Node 20.19.0 and 22.23.5 | renders an SVG |

Browser differences, both explained:

- `/`: `src/components/SiteResume.tsx` stores `ep_last_path` in a cookie. Cookies ignore ports, so `/` redirected to the page visited last. On repeat visits both builds rendered the same.
- `/theory`: React error #418 appeared once on base and once on head. Intermittent on both.

## Findings

1. Low. `package.json:7` declares `node >=20.9.0`, which is lower than the tree supports. `puppeteer` 25.19.0 (`package.json:185`) requires `>=22.12.0`, and `lighthouse` 13.6.0 (`package.json:160`) requires `>=22.19`. `@supabase/supabase-js` 2.119.2 requires `>=22.0.0`, which a fresh resolve of base also picks. Vercel selects the newest Node major for this kind of range, so the deploy is not affected. Local Node 20 gets engine warnings. Suggested follow-up: `>=22.19`.
2. Info. `package.json:185`: on the first full head install the `puppeteer` postinstall failed to extract Chrome. npm still exited 0 (`install.mjs` catches the error). A retry into an empty cache succeeded.
3. Info. `package.json:186` forces `toml` 5 although `remark-mdx-frontmatter` 4.0.0 declares `^3.0.0`. It works in the checks above.
4. Info. `package-lock.json` is gitignored, so each deploy resolves again and the audit result is not pinned. This predates the commit.

## Seen on both base and head (not from this commit)

- Every sampled page throws `Invalid or unexpected token` in the browser.
- `docs/theory/index.md:147`: `./images/concept_flow.svg` returns 404 on `/theory`.
- The sitemap lists `/about`, which returns 404.
- Next loads `next.config.js` first, so `next.config.mjs` is ignored and its security headers are absent from both builds.

## Not verified

- Vercel itself, including its Node setting and build cache.
- Linux x64 install and build (Docker was not running). Only the lockfile entries for the Linux sharp, SWC and esbuild binaries were checked.
- Node 20.9.0 exactly.
- `npm run dev`, turbo tasks, jest, lint, a full lighthouse run (only `--version`), and `src/scripts/renderMermaid.js` (only `mmdc` directly).
- Client-side Mermaid (no diagram on the sampled pages), chat UI interaction, a live Anthropic call.
- The commit claim that reverting any one major brings back a high finding, and the base figure of 94 from the old lockfile.
