---
title: "Independent prospective snapshot oracle"
description: "Draft raw-byte expected-answer and support contract for two proposed pilot families."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

The separately authored `engine/epiphysics/prospective_oracle.py` derives snapshot query expectations directly from the [raw input contract](./prospective-inputs.md) and the proposed declaration v2, SHA256 `ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65`. It covers software components and local delivery obligations only. Its tests use invented bytes; no cohort has been registered or collected. The other five entity families remain unmeasured.

The author did not read, copy, import or compare the candidate normalizer, views, their helpers, tests or outputs. Standard-library JSON, SHA256, time and numeric primitives are shared dependencies, not evidence of host or mathematical independence. No candidate success label, normalized packet, saved representation, answer or producer result is an oracle input.

## Public callable and bounds

`expected_queries_from_raw_sources(manifest_bytes, bodies) -> bytes` accepts the exact UTF-8 manifest and plain dictionary of raw body/header bytes described by the raw input contract. Keys are declared observation IDs and release `<id>:headers` keys, never paths. It performs no filesystem reads, network access, command execution, model calls, ledger access, scheduling or input mutation. Module constants are immutable values; no construction input is retained in global state.

The returned bytes are sorted-key canonical UTF-8 JSON, at most 65,536 bytes. Input caps are the public raw caps: manifest 262,144; question and acceptance 65,536 each; release body 1,048,576 per slot; serialized header pairs 16,384; selected source 8,192. There are at most sixteen release receipts and eighteen total receipts. This oracle does not build a normalized packet or test candidate representation/packet-size limits. It refuses its own output overflow without trimming or returning partial bytes.

Malformed manifest/receipt envelope structure or inconsistent cross-receipt identities raises `ValueError`. Operational inability raises the separate `OracleUnavailable(ValueError)` at that boundary, including an output that exceeds the oracle cap. A caller must distinguish this subclass before a general `ValueError` handler. Raw observation problems instead appear as explicit exclusion or unavailability in a completed oracle envelope. The caller must retain original manifest/body/header bytes and exception evidence; the pure function cannot durably retain them.

| Envelope field | Meaning |
| --- | --- |
| `oracle_schema_version` | Exact integer 1. |
| `declaration_sha256`, `manifest_sha256`, `input_bodies` | Reviewed declaration identity, exact supplied manifest hash, and sorted declared body/header-key inventory with supplied/missing status, actual byte length and SHA256 or null for absent bytes. |
| `family`, `question_id` | Verified question-body claims, or null when the question cannot establish them. |
| `required_fields_by_family`, `required_fields`, `inapplicable_fields` | Public six/ten-field grammar and family-specific applicability. An unreadable question leaves family-specific fields empty rather than guessing a family. |
| `answers`, `field_status`, `required_support`, `unknown_reasons` | Every applicable field has either a known value and full support, or null, `oracle_unknown`, an empty unestablished support list and explicit reasons. Unknown support is never a vacuous success. |
| `status` | `available` only when every required field is known; otherwise `unavailable`. This is neither a numeric outcome nor a score. |
| `observations`, `eligible_observation_ids`, `missing_slots`, `reasons` | Sorted observation admission/exclusion/unavailability, positively admitted receipt IDs, missing declared prior/opening slot receipts and packet-level reasons. Individually admitted receipts do not establish an available whole snapshot. |
| `timing_assurance`, `independent_collection_verified` | Always `caller_claims_only` and false. No wire execution, independent retention or clock witnessing is claimed. |

## First explicit required-support convention

The declaration delegates enumerating full required support to the independent oracle. Before oracle execution or candidate comparison, the supervisor adopted this proposed convention without consulting candidate behavior. The private decision is `prospective-oracle-v1/root-contract-decision.json`, SHA256 `1f6c4c34974395c4f1015d72488b037f200cc0920c1dbff37254791a9a0cc70a`. This is a pre-registration convention, not a finding that a candidate conforms.

Let Q be the admitted question-contract receipt, R every admitted prior/opening release sample (including valid empty samples), O the opening receipt, A the admitted acceptance and S the admitted source blob. Each support list is unique and lexicographically sorted.

| Required field | Required eligible support |
| --- | --- |
| `subject_id`, `knowledge_cutoff_utc`, `outcome_cutoff_utc` | Q. |
| `source_observation_ids` | The complete admitted snapshot manifest, including Q: Q + R for releases, Q + A + S for obligations. The answer is that same sorted ID set. |
| `seen_id_set` | Q + every R, including samples with no release records. |
| `opening_eligibility` | Q + O, including a valid empty opening. |
| `promisor_role_id`, `beneficiary_role_id`, `quality_rule_hash`, `acceptance_event_id`, `authorized_submission_channel_id` | Q + A. |
| `source_sha256` | Q + A + S. |

The question is required for source-derived fields because it binds the subject, snapshot, selected observations and direction. Empty samples support the complete bounded source universe even though they contribute no IDs. Additional true eligible candidate references may later be permitted by the declaration, but this component neither evaluates candidates nor scores redundant evidence. Observation-level support does not assert span-level entailment.

Identity uniqueness is enforced within observation, slot and entity collections. Observation and slot IDs have separate namespaces from entity IDs. Actual body/header dictionary-key collisions and incompatible entity-kind reuse refuse. Derived source/release IDs may not collide with differently typed declared entities. Same-kind role reuse, including explicitly identical promisor and beneficiary IDs, is allowed; role names imply neither direction nor authority.

## Independent derivation and missingness

For releases, exact positive integer IDs and exact boolean draft/prerelease fields determine the seen set and current opening eligibility. All valid prior IDs remain, including drafts/prereleases, disappeared IDs and a later stable state of the same ID. Publisher values, tags, array order and purported freshness cannot establish eligibility. Unknown API fields and optional publisher metadata remain in caller-retained bytes; they do not enter these six answers. All raw JSON is still strictly parsed, including numeric values in unselected fields.

Each declared slot can bind one attempt. Slots after the opening are excluded even if their claimed retention is early. A valid opening is required. A valid empty opening gives an empty eligibility map while retaining prior history. Missing, invalid or late bodies are excluded observations, never admitted empty responses. An explicit invalid prior attempt may be excluded while preserving valid history. Established body, clock and request-window exclusions are decided before decoding irrelevant headers; a later parse/runtime limit cannot erase those known exclusion reasons. An otherwise potentially eligible prior with unreadable headers remains unavailable. A missing required prior/opening receipt, or operational inability to read potentially eligible history, prevents establishing complete membership and the seen set. A valid opening's own eligibility may remain known independently. An invalid opening leaves source-derived snapshot fields unknown while verified question identity/time fields can remain known.

Receipts independently bind body/header bytes, exact hashes, lengths, complete flags, request claims, local UTC and monotonic elapsed times, epochs, start/completion/retention windows and cutoff. Unknown or extra fields, substituted slots and undeclared dictionary keys refuse. Header order/duplicates remain in retained raw bytes; duplicate Content-Encoding fields and nonidentity encodings are invalid. A Link header, including `rel=next` or an unparseable Link value, is not a reason to reject the bounded sample. This oracle does not follow links or expose a Link diagnostic parser because Link interpretation cannot change its required answers.

For obligations, the question and exact acceptance bytes must agree on subject, due instant, directed roles, exclusive channel, quality binding, path, source length/hash and Git object/commit identities with exact JSON types. The raw blob must independently match its SHA256, length and recomputed Git blob ID. Strict UTF-8, NUL absence, canonical eligible path shape, 256–8,192 byte range and at most 128 LF-partitioned physical lines are checked without changing CRLF or final-newline bytes. Only source/acceptance/receipt evidence is accepted; no delivery or checker output enters this query oracle. If either acceptance or source cannot be established, the dependent obligation fields remain unknown.

## Runtime and assurance limits

The measured executable is `/Users/ianderrington/miniconda3/bin/python`, Anaconda Python 3.12.9 with Clang 14.0.6 on macOS arm64. Its integer digit guard was 4,300 and Python recursion setting 1,000; neither was changed. Exact IDs above 2^53 and a 4,300-digit ID passed; 4,301 digits produced explicit runtime unavailability. Finite decimal lexemes must round-trip through the runtime JSON number representation without changing decimal value. `1e400`, `1e-400` and an overprecise finite decimal were unavailable, whereas forbidden literal `NaN`/`Infinity` were malformed JSON. No rounded value replaces raw bytes. Deep JSON can also be operationally unavailable; tested depths are observations of this runtime, not a portable maximum.

This component does not authenticate registration, a complete applicable schedule, public source selection, commit membership, receipt honesty, actual HTTP requests, absence of redirects/retries, or durable readiness by the cutoff. Those are collector, selector, binder and runtime gates. It does not resolve future releases or deliveries, check document quality, evaluate preservation, score forecasts, launch a study or create a supervisor. The private expected packet must eventually be retained by C and withheld from candidates by a separately reviewed runtime.

The [implementation record](./runs/2026-11-27-prospective-oracle.md) retains checks and first failures. Frozen source requires an independent critic and supervisor adjudication, followed by separately run raw-input comparisons and unchanged saved-view checks. Agreement cannot establish truth by itself; disagreement must not be repaired by weakening frozen oracle expectations to candidate outputs.
