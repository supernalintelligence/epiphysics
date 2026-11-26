---
title: "Observatory integration and collection: 26 November 2026"
description: "Bounded run record: integration, checker recovery, collection, and remaining publication work."
date: 2026-11-26T00:39:03.942601+00:00
draft: true
contentType: article
tts:
  enabled: false
feedback:
  enabled: false
---

## Completed work

The first observatory slice is integrated on `ian-dev` at `8a8b10db`. It contains the redesigned landing, overview, and chronological example; the local evidence/forecast engine; the research plan and protocol; and the aggregate status display. The independent review is committed in `.supernal/reviews/worktree-epiphysics-observatory.md`. No production deployment is claimed.

This chat now receives unrestricted filesystem access with approval prompts disabled. Its prior restrictions no longer block Git work. The browser has a separate saved-origin restriction; final rendered visual verification remains outstanding. A single retry confirmed that restriction, and no alternate route was used.

## Validation and checker recovery

- All 26 engine tests passed, and the Next.js 15.5.29 production build passed before integration.
- The managed landing completed, but its shared TypeScript service twice timed out. The tool retained the integration and asked for the remaining check; the landing was not replayed.
- A fresh, isolated instance of the same repository TypeScript service checked the exact 12 changed TypeScript files against the project configuration. It returned `errors: []`, TypeScript 5.9.3, in 4.47 seconds. The shared service was not restarted or disabled, and no gate was bypassed. The result is retained locally in `/tmp/epiphysics-scoped-typecheck-20261126.json`.
- A full direct typecheck completed with 44 diagnostics: 42 in pre-existing source areas and two in the shared checkout's generated Next.js route types. None are in this slice's changed files. This is not a clean repository-wide typecheck.
- The built preview was preserved outside the disposable worktree and restarted on the existing port before worktree cleanup.

## Collection

Run key: `2026-11-26-project`. The persistent ledger was verified before and after collection. The run captured the canonical project README once, with no collection failure, no resolution, and no expiry. Fourteen total ledger events now pass local integrity verification.

Recorded through: `2026-11-26T00:36:09.938508+00:00`. Last capture: `2026-11-26T00:36:09.935411+00:00`. Aggregate status: 2 observations, 2 forecasts, 2 pending, 0 resolved, 0 expired, 0 collection failures. The forecasts use the constant-0.5 byte-change baseline. They are not resolved yet, so there is no measured predictive advantage or Brier result to report. Timestamp assurance remains the local collector clock.

The generated site artifact contains aggregates and the public source URL, not the raw source or local file path. It becomes publicly visible only after the reviewed production promotion. Engine paid API calls and external spend: zero.

## Coordination and next work

SCI's earlier mathematics-note response remains verified. The new integration notice is queued as `FLdOutkd8wik5vXf8u-89`; delivery is not confirmed. Its session is busy with independent review of the separate `site-bugfixes` worktree. Do not resume or interrupt that active session merely to force delivery.

The repository now follows `ian-dev` → pull request to `main` → pull request to `production`. Production is the deployment branch. Preserve SCI's work on CSS chunk loading, image paths, and security headers; integrate that reviewed fix before production promotion. Keep the older mathematics note until the accepted qualifications and unique material are retained in the canonical note.

Next publication step: push reviewed development work and prepare its promotion request. Next research component, after publication checks: independent timestamp-witness adapter. The daily heartbeat was updated to read current repository policy, collect from the persistent store, refresh aggregate status, and work on at most one task for 30 active minutes.
