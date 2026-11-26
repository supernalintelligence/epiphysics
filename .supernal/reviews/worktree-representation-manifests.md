---
task: representation-manifests
branch: worktree-representation-manifests
reviewed_patch_id: 64dbe49fb9f2350ed6c74f3ae1c99a87a28a45f4
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/manifest_safety
reviewer_output_sha256: 9e91122bd4788d83de21339628a9f9f0279cfb5e065eae3973d2586e7c0bf112
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 2, low: 0 }
resolved: { fixed: 2, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 17, lines: 1607 }
---

## Conclusion
Ready to land: yes
Two independent reviewers checked manifest identity/bindings, forecast consumers, capability probes, the controller and documentation. Both verified append-boundary validation and exact-replay fixes; no findings remain open.

## Reviewer report
### Unguided final verification: /root/manifest_critic

Final delta review: **original finding resolved; no new actionable findings.** Read-only review; no edits made.

- [manifests.py:286](/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/representation-manifests/engine/epiphysics/manifests.py:286) now prepares metadata without reading mutable blobs, then rechecks artifact, evidence, construction-receipt, inference-receipt, and question bindings inside the append validator.
- [store.py:228](/Users/ianderrington/git/ianderrington/epiphysics/.worktrees/representation-manifests/engine/epiphysics/store.py:228) retains deadline, snapshot availability, and duplicate-method/question checks before invoking the optional callback. Existing callers remain compatible. Callback rejection rolls back; exact retries bypass validation through existing append idempotency.
- Independently reran the original race reproduction: corruption before forecast append now raises `Retained blob hash or size mismatch`, appends **zero forecasts**, and closes the transaction.
- Independently reran the replay reproduction: exact retry after predictor loss returns the original forecast; changed probability raises `Idempotency key already has different content`. Integrity verification still detects the missing blob.
- Reviewed the new callback tests, all-input mutation tests, replay tests, and probe mutation controls. Documentation and CI consistently use `representation-manifest-probes-v2`, denominator **22**, and distinguish replay from current blob integrity.

Validation: **158 engine tests passed** in 35.300 seconds; independently executed capability report passed **22/22** checks; `git diff --check` passed. No staged changes were present during review.

### Guided final verification: /root/manifest_safety

Both P2 findings are fixed; no new actionable issues found.

- Append-time validation rejects the original predictor-corruption reproduction, creates **zero forecasts**, and rolls back cleanly. Tests also cover evidence and construction/inference receipts.
- Identical replay after blob loss returns the original event without appending. Changed requests remain rejected; new forecasts still require valid retained bytes.
- The trusted callback runs after core deadline/duplicate checks, inside the write transaction, using the exact recorded timestamp. Replay skips it.
- Probe v2 passes **22/22** checks. Mutation controls detect removed binding validation and broken replay.

Ran **40 tests successfully**: 36 manifest/probe/CLI tests plus four ledger callback tests. Read-only review; no files edited.

## Checks run, and what each covered
- Full engine suite: 158 tests passed; /tmp/epiphysics-manifests-tests.log. Includes 27 manifest, nine probe/CLI, 32 controller and four new core callback tests.
- Actual manifest capability report v2: 22/22 checks. Existing source/history checks remain 8/8 and 6/6; seven-family oracle control remains 30/30.
- Production site build passed; /tmp/epiphysics-manifests-build.log. Existing configuration skips TypeScript/lint validation; no TypeScript changed. Generated content index inspected, archived in /tmp and restored.
- Both edited CI steps passed locally after supplying the standard RUNNER_TEMP environment. Initial missing local harness environment was diagnosed; no workflow bypass or remote CI result claimed.
- Real persistent-store worker representation-manifests-20261126 consumed source-assertions-20261126:next and queued build_representation_transformations. Receipt c44d3995cb3f483d92c748d804c9dd32, exit 0, 0.447 seconds, zero external spend. Changed contracts correctly yield incomparable_contract_change.
- Pre-commit secret/branch/metadata/date/document checks and whitespace checks passed. Public run note records exact execution timing and limitations.

## Not verified
- No model inference, verified construction execution, semantic/casual equivalence, predictive/business advantage, externally verified costs or timestamps, live settlement or remote deployment is established.
- Unknown costs remain null; reported costs and artifact/receipt hashes are retained declarations.
- Exact replay returns historical metadata even after blob loss; it does not certify present integrity. Full verification still detects unavailable evidence.
- B2 transformations are unmeasured future work. B1 completes only manifest metadata and forecast binding.
- Local validation is not a security boundary against an operator controlling code, storage or clock. Future heartbeat execution still depends on host/session availability.

## Findings
- [medium] [fixed] Revalidate all forecast bindings and retained artifact/evidence/receipt bytes inside the append validator after core deadline and duplicate checks; reject changes during the preparation/write gap without appending.
- [medium] [fixed] Prepare replay-comparable immutable metadata before append and defer mutable byte validation to new writes, preserving exact retries after blob loss while rejecting changed requests.
