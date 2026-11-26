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

Use the required/optional fields in the table above and existing ledger IDs. The generated manifest schema version and hashes are not caller-supplied fields. `epiphysics.manifest_checks.run_manifest_checks()` runs 22 actual-API checks on temporary synthetic ledgers under `representation-manifest-probes-v2`. `representation_manifest_preservation` is passed checks / 22; rows and counts appear in `report.manifest_checks`. They cover stable/distinct identity, retained inputs/cost claims, rejected late/corrupt/missing evidence, forecast binding and duplicate prevention. B2 transformations, declared loss and split/merge preservation remain separate work. Verified artifact execution and its receipts are also outside B1; this metric does not measure them.

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

Assessment records preserve input bytes, evaluator, assertion/manifest implementations, both capability probes, store and controller bytes, their hashes, metrics, actual elapsed time, and the previous decision's subsequently observed metric. A single completion event contains both the result and its queued successor. Exclusive predecessor claims prevent two assessments from consuming the same step. Identical completed requests replay without new events; changed inputs cannot reuse a run key. Failures caught after an assessment claim retain any captured inputs and queue diagnosis. Invalid JSON or policy can be refused before claiming a step: no ledger transition is created and the queue is unchanged. When invoked through `dispatch`, that child refusal appears in its process receipts/output. Interrupted claims require inspection rather than blind replay.

Each implementation module retains its source bytes and executing code object when imported. The controller pins those identities, checks the retained internal dependency bindings, and compares the loaded code with a fresh compilation of the retained source, without executing it. Assessments refuse module reloads, mismatched cached bytecode, and on-disk source drift before claiming work and before recording a passing completion. Use a fresh process after reviewed changes; discard a stale bytecode cache when the diagnostic identifies one. These checks detect accidental identity changes, not deliberate tampering by an operator who controls the process.

The action selector is a transparent priority rule: repair temporal eligibility, evidence mapping, missing coverage, or the weakest family, then failing assertion or manifest probes. Assertion failures select `repair_source_span_assertions`; manifest failures select `repair_representation_manifests`. Only passing the 30 representation checks, both assertion metrics and `representation_manifest_preservation` advances to `build_representation_transformations` (Packet B2). `transformation_preservation` remains unmeasured; a B2 queue entry does not certify transformations or complete all of Packet B. Success probabilities and costs remain unestimated.

Previous targets are compared descriptively only when all eight measurement-contract hashes match: `suite`, `evaluator`, `policy`, `assertions`, `source_span_probe`, `store`, `manifests`, and `manifest_probe`. Changed contracts, including a transition from a run without the newly required module hashes, produce `prior_action_outcome.status: incomparable_contract_change`, with changed input names and no delta or `target_met`. Candidate or controller changes alone do not prohibit comparison. A missing prior measurement is `unmeasured`. Comparable changes still have no causal attribution. A perfect fixture result cannot authorize deployment, increased scale, paid calls, or promote an unmeasured capability.

The supplied policy `offline-contracts-manifests-v3` permits only the offline fixture stage, requires all seven families, sets external spend to zero, and disables scale changes. Its assessment duration is an elapsed-time acceptance check, not process isolation. The atomic queue records what should happen next; **writing a queued step does not execute it**. An invoked worker or supervisor must perform the work and then record what actually happened.

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

If output delivery fails after durable completion, the result is `assessment_completed_delivery_failed`, the receipt's `delivery_status` is `failed`, and `authoritative_transition_id` identifies the preserved completion. The CLI exits nonzero even though the assessment completed. Read the authoritative transition and current `status`, then consume the queued successor within scope; **do not rerun completed work because output exceeded the cap**. If no authoritative transition is confirmed, inspect the receipts and ledger rather than assuming completion or failure. `status` verifies state but does not launch work. The desktop supervisor assigns implementation to a scoped builder; this worker cannot implement the recommended source-span stage by itself.

This is bounded process supervision for a trusted checkout, **not a security sandbox** or isolation from a hostile local operator. The fixed program and current policy provide zero external spend; they do not establish a general network or filesystem security boundary. A completion-triggered supervisor can continue from recorded metrics, but the heuristic queue does not become a calibrated prediction or permission to increase scale.
