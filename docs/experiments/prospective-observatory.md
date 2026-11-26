---
title: "Prospective observatory: evidence and evaluation protocol"
description: "Compare representations on future outcomes with frozen evidence, declared budgets, and explicit temporal limits."
date: 2026-11-24T00:00:00.000Z
draft: false
author:
  name: "Epiphysics"
contentType: article
status: "Draft protocol; no confirmatory cohort registered"
tts:
  enabled: true
  provider: openai
  voice: onyx
  enableSpeed: true
  enableProgress: true
feedback:
  enabled: true
---

> **Status: instrumentation implemented; scientific comparison planned.** This is a protocol template, not a preregistered completed experiment. Cohort, dates, sample target, budgets, effect threshold, and independent resolver must be filled and committed before confirmatory use. The engine provides a constant-baseline collection cycle and descriptive scoring, not an autonomous learned predictor.

## Question and hypotheses

Can revising a representation of entities and dependencies improve prediction on future outcomes at a declared resource budget?

**Primary comparison proposed:** evolving entity representation versus the same model using raw eligible evidence, evaluated on matched questions and snapshots. **Secondary comparisons:** fixed entity representation; base-rate/statistical baseline; construction cost; transfer to another environment. The current constant 0.5 method is an instrumentation baseline, not a strong scientific comparator.

The null is no useful improvement at matched cost. A favorable result supports the tested method on the tested population. It does not establish universal mechanics, prove that discovered boundaries are uniquely real, or validate every Epimechanics claim. Abandoned persistence and ladder tests are outside this protocol; an improved interface does not revive them.

## Registration before a confirmatory cohort

| Field | Required declaration |
| --- | --- |
| Population and source coverage | Environment, source allowlist, selection process, exclusions, expected missingness |
| Questions and dependence | Templates, families, horizons, eligibility, target/minimum resolved sample, clustering unit |
| Timing | Start/end, deadlines, cutoff rule, resolution/lateness window, witness requirement |
| Candidates | Frozen method/code/prompt/model, construction procedure, allowed memory, tools, update policy |
| Resources | Currency, tokens, calls, wall time, bytes, concurrency, retries, shared-cost allocation |
| Outcomes | Resolution source/rule, independent resolver, disagreement, corrections, unresolvable cases |
| Analysis | Primary loss, benefit threshold, interval procedure, dependence, multiplicity, coverage constraints |
| Stopping and promotion | Fixed cohort or sequential rule, budget stop, outages, candidate acceptance, rollback |
| Reproduction | Artifact manifest, environment/version receipt, retention, export/replay instructions |

Empty fields mean exploration only. Do not select a sample target, favorable subgroup, or stopping time after seeing outcomes and call the experiment preregistered.

## Evidence and temporal eligibility

Capture raw bytes before extraction. Record source identity, content hash, claimed publication/event times, collection time, revisions, and failures. Eligibility follows collection time. A document first imported after the cutoff is ineligible even if its publication date is older.

Freeze a manifest before a forecast. Representation evidence and inherited memory must be eligible for that snapshot. Record extraction/representation versions. The engine enforces snapshot evidence references and basic temporal lineage; semantic leakage through arbitrary model metadata or an external service still requires protocol controls.

The local ledger is independently unwitnessed. Chain/blob verification checks retained local integrity, not the honesty of its clock or completeness of history. A proposed witness adapter must establish that a snapshot/forecast commitment existed no later than the relevant deadline. Verification may finish later, but its proven time bound must satisfy the deadline before the result is called witnessed. Until then, timing assurance is **local collector record only**. Pending/failed submissions are not verified. A witness does not establish truth, completeness, exact event time, or continued content availability.

## Model contamination and changing models

Historical evidence snapshots do not prevent a current model from knowing historical outcomes. Historical replay is diagnostic unless model temporal exposure is established. The main evaluation predicts outcomes that have not yet occurred.

Record available provider/model/version identifiers, execution time, prompt, tools, retrieval rules, and provider fingerprint. Mark provider changes and segment analysis; do not silently treat a changed model as the same fixed method. Preserve retrieval responses, not only queries. No candidate may retrieve an outcome while answering its question.

Optimization can learn from completed development cohorts. Final evaluation uses a newly frozen future cohort whose outcomes were unavailable during selection. Declare any adaptive update policy as part of the candidate. Repeatedly inspecting held-out results turns them into development data.

## Two environments

**A: software and agent work.** Begin with whether a registered task completes within a limit or a scheduled run fails under defined conditions. Preserve task definitions, dependency state, tool traces, and result criteria. Randomized interventions can support causal claims where practical; observational prediction alone cannot.

**B: public AI organization activity.** Use declared official sources and narrow events such as a named release appearing in a specified registry within a window. Separate publication, service availability, and adoption. Record uncertain boundaries and dependencies. Control claims require operational variables such as access rules, resource allocation, or substitution costs.

Representations can use text, graphs, latent variables, or programs. Test splitting/merging entities and changing directed relations against fixed alternatives. A transfer cohort in B follows selection in A; it is a new test, not a pooled claim of universality.

## Forecasts and resolution

Each method records one prediction, abstention, or failure per question before its deadline. Failed/abstained attempts retain a reason and no probability. Include construction/inference cost even for failures. The engine prevents a second attempt by the same method on the same question; a new horizon or revision needs a new registered question and eligibility rule.

A resolver applies the declared rule to later evidence independently of which method benefits. Disagreement and insufficient evidence remain visible. Never force an unresolved question to zero. Corrections append a resolution superseding the previous one; reports identify resolution IDs. Keep original and corrected versions when a published score changes.

Questions used to choose actions need an exposure/action record. Report observational forecasts separately from intervention effects because acting on a forecast can change its outcome.

## Scoring and interpretation

For binary forecasts, the initial loss is Brier score: `(probability - outcome)^2`, with smaller values better. Compare methods on the same question and snapshot. Report matched/attempted samples, predicted/failed/abstained counts, pending/unresolvable outcomes, coverage, cost, and per-family performance. Do not report only the subset a method chose to answer.

The engine's `compare` returns right-minus-left mean Brier loss for matched question/snapshot pairs. It does not enforce budgets or estimate significance. Its `score` uses the latest resolution correction and retains that resolution ID per row. These outputs are descriptive.

Before confirmatory use, add calibration, cost accounting, and uncertainty estimates that respect related questions, entities, and overlapping horizons. Ten versions of one event are not ten independent discoveries. Predeclare minimum coverage and how failures affect usefulness; low loss on very few answered questions is not automatically a win. A rule may include explicit failure cost but cannot retrospectively invent probabilities for failed forecasts.

Promotion requires registered benefit, coverage, and cost gates on a new prospective cohort. Retain null, negative, and inconclusive results with their artifacts. Statistical benefit in one experiment establishes neither causal mechanism nor transfer.

## Run the implemented plumbing

From the repository root, create an explicitly synthetic example in an empty store. It uses fictional data and an injected clock; never merge it into empirical evidence:

```bash
PYTHONPATH=engine python3 -m epiphysics --store /tmp/epiphysics-synthetic-example demo
PYTHONPATH=engine python3 -m epiphysics --store /tmp/epiphysics-synthetic-example verify
```

For a real-time local collection cycle using the repository fixture:

```bash
PYTHONPATH=engine python3 -m epiphysics --store /tmp/epiphysics-local-capture cycle --config engine/examples/local-cycle.json --run-key first-capture
PYTHONPATH=engine python3 -m epiphysics --store /tmp/epiphysics-local-capture verify
```

The example horizon is 120 seconds. After that horizon and within the lateness window, use a new run key to capture again and resolve the earlier question:

```bash
PYTHONPATH=engine python3 -m epiphysics --store /tmp/epiphysics-local-capture cycle --config engine/examples/local-cycle.json --run-key second-capture
PYTHONPATH=engine python3 -m epiphysics --store /tmp/epiphysics-local-capture score
```

No file change is needed to test an unchanged outcome. Every successful cycle opens a new question, so the latest forecast stays pending. Reusing a completed key returns its result without collecting again. Inspect interrupted runs and use a new key rather than blindly replaying. Synthetic demos require fresh empty directories; existing evidence is never overwritten.

The cycle compares exact hashes at the first successful capture inside the resolution window. It does not determine when a semantic event happened; a file that changes and changes back can have the same final hash. The constant 0.5 baseline makes zero model calls and scores 0.25 on every resolved binary outcome. This checks instrumentation, not predictive skill.

The runner accepts 1–10 sources, a 1 MB capture limit per source, and a 10-second HTTPS timeout. It records failures and expires questions that miss the window. A local app heartbeat now schedules bounded work. Machine-enforced total wall-time/spend budgets, semantic source adapters, model optimization, witnesses, and exchange actions remain planned.

## Reproduction and release gate

A result bundle needs its registration, eligible evidence where redistribution permits, hashes for restricted evidence, all questions/attempts, candidate/environment receipts, resolutions/corrections, scoring implementation, costs, and limitations. Restricted inputs limit independent reproduction; hashes cannot reproduce missing content.

A separate operator should reconstruct snapshots/scores and verify declared witness status. Public summaries distinguish **synthetic**, **locally recorded**, **independently witnessed**, **unresolved**, and **corrected** where applicable. A mock display is not a live ledger.

The [implementation plan](/planning/2026-11-24-recursive-observatory) assigns the next gates. [The research program](/research/recursive-research-program) explains the purpose without requiring the reader to adopt the theory.
