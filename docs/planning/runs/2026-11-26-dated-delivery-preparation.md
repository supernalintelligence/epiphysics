---
title: "C10 dated artifact-delivery preparation"
description: "Implementation and validation of one future maintenance delivery, with first-submission and timing evidence preserved."
date: 2026-11-25
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

Implementation is active in managed worktree `dated-delivery`, based on local integration commit `a4937d5`. The actual predecessor remains `improvement:decision-information-20261126:complete`, hash `de026ede9d29de02516e59119edd34ad63871f12ab434b554a71e0dd8636627d`, and its queued step is `decision-information-20261126:next / prepare_dated_evidence_quality_protocol`. No C10 preparation acceptance, task registration, actual source selection or delivery has occurred at this checkpoint.

The [public protocol](../../experiments/dated-artifact-delivery.md) describes one future link-inventory delivery serving the existing cross-reference-maintenance backlog. C9 and earlier site builds are already observed and cannot be reclassified as that future delivery. The prospective unit is the new first submitted artifact, not a claim that existing document content has never been seen.

The first independent plan review found three concrete lifecycle gaps: evidence captured after registration needed its own stable checkpoint; missing and unresolved delivery outcomes needed a finite consuming phase; and malformed first artifacts needed to remain negative delivery results instead of becoming replaceable preclaim failures. The corrected plan preserves all three and passed targeted recheck. Original plan SHA-256: `bd17336a4a4052e4dc31bec3008336082483124cc765ad90a10bcc942d2427db`; corrected plan: `b58fd8b18ce3ba79314768a49852f8aa7b55fbc385f0112f54b546a5c035d16d`; review including recheck: `b00f85a4851e64e5169d0e8ac232662803d9915a9bf02ce309da7ac63f5b9ac5`.

One builder owns phase validation, immutable ancestry, the contract and core tests. A separate author owns the pure inventory verifier and its parser controls. Root owns the existing decision-assessment bridge, controller integration and lifecycle tests. An additional non-author reviews the controller and final packet. No worker is authorized by this preparation to inspect a future selected document, execute its producer or mutate retained C8/C9 evidence. Tiny owned fixtures support implementation controls.

Private plan, validation and execution records belong in `.supernal-local/control-exchange/dated-delivery-v1/` in the persistent shared checkout. The supervisor continues active eligible work; checkpoints and the existing 15-minute recovery wake do not create permission to duplicate a running worker or rerun an exposed study.

Initial validation passed 235 tests across eleven decision/delivery modules in 40.129 seconds (40.392 seconds for the outer process), with every tracked validation input unchanged during the run. Separate retained windows passed fourteen core controls, seventeen verifier controls, and four real controller/core lifecycle controls. These used owned temporary fixtures; they did not select or execute the future maintenance task. Legacy controller controls and validation of the reviewed repairs remain pending at this checkpoint.

Review found concrete gaps despite that passing run: late submissions could rescue primary quality; future-effective verification could become operative; an asserted overflow lacked sufficient retained bytes; boolean registration versions passed into a stricter next consumer; malformed Unicode metadata could escape the negative-artifact path; pending evidence could claim the queue too early; overflow prefixes lacked registration/submission ordering; and registration did not preserve exact prepared protocol bytes. A separate verifier output-expansion finding was already repaired and independently checked. The core builder is repairing these boundaries, with separate controller tests asserting that waiting states leave the ledger and queued step unchanged. The initial reviews and validation receipts are preserved rather than replaced by later passing results.

Earlier component development also exposed raw-byte comparison and fixture-clock errors. Their first interactive failures are recorded in the component receipt summary; complete raw logs for those two initial runs were not retained. Later named validation windows have captured output. No missing log is represented as independently recoverable evidence.

The repaired source passed 246 tests across the same eleven modules in 51.208 seconds, plus six legacy controller/concurrency/recovery controls in 40.158 seconds. Both process windows retained exact source hashes and reported no changed inputs. The new three real-controller readiness controls also passed independently in 2.080 seconds with no verifier calls or event/queue mutation. Independent repair review and the private preparation-caller review are still being completed; no actual preparation result is implied by these fixture passes.
