---
title: "Observatory publication status: 26 November 2026"
description: "Development integration is complete; the dependency audit blocks publication."
date: 2026-11-26T00:42:56.487872+00:00
draft: true
contentType: article
tts:
  enabled: false
feedback:
  enabled: false
---

The observatory implementation and collection-status follow-up are integrated locally on `ian-dev` at `5b4254ca01f2469cb018b0ce8db3bfb435f720b7`. The independent reviews, passing build, 26 engine tests, recovered scoped typecheck, and 14-event collection integrity check are recorded in the preceding run note.

The first push of `ian-dev` passed the test-suite and secret-scan hooks, then failed the existing dependency security audit: 46 vulnerabilities, comprising 35 moderate and 11 low. The push did not complete. No remote promotion request or production deployment was created. Audit thresholds and hooks were not changed or bypassed.

SCI already owns the dependency/security work and the separate site-loading fixes. The exact push result was queued to SCI as `Gu-bVU3lSuc2iZFIIXTmn`; delivery is unconfirmed. Its active session was not interrupted. Coordinate through the existing session before duplicating that dependency work or choosing a different audit policy.

Next: resolve the dependency gate through the repository's approved policy, integrate the independently reviewed site-loading fix, push development, and promote through the required pull requests. Final rendered layout and deployment verification remain outstanding. The saved browser-origin restriction is separate from this chat's now-working Full Access mode.

The bounded daily collector remains active. No additional research task, paid engine call, or external spend was started during this publication check.
