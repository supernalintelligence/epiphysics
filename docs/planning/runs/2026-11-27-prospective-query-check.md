---
title: "Prospective query-content checker implementation record"
description: "Frozen literal controls and first bounded invented raw-to-saved-view comparison."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

The [content checker contract](../prospective-query-check.md) fixes comparison and schema-error rules before execution. Work is scoped to the new checker, its tests, these two planning documents and the experiment overview. C16 oracle, candidate normalizer/views, their tests, the declaration and prior evidence are frozen dependencies. The original C12 study is untouched. No source commit or integration is performed by this builder.

Literal controls and the two selected C16 baseline raw fixtures are frozen privately under `prospective-query-check-v1`. The first executions and independent review will be appended below without overwriting their receipts. The builder's total test/comparison process allowance is 180 seconds; the independent critic receives 90 seconds. Agent effort and monetary cost are unmeasured/null. Nested phase durations are not summed with outer wall intervals.

## Executed controls

The first literal run passed **20 tests**, with zero test failures. The literal source and complete expected result were copied and hashed before execution in `literal-freeze-v1`; `literal-run-01` retains stdout, stderr and its process receipt. The unittest-reported nested duration was 0.018 seconds and the enclosing process wall interval was 0.286391417 seconds. These are overlapping measurements, not additive costs. Subcases exercise the listed malformed-schema, support, type and numeric boundaries; twenty is the test-method count, not a claimed count of independent observations.

Execution used `/Users/ianderrington/miniconda3/bin/python`, Anaconda Python 3.12.9, Clang 14.0.6, on macOS 26.5.1 arm64. The integer-digit guard remained 4,300 and recursion limit 1,000. Exact integers above 2^53 and at the 4,300-digit guard passed. A 4,301-digit value/key, nonfinite literals, overflowing/underflowing or overprecise decimal lexemes and oversize input produced the declared refusal/diagnostic behavior. No global runtime settings changed.

## First and only selected integration attempt

`comparison-freeze-v1` pins 52 files, including the exact two C16 baseline fixture directories and their copied raw bytes/literal expectations, oracle/candidate/checker sources and dependency tests, public contracts, declaration, prior support decision, supervisor content policy, and the private `compare-once.py` recipe. Its `pins.json` precedes execution. `comparison-first-attempt` retains all outputs and per-phase receipts; `comparison-process-01` retains outer stdout/stderr and exit status. The harness uses exclusive creation of the attempt directory and does not retry or import fixture helpers.

Both independent oracle envelopes exactly equaled the existing frozen literal answers and support. Both normalizations, four encodings and four decodings returned successfully, with exact saved/reread hashes and bytes matching. There were no exceptions, candidate schema errors, invalid references, duplicate eligible references, oracle unknowns or missing values in these two selected cases. The absence of those failures is bounded to these fixtures.

| Invented fixture | Arm | Planned / evaluable fields | Value matches | Supported-content matches | Missing-support fields | Additional eligible references | Content complete |
| --- | --- | --- | --- | --- | --- | --- | --- |
| One release baseline | Flat | 6 / 6 | 6 / 6 | 5 / 6 | 1 / 6 | 1 | No |
| One release baseline | Graph | 6 / 6 | 6 / 6 | 5 / 6 | 1 / 6 | 1 | No |
| One obligation baseline | Flat | 10 / 10 | 10 / 10 | 4 / 10 | 6 / 10 | 0 | No |
| One obligation baseline | Graph | 10 / 10 | 10 / 10 | 4 / 10 | 6 / 10 | 0 | No |

In both release forms, `seen_id_set` cited `a-open` and `z-prior` but omitted required `q-release`. Its value was correct. `opening_eligibility` recovered both required `a-open` and `q-release` and also cited eligible `z-prior`; that extra was reported and did not prevent its supported-content match.

In both obligation forms, `promisor_role_id`, `beneficiary_role_id`, `quality_rule_hash`, `acceptance_event_id` and `authorized_submission_channel_id` cited `a-accept` but omitted required `q-obligation`. `source_sha256` cited `a-accept` and `s-source` but also omitted `q-obligation`. All six values were correct; these are required-support gaps under the convention frozen before comparison. Common question fields and complete source membership matched. These results must not be repaired by changing required support to candidate behavior.

Release encoding sizes were 10,760 flat and 10,995 graph bytes; each decoded response was 582 bytes. Obligation encoding sizes were 6,579 flat and 6,672 graph bytes; each decoded response was 1,017 bytes. These counts describe precisely retained files, not general cost superiority. The comparison's outer subprocess wall interval was 0.468896541 seconds; the nested harness interval was 0.193745459 seconds, and nested release/obligation intervals were 0.007180542/0.005329583 seconds. Import, pin verification and receipt writes are included differently at these boundaries. Each call's inner duration is retained individually; overlapping intervals are not summed. Total builder test/comparison outer-process time was **0.755287958 seconds of 180 seconds**. CPU, peak memory, agent effort and monetary cost were unmeasured/null.

The first comparison is retained unchanged and is not rerun. Candidate normalizer, encoders/decoders, oracle, expected answers and prior artifacts remain unchanged. The two forms share their query implementation; equal results are not independent replications. The explicit calls demonstrate the tested data flow but do not establish hostile-host isolation or readiness of a registered runtime. All four results leave interface/runtime assurance unverified; there is no preservation certification or forecast eligibility.

## Review and next action

At final source freeze, the five owned files, unchanged root loop/TODO files, dependency and authority pins, exact base/diff and all receipts are captured under `review-freeze-v1`. A fresh unguided critic receives only location/base/diff/pins plus the read-only scope and 90-second independent-check allowance. Source stays unchanged pending supervisor adjudication. The independent review result is retained separately; the builder neither commits nor lands this work.

The concrete next candidate-repair packet is to recover question-contract support for release history and all six obligation-derived fields, inspect their shared normalization/query path, and separately review any resulting candidate change. This packet does not implement that repair. The checker may pass its own literal controls while correctly exposing candidate gaps. Five other families remain unmeasured, and the future 64-field-per-arm denominator is not substituted for these six/ten-field fixtures. There is no prediction, learning, calibration, causal or business-advantage claim and no original-study execution, live collection, paid/model request, transaction, registration or deployment.

## Independent review and bounded numeric repair

The first unguided critic found one P2: valid JSON zero with an extreme positive or negative exponent could raise `decimal.InvalidOperation` outside the documented parser boundary. The independent probes, report and the critic's initial wrong-working-directory test setup failure remain retained in `review-v1`. All 139 source/evidence pins verified before and after that review. Its 20 existing tests passed, but did not cover this numeric edge; total reviewer check-process time was 0.634653041 seconds of 90 seconds. The supervisor accepted the finding after inspecting the source and reproduction.

The authorized repair only catches Decimal conversion/comparison exceptions inside the numeric parser and translates them to the existing `numeric_limit` ValueError path. Candidate input yields explicit numeric-limit diagnostics; oracle input yields `CheckerRefusal`. Valid JSON syntax is not relabeled invalid syntax, and numeric globals remain unchanged. No support policy, expected answer, oracle or candidate implementation changed. The original source freeze, first comparison and failed critic probes remain immutable; the integration was not rerun.

Before checker-only validation, `repair-literal-freeze-v1` froze the source/tests and 18 specified numeric lexemes on both public inputs: eight operational-limit cases include positive/negative extreme-exponent zero, signed/decimal zero and nonzero extremes; ten nearby finite zero/nonzero cases must reach ordinary schema checks. The deliberately extra `probe` key distinguishes successful numeric parsing from a runtime limit. These add 36 literal boundary calls to the suite. All **22 checker test methods passed** on the first repair run. Its outer process interval was 0.115502916 seconds and nested unittest duration 0.017 seconds. Total builder test/comparison process time is now **0.870790874 seconds of 180 seconds**. These receipts retain the same Python 3.12.9 runtime, 4,300-digit guard and 1,000 recursion limit. Effort/cost remain null.

`repair-freeze-v1` separately pins the repaired five-file scope, exact repair/full diff, dependencies and retained evidence for the existing independent critic's recheck under its remaining allowance. Source is held unchanged during recheck; root integrates only after adjudicating closure. The original integration remains attributed to its original checker source pin, with the same 5/6 release and 4/10 obligation supported-content matches per arm. It is not presented as a rerun against repaired code.
