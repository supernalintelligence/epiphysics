---
task: source-assertions
branch: worktree-source-assertions
reviewed_patch_id: 4d733646778b5178a82465e807b3154b83b568ed
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/assertion_safety
reviewer_output_sha256: b78afd7dff5f770e5015c064de596364d13ffbcabc1089e563cdcc371df6b406
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 3, low: 0 }
resolved: { fixed: 3, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 18, lines: 1365 }
---

## Conclusion
Ready to land: yes
Two independent reviewers checked the assertion API, correction lock and historical semantics, capability probes, controller integration and documented boundaries. All three execution-identity finding classes were fixed; both reviewers verified the final dependency-graph correction.

## Reviewer report
### Unguided final verification: /root/assertion_critic

Final delta review passed. **No new findings; the cached-bytecode fix remains effective.**

The dependency graph covers every internal import used by assessment:

- Controller → assertions, evaluator, probes, store.
- Assertions → store.
- Evaluator → store.
- Probes → store and assertions.
- Store → no internal dependencies.

Each module captures dependency code identities when its imports bind. The controller pins those tuples and checks every edge before claiming work, under the claim lock, and after probes. This detects dependencies reloaded before the controller imports, including a probe retaining an old `Ledger` class.

The source-versus-executing-code comparison remains unchanged and still rejects valid stale bytecode.

Verification completed:

- Three targeted tests passed, including all four transitive dependency cases, stale probe aliases, and timestamp-valid stale bytecode.
- Each transitive case requires refusal with zero ledger events.
- Implementation validation passed under `-OO`.
- `git diff --check` passed.
- No files were edited.

Final reviewed hashes:

```text
improvement.py
b9814b70dc7455adb51a7ca28902c6f727d9f77001b6fe8701a0abf4872d4f4c

test_improvement.py
363c8f9e4a5f3a99a5fae00ecb2c3fc4403dabdd5095510255fced9da54ee7fa
```

### Guided final verification: /root/assertion_safety

**P2 findings verified fixed. No remaining actionable findings in the reviewed scope.**

- Exact transitive store-reload reproduction now refuses with **zero ledger events**.
- Source drift, stale imported aliases, retained assessment/ledger objects, and stale bytecode are covered by the final guards.
- Independently reran all **29 controller tests: passed**.

The fix rejects unsupported reloads and accidental source drift while preserving the recorded implementation identity. Review was read-only.

## Checks run, and what each covered
- Full engine suite: 115 tests passed; /tmp/epiphysics-source-assertions-tests.log. Includes 24 assertion tests, five probe/CLI tests, 29 controller/dispatch tests and existing ledger/monitor/knowledge/evaluator tests.
- Fourteen actual assertion API probes passed (8 source-span and 6 history/conflict contracts); broken API mutations are detected independently of candidate answer scores.
- Production site build passed; /tmp/epiphysics-source-assertions-build.log. Existing configuration skips TypeScript/lint validation; no TypeScript source changed. Generated content index was inspected, archived in /tmp and restored.
- Updated workflow capability and real subprocess/status checks ran locally; no remote CI result claimed.
- A real persistent-store subprocess consumed bootstrap-20261126-positive:next, recorded source-assertions-20261126, and queued build_representation_manifests. Receipt 6cc80d4b38c24fd8bf737764b144976d, exit 0, 0.457 seconds, zero external spend. Changed measurement contracts correctly prevented a gain claim.
- Existing heartbeat updated through the app tool; saved active 15-minute recovery cadence verified. Active work continues after checkpoints; future wake execution is not assumed.
- Pre-commit secret/branch/metadata/date/document checks and whitespace checks passed. The final run note and checklist report these verified results.

## Not verified
- No learned model, extraction accuracy, semantic truth, predictive/business advantage, external timestamp witness, remote deployment or live scale increase is established.
- Explicit logical negation and retraction semantics are deferred; accepted scope is the implemented source-backed assertion slice.
- Python source/code/dependency checks detect accidental drift and unsupported reloads; they do not defend against a malicious operator controlling the process, database or clock.
- World-valid intervals are claims. Historical projection is distinct from full ledger/blob verification.
- Representation manifests and transformations are subsequent work. Scheduling and queue records alone do not execute builders or guarantee uninterrupted host availability.

## Findings
- [medium] [fixed] Bind recorded implementation bytes to import-time sources and reject source drift before claiming and after probes; do not attribute old loaded code to newly edited files.
- [medium] [fixed] Pin internal dependency code identities and reject reloads, stale callable aliases, stale Ledger instances and transitive dependencies loaded before the controller.
- [medium] [fixed] Compare executing module code with a fresh non-executed compilation of retained source; reject timestamp-valid stale bytecode even in a fresh process.
