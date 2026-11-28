---
title: "Timestamp research selected for the knowledge map"
description: "A bounded catalog extension and coordinated public provenance refresh, preserving the public selection."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: false
---

## Why explicit curation was needed

The attempted private refresh stopped before compilation: the [snapshot essay](../../research/knowledge-snapshots.md) was not one of the catalog's 37 selected documents, and none of those 37 document hashes had changed. The retained preflight refusal corrected the earlier assumption that landing the essay would automatically update the graph.

This packet adds six nodes and eight directed edges. It selects the already committed essay and [time-witness research record](2026-11-27-time-witness-research.md), adds the exact OpenTimestamps client reference, and separates three claims: RFC 3161 accuracy semantics, pending OpenTimestamps proofs, and the proposed conservative cutoff rule. Existing nodes, edges and claim statuses remain unchanged; the broader `claim_witness`, `rfc3161_timestamp` and `opentimestamps` entries are reused rather than replaced.

[RFC 3161 section 2.4.2](https://www.rfc-editor.org/rfc/rfc3161.html) supports the reported accuracy definition. The [OpenTimestamps client documentation](https://github.com/opentimestamps/opentimestamps-client) supports the client-specific pending/completion distinction, hours-long confirmation description and Bitcoin Core verification requirement. The latter is an undated, mutable bibliographic reference: its remote bytes and immutable revision were not retained. The cutoff rule remains an inferred, unimplemented proposal under an explicit trust policy; no backend, library or provider is selected. The current pilot's external witness remains null.

## Public provenance dependency

The public exporter checks all four catalog files against its exact committed pin before selecting allowed nodes. Consequently, even this private addition requires a coordinated provenance update to preserve the existing public verifier. Root authorized a four-file packet: the registry, this note, the public policy and the saved public map. The policy's node and document allowlists must remain unchanged.

The public selection contains 61 nodes, 70 edges and 12 documents. All 12 document contents match the previous public pin. The planned replacement may change only source-commit references and derived catalog/payload hashes; public claim statements, source metadata, document content hashes, routes and edges must remain identical. Neither selected draft document is approved for the public map.

The managed worktree's original generated content is stale and lacks the approved routes. After the catalog commit establishes a new pin, the existing content preprocessor must run once, followed by an explicit exporter replacement bound to the previous artifact's exact raw hash and the read-only verifier. Generated content will be archived with its verification evidence before restoring only this worktree's original generated file. No shared checkout cache is used.

## Validation and handoff boundary

One catalog validation passed in 2.076692 seconds under a 30-second process limit. Its private candidate contains 157 nodes, 190 edges and 39 documents: the existing 37 plus the two newly selected documents. All document bytes came from committed HEAD `f22ae969a5d7fe3285db0dd41d9d2a7c9ca62a75`; this new run note is not a selected graph document. The candidate payload hash is `368c5c17e8ff13375aeed8c75d4279ca9d6049718e25b64e6bf52e3f209d9b19`. The candidate and complete source identities are retained privately under `.supernal-local/timestamp-map-20261127/`. This validates catalog structure and retained local bindings, not claim truth or external witnessing.

This record is prepared before public export and complete-packet review. Their actual outputs, source comparisons and any failures belong in the retained handoff receipt; this note does not assert that those future steps passed. Root owns independent acceptance, integration and the final private graph refresh. No new web research, witness submission, cryptographic service test, model call, research cohort, production build or deployment is part of this packet. External program spend is zero; whole-agent cost is unknown.
