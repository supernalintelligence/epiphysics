---
title: "C21 pure producer implementation record"
description: "Separately authored artifact generation on frozen invented controls."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

C21 implements only the [pure artifact producer](../prospective-producer.md).
The supervised source base is `676092307c6244269e0ffb5b402e1e6cadb386eb`.
The normative declaration digest remains
`ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65`.
The API and fixed exception semantics were proposed and accepted before any
producer call. No quality-checker or candidate implementation, test, fixture or
review was used in producer authoring or validation.

## Retained preparation

The first independently written expectation-preparation subprocess failed before
any producer call: it sought odd-sized neighboring canonical artifacts of
65,535 and 65,537 bytes in a family whose internal offset digits occur twice.
It did establish the exact 65,536-byte member. That script and its failure remain
under `literal-preparation-v1`.

The distinct `literal-preparation-v2` correctly fixed prefix sizes but incorrectly
assumed two-byte increments. Its independently serialized partitions exposed
four-byte increments, because two internal decimal boundaries moved. That script,
failure and original expected bytes remain retained. Neither failure is a
producer result, and neither changed the public quality rule or producer.

`literal-preparation-v3` froze successful expectation preparation. Sources of
three, four and five `x` bytes followed by 656 LF bytes respectively have complete
canonical artifacts of 65,532, 65,536 and 65,540 bytes. Their first line ends at
4, 5 or 6; each remaining line is one LF byte. The expected source/slice/artifact
hashes and full fields and bytes are retained before producer execution. The
above-cap expected artifact is a control for refusal, never an admitted output.

## Validation and resource accounting

The source and seven self-contained test methods were frozen before the first
producer invocation. The ten literal controls include explicit complete artifact
bytes; six capacity controls bind complete expected bytes privately and fixed
source/artifact hashes and lengths in the test module. Wrong-type and refusal
controls are separate. Invented empty/short/non-UTF8/NUL/high-line-count inputs
are not eligible selected sources.

The first frozen execution, `producer-first-tests-v1`, passed all seven methods
with no producer failure or repair. It made 64 calls: 50 returned artifacts and
14 raised the expected type/capacity exceptions. The exact 65,536-byte artifact
passed; the independently expected 65,540-byte artifact was refused. The source
and test hashes stayed unchanged after their pre-execution freeze:

| Frozen item | SHA256 |
| --- | --- |
| Producer source | `b75e28b42c0dab8b90275da511848ea49e865c11891414d3c180a51b25fecf4a` |
| Tests | `df789d61600c8d49dba6c0ad7e0957852babde066c99ccccf63e7ebf887f157c` |
| Pre-execution manifest | `1a74bd053fb428ec9258ef6e1d150996cf098362e928713ac7fd753feb2fdb47` |

| Retained subprocess identity | Outer seconds | Result |
| --- | ---: | --- |
| `literal-preparation-v1` | 1.663363459 | Preparation failure retained |
| `literal-preparation-v2` | 0.045302167 | Preparation failure retained |
| `literal-preparation-v3` | 0.037364709 | Expectations frozen |
| `freeze-first-v1` | 0.310223041 | Pre-execution state frozen |
| `producer-first-tests-v1` | 0.063146167 | Seven methods passed |

These measured outer intervals total 2.119399543 seconds through the first
producer test subprocess. The unittest-reported 0.007 seconds is nested within
the last interval. Subsequent whitespace/final-freeze checks have separate
retained receipts and remain charged to the same allowance.

The runtime is Python 3.12.9 at the supplied interpreter. Each builder control subprocess is
limited to 30 seconds within a combined 180-second allowance, with stdout,
stderr, exit status, UTC interval and measured outer duration retained. Any nested
timings overlap their outer interval and are not added again. Review has a
separate maximum 90-second invented-control allowance. Whole-agent effort,
CPU time, peak memory and monetary cost are unknown; external program/model
spend is zero. These limits are implementation-control limits, not a validated
future producer-slot runtime.

## Scope and review

Only five assigned producer/documentation paths are changed. Root-owned planning
changes are preserved and pinned. The source/test/runtime/dependency/control pins
and full review diff are retained locally. Fresh independent review and supervisor
adjudication are pending; this record makes no independent acceptance claim.

There was no source-pool inspection or selection, registration, collection,
candidate call, scored delivery, scheduler, C12/C17 execution or declaration
change. No broad suite or research rerun was performed. The pure function does
not bind acceptance, prove firstness, retain output, establish complete delivery,
enforce timing or resolve an obligation. Those remain future integration gates.
