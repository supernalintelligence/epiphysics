---
task: epiphysics-observatory
branch: worktree-epiphysics-observatory
reviewed_patch_id: 54ace537ecaf7d82a2217259b1830d6d57f59e30
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/engine_review
reviewer_output_sha256: f302406cda0c9923a9d328ef352ee55e19fabaa01294007a9d7d4432d2228674
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 2, medium: 7, low: 0 }
resolved: { fixed: 9, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 41, lines: 2927 }
---
## Conclusion
Ready to land: yes
All nine review findings are resolved. The primary author inspected the engine reviewer's fixes and reran all 26 tests. This records source-level approval with the visual-verification limitation below; it is not scientific validation.

## Reviewer report
**Ready to land: Yes, within the reviewed engine and collection-status scope.** No unresolved blocking findings remain from this review.

Reviewer: `/root/engine_review`. Final inspection date: 25 November 2026. The actual model identifier is not exposed to me; I have not inferred it.

I independently reviewed the primary author’s engine, workflow, and public-status changes and reproduced the findings below. I subsequently implemented the requested fixes and regression tests. This final inspection therefore includes review of my own fixes; the primary author should retain their separate review of those changes. No files were modified during this final inspection.

Seven findings were identified and resolved:

1. **P1 — Concurrent duplicate forecasts.** Two writers could pass the method/question uniqueness check before either appended, creating duplicate scored attempts. In [store.py](/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/epiphysics-observatory/engine/epiphysics/store.py), validation now runs inside the SQLite write transaction. Regression tests confirm only one competing forecast succeeds. Resolution and correction ordering receive the same transactional protection.

2. **P2 — Duplicate cycle execution for one run key.** Concurrent callers could share an idempotent start record and both collect evidence. Cycle starts now require an exclusive claim. Tests confirm one start, completion, observation, question, and forecast; subsequent completed-run replay remains unchanged.

3. **P2 — Missing sources never expired.** Collection failures skipped expiry processing. Expiry now runs independently of capture success, including when a source is removed from configuration. Scores distinguish expired forecasts from pending ones.

4. **P2 — Forecast timestamps could cross their deadline.** Validation previously checked an earlier clock reading than the stored event timestamp. New-event validation now uses the timestamp acquired after obtaining the write lock. A regression test confirms a writer delayed past its deadline is rejected. Identical recorded events remain safely replayable.

5. **P1 — Status publication could destroy evidence.** An output path targeting the ledger database replaced it with JSON. Publication now rejects destinations inside the evidence store, source aliases, and non-JSON destinations before creating directories or replacing files. Tests cover direct paths, directory symlinks, source symlinks, and source hard links.

6. **P2 — Unsupported forecasts were mislabeled as the baseline.** Public status previously aggregated other methods and probabilities under a constant-0.5 description. It now rejects forecasts unless their method is `constant-0.5-v1`, status is `predicted`, and probability is `0.5`.

7. **P2 — Status combined different database states.** Concurrent collection could produce counts newer than the displayed capture timestamp. Events, integrity verification, and scoring now run within one explicit read transaction. A concurrent-collection regression confirms the exported record remains consistent.

Final validation passed: **26 engine tests on Python 3.14.8**, focused ESLint checks for both collection/observatory components, and the CLI synthetic demo. The demo exited successfully with nine events, valid integrity, and one matched comparison. No separate workflow or component correctness defect remains identified.

Remaining limitations are explicit: the ledger assumes a trusted local operator, timestamps have no independent witness, and public status is a deployed snapshot rather than a live service. This review did not execute GitHub’s Python 3.11 environment or perform browser visual verification. Earlier repository-wide TypeScript checking failed in files outside the reviewed changed components; this report does not claim a clean repository-wide typecheck.

### Additional UI review — /root/site_research

**Ready to land: yes, subject to the repository’s build/test gates passing and retaining the visual-verification limitation below.** I found no remaining blocking defect in this independent, read-only UI review.

The reported overlap has a concrete source-level fix: the observatory introduction now uses an ordinary `div`, so it no longer inherits the global `header` height and stacking rules. The chronological entries have explicit spacing and responsive layouts. The revised landing page uses a research introduction and plain work index, with implemented work distinguished from proposed evaluation and timestamp infrastructure.

Both earlier findings are resolved in code. The step controls now wrap instead of forcing five columns into a narrow viewport. Paused and reduced-motion states snap to the selected representation and stop scheduling animation, rather than allowing point interpolation to continue. All **103 referenced CSS classes** resolve. The specified informational text colors have calculated contrast of at least **5.20:1** against their backgrounds.

`CollectionStatus` clearly separates the real collection record from the fictional example. Its artifact contains one observation, one pending forecast, and zero resolved forecasts; the aggregate counts reconcile and the capture timestamp parses. The copy identifies the display as a deployed status snapshot, not a live connection, and discloses the local clock and constant 50% byte-change baseline.

The public README URL matches the configured Git origin: `supernalintelligence/epiphysics`, with the expected `blob/main/README.md` path. This is a source-location link, not an immutable capture permalink. All newly linked internal destinations exist and are publicly loadable, including `/overview`, `/observatory`, the research program, prospective protocol, theory map, and `#temporal-evidence`.

The plan accurately distinguishes the active, host-dependent daily heartbeat from the unimplemented scientific optimizer. SCI contact is recorded as established, while observatory review remains pending.

**Limitations:** browser access to the final origin was refused; I used no browser workaround. Final rendered visuals, actual spacing across devices, browser interactions, and external-link reachability were not verified. This recommendation is source-level approval, not visual acceptance of the final design. No files were changed.

## Checks run, and what each covered
- Primary author: all 26 engine tests passed on Python 3.14.8, covering immutable evidence, provenance cutoffs, forecasts, corrections, concurrent writers, deadlines, bounded collection, expiry, and public status protection/consistency.
- Production Next.js 15.5.29 build passed for the redesigned UI and connected collection status using the shared, updated dependencies (log: /tmp/epiphysics-observatory-landing-build.log).
- Reviewer: focused component ESLint, synthetic CLI demo, 103 CSS references, declared color contrast, and newly linked route existence.
- Primary author: read the public-status output protections and read-transaction regression tests; confirmed the public source URL against the configured Git remote.
- Primary author: git diff --check passed; generated content-data.json is excluded from this patch because prebuild regenerates it.
- SCI communication reviewer verified receipt and explicit response in the exact Claude session transcript. This does not establish an observatory design review.

## Not verified
- Final rendered appearance and download interaction: the browser tool refused the origin through saved permissions or managed policy. No alternate browser route was used to bypass that restriction.
- Repository-wide type checking has 42 existing errors outside the changed files; Next.js is configured to skip type and lint errors. No clean repository-wide typecheck is claimed.
- GitHub Python 3.11 execution, deployment, independent timestamps, learned-model advantage, guaranteed growth, and real value settlement are not established by these local checks.
- The daily heartbeat depends on the local host and uses bounded zero-paid-API work. The current collector is a file-byte-change baseline, not a test of Epimechanics' predictive merit.

## Findings
- [high] [fixed] Forecast method/question uniqueness was not atomic across writers; validation now runs within the write transaction.
- [medium] [fixed] Concurrent cycles could both run for one key; starts now use an exclusive claim.
- [medium] [fixed] Failed or removed sources could stay pending indefinitely; expiry is independent of collection success.
- [medium] [fixed] A forecast could cross its deadline waiting for a write lock; validation uses the timestamp after locking.
- [high] [fixed] Status output could overwrite evidence; protected store paths, source aliases and non-JSON destinations are rejected.
- [medium] [fixed] Status could mislabel other forecasts as the constant baseline; unsupported method, probability and attempt states are rejected.
- [medium] [fixed] Status reads could mix concurrent database states; all reads share one transaction snapshot.
- [medium] [fixed] Overview controls could overflow narrow viewports; controls wrap responsively.
- [medium] [fixed] Pause and reduced-motion states allowed ongoing interpolation; selected stages now snap and stop animation scheduling.
