---
title: "Pure prospective artifact producer"
description: "Version-1 byte-to-line-index contract and bounded refusals."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

`engine/epiphysics/prospective_producer.py` provides
`produce_line_index(source: bytes) -> bytes`. It produces one complete line-index
artifact from the exact supplied built-in bytes. The function has no command-line
entry point, file access, store access, network, model call, scheduler or delivery
action. A future execution driver must bind obligation identity, the public
schema and the exclusive first-submission channel separately.

## Public artifact

The returned artifact is UTF-8 JSON with sorted object keys, compact comma/colon
separators and no trailing newline or BOM. Its exact top-level fields are:

| Field | Value |
| --- | --- |
| `schema_version` | Integer `1` |
| `source_sha256` | Lowercase SHA256 of the complete supplied bytes |
| `source_byte_length` | Exact integer byte length |
| `lines` | Ordered array of objects with exactly `start`, `end`, `sha256` |

For nonempty input, each line starts at zero or immediately after an LF byte,
unless that LF is terminal. Each end is the next start or the source length.
The hash covers the entire byte slice, including LF and any preceding CR. Lone
CR does not split a line. Multibyte characters do not change byte-offset
semantics. Empty input returns `lines=[]`; terminal LF adds no empty line.
No timestamp or obligation identifier is inserted into the artifact.

The artifact's SHA256 can be calculated by a caller over the returned bytes;
it is not an additional self-referential artifact field. The source digest and
artifact digest identify different byte sequences. Deterministic serialization
does not prove timing, authorship, authenticity or source truth.

## Capacity and refusal

The fixed processing limits are 8,192 source bytes and 65,536 artifact bytes,
both inclusive. The implementation appends one encoded line only after checking
that the line, separator and reserved metadata tail fit. No partial artifact is
returned or emitted. It does not change interpreter settings.

| Condition | Result |
| --- | --- |
| Exact built-in `bytes` within both capacities | Complete artifact `bytes` |
| Any other type, including `bytearray`, `memoryview`, and a `bytes` subclass | `TypeError("source must be built-in bytes")` |
| Source longer than 8,192 bytes | `ProducerRefusal("source byte limit exceeded")` |
| Complete canonical artifact would exceed 65,536 bytes | `ProducerRefusal("artifact byte limit exceeded")` |

`ProducerRefusal` subclasses `ValueError`. These fixed messages contain no source
content. Wrong type is checked before length. Refusal describes this function's
capacity; it is not an obligation outcome or a quality-checker verdict.

Processing capacity is separate from source selection. Actual selection still
requires a confirmed public, strict UTF-8 Git blob without NUL, 256–8,192 raw
bytes and at most 128 LF-defined physical lines, plus the declared repository,
path and exclusion rules. This function does not perform selection. Empty,
short, malformed UTF-8, NUL-containing and high-line-count invented controls
remain noneligible boundary inputs even when processing succeeds.

## Authorship and evidence

The implementation and expectations were authored from the declared public rule
and standard-library JSON/SHA256 primitives. The producer author did not inspect,
import or use the existing quality checker, its tests or review, candidate
normalizers/representations, oracle, query checker or their helper code.
The package initializer is inert and was inspected as an import dependency.

Before the first producer call, the source, tests, runtime, dependencies and
independently stated source partitions, slice/source hashes, expected fields and
complete canonical artifact bytes were frozen. Ten small literal cases and six
capacity cases cover ordinary and empty source, leading/adjacent/terminal LF,
CRLF/lone CR, multibyte offsets, identities, deterministic output, wrong types,
source limits, high line counts and the exact artifact cap. Expected partitions
are literal slices or explicit numeric families; they are not derived by running
the producer or a shared splitting helper.

The [implementation record](runs/2026-11-27-prospective-producer.md) retains
preparation failures, execution identities, measured limits and review state.
These are invented implementation controls, with no forecast, predictive,
causal or business-advantage metric. Driver/broker integration, independent
quality resolution, timing and source-selection gates remain separate work.
