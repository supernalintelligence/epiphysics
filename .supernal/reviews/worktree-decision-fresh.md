---
task: decision-fresh
branch: worktree-decision-fresh
reviewed_patch_id: ca6c72134f3ce8d702284753157893e8a0692d23
reviewer_model: "Inherited session model; identifier not exposed"
reviewer_agent_id: /root/c8_whole_review
reviewer_output_sha256: 1dca1f89ea981bc191ff10bb48906fa723903f5b1f6823da5c7ba0deaa87a4c0
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 7, low: 1 }
resolved: { fixed: 8, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 21, lines: 2580 }
---

## Conclusion
Ready to land: yes
The single fresh comparison is independently audited and accepted in the persistent queue. All eight review findings are resolved; focused tests, real acceptance, public evidence guard, site build and committed knowledge-map compilation passed. This is a local landing with the original evidence archived and the next diagnosis already prepared.

## Checks run, and what each covered
- Final eight decision modules: 158 tests passed in 9.708 seconds, all 79 source/test files unchanged. Five legacy completion, ownership, selector and real-dispatch controls passed in 43.940 seconds on the unchanged controller paths.
- Independent reviews: four contract-mutation controls, seven harmless process-tree/transport controls, 22 outer-wrapper mocks and 13 acceptance-wrapper mocks. Whole-patch and shared-ownership paths received separate non-author review.
- One actual comparison: 24 cases, 96 attempts, 194 journal records, all six program checks true. Independent standard-library audit checked 569 source spans and 392 ratios without executing a candidate.
- One actual retained-result acceptance: assessed and delivered; 606 valid ledger events, 15 completed assessments, no unfinished run, successor investigate_decision_information_limits. All 114 pinned files retained their bytes and metadata; no candidate rerun.
- npm run build and three-link homepage evidence guard passed. Archived content contains 59 public records including protocol/result, excluding the draft internal record. Worktree generated content was restored after exact-byte archival.
- Final committed catalog ca5495b compiled: 135 nodes, 165 edges, 30 documents, 32 bibliographic sources; payload ca4aac73ec777f2f167d18d9e8fcdc6a469a859d6d8792d6f05416c26f7b7c92. Independent reviewer reproduced it.
- All 114 acceptance-gate files were archived as verified content-addressed copies before worktree removal. Repository commit checks and git diff --check passed. SCI update delivered through its existing native address; a new reply has not been verified.

## Not verified
No full-repository C8 suite, browser/rendered-layout inspection, accessibility audit, remote CI execution, push or deployment. No performance improvement claim for the existing 1.74 MB shared JavaScript bundle. No real payments, learned selector, representative business performance, independent timestamp witness or authority expansion. Program model calls/external spend are zero; agent/reviewer costs are separate and not fully measured. C9 is prepared, not implemented in this packet.

## Findings
- [medium] [fixed] Caller omitted both contract files from preclaim and postflight source pins.
- [low] [fixed] Public protocol described attempt starts that the journal does not record.
- [medium] [fixed] Missing report prevented hashing an available partial journal and obscured transport failure categories.
- [medium] [fixed] Retained validator accepted caller duration shorter than the enclosed program.
- [medium] [fixed] Nested process groups escaped the outer timeout; one owning group now covers the entire fixed invocation.
- [medium] [fixed] Private outer eligibility assertions disappeared under optimized Python; explicit checks now enforce them.
- [medium] [fixed] Malformed caller receipts and postflight failures could escape persistence or overwrite the original launch failure.
- [medium] [fixed] Unsupported experiment lifecycle status broke the unchanged knowledge catalog; results remain observed claims while design nodes keep the supported schema.

## Reviewer report
Independent C8 final landing review

Reviewer: /root/c8_whole_review. Verdict: fixed; no actionable finding remains in the reviewed final snapshot. This is a non-author landing review, including independent retained-artifact verification. It is not a deployment or visual-design certification.

Reviewed identity and scope

Repository worktree: /Users/ianderrington/git/ianderrington/epiphysics/.worktrees/decision-fresh. Reviewed base: 2a2427e14cd5b1c55e9db85fe017c805659fa85b. Final reviewed tip: ca5495b1deca9b00a388e4ea9411ed6ba2703d0b. The final worktree is clean. The complete committed patch contains 21 files, 2,472 insertions and 108 deletions (2,580 changed lines). The owner reports managed dry-run reviewed_patch_id ca6c72134f3ce8d702284753157893e8a0692d23; I independently verified the base/tip and Git diff size, not the implementation of the managed landing tool.

Scope includes the fresh caller/generator/runner, retained-result validator, controller transitions and tests; public protocol/result; homepage evidence; registry; roadmap and internal execution record. Private outer and acceptance wrappers, immutable actual evidence, acceptance transition and archives were also inspected as supporting execution evidence. I did not author production changes, commit changes, regenerate a cohort, invoke a candidate or acceptance, mutate the research ledger, push or deploy. The separately recorded audit code and this new review report are reviewer outputs. Earlier pinned review reports remain unchanged.

Findings and resolutions

The consolidated review packet contains seven medium findings and one low finding, all fixed, with zero open. Two medium findings and the low finding were found by this reviewer; five medium findings came from companion cross-reviews and were inspected here. Findings describe resolved defects, not open requests.

1. Medium, fixed; this reviewer: the caller originally omitted both registered contracts from its preclaim freeze. A changed contract could consume the one-shot invocation and be reported unchanged until later validation rejected it. engine/examples/control-exchange/fresh-caller.py:113-120 now requires the exact fixed contract keyset, bounded reads and digest matches before claim; both contracts participate in postflight checks at lines 178-186. I independently reproduced the original defect with a mocked child, then verified four controls: either preclaim mutation refuses with no child/no claim, and either during-child mutation retains a failed InputChanged receipt. No actual experiment ran in these controls.

2. Low, fixed; this reviewer: the protocol overstated journal evidence as attempt starts. docs/experiments/control-exchange-fresh-comparison.md:27 now describes each worker return and independently evaluated outcome, matching worker_returned and attempt_evaluated records. Interrupted-run evidence is no longer overstated.

3. Medium, fixed; companion cross-review: a missing report prevented retaining the hash of an available partial journal. fresh-caller.py:153-163 now captures the two artifacts independently and preserves transport/capture failure categories. I inspected the repair and final test evidence.

4. Medium, fixed; companion cross-review: the retained validator accepted a caller duration shorter than its enclosed program. engine/epiphysics/decision_assessment.py:515 now requires program duration no greater than caller duration. I inspected the regression and independently checked actual nested timings.

5. Medium, fixed; companion outer review, independently exercised here: nested processes created new groups and could escape the outer timeout. engine/epiphysics/decision_pilot.py:149-160 now always cleans the owning group, even after successful direct-parent exit; nested transports clean their direct child. fresh-caller.py:150 and decision_pilot.py:180 explicitly inherit the outer group. I independently ran seven harmless transport controls in 1.435 seconds, covering owning/nested timeouts, mocked worker inheritance, nested descendants under outer timeout, successful parent exit with a remaining detached-stream descendant, output cap/nonzero exit, prelaunch limits, and interrupted partial-output retention. All passed. These processes only slept or emitted test bytes.

6. Medium, fixed; companion outer review: optimization-sensitive assertions guarded private outer eligibility. execute-once.py now uses explicit exceptions for gates, predecessor, queue and frozen files. The companion review's 22 mocked controls include optimized Python refusal.

7. Medium, fixed; companion outer review: malformed/missing caller receipts could lose the original failure or escape outer persistence. The wrapper now performs a bounded single read, validates object shape, retains exact read identity/truncation, and records ordered stage failures including original launch and queue-postflight failures. I inspected the final wrapper and companion controls.

8. Medium, fixed; this landing review: registry experiment status reported_exploratory_result violated unchanged knowledge.py's proposed-only design-node contract and caused compilation to fail. I independently reproduced ValueError: experiment nodes must have status: proposed. research/meta-representation/registry.json:702 now retains status proposed; completion is represented by observed claim/document nodes and the authoritative runtime queue. I checked node/edge/path validity and independently compiled the final committed catalog read-only. No frozen engine code was changed for this repair.

The internal record's historical opening was also clarified to “Preparation began”; this minor wording correction is not counted as another material finding.

Independent actual-result audit

I wrote a separate standard-library-only audit over the retained cohort, raw worker outputs, source provenance, report, journal, custody and receipts, with read-only SQLite access. It imports no engine and executes no candidate/view/policy or generator. Its final result passed 5,713 checks: the exact 89-file execution gate matched; 104 original files retained their bytes, sizes and modification times; 96 rows, 194 journal records, 569 source spans and 392 aggregate/stratum ratios were checked. Public input bytes/hashes, worker requests/responses, coverage/index provenance, lossless references, world/observer/effect arithmetic, paired comparison and successor were independently reconstructed. Original C7 continuity and hash-chain prefix matched. An initial audit-only invocation encountered a serialization error in my audit helper; that helper was repaired and only the audit rerun. The registered experiment was not rerun.

The 24-case result contains 11 world opportunities, 9 visible actionable opportunities, 7 forbidden cases, 3 duplicate opportunities, 4 not-ready/invalid cases and 21 ordinary cases. Both compact arms completed 7/11 world and 7/9 visible opportunities; both lossless controls completed 9/11 and 9/9. All arms proposed 2 unauthorized, 1 duplicate and 3 invalid-artifact releases out of 24. Compact arms held 11/24; lossless arms held 9/24. There were no failed outputs, unauthorized effects or duplicate effects.

The compact paired comparison has two flat-only successes (fresh-pressure-03/04), two relational-only successes (fresh-pressure-01/02), five joint successes and fifteen joint nonsuccesses: net difference zero. The independently selected next action is investigate_decision_information_limits.

Crucially, every arm accepted three simulated invalid-artifact releases: fresh-late-02, fresh-auth-02 and fresh-dispute-02. The authority/duplicate guard does not establish artifact quality. Zero unauthorized/duplicate effects must not be read as zero harmful releases. The public result, homepage and registry explicitly preserve this distinction. The later 3/10 compact and 3/12 lossless accepted-release fractions are correctly labeled post-experiment diagnostics, not preregistered C8 metrics. No real payments occurred.

Actual program wall time was 5.823359042 seconds, caller time 5.902033875, outer transport 5.973342000, and outer preflight through caller reap 6.120405417. The 30/60-second limits remain unchanged. The outer interval includes caller final receipt persistence and excludes the outer supervisor's later postflight/persistence. Program model calls and external spend are zero; agent/reviewer costs and memory are unknown rather than zero.

Pinned audit identities, SHA-256:
- actual-artifact-audit.py: 0e335a9ed7fe7f2c1cecc341ee0a4762388c0662db55b8070ea5f498f93a0624
- actual-artifact-audit.json: d799465517c71155b7a6d425d610ed2f8d1caef171d7075ccf538c12ba787444
- actual-artifact-audit.md: 87c9bb807731f69a792932eaaaf136c3fa26875f4cce1b46def7d6e5062bac14
- actual report: 9375a4063da5e72a45931614386007f56c0c523176742c19ce52a7d9a8973098
- actual journal: 27234b1046e810a6db2531577de29d4ee310192e2f82578f82b47cd0e0edba60
- original execution gate: ad8843e6cfb2af88f06c65d0d46b4d4a83a58d4813fac6c12c80a0cd6ee13f11

Independent retained acceptance and preservation checks

I read the retained acceptance and authoritative ledger without invoking acceptance. I independently recomputed the entire 606-event hash chain, checked 15 completed assessments and exact retained-transition equality, and verified event improvement:decision-fresh-20261126:complete at head 4d89e0f7672afd881ea0a9a8b95a3b31bc66f3c4d1e9934978b4392f4f7cc17a. The queued successor is decision-fresh-20261126:next / investigate_decision_information_limits, with no unfinished assessment. The overall assessment identity independently recomputes to 79be0abdc5398edbd59378c2f8831af458f642add9bd7709a7434ffaedc83c05 and decision identity to d7e72425a3984d8ae4a6e4e66a4febc0f531d37995ad5f510c5c6756618d2e8b. Input manifests and nested identity agree.

The actual acceptance receipts show delivered assessment, no inspection errors, no candidate reruns, dispatch wall 9.101681791 seconds and inner assessment wall 8.488063792 seconds. I independently matched every original 89-file execution-gate digest and all 114 acceptance-gate digests. I also verified the new archive index has exactly the acceptance gate's 114 paths/hashes; each content-addressed blob matches its digest, declared length and original source bytes. Archive index SHA-256: 04681e38a4ae4c0060498d1f8dae413ab0a4638cf47d21373b69c7a35e12a024. This preserves gated source copies when the worktree is later removed. These checks do not constitute a new acceptance or execution.

Final catalog and site integration

My independent read-only compilation from final commit ca5495b1deca9b00a388e4ea9411ed6ba2703d0b yields 135 nodes, 165 edges, 4 catalog files, 30 documents totaling 348,265 bytes, and 32 bibliographic sources. Node kinds are 49 claims, 30 documents, 13 experiments, 7 representations, 32 sources and 4 transformations. Payload hash: ca4aac73ec777f2f167d18d9e8fcdc6a469a859d6d8792d6f05416c26f7b7c92. The owner's retained 2026-11-26-ca5495b.json agrees (file SHA-256 3da86ef8445f29db2b255e630e887bc4fedf63f425744a93c5c682c8fa13afd8). The earlier 4a04636 preview is not the final catalog.

I checked all three homepage evidence anchors against current public text and the retained build content. Counts, paired limits, simulated bad-delivery result and successor agree with independently audited evidence. Protocol/result documents are public; the draft internal run record is absent from the 59-record public content artifact. site-build-content.json SHA-256 is e6541b9fb4898a201ea5a3de47f516ad373cc361645e24ecbbf4b863193c30b0. Roadmap, daily loop, internal record and registry consistently treat the information-limit diagnosis as next work, preserve exposed history and avoid claiming graph superiority or completed C9 work.

Validation attribution and limitations

Own execution: the four mocked contract controls, seven harmless transport controls, standard-library actual-artifact audit, read-only acceptance/hash-chain checks, final registry validation and committed-catalog compilation. No experiment or acceptance was rerun by this reviewer.

Inspected owner evidence: the final eight-module decision suite passed 158 tests in 9.708 seconds (9.932043541 seconds outer wall), with 79 source/test files unchanged. The earlier 155-test suite is historical, not the final validation. Five legacy controller/dispatch controls passed in 43.940 seconds (44.143925125 seconds outer wall), with 79 files unchanged; those controls predate the transport repair and cover unchanged controller paths. The site evidence guard passed three links and the production build passed with 16 static pages. I did not independently rerun these suites or build.

Inspected companion evidence: 22 private outer-wrapper mocks and 13 private acceptance-wrapper mocks passed. The acceptance wrapper review had no finding; the outer review's three fixed findings are counted above. I did not rerun these companion mocks.

No full-repository C8 test-suite claim, browser/rendered-layout inspection, accessibility/performance audit, publication or deployment is made. The existing 1.74 MB shared first-load JavaScript is not an improvement established by this patch. The research cohort is one hand-designed exploratory batch, not a representative benchmark, confidence estimate, demonstrated learned improvement or business-performance result. Local timestamps, hashes and exclusive claims establish consistency within the retained workflow, not independent witnessing, global first exposure/sole execution or a new operating-system security boundary. Bibliographic catalog sources were not independently recaptured by compilation.

The reviewed snapshot is suitable for the owner's managed landing process with these stated limits. This report is final and must be copied verbatim without modifying the previously frozen evidence.
