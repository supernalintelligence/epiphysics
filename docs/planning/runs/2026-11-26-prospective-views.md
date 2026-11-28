---
title: "Persisted prospective view construction"
description: "First bounded table/graph implementation, saved-byte controls and remaining pilot gates."
date: 2026-11-26
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

The reviewed declaration v2 closes two policy ambiguities: decode only from the saved representation and enumerated public context, and register an input manifest without requiring its own digest or future receipt. This packet implements only the two view constructors and byte-only query decoders. The separate collector, independent raw-source oracle, producer/checker, registration bindings and timing support remain unbuilt for the pilot. No actual study, collection, registration or forecast issuance occurred.

One pure module defines the normalized typed-fact schema, chronological rows, directed graph edges and shared query semantics. Both encoders consume exactly the same input bytes; encodings retain their SHA256. No precomputed answer dictionary or constructor-state cache is stored. The module imports only JSON, regular expressions and the existing pure canonical JSON/hash/time utilities. Decoding reads neither files nor ledger/source APIs. This is inspected data flow, not an operating-system isolation guarantee.

The first scoped validation passed **21 tests**, with 0.054 seconds reported by unittest and **0.196441 seconds outer runtime** against a 180-second builder-test allowance. Retained evidence is private under `.supernal-local/prospective-views-v1/validation-r1/`, including full output, receipt, invented input bytes, saved encodings and decoded answers. No failing test was discarded. Whole-project suites and unrelated builds were not repeated.

Both families passed actual save/hash/reread controls. Release answers preserved ID `9007199254740993123` without floating-point loss, kept a prerelease/stable history, derived opening eligibility from booleans and retained malformed publisher metadata unchanged. Obligation answers preserved promisor/beneficiary direction and independently specified source/acceptance provenance. Swapping roles remained visible rather than being silently corrected. These are deliberately invented input facts, not verified statements about any actual organization or source.

The two loss controls remove all copies of a unique role fact and separately remove its provenance from a valid-format encoding. Both byte-only decoders refuse; neither consults the original packet. Other controls cover conflicting active claims, explicit revisions, revision cycles/forks, after-cutoff evidence, exact-cutoff eligibility, source-clock substitution, missing release booleans, empty versus missing opening samples, extra public query context, malformed JSON/UTF-8, input/encoding/output bounds and forbidden state/IO paths.

The declared observation/source metadata remains a claim until a future normalizer and independent oracle bind it to retained raw sources. Equal query results here establish scoped normalized-fact preservation only. They do not establish complete external evidence, a seven-family comparison, predictive advantage, independent evaluator correctness or live runtime timeliness. Parent and child timings must not be added to infer whole-step effort; agent/review effort, CPU/memory cost, success probabilities and next-action utility remain unmeasured/null. Program network/model/paid calls are zero for this packet.

Next: independent review of the frozen source and loss controls, then bind this component into the smallest reviewed runtime slice. No original C12 attempt or failed queue was consumed. Root separately maintains the loop/TODO updates in this worktree and checks content generation; this builder does not claim those checks as performed.

## First independent review and narrow repair

The independent critic reproduced two P2 defects in 0.123102 seconds using its own invented fixture. Removing the sample support from a superseding release-state correction let the original sample-filtering code resurrect a superseded value, flipping opening eligibility. Separately, moving graph entity references into literal slots preserved decoded answers while eliminating entity-target edges. The first frozen source, counterexample bytes, outputs and review remain unchanged in the private evidence directory.

The repair requires one explicit source sample for every release assertion and requires release revisions to stay within that sample. Genuine later samples remain distinct retained observations. A valid same-sample correction now overrides its old value; removing its sample support refuses instead of restoring the old value. Graph entity relations must use entity targets and cannot be disguised as typed literals. These changes repair the declared representation contract; they do not revise a scoring rule or a started study.

After repair, **24 scoped tests passed** in 0.070 seconds unittest / **0.191372 seconds outer time**. Three added controls cover corrected release-state provenance loss, cross-sample revision refusal and entity-as-literal graph refusal. The earlier 21 tests were repeated because the affected validators serve both encoders/decoders; overlapping executions are not independent research cases. Total recorded builder test time is 0.387813 seconds of the 180-second allowance. The repaired source and exact diff are separately frozen under `.supernal-local/prospective-views-v1/repair/` for the same critic's recheck. No actual study or source collection occurred.
