---
title: "Bounded capacity for research engine CI"
description: "Separate the complete unit suite from dependent smoke checks while preserving the existing verify gate."
date: 2026-11-25
draft: true
tts:
  enabled: false
feedback:
  enabled: false
---

The supervisor's SCI release investigation reported that both release CI runs reached the 20-minute job timeout. The engine test step alone took 18 minutes 51 seconds, leaving at most 69 seconds for setup and the remaining smoke checks. This record attributes those remote timings to that investigation; this change has not been run on GitHub Actions.

The workflow now runs the unchanged complete engine unit suite in `unit-tests`, with a finite 30-minute job timeout. The existing `verify` job retains every smoke check and its 20-minute timeout, and depends on `unit-tests`. Each job checks out the same workflow revision and sets up Python 3.11 with the existing environment. No shared artifact or mutated unit-test workspace is required by the smoke commands: their inputs come from the checkout or their own temporary stores.

The `verify` job uses `always()` and begins with a prerequisite guard that succeeds only when `unit-tests` has result `success`. This keeps its existing check identity meaningful after unit failure, cancellation or skipping. GitHub documents that a dependent job skipped after upstream failure may not block merging, and recommends `always()` with `needs` for this case. [Required-status-check troubleshooting](https://docs.github.com/en/pull-requests/how-tos/merge-and-close-pull-requests/troubleshooting-required-status-checks#handling-skipped-but-required-checks). Job deadlines remain finite and apply independently. [Workflow timeout syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idtimeout-minutes).

All 11 original command bodies are unchanged: one complete unit discovery invocation and ten smoke steps. The synthetic controls, capability checks, real offline-worker smoke, representation-comparison smoke, prepared-coverage smoke and ledger demo remain present. Triggers, path filters, read-only permissions, action versions and Python version are unchanged. The added gate contains no failure override. Worst-case configured job time is now 30 plus 20 minutes, with an additional checkout/setup; this capacity allocation does not establish a new measured runtime or guarantee that future workloads fit.

Local validation on 2026-11-26 UTC used Python 3.14.8 and PyYAML 6.0.3 with string-preserving parsing and duplicate-key rejection. Structural assertions confirmed the two deadlines, dependency and gate, identical setup/environment, unchanged triggers/permissions, and exact preservation of every original run-step mapping. The original smoke section was also compared byte-for-byte. All 12 current shell bodies passed `bash -n`; all eight embedded Python programs parsed successfully. The new prerequisite command was executed with five owned result strings: `success` exited 0; `failure`, `cancelled`, `skipped` and an empty value each exited 1. `git diff --check` passed. No engine suite, smoke invocation, remote CI, push or deployment was performed for this workflow-only change; `actionlint` was not installed.

Source identities:

- Base commit: `56899eef99972284e4dc933e99ed8de118d4ca83`.
- Original workflow SHA-256: `c21aaca467b066aab7966047bcb6bfceb3cc96f0cbf17baf821dcf68c18e8e12`.
- Revised workflow SHA-256: `2d976a45fc7b2dc957d8e3dc0103ec2015eb4912d274ab1e384af684c6947f61`.

Independent review found no actionable issues and independently repeated the structure, syntax and prerequisite-guard checks. Its exact report SHA-256 is `88f5135bda8b32c54ce9337745ea3bcf02271e142bc06ad35d198764ae22c48d`; remote CI remains unverified. The mathematics note, public-map implementation, private caller and actual evidence ledgers are outside this change.

The uncommitted patch was fast-forwarded onto integrated C11 commit `07fc37314c41fd9fcca481a3aed63d1b9724c759` before its own commit. The reviewed workflow bytes did not change.
