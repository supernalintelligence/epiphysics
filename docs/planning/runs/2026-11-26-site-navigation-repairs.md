---
title: "Site navigation and diagram repairs"
description: "Bounded collection-heading, unpublished-link and Mermaid layout repairs with local checks."
date: 2026-11-25
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

The bounded repairs are prepared for independent review and integration. Collection indexes now receive a metadata heading when their body supplies no level-one heading, the research overview no longer links to an unpublished brainstorm page, and the entity-interaction diagram avoids connecting nested containers to their ancestors. No scientific prose, equations or claims were changed. No full site build, browser inspection, deployment, commit or landing was performed by this worker.

The client/reporting date is **2026-11-25**. The actual local execution date is **2026-11-26 UTC**; individual start/end timestamps and elapsed process durations are retained separately. The managed worktree is `site-navigation-repairs`, based on `1883963d6f3af8a0c57568e971cea813b5e49f9c`. Evidence is in the shared checkout at `.supernal-local/site-navigation-repairs-v1/`, outside published content.

## Source and boundaries

SCI reported six live indexes without an `h1`, a broken `/research/brainstorms` link and a failed diagram on `/theory/02_5_entity_interaction`. Those are attributed observations; this worker did not reproduce them in a browser. Local source inspection identified the shared title suppression, the excluded brainstorm README, and the diagram's ancestor-container edges.

Both section and nested collection routes render `CollectionDisplay`, which forwards `isIndex`, metadata and HTML to `CollectionTTSContent`. The latter previously suppressed all index titles. It now parses the existing HTML with the already-installed `html-react-parser` dependency to identify real `h1` elements, ignoring comments, escaped examples and inert templates. An authored heading prevents a duplicate; explicit `hide: [title]` still suppresses the metadata title. Indexes retain their prior omission of article bylines. The collection consumer also allows a visible metadata title when its index body is empty.

The production preprocessor requires frontmatter containing a title. `docs/research/brainstorms/README.md` has none and remains excluded. The research overview retains the brainstorm/handoff description without the invalid README site link. No brainstorm files, publication rules or generated public content were changed.

The diagram retains its five nested containers, Cell and External entities, six exchange arrows and their labels. Each exchange now attaches to an ordinary loop node within its containing level. Text line breaks use `<br/>`. A byte comparison with the retained original confirms that everything outside the Mermaid fence is unchanged.

## Local validation

| Check | Observed result | Process duration |
| --- | --- | ---: |
| Heading tests before repair | 8 failed and 7 passed, reproducing the missing-title behavior | 5.603 s |
| Final heading tests | 15 passed across both component suites | 2.300 s |
| Final scoped lint | No errors or warnings in the two components and their tests | 2.592 s |
| Six source indexes through production preprocessing and actual component server rendering | Each has zero authored `h1` elements and one metadata `h1` in server output | 1.917 s |
| Source/link controls in the same check | No brainstorm site link; README still excluded; theory text outside diagram unchanged | Included above |
| Mermaid parser plus simulated SVG layout | Original parses but throws a container-cycle error; repaired version parses and returns SVG without `NaN`/`Infinity` | 3.030 s |
| TypeScript baseline/current comparison | Same 42 diagnostics before and after; zero new or owned-file diagnostics | 8.484 s |

The six source indexes checked were `applications`, `experiments`, `theory`, `experiments/blog`, `research/tensor_programs` and `research`. The production preprocessing functions were loaded with only the all-files `main()` invocation omitted; only these sources and the excluded README were processed. The server check compiled the actual title component and its imports into a private test artifact. `SafeHTML` populates body content in an effect; separate React/jsdom tests use the real `SafeHTML` to verify authored headings, explicit title hiding, content changes, empty index bodies and existing non-index bylines.

Mermaid **11.17.2** accepts both diagrams syntactically. With jsdom and explicitly approximate SVG/text measurements, the original fails with `Setting Civilization as parent of Civilization would create a cycle`; the repaired diagram produces a 22,724-byte simulated SVG. This identifies and tests the layout-cycle repair, **not browser rendering, visual quality, typography or responsive layout**. The measurement shims and output are retained in `check-mermaid.mjs`, `mermaid-results.json` and `after.simulated.svg`.

Failed harness attempts are retained rather than counted as passes: the first Mermaid run lacked the jsdom `CSSStyleSheet` global; the first source-page harness omitted a required relative-path argument; its second attempt used classic JSX transformation instead of automatic JSX. Corrected invocations produced the results above. The initial repository typecheck also found missing matcher type imports in the new tests; explicit imports fixed those. A later compiler-host comparison reads the retained original component bytes and omits the new tests for its baseline, leaving the worktree unchanged. Both baseline and repaired programs report the same 42 unrelated diagnostics. A clean whole-repository typecheck is not claimed.

`commands.jsonl` records exact commands, working directories, UTC timings, exit codes and log filenames. The `before/` and `after/` trees preserve source bytes; the final manifest binds them with SHA-256. The existing root `node_modules` symlink was used without installing packages. Registry discovery returned no matches and reported 20 registry errors; repository instructions and the existing managed-worktree instructions were read. The root agent retains responsibility for independent review, the full build and integration.

Independent review found one low-priority factual overstatement in the replacement research-index sentence: one existing brainstorm has `draft: false` and is already emitted. The supervisor verified its frontmatter and removed the blanket unpublished claim. The README remains excluded and no brainstorm publication policy changes. Source/test checks above are unchanged. The subsequent full combined build is recorded below.


## Supervisor build

One actual production build passed on the reviewed date/CI/map base `1883963d6f3af8a0c57568e971cea813b5e49f9c`. Its npm process ran from `2026-11-26T21:01:56.539854Z` to `21:03:06.014317Z`, returned zero, and took 69.475131 seconds. The enclosing record/artifact runner returned zero in 74.555209 seconds. Source identities were identical before and after; complete streams, generated content and selected HTML/manifests remain in `build/`. The newly generated cache was archived and restored to its pre-build bytes; the owned build directory was removed. Global type/lint checks are skipped by this repository's build and are not inferred from its success.

An earlier invocation refused before starting npm because the scoped lint had left a `.next` directory. Inspection identified exactly one owned ESLint cache file. That directory was moved intact into the private evidence archive, with its hash checked; the refusal receipt remains in `build/preflight-refusal/`. After resolving that ownership condition, the actual build ran once. No build result was discarded or replaced by a repeat.

The helper reuses the previously reviewed date-build runner with only its worktree and seven owned paths changed; an AST comparison confirms identical functions. The build checks do not provide browser or visual verification. Independent closing review and local landing remain pending.
