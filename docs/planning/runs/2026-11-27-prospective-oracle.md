---
title: "Prospective raw-source oracle implementation record"
description: "Invented-fixture construction, retained failures and draft freeze for independent review."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

C16 adds a separately authored pure snapshot-query oracle for software components and local delivery obligations. It implements the [public oracle contract](../prospective-oracle.md); no study, registration, collection, forecast, producer, quality check or outcome resolution occurred. Other entity families are unmeasured.

The managed worktree is `worktree-prospective-oracle`, based on `909ae65daca4a4507bd10d07b8c29e520952e42f`. Ownership is the oracle, its tests, the oracle contract, this record and the experiment overview. Supervisor edits in `DAILY_LOOP.md` and `TODO.md` were retained byte-for-byte and are included in the freeze, without author edits. Shared-checkout advancement is for the supervisor to reconcile; this work does not change its base identity.

## Authority and independent authorship

Inputs were the public raw contract, the experiment overview, root repository instructions and proposed declaration v2, SHA256 `ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65`. Candidate normalizer/view implementations, helpers, tests, expected answers and outcomes were neither read nor imported. No store utilities, original C12 evidence, other studies or actual pilot data were accessed.

The author asked the supervisor to resolve required-support and identity ambiguity before oracle execution. The adopted transitive convention requires the question plus all relevant direct receipts; full details are in the public contract. The private `root-contract-decision.json` has SHA256 `1f6c4c34974395c4f1015d72488b037f200cc0920c1dbff37254791a9a0cc70a`. The chat decision preceded execution; its separately written decision artifact followed. It was not derived from candidate behavior. Same-kind role reuse is allowed, and a prior sample cannot simply be dropped to hide an entity-kind conflict.

Exact invented release and obligation inputs, literal expected answers and literal required-support sets were saved in `expected-freeze-v1` before the first oracle call. They remained unchanged through all builder runs. The pre-execution source, expectation pins and interpretation history are retained in `pre-execution-draft-v1`. Expected source SHA256 was computed directly from the invented raw blob using standard SHA256, not through the oracle. No cross-component comparison was performed by this author.

## Executed checks and original failures

All evidence is privately retained beneath shared `.supernal-local/prospective-oracle-v1/`; it is not study data. Each case stores the exact manifest, exact body/header bytes, their dictionary-key inventory, output or exception. No prior failure directory was reused or overwritten.

| Run | Result | Retained raw cases | Outer test-process wall | Nested unittest wall |
| --- | --- | --- | --- | --- |
| `builder-run-01` | 30 tests, 28 pass and 2 control failures | 149 | 0.986922125 s | 0.755 s |
| `builder-run-02` | 30/30 pass after control corrections | 150 | 0.794305875 s | 0.622 s |
| `builder-run-03` | 31/31 pass after identity review and added controls | 153 | 0.838830166 s | 0.672 s |

The first purity test incorrectly treated `re.compile` as dynamic program execution. Its correction permits only this specific standard-library regex call while retaining the forbidden-effect checks. The first nesting test incorrectly assumed 2,000 arrays would exceed this interpreter's operational ability. That input parsed and then correctly failed the envelope schema. The corrected controls preserve this schema failure and separately observe runtime unavailability at depth 10,000. No portable recursion threshold is claimed. Original failure logs, raw bytes, outputs and receipts remain unchanged.

A subsequent author review caught that an entity-kind collision in a valid prior sample must refuse the inconsistent snapshot rather than exclude that sample and shrink history. The third run added prior/opening collision checks and explicit same-role reuse. These are identity controls; the pre-execution literal semantic answers and support sets did not change.

Controls cover the six/ten literal answers and full support; prior draft/prerelease history and a same-ID stable transition; exact IDs above 2^53; empty versus missing/invalid/late samples; missing prior receipts; excluded future slots; zero/five/six records; duplicate keys/IDs; strict booleans and lengths; header and body identity/caps; request and retention windows; clock order/epoch/drift; equivalent time spellings; optional malformed publisher metadata; directed acceptance, exact quality/channel/source bindings; UTF-8, CRLF, multibyte and final-LF source bytes; source/blob hashes and line/size boundaries; declaration/identity failures; integer/decimal/nesting operational distinctions; and explicit output overflow. The import/effect scan covers only this module's declared surface, not hostile-host isolation.

The exact command was `/Users/ianderrington/miniconda3/bin/python -m unittest discover -s engine/tests -p test_prospective_oracle.py -v`, with `PYTHONPATH` set to this worktree's `engine` and private retention enabled. Cumulative outer test-process wall time was 2.620058166 seconds of the authorized 180-second builder cap. Nested unittest timings are contained within those outer intervals and are not added again. Wrapper/fixture-freeze/authoring time is not included in that test-process measure. Total agent effort, agent cost, CPU and peak memory remain null. Study-program network calls, model calls and spend were zero.

Runtime: `/Users/ianderrington/miniconda3/bin/python`, Python 3.12.9 packaged by Anaconda, Clang 14.0.6, macOS 26.5.1 arm64; integer digit guard 4,300 and Python recursion setting 1,000. No global limits changed. Other interpreters were not tested. Accepted finite decimal values preserve their decimal round-trip value; impossible finite decimals are operationally unavailable, while literal nonfinite JSON is malformed.

## Freeze and next gates

`freeze-v1` retains the five owned source/document files, unchanged loop/TODO bytes, public input/experiment contracts, original base and exact diff, declaration and supervisor-decision pins, relevant standard-library/runtime identities, initial/pre-execution pins, expected-fixture pins and all builder-evidence hashes. Full raw cases remain in their original directories rather than being duplicated into the freeze. No source commit or landing was performed by this author.

The next automatic step is a fresh unguided read-only critic over the exact freeze, with an independently recorded test-process budget of at most 90 seconds. Its report is an append-only private artifact. Source remains unchanged while the supervisor adjudicates that report. This draft record does not predeclare a passed review.

After that gate, a separate actor may compare frozen raw fixtures against the shared normalizer and saved representations. It must preserve first disagreements and resolve them against the public contract rather than copying candidate results into oracle truth. Collector/selector completeness, registration-relative binding, absolute-time assurance, deadline-ready private expectations, runtime readiness, producer/checker/resolver and launch review remain separate unfinished gates. No current fixture result establishes candidate conformance, seven-family coverage, prediction quality or prospective readiness.

## Adjudicated review repair R1

The independent initial report is retained unchanged in `review-v1/report.md`, SHA256 `203509adffe6b38aac99d9ef4c18c44d5a440d7e2bb9759c779f1137d949d8b1`. Of 35 adjudicable independent controls, 34 matched; R1 exposed one medium/P2 correctness defect. An already incomplete prior sample lost its conclusive `body_incomplete` exclusion when separately bound headers containing `1e400` raised runtime unavailability. That incorrectly suppressed otherwise available membership and seen-ID answers. The paired potentially eligible prior correctly remained unavailable. The supervisor inspected and accepted R1 before authorizing repair.

The initial review also preserves its own metadata-harness failure and mistaken depth expectation, separate from the product finding. Its cumulative outer test-process wall was 0.287082750 seconds within its separate 90-second cap; nested intervals are recorded independently in that report. No review failure or expected file was replaced.

The narrow repair moves established body/clock/window disqualification ahead of header decoding. Header disqualification still precedes body JSON parsing, and potentially eligible unreadable evidence still causes runtime unavailability. It changes neither support conventions, original literal expectations, numeric settings, declaration nor candidates. New literal regression expectations were frozen in `repair-expected-freeze-v1` before execution. The controls combine missing/incomplete/hash-invalid bodies, clock epochs, request start/duration and retention/cutoff failures with malformed or runtime-unreadable headers; they also retain the paired genuinely uncertain case and invalid-opening behavior.

`repair-run-01` passed 35/35 tests over 180 retained raw cases. Outer process time was 0.410366125 seconds; nested unittest time was 0.321 seconds. Cumulative builder test-process time is now 3.030424291 seconds of 180, without adding nested intervals. Raw inputs, outputs, pre-execution repair source and expectation pins are separate append-only artifacts. All original fixture, builder and review files remain unchanged.

`repair-freeze-v1` pins the repaired five owned files, unchanged root loop/TODO and public dependencies, exact base/diff, original freeze and review pins, new expectation pins and repair test evidence. Source is held unchanged for the independent recheck and supervisor integration decision. This record does not predeclare R1 closed; the recheck report remains a separate evidence gate.
