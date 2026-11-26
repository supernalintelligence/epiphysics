---
title: "Representation manifests and the next executable step"
description: "Stable method identities, bound forecasts, review fixes, and a measured handoff to transformations."
date: 2026-11-25
tts:
  enabled: false
feedback:
  enabled: true
---

On **25 November 2026, America/Los_Angeles**, B1 followed the completed assertion packet during the same active supervisor session. Three scoped builders implemented the API, executable capability checks, and docs/CI. Two independent reviewers checked the result and verified the fixes below.

## Implemented boundary

A representation manifest binds a specific representation and frozen snapshot to retained construction, configuration, ontology and predictor artifacts, exact declared evidence, task/horizon, unit labels and construction-cost claims. Its stable method ID excludes snapshot-instance IDs and actual cost, so recapturing identical artifacts preserves method identity while changing an encoding or artifact creates a distinct method.

The forecast adapter fixes the representation, snapshot, method and manifest reference. It records a supplied probability; it does not execute the predictor. Costs remain reported or unknown, with unknown quantities retained as null. Artifact and receipt hashes do not prove execution or independently verified expenditure.

## Actual assessment

| Contract | Result |
| --- | --- |
| Representation oracle control | 30/30 across seven families |
| Source spans | 8/8 |
| Assertion history | 6/6 |
| Manifest and forecast bindings | 22/22 |

The manifest probe contract is **`representation-manifest-probes-v2`**, and the policy is `offline-contracts-manifests-v3`. Every check exercises the real API on a fresh synthetic ledger. The oracle still copies expected answers; neither these results nor the new metadata establish predictive improvement.

A real worker consumed `source-assertions-20261126:next` and recorded **`representation-manifests-20261126:next`**, action **`build_representation_transformations`**. The new contract differs from the prior one, so the comparison is `incomparable_contract_change`, with no delta or target-achievement claim. Transformation preservation remains unmeasured.

Dispatch `c44d3995cb3f483d92c748d804c9dd32` started at **2026-11-26T04:50:23.293374+00:00**, ended at **2026-11-26T04:50:23.740104+00:00**, returned 0, and took 0.447 seconds. The assessment recorded 0.312 seconds, zero model calls and zero external spend. Exact inputs and process receipts remain in the dedicated local improvement store. The reviewed worktree was assessed before local integration; this is not remote deployment or independent timestamping.

## Review and verification

**158 engine tests passed**, including 27 manifest tests, nine probe/CLI tests, 32 controller tests and four new core callback tests. The production site build passed; its existing configuration skips TypeScript/lint validation, and no TypeScript source changed. Both updated CI steps passed locally with a runner temporary directory configured. An initial local harness invocation lacked `RUNNER_TEMP`; supplying the environment used by CI resolved that harness error without changing the workflow.

Review found two related defects. A retained blob could change after forecast preparation but before writing, and an identical retry after blob loss could fail before reaching idempotency handling. New writes now revalidate bindings in the ledger's write-lock validator, after the existing deadline/duplicate checks. Preparation reads immutable metadata, allowing an identical retry to return the original event after blob loss. Changed retries still fail. Returning historical metadata does not certify present blob availability; integrity verification continues to report missing or corrupt evidence.

The version-two probes explicitly mutate predictor and inference-receipt bytes at the append boundary and test exact replay after loss. Mutation controls detect removal of the validator or broken replay. The earlier source/code/dependency identity safeguards remain in force.

## Immediate continuation

The next builder will execute **B2a: graph identity and projection**, with retained recipe/configuration, parent/output bindings, generated outputs and explicit losses. It will accept no caller-supplied output and execute no arbitrary artifact code. Split/merge and broader encoding support remain later B2 work. B1 therefore completes the manifest slice, not all of Packet B.

The supervisor continues into that queued work during the active session; the existing 15-minute heartbeat is a recovery backstop. Each step still requires actual execution, independent review and a measured successor.
