# Frozen retrieval development inputs

These are owned questions and source references for the four-source local capture documented in [the B2b run](../../../docs/planning/runs/2026-11-25-graph-views.md). They do not contain the third-party article bytes. The matching evidence store must already retain the named snapshot and exact observations; fetching a changed live page is not reproduction of this corpus.

- `control-freeze.json` selects the four eligible observations and a stable corpus event ID.
- `control-queries.json` contains only candidate-visible query IDs and text. Add `corpus_id` and a fresh `run_key` to form a run request.
- `control-development.json` is evaluator input: eight supported questions, four corpus-unsupported questions, exact gold spans and limitations. Never pass this file to the candidate.

A curator prepared the cohort from retained bytes. A separate reviewer verified all twelve gold spans, supporting context for every positive question, and lack of the requested facts in the four-source corpus for the unsupported questions. Before any baseline run, “standard models” in the first question was clarified to “standard generally available models”; preview policy differs. No gold span changed. Questions and scoring rules are frozen before observing retrieval results.

The corpus is small and builder-visible. Unsupported means the requested fact is absent from these sources, not universally false. Gold spans are not an exhaustive inventory of every alternative supporting passage. The baseline returns passages, so an unsupported question receiving lexical matches is not itself a hallucinated answer.

The source snapshot is dated by the local collector. Later code, configuration and query artifacts describe the retrospective experiment; they are not evidence that the algorithm or questions existed at the earlier cutoff. No external timestamp proof is present.

`engine/tests/test_retrieval.py`, `test_retrieval_evaluation.py` and `test_retrieval_cli.py` use owned synthetic bytes to verify behavior without requiring the local development archive. Their results are conformance checks, not this corpus's retrieval quality. The [measurement contract](../../../docs/experiments/representation-metrics.md) defines the separate real development metrics and reproduction gate.

## Supply the measured baseline to the controller

`control-improvement-policy.json` declares the exact C1 source snapshot, corpus, cohort, queries, gold, historical implementation/dependencies, runtime and two execution hashes. Its `retrieval_study` field binds the intended study; it is not a supplied score. The rest of the policy preserves the seven entity families, 30-second assessment limit, zero external spend and disabled scale changes.

Copy `control-study.json` to a private local file and replace its two placeholder absolute paths with the retained evidence store and this checkout's `control-development.json`. Paths can move; the declared content identities cannot. Do not point the evidence path at the dedicated improvement store or fetch current web pages to replace missing archived bytes.

Pass the resolved request with `--retrieval-study /absolute/path/to/study.json` on the existing improvement `assess` or `dispatch` command, using `control-improvement-policy.json` as its policy. Read the improvement status first and use its current predecessor and a fresh run key. Retained C1 events are validated and rescored; this does not launch a third search or change C1's questions. The controller records actual retrieval separately from its synthetic checks and preserves the original evidence store.

Both example files contain owned identifiers and hashes only. Source bytes, expanded local paths, captured bundles and process receipts belong in the private local archive. The [C2 run record](../../../docs/planning/runs/2026-11-25-retrieval-controller.md) records validation status and the real handoff separately from the examples.

## Compare the two fixed indexing representations

The same `--retrieval-study` handoff accepts a schema-2 study containing exactly two raw-window runs and two static HTML text-node runs. It validates and scores retained executions; supplying a study does not start searches. Execute the four runs in raw A, raw B, HTML A, HTML B order, completing each before starting the next. Every run uses the same corpus, ordered queries, search configuration, runner, indexing implementation, runtime, decoder and parser dependencies. Only the fixed recipe changes. Keep the existing development questions and gold untouched.

The request has `schema_version: 2`, `study_id`, `evidence_store`, `cohort_file`, `protocol_file`, `corpus_id` and `arms`. All three paths are absolute locators. `arms` has exactly `raw` and `html`, each containing `indexing_recipe` and two `run_terminal_ids`. The recipes are `raw-window-text-v1` and `static-html-text-nodes-v1`, respectively. The private study file supplies recorded terminal IDs, not result summaries.

The policy's schema-2 `retrieval_study` declaration binds the common snapshot ID/hash/manifest hash, corpus ID/hash, cohort/gold/query hashes, source/passages/config hashes and exact `protocol_hash`. Each declared arm contains its fixed `indexing_recipe`, `candidate_algorithm_hash`, and two maps keyed by its terminal IDs: `projection_hashes` and `run_terminal_hashes`. Candidate and output hashes come from verified receipts after execution; they are observed bindings, not evidence of preregistration. Retain the exact [comparison protocol](html-comparison-protocol.json) before execution separately from those post-run bindings. The adapter preserves protocol bytes and identity without interpreting arbitrary policy text as executable instructions.

Raw sources and citations remain unchanged: search results identify complete original byte windows. HTML projection supplies indexed text plus a checked mapping back to source bytes; a retrieved window covering a gold span does not establish that every gold byte survived projection. No answer generation or external model call is added. Numeric BM25 scores are not calibrated confidence and should not be compared across arms as confidence.

The neutral validation and scoring identity is separate from candidate identity. It includes the source/corpus, queries, gold, scoring code and shared decoder; it excludes the runner, indexing implementation and protocol description. Reports identify execution and candidate dependencies separately. A current rescore of a legacy receipt preserves its original execution fields; it does not replace the measurement identity recorded by the original historical assessment.

Both repeats in each arm must agree on projection, ordered results and evaluation. A valid disagreement reports reproduction zero, retains all four reports, omits quality deltas and queues repair. Once both arms reproduce under the common measurement, the controller queues fresh-question coverage evaluation for a gain, tie or regression. It retains the raw operational baseline and does not authorize adoption or another tuning cycle on visible gold. Earlier integrity and conformance failures retain priority.

The adapter captures one coherent evidence prefix into the separate improvement store without modifying the source store. It enforces at most 256 events, 128 artifacts, 4 MB per artifact, 16 MB per bundle and 1 MB per request/cohort/protocol. Replay uses captured bytes even if the original paths disappear. Reports include receipt-reported resources for all four executions; those inner times exclude locked revalidation and commit. Outer caller time and builder/reviewer cost remain separate, and whole-step cost is unmeasured. Production assessment and dispatch budgets remain 30 and 60 seconds.

The comparison protocol is retained as opaque hash-bound bytes, not executed or interpreted by the adapter. The supervisor must separately bind static input identities to its pre-run freeze and enforce any historical migration bridge before candidate execution. A valid four-receipt report proves the adapter's fixed input/order/reproduction checks; it does not independently prove preregistration timing or execution provenance.
