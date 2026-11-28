---
title: "Prospective artifact quality contract"
description: "Independent content checking of complete supplied line-index artifacts."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

`engine/epiphysics/prospective_quality.py` implements the public `first-artifact-quality-v1` content predicate independently from raw source bytes. Its single entry point is `check_line_index(source_bytes, artifact_bytes)`. Both arguments are exact `bytes`, or `None` when unavailable. The caller must establish that the supplied artifact is complete before using this API. The function cannot establish completeness itself, and a retained prefix must never be supplied as a complete artifact.

The result has `quality` (`true`, `false` or `null`), `reason`, `source_sha256`, `source_byte_length`, `artifact_sha256` and `artifact_byte_length`. Identities bind the exact supplied bytes, including artifact whitespace. Missing or wrong-type inputs have null identities for the unavailable bytes; any available byte input still receives its own identity. Parser capacity failure preserves identities already computed. One reason records the first decisive check; this is not an exhaustive defect inventory.

## Exact public content rule

An artifact is strict UTF-8 JSON without a BOM, duplicate object keys, nonfinite tokens or trailing non-whitespace. Only JSON whitespace is insignificant. Duplicate keys are detected after escape decoding, at every parsed object. The maximum artifact length is 65,536 bytes, inclusive. Object ordering and insignificant whitespace are immaterial; array ordering is exact.

The top-level object has exactly `schema_version`, `source_sha256`, `source_byte_length` and `lines`. Version is the integer 1. Source hash is the lowercase SHA256 of all source bytes. Source length is their exact nonnegative integer count. `lines` is an array of objects having exactly `start`, `end` and `sha256`. Offsets are nonnegative integer JSON primitives, and the hash is lowercase SHA256. Booleans, strings, null and floating-point numeric tokens cannot substitute for integers. A legal integer `-0` has the value zero. Huge integer tokens are compared exactly without conversion or rounding; floating-point tokens, including huge exponents, cannot fill any public numeric field. No global integer-digit or recursion setting is changed.

For nonempty source bytes, starts are 0 and the position after every LF except a terminal LF. Each end is the next start or the source byte length. The hash covers the entire raw slice, including LF and any preceding CR. Lone CR does not split a line. Multibyte UTF-8 changes byte offsets; character positions are irrelevant. A terminal LF adds no phantom empty line. Empty source has `lines=[]` and is a boundary fixture only.

The checker does not decode or normalize source bytes. Its processing capacity is 8,192 source bytes. This capacity is separate from source-selection eligibility: actual selected sources must also meet the declared 256-byte minimum, 128-line maximum, strict UTF-8/no-NUL rule, frozen Git and public-content requirements, and all other selection conditions. The checker can demonstrate the raw-byte predicate on invented short, empty, newline or non-UTF-8 boundary fixtures without making them eligible sources. No actual source pool is read or selected by this component.

## Failure and unavailable results

| Result | Reason | Meaning |
| --- | --- | --- |
| `true` | `matches` | Every declared content value matches the raw-byte rule. |
| `false` | `artifact_size` | Complete supplied artifact exceeds 65,536 bytes. Its identity hashes all supplied bytes, never a prefix. |
| `false` | `artifact_utf8`, `artifact_json`, `artifact_duplicate_key`, `artifact_nonfinite` | A disclosed encoding/parser failure in the complete supplied artifact. |
| `false` | `artifact_schema` | Wrong exact field sets, object/array structure, primitive types, nonnegative constraints or hash spelling. Extra fields are schema failures, not accusations of fabricated evidence. |
| `false` | `content_mismatch` | Structurally valid values, line count or line ordering differ from independently recomputed truth. |
| `null` | `missing_source`, `missing_artifact`, `input_type` | Required bytes are unavailable. `None` is distinct from `b''`. |
| `null` | `source_capacity` | Source exceeds this checker's supported processing capacity; this does not prove bad artifact quality. |
| `null` | `checker_capacity` | Memory, recursion or overflow prevented the check. Deep valid JSON may exceed parser capacity; that is not a proven schema defect. |

Missing inputs and wrong input types are checked before size/content decisions. With both byte inputs present, exact over-limit artifact bytes establish a size failure even if the source exceeds processing capacity. Resource failures while establishing identities or evaluating content are unavailable. An unhandled checker crash, external timeout or absent checker receipt also remains unresolved at the caller; it must never be converted to `quality=false`.

An empty supplied artifact fails JSON as a content object. A future broker may instead classify an independently confirmed closed, zero-byte stream as no submission under the delivery rule. Conversely, malformed nonempty JSON can be a complete submitted artifact when EOF and retention are established. Those stream facts are outside this checker. Receipt-derived overflow from a bounded prefix also belongs to the later broker/resolver, even though that component may independently establish the public size failure.

## Authority and independence limits

This function performs no file, network, model, store or scheduler action. It reads no declaration or private fixture at runtime, imports only standard-library dataclasses, JSON and SHA256 support, and neither imports nor reuses a producer, normalizer, view, query oracle or query checker. The author used the public declaration and invented raw byte controls. The future producer has not been implemented or selected and must have a different author. Shared JSON/SHA256 and the same host remain acknowledged dependencies; algorithm separation does not prove host or mathematical independence.

Quality alone establishes no firstness, complete capture, arrival time, durable retention, acceptance, source eligibility or integrity, rights, payment, producer cleanup or final obligation outcome. The caller must separately bind these exact byte identities to the selected source and complete first artifact. It must retain independent resolution by the declared deadline. A passing content result gives no registration or execution authority and no predictive, causal or business-value evidence.

The [implementation record](runs/2026-11-27-prospective-quality.md) records the frozen controls, first failures, actual bounded execution and review status. No C12/C17 comparison or existing candidate was run in this packet.
