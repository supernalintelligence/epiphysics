---
title: "Metrics for comparing representations and improvement steps"
description: "Versioned metric contracts that separate conformance, forecasts, causal preservation, operating costs, and distribution of benefits."
date: 2026-11-25
draft: false
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

A representation is useful for a specified task, observer, scale, and horizon. It is not reality, and a score on one task is not a universal measure of its value. This protocol supplies the measurement rules for the [stepwise improvement loop](../planning/stepwise-improvement-loop.md) and the [representation comparison experiments](representation-comparison.md).

## A contract before a score

Every promoted metric needs a versioned contract card. Freeze it before inspecting the outcomes used for an acceptance decision. A changed definition starts a new comparison; retain the earlier record.

| Field | Required declaration |
| --- | --- |
| Identity and purpose | Metric ID/version, owner, task or decision it informs, and what it does not measure. |
| Definition and units | Exact numerator/formula, denominator, units, direction of improvement, and aggregation. |
| Cases and eligibility | Population/cohort, family labels, inclusion/exclusion rules, source rights, snapshot cutoff, and model/input versions. |
| Horizon and resolution | Prediction or observation window; resolution source; late, revised, censored and unresolved outcomes. |
| Baseline and comparison | Frozen comparator, matched information/resource budgets, paired cases where possible, and declared controls. |
| Failure treatment | Missing answers, abstentions, timeouts, malformed output, invalid evidence, retries and duplicate attempts. |
| Uncertainty | Sampling/dependence assumptions, interval method, minimum case count, and stopping rule. |
| Decision margin | Smallest practically useful improvement, per-family floors, tolerated regression, side-effect ceilings, and rollback trigger. |

These fields are the required design for future comparisons; the present evaluator emits a fixed synthetic conformance report, not a general metric-card registry. A target with no denominator, horizon or eligibility rule is not ready for automatic optimization.

## Implemented offline contract metrics

The current suite is `engine/examples/improvement/entities.json`, evaluated by `engine/epiphysics/representation_checks.py`. It contains **30 fictional checks across seven families**. Its nine dimensions are identity, relation direction, relation type, time, units, contradiction, hierarchy, boundary, and workflow. Expected values and evidence sets are curated fixture obligations, not independently discovered truth.

| Metric | Definition, unit and direction | Failure treatment and scope |
| --- | --- | --- |
| `accuracy` | Correct declared checks / all declared checks; fraction, higher | Correct means exact expected JSON value **and** exact eligible evidence set. Missing and wrong answers count as failures. |
| `coverage` | Checks with supplied answers / all declared checks; fraction, higher subject to accuracy | A wrong answer still counts as answered. Coverage cannot substitute for correctness or licensed evidence. |
| `provenance` | Checks with exactly the required evidence set and no late cited observation / all checks; fraction, higher | Missing answers fail. This checks identifier ancestry, not source-byte span resolution or factual truth. |
| `temporal_violations` | Checks citing at least one observation recorded after the case cutoff; count, lower | Multiple late citations in one check count once. Exact-cutoff evidence is eligible. No citation is not proof that no hidden future knowledge influenced an answer. |
| `macro_family_accuracy` | Unweighted mean of the seven family accuracies; fraction, higher | Prevents a family with more checks dominating the average; still report the underlying counts. |
| `worst_family_accuracy` | Minimum family accuracy; fraction, higher | Reveals the weakest family; ties are not evidence of equal real-world difficulty. |

The report retains per-case checks and counts, family accuracy, and dimension summaries. Malformed schemas, duplicate/unknown case or check IDs, unknown evidence IDs, and invalid reference obligations are rejected rather than scored as ordinary answers. Caught failures after claiming a step produce ledger failure records. Invalid JSON or policy may be refused before a claim, leaving the queue unchanged; a dispatched child's refusal remains in process receipts/output. Include those refusals in attempt reporting instead of treating ledger transitions as every attempted run.

For fixture acceptance, the target is all declared checks correct, full coverage and provenance, and zero temporal violations. The copied-answer `reference` control is expected to pass; the `degraded` control should expose known losses. These deterministic checks have no sampling confidence interval and establish only conformance on the enumerated inputs. They do not establish model quality, scientific validity, generalization, or business improvement.

## Entity diversity and preservation

| Required family | Example obligation |
| --- | --- |
| Software service | Preserve who depends on whom, parallel relation types, retry and authority rules. |
| Organization | Distinguish ownership, containment, employees, delegated rights and disputed control. |
| Person or role | Separate similarly named people from roles; preserve changing authority and time units. |
| Contract or obligation | Retain debtor/creditor direction, currency/scale, disputed due dates, and settlement idempotency. |
| Physical asset | Preserve serial identity, measured units, part/owner distinction and observation cutoff. |
| Collective | Represent informal membership, changes through time, nested groups and disagreements. |
| Representation itself | Separate a representation from its referent; retain competing boundaries and oracle status. |

Keep these families through each candidate comparison; do not silently drop a difficult family. These seven are a diversity requirement for this suite, not an exhaustive ontology of entities. Later cohorts should vary domains and case difficulty within each family, report macro and worst-group outcomes, and account for related cases sharing a source or entity. Small groups need counts and uncertainty, not an apparently precise ranking.

## Executed source-span and history contracts

`engine/epiphysics/source_span_checks.py` now runs contract `source-span-probes-v1` against the actual assertion API using fresh temporary synthetic ledgers. Its fourteen checks are separate from the thirty representation-answer checks:

| Metric | Denominator and passing obligations | Decision rule |
| --- | --- | --- |
| `source_span_resolution` | Eight executable checks: exact multibyte content, typed assertion recording, negative/out-of-range/empty offset rejection, wrong span digest rejection, whole-blob corruption rejection, and exclusion of late evidence despite an old publication claim | Passed checks / 8; higher. Require 1 before advancing. |
| `assertion_history_preservation` | Six executable checks: historical view, current revision without erasure, coexisting conflicting reports, no revision fork, observer lineage, and separate half-open world validity | Passed checks / 6; higher. Require 1 before advancing. |

Each check is a positive or negative API contract, not a sampled source span or a real-world recall estimate. Exceptions and false results fail the check and retain a diagnostic. `report.source_span_checks` records the version, rows, counts, metrics and `all_passed`; the two fractions also appear in the assessment's metrics. Require all fourteen contracts without dropping failed rows. These deterministic counts have no sampling confidence interval and establish neither semantic extraction quality nor population generalization.

The implementation resolves byte bounds/digests against captured sources, records method identity and typed values/units, and keeps corrections and contradictions as immutable assertion events. Matching source bytes does not prove that a claim is true. Failed capability checks route to `repair_source_span_assertions`; passing them permits evaluation of B1's manifest contracts. Earlier bootstrap records accurately describe the earlier unmeasured source-span stage.

## Executed manifest metadata contracts: B1

`engine/epiphysics/manifest_checks.py` runs `representation-manifest-probes-v2` against the actual manifest API on fresh temporary synthetic ledgers. The metric `representation_manifest_preservation` is **passed checks / 22**, higher being better, with acceptance requiring 1. The checks cover stable method identity across snapshots/recapture; distinct encodings; changes to each of four artifact roles and semantic descriptor fields; retained snapshot, evidence, units and cost claims; unknown costs; rejected late/corrupt artifacts and duplicate/missing evidence; exact forecast binding; family/horizon mismatch; duplicate method/question attempts; tampering before a forecast; predictor/receipt changes between preparation and append; and exact replay after blob loss without creating a new event.

False results and exceptions fail their declared check and retain a diagnostic. `report.manifest_checks` contains version, rows, counts, metric and `all_passed`; the fraction also appears in assessment metrics. These 22 checks have a separate denominator from the 30 representation-answer checks and the 8+6 assertion checks. They are deterministic implementation contracts without a sampling confidence interval, not extraction quality, predictive performance or an estimate of success across arbitrary manifests.

B1 preserves a stable method descriptor and a particular representation/snapshot instance. The method identity includes encoding, schema, construction-method label, retained construction/configuration/ontology/predictor content hashes, observer, task, horizon and units. Snapshot IDs, times, representation payload and reported actual costs belong to the instance and do not redefine the method. The forecast adapter binds a supplied probability to the exact manifest and existing forecast safeguards; it does not run the predictor.

Construction/inference costs remain `reported` or `unknown`. Unknown quantities stay null. Receipt hashes preserve the submitted documentation, not proof that a cost occurred or a construction ran. Later cost receipts are distinguished from snapshot-eligible evidence. Do not treat these records as enforced budgets, independently measured resource use, or executable reproduction.

A B1 failure routes to `repair_representation_manifests`. Passing B1 permits evaluation of the fixed-transform contract below; B1 itself establishes neither executed transformations nor causal/semantic equivalence.

## Executed fixed graph contracts: B2a

`engine/epiphysics/transformation_checks.py` runs `graph-transformation-probes-v2` against the actual `execute_graph_transform` API. **`transformation_preservation` is passed checks / 26**, higher being better, with acceptance requiring 1. Its name refers only to this fixed identity/induced-subgraph contract, not general preservation of meaning.

The declared checks cover exact identity and zero loss; induced projection with directed/parallel edges; retained unit labels, evidence and metadata; computed removal losses; all-parent entity and relation mappings; unchanged inputs; bound start/completion records; successful and rejected replay after blob loss; changed-request refusal; unknown entity and supplied-output rejection; late recipe/configuration/implementation/dependency refusal; tampered inputs; dangling endpoints; concurrent claims; interrupted-run diagnosis; configuration/evidence mutation between preparation and completion; and durable rejection/replay of duplicate surrogate keys in recipe/configuration artifacts.

The worker computes the output instead of accepting a declared one. A completion embeds `output_model`, its hash, complete removed entity/relation records, lost evidence references and source-to-output mappings. `canonical_exact` means JSON equality only. Retained attributes and other metadata are copied; semantic consistency after projection is not inferred. The parent is limited to `directed-graph` / `epiphysics.graph.v1`. Recipe and loaded implementation/dependency bindings must be eligible in the parent snapshot; retained code bytes are verified, never executed as arbitrary programs.

False results and exceptions fail their check and retain a diagnostic. `report.transformation_checks` records version, rows, counts, metric and `all_passed`; the fraction also appears in assessment metrics. Its 26-case denominator remains separate from representation 30, source-span 8, history 6 and manifest 22. These are deterministic synthetic conformance tests without population confidence intervals, predictive lift or an independent execution witness. Replay returns a historical record, not a fresh run or current-availability claim.

B2a failures select `repair_graph_transformations`; passing its metric permits the separate B2b checks below. B2a creates no new representation/forecast manifest and does not complete all Packet B or establish arbitrary-encoding or causal/semantic equivalence.

## Executed graph partition/merge contracts: B2b

`engine/epiphysics/graph_view_checks.py` runs `graph-view-probes-v1` against `execute_graph_views`. **`split_merge_preservation` is passed checks / 45**, higher being better, with acceptance requiring 1. The name is limited to partitioning existing graph records and merging compatible graphs; it does not measure splitting physical entities, semantic fission, or redistribution of quantities.

The checks exercise exhaustive disjoint named partitions, directed/parallel/self-loop preservation, cross-partition losses, mappings for every source record and metadata field, strict merge and identical-record deduplication, parent-order normalization, unchanged inputs, bound receipts and replay. Negative cases cover missing/overlapping/empty/unknown partition assignments; conflicting entities, edges, evidence, relation IDs and root metadata; incompatible snapshots, observer, task/horizon, units, ontology and predictor; supplied output; late or altered artifacts; completion-boundary mutations; concurrent/interrupted claims; UTF-8-safe malformed-input rejection/replay; and identifier bounds. View names over 128 UTF-8 bytes produce recorded rejection before output expansion; parent manifest IDs over 512 UTF-8 bytes refuse before lookup or claim with no new events. The bound probes use multibyte identifiers and distinguish bytes from character counts.

The operation generates named output graphs and hashes, parent-tagged removed cross-edges, lost evidence-reference sets, all-parent ancestry and deduplication records. Partition groups cover every existing entity exactly; retained attributes and unit labels are copied. Merge collisions require canonical equality of full records, including provenance; differing evidence is not silently unioned. Compatible declared semantics and matching root metadata are prerequisites, not proof of semantic equivalence. Cross-view cycles can be broken by the explicitly recorded edge losses.

Controls that disable only the identifier caps fail both corresponding cases; removing only completion validation fails its three boundary cases while ordinary partition/merge checks still pass. False results and exceptions fail their declared check and retain diagnostics. `report.graph_view_checks` stores version, rows, counts, metric and `all_passed`, and the fraction also appears in assessment metrics. Keep the 45-case denominator separate from representation 30, source-span 8, history 6, manifest 22 and fixed-transform 26. These are deterministic synthetic conformance cases, without population confidence intervals, external execution witnessing or predictive benefit.

B2b failures select `repair_graph_views`; its passing metric permits the separate B2c consumer checks below. B2b alone embeds outputs without creating B1 representations/manifests. Neither a retained output nor a queued next action completes the consumer bridge.

## Atomic graph output materialization contracts: B2c

`engine/epiphysics/materialization_checks.py` runs `materialization-probes-v1` against the actual materialization API and B1 consumers. **`output_manifest_materialization` is passed checks / 30**, higher being better, with acceptance requiring 1. This is an output-consumer and atomicity contract, separate from graph-transform preservation and predictive quality.

Positive checks materialize all four fixed operations into exact graph outputs and usable manifests, preserve snapshot/artifact/semantic bindings, single- and multi-parent ancestry, loss/map links, stable derived method identities and original evidence, and exercise the existing forecast consumer. Negative checks cover wrong completion output, changed requests, altered configuration/parent evidence, incompatible execution dependency identity and non-completion inputs. Replay after blob loss is distinguished from present byte integrity.

Failure and interruption checks require the entire output set to roll back; a second connection must see no provisional outputs. Completion-boundary mutation must roll back the bundle, and concurrent claims must produce one complete output set. Mutation controls remove the atomic group, change output/binding fields, erase ancestry/links, or remove completion validation. Ordinary positive operations must still pass where the mutant is intended to target one guard. A reject-all implementation cannot satisfy the positive controls.

Resource cases cover oversized method descriptors and repeated output metadata before any output writes. Malformed completion and artifact containers must yield durable rejection and exact replay. A coherent forged completion has matching start/terminal identities and a recomputed altered-output hash, so its check must reach fixed-operation recomputation; removing only that equality guard is detected. The timing case requires grouped writes to refuse fresh evidence, questions and forecasts, permits a snapshot over retained evidence, and checks live forecasting after commit. Disabling that restriction must fail its case while ordinary materialization still succeeds.

Reports retain every check and diagnostic under `report.materialization_checks`, alongside the separate 30 representation, 8 source-span, 6 history, 22 manifest, 26 identity/projection and 45 partition/merge denominators. A fraction of 1 establishes these synthetic consumer contracts only. It does not show learned representation quality, truthful sources, an externally witnessed execution or an advantage on future questions.

Materialization failures select `repair_transform_materialization`. All preceding gates and B2c passing select `build_retrieval_baseline` (Packet C), whose **`retrieval_baseline_reproducibility` remains unmeasured**. Construction costs stay unknown; the bridge does not supply a predictor or a learned action-selection policy. New materialization requires the exact current execution contract; incompatible historical completions require a fresh eligible execution instead of silent migration.

## Prediction, calibration and coverage

For binary outcomes, use mean Brier loss `(p − y)²` or log loss `−[y log p + (1−y) log(1−p)]`, lower being better. CRPS compares a predictive cumulative distribution with a realized scalar outcome; its units follow the outcome. Proper scores reward truthful probabilities in expectation. Calibration compares probabilities with observed frequencies; interval coverage needs interval width alongside it. [Gneiting and Raftery (2007)](https://sites.stat.washington.edu/raftery/Research/PDF/Gneiting2007jasa.pdf)

This improvement evaluator does not compute those forecast metrics. Future contracts must fix probability bounds or zero-probability handling, continuous variable units, missing forecasts, outcome delays, and censoring before a run. Log loss uses dimensionless probabilities; Brier loss is dimensionless. CRPS values for different physical units cannot be averaged without a declared normalization and interpretation.

Report both answer coverage and performance on the answered subset, with all eligible cases visible. An abstaining model must not beat a full-coverage baseline merely by hiding difficult cases. Register any selective-prediction threshold before final evaluation. Show calibration by family and forecast horizon with uncertainty; a small number of outcomes cannot establish calibration.

Use prospective cohorts for claims about predicting new events. Record model/version, training-cutoff information if available, allowed evidence, prompt/tools, and every attempted candidate. Historical replay may test evidence filtering while remaining contaminated by knowledge embedded in a model. A timestamped input bundle cannot remove that contamination. Keep final outcomes inaccessible to search; selecting on final results consumes that cohort and requires a new one.

## Task fitness, causal structure and operations

| Measurement layer | Concrete question | Evidence required |
| --- | --- | --- |
| Task fitness | Does the representation improve answers, retrieval or forecasts on the registered task? | Frozen baseline; matched information/cost; scoring and coverage by family. |
| Integrity | Does it preserve sources, time, identity, units and disagreement? | Replay, mutation, late-arrival and contradiction fixtures; zero critical violations. |
| Causal or intervention preservation | Does a transformation retain predictions under specified interventions? | Explicit intervention set and variable mapping; simulator with known structure or an identified experimental design; declared tolerance. |
| Operational quality | Does the loop finish reliably within resource limits? | Attempt denominator; completion/failure rate; elapsed time and p50/p95 latency; CPU/memory/storage and model/tool charges; recovery and duplicate-effect tests. |
| Domain or business outcome | Does an authorized service create useful results for its intended participants? | Domain outcome and baseline, observation window, costs and side effects; randomized or otherwise justified causal design for causal claims. |
| Distribution and rights | Who receives benefits, pays costs, controls decisions, and can contest or exit? | Participant/group breakdown, permissions and data rights, concentration/access measures, dispute outcomes; explicit stakeholder definitions. |

A preserved correlation is not a preserved intervention. Tests of relation direction and workflow metadata are useful prerequisites but do not validate a causal model. Representation changes such as aggregation or merging need declared lost distinctions; passing a query test cannot license stronger equivalence claims.

Costs include ingestion, extraction, embeddings, index/graph building, storage, querying, evaluation, retries, review and maintenance. Report both marginal query cost and amortized total cost at a declared workload. Time and compute are real costs even when external spend is zero. Current receipts describe assessment runtime and zero program model calls/external spend; they do not measure the full builder/reviewer effort or total improvement-step cost. Those costs need separate records before learning a return-on-effort policy.

Do not collapse these layers into a universal value number. Any weighted objective is a declared decision policy with beneficiaries and tradeoffs; report its components. For distributed exchange, distinguish an offer, delivery, verified quality, payment and a governance right. Network centrality alone does not establish control, social benefit, or monetary value.

## Action forecasts and promotion

The current selector stores observed metrics, candidate actions, directional targets and reasons; estimated cost and success probability are null. A descriptive before/after comparison requires matching fourteen measurement-contract hashes: `suite`, `evaluator`, `policy`, `assertions`, `source_span_probe`, `store`, `manifests`, `manifest_probe`, `transforms`, `transformation_probe`, `graph_views`, `graph_view_probe`, `materialization`, and `materialization_probe`. These cover the declared suite/policy and all current API/probe implementations. Otherwise `prior_action_outcome` is `incomparable_contract_change`, names changed inputs, and omits both delta and `target_met`. A comparison with an earlier run lacking newly required module hashes is therefore incomparable. Candidate or controller changes alone remain comparable; missing prior measurements are `unmeasured`. Contract equality enables a comparison, not causal attribution.

Separate assessment completion from delivery success: an output-cap failure can return `assessment_completed_delivery_failed` after an authoritative completion was recorded. Count the completed assessment once, record the delivery failure separately, and use the retained transition/current queue rather than rerunning it. To learn a selector later, predeclare an outcome window, action success criterion, cost measurement and baseline policy; preserve rejected and failed actions.

Promote a candidate only when the registered practical margin, per-family floors, integrity and side-effect gates all pass with the required uncertainty treatment. Keep development feedback separate from protected final evaluation. Shadow trials, canaries and larger workloads require the additional gates in the [stepwise loop](../planning/stepwise-improvement-loop.md); fixture success alone grants none of them.
