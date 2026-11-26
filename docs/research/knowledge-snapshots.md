---
title: "We cannot test yesterday's predictions with today's knowledge"
description: "A draft essay on preserving evidence available before an outcome, model contamination, and the limits of timestamp proofs."
date: 2026-11-24T00:00:00.000Z
draft: true
author:
  name: "Ian Derrington"
contentType: article
status: "DRAFT FOR REVIEW"
tts:
  enabled: true
  provider: openai
  voice: onyx
  enableSpeed: true
  enableProgress: true
feedback:
  enabled: true
---

> **DRAFT FOR REVIEW — proposed first-person essay for Ian Derrington.** Prepared for review in the Epiphysics repository. It has not been published to Ian's personal site or social accounts, and the wording is not an approved personal statement.

I want to build systems that make better predictions. But before asking whether a model predicts well, I need to answer a less glamorous question: **what could it actually have known?**

Suppose I ask an AI system to predict an event from six months ago. I give it documents dated before the event, and it produces an impressive answer. What have I learned?

Perhaps the model recognized a real pattern. Perhaps the documents were edited later. Perhaps a search result supplied an updated summary. Perhaps the model encountered the outcome during training. A historical date in the prompt does not separate those possibilities.

The difficulty is not that all backtesting is impossible. Carefully preserved data and appropriate models can support meaningful historical tests. The difficulty is that a dataset that looks historical is not necessarily a record of historical knowledge. For many open-world questions, we cannot currently establish the stronger claim.

## The past has more than one clock

I want to preserve at least four different times. When did the event happen? When does the source say it published the information? When did our collector first record these exact bytes? When did an independent party witness a commitment to them?

These times answer different questions. A document retrieved today may accurately describe an event from last year. It still does not belong in a snapshot of what our system had collected last year. A publication date is a source claim, not permission to move an observation backward in time.

The archive also needs revisions, collection failures, and missing sources. Otherwise “what we knew” quietly becomes “what survived in the archive and looked useful afterward.” Retaining raw bytes alongside parsed text helps us notice when an extractor or document changed.

My working definition of a knowledge snapshot is deliberately modest: an exact record of the evidence a particular system had collected by a declared cutoff, with its provenance and known gaps. It is not everything anyone in the world could have known.

## Freezing the input does not freeze the model's knowledge

Even a clean archive leaves the model problem. A current model may know later outcomes through its weights. Restricting retrieval to an old snapshot does not remove that information. Asking the model to pretend it lives in the past does not demonstrate that it has forgotten the future.

I would still use historical tests to debug pipelines, compare encodings, and find obvious failure modes. I would label their temporal limits and avoid treating an uncertain backtest as clean forecasting evidence.

For the strongest initial test, I would make predictions now about outcomes that have not yet occurred. Record the question, resolution rule, probability, model identifier, prompt, tools, evidence snapshot, and cost before the deadline. Then wait. Regularly refreshed future questions have a practical precedent in [ForecastBench](https://www.forecastbench.org/about/).

Waiting is not wasted time. It is how a clean forward record comes into existence. If we want a trustworthy archive next year, we need to start collecting it this year.

## What a blockchain can help prove

A timestamp service is useful for one narrow part of this problem. [OpenTimestamps](https://opentimestamps.org/) supports proofs that committed data existed before a point in time. A non-blockchain approach is the time-stamp authority protocol described in [RFC 3161](https://www.rfc-editor.org/info/rfc3161/).

I would treat these as independent witnesses to a digest. They do not establish source truth, completeness, exact event time, or continued content availability. We must retain the bytes and proof, verify the receipt, and distinguish pending from completed attestations.

Batching snapshot and forecast commitments could make that layer practical. But committing only successful predictions would still mislead. We also need a registered question set, an attempt log, and a rule for including failures and unresolved outcomes.

Today, Epiphysics has a local hash-linked ledger, not an independent timestamp integration. That gives us an inspectable local record. A privileged operator could still rewrite the entire store; an outside checkpoint is needed to detect that kind of replacement.

## Why this matters for recursive AI systems

An AI company can use models to make decisions that change its resources, capabilities, and future access to information. Other organizations respond. The system we want to predict is learning and changing partly because of predictions made within it.

I do not want to assume in advance that this must end in permanent concentration or inevitable decentralization. I want representations that make competing mechanisms visible: access to compute, control over distribution, portability, switching costs, collaboration, and the costs of maintaining dependencies. The model should revise its boundaries when “one company” turns out to be the wrong unit of analysis.

To test those ideas later, we need a record of what was observable earlier. Otherwise it is too easy to invent a convincing explanation after the outcome and mistake it for foresight. The same concern applies to our research loop: preserve what a candidate saw before it was judged.

## The small system I would start with

Preserve selected sources and revisions. Freeze a snapshot. Register a narrow question with an unambiguous resolution rule. Compare a simple baseline with a richer representation under a declared budget. Record every attempt. Resolve from later evidence. Publish enough for someone else to reproduce the comparison.

Repeat that process before adding an ambitious optimizer or payment network. Make the archive exportable and evaluation independent. Add a witness that verifies a limited timing claim, and describe the limit clearly.

The broader opportunity is shared infrastructure for remembering what was knowable. A useful contribution could be a clean snapshot, a careful question, a correction, or a reproduction. Other people can build on these even if they disagree with the theory that inspired the project.

The [research program](/research/recursive-research-program) and [prospective protocol](/experiments/prospective-observatory) describe the implementation and current limits.
