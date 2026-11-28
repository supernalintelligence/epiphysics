---
title: "Prospective calendar derivation contract"
description: "Pure absolute-time calculations for the pinned proposed pilot, without registration or runtime authority."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

`epiphysics.prospective_schedule` supplies the mathematical calendar needed by a future instance binder. Its only declaration is the exact proposed v2 bytes, SHA256 `ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65`. No registration, document selection or collection exists for this pilot. This pre-registration engineering covers two families; five remain unmeasured.

## API and strict comparison

`derive_schedule(declaration_bytes, supplied_origin_utc) -> bytes` returns sorted-key UTF-8 JSON with compact separators, no trailing newline and no nonfinite numbers. `verify_schedule(declaration_bytes, supplied_origin_utc, schedule_bytes) -> None` succeeds only when the supplied calendar has exactly the calculated fields, types, values and array order. It does not return a repaired calendar. Both raise `ScheduleRefusal(ValueError)` with a bounded static reason code on malformed input or unsupported calendar range; no partial plan is returned.

Declaration and calendar input/output caps are each 131,072 bytes. Inputs must be exact Python `bytes`; the UTC origin must be an exact `str`. Declaration hashing precedes parsing: changed bytes, even semantically equivalent JSON whitespace, refuse. That fixed byte identity also fixes the declaration's schema, counts, field sets, types, IDs and cross-bindings. The module is deliberately specific to this proposed declaration rather than a general declaration validator. Parsing refuses duplicate object keys, invalid UTF-8/BOM, floating/nonfinite JSON numbers, integer lexemes longer than twenty characters, and invalid/trailing JSON. Runtime nesting inability is explicit. These bounds do not change study budgets.

Verification accepts insignificant JSON whitespace and object-key order. It preserves array order, requires canonical timestamp spelling in the supplied plan, and rejects omitted/extra fields, slots, duplicates, substitutions, reordered entries, retimed boundaries, changed types/budgets, altered authority flags or pruned membership. It compares canonical serialized values, avoiding Python's boolean/integer equality. Original inputs remain caller-retained; this pure module cannot persist them.

## Calendar and membership

The origin accepts UTC RFC3339 seconds with `Z` or `+00:00`, optionally one to six fractional digits. Non-UTC offsets, negative-zero offsets, leap seconds, local dates, invalid calendars and excess fractional precision refuse. Output always uses six fractional digits and `Z`, retaining the exact microsecond value. Integer-second `timedelta` arithmetic adds only declared `*_offset_seconds` fields; their absolute names replace that suffix with `_utc`. Duration limits, byte caps, ordinals and all other values are unchanged. Year-range overflow, including an audit deadline after year 9999, refuses the complete result; there is no clamping or schedule shift.

The exact envelope has `schedule_schema_version: 1`, `declaration_sha256`, `supplied_origin_utc`, `timing_assurance`, `registered`, `launchable`, `execution_authorized`, `relative_schedule`, `absolute_schedule`, `overall_audit_deadline_offset_seconds`, `overall_audit_deadline_utc`, `release_snapshot_membership`, `counts`, `source_policy`, `http_policy` and `representation_budgets`. Source and HTTP policies and the representation budget object are copied unchanged from the declaration. Producer budgets remain in both relative and absolute producer slots. The caller must retain the original byte-pinned declaration; the parsed relative schedule is also included unchanged in the result.

Both schedules retain all eight questions, sixteen HTTP slots, sixteen method slots and four producer slots in declared order, with unchanged identities, question/method bindings, ordinal values, opening/outcome relationships and inclusive endpoints. The overall audit deadline is origin plus 1,209,600 seconds. A calendar endpoint is a mathematical limit, not evidence that an operation reached it.

Each `release_snapshot_membership` entry has exactly `question_id`, `opening_poll_id` and `slots`. Each slot has exactly `id` and `nominal_at`, matching the [raw-input question evidence grammar](./prospective-inputs.md). Membership uses the complete declared sixteen-slot set and includes all pilot slots at or before that question's opening: **1, 5, 9, 13** for R1–R4. Pj.3 is E_j minus 300 seconds, preceding the next opening. No caller-provided subset can replace this complete set. This requirement identifies slots whose receipts must be considered; it does not admit missing/invalid samples or certify source completeness beyond this bounded pilot. Observation identities and actual receipts remain future collector/binder inputs.

## Authority and remaining gates

`timing_assurance` is always `supplied_origin_only`; `registered`, `launchable` and `execution_authorized` are always false. A supplied origin is a calculation input and proves neither an accepted registration nor a trustworthy clock, retained post-binding or satisfied start window. This module imports only standard-library JSON, hashing, regular expressions and datetime arithmetic. It opens no files/store, reads no wall clock, sleeps nowhere, selects no repository documents, launches no processes and performs no network, model, producer, candidate or scheduled work.

The future binder must verify the real retained registration receipt and pre-manifest digest before using its receipt time as R. The pre-manifest excludes its own hash, receipt, R and absolute schedule; the generated post-registration binding is separate and needs its own durable retention evidence. The eventual runtime must verify that binding before the first slot and enforce real 10/60-second starts and durable completion windows. Calculation and content agreement cannot satisfy those gates, authorize execution, establish receipt honesty or provide forecast/scientific advantage evidence. See the [implementation record](./runs/2026-11-27-prospective-schedule.md) for invented controls and review status.
