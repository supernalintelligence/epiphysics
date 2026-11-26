# Adversarial review: worktree-site-bugfixes

- Commit: d638198 (base d43aa3a). `next.config.js`, deleted `next.config.mjs`, `scripts/preprocess-content-simple.js`, `public/content-data.json`.
- Verdict: **PASS**. No build, runtime or visible regression found in the commit. Finding 1 concerns the current `ian-dev` tip, not this commit, and needs action before that tip deploys.

## What was run

Head and base were exported with `git archive` into the session scratchpad, with a clone of the main checkout's `node_modules`. Node 24.3.0.

| Check | Result |
|---|---|
| `migrate-images-to-public.js && next build`, head and base | both pass, same route table, 12/12 static pages |
| `next start`, 56 paths | same status on both (54 x 200, 2 x 404: `/nope-404`, `/robots.txt`) |
| Security headers | present on all 56 head paths and on a `/docs/` image, absent on base. `X-Powered-By` gone |
| `<script>` tags pointing at CSS | base 49 of 56 paths, head 0 |
| Content JSON, base against head | 43 entries on each. 30 `<img>` `src` values changed, nothing else |
| Rewritten targets | all 30 tracked in git with exact case. 26 unique URLs return 200 with image content types |
| Preprocessor, head against base, over committed `docs/` | the new plugin changes exactly those 30 values. Image sources match the committed JSON |
| `/api/feed` image URLs | base: relative and 404. Head: `/docs/` URLs that resolve |
| Headless Chrome, 19 routes, base and head, external requests blocked | broken images: base up to 12 per page, head 0. `Invalid or unexpected token`: every base page, no head page |
| Computed styles on those routes | no difference apart from a one-element `SCRIPT` count on some pages. Pixel differences are the home particles and the share button glow |
| Fresh profile: home, then clicks to `/theory` and Part 1 (desktop, and 390 px wide) | head loads styles and images, no page errors, no horizontal overflow at 390 px |
| Built assets | vendor JS byte-identical. App chunks differ in module ids. CSS: two base files merged into one with the same rules |
| Function file traces | differ only in chunk file names. `content-data.json` still traced |
| Frontmatter cover images | all 41 relative paths point to tracked files |

## Findings

1. **High, not caused by d638198.** `ian-dev` is now at b2d1852, 10 commits past the base. Its `package.json` adds the preprocessor to `vercel-build` (line 20) and as `prebuild`. `docs/theory/self_application_and_lawvere.md` is not tracked there (it exists only as an untracked file in the main checkout). Running the preprocessor on the merged tree (b2d1852 + d638198) drops the entry `theory/self_application_and_lawvere`, which the committed `content-data.json` contains. A deploy of that tip would remove the page. Commit the source file before deploying. The same regeneration applies this commit's image rewrite: 30 images, none relative or missing.
2. Info. `next.config.js:12-25`: the headers take effect for the first time. `X-Frame-Options: DENY` blocks all framing of the site, and camera, microphone and geolocation are disabled. No same-origin iframe or device API call was found in `src/`, `docs/` or the two `@supernal` packages. Any outside page that embeds the site would stop working.
3. Info. `next.config.js:137-143`: the merged `fs`/`path` fallback changes nothing in the build. Next's rule-level `path-browserify` fallback (`next/dist/build/webpack-config.js:1502`) still applies, and the vendor JS is identical.
4. Info. `next.config.js:165-172`: after the fix the `Toast` module rules sit earlier in the merged stylesheet than some `node_modules` rules. The class names are hashed and no style difference appeared.
5. Info, predates the commit. `package.json:15` (`predev`) regenerates `content-data.json`, so a clean clone loses the page in finding 1. Regenerated HTML also differs from the committed HTML for 27 entries.

## Seen on both base and head (not from this commit)

- React error #418 appears intermittently (`/theory`, `/applications`).

## Not verified

- Vercel itself, its Node setting, Linux, and a fresh dependency install.
- A build or server run of the merged tree. `git merge-tree` against b2d1852 is clean and no file overlaps; only the content regeneration was simulated.
- Which branch deploys production, and the live site.
- `npm run dev`, jest, lint, `tsc`.
- The site's dark theme toggle (emulating `prefers-color-scheme` left pages light), Safari and Firefox.
- Text-to-speech, analytics and other external services (requests blocked), deploy environment variables, POST API routes, chat interaction, Mermaid diagrams specifically.
- Embedding of the site by outside pages.
