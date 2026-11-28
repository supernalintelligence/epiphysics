---
title: "C22 saved artifact integration record"
description: "One retained producer/checker connection on six fresh invented sources, with fixed byte expectations."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

C22 asks the bounded [saved-byte compatibility question](../prospective-artifact-roundtrip.md).
The supervisor selected it before broker/runtime construction, from base
`133c6691b9576293e307e62c8cd0480352d6ccbb`. The integration author did not author
either accepted component. No standalone component test suite or prior component
fixture was used as fresh coverage. No production module or acceptance rule changed.

## Frozen inputs and original results

The immutable producer SHA256 is
`b75e28b42c0dab8b90275da511848ea49e865c11891414d3c180a51b25fecf4a`;
the immutable checker SHA256 is
`b2414e4b6cf1ca4a1870fe5d649606d52a501b5a75dabc8ed53918c4ee2152a7`.
The proposed normative declaration was verified as
`ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65`.
Python is `/Users/ianderrington/miniconda3/bin/python`, version 3.12.9.

Before the first pipeline call, preparation froze all six raw sources, independent
literal partitions, exact expected fields/canonical bytes and expected outcomes.
The 178 pre-execution pins include loaded source/runtime dependencies, the test,
declaration, preparation driver, supervisor selection and unchanged root-owned
`DAILY_LOOP.md`/`TODO.md`. The test also saved its full plan and control expectations
before calling either component. Shared JSON/SHA256 and the common host remain
acknowledged dependencies.

| Invented case | Source bytes / lines | Expected result | Observed saved result |
| --- | --- | --- | --- |
| Ordinary LF | 265 / 3 | Complete, 434 bytes; content pass | Exact bytes; `true/matches` |
| CRLF and lone CR | 267 / 3 | Complete, 434 bytes; content pass | Exact bytes; `true/matches` |
| Multibyte UTF-8 | 26 / 3 | Complete, 430 bytes; content pass | Exact bytes; `true/matches` |
| Empty boundary | 0 / 0 | Complete, 137 bytes; content pass | Exact bytes; `true/matches` |
| Leading/adjacent LF | 22 / 4 | Complete, 526 bytes; content pass | Exact bytes; `true/matches` |
| Artifact capacity | 700 / 700 | `ProducerRefusal`, no artifact | Exact `artifact byte limit exceeded`; no quality call |

Only the first two meet the declared size and line-count bounds. None is selected
public data. The last source's hypothetical complete expected artifact is 69,920
bytes; retaining that expectation does not manufacture a returned output.

There were exactly six producer calls, one per planned source, and seven checker
calls: five original complete outputs plus two intentionally complete negative
fixtures. Every actual producer output and refusal was retained outside the
worktree. Five of five available original artifacts passed content checking, and
all six planned producer outcomes matched their frozen expectations. No original
outcome was repaired or replayed. There were no unexpected first-run test failures;
the expected refusal and negative controls remain retained, not discarded.

## Retention and content controls

All four focused test methods passed. Six controls covered missing source/output,
incorrect source/output bindings, a corrupted copy and a truncated copy. All six
raised `RetentionFailure`, with zero checker calls and no quality result. The
intact original control bytes remain available. Two separate, intentionally
complete negative fixtures yielded `false/artifact_json` and
`false/content_mismatch`, with their own exact byte identities. They are not bad
first producer submissions. A further exclusive-save control refused an overwrite
and preserved the original bytes.

The separate read-only audit verified all 178 pre-execution pins and hashed all
56 original execution files with `/usr/bin/shasum -a 256`, independently rereading
the retained bytes and comparing all six cases to frozen expectations. It made
zero producer/checker calls. Local exclusive saves, flush/fsync and hash agreement
establish the observed file operations; they do not establish real first-submission
receipts, broker completeness, arrival deadlines or arbitrary host isolation.

## Budget and retained evidence

The first focused subprocess used 0.155614958 seconds of outer elapsed time, with
0.020239375 seconds measured inside the test body. The read-only audit subprocess
used 0.124473416 seconds outer time, including 0.094911959 seconds in its audit body
and 0.035340875 seconds in the nested external hash command. Nested times overlap
their enclosing measurements and are not added again. The two bounded test/control
subprocesses total 0.280088374 seconds against the 180-second builder allowance;
each had a 30-second timeout, and the nested hash process a 15-second timeout.
Preparation, source reading/editing, orchestration, review and whole-agent costs
are not represented by this subtotal; whole-agent effort/cost remain unknown.

Evidence is exclusively under the durable local directory
`/Users/ianderrington/git/ianderrington/epiphysics/.supernal-local/artifact-roundtrip-v1/`:

- `supervisor-selection.json` and `root-owned-document-pins.json` preserve scope and root edits.
- `prepared/` and `pre-execution-pins.json` freeze expectations/source/dependencies before calls.
- `first-run/` preserves the cohort, source bytes, actual complete outputs, refusal,
  per-case typed results, negative/control files and actual call counters.
- `first-run-process.json`, `first-run.stdout` and `first-run.stderr` retain process observations.
- `saved-file-audit.json`, `saved-file-external-shasum.txt` and `audit-process.json`
  retain the independent reread audit and its timing.
- `review-freeze/` binds the complete diff, source/dependencies and original evidence
  for a fresh independent critic. Review and supervisor adjudication are pending
  at this source freeze; later review records must preserve these original identities.

No network, model, paid call, transaction, source-pool collection/selection,
registration, store append, C12/C17 rerun, existing research-queue consumption,
scheduler/broker construction or actual pilot occurred. No missing private fixture
was scored as passed. The next work remains the separately scoped collection,
broker/process-capture, receipt/deadline resolution and registration/runtime gates;
this compatibility result supplies no predictive, causal or business-advantage claim.
