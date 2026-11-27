---
title: "Prospective saved-query dependency-support repair"
description: "New frozen engineering conformance for question-binding ancestry in two saved forms."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

C18 addresses the dependency loss retained by the [first C17 comparison](./2026-11-27-prospective-query-check.md). That immutable comparison recovered 6/6 release values with 5/6 supported-content matches and 10/10 obligation values with 4/10 supported-content matches per form. It is not rerun. The current checker includes C17's later numeric-boundary repair, so this packet has a different measurement implementation identity as well as new candidate code and new invented cases. Results are new engineering conformance, not a before/after improvement estimate or causal attribution.

The expected target is exact values plus full encoded dependency support in every newly declared valid case, with missing required facts/support remaining explicit failures. Scope is `prospective_views.py`, its tests, permitted provenance-only literals in `test_prospective_inputs.py`, this record and the experiment overview. Root-owned loop/TODO changes are preserved. Oracle, checker, raw normalizer, their tests/acceptance rules, public contracts, declaration and old evidence remain fixed. Original C12 stores/candidates/keys/runner are outside the packet.

## Exact change and dependency boundary

The shared query already resolves the active `question.subject` fact to choose the subject. Derived answers now retain that selected fact's encoded observation references: release history, opening eligibility, the five direct obligation fields (promisor, beneficiary, quality-rule hash, acceptance event and channel), and source hash. Source hash retains the explicit `obligation.source` edge's support and the selected source hash fact's support as well. No hardcoded receipt label or whole-observation append supplies these dependencies. Active equal-valued facts retain their existing combined support; superseded support is not revived. Source membership continues to report all included observations, as before.

Both decoders still accept only persisted encoding bytes and public field grammar. Oracle, expected values and raw bytes are not decoder arguments or globals. No value, time, role direction, revision, identity, optional publisher metadata, admission rule or size limit changes. The existing release sample support remains, including every valid empty/prior sample. The broader existing opening support remains eligible extra support under the fixed checker policy.

Legacy expected-provenance literals change only as allowed by C16's pre-existing convention: `seen_id_set` adds the question receipt; `source_sha256` adds it alongside acceptance and source; promisor, beneficiary, quality-rule hash, acceptance event and channel add it alongside acceptance. The view tests previously asserted only promisor and source hash explicitly; the raw-input helper asserts all six obligation-derived fields. Raw fixture inputs, expected values and exclusion/refusal expectations stay unchanged.

## New frozen controls

Private evidence lives under `.supernal-local/prospective-support-v1/`. Before execution, `literal-freeze-v1` records exact candidate/test sources, fixed dependencies, public contracts and authority hashes, and copies four independently authored raw manifests/body dictionaries with literal expected values and required support. The new release fixtures use IDs 118, 307 and 9007199254741777, preserve a draft-to-stable history and malformed/absent publisher metadata, include an empty prior sample, and separately exercise empty opening and all-empty history. The obligation uses explicit counterintuitive role names, an independently fixed 380-byte CRLF/UTF-8 source, raw SHA256 and Git blob identity. No old oracle-baseline fixture builder is imported.

Each reference oracle sees only the new raw manifest and bodies; its answers/support must equal the prewritten literal artifact. Candidate normalization then supplies both encoders. Actual saved bytes are flushed, hashed and reread before byte-only decoding, and the frozen checker compares retained outputs against the independently established envelope. No oracle or expected artifact enters decoding. Label presence is insufficient: removing the encoded subject fact, its support, its receipt or substituting an unknown reference must refuse. Rebinding subject support to another existing receipt leaves the original question label present but must fail the fixed checker. Active question and source-path revisions use distinguishable references, reject missing active support, preserve old facts and omit unrelated receipts from derived ancestry.

## Executions and limits

The first and only builder check process passed **57 test methods**, including the five new dependency/conformance methods and the affected legacy view/raw-input suite. There were zero unexpected failures or errors. `checks-first-attempt` retains exact inputs, normalized packets, saved forms, decoded outputs, checker diagnostics, expected refusals, stdout/stderr, the pre-execution recipe and process receipts. Its source and expectation freeze contains 126 pins; all verified before execution and again before this results-only documentation update. Candidate/test and fixed-dependency bytes stayed unchanged throughout.

| New invented case | Saved forms | Exact value matches per form | Supported-content matches per form | Additional eligible references per form | Content complete |
| --- | --- | --- | --- | --- | --- |
| Release history with empty prior sample | Flat and graph | 6/6 | 6/6 | 1 | Yes |
| Release with empty opening | Flat and graph | 6/6 | 6/6 | 1 | Yes |
| All release samples empty | Flat and graph | 6/6 | 6/6 | 0 | Yes |
| Obligation with explicit source/acceptance ancestry | Flat and graph | 10/10 | 10/10 | 0 | Yes |

Each of these eight checks had no schema errors, invalid or duplicate references, missing values/support or oracle unknowns. Every independently derived oracle answer/support map matched its frozen literal artifact. The one allowed extra release reference is the prior nonempty sample in opening eligibility. Empty samples remain required support for history; the all-empty case still recovers their complete receipt set.

The negative controls retained **22 expected decoder refusals**: sixteen subject-fact/support/receipt/unknown-reference losses across both families/forms, and six active question/source-path/source-hash support losses. Four additional saved outputs deliberately redirected the subject fact to an existing non-question receipt while preserving the question label elsewhere. Exact values still matched, but the fixed checker rejected completion: release had two missing-support fields and obligation seven, in each form. Revision controls preserved superseded rows, selected the new binding/path support, and excluded unrelated source receipts from derived answers. These are intentional diagnostic failures, not discarded attempts.

Execution used `/Users/ianderrington/miniconda3/bin/python`, Anaconda Python **3.12.9**, Clang 14.0.6, macOS 26.5.1 arm64. The integer-digit guard stayed **4,300** and recursion limit **1,000** before/after. The outer test/control subprocess interval was **0.506340000 seconds of the 180-second builder cap**. Nested harness time was **0.419331208 seconds**, including loading tests; unittest reported **0.356 seconds**. These overlap and are not summed. A separate fresh critic receives 90 seconds. Total agent effort, cost, CPU and peak memory are unmeasured/null. Study-program network calls, model calls and spend are zero.

The measurement's exact SHA256 identities are pinned in `literal-freeze-v1/pins.json` (`fbd367896823eea07415cdecb0c3f2e0100a8cadbdae4b1239661ae71edc2a0e`):

| Dependency | SHA256 |
| --- | --- |
| Candidate views | `6410e25a6916924a31c1eb8dbf6ebe9273c9f8e62a30e38f24ddf004f327b959` |
| Fixed raw normalizer | `d1811eba3dc2934669b46c5c29a3cf3658a9b531f403f2ed3a0519c47c1ac5d8` |
| Fixed oracle | `df7d2d07cb394ce311bf1a490f9fb8de6535a60b6004a8b3dced0b1396c0dd9e` |
| Fixed repaired checker | `8b19f8e80a3334b631e3437af47d2effddf11ed68634dc6b6433e9977eb9a9c9` |
| Shared store utilities | `fda268dfa48beb28ee34a3bef714979f85e2e46db28bd7dc4cb1bc0395d6b0d1` |
| Public raw-input contract | `5d2c4450fc30dc896e7f56acd37d8025fbe46f1a70d3396c6b788cf7487edacd` |
| Public oracle/support contract | `c23f5a493e04cc49d89e0607bef320807b06adac5905ee30c641d4bc27ae983e` |
| Public checker contract | `8afbbb1ba07c2269be59f0615acc0a3e9c3ac6e5d9adda5aab8d86ba018b315b` |

## Review and next gates

At review freeze, `review-freeze-v1` pins the five owned files plus unchanged root loop/TODO files, exact diff/base, oracle/checker/normalizer/store and evaluator tests, public contracts, declaration v2 (`ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65`), required-support decision (`1f6c4c34974395c4f1015d72488b037f200cc0920c1dbff37254791a9a0cc70a`), receipts and original C17 evidence. A fresh unguided critic receives location/base/diff/pins and read-only constraints. The builder holds source unchanged and makes no commit or landing; the supervisor adjudicates independently. Independent review remains pending at this source freeze, and its report is retained separately without rewriting this freeze.

Only two families are scoped; five remain unmeasured. Shared query logic means matching flat/graph results are not independent replications. Content agreement does not certify preservation, hostile-host isolation, forecast eligibility, source selection, clock witnessing, registration or a functioning collection/runtime boundary. No actual study exists for this pilot. Collector, selector/binder, timing, producer, quality-checker and full runtime review remain launch gates. No external retrieval, original-study execution, live collection, scheduling, registration, transaction, deployment, forecast, scoring, learning or universal generalization is performed.
