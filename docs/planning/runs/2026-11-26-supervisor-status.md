---
title: "Epiphysics — supervisor status"
description: "Current implementation, active agents, measured evidence and the next decision."
date: 2026-11-26
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

Checkpoint: 2026-11-26 23:36 UTC.

Codex is supervising the work: assigning bounded tasks, commissioning independent reviews, checking results, integrating changes and selecting the next step. Builders and reviewers execute separate assignments. SCI remains a separate collaborator, with a verified communication channel and no overlapping file ownership.

## Where we are

| Area | Evidence and current state |
| --- | --- |
| Website | Landing page, navigation, dates, diagrams and public research results updated locally. The combined build passed with 67 content records and 17 static pages. These changes have not been deployed or visually verified in a browser. |
| Knowledge catalog | 151 nodes and 182 relationships; the separate reviewed public selection has 61 nodes and 70 relationships. These are organization and coverage counts, not predictive-quality scores. |
| First evidence-reading trial | Six cases ran once. Five answers included all required evidence plus one valid title reference excluded by the scoring key; one case abstained. The provisional exact-match score was 0/6. Acceptance was interrupted by a process-inventory timeout. The original attempt is preserved and closed as a failure, with diagnosis queued. |
| Recovery | Independent failure audits and a reviewed caller repair are complete. The interrupted claim was reconciled without rerunning the trial. The new caller has not been used for another actual trial. |
| Shared task system | Two invented domains use the same dispatcher and parent acceptance path. After independent reviewers found two boundary defects, the repaired version passed 32 tests. Both fixes have been independently checked; local integration is next. |
| Prospective study | A concrete declaration is prepared and undergoing independent review for a small comparison of a chronological table and a typed temporal graph. Its pilot implementations and timing support remain unbuilt; it is not registered, collecting data or running. |
| Continuity | The 15-minute follow-up automation is active. It checks current state and workers before starting more work; availability still depends on the host and app. |

The C12 implementation, public trial diagnosis and homepage evidence update are integrated locally at `9d598f2301d9eafdb56e54a8862e1a14d73b3d61`. The shared work-contract changes are reviewed in the separate managed worktree and have not landed. The shared branch also contains the subsequent, separately owned mathematics update `27c75f46461728f27eea381dfd9923143c5b5a32`; it does not overlap these changes. Other agents' unrelated files are preserved.

## Who is working

| Worker | Assignment |
| --- | --- |
| Root supervisor | Priorities, task boundaries, evidence checks, review decisions, integration and reporting |
| Shared-contract builder | Initial implementation completed and frozen for review |
| Independent critic | Completed review; reproduced malformed legacy input taking over the new work queue |
| Independent safety reviewer | Completed review; reproduced a database commit crossing the deadline while returning ordinary success |
| Boundary-repair builder | Completed both fixes and 32 passing checks; independent reviewers confirmed the corrected behavior |
| Prospective-study researcher | Completed the proposed declaration; a separate critic is reviewing measurement validity and feasibility |
| SCI collaborator | Separate scientific work; actual acknowledgement received; has not independently checked our latest results or commits |

Worker states are this checkpoint's observations, not a claim that every worker runs continuously. The private supervisor record is updated as assignments change.

## What the evidence means

The first trial exposed a measurement-policy ambiguity: a valid extra citation was counted as an exact-match failure. The original key and scores remain unchanged. Future comparisons need explicit reference rules and new unseen cases; changing the key after seeing answers would not be a valid repair of that experiment.

The shared task interface now separates fixed tasks and expected obligations from submitted answers. Two methods can therefore answer the same questions differently without accidentally changing the identity of the comparison. Changing the cohort, measurement policy, denominator or pinned measurement implementation prevents an improvement claim. The two current adapters only assess invented retained inputs; they do not demonstrate general intelligence, predictive advantage or compatibility with the original trial's continuation.

Independent review caught defects that the builder's tests missed. One allowed malformed legacy input to consume a new work successor. The other showed that a deadline check before a database commit cannot prove the commit finished before that deadline. The repaired parent now reports an observed late publication as failed delivery with automatic continuation disallowed, preserving durable history. It does not add a receipt-gated ownership check: the supervisor must inspect the returned delivery status before advancing, and ledger status alone is insufficient. No arbitrary disk-latency guarantee is claimed.

## Next decisions

1. Finish recording the independent reviews and integrate the reviewed local implementation while preserving the separate mathematics update already on the shared branch.
2. Review the prospective declaration before registration. Its fixed 0.5 forecasts are integrity controls, not a proposed predictive advantage; compare evidence preservation, queries, abstentions and cost first.
3. Implement and validate only the collection and resolution components required by that declaration. Preserve missing observations as unknown and distinguish source dates from first observation and independent timestamps.
4. Use the resulting evidence to choose the next representation or method experiment. Estimated task utility and success probability remain unknown; the current selector uses explicit priority rules, not a learned predictor.

The research program includes organizations, software, obligations and value exchange. Published roles are not proof of actual control, payment settlement is not proof of delivered value, and blockchain timestamps can support prior existence without establishing truth or completeness. These distinctions belong in the representation and measurement design before broader claims about AI-company dominance or recursive systems are tested.

Human usability, predictive improvement, cross-domain generalization and self-sustaining distribution remain unmeasured. The immediate priority is producing interpretable prospective evidence and making the site explain the actual state clearly.

See the [preserved trial record](2026-11-26-evidence-navigation.md), [shared work-contract record](2026-11-26-work-contracts.md), and [public trial diagnosis](../../experiments/results/2026-11-26-first-evidence-reader.md). The user-facing status report does not authorize another run of the original trial or a deployment.
