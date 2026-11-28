---
title: "Captured-artifact quality evidence"
description: "Pure bounded intake of supplied capture bytes, with conditional consistency and independent content results."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

`engine/epiphysics/prospective_quality_evidence.py` connects the
[C23 capture format](prospective-capture.md) to the unchanged
[C20 content checker](prospective-quality.md). Its result is explicitly
**conditional supplied-byte consistency and content evidence**. Matching
caller-supplied hashes cannot authenticate a capture, prove ledger membership,
establish registration or authorize continuation.

## Six-input contract

`assess_captured_artifact` has exactly six required keyword arguments. Each is an
exact built-in `bytes` value or `None`; `None` means unavailable. Byte subclasses,
bytearray and other types are unavailable inputs. It returns canonical UTF-8 JSON
as exact `bytes`, at most 4,096 bytes. The fixed evaluation contract identifier is
`captured-line-index-evidence-v1`, with output `schema_version=1`.

| Argument | Inclusive byte cap | Meaning |
| --- | ---: | --- |
| `expected_bytes` | 16,384 | Caller-supplied expected contract and event-byte anchors |
| `claim_bytes` | 65,536 | Complete canonical C23 claim event envelope |
| `terminal_bytes` | 65,536 | Complete canonical C23 terminal event envelope |
| `receipt_bytes` | 65,536 | Exact canonical capture receipt referenced by the terminal |
| `source_bytes` | 8,192 | Exact source bytes to bind and check |
| `stdout_bytes` | 65,536 | Exact retained stdout bytes, possibly a prefix |

The accepted aggregate input cap is 286,720 bytes. Oversized inputs are not
hashed or parsed; their available length is reported with no digest. Other
bounded available inputs retain their own identities. This is a data-volume
bound, not a guarantee against host failure or an external execution timeout.

The expected contract has exactly `schema_version`, `binding`,
`source_byte_length`, `capture_sha256`, `runtime`, `claim_bytes_sha256` and
`terminal_bytes_sha256`. Version is integer 1. `binding` has the ten existing C23
fields: `instance_id`, `question_id`, `slot_id`, `channel_id`,
`acceptance_sha256`, `declaration_sha256`, `source_sha256`, `schema_sha256`,
`producer_sha256` and `worker_sha256`. Identifiers use C23's 1–120-character ASCII
pattern; digests are 64 lowercase hexadecimal characters. `runtime` has exactly
`path`, `sha256` and `version`, matching the expected claim metadata.

The caller must obtain these expectations separately from the evidence being
tested: approved capture/source/runtime contract references and exact event-byte
anchors from its trusted retained-event export. C24 does not create, discover or
authenticate that provenance. It is possible to supply a self-consistent invented
contract and invented evidence; the resulting conditional content statement is
not proof that a capture occurred. The tests deliberately do this and label all
such metadata as invented.

Actual loaded C20/C24 code and runtime pinning remain separate caller prerequisites.
The output's evaluation-contract string is a format/semantic identity, not a
measured source hash or a loaded-code attestation. Capture/runtime hashes found in
metadata are compared as declarations, never manufactured into such an attestation.

## Structural verification and content admission

Metadata must be strict UTF-8 JSON with no duplicate keys or nonfinite values,
and must match its exact compact, sorted-key canonical encoding. Artifact stdout
does not have this metadata-canonicalization restriction: C20 still permits
insignificant JSON whitespace. Metadata numbers are bounded to signed 63-bit
magnitude for integers and finite floats of at most that magnitude. There are at
most 4,096 visited metadata nodes, depth 32, strings of 4,096 characters, runtime
version strings of 1,024 characters and error-description lists of sixteen items.
Unsupported shapes, excessive capacity or unknown versions stay unavailable.

The consumer verifies the current C23 event, claim, receipt and stream shapes and
their primitive types. It recomputes the existing ledger event hash over exactly
`id`, `kind`, `recorded_at`, `body` and `previous_hash`. The caller's raw event-byte
hashes also bind `seq`, which that event hash does not include. The claim ID is
derived from the canonical instance/channel pair; the terminal ID adds
`:finished`. Kinds, positive sequences and terminal-after-claim sequence order
must match. The terminal need not immediately follow the claim: unrelated ledger
events may intervene. Two consistent event envelopes do not establish full chain
membership or an exclusive first attempt.

Expected binding/capture/runtime declarations, claim ID/hash, epoch, terminal
receipt hash, source length/hash and stream identities must agree. Receipt and
stdout paths must lexically match the claim's channel directory. Paths are never
opened, resolved or traversed. Stderr metadata is checked structurally, but no
stderr bytes are supplied or claimed verified by this API.

Only consistently bound, complete, nonempty stdout enters C20. Admission requires
observed EOF, `complete_bytes_observed=true`, `retention_verified=true`, a
well-formed non-null file-durability observation, and equal actual/prefix/retained/
full identities and byte counts. The exact supplied source and stdout are passed
once to unchanged `check_line_index`; expected bytes never replace either input.
The returned C20 type, allowed reason, tri-state quality and every source/artifact
identity are checked before inclusion in the result.

| Result status | Meaning | Quality result |
| --- | --- | --- |
| `checked` | Admitted complete nonempty bytes received a content judgment | Exact C20 true/false and identities |
| `closed_empty` | Consistent retained EOF with zero stdout bytes | Null; no checker call and no no-submission claim |
| `overflow_observed` | Bound receipt reports more than 65,536 observed bytes; only its verified prefix is supplied | Null; prefix never enters C20; size/outcome resolution deferred |
| `unavailable` | Missing, malformed, over-cap, misbound, unretained, incomplete or otherwise unresolved input/checker evidence | Null, except a valid C20 unavailable result retains its own null quality and identities |

Reasons are fixed, bounded strings: input-specific missing/type/capacity reasons;
metadata format/schema/capacity reasons; event/contract/receipt/source/stdout
binding or consistency reasons; and checker unavailable/error/contract-mismatch
reasons. No exception message or arbitrary input text is echoed. An unexpected
checker exception cannot become `quality=false`. Python cancellation, including
`KeyboardInterrupt` and `SystemExit`, propagates; no return or missing return
establishes a successful evaluation. Outer failures remain unresolved at the caller.

## Independent facts and remaining provenance

Nonzero exit, unreaped-child metadata, stderr retention problems, close uncertainty
and unverified local clocks do not automatically determine artifact quality.
Their field shapes are validated, but C24 does not reimplement lifecycle or clock
resolution. A consistently retained complete malformed nonempty artifact may
receive a genuine C20 false content judgment. Incomplete or misbound bytes may not.

Every result includes the six supplied-input identities, an optional C20 result,
and any admitted stdout observed-count lower bound. It always states
`publication="not_assessed"`, `firstness="not_established"`,
`obligation_outcome=null` and `continuation_allowed=false`. There is no date, rights,
registration, source-selection or outcome judgment. Returned publication evidence
is outside these six inputs: its separate actual observation must be retained by
the caller. Neither terminal `recorded_at`, its eventual commit, receipt-file
durability nor content success reconstructs lost or timely publication.

The required trusted capture provenance and committed-event export/anchor source
remain an upstream gap. C24 verifies consistency conditional on supplied evidence;
it cannot independently observe EOF, fsync, worker execution, trusted code loading,
ledger commitment or surviving supervision. No disk/ledger provenance acquisition,
new ledger, queue, controller, producer launch or registration is added here.

The module imports only the unchanged content checker and standard library.
Its small local canonical/digest operations match the inspected ledger functions;
importing that ledger or capture module would perform source-file reads. No upstream
module was refactored. The [execution record](runs/2026-11-27-prospective-quality-evidence.md)
retains the fresh controls, original results, actual identities, costs and review state.
