---
title: "Research-map introduction layout repair"
description: "A bounded source correction, frontend checks and remaining rendered verification."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: false
---

## Scope and source finding

The research-map introduction used a `header` element. The global navigation rule in `src/app/globals.css` assigns every `header` a height of `var(--header-height)`, defined as `4rem`, plus positioning and stacking rules. The mobile rule also assigns `overflow-x: hidden`. The map's local header class adds substantial padding but does not reset that height. These source rules expose the multi-paragraph introduction to the same fixed-height collision previously repaired in the presentation pages. The exact overlap or clipping was not observed in a rendered page.

Only the opening and closing wrapper tags in `src/components/research-map/ResearchMap.tsx` change from `header` to `div`, following the ordinary content containers used by the other repaired introductions. The class, all text blocks and the level-one heading remain unchanged. Global CSS, graph data, interactions and scientific content are untouched. This is a presentation support repair alongside the separate C20 core build.

## Actual validation

Validation ran once in managed worktree `research-map-header` at base `466ee4f19847dc81ec649059813718730c9378d2`, using existing local dependencies, Node v24.3.0 and npm 11.8.0. No dependency installation or network command was used.

| Check | Observed result | Process seconds |
| --- | --- | ---: |
| Existing public-map typecheck | Eight entries, eleven local source files, zero diagnostics | 2.829 |
| Existing scoped lint | Exit 0; no lint warnings or errors | 2.105 |
| Existing map model and focus tests | Two suites, thirteen tests passed | 3.136 |
| `npm run build`, including existing prebuild checks | Exit 0; 67 content records and 17 static pages | 41.632 |

The subprocess total, including Node/npm version checks, was 49.934 seconds within the 240-second aggregate allowance. No individual timeout exceeded 180 seconds. The build skips global type/lint validation by existing configuration; the separate scoped checks above are the claims made here. The existing multiple-lockfile tracing-root warning and `next lint` deprecation notice remain. No check failed or was replayed.

The changed component's SHA-256 remained `f167ba52792b90e8d96b28a8a10522cbd066f4fee54268a96f57b3223feba716` throughout validation. All 486 pinned source/configuration text inputs were unchanged. Command outputs, elapsed times, input manifests and the validation helper are retained privately under `.supernal-local/research-map-header-v1/` in the shared checkout.

The worktree content cache was snapshotted before preprocessing. The generated build input has 6,138,316 bytes and SHA-256 `cf83c2b725d904987d08be9dee5c29188059446d04a2ad810416277b13b0975d`; its exact bytes are retained separately. The worktree cache was then restored to its original SHA-256 `560f54a5446479772f3bd6ba80d99951ac0c91d02ff0894a38ffe6dece399b80`. The shared checkout's separate cache stayed unchanged. This draft run record was authored after validation and was not a build input.

## Remaining boundaries

No browser, preview, screenshot, alternate renderer, deployment, commit or landing was performed. Source checks and a successful build do not establish visual correctness. Independent review and allowed rendered verification remain outstanding. When browser access is available, check `/research-map` at 360, 768 and 1280 pixels and at 200% zoom for unobscured introduction text, controls and keyboard focus.

Separate future presentation opportunities remain queued: explain the deterministic evidence reader on the landing page; connect a concrete, explicitly synthetic relationship to its worked-example evidence; and label the example's forecast deadline distinctly from its earliest resolution time. They are outside this repair.
