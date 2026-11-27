---
task: prospective-raw-inputs
branch: worktree-prospective-inputs
reviewed_patch_id: f8de6d21bd1f316ada047736b370ff8bcd96133b
reviewer_model: "Codex collaborator; model identity not separately recorded"
reviewer_agent_id: /root/prospective_inputs_builder/inputs_critic
reviewer_output_sha256: 849247b6278cd42495b90c60f9d617ffd05b98d4ae388c78d7767d70551f0aca
author_session_id: ""
verdict: fixed
findings: {critical: 0, high: 0, medium: 0, low: 3}
resolved: {fixed: 3, skipped: 0}
skip_class: ""
skip_reason: ""
size: {files: 7, lines: 1018}
---

## Conclusion
Ready to land: yes
The raw-byte adapter and its explicit two-family input contract passed independent review after three retained counterexamples were repaired. This component verifies supplied evidence consistency; it neither establishes independent collection truth nor launches the prospective study.

## Checks run
The repaired adapter and unchanged views passed 52 related builder tests. The independent reviewer replayed all sixteen original controls against byte-identical inputs and added twenty-three adjacent controls: all 39 passed. Original failures and review evidence remain unchanged. Total builder test-process time was 2.147699 seconds; original plus recheck independent control-process time was 0.6815575 seconds. Both used /Users/ianderrington/miniconda3/bin/python, Python 3.12.9, with measured integer guard 4300. Root inspected each corrected source boundary and verified all twelve source, coordination and dependency pins before the source commit. Git whitespace checks and the eight configured precommit checks passed. Source commit: 4a73202aa0f245097712b9d4333c4febebf406af. The reviewed composite diff and the canonical Git diff have separately retained hashes; all seven committed file bytes match the frozen review pins. No extra source edits followed review.

## Not verified
No independent raw-source oracle, collector, runtime timing service, registration, quality or outcome resolution, actual research run, or original C12 replay was performed. No whole-repository suite, frontend build, rendered browser check, remote CI, push or deployment is claimed for this packet. New documentation is draft engineering material. Review covers supplied bytes and clock claims, not HTTP execution, independent timestamps, public source selection or actual commit membership. Two-family invented controls establish neither seven-family generalization nor predictive advantage. Agent effort, total cost, CPU/memory and utility remain unknown. The managed CLI reported a stale compiled tool and deferred its rebuild because another writer held that separate repository's lock; its executed checks and outputs are recorded without modifying or bypassing that lock.

## Findings
- [low] [fixed] Quoted Link title text was mistaken for a relation; complete parameter parsing now keeps title contents separate from actual rel parameters.
- [low] [fixed] Unicode publisher-date fraction digits were marked RFC3339-valid; ASCII grammar now preserves such raw claims as invalid optional metadata.
- [low] [fixed] Adding duration windows overflowed the maximum UTC year; elapsed comparisons preserve inclusive limits without uncaught overflow.

## Reviewer report
---
title: "Independent recheck of adjudicated raw-input repairs"
tts:
  enabled: false
feedback:
  enabled: false
---

Disposition: all three original P3 findings are closed by the frozen repair. No new actionable finding arose in this focused recheck. This conclusion is confined to the adjudicated repairs and nearby behavior; it is not registration, integration or launch approval.

Reviewed source SHA256: `d1811eba3dc2934669b46c5c29a3cf3658a9b531f403f2ed3a0519c47c1ac5d8`. Repair manifest: `c749333f8e914f279afbdedcf8af15133c0ae6a083434fbf40a85b1eed3d4abe`. Repair diff against the original freeze: `2b48f8f23a33a628c3a863a30b7d7619aae842c844c32fae2834ed84087da21a`. Full base diff: `0a6a60ad914a5edf8e74db45b8d68816ff3ccf0cd951dc8dfd2a2497f38ebc0c`. Tests: `128bda1e9bfd5aadad3aeb3935faf333b5d1dfcbe3d599f120c842370588d056`.

1. **Quoted Link parameter content — closed.** `engine/epiphysics/prospective_inputs.py:185–188` now consumes complete parameters with their quoted values, then checks the parameter name. The retained original title containing `; rel=next ` now yields `absent`. Nearby controls passed for a real next relation after a quoted title, an empty relation, uppercase parameter name, semicolons inside titles, two links, and conservatively unparseable escaped quotes/malformed headers. No diagnostic control changed release admission or answers.

2. **Non-ASCII publisher date digits — closed.** At `engine/epiphysics/prospective_inputs.py:157`, every date digit position now uses `[0-9]`. The original Arabic-digit fraction remains byte-for-byte in the raw claim and is labelled invalid with null precision. Nearby controls passed for mixed fraction digits and Unicode year digits, a valid twenty-digit ASCII fraction, invalid calendar and offset values, a valid negative offset, and explicit null. Each admitted nearby case saved/hash-checked/reread both encodings; the attributed optional value survived unchanged, and required queries decoded using only the saved bytes and a literal public query.

3. **Upper-year window overflow — closed.** At `engine/epiphysics/prospective_inputs.py:217` and `:220`, the checks now compare elapsed differences instead of adding windows to the nominal datetime. The exact original year-9999 counterexample is admitted. Adjacent controls passed at inclusive 60-second start and 120-second retention limits; one microsecond beyond either limit and one microsecond before nominal refuse with the correct reasons. Ten-second completion remains inclusive and an extra microsecond refuses. Zero-duration upper-year, full upper-year window and full year-0001 window cases all survived both saved representations and required-query decoding.

The original independent control source was copied byte-for-byte into this new review directory and rerun without modifying the original review: **16/16 passed**, compared with the original 13/16. `original-input-replay-comparison.json` establishes exact byte equality of every replayed manifest, body-identity map and raw body against the retained original inputs. The original failed assertions, tracebacks, outputs, receipts and report remain unchanged. A separate independently authored adjacent script ran **23/23 passing controls**. The builder suite was not used as independent correctness proof.

Both subprocesses used exactly `/Users/ianderrington/miniconda3/bin/python`, Python **3.12.9**, Anaconda/Clang **14.0.6**, measured integer-digit limit **4300**, with `-B`. Replay elapsed time was **0.13938837498426437 seconds**; adjacent controls took **0.2466993749840185 seconds**. Including the original review controls, total recorded independent control-process time is **0.6815574999782257 seconds**. Short local read/verification processes also stayed far below the original 90-second total allowance. `process-receipt.json` records executable/version, commands, timeouts, hashes, exits and accounting; both child exits were zero.

The before/after pin receipts check 202 artifact entries: repaired worktree and frozen copies, coordination/dependency pins, original frozen copies, every artifact listed in the original review manifest, declaration, manifests and diffs. All match, and the original review report still has SHA256 `816f18f6f1efa8e891d5cff175ae09efb3a2d9a98a93bde6c75d6a228ae55589`. No reviewed source, root coordination file, original evidence or declaration was edited by the reviewer. All new writing is under `repair-r1/review/`.

Study-program network calls, model calls and spend remain zero; whole-agent effort and cost remain null. No actual C12 ledger/candidates/keys/evaluation, research data/outcomes, collection, registration, forecasting or scheduling was accessed. Final disposition and integration remain with root.
