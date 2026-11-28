---
title: "Prospective raw input contract"
description: "Version 1 of the bounded byte-to-fact interface for two proposed pilot families."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

This engineering contract implements one part of the proposed representation integrity pilot: supplied raw evidence bytes become one canonical typed-fact packet shared by the existing flat and graph encoders. It neither registers nor launches a study. The normative proposed declaration remains v2, SHA256 `ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65`. Final collection, selection, independent oracle, absolute-time binding, methods and runtime gates remain unfrozen.

## API and authority boundary

`epiphysics.prospective_inputs.normalize_inputs(manifest_bytes, bodies)` takes UTF-8 JSON manifest bytes and a plain dictionary from declared observation IDs to exact Python `bytes`. A release observation's retained header-pair bytes use the additional key `<observation_id>:headers`. These are dictionary keys, never filesystem paths. Missing declared bytes are allowed as evidence of unavailable input; undeclared keys and identity collisions refuse. Caller inputs are not mutated.

The result is `(normalized_bytes_or_None, diagnostics_bytes)`. Both outputs use sorted-key canonical UTF-8 JSON. `None` means no shared packet is available; it must not become an empty source or a numeric outcome. Malformed envelope/declaration structure raises `ValueError`. Runtime inability raises the distinct `InputUnavailable` subclass at that boundary, or is recorded with `runtime_*_unavailable` and, for a release observation, `status: unavailable`. Such an observation refuses the whole shared packet, including when it is a prior sample. This prevents silently excluding potentially eligible history.

Diagnostics contain `raw_input_schema_version`, `status` (`normalized` or `refused`), `timing_assurance: caller_claims_only`, `independent_collection_verified: false`, `observations`, `missing_slots`, and `reasons`. Observation entries have `id`, `status` (`admitted`, `excluded`, or `unavailable`), and a reason or null. Admitted release entries also include record count, count of excluded unselected fields, and the diagnostic Link `rel=next` flag (`present`, `absent`, or `unparseable`). Diagnostics are at most 65,536 bytes. They are not decoder context or an independent expected-answer map.

The adapter examines bytes, exact hashes, lengths, declared types, and internal consistency of times; it does not accept `valid: true` or precomputed answers. It cannot prove that HTTP ran, that supplied timestamps are honest, that an epoch was independently monitored, that a claimed Git commit contains a blob, or that a declaration is genuinely frozen. Source selection/publication, the complete schedule, registration-relative formulas and receipt authenticity require separately reviewed binding/collection evidence. All supplied local clock assertions remain caller claims. The code imports existing canonical JSON/hash/time utilities and the existing normalized-input bound; it opens no ledger and performs no data-dependent filesystem access, network, command execution, scheduling, forecast, quality check or outcome resolution. The existing `store` utility module reads its own implementation source at import; this is not a raw-evidence read or proof of host isolation.

## Manifest and receipts

The manifest has exactly:

| Field | Grammar |
| --- | --- |
| `raw_input_schema_version` | Exact integer `1`, not boolean. |
| `declaration_sha256` | The v2 hash above. |
| `question_observation_id` | ID of the question-contract receipt. |
| `observations` | Array of 1–18 unique receipts: one question and at most sixteen release observations, or one question plus its acceptance and source. |

IDs are nonempty strings of at most 200 characters with no leading/trailing whitespace. SHA256 values are lowercase 64-digit hexadecimal. Collections have exact field sets except raw release records, whose unselected API fields remain in retained raw bytes. Manifest size is at most 262,144 bytes. JSON uses strict UTF-8, no BOM, duplicate keys, nonfinite literal numbers, or trailing non-whitespace.

Every receipt has exactly `id`, `kind`, `content_sha256`, `retained_byte_length`, `observed_byte_length`, `complete`, `observed_at`, `validated_at`, `retained_at`, `time_basis`, and `clock`. Release receipts additionally have `slot_id` and `http`. Kinds are `question_contract`, `release_sample`, `acceptance`, and `source_blob`. Complete is an exact boolean; counts are nonnegative exact integers. For admission, complete must be true, both lengths must equal the supplied body length, and its computed hash must match. Incomplete/overflow prefixes remain caller-retained evidence and receive exclusion diagnostics; their hash is never presented as a complete response hash.

Local timestamps use UTC RFC3339 with `Z` or `+00:00` and zero to six fractional digits. Comparisons use instants, not lexicographic strings. Normalized times use six fractional digits and `Z`. Body observation must precede or equal validation, which precedes or equals durable retention. `time_basis` must be `local_clock`.

`clock` has exactly `start_utc`, `start_ns`, `observed_ns`, `validated_ns`, `retained_ns`, `start_epoch`, `end_epoch`. Nanosecond values are nonnegative exact integers in nondecreasing order. Epoch IDs must match. Each UTC elapsed interval from start to observation, validation, or retention must differ from its monotonic counterpart by at most one second. These are consistency checks of supplied claims, not independent witnessing.

Question and acceptance bodies are at most 65,536 bytes each. Release bodies are at most 1,048,576 bytes per slot. Retained header pairs have a 16,384-byte serialized bound; source blobs have the existing 8,192-byte selected-document bound. The normalized packet retains the unchanged 262,144-byte limit; existing encodings retain their unchanged 524,288-byte limit. Overflow refuses; there is no trimming, selective optional-field removal, retry, or budget increase.

## Question body

The question body is JSON with exactly `schema_version` (exact integer 1), `family`, `question_id`, `subject_id`, `knowledge_cutoff_utc`, `forecast_deadline_utc`, `outcome_cutoff_utc`, `resolution_rule_id`, and `evidence`. Family is `software_component` or `local_delivery_obligation`. IDs and times follow the grammar above. Its retained time must be no later than knowledge cutoff, then forecast deadline, then outcome cutoff. Each question fact cites this retained question-contract observation.

The adapter consumes a frozen declaration supplied by a later instance binder. It does not derive registration or accept a question payload as proof that registration happened. An independent oracle can read this public schema and the same raw contracts without importing this adapter, the view module, or their helpers.

## Release evidence

For releases, question `evidence` has exactly `source_id`, `request_url`, `opening_slot_id`, and `slots`. `slots` is an array of 1–16 objects with exactly `id` and `nominal_at`; IDs and nominal instants must each be unique. The opening ID must name a declared slot at or before the knowledge cutoff. The complete applicable schedule, including every prior pilot slot, must be bound by the caller; the eventual instance binder must check that declaration against the sixteen-slot pilot. This adapter refuses missing receipts for any declared prior/opening slot. To represent an explicitly failed/not-started prior slot, retain its receipt and available prefix/absence, which produces an exclusion reason. Future slots need no receipt.

The URL must be exactly `https://api.github.com/repos/modelcontextprotocol/python-sdk/releases?per_page=5`. Each release receipt binds one slot only; unknown slots, duplicate slot attempts, or substituted observations refuse. No research probe or undeclared source can enter. Slots after the current opening are excluded even when their claimed retention precedes the knowledge cutoff. Every valid declared prior/opening sample is preserved; a late, malformed, incomplete or missing sample is excluded with a reason. A missing/invalid opening refuses the whole packet. An actually valid empty opening is admitted and yields an empty opening-eligibility map while keeping prior IDs.

`http` has exactly `request_url`, `request_method`, `request_headers`, `status_code`, `completion`, `headers_sha256`, `headers_complete`, and `headers_observed_byte_length`. Method must be `GET`, status exact integer 200, completion `completed`, headers complete exact boolean true. Request headers must exactly equal:

```json
{"Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28","Accept-Encoding":"identity","User-Agent":"Epiphysics-Prospective-Integrity-Pilot-v1"}
```

Header bytes are strict JSON arrays of two-string `[field_name, field_value]` arrays, retaining order and duplicates. Header names follow HTTP token characters; values cannot contain CR/LF/NUL. The hash and observed length bind that exact retained serialization, whose overhead makes this cap conservative. Absence of Content-Encoding means identity; otherwise exactly one `identity` field is required. Raw Link values remain in these bytes; the conservative diagnostic parser inspects whole parameters with quoted values, never searches inside a title for a relation, and never follows links. `rel=next`, an unparseable Link, or five returned records does not invalidate the bounded sample. These retained field pairs and supplied status/request claims are not proof of actual wire execution, redirect/retry absence, or transport capture; a later collector must enforce and retain those facts.

Request start must be between nominal and nominal+60 seconds, inclusive. Both UTC and monotonic start-to-body-completion duration must be at most ten seconds. Observation, validation and retention must finish by nominal+120 seconds and retention must also be at or before this question's knowledge cutoff. These windows compare elapsed durations, avoiding calendar overflow at the accepted UTC year boundary. Eligibility never uses publisher dates, array position, source naming or purported freshness.

Body JSON must be an array of 0–5 objects. Each contains a positive integer `id` and exact boolean `draft` and `prerelease`. Repeated IDs, including identical duplicate records, invalidate that sample. IDs are never converted to floating point or strings for normalized facts. All IDs, including drafts and prereleases, are retained. The same ID in separate samples uses the same component-scoped release entity but separate observations and assertions, each with `supersedes: null`; a later state never erases an earlier one.

Only `tag_name`, `created_at`, and `published_at` additionally enter normalized facts. Presence creates an attributed `raw`/`precision`/`parse_status` object; absence creates no assertion. Null remains raw null with null precision and `unparsed`. String tags have precision `string` and status `valid`; other nonnull tag values are `invalid` and unchanged. Date strings matching a full RFC3339 seconds/fraction/offset grammar with ASCII digits are calendar-validated without converting their value. Precision is `second` or `fractional_digits:N`; the complete original fraction remains raw, including more than six digits. No fraction is used for local timing. Invalid dates, including non-ASCII digit fractions, retain raw values and `invalid`, including syntactically recognizable precision where available. Unknown API fields stay in the retained response and are counted as excluded, never inferred into facts.

## Obligation evidence

For obligations, question `evidence` has exactly the following fields:

`acceptance_observation_id`, `acceptance_sha256`, `source_observation_id`, `acceptance_event_id`, `promisor_role_id`, `beneficiary_role_id`, `authorized_submission_channel_id`, `quality_rule_hash`, `quality_parameters`, `source_sha256`, `source_byte_length`, `source_path`, `source_blob_id`, `git_object_format`, `source_commit_id`.

Acceptance and source observations must both be complete, verified against supplied bytes, and retained at or before the cutoff. No other observation is allowed. The acceptance bytes must match the question's acceptance hash. Acceptance JSON contains exactly the same fields from `acceptance_event_id` onward, plus `schema_version: 1`, `obligation_id` and `due_utc`; it omits the three observation/hash reference fields. Every binding must agree with the question declaration with exact JSON types; obligation ID must equal the subject, and due instant must equal the outcome cutoff. Roles and channel are explicit IDs; their names carry no inferred authority or direction. Quality parameters must be an object. The quality-rule hash is an explicit declared public-rule binding, not a computed quality result or a claim that a checker exists.

The exact source bytes must match raw SHA256 and integer length. Git object format is `sha1` or `sha256`; blob ID is recomputed over `blob <decimal byte length>\0<exact bytes>` with that algorithm. Commit ID must have the matching hash grammar; actual commit membership and public selection are claims for the independent selector/binder, not checked through repository reads. The canonical relative `.md` path must lie under `docs/theory/`, `docs/research/`, or `docs/applications/`, with no empty, dot, parent, backslash or NUL segments. Bytes must be strict UTF-8 without NUL, 256–8,192 bytes, at most 128 physical LF-partitioned lines. CRLF, multibyte text and final LF are preserved exactly. Empty source is a tested selection-boundary refusal. The adapter does not perform pool selection/ranking, inspect unrelated paths, infer public status, or certify absence of draft/excluded documents; the independently retained selector declaration remains a launch prerequisite. No delivery artifacts, outcomes or business-value computation are accepted.

Obligation facts cite acceptance; source facts cite the source observation. The source entity ID is `source:` plus SHA256 of canonical JSON `[source_commit_id, source_path, source_blob_id]`. Role direction is preserved even when names suggest the opposite. No document text is copied into the normalized packet: its exact retained bytes remain shared payload, and a reference is not a reconstruction claim.

## Determinism and operational limits

Release entity IDs are `release:` plus SHA256 of canonical JSON `[subject_id, integer_release_id]`. Assertion IDs are `assertion:` plus SHA256 of `[subject_id, predicate, sorted_observation_ids]`. Observation IDs are supplied declared identities. Every assertion has a singleton supporting observation here and known time equal to that observation's retained time. Entities sort by ID; observations/assertions sort by actual time then ID. Input collection order and equivalent time spellings cannot change identities. Reordering raw release records changes the raw-body hash while preserving derived fact identities; this correctly distinguishes byte evidence from semantic facts.

Accepted integers retain exact arbitrary-precision values within the runtime's parser/serializer capability. The measured interpreter is `/Users/ianderrington/miniconda3/bin/python`, Python 3.12.9 packaged by Anaconda with Clang 14.0.6. Its measured integer conversion guard is 4,300 digits: a 4,300-digit positive ID passes both saved-view round trips, while a 4,301-digit otherwise valid ID is explicitly unavailable. No global integer setting is changed, and these controls make no compatibility or boundary claim for another interpreter/version. This is an operational limitation, not a source-schema upper bound or a claim of full arbitrary-digit support. A finite lexeme such as `1e400` exceeds runtime float range and is unavailable, distinct from disallowed literal `NaN`/`Infinity`. Finite decimals that cannot round-trip through the runtime JSON number representation without changing their decimal value are also unavailable; raw bytes are never replaced by rounded values. Nested JSON beyond runtime ability likewise remains an operational refusal. The later independent oracle must preserve these distinctions and must not derive truth from this module's success/failure label.

The caller retains original manifest, bodies, prefixes and diagnostics on success or failure. The pure function cannot durably retain them itself. Engineering tests do retain those exact invented inputs, outputs and refusals. Test execution is capped at 180 seconds across builder runs, with unknown total agent/cost estimates null and zero study-program model/network/spend. No preservation score, performance comparison or seven-family result follows from these controls.
