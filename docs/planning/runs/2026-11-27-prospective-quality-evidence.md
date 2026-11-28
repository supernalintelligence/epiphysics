---
title: "C24 captured-artifact quality evidence record"
description: "Frozen invented capture metadata and bounded conditional content intake, without capture or outcome execution."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

C24 implements the [six-input evidence contract](../prospective-quality-evidence.md)
after supervisor design adjudication. Its managed source base is
`504960ddae873e2642c563e7ddb87fcf1f98010d`, the integrated C23 capture revision.
The author previously implemented C22 integration and authored neither the C20
checker nor C21 producer. The new consumer imports neither producer nor capture
nor ledger. Both accepted components and all earlier evidence remain unchanged.

## Scope and frozen expectations

The public API performs pure supplied-byte structural verification and calls the
unchanged C20 checker only for consistently retained, complete, nonempty stdout.
Its fixed contract is `captured-line-index-evidence-v1`; matching caller-supplied
anchors does not authenticate them. A trusted provenance/export path, actual loaded
C20/C24 code/runtime pinning, publication retention and later resolution remain
separate prerequisites. No new filesystem/ledger reader supplies those missing facts.

Before any consumer or checker call, the author froze 70 fresh control definitions,
all exact input bytes/types, exact expected canonical outputs or propagated
exceptions, expected checker calls and 650 source/runtime/evidence pin records.
The new literal source is `C24 stone ☆\r\nplum\rharbor\nfin`: 30 UTF-8 bytes with
independently written raw slices `[0,15)`, `[15,27)` and `[27,30)`. Canonical artifact
fields and SHA256 values were computed from those literal slices without either
component or a reused splitter. A separate exact-source-cap fixture declares one
8,192-byte slice of repeated ASCII `C`; an exact-artifact-cap fixture uses a complete
valid JSON artifact plus insignificant trailing whitespace to reach 65,536 bytes.

Capture claim/receipt/terminal envelopes are independently constructed invented
metadata. Their declared runtime path, hashes and 2034 timestamps are explicitly
synthetic, not observations of real capture, registration or runtime execution.
The actual execution pins separately bind Python 3.12.9 at
`/Users/ianderrington/miniconda3/bin/python`, the new module/tests and loaded
dependencies. The unchanged C20 source SHA256 is
`b2414e4b6cf1ca4a1870fe5d649606d52a501b5a75dabc8ed53918c4ee2152a7`.
Root-owned `DAILY_LOOP.md` and `TODO.md` updates are included in the freeze and
preserved without builder edits.

## Original execution

The focused command ran only `test_prospective_quality_evidence.py`. Both test
methods passed. All 70 consumer calls matched the frozen exact-output/exception
expectations. There were no unexpected original failures and no repair or replay.

| Observed first-execution class | Controls | Checker behavior |
| --- | ---: | --- |
| `checked` content | 12 | Twelve actual C20 calls: nine true, three expected false |
| `closed_empty` | 1 | No checker call; no no-submission claim |
| `overflow_observed` | 1 | No checker call; retained prefix stays outside C20 |
| `unavailable` | 54 | Forty-nine stopped before checking; five used explicit checker fault controls |
| Propagated Python cancellation | 2 | Injected `KeyboardInterrupt`/`SystemExit`; no evidence result returned |

The nineteen checker-boundary invocations therefore comprise twelve real C20
calls and seven injected dependency/cancellation controls. There were zero capture,
producer or ledger calls. No actual worker was launched and no prior
C12/C17/C20/C21/C22/C23 cohort or standalone suite was replayed.

Controls cover missing and wrong-type inputs for all six arguments, all six
over-cap boundaries, exact source/artifact capacity, strict metadata parsing,
duplicate/nonfinite/huge/deep/noncanonical metadata, capture/runtime/claim/terminal/
receipt/source/stdout bindings, sequence and path mismatches, malformed stream
claims, missing durability, unverified retention and incomplete output. Complete
invalid UTF-8, malformed JSON and wrong-content artifacts receive their expected
false judgments; they are separately authored complete fixtures, not truncated
original capture files. A deliberately interleaved terminal event remains valid
without requiring direct claim-to-terminal chain adjacency.

Additional complete-content controls preserve independent nonzero-exit,
unreaped-child, clock-uncertainty, stderr-retention and close-uncertainty facts.
Checker controls distinguish unavailable content, an exception, wrong identity,
wrong result type and a non-boolean judgment. Cancellation propagates. The module
does not import capture, producer or ledger; interpreter recursion and integer-digit
settings remain unchanged. The largest returned evidence object was 1,282 bytes,
within the 4,096-byte cap.

## Reread audit, cost and review

A separate read-only audit verified all 650 pre-execution pin records and all
623 original execution files. It compared the actual outputs to the independently
prepared expected bytes, checked retained input bytes/types and exact call counts,
and confirmed constant non-authorization fields. It made no consumer/checker call.

The focused test subprocess used 0.247391833 seconds outer elapsed time; the test
body measured 0.156090042 seconds. The saved-evidence audit subprocess used
0.267412792 seconds outer, with 0.243063708 seconds inside its body. Their combined
outer test/audit time is 0.514804625 seconds against the 180-second author allowance;
each subprocess had a 30-second timeout. Preparation/freezing separately measured
0.525643250 seconds. A subsequent read-only summary inspection reported
0.062113583 seconds of outer command time. Nested measurements overlap their
enclosing measurements and must not be added twice. Final freeze/handoff costs
are separately recorded in the handoff receipt. Whole-agent time, orchestration
and monetary cost remain unknown; external program/model/service spend was zero.

All original local evidence is retained outside the disposable worktree under
`/Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/prospective-quality-evidence-v1/`:

- `prepared/` contains the complete independent input/expectation freeze.
- `pre-execution-pins.json` binds actual source/runtime dependencies, root-owned
  documents, preparation driver and prepared controls before component execution.
- `first-run/` retains every input/type declaration, expected and actual output,
  exception record, checker-call count and the two focused test results.
- `first-run-process.json` and its stdout/stderr files retain the original process
  observations. `saved-audit.json` and `audit-process.json` retain the reread audit.
- `review-freeze/` binds the complete six-file source diff and source/dependency/
  evidence identities for root-managed independent review.

Review and supervisor acceptance are pending at this source freeze. No commit,
landing, rendered check, deployment, actual source selection, registration, capture,
store append, queue change, controller or outcome resolution occurs in C24. This
packet supplies no firstness, rights, time, predictive/causal/business advantage,
continuation or hostile-host-isolation claim.

## R1 dependency-test isolation repair

The original standalone execution remains **70 controls passed**. Independent
review subsequently found a source-level test-discovery defect: the purity test
asserted that capture, producer and store were absent from the parent process's
global `sys.modules`. Neighboring tests can legitimately import those modules
before this test runs. Root accepted that P2 finding in `adjudication-v1.json`;
the adjudication records no production-consumer finding. The standalone result
did not establish coexistence with shared discovery, and is not rewritten as
either a new failure count or proof that this defect was absent.

R1 changes only the dependency-purity test and this factual history. Its import
and AST assertions now run in a fresh isolated interpreter. The test retains the
child's raw stdout/stderr, exit/timeout observation and parsed dependency result
before making its assertions. It does not clear the parent's module table or
change global interpreter limits. The production consumer and root-owned
`DAILY_LOOP.md`/`TODO.md` remain byte-identical to the first freeze.

Before the first R1 control, exact revised test/runtime identities, the control
program, literal expected child stdout and the focused integration intent were
frozen under `revision-r1/`. The control imported `epiphysics.store` in the parent
without opening a ledger, then directly ran only
`QualityEvidenceTests.test_pure_dependency_surface`, without class/cohort setup.
That one test passed. The fresh child reported no capture/producer/store imports
and the exact expected consumer import list. All prior parent module-object
identities and interpreter limits were preserved. Consumer, checker and ledger
calls were zero. The original 70 controls and all earlier suites/cohorts were not
replayed; this was a focused shared-discovery coexistence check, not a full-suite run.

The R1 focused process used 0.382160375 seconds outer elapsed time within a
20-second limit. Its body took 0.071603791 seconds, including a fresh-interpreter
subprocess taking 0.070149416 seconds within a 10-second limit. Preparation/freezing
separately took 0.095356208 seconds. Both first outputs and stderr are retained;
there were no unexpected R1 errors or failures. Nested times overlap their outer
measurements and are not added again. The R1 handoff records final freeze work
and the cumulative accounting against the original 180-second author allowance;
whole-agent costs remain unknown and external program/model/service spend is zero.

`revision-r1/review-freeze/` preserves the revised complete six-file diff, changed
source snapshots, original evidence and current pins for both root-managed
reviewers. The original source snapshot, first-execution results, reviewer records
and accepted discovery finding remain retained. Whole-boundary re-review and
supervisor acceptance are pending at this R1 freeze; no commit or landing occurred.
