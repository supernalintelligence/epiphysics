---
title: "Two compact records, different missed decisions"
description: "A twelve-case simulation found opposite retention failures and the same limit from a late revocation."
date: 2026-11-25
draft: false
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

Two ways of keeping a small record reached the same overall result and missed different decisions. The chronological view lost older essential evidence. The relational view lost recent essential evidence when nearby notes filled its storage budget. Neither view was better across these twelve exposed development cases.

The [experiment](../control-exchange-decision-pilot.md) concerns one delegated job and a proposed release of a simulation credit. Both views receive the same evidence available at the decision time, have a 2,048-byte storage limit, and use the same conservative decision rule. Graph metadata counts toward that limit.

| Measure | Chronological view | Relational view |
| --- | --- | --- |
| Completed opportunities supported by available evidence | 4/5 | 4/5 |
| Completed valid opportunities in the stipulated world | 4/7 | 4/7 |
| Unauthorized release proposals | 1/12 | 1/12 |
| Duplicate release proposals | 0/12 | 0/12 |
| Valid hold outputs | 7/12 | 7/12 |
| Missing or invalid outputs | 0/12 | 0/12 |

**The compact views each missed a different storage-pressure case.** With enough space to retain every available record, both control runs completed 5/5 observable opportunities and 5/7 world opportunities. Their decoded facts and decisions agreed with the independent reference. These controls check the implementation; their larger storage budget prevents a fair compact-view performance comparison.

**A record can be accurate about the past and insufficient for a current decision.** In one case, authority had been revoked before the decision, but the revocation arrived after the evidence cutoff. Both compact views and both lossless controls proposed a release. All four recorded that proposal as unauthorized in the simulated world. The stipulated-world guard refused it, so there were zero unauthorized effects. Zero effects demonstrates the common simulation guard, not the safety of either observer or a working distributed authorization service.

Two cases make that limit concrete: `dev-01` and `dev-02` supply exactly the same observer input, but authority remains valid only in the first. Every arm returned the same proposal for both. A deterministic decision based solely on that identical input cannot release the first and hold the second. Distinguishing them requires additional information or authority checks; holding both instead sacrifices the valid opportunity. This is an information limit under the stated conditions, not evidence that one graph design is inadequate.

There were seven world opportunities but only five that the complete available evidence justified acting on. Missing verification and conflicting verification account for the other two. Keeping these denominators separate prevents unavailable or contradictory evidence from being misreported as a storage failure. There were no invalid-artifact outcomes in this development set; the zero invalid-artifact proposal count does not test that failure mode.

The single recorded comparison retained all 48 attempts: twelve cases for each compact view and each lossless control. All six implementation and execution checks passed. The caller measured 7.753 seconds through child completion and final report persistence; this excludes the caller's own receipt persistence and all builder/reviewer effort. No models were called and no real payments or external control changes occurred.

The next step is a separately reviewed 24-case exploratory comparison with new cases, including invalid artifacts and dispute timing. The simpler chronological view remains the baseline. A small scripted comparison cannot establish general predictive advantage, company-level concentration, recursive adaptation or economic value. A later prospective test would need real dated receipts and its own authority and observation assumptions.

The retained result has SHA-256 `b4475ad656e3fa6224a1cfa43110b5635e64819876a8e06ffd5985624720d5f9`; its attempt journal has SHA-256 `78289a4abe277683998cd2a6804446756613c0204ca296f474c774eeace0ca40`. These are local integrity references, not independently witnessed timestamps. Owned inputs, code and a compact result summary are in `engine/examples/control-exchange`.
