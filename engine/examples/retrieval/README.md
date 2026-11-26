# Frozen retrieval development inputs

These are owned questions and source references for the four-source local capture documented in [the B2b run](../../../docs/planning/runs/2026-11-25-graph-views.md). They do not contain the third-party article bytes. The matching evidence store must already retain the named snapshot and exact observations; fetching a changed live page is not reproduction of this corpus.

- `control-freeze.json` selects the four eligible observations and a stable corpus event ID.
- `control-queries.json` contains only candidate-visible query IDs and text. Add `corpus_id` and a fresh `run_key` to form a run request.
- `control-development.json` is evaluator input: eight supported questions, four corpus-unsupported questions, exact gold spans and limitations. Never pass this file to the candidate.

A curator prepared the cohort from retained bytes. A separate reviewer verified all twelve gold spans, supporting context for every positive question, and lack of the requested facts in the four-source corpus for the unsupported questions. Before any baseline run, “standard models” in the first question was clarified to “standard generally available models”; preview policy differs. No gold span changed. Questions and scoring rules are frozen before observing retrieval results.

The corpus is small and builder-visible. Unsupported means the requested fact is absent from these sources, not universally false. Gold spans are not an exhaustive inventory of every alternative supporting passage. The baseline returns passages, so an unsupported question receiving lexical matches is not itself a hallucinated answer.

The source snapshot is dated by the local collector. Later code, configuration and query artifacts describe the retrospective experiment; they are not evidence that the algorithm or questions existed at the earlier cutoff. No external timestamp proof is present.

`engine/tests/test_retrieval.py`, `test_retrieval_evaluation.py` and `test_retrieval_cli.py` use owned synthetic bytes to verify behavior without requiring the local development archive. Their results are conformance checks, not this corpus's retrieval quality. The [measurement contract](../../../docs/experiments/representation-metrics.md) defines the separate real development metrics and reproduction gate.
