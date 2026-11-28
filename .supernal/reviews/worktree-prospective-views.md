---
task: prospective-persisted-views
branch: worktree-prospective-views
reviewed_patch_id: 36a7b259a3744fcff895332d8d5e6db7fef461ff
reviewer_model: "Codex collaborator; model identity not separately recorded"
reviewer_agent_id: /root/prospective_views_builder/views_critic
reviewer_output_sha256: 285ff7f25e62103cd47e7301cd2175d2485ccdfd8018f7b1d7f68e890a94d706
author_session_id: ""
verdict: fixed
findings: {critical: 0, high: 0, medium: 2, low: 0}
resolved: {fixed: 2, skipped: 0}
skip_class: ""
skip_reason: ""
size: {files: 6, lines: 761}
---

## Conclusion
Ready to land: yes
The two saved-representation decoders and their bounded constructors passed independent review after both concrete counterexamples were repaired. This is a pure normalized-fact component; no actual pilot or original trial is run by this patch.

## Checks run
All 24 repaired builder tests passed in 0.191372 seconds of outer execution. The independent reviewer preserved both initial failures and checked their corrected behavior plus adjacent sample history, chained revisions, optional JSON and obligation behavior: 25 grouped controls passed in 0.281224 seconds. Root verified all six reviewed file pins and the unchanged store dependency. Fresh content preprocessing and the research-progress/public-map checks passed in 3.856972 seconds, with generated cache restored and frozen source unchanged. Both new documents are drafts excluded from generated public content; subsequent repair edits kept their metadata and draft state unchanged. No shared foreign cache was replaced. The exact reviewed diff remained unchanged after incorporating the separately reviewed daily-observatory refresh. Source commit: 4f8afff70dc4f0ab78bdc45c060fd1c1e03ed3d3. Eight configured precommit checks passed.

## Not verified
No full project build or suite, browser check, deployment, actual C12 replay, prospective pilot registration, source collection, scheduler or runtime integration was performed by this component. The separate daily observatory refresh is already integrated and does not supply pilot data. Normalized source facts, time claims and hashes are not independently verified raw evidence. The pilot still needs its collector, normalizer, independent oracle/checker, registration bindings and timing support. Two-family fixture results establish neither seven-family generalization nor predictive advantage. Data-flow inspection is not hostile-host isolation; unmeasured agent effort, CPU/memory costs and next-action utility stay unknown.

## Findings
- [medium] [fixed] Missing sample support on a superseding release correction could reactivate a superseded value; every release assertion now requires one sample and revisions stay within that sample, preserving separate historical observations.
- [medium] [fixed] A graph could hide all entity relations in literal slots while returning complete answers; entity objects now require actual graph targets and malformed literal substitutions refuse.

## Reviewer report
# Independent repair recheck

Disposition: both original P2 findings are independently closed for the exact repaired frozen revision. No additional actionable finding in the repair or adjacent behavior reviewed. This is a scoped component acceptance, not approval of prospective registration or runtime operation.

## Finding closure

**Release revision support loss: closed.** The original reviewer-owned saved encodings are replayed read-only. Their intact baselines and corrections retain exactly the original answers; removing correction provenance now raises `ValueError: A release assertion requires exactly one sample provenance` in both flat and graph decoders. New independently invented controls confirm that removing an intermediate revision's support also refuses, as do contract-only support, two samples, and cross-sample revision links. The new one-sample requirement plus same-sample revision constraint closes the route by which sample filtering hid a supersession relation. Three valid chained same-sample corrections preserve the final corrected answer.

**Entity relations as graph literals: closed.** The unchanged original zero-entity-target counterexample now raises `ValueError: Entity graph relations require a target`. Adjacent controls confirm that disguising entity relations as string/JSON literals and moving a scalar fact to an entity target also refuse. A valid publisher JSON payload containing nested keys named type/entity remains ordinary data and round-trips successfully.

## Adjacent behavior

New independent release fixtures verify that a prior draft sample and a stable opening sample remain distinct, retain the same seen release ID, and answer each sample's eligibility correctly. Valid extra non-sample support remains allowed alongside exactly one release sample. New obligation fixtures retain role direction, source provenance and non-release revision behavior without requiring release samples. All tested encodings were saved and reread from this new review directory. No broad builder suite was run.

The repair deliberately narrows the pre-run normalized schema: every release assertion requires exactly one sample; a new sample is an independent observation rather than a cross-sample revision. That rule is reflected consistently in the module, changed tests and public explanation. The root-owned DAILY_LOOP.md and TODO.md remain identical to their previous freeze. Module consumers remain the previously reviewed tests; no runtime integration was added.

## Scope, evidence and limits

Inspected the repair-only diff, current six-file `git diff HEAD`, empty staged diff, affected implementation and tests, and updated documentation. Both repaired manifest/diff pins and all six source hashes plus store.py dependency hash match before and after recheck. HEAD remains `0d07270e7cfce096bebc7b81b3aeb3d7dfc9b67d`. Original manifest/diff pins still match; all 27 files in the original review directory have identical before/after hashes.

`recheck.py` independently replayed the reviewer-owned synthetic counterexamples and used newly invented release/obligation inputs. **25 focused controls passed** in **0.28122391598299146 seconds outer runtime**, within the 45-second allowance; internal check time was 0.20201029104646295 seconds. These are grouped controls, some covering both forms, not 25 independently sampled research cases. Full output, exact command, UTC execution start and output hashes are in `checks.stdout`, `checks.stderr`, and `checks-receipt.json`. Exact verification times/hashes are in `pins-before.json` and `pins-after.json`; saved sources, encodings and answers are retained alongside them.

No frozen sources or original review artifacts were edited. Actual store/ledger actions, network/model/paid calls, prior-study candidate access, collection, registration, scheduling and commits: zero. This recheck does not establish raw-source truth, collector completeness, independent oracle correctness, runtime isolation or live timing; those remain separate declared gates.
