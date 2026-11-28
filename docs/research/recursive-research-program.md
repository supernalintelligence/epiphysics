---
title: "The Epiphysics research program"
description: "How Epiphysics will preserve evidence, compare representations, and study systems that change themselves."
date: 2026-11-24T00:00:00.000Z
draft: false
author:
  name: "Epiphysics"
contentType: article
tts:
  enabled: true
  provider: openai
  voice: onyx
  enableSpeed: true
  enableProgress: true
feedback:
  enabled: true
---

Epiphysics is building a way to ask a practical question: **does a better description of a system help us predict what happens next?** We preserve the information available at the time, compare different descriptions, make predictions before the result, and keep the record when an idea fails.

The first implementation is a local evidence and forecast ledger. It can preserve exact files, record source revisions, freeze an evidence snapshot, register predictions, and compare them with later outcomes. A simple collection cycle predicts whether a source's bytes will change, always using probability 0.5. That checks the plumbing. It is not a learned forecasting system or evidence that Epimechanics works.

[See the five-step overview](/overview) or [inspect the observatory example](/observatory). The example is synthetic and labeled accordingly; its illustrative numbers are not live research results.

The [public research map](/research-map) makes a curated set of claims and their relationships inspectable. Search a claim, read its status and basis, then follow directed citations, qualifications, and proposed next tests. Bibliographic sources remain distinct from measured results; the diagram uses the same relationships as the text list.

## Start with the description, not a fixed list of things

Consider an AI service that depends on a model provider, a data source, and a distribution platform. One description treats the service as a single company. Another treats it as a network of dependencies. A third follows the people and decisions that control access. Different descriptions may help predict an outage, a product release, or the cost of switching providers.

We want a system that can propose these alternatives and test them. It might split one entity into several, group several into a working unit, add a missing dependency, or discard a distinction that does not help. Its representation is a model of the world, not the world itself. A graph is one possible format; text, learned state variables, and executable models may also be useful.

Every proposed entity and relationship needs evidence and an uncertainty label. Something directly recorded, something a source reports, and something the model infers should look different. A model's guess about an organization's beliefs must remain a guess.

## The same loop, used carefully in different places

1. **Observe:** preserve what was available, including changes and missing captures.
2. **Represent:** propose entities, relationships, and alternative explanations.
3. **Predict:** record what would happen, with a probability and a clear deadline.
4. **Evaluate:** compare with later evidence, including cost, failures, and uncertainty.
5. **Revise:** keep useful changes, reject unsupported ones, and make the comparison reproducible.

Our first environment is our own software and agent work. Tasks, tool calls, dependencies, completion times, and failures can be measured directly. We can sometimes make controlled changes and see what follows.

Our second environment is the public activity of AI organizations and their dependencies. Here we have less control and incomplete evidence. We will begin with narrow questions whose answers can be checked from declared sources. A result in the first environment does not automatically transfer to the second.

## Systems that change themselves

The important pattern is recursive: an organization uses a model to make a decision; that decision changes its resources or dependencies; those changes affect what it can learn and do next. Our own research system is part of the same pattern.

This makes AI concentration and distributed value exchange research questions. Better capabilities may help a company accumulate resources and control. Portable tools, competing providers, and open interfaces may push in another direction. Infrastructure and coordination limits may constrain both. We should preserve evidence for competing explanations rather than decide the answer in advance.

“Control” needs concrete measurements: who can set access rules, allocate a resource, alter an interface, or prevent a dependency from being replaced? Money received, useful work delivered, reputation, predictive accuracy, and control are related possibilities, not interchangeable measures.

We will first study exchange in a small simulation. One agent offers a service, another accepts, the work is delivered and checked, and a transfer or dispute is recorded. Services could include collecting evidence, producing a forecast, supplying computation, or reproducing a result. Payment technology is an adapter to this process. The scientific question is whether the arrangement produces useful work and how it changes dependency and control.

Predictions and published models can themselves affect behavior. That is why the planned record includes actions and exposure, not just forecasts. This concern is studied explicitly in [Performative Prediction](https://proceedings.mlr.press/v119/perdomo20a.html).

## How modern AI fits

AI can retrieve relevant evidence, propose competing representations, write candidate programs, and suggest experiments. Each proposal needs an explicit resource budget and a fixed evaluation rule. A more elaborate representation earns its cost only if it helps on new cases.

The planned comparisons include a simple statistical baseline, an LLM given raw evidence, a fixed entity model, and an entity model allowed to change. They must see the same eligible evidence and receive declared, comparable budgets. Representation construction and retrieval count toward cost. A visually impressive graph is not an evaluation result.

Autonomous improvement is a later component. The current collection cycle makes no model calls. Before enabling an optimizer, we need limits on spending, time, retries, and candidate count; a separate evaluator; and a record of every rejected change. Two-way contact with the Epiphysics SCI Claude session has been established through project messages. Its review of this observatory and an integration agreement remain pending.

## Temporal evidence

A date on a web page does not prove what the page said on that date. A later edit can silently change the evidence a historical test uses. A current AI model may also already know how a historical event ended, even when its prompt contains only old documents.

We therefore prioritize forecasts about future outcomes and retain exact evidence as it arrives. Historical experiments remain useful for debugging and exploration, but their claims must match their temporal limits. Repeated future-event evaluation also has precedents such as [ForecastBench](https://www.forecastbench.org/about/).

Independent timestamps are planned. They can support a claim that committed data existed before a time; they do not establish that the data were true or complete. The local implementation currently has no external witness. The [prospective protocol](/experiments/prospective-observatory) explains the timing limits.

## What would count as progress?

A useful early result is a stranger reproducing a score from the same evidence and finding the same answer. A stronger result is a representation improving a preregistered future comparison at matched cost. A stronger result again is that benefit surviving in a different environment.

We will also count failures honestly: a representation may add cost without helping; a question may prove unresolvable; a method may fail to run; a promising effect may vanish on new data. The [prospective protocol](/experiments/prospective-observatory) explains how those cases remain visible.

Epimechanics is the theoretical program motivating some candidates. Its broad claims are not established by this infrastructure. An entity is anything representable, auto-causal density concerns persistence rather than entityhood, and the Lagrangian is a structural postulate. Earlier abandoned tests do not become new evidence because the interface improves.

## Make the work useful to someone else

The contribution path should be concrete: inspect one forecast, reproduce one result, challenge one resolution, contribute one clean source, or propose one question with a clear answer rule. A useful result should carry its evidence, method, cost, and limits wherever it is shared.

We will measure successful reproductions and contributions, not assume that a project becomes viral because it has an animation. The moving points in the overview illustrate how descriptions can change; evidence must come from the experiments.
