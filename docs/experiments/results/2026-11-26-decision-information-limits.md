---
title: "A complete record can still contain a wrong verification"
description: "Four of 22 verification claims disagreed with simulated artifact validity. Three positive claims led every method to release an invalid delivery."
date: 2026-11-25
draft: false
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

Four of 22 eligible verification claims disagreed with stipulated artifact validity. Three said pass for artifacts that the simulated world later identified as invalid. Every record method released those three deliveries, including both methods that kept all available evidence.

The fourth disagreement was a fail verdict for a valid artifact in `fresh-dispute-03`. This establishes a mismatch between the recorded verdict and the stipulated validity outcome. It does not establish dishonesty, intent, or how a real verifier would judge the artifact.

This [retained-evidence diagnosis](../control-exchange-information-limits.md) examined the [previous comparison](2026-11-26-fresh-decision-comparison.md): 24 scripted cases, four methods and 96 saved attempts. It generated no cases and reran no decision candidate. Each counted claim was available at the cutoff, effective by the decision, and bound to the relevant task, artifact and authorized verifier. The 22 distinct claims occurred in 22 cases; all had a stipulated outcome. Counting them once avoids multiplying a verification failure by the four methods that encountered it.

Each compact method lost two observable opportunities through bounded retention. The chronological and relational methods each completed seven of nine opportunities supported by available evidence, missing different cases. Both complete-record controls recovered all nine. Their equal totals give no overall advantage to either compact method in this batch.

| Measurement | Each compact method | Each complete-record control |
| --- | ---: | ---: |
| Completed opportunities supported by available evidence | 7/9 | 9/9 |
| Valid timely releases among all world opportunities | 7/11 | 9/11 |
| Invalid accepted deliveries among all cases | 3/24 | 3/24 |
| Invalid accepted deliveries among not-ready or invalid cases | 3/4 | 3/4 |
| Invalid accepted deliveries among accepted deliveries | 3/10 | 3/12 |

These denominators answer different questions. Three of the 21 positive verification claims concerned invalid artifacts. The four total verdict disagreements include the negative claim for a valid artifact. Neither count estimates a real service's failure rate: these mechanisms and outcomes were deliberately scripted.

More storage recovered missing evidence; it did not make the verification true. The simulated release guard checked authority and previous releases, not artifact quality. All 24 outcome revelations occurred after the decision cutoff. The diagnosis also distinguished 14 observed events whose effective times were still in the future. Later knowledge can explain a decision retrospectively without becoming evidence the decision maker had then.

The accepted diagnosis selects preparation of a dated evidence-quality protocol. The next step is to specify what would make one naturally occurring delivery check interpretable: versioned acceptance criteria, artifact and method identities, the actor and authority, the raw result, revisions, and separate observation, effective and outcome times. This is preparation only. No prospective collection, comparison, payment or live control change has been performed by this step.

All four diagnostic checks passed, covering 96 of 96 retained attempts with no unresolved rows. An independent standard-library audit reconciled the rows, original metrics, verification counts, timing boundaries and retention evidence without importing the engine or rerunning a candidate. Its 137 inspected input, output and gate files stayed unchanged during the audit. The auditor wrote the diagnostic tests and private invocation caller, but did not author the diagnostic core; other explanatory labels remain the diagnosis's claims, not independently proven causes.

Validation passed 191 decision-related tests, six legacy controller controls and 21 isolated caller mocks. This was not a full-repository test run. The first diagnostic computation took 0.147 seconds, excluding completion revalidation; the enclosing assessment took 12.517 seconds and caller dispatch took 13.529 seconds. These scopes overlap. Dispatch timing excludes later caller persistence and postflight inspection. Programs made no model calls or external expenditure; agent/reviewer work and memory costs remain unmeasured.

The reviewed implementation was commit `b79a726c07410495798a94524919c28a49abcf5e`. Invocation began at `2026-11-26T16:55:27.124835+00:00`; the controller accepted completion at `2026-11-26T16:55:40.133017+00:00`. The completion event is `improvement:decision-information-20261126:complete`, sequence 687, hash `de026ede9d29de02516e59119edd34ad63871f12ab434b554a71e0dd8636627d`.

| Retained artifact | SHA-256 |
| --- | --- |
| Accepted report, 29,662 bytes | `87fd9e53f6458933e3a8678d9afc2aa0046c2a1f7c270a7d64f105109e36185e` |
| Diagnostic table, 392,394 bytes | `7d1da05f7bfa9034647afd672b55fe38aaf7d64e94830ea7fee6d5e02e9e592a` |
| Independent audit, 51,002 bytes | `19a0f8a71c479da7ae86dac92bf3fe67d93c670b10452ed92aa14eedb0b6828c` |

These local records establish consistency, not independently witnessed prior existence or dataset completeness. The result concerns this simulation; it does not demonstrate predictive gain, real-world safety, or an autonomous system improving itself.
