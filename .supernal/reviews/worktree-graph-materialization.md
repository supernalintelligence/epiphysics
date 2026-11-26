---
task: graph-materialization
branch: worktree-graph-materialization
reviewed_patch_id: 32de7dea32ebb8453674a45cd188cc1f153b26c2
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/materialization_final_safety
reviewer_output_sha256: 755c8608f11f65e867d9c6e88d3048476cbfef1464bc6c8b720fa6c3a0057276
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 6, low: 0 }
resolved: { fixed: 6, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 19, lines: 2735 }
---

## Conclusion
Ready to land: yes
Two independent reviewers verified the final fixes and downstream consumer path. All final tests and the real persistent assessment passed; no actionable findings remain.

## Reviewer report
### Unguided final review: /root/materialization_final_critic

No actionable findings remain.

Reviewed `git diff HEAD`, the empty staged diff, and all five untracked engine files under the repository instructions. Traced CLI entry, transaction ownership, manifest registration, historical lookup/replay, forecasting, chained transformation consumers, and assessment integration.

Independently reproduced the malformed-observation failure and verified its final fix: durable rejection, no partial outputs, and exact replay without additional events. A materialized manifest also successfully fed another transform and materialization, preserving the graph and ledger integrity. `git diff --check` passed.

No files edited. Full-suite validation remains with the primary agent.

### Guided final review: /root/materialization_final_safety

No remaining actionable findings.

The malformed retained-observation gap is fixed and independently verified for identity and partition execution, including exact rejection replay after blob loss.

All 15 focused tests passed, covering atomicity, validator mutation, time boundaries, forecasting, bounds, malformed inputs, all 30 capability probes, and isolated recomputation-removal detection. No files edited; full suite left to root.

## Checks run, and what each covered
- Final full engine suite: 308 tests passed in 244.938 seconds; /tmp/epiphysics-materialization-tests-final.log. Earlier pre-final-container suite: 304 passed in 219.438 seconds.
- Atomic/store baseline: 108 tests passed. Final materializer: 28 focused tests passed in 5.247 seconds. Probe/CLI: 11 passed; controller consumer and affected AST-based source-drift/reload checks passed. Guided reviewer independently passed 15 targeted tests in 6.959 seconds.
- materialization-probes-v1 passed 30/30. Coherent forged output reaches recomputation; isolated equality-guard removal and grouped-kind restriction removal fail their checks while ordinary materialization still passes. Real method-descriptor and repeated-metadata limits are exercised before output writes.
- Both changed CI steps ran locally, including fresh fixed child dispatch; no remote CI result claimed. Production assessment acceptance/dispatcher limits remain 30/60 seconds; only CI overall job limit increased to ten minutes based on measured suite duration.
- Production site build passed; /tmp/epiphysics-materialization-build.log. Existing build skips TypeScript/lint checks, no TypeScript changed. Generated index inspected (43 to 58 entries, no removed slugs), archived and restored. Catalog compiled 94 nodes, 109 edges, 13 committed documents and 31 bibliographic sources.
- Real persistent assessment graph-materialization-20261126 consumed graph-views-20261126:next and queued build_retrieval_baseline. Receipt 1bf743c085854bdc90c0ee22ff84ac5f returned 0 in 16.053 seconds, with zero program model calls/external spend. All preceding capability gates passed. New contracts correctly remain incomparable.
- Persistent improvement ledger verifies 84 events, seven completed assessments, no unfinished claims; head 32605bda5fd2eaf69bf15eb7c391f8e2f07e1510e38b4983f488de0e429c9391.
- SCI native-session delivery returned accepted:true and a matching session ID; its reply confirmed ownership and no dependency blocking B2c/C. No queue-only delivery claim.
- Whitespace and commit secret/branch/metadata/date/document checks passed.

## Not verified
- No semantic equivalence, physical entity fission, predictive/business advantage, learned action policy, independent time/execution witness, live settlement or deployment is established.
- Whole builder/reviewer/supervisor cost remains unknown; zero resources describe the assessment program only.
- Time is the local collector clock. SQLite groups cover derived event records, not filesystem blob rollback. Arbitrary operator/interpreter mutation is outside the trusted-process assurance.
- Exact historical replay does not certify current blob availability. New materialization deliberately refuses incompatible old execution contracts; it does not re-execute arbitrary archived code.
- Retrieval reproducibility/quality remain unmeasured by this packet. The curated 12-query development cohort is not sealed final evaluation; raw third-party source bytes remain local.
- Existing site audit/promotion restriction and unrelated shared-checkout files were preserved.

## Findings
- [medium] [fixed] Reject append-validator body mutation and hash the exact captured stored JSON; rollback/poison groups on failure.
- [medium] [fixed] Align grouped snapshot cutoff with its fixed recorded timestamp so normal-clock snapshots remain usable.
- [medium] [fixed] Prevent shared transaction time from backdating new observations/questions/forecasts, including generic appends; capture refuses before blob writes and live forecasting occurs after commit.
- [medium] [fixed] Validate malformed completion and parent artifact containers before dictionary operations, with durable rejection and exact replay.
- [medium] [fixed] Correct forged-output probe to reach fixed recomputation with coherent IDs and model hash, and detect isolated equality-guard removal.
- [medium] [fixed] Preflight retained observation containers and cost-reference consistency before recipe/parent helpers, eliminating unfinished claims on malformed metadata without broad exception swallowing.
