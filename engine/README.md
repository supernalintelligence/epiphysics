# Local research engine

This first slice preserves observations, information snapshots, representation hypotheses, prospective binary forecasts, and corrected outcomes in a local SQLite event ledger. It runs with Python 3.10+ and the standard library. It does **not** yet learn representations, call an AI model, pay agents, or obtain independent timestamps.

## Run and verify

Run from the repository root:

```sh
PYTHONPATH=engine python3 -m unittest discover -s engine/tests -v
PYTHONPATH=engine python3 -m epiphysics --store engine/.data/demo demo --output engine/.data/demo-export.json
PYTHONPATH=engine python3 -m epiphysics --store engine/.data/demo verify
```

The demo uses fictional evidence, probabilities, outcome, and clock. It requires an empty store and never overwrites an existing export. Choose a new directory and filename to rerun. `src/components/home/observatory-demo.json` is the generated artifact displayed by `/observatory`.

## A bounded collection cycle

```sh
PYTHONPATH=engine python3 -m epiphysics --store engine/.data/local cycle --config engine/examples/local-cycle.json --run-key first
# Run later with a new scheduler key, at least two minutes after the first run.
PYTHONPATH=engine python3 -m epiphysics --store engine/.data/local cycle --config engine/examples/local-cycle.json --run-key second
PYTHONPATH=engine python3 -m epiphysics --store engine/.data/local score
```

Each cycle captures up to ten explicitly configured sources, resolves eligible earlier byte-change questions, creates new questions, and records a constant 0.5 forecast. Duplicate completed run keys return the original result. An interrupted run requires inspection and a new key; partial records remain. There is no retry loop or shell execution. This is a collection and scheduling test, not a substantive forecast of an institution or an AI system.

A source is either `{"id":"signal","kind":"file","path":"signal.txt"}` (relative to the configuration file) or `{"id":"public-source","kind":"https","url":"https://example.org/data"}`. Each response is limited to 1 MB and a ten-second network timeout; redirects are refused. Use only sources appropriate to archive. The configuration is trusted operator input, not a public API. It can read explicitly selected local files and network addresses; do not expose it to untrusted callers.

`horizon_seconds` must be at least 120. `max_lateness_seconds` is the allowed delay after that horizon, from zero through seven days. The question is whether exact bytes differ at the **first successful capture within that window**. Missing windows remain unresolved and receive an expiration record on a later cycle, even when collection fails. Dynamic timestamps in a page count as byte changes. Semantic interpretation is not implemented.

`engine/examples/project-cycle.json` monitors this project's README on a daily horizon with a 36-hour grace period. It is a plumbing baseline and can be invoked by the bounded research cadence in `DAILY_LOOP.md`. Manual examples use ignored `engine/.data/`. Scheduled project evidence uses the shared checkout’s `.supernal-local/observatory`, outside disposable worktrees; back it up separately. Run the scheduled configuration from that shared checkout so source paths remain stable. A scheduler invocation is required: the CLI does not run a daemon.

## Record contracts

Use `capture FILE --source LABEL [--published-at TIME] [--revision-of ID]`, then `snapshot [--cutoff TIME]`. `record KIND INPUT.json` accepts the following keyword fields; generated IDs from earlier commands must be substituted by the caller:

| Kind | Required fields | Optional fields |
| --- | --- | --- |
| `question` | `text`, `deadline`, `resolve_after`, `resolution_rule`, `family` | `event_id` |
| `representation` | `snapshot_id`, `model`, `observer`, `method` | `parent`, `event_id` |
| `forecast` | `question_id`, `snapshot_id`, `method`, `probability`, `model` | `representation_id`, `status`, `reason`, `cost`, `event_id` |
| `resolution` | `question_id`, `outcome`, `evidence_ids`, `explanation` | `supersedes`, `event_id` |
| `assertion` | `snapshot_id`, `subject`, `predicate`, `object`, `observer`, `method`, `spans`, `basis` | `valid_from`, `valid_to`, `supersedes`, `contradicts`, `event_id` |
| `manifest` | `representation_id`, `encoding`, `schema_id`, `artifacts`, `task`, `horizon_seconds`, `units`, `evidence_ids`, `construction_cost` | `event_id` |
| `manifest-forecast` | `manifest_id`, `question_id`, `probability` | `status`, `reason`, `inference_cost`, `event_id` |

Times must include a timezone. Questions require now < deadline < resolution time. Each method gets one forecast attempt per question. Forecast model metadata must contain `identifier`; record the prompt hash, model version, input manifest, seed, and budget where relevant. A failed or abstained attempt uses `probability: null` and a reason. Costs are recorded metadata, not enforced budgets.

Representation models have `entities` and `relations` arrays. Entities need an `id`; relations need `source`, `target`, and `type`. Both need an epistemic `basis` (`observed`, `reported`, or `inferred`) and nonempty `evidence_ids` from the selected snapshot. A→B and B→A are distinct; no boundary is declared the uniquely real entity. Parent representations must preserve the observer and cannot point back from a later information cutoff.

Outcomes are integer 0 or 1 with evidence and an explanation. A correction must explicitly supersede the latest resolution. Scores retain the resolution ID used. `compare METHOD_A METHOD_B` matches the same question and snapshot and reports Brier(B)−Brier(A). It does not certify matched model budgets or statistical significance. `score` also reports pending and expired outcomes, failures, abstentions, and coverage.

`export --output NEW_FILE.json` writes metadata and event hashes; raw blobs remain in the store. `verify` checks every chain link and stored source blob, returning a nonzero status on detected corruption. No command deletes evidence.

## Source-backed assertions

`epiphysics.assertions` adds three Python functions over the existing `Ledger`:

```python
resolve_span(ledger, snapshot_id, span) -> bytes
record_assertion(
    ledger, snapshot_id, *, subject, predicate, object, observer, method,
    spans, basis, valid_from=None, valid_to=None,
    supersedes=None, contradicts=None, event_id=None,
) -> dict
assertions_as_of(ledger, known_at, valid_at=None, observer=None) -> list[dict]
```

An assertion's typed object is either `{"kind":"entity","id":"..."}` or `{"kind":"value","value":SCALAR,"unit":STRING_OR_NULL}`. Scalars must be finite JSON values. Units are preserved labels, not automatic conversions or validated physical dimensions. `basis` is `observed`, `reported`, or `inferred`; `method` identifies the extraction or recording method.

Each assertion requires 1–100 distinct spans shaped as `{"observation_id":"...","start":0,"end":12,"sha256":"..."}`. Offsets address bytes, not characters; the end is exclusive and the range must be nonempty. Resolution verifies snapshot membership and cutoff eligibility, observation/manifest hashes, the complete blob hash and size, bounds, and the selected bytes' SHA-256. Missing, altered or symlinked blobs are refused. A span hash proves preserved bytes, not that they support a true interpretation.

Corrections are new `assertion` events with `schema_version: 1` and `supersedes` naming the prior event; there is no separate revision event kind. A correction preserves its observer, cannot regress the evidence cutoff, and must extend the latest revision rather than fork it. `contradicts` retains explicit links to other assertions without deleting or choosing between them. Identical event-ID requests replay; a changed request cannot reuse that ID.

`assertions_as_of` returns visible, unsuperseded assertion events at local knowledge time `known_at`, then optionally filters by observer and a claimed world-valid interval `[valid_from, valid_to)`. Null interval endpoints are unbounded. Knowledge time cannot be in the future. Later corrections leave earlier knowledge-time queries unchanged; a retired assertion does not revive merely because its correction is outside a requested world interval. Returned objects are claims with provenance, not a resolved truth table. Full ledger/blob verification remains a separate integrity check.

The CLI accepts an assertion JSON file with the fields above (without the generated `schema_version` field), and queries the resulting history:

```sh
PYTHONPATH=engine python3 -m epiphysics --store /absolute/path/to/evidence-store record assertion assertion.json
PYTHONPATH=engine python3 -m epiphysics --store /absolute/path/to/evidence-store assertions \
  --known-at 2026-11-25T18:00:00-08:00 --valid-at 2026-11-25T00:00:00-08:00 --observer observer-id
```

Substitute real existing snapshot/observation IDs, byte offsets/digests, an observer, and eligible times. These commands use an evidence store, not the dedicated improvement-assessment store.

`epiphysics.source_span_checks.run_source_span_checks()` exercises the actual assertion API on fresh temporary synthetic ledgers. Contract `source-span-probes-v1` has 14 checks: eight for `source_span_resolution` and six for `assertion_history_preservation`. Each metric is passed checks divided by its declared count. Positive controls, rejected malformed/altered/late spans, preserved corrections/conflicts, lineage constraints and half-open world time are checked; exceptions produce failed rows with diagnostics. These are implementation conformance fractions, not extraction accuracy or source truth. The improvement report embeds the rows under `source_span_checks` and adds both metrics alongside the original 30 representation checks; the denominators stay separate.

## B1: source-bound representation manifests

`epiphysics.manifests` records manifest metadata and binds supplied forecasts to it. It never executes a retained artifact or calls a predictor:

```python
method_identity(descriptor) -> str
register_manifest(
    ledger, representation_id, *, encoding, schema_id, artifacts, task,
    horizon_seconds, units, evidence_ids, construction_cost, event_id=None,
) -> dict
forecast_manifest(
    ledger, manifest_id, question_id, probability, *, status="predicted",
    reason=None, inference_cost=None, event_id=None,
) -> dict
```

`artifacts` maps exactly four roles—`construction`, `config`, `ontology`, `predictor`—to retained observation IDs. All artifact bytes and representation evidence must belong to the representation's snapshot and pass hash/cutoff checks. `evidence_ids` must exactly match the union of evidence references in the representation model. The task is `{"id":"...","family":"...","outcome_type":"binary"}`; `horizon_seconds` is a positive integer; `units` maps field names to unit labels without conversion.

The resulting `representation_manifest` event has a stable `method_id` plus the specific representation/snapshot IDs and hashes, model hash, cutoff, artifact/evidence references and construction-cost claim. The method ID hashes encoding, schema, construction-method label, the four artifact content hashes, observer, task, horizon and units. It excludes instance IDs, snapshot times, evidence/model payload and actual cost. Recapturing identical artifacts for another snapshot therefore preserves method identity; changing an encoding or artifact changes it. This distinguishes a method from a representation instance and prevents a new instance alone from bypassing the one-method/one-question forecast rule.

Construction and inference costs use this exact shape; null or omitted inference cost becomes the unknown form:

```json
{"basis":"unknown","elapsed_seconds":null,"model_calls":null,"external_spend":null,"currency":null,"receipt_ids":[]}
```

`basis: "reported"` requires at least one quantity: nonnegative finite elapsed time/spend or a nonnegative integer model-call count. Spend requires a currency label; unknown spend requires null currency. Unknown cost retains null quantities and no receipts, rather than becoming zero. Receipt observation IDs retain hashes and must exist before the record; they may follow the evidence cutoff because they are cost documentation, not predictive evidence. Receipt bytes and reported amounts are neither independently verified expenses nor proof of execution. The forecast references construction cost by manifest and records inference cost separately, avoiding automatic duplication of the construction claim.

`forecast_manifest` rechecks manifest/artifact bindings, requires the question family and binary outcome type to match, and requires `resolve_after − snapshot cutoff == horizon_seconds`. It records the supplied probability through the existing deadline/status/duplicate-attempt safeguards, with the stable method ID, exact representation/snapshot, manifest ID/hash and predictor content hash. This is forecast binding, not model inference or a verified executable reproduction. New forecasts revalidate artifact, evidence and receipt bindings under the existing append lock. Preparation builds comparable metadata without requiring mutable blobs, so an identical retry can return the original event after blob loss. That replay does not certify current blob availability; ledger verification reports missing or corrupt content.

The CLI exposes both operations with bounded JSON objects of at most 1 MB; duplicate keys and nonfinite numbers are rejected:

```sh
PYTHONPATH=engine python3 -m epiphysics --store /absolute/path/to/evidence-store record manifest manifest.json
PYTHONPATH=engine python3 -m epiphysics --store /absolute/path/to/evidence-store record manifest-forecast forecast.json
```

Use the required/optional fields in the table above and existing ledger IDs. The generated manifest schema version and hashes are not caller-supplied fields. `epiphysics.manifest_checks.run_manifest_checks()` runs 22 actual-API checks on temporary synthetic ledgers under `representation-manifest-probes-v2`. `representation_manifest_preservation` is passed checks / 22; rows and counts appear in `report.manifest_checks`. They cover stable/distinct identity, retained inputs/cost claims, rejected late/corrupt/missing evidence, forecast binding and duplicate prevention. This B1 metric does not measure executed transformations; the separate B2a/B2b contracts below cover only fixed graph operations. Arbitrary artifact execution remains outside these slices.

## B2a: executed graph identity and projection

`epiphysics.transforms.execute_graph_transform(ledger, parent_manifest_id, recipe_observation_id, *, run_key)` executes one fixed local operation. It accepts no caller-supplied output and never evaluates retained code bytes. The parent must have B1 encoding `directed-graph` and schema `epiphysics.graph.v1`. Its model must contain explicit `entities` and `relations` arrays, with valid IDs, typed directed endpoints, epistemic basis and eligible evidence. Limits are 1 MB for the graph, 1,000 entities and 5,000 relations. Cycles, self-loops, opposite directions and different relation types between the same endpoints are allowed.

The retained recipe has exactly these fields:

```json
{
  "schema_version": 1,
  "operation": "identity",
  "config_observation_id": "CONFIG_OBSERVATION_ID",
  "implementation_observation_id": "TRANSFORM_SOURCE_OBSERVATION_ID",
  "implementation_sha256": "SHA256_OF_RETAINED_TRANSFORM_SOURCE",
  "dependency_observations": {
    "epiphysics.store": "STORE_SOURCE_OBSERVATION_ID",
    "epiphysics.assertions": "ASSERTION_SOURCE_OBSERVATION_ID",
    "epiphysics.manifests": "MANIFEST_SOURCE_OBSERVATION_ID"
  },
  "output_schema": "epiphysics.graph.v1"
}
```

These placeholders must be replaced with actual observation IDs and a lowercase SHA-256 digest. Identity configuration is `{}`. Projection uses `operation: "project_entities"` with configuration `{"entity_ids":["existing-id"]}`; IDs must be unique and present in the parent, and an empty selection is allowed. Recipe, configuration, implementation and dependency observations must all belong to the parent snapshot. Retained implementation/dependency bytes must match the actual loaded fixed implementation; captures made after the cutoff cannot be backdated by a publication claim. Capture required artifacts before freezing the snapshot. Missing artifacts require a new eligible snapshot and parent, not a retrofit of old evidence.

Identity copies the complete graph. Projection keeps selected entity records and edges whose two endpoints remain, preserving retained payload fields and parent array order. Other graph metadata is copied unchanged; this is not semantic reconciliation of metadata references. Unit labels and entity IDs are not converted or merged. The generated result contains:

- `output_model`, `output_model_hash`, and `canonical_exact` (canonical JSON equality with the parent, not semantic equivalence).
- `losses.removed_entities` and `removed_relations` with full removed records; `removed_evidence_ids` is the reference set absent from the entire output.
- `source_to_output.entities`, mapping every parent ID to itself or null; relation mappings use directed typed `source_key`/`output_key` triples, or null for removal.
- A stable `recipe_id` from operation, exact configuration/implementation/dependency content hashes and output schema. Parent instance IDs and observation IDs remain separately bound in request/input records.

The operation appends `graph_transform_started`, then one `graph_transform_completed` or `graph_transform_rejected` event. Completion embeds the generated output and losses together; it does not create a new representation, manifest or forecast. Before completion, the implementation rechecks inputs and recomputes the result under the ledger write lock. The terminal record is capped at 10 MB, and each retained recipe/code/configuration artifact at 1 MB. Model calls and external spend are zero.

An addressable invalid recipe/input produces a retained rejection with bounded diagnostics. Missing IDs, malformed invocation or incompatible runtime state can refuse before a claim; not every error produces a terminal record. An identical completed or rejected request replays its historical terminal event without rerunning, including after blob loss; this does not certify current blob integrity. Changed requests cannot reuse a run key. An unfinished start requires diagnosis, and concurrent identical keys cannot claim twice.

```sh
PYTHONPATH=engine python3 -m epiphysics --store /absolute/path/to/evidence-store graph-transform transform.json
```

The bounded input JSON contains only `parent_manifest_id`, `recipe_observation_id` and `run_key`. Run keys use 1–100 letters, digits, dots, underscores or hyphens. Completed results/replays exit 0; recorded rejections print their event and exit 2. Use an evidence store, not the dedicated improvement store.

`epiphysics.transformation_checks.run_transformation_checks()` runs `graph-transformation-probes-v2`: `transformation_preservation` is passed checks / 26. Rows, counts and diagnostics appear in `report.transformation_checks`. These checks execute the fixed API on fresh synthetic ledgers and include loss/mapping checks, immutable inputs, receipts, replay, rejected late/tampered inputs concurrent/interrupted claims, completion-boundary input changes and UTF-8-safe malformed-input rejection. The implementation trusts the local Python process, ledger and filesystem; it is not a security sandbox. It does not measure split/merge, arbitrary encodings, semantic/causal equivalence, model inference or independent execution attestation. B2b remains the separate split/merge capability.

## B2b: executed graph partition and strict merge

`epiphysics.graph_views.execute_graph_views(ledger, parent_manifest_ids, recipe_observation_id, *, run_key)` executes fixed record operations. Parent IDs are a distinct, nonempty list of at most 16, with each ID limited to 512 UTF-8 bytes; ordering is normalized and duplicates are refused. Oversized IDs refuse before any parent lookup or run claim, without appending events. All parents use `directed-graph` / `epiphysics.graph.v1`. This API accepts no output payload, executes no arbitrary artifact bytes, and does not divide physical entities or redistribute quantities.

The recipe uses the same seven fields as B2a, with `operation` set to `partition_entities` or `merge_graphs`, implementation bytes for `graph_views.py`, and exactly four dependency observation keys: `epiphysics.store`, `epiphysics.assertions`, `epiphysics.manifests`, `epiphysics.transforms`. Recipe, configuration and all loaded-code bindings must already be eligible in the common parent snapshot. Stable recipe identity hashes the operation, exact configuration/code/dependency bytes and output schema; parent instance IDs remain separate request bindings.

- **Partition:** exactly one parent; configuration `{"views":{"left":["entity-a"],"right":["entity-b"]}}`. The 1–64 named groups must be nonempty, disjoint and cover every parent entity exactly. Each view name is limited to 128 UTF-8 bytes. Oversized names retain started/rejected records and are refused before output or mapping computation. Each output preserves records and array order within its induced view. Cross-partition relations are removed and recorded in full; cycles wholly within a view remain, while cross-view cycles may break through those explicitly removed edges. Root metadata is copied without interpreting its meaning.
- **Merge:** 2–16 distinct parents; configuration `{"conflicts":"reject"}`. Parents must match exact snapshot ID/hash, encoding/schema, observer, task/horizon, units, ontology/predictor content hashes and canonical root metadata. Colliding entity IDs or directed typed edge keys require identical complete records, including attributes, basis and evidence. Conflicting relation IDs are also refused. Identical records are deduplicated with ancestry retained; quantities, units and evidence are not silently reconciled. Output entities and edges are sorted deterministically, independently of caller parent order.

Completion embeds `outputs`, a map from view name to `{model, model_hash}`; merge uses the name `merged`. `losses.removed_relations` contains parent-tagged cross-edge records, and `removed_evidence_ids` is the input/output reference-set difference. `removed_entities` is empty for accepted exhaustive partitions and strict unions. `source_to_output` retains each parent's entity, relation and metadata destinations; `deduplications` retains the parent IDs behind identical merged entities/relations. These structures describe graph records, not semantic identity or a conserved physical state.

The API appends `graph_views_started` followed by one `graph_views_completed` or `graph_views_rejected` event. It recomputes the operation and revalidates mutable bytes under the completion write lock. An addressable invalid request retains a rejection; unaddressable inputs can refuse before claiming. Exact terminal replay returns the historical result, including after blob loss, without certifying current integrity. Changed requests cannot reuse a key, concurrent claims cannot duplicate it, and an unfinished start requires diagnosis. Input parents stay unchanged.

Inherited per-graph limits are 1 MB, 1,000 entities and 5,000 relations. Combined input models and combined output models are each capped at 2 MB; terminal records at 10 MB. Program model calls and external spend remain zero. The implementation trusts the local process, ledger and filesystem; retained metadata and these local records are not an external execution witness.

```sh
PYTHONPATH=engine python3 -m epiphysics --store /absolute/path/to/evidence-store graph-views views.json
```

The bounded JSON object contains `parent_manifest_ids`, `recipe_observation_id` and `run_key`. Completion/replay exits 0; recorded rejection prints the event and exits 2. Use an evidence store, not the improvement-assessment store.

`epiphysics.graph_view_checks.run_graph_view_checks()` executes `graph-view-probes-v1`. The metric `split_merge_preservation` is passed checks / 45, limited to graph partition/merge. Rows, counts and diagnostics appear in `report.graph_view_checks`; its identifier-bound cases exercise multibyte UTF-8 names and IDs, including their different refusal paths. It does not measure semantic entity fission, arbitrary encodings, predictive benefit or output materialization. B2b itself embeds outputs; the separate B2c consumer below creates their representations and manifests.

## B2c: atomic graph output materialization

`epiphysics.materialization.materialize_graph_outputs(ledger, completion_id, *, run_key)` consumes a completed B2a/B2b execution and creates its entire output set as representations and B1 manifests. B2a uses the output name `output`; B2b retains its named views. The caller supplies no graph or probability. `get_materialized_outputs(ledger, terminal_id, *, verify_bytes=True)` returns the checked receipt, representations and manifests for a completed bundle.

An exclusive start precedes a single owned `Ledger.atomic_write()` transaction. All output representations, manifests and the completion receipt commit together. Validation failure rolls them all back before a rejection is appended; interrupted starts require diagnosis. Existing orphan output IDs are refused instead of adopted. Output IDs derive from the run key and a hash of the view name. Exact terminal retries return the original receipt; historical lookup with byte checks disabled does not certify current blob availability.

The transaction covers SQLite events, not content-addressed blob files. Groups accept derived records over already-retained evidence. New observations, questions and forecasts are forbidden, including through generic append; capture refuses before writing a blob. Forecast consumers run after commit under their normal live deadline checks. Snapshots inside a group use its fixed cutoff. Other connections see no partial bundle. Nested groups, unowned transactions and reentrant appends are refused; append failures poison the group even if a caller catches the error. All bundle events use one local transaction timestamp, which is not an externally witnessed completion time.

Generated model hashes stay unchanged. Derived method identity includes the execution recipe, output view and sorted parent method identities, preserving parent multiplicity while excluding instance IDs. The receipt binds every parent instance and hash, derivation descriptor and loss/mapping references. A single-parent output uses the existing representation parent field; a merged output uses `parent: null` because that field cannot express multiple parents. The bundle receipt carries the complete merge ancestry.

New manifests inherit observer, snapshot, encoding/schema, task/horizon, units, ontology and predictor from compatible parents. Construction/configuration artifacts come from the eligible execution recipe. Construction cost remains explicitly unknown. The resulting manifests can enter existing consumers; materialization itself generates no forecasts and proves no predictive advantage.

Version one accepts new materialization only when the recorded execution implementation and dependency hashes match the currently verified fixed operations. A changed dependency requires a fresh execution with newly eligible source bytes and snapshot. Old completions are not silently relabeled as current execution. Previously materialized bundles retain historical lookup/replay; lookup does not re-execute an old recipe. No arbitrary retained program is evaluated.

Bounds are checked before expansion or output writes: parent method descriptors are at most 16,384 bytes and the conservative combined output-record estimate is at most 8 MB. Existing graph limits, 128-byte view names, 512-byte involved IDs and 10 MB input/terminal records also apply. Malformed completion containers retain a durable rejection rather than an unfinished claim. `materialization-probes-v1` exercises thirty actual consumer and atomicity checks, including targeted controls that remove one guard while retaining ordinary successful behavior.

The CLI accepts one bounded strict-JSON object containing `completion_id` and `run_key`:

```bash
PYTHONPATH=engine python3 -m epiphysics --store ./local-study materialize-graphs request.json
```

A committed completion or exact replay exits 0; recorded rejection exits 2. API checks, their measured denominator and selector integration are documented in the [metric contracts](../docs/experiments/representation-metrics.md).

## C1: frozen lexical retrieval baseline

The lexical baseline freezes explicitly selected observations from one source snapshot before building a fresh in-memory SQLite FTS5 index. Future or unselected sources do not enter either matches or corpus statistics. Passages preserve exact UTF-8 byte ranges, including raw markup. The default is 2,048-byte windows with 256-byte nominal overlap, `unicode61 remove_diacritics 2`, literal OR query terms and five results. BM25 sorts ascending; source ID, offsets and span hash break ties deterministically. A lexical match does not establish answerability.

The public interfaces are `freeze_retrieval_corpus`, `run_lexical_retrieval` and `get_retrieval_run` in `epiphysics.retrieval`. `epiphysics.retrieval_evaluation.project_queries` strips evaluator-only fields; `evaluate_retrieval` checks a completed run against a separate development cohort and returns a report without writing events. The pure candidate receives passages, query IDs/text and config, never gold spans, expected answers or source labels.

```bash
PYTHONPATH=engine python3 -m epiphysics --store ./local-study freeze-retrieval freeze.json
PYTHONPATH=engine python3 -m epiphysics --store ./local-study run-retrieval run.json
PYTHONPATH=engine python3 -m epiphysics --store ./local-study evaluate-retrieval evaluation.json --output new-report.json
```

All request files are strict bounded JSON objects. Freeze input contains `snapshot_id`, `observation_ids`, optional `config` and optional `event_id`. Run input contains `corpus_id`, `queries` (each with `query_id` and `query`) and `run_key`. Evaluation input contains `cohort` and `run_terminal_id`. A recorded run rejection exits 2; completed runs/replays exit 0. Evaluation output files are exclusive new exports and are never silently replaced. Retain the report, cohort and evaluator artifacts separately when recording an experiment.

The [development inputs](examples/retrieval/README.md) refer to an existing four-source local archive; they are not a replacement for its source bytes. Two fresh run keys and indexes are required to test reproduction. An exact historical replay returns its earlier receipt and does not run another search. Record code/dependency, runtime, source, corpus, passage, config, query, cohort and result identities; runtime changes can affect tokenization and scores.

Source eligibility is distinct from experiment timing. Newly built retrieval code and curated questions may run against an earlier source snapshot as a retrospective development experiment. Their later execution artifacts must never be indexed or backdated into the source corpus. This is not a forecast by a predictor proven to exist at that earlier cutoff.

C1 provides a standalone baseline and evaluator. C2 adds an optional `--retrieval-study FILE` to improvement `assess` and `dispatch`, with a declared contract under policy `retrieval_study`. It validates and rescores actual retained executions before the queued `build_retrieval_baseline` action can close. See [the study examples](examples/retrieval/README.md) and [C2 run record](../docs/planning/runs/2026-11-25-retrieval-controller.md). A synthetic capability fraction is not a measured retrieval-quality result. The [metric contracts](../docs/experiments/representation-metrics.md) define full-span coverage, source recall, reciprocal rank, unsupported-query retrieval, empty results and their denominators.

The optional `indexing_recipe` in a `run-retrieval` request is exactly `raw-window-text-v1` (default) or `static-html-text-nodes-v1`. New executions emit schema 2; the getter and exact replay preserve historical schema-1 records. HTML extraction changes indexed text only. Ranked hits continue to name raw source spans; bounded projection artifacts retain every copy/entity/separator mapping, including empty windows. The neutral validator and evaluator do not import the candidate or runner. See the [fixed comparison protocol](../docs/experiments/retrieval-html-comparison.md) for parser rules, limits, bridge and interpretation.

C4 adds cohort schema 2 for alternative sufficient support bundles and jointly required spans. Its `retrieval-coverage-evaluation-v2` scorer measures whether an entire bundle is covered, with matched supported/unsupported pairs and explicit unmeasured entity families. The separate preparation helper validates and freezes the original cohort/protocol/review bytes against a historical raw candidate without executing search. Study schema 3 uses the existing controller transport with explicit `preparation` and `evaluation` phases: readiness contains no quality, selects two intended raw runs, then their validated evaluation selects a bounded evidence diagnosis. See the [coverage protocol](../docs/experiments/retrieval-coverage.md) and [input/worker examples](examples/retrieval/README.md). These new metrics are not comparable to old gold-span aggregates across changed cohorts and contracts.

## Assurance limits

Append-only triggers and hashes protect against accidental edits through this interface. An operator controlling the database, code, or clock can rewrite the entire history. Without an independently witnessed checkpoint, truncation and wholesale rewriting are not externally detectable. A blockchain anchor would establish prior existence of committed bytes under its assumptions; it would not establish truth, completeness, collection time, or a model's actual information access.

Snapshot selection uses collection time, never a source's publication claim. A model's training data, hidden memory, undeclared tools, or manual reasoning can still leak later information. Process isolation, model-access manifests, signed witness adapters, immutable public bundles, prospective holdouts, and independent resolution are next implementation gates. The current ledger is intended for a trusted local operator; it is not a multi-tenant service.

See `docs/planning/2026-11-24-recursive-observatory.md` for the component roadmap and `docs/experiments/prospective-observatory.md` for the evaluation protocol.

## Updating the site's collection record

The site imports `src/components/home/observatory-status.json`. This is a recorded aggregate refreshed when the daily monitor is due, through reviewed commits/deployments, not a browser connection to a private local database. The active supervisor continues ready work immediately; its 15-minute heartbeat is a recovery backstop and does not change the monitor's daily observation window. The first real collection was recorded on 25 November 2026; the example forecast remains clearly synthetic.

After collecting and verifying the dedicated README monitor, run from the checkout containing the engine:

```sh
PYTHONPATH=engine python3 -m epiphysics --store /absolute/shared-checkout/.supernal-local/observatory publish-status --source /absolute/shared-checkout/README.md --output src/components/home/observatory-status.json
```

This explicit command atomically replaces only the derived status file. It exports timestamps, counts, source link, and local assurance labels. It refuses a mixed-source store or a failed integrity check, and omits raw contents, local paths, prompts, and internal event IDs. Publish the changed artifact through the normal reviewed site workflow. A missed scheduler wake leaves an older visible capture time; it must not appear as a fresh successful run.

## Offline research knowledge catalog

The knowledge compiler validates a curated research map. It does not determine truth, run experiments, call a model, access the network, or mutate the evidence ledger.

```sh
PYTHONPATH=engine python3 -m epiphysics.knowledge --repo . --catalog research/meta-representation
PYTHONPATH=engine python3 -m epiphysics.knowledge --repo . --catalog research/meta-representation --output /tmp/research-map-new.json
```

Without `--output`, the command validates and prints a summary. With it, validation finishes before creating the artifact, and an existing output file is never replaced. Relative catalog paths are resolved from the Git repository root. Output paths are resolved from the current working directory.

A catalog directory contains `sources-*.json` arrays and `registry.json`, whose shape is `{"schema_version":1,"nodes":[],"edges":[]}`. Every node requires a globally unique `id`, `kind`, and nonempty `title`:

- `source`: requires `bibliographic_only: true`, a credential-free HTTPS `url`, `date`, `date_type`, `reviewed_on`, `claim_supported`, and `limitation`. Bibliographic dates accept `YYYY`, `YYYY-MM`, or `YYYY-MM-DD`. A null date is allowed only with `date_type: "undated_live_documentation"` or `"mutable_main_revision_unverified"`; `reviewed_on` always requires a real `YYYY-MM-DD`. These are bibliographic metadata, **not archived external source bytes**.
- `document`: requires an explicit repository-relative `repo_path`. The compiler freezes Git HEAD once and embeds exact UTF-8 text from that committed regular file, its `content_sha256`, and `commit`. It does not read the document's working-tree version. Untracked paths, committed symlinks, and traversal are rejected. Those three generated fields cannot be supplied in the input.
- `claim`: requires a `statement`, `basis` (`reported`, `inferred`, or `observed`), and `status` (`definition`, `hypothesis`, `reported_result`, `implementation_finding`, or `contested`). Probability and confidence fields are not accepted.
- `representation`, `transformation`, and `experiment`: require `status: "proposed"` for this initial catalog. A proposed experiment is not a completed or validated result.

Edges require `source`, `target`, and `type`. The allowed endpoint kinds are `cites` (claim → source/document), `challenges` (claim → claim), `motivates` (claim → representation/transformation/experiment), `compares` (experiment → representation), `transforms` (transformation → representation), `depends_on` (any → any), and `implements` (document → representation/transformation). Endpoints must exist. Duplicate triples are rejected; opposite directions and different edge types between the same nodes remain distinct. Contradictory claims are retained rather than resolved automatically.

Catalog JSON is read locally and may be uncommitted; embedded documents always come from the pinned commit. Limits are 5,000 nodes, 100 catalog files plus document entries, 1 MB per document, and 10 MB for catalog inputs plus embedded document bytes. The canonical compiled payload also cannot exceed 10 MB. Sources outside the explicitly named catalog files and documents are not scanned.

The artifact includes UTC `generated_at`, counts, assurance labels, and `graph_payload_hash`: SHA-256 of canonical JSON containing `schema_version`, `commit`, sorted `nodes`, and sorted `edges`. Generation time is excluded from that hash, so identical inputs at the same commit replay identically. Compilation time and Git history make **no historical cutoff-eligibility or independent-timestamp claim**. Validate this compiler with `PYTHONPATH=engine python3 -m unittest discover -s engine/tests -p 'test_knowledge.py' -v`.

## Representation conformance controls

`epiphysics.representation_checks` evaluates explicit query contracts with four Python functions: `validate_suite(suite)`, `reference_candidate(suite)`, `degraded_candidate(suite)`, and `evaluate(suite, candidate)`. It uses the standard library and makes no network or model calls. Different representation adapters may return answers to the same queries without sharing an internal ontology.

`engine/examples/improvement/entities.json` contains 30 fictional checks across seven families: software services, organizations, person roles, contract obligations, physical assets, collectives, and representations. Its nine dimensions are identity, relation direction, relation type, time, units, contradiction, hierarchy, boundary, and workflow. The cases include homonyms, directed and parallel relations, disputed records, changing membership, currency and units, invoice retries, and approval authority. These are synthetic contracts, not extracted source assertions or empirical results.

The suite has `schema_version: 1` and `cases`. Each case has `id`, `family`, `description`, `cutoff`, `observations: [{id, recorded_at}]`, and `checks: [{id, dimension, expected, evidence_ids}]`. A candidate has `schema_version: 1` and `cases: [{id, answers: [{check_id, value, evidence_ids}]}]`. Cases, checks per case, and observations per case are each limited to 100. The journal's file loader additionally limits each input to 1 MB.

Correctness requires canonical JSON equality and the exact reference evidence set; object-key and evidence order do not matter, while array order and numeric types do. Booleans cannot stand in for numbers. Every reference check must cite nonempty evidence recorded at or before its cutoff. Missing answers remain in the denominator. Wrong values and incomplete evidence receive failed scores; known evidence after the cutoff also records a temporal violation. Malformed schemas, nonfinite values, duplicate or unknown identifiers, and invalid timestamps raise `ValueError`.

The report contains per-check diagnostics, per-case counts, overall accuracy/coverage/provenance counts and ratios, per-dimension summaries, and per-family accuracy. Macro accuracy weights families equally; worst-family accuracy makes a weak family visible. Accuracy requires value and provenance correctness. Coverage counts all supplied answers, including wrong ones. Temporal violations count checks citing at least one late observation.

The `reference` control deliberately copies every expected answer: its 30/30 score is an oracle conformance check, **not a prediction, learned model, or evidence of scientific or business value**. The `degraded` control loses evidence, relation direction, and unit qualifiers. With the current fixture it scores 18/30, retains 30/30 answer coverage and 23/30 provenance, and has worst-family accuracy 0.5. These two controls test whether the evaluator detects its declared failures; neither learns from the fixture.

## Improvement assessment journal

`epiphysics.improvement` records assessments in a dedicated local ledger. Keep this store separate from the observatory monitor and other workflows. These commands evaluate the controls directly and record the completion-to-next-step decision:

```sh
PYTHONPATH=engine python3 -m epiphysics.improvement --store engine/.data/improvement assess \
  --policy engine/examples/improvement/policy.json \
  --suite engine/examples/improvement/entities.json --candidate degraded \
  --run-key control-negative --after-step initial \
  --completed-work "Evaluated the synthetic lossy control"
PYTHONPATH=engine python3 -m epiphysics.improvement --store engine/.data/improvement status
PYTHONPATH=engine python3 -m epiphysics.improvement --store engine/.data/improvement assess \
  --policy engine/examples/improvement/policy.json \
  --suite engine/examples/improvement/entities.json --candidate reference \
  --run-key control-positive --after-step control-negative:next \
  --completed-work "Evaluated the copied-answer oracle control"
```

`--candidate` also accepts a local JSON answer file. The Python entry points are `assess(ledger, policy_path, suite_path, candidate, run_key, after_step="initial", completed_work="...")` with the last two arguments keyword-only, and `status(ledger)`. A completed-work description records the operator's claim; an assessment is not proof that a queued implementation task was performed. Switching from the degraded control to the oracle is not a demonstrated improvement in a learned system.

Assessment records preserve input bytes, evaluator, assertion/manifest/transform/graph-view/materialization implementations, all capability probes, store and controller bytes, their hashes, metrics, actual elapsed time, and the previous decision's subsequently observed metric. A single completion event contains both the result and its queued successor. Exclusive predecessor claims prevent two assessments from consuming the same step. Identical completed requests replay without new events; changed inputs cannot reuse a run key. Failures caught after an assessment claim retain any captured inputs and queue diagnosis. Invalid JSON or policy can be refused before claiming a step: no ledger transition is created and the queue is unchanged. When invoked through `dispatch`, that child refusal appears in its process receipts/output. Interrupted claims require inspection rather than blind replay.

Elapsed time and zero program model calls/external spend describe the assessment only. They do not include builder/reviewer effort or establish a measured total cost for the improvement step.

Each implementation module retains its source bytes and executing code object when imported. The controller pins those identities, checks the retained internal dependency bindings, and compares the loaded code with a fresh compilation of the retained source, without executing it. Assessments refuse module reloads, mismatched cached bytecode, and on-disk source drift before claiming work and before recording a passing completion. Use a fresh process after reviewed changes; discard a stale bytecode cache when the diagnostic identifies one. These checks detect accidental identity changes, not deliberate tampering by an operator who controls the process.

The action selector is a transparent priority rule: repair temporal eligibility, evidence mapping, missing coverage, or the weakest family, then failing assertion, manifest, fixed-transform, graph-view or materialization probes. Those failures select `repair_source_span_assertions`, `repair_representation_manifests`, `repair_graph_transformations`, `repair_graph_views` or `repair_transform_materialization`. Only passing all preceding gates plus B2c advances to `build_retrieval_baseline` (Packet C). Without a validated actual study, `retrieval_baseline_reproducibility` remains unmeasured. A supplied retained pair or fixed four-run comparison is validated separately; successful comparison advances to fresh coverage regardless of its quality direction. Success probabilities and whole-step costs remain unestimated.

Previous targets are compared descriptively only when all fourteen measurement-contract hashes match: `suite`, `evaluator`, `policy`, `assertions`, `source_span_probe`, `store`, `manifests`, `manifest_probe`, `transforms`, `transformation_probe`, `graph_views`, `graph_view_probe`, `materialization`, and `materialization_probe`. Changed contracts, including a transition from a run without the newly required module hashes, produce `prior_action_outcome.status: incomparable_contract_change`, with changed input names and no delta or `target_met`. Candidate or controller changes alone do not prohibit comparison. A missing prior measurement is `unmeasured`. Comparable changes still have no causal attribution. A perfect fixture result cannot authorize deployment, increased scale, paid calls, or promote an unmeasured capability.

The supplied policy `offline-contracts-materialization-v6` permits only the offline fixture stage, requires all seven families, sets external spend to zero, and disables scale changes. Its assessment duration is an elapsed-time acceptance check, not process isolation. The atomic queue records what should happen next; **writing a queued step does not execute it**. An invoked worker or supervisor must perform the work and then record what actually happened.

The supervisor checks progress every 30 minutes or three core steps, then continues ready authorized work while its session is active. These checkpoints are review boundaries, not session stop rules. The 15-minute heartbeat checks for an existing active job before dispatching; it must not duplicate that work. Worker time/output limits and zero external spend remain unchanged. Neither schedule configuration nor a durable queue promises an always-online agent.

## Dispatching a real assessment worker

`dispatch` starts a separate Python process that executes the assessment program and waits for its result. Use a fresh dedicated store for this example:

```sh
PYTHONPATH=engine python3 -m epiphysics.improvement --store engine/.data/improvement-worker dispatch \
  --policy engine/examples/improvement/policy.json \
  --suite engine/examples/improvement/entities.json --candidate reference \
  --run-key worker-control --after-step initial --timeout-seconds 30 \
  --completed-work "Ran the synthetic oracle through the assessment worker"
PYTHONPATH=engine python3 -m epiphysics.improvement --store engine/.data/improvement-worker status
```

The Python entry point is `dispatch(store, policy_path, suite_path, candidate, run_key, *, after_step="initial", completed_work="...", timeout_seconds=60)`. The program is fixed to the current Python interpreter running `epiphysics.improvement assess`; callers cannot supply a shell command or choose another executable. The child uses the engine directory, a fixed Python import path, a minimal environment, and no standard input. It makes no network or model calls and records zero external spend.

The timeout must be positive and at most 60 seconds. Combined standard output and error are limited to 1 MB. On a timeout or output-limit failure, the dispatcher kills and reaps its assessment child. It may queue diagnosis only for that child's matching dispatch-ID/PID unfinished claim after reaping; completed transitions and unrelated claims are preserved. A launched child has local receipts under `STORE/dispatches/UUID/`: `start.json`, `output.log`, and `finish.json`. These record the command, PID, timing, return code, output hash, and recovery result. Dispatcher argument/store refusal can occur before a child or receipts exist. The timeout requires the dispatcher to remain alive; a start receipt without a finish receipt requires process investigation. Receipts are local records, not independently witnessed attestations.

Dispatch returns `result`, `dispatch` (the receipt), `assessment` (the delivered assessment or null), and a bounded `authoritative_transition` when verified. That transition contains the event ID/hash, kind, run key, result and minimal successor fields. A successful fresh invocation leaves one completed assessment, no unfinished runs, and the queued step `worker-control:next`.

If output delivery fails after durable completion, the result is `assessment_completed_delivery_failed`, the receipt's `delivery_status` is `failed`, and `authoritative_transition_id` identifies the preserved completion. The CLI exits nonzero even though the assessment completed. Read the authoritative transition and current `status`, then consume the queued successor within scope; **do not rerun completed work because output exceeded the cap**. If no authoritative transition is confirmed, inspect the receipts and ledger rather than assuming completion or failure. `status` verifies state but does not launch work. The desktop supervisor assigns implementation to a scoped builder; the assessment worker cannot implement the queued capability by itself.

This is bounded process supervision for a trusted checkout, **not a security sandbox** or isolation from a hostile local operator. The fixed program and current policy provide zero external spend; they do not establish a general network or filesystem security boundary. A completion-triggered supervisor can continue from recorded metrics, but the heuristic queue does not become a calibrated prediction or permission to increase scale.
