---
title: "Two domains, one assessment lifecycle"
description: "An engineering fixture protocol separating preserved evidence, process completion and accepted measurements."
date: 2026-11-26
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

This protocol checks whether reference selection and artifact quality can use the same bounded assessment lifecycle. All cases are invented and all answers/artifacts are supplied in advance. No candidate generates a new prediction. The resulting scores measure conformance to explicit fixture rules, not general correctness, research quality or predictive advantage.

The reference fixture has five cases: exact required references; required references plus a valid extra field; an invalid reference; missing required evidence; and abstention. Its strict policy accepts 1/5. An alternate policy allowing valid extras accepts 2/5, but the changed policy makes those measurements incomparable as an improvement claim. Valid extra evidence, false evidence, missing evidence and abstention remain separately visible.

The artifact fixture has four cases: a conforming JSON object, the same object with an incorrect expected digest, a non-object JSON value with a matching digest, and abstention. Its declared rules accept 1/4. Byte limit, digest match, object format, required keys and extra-key permissions are separately reported. This tests mechanical obligations only.

Each domain must pass through the actual allowlisted CLI, separate assessment process, retained input/output/process receipts and parent-owned atomic completion. The fixed child program and static adapter registry are identical across both runs. A child report without parent acceptance must leave the queue unchanged. The accepted result includes fixed total/family denominators and keeps general accuracy and predictive advantage unknown. Fixed task/evidence/expected obligations define the cohort; a separately hashed outcome manifest binds supplied answers/artifacts to that cohort. Changing those answers must preserve measurement identity while changing the appropriate measurements. Mutation after preparation must refuse even when declared outcome hashes are recomputed.

Controls cover duplicate attempts, stale or foreign ownership, changed parent checkpoint, modified input/source/policy, missing acceptance after child success, original deadline expiry, interruption during publication or locked closure, and delivery loss after durable completion. Failure handling must preserve original attempts and deadlines; it cannot silently replay them. These are local controls under a surviving trusted supervisor, not hostile-host isolation or independent timestamping.

The reuse check saves a real reference-only source checkpoint before adding artifact quality, then compares shared lifecycle/controller sources byte for byte. The second adapter may add its own scorer, registry entry, fixtures and tests; it must not require a new domain branch in the generic controller. A source-code comparison does not measure total implementation effort or prove reuse for arbitrary future domains.

The [run record](../planning/runs/2026-11-26-work-contracts.md) records actual outcomes. The original C12 failed assessment is outside this experiment: its inputs, scoring and diagnosis queue are preserved, and no actual study is rerun or migrated.

Independent review added real delayed-write controls at the terminal SQLite commit, failure-recovery commit, authoritative lookup and final receipt persistence. A crossed deadline must return explicit late delivery with automatic continuation disallowed, even when the original event is durable. It must retain exactly that one terminal event and never report ordinary timely success. These injected delays exercise the observation boundary; they do not prove bounded disk latency. Consumers require successful parent delivery and its timing classification before continuing; the ledger alone does not enforce that consumer rule.
