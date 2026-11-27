---
title: "Permission guidance repair: integration and observed behavior"
description: "A local guard-message correction, its reviewed evidence, and the tests that remain unrun."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: false
---

## Problem and resulting behavior

The project's preference guard conservatively inspects script-shaped operands in shell commands. An ordinary source read could therefore receive a message asserting that the file was being executed and directing the reader into a preference-approval workflow. The accepted correction changes the comment and rejection explanation while preserving the original allow/block decisions. It explains the unverified shell semantics and points source inspection toward an available direct reader, committed content through `git show HEAD:<path>`, and current tracked changes through `git diff HEAD`.

An earlier proposal to exempt commands named `cat` was rejected after independent review demonstrated command-resolution weaknesses, including shell functions shadowing an absolute path. That exemption was removed completely before acceptance. The broader permission-block task remains open; ordinary shell-source reads can still be conservatively refused.

## Review, verification and integration

Two independent source reviewers accepted the narrowed correction. A further independent review checked the complete source/test/change-document patch and its workflow evidence. The required controlled-file change record was created through the normal project workflow, without inventing a human approval or changing protected preferences.

The retained exact-source private cohort passed **23 controls with 29 assertions**. Its earlier failed cohort remains preserved as a fixture-placement error; it was not relabelled as a pass. These private handler controls are separate from the repository suite.

The focused repository command was refused by the automatic guard before execution. **All 35 repository cases—24 added and 11 original—remain unrun.** The later checks do not replace that missing result.

In the separate `supernal-coding` repository, source commit `30d9fc7815e679405f27ef27c821461609cc26cc` was locally integrated at `a8935a3823d24e694e436a6aebcd9e5ca422a270`. Normal worktree finish exited zero and removed the completed worktree. Its normal typecheck reported one file in one package with zero errors; the workspace-dependent check also passed. Root verified that the integrated source, test, change document and review record matched the accepted hashes. No push or deployment was performed by this repair.

## One live observation

The result recorded at 07:36:56 UTC shows that one ordinary source-inspection command was denied before execution with the new explanation and source-reading alternatives. The expected guidance was observed, and the guard source and installed binary hashes remained unchanged across that check. The installed binary had changed earlier; whether the normal workflow or concurrent system activity built it was not determined. No explicit build by root or the worker is claimed.

This single live decision demonstrates the corrected guidance on that route. It does not execute the 35 repository cases, establish every runtime route, or resolve all permission interruptions. No user permission request, preference/passkey modification, or guard bypass was used for that check.

Root's integration receipt and live observation are retained privately at `.supernal-local/permission-read-repair-v1/post-review-verification/root-landing-receipt.json` and `.supernal-local/permission-read-repair-v1/post-landing-guidance-check/result.json`. Further work should diagnose a concrete remaining refusal through its supported workflow, preserving the original evidence rather than repeatedly retrying it. This documentation packet itself awaits independent review and integration.
