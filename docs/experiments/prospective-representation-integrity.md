---
title: "A prospective representation integrity pilot"
description: "Proposed comparison and the first implemented saved-view component; no prospective run has begun."
date: 2026-11-26
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

The proposed pilot compares a chronological table and a typed directed graph over the same dated evidence. Its two families are sampled software releases and local delivery obligations. Eight questions, sixteen bounded source samples, sixteen method slots and four shared deliveries are proposed. Both forecast controls return 0.5, so equal Brier loss is expected; this is an integrity and preservation comparison, not a claim of predictive advantage. Nothing has been registered, collected or scheduled for this pilot.

The reviewed declaration v2 is retained privately with SHA256 `ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65`. It separates original source access during construction from decoding the saved representation, and separates registration inputs from the receipt/time bindings generated later. A local role name is not authenticated independent authorship. The independent raw-source oracle, collector, timing support, producer, quality checker, registration bindings and complete runtime review remain required future work.

## Implemented slice

`engine/epiphysics/prospective_views.py` implements pure encoders and decoders. It does not read files, contact sources, open a ledger, schedule work, issue forecasts or score a study. The caller supplies bounded UTF-8 JSON bytes to `encode_flat` and `encode_graph`; each returns bounded encoding bytes. The caller must save those bytes, hash them and reread the same bytes before calling `decode_flat_answers` or `decode_graph_answers`. Tests perform that actual file round trip. A future runtime must enforce and retain its own corresponding receipt.

Both decoders accept only `(persisted_encoding_bytes, public_query)`. Public query has exactly `query_schema_version: 1`, the declared `family`, and the ordered required field names. It carries no question/role/source identifiers, absolute times, answers, expected provenance, source packet or fallback callback. The wrapper may later attach envelope identity and probability 0.5, but cannot fill or correct an answer. Decoders share a pure semantic query implementation after reconstructing facts from their own format; this is not two independently implemented oracles.

## Normalized fact packet, version 1

The input has exactly `schema_version`, `family`, `entities`, `observations` and `assertions`. Its maximum is 262,144 bytes. Family is `software_component` or `local_delivery_obligation`. This is a deliberately bounded pilot schema, not a universal entity ontology. A future normalizer must produce the same eligible packet for both encoders and independently establish its relationship to raw source bytes.

| Collection | Exact record fields and interpretation |
| --- | --- |
| `entities` | `id`, `kind`. IDs are unique within the entity collection. Kinds are question, software component, release, local delivery obligation, role, source or channel, using the code's underscore spelling. Exactly one question is required. |
| `observations` | `id`, `kind`, `content_sha256`, `observed_at`, `retained_at`, `time_basis`. Kinds are `question_contract`, `release_sample`, `acceptance`, `source_blob`. Time basis is explicitly `local_clock`. Each retained timestamp must be at or after observation and at or before the question's knowledge cutoff. |
| `assertions` | `id`, `subject`, `predicate`, `object`, `observation_ids`, `known_at`, `supersedes`. Object has exactly `type`, `value`: entity reference, string, integer, boolean or JSON as prescribed by the predicate. Subject/target kinds enforce relation direction. Known time cannot precede its cited retained observations or exceed the cutoff. |

The predicate registry in the module is the normative type map. Question facts bind subject, knowledge/forecast/outcome deadlines, resolution-rule identity and, for release questions, the opening observation. Release facts bind component, integer ID, draft/prerelease state and optional attributed publisher fields. Obligation facts bind promisor, beneficiary, submission channel, source, acceptance identity and quality rule/parameters. Source facts retain hash, path, blob identity and byte length. Predicates outside that explicit registry refuse. Missing required query facts refuse at decoding rather than becoming defaults. The validator is not an independent check that the normalizer included every source fact.

Observation references must exist in the packet. Empty assertion support may be retained as missing provenance but cannot license a required answer. Release assertions additionally require exactly one explicit release-sample reference: losing that reference refuses, rather than changing which observation the assertion belongs to. Supersession links preserve the original assertion, require the same subject/predicate and nondecreasing knowledge time, and reject missing ancestors, forks and cycles. A release correction must remain within the same sample as its predecessor; a later sample is a separate observation, not a revision that erases the earlier one. Conflicting active values refuse a single-valued query. Matching active values may combine their cited support. These conventions are declared representation semantics, not assertions that the underlying evidence is true.

Release assertions are scoped to one source sample; their chronological repetition does not erase earlier samples. The seen-ID answer unions all sampled IDs, including draft/prerelease IDs. Opening eligibility uses the opening sample's exact boolean fields; missing booleans do not mean false. Stable transitions under the same ID do not invent new IDs. The module answers these snapshot queries only; it does not resolve future release novelty. Large integer IDs remain integers. A missing opening observation refuses, while a declared empty opening sample can yield an empty map. Raw response validity/completeness is a future collector/oracle responsibility, not established by the `release_sample` label.

Optional `tag_name`, `created_at` and `published_at` assertions retain an object with `raw`, `precision`, `parse_status`. Raw JSON values, including malformed dates and explicit nulls, remain distinct from absent facts. These publisher claims cannot substitute for knowledge times or change release eligibility. Source hashes and time labels are retained declarations here; this slice does not read the referenced blobs or independently witness time.

## Saved forms and queries

The flat form contains chronologically ordered assertion `rows`, sorted by actual knowledge instant then assertion ID, plus entities and observation metadata. The graph form contains typed `nodes` and directed assertion `edges`. Each edge has its assertion ID, source entity, predicate, either an entity target or typed scalar/JSON literal, observation references, known time and supersession link. Entity relations must use the target field; hiding an entity reference in a literal refuses. Graph targets are real relation endpoints, not a cached answer dictionary. Both forms retain the SHA256 of the exact input packet, preserving evidence that both constructors received equal bytes without giving the decoder access to those bytes.

The encoding limit is 524,288 bytes and the answer limit 65,536 bytes. Duplicate JSON keys, malformed UTF-8, nonfinite numbers, unknown fields/types, dangling references, unsupported clocks and overflow refuse. Nothing is silently truncated, filtered or repaired. A lossless round trip preserves the normalized facts and their metadata, not every field from the original external API response. The proposed pilot deliberately excludes unselected API fields from its normalized universe.

Common answers are subject identity, knowledge/outcome cutoffs and included observation IDs. Release answers add seen IDs and opening eligibility. Obligation answers add promisor, beneficiary, source hash, quality-rule hash, acceptance identity and submission-channel identity. Every field returns observation-level provenance. Valid extra support can remain visible; this module does not score exact evidence-set equality or prove span-level entailment. The independent oracle must later determine required support from raw evidence without calling these query functions.

## Validation and remaining gates

Invented controls save/reread both encodings, compare independent literal answers, preserve malformed optional metadata, check directed roles and revisions, and remove every encoded copy of a unique required fact or its required support. Loss causes refusal and cannot be repaired through the original packet or shared state. The [implementation record](../planning/runs/2026-11-26-prospective-views.md) records executed checks, artifacts and limits.

This module is not yet connected to the bounded pilot runtime or the shared work-contract dispatcher. It adds no registration, external requests, model calls, transactions, scheduler or continuation authority. Its tests do not establish hostile-host isolation, real observation completeness, forecast calibration or graph superiority. The proposed 10–60-second start windows cannot be met by the existing 15-minute heartbeat alone; that remains an explicit launch prerequisite.
