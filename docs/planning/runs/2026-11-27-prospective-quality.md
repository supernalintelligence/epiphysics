---
title: "C20 independent artifact quality implementation record"
description: "Frozen invented controls, retained first failures and bounded content-only checking."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

C20 adds the independently authored [artifact content checker](../prospective-quality.md), its focused tests and public documentation. The supervisor selected this packet after C19; its source base is `466ee4f19847dc81ec649059813718730c9378d2`. The private proposed declaration was verified as SHA256 `ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65`. Its exact bytes remain private. This is pre-registration engineering; nothing was selected, registered, collected, delivered or scored for an actual pilot.

## Implementation and independence

The pure `check_line_index` API accepts exact source bytes and one complete supplied artifact, with explicit missing-input semantics. It returns a tri-state quality judgment and exact supplied-byte identities. It checks the fixed field sets, primitive types, strict JSON/UTF-8 parser policy, 65,536-byte artifact cap, LF byte boundaries and SHA256 of every complete slice. It distinguishes proven content failures from unavailable source/parser capacity. Its 8,192-byte source capacity does not assert source eligibility. Source qualification, completeness, firstness, clocks, acceptance, rights, payment and final outcome remain separate.

The checker was authored from the declaration and invented raw byte literals. No producer, prospective normalizer, view, query oracle, query checker, production helper or their tests were read, imported or reused in this build. The existing package initializer contains only its description/version. Standard-library dataclasses, JSON and SHA256 are shared dependencies. The future producer is not implemented or selected and requires a different author. This establishes a bounded authorship/dependency separation claim, not host isolation or mathematical independence.

## Frozen controls and retained first failures

Before the first checker execution, 88 explicit source/artifact controls were retained with independently stated byte partitions and expected results. Their manifest SHA256 is `01bac89e124a0243eb6aaf479d5543ee54b5b266387969a8a5e2b88a5061625a`. The control preparation program used explicit source/slice literals and standard-library hashing, without a candidate import or line-splitting helper. Source, test, runtime/dependency, declaration and control pins were frozen before execution. Short, empty, newline, Unicode, non-UTF-8 and NUL-containing controls are labeled invented boundary fixtures; none are actual selected documents or proof of eligibility.

The first run executed 12 test methods and retained two failures. One private control assumed that 2,000 nested JSON arrays would exceed parser capacity; a public test assumed the same at Python's recursion limit plus 100 (1,100). Python 3.12.9 parsed both and the checker correctly rejected the top-level list as a schema failure. The two expectations incorrectly equated Python's general recursion setting with the JSON scanner's threshold. The first source/test snapshot, manifest, stdout, stderr and receipt remain unchanged.

A separately retained standard-library-only probe observed successful parsing at depths 1,100 and 2,000 and `RecursionError` at 32,000, with the global recursion limit still 1,000. The supervisor inspected the source, original failure output and probe, and approved only a distinct control/test correction. No checker source changed. No new depth scanner or global recursion/digit setting was introduced.

The v2 control manifest keeps the original 2,000-depth bytes with their corrected schema-failure expectation, adds an explicit 32,000-depth unavailable control, and contains 89 cases. Its SHA256 is `7d970a2b3305f94d07e51c2f4cdd29691dbd4087bb2c47465e29746fd399a9e5`. The public test now uses the observed 32,000-depth control. That depth is an observation on the pinned Python 3.12.9 runtime, not a portable parser limit. A separate injected parser-memory failure checks unavailable-result semantics.

## Actual bounded execution

The interpreter was Python 3.12.9 at the supervisor-specified local interpreter path, with executable, libpython and loaded standard-library source/extension hashes retained privately. Every subprocess had a wall timeout. The dedicated suite discovers only `test_prospective_quality.py`; no existing candidate, C12/C17 comparison or broader experiment suite was executed.

| Execution identity | Observed result | Outer subprocess wall seconds | Nested runner seconds | Timeout seconds |
| --- | --- | --- | --- | --- |
| builder-v1 | 12 tests; 2 depth-expectation failures retained; 87/88 private controls matched | 0.095622583 | 0.009 | 30 |
| depth-probe-v1 | Three standalone stdlib parser observations completed | 0.020711042 | unmeasured | 5 |
| builder-v2 | All 12 tests passed, including all 89 corrected/new private controls | 0.117587209 | 0.013 | 30 |
| missing-controls-v1/unset | One explicit unavailable-fixture skip | 0.126268708 | 0.000 reported | 5 |
| missing-controls-v1/missing-directory | One explicit missing-fixture skip | 0.088978458 | 0.000 reported | 5 |

Total measured outer test/control subprocess time is 0.449168000 seconds, below the separate 180-second builder allowance. Nested timings are displayed separately and are not added to that total. Preparation, authoring, filesystem pinning and whole-agent effort were not measured by these subprocess timers. CPU, peak memory, whole-agent effort and monetary cost remain unknown. Reported zero nested time is runner rounding, not a zero-cost claim. The two missing-fixture checks are skips, not passing fixture evidence.

Controls cover ordinary/empty sources, terminal and nonterminal LF, CRLF/lone CR, multibyte byte offsets, full-slice hashes, exact identities under whitespace, reordered/missing/extra lines, primitive confusion, missing/extra fields, duplicate and escaped keys, malformed UTF-8, BOM and trailing bytes, nonfinite values, huge integers/exponents, depth capacity, exact byte caps and unavailable inputs. Original and corrected control identities remain separate. Tests do not prove complete delivery, source selection, runtime timing guarantees or outcome resolution.

## Freeze and review state

The full proposed diff includes the five builder-owned source/test/document paths and three unchanged supervisor-owned planning/status paths. Before independent review, new files are included using intent-to-add, the complete diff is retained, and changed files, declaration, runtime/dependencies, control snapshots, receipts and evidence are pinned. The supervisor-owned file hashes are checked unchanged. All first failures remain retained; the candidate source is held fixed.

One fresh unguided critic will review this exact freeze read-only with a separate maximum 90-second invented-control budget. Review and supervisor adjudication are pending at this source freeze. Any finding or permitted repair requires distinct retained evidence; this record does not claim landing approval or launch readiness. The root supervisor owns adjudication, commits and landing.

The private evidence directory is retained by the supervisor and is not published here. It contains versioned manifests, source/test snapshots, interpreter/dependency pins, exact output and receipts, the separate depth probe and the control-only repair basis. Public source and tests operate without that private directory; absent private controls are explicitly skipped rather than represented as successful checks.

No new scheduler, store, collector, generic schema framework or producer was added. No models, network requests, transactions, registrations, source-pool reads, source selections or publication actions occurred. Quality checking remains one component of the proposed two-family integrity pilot; the other five families and any predictive, learning, causal or business advantage remain unmeasured.
