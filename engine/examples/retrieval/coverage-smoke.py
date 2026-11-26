"""Owned synthetic preparation/execution integration; no real quality claim."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

from epiphysics import retrieval, retrieval_coverage, retrieval_evaluation
from epiphysics.store import Ledger, canonical, digest


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def child(arguments):
    result = subprocess.run([sys.executable, "-m", *arguments], capture_output=True,
                            text=True, timeout=75, check=True)
    return json.loads(result.stdout)


def run():
    with tempfile.TemporaryDirectory(prefix="epiphysics-coverage-", dir=os.environ.get("RUNNER_TEMP")) as directory:
        root = Path(directory).resolve()
        evidence = root / "evidence"
        ledger = Ledger(evidence)
        try:
            texts = [
                b"Amber archive stores blue receipts. The receipt color in Amber archive is blue. Amber archive verifies two signatures.",
                b"Birch service requires signed requests. Birch service accepts opaque identifiers.",
                b"Cedar registry lists active workers.",
                b"Delta protocol records invoice totals.",
            ]
            for index, raw in enumerate(texts):
                ledger.capture(f"owned:coverage-source-{index}", raw, event_id=f"source-{index}")
            snapshot = ledger.snapshot(event_id="snapshot")
            corpus = retrieval.freeze_retrieval_corpus(
                ledger, snapshot["id"], [f"source-{index}" for index in range(4)], event_id="corpus")
            # Historical candidate metadata is required before fresh questions.
            reference = retrieval.run_lexical_retrieval(
                ledger, corpus["id"], [{"query_id": "historical", "query": "Amber"}], run_key="reference")

            def span(source, needle):
                start = texts[source].index(needle)
                return {"observation_id": f"source-{source}", "start": start,
                        "end": start + len(needle), "sha256": digest(needle)}

            subjects = [
                (0, "Amber archive receipt color", "Amber archive receipt retention", [
                    {"bundle_id": "direct", "spans": [span(0, b"Amber archive stores blue receipts.")]},
                    {"bundle_id": "restatement", "spans": [span(0, b"The receipt color in Amber archive is blue.")]},
                ]),
                (0, "Amber archive stored receipts and required signatures", "Amber archive stored receipts and signature price", [
                    {"bundle_id": "joint", "spans": [span(0, b"Amber archive stores blue receipts."),
                                                       span(0, b"Amber archive verifies two signatures.")]},
                ]),
                (1, "Birch service request requirement", "Birch service request expiration", [
                    {"bundle_id": "direct", "spans": [span(1, b"Birch service requires signed requests.")]},
                ]),
                (1, "Birch service identifier type", "Birch service identifier rotation", [
                    {"bundle_id": "direct", "spans": [span(1, b"Birch service accepts opaque identifiers.")]},
                ]),
                (2, "Cedar registry worker status", "Cedar registry worker salaries", [
                    {"bundle_id": "direct", "spans": [span(2, texts[2])]},
                ]),
                (3, "Delta protocol recorded quantity", "Delta protocol invoice due date", [
                    {"bundle_id": "direct", "spans": [span(3, texts[3])]},
                ]),
            ]
            cases, pairs = [], []
            for index, (source, supported, unsupported, bundles) in enumerate(subjects):
                pair_id = f"pair-{index}"
                for label, query, support in (("answerable", supported, bundles), ("unanswerable", unsupported, [])):
                    cases.append({"question_id": f"q-{index}-{label}", "query": query, "pair_id": pair_id,
                                  "answerability": label, "support_bundles": support,
                                  "rationale": "Owned synthetic presence/absence control, not a population claim.",
                                  "family_tags": ["software_service"], "relation_tags": ["obligation"],
                                  "novelty": {"related_prior_question_ids": [], "distinction": "Owned integration fixture."}})
                pairs.append({"pair_id": pair_id, "supported_question_id": f"q-{index}-answerable",
                              "unsupported_question_id": f"q-{index}-unanswerable",
                              "anchor_observation_ids": [f"source-{source}"],
                              "changed_requirement": "Replace a stated property with an unstated property.",
                              "matching_rationale": "Same invented named system and comparable query scope."})
            cohort = {"schema_version": 2, "snapshot_id": snapshot["id"], "cohort": "development",
                      "cohort_id": "owned-coverage", "source_scope": "selected_corpus_only",
                      "support_semantics": "any_complete_bundle_v1", "cases": cases, "pairs": pairs,
                      "limitations": ["Owned synthetic integration data, not real evidence coverage."]}
            cohort_raw = canonical(cohort).encode()
            queries = retrieval_evaluation.project_queries(cohort)
            protocol = {"schema_version": 1, "study_id": "owned-coverage", "corpus_id": corpus["id"],
                        "corpus_hash": corpus["hash"], "source_snapshot_hash": snapshot["hash"],
                        "cohort_file_sha256": digest(cohort_raw), "projected_queries_hash": digest(canonical(queries).encode()),
                        "scoring_contract_id": "retrieval-coverage-evaluation-v2", "indexing_recipe": "raw-window-text-v1",
                        "executions": 2, "expected_pairs": 6, "cutoffs": [1, 3, 5], "adoption": "none",
                        "scope": "fresh_builder_visible_development",
                        "exposure": {"prior_results_seen": True, "fresh_results_seen": False},
                        "limits": {"model_calls": 0, "external_spend": 0, "assessment_seconds": 30, "dispatch_seconds": 60},
                        "successor_rule": "coverage-next-v1"}
            review = {"schema_version": 1, "cohort_file_sha256": digest(cohort_raw), "corpus_hash": corpus["hash"],
                      "curator_id": "owned-fixture-curator", "reviewer_id": "owned-fixture-reviewer",
                      "reviewed_source_ids": [f"source-{index}" for index in range(4)], "unresolved_case_ids": [],
                      "cases": [{"question_id": case["question_id"], "decision": "accept",
                                 "reviewed_bundle_ids": [bundle["bundle_id"] for bundle in case["support_bundles"]],
                                 "unsupported_reason": "Requested property is absent from all four owned source texts."
                                 if case["answerability"] == "unanswerable" else None,
                                 "alternatives_search_note": "Checked the four complete owned strings.",
                                 "pair_match_note": "Matching invented system; stated versus unstated property.",
                                 "novelty_note": "Synthetic fixture; no real-curator independence claim."} for case in cases]}
            protocol_raw, review_raw = canonical(protocol).encode(), canonical(review).encode()
            binding = {"id": reference["id"], "hash": reference["hash"]}
            prepared = retrieval_coverage.validate_coverage_preparation(
                ledger, cohort_raw=cohort_raw, protocol_raw=protocol_raw, review_raw=review_raw, reference_terminal=binding)
            freeze = retrieval_coverage.create_coverage_freeze(
                ledger, cohort_raw=cohort_raw, protocol_raw=protocol_raw, review_raw=review_raw,
                reference_terminal=binding, run_keys=["fresh-a", "fresh-b"])
        finally:
            ledger.close()

        for name, raw in (("cohort", cohort_raw), ("protocol", protocol_raw), ("review", review_raw)):
            (root / f"{name}.json").write_bytes(raw)
        common = {"schema_version": 3, "study_id": protocol["study_id"], **prepared["lineage"],
                  "protocol_hash": digest(protocol_raw), "review_hash": digest(review_raw),
                  "freeze_event_hash": freeze["hash"], "reference_terminal": binding,
                  "candidate_algorithm_hash": prepared["candidate_identity"]["algorithm_hash"],
                  "evaluator_identity_hash": prepared["evaluator_identity_hash"], "runtime_hash": prepared["runtime_hash"]}
        request = {"schema_version": 3, "phase": "preparation", "study_id": protocol["study_id"],
                   "evidence_store": str(evidence), "cohort_file": str(root / "cohort.json"),
                   "protocol_file": str(root / "protocol.json"), "review_file": str(root / "review.json"),
                   "corpus_id": corpus["id"], "freeze_event_id": freeze["id"]}
        policy = json.loads(Path("engine/examples/improvement/policy.json").read_text())

        def dispatch(phase, after_step, terminals=()):
            declared = {**common, "phase": phase}
            study = {**request, "phase": phase}
            if phase == "evaluation":
                declared.update(run_terminal_hashes={run["id"]: run["hash"] for run in terminals},
                                projection_hashes={run["id"]: run["body"]["projection_hash"] for run in terminals})
                study["run_terminal_ids"] = [run["id"] for run in terminals]
            policy["retrieval_study"] = declared
            (root / "policy.json").write_text(canonical(policy))
            (root / "study.json").write_text(canonical(study))
            return child(["epiphysics.improvement", "--store", str(root / "improvement"), "dispatch",
                          "--policy", str(root / "policy.json"),
                          "--suite", str(Path("engine/examples/improvement/entities.json").resolve()),
                          "--candidate", "reference", "--run-key", "owned-coverage-" + phase,
                          "--after-step", after_step, "--retrieval-study", str(root / "study.json"),
                          "--timeout-seconds", "60", "--completed-work", "Owned synthetic coverage " + phase])

        preparation = dispatch("preparation", "initial")["assessment"]
        ready = preparation["report"]["coverage_preparation"]
        require(ready["status"] == "ready" and "quality" not in ready, "Preparation invented quality")
        require("actual_retrieval" not in preparation["report"], "Preparation substituted historical quality")
        require(preparation["next_step"]["action"] == "execute_fresh_coverage_baseline", "Readiness did not select execution")
        terminals = []
        for key in ("fresh-a", "fresh-b"):
            path = root / f"{key}.json"
            path.write_text(canonical({"corpus_id": corpus["id"], "queries": queries,
                                       "run_key": key, "indexing_recipe": "raw-window-text-v1"}))
            terminals.append(child(["epiphysics", "--store", str(evidence), "run-retrieval", str(path)]))
        evaluation = dispatch("evaluation", preparation["next_step"]["id"], terminals)["assessment"]
        actual = evaluation["report"]["actual_retrieval"]
        require(actual["reproducibility"]["value"] == 1, "Fresh repeats did not reproduce")
        require(actual["measurement_contract_identity"]["hash"] == ready["measurement_contract_identity"]["hash"],
                "Preparation and evaluation measurement identities differ")
        require(actual["quality"]["runs"][0]["metrics"]["complete_support_rate_at_k"]["5"]["value"] == 1,
                "Owned complete-support fixture failed")
        require(evaluation["next_step"]["action"] == "prepare_answerability_evidence_gaps", "Unexpected evaluated successor")
        readonly = Ledger.open_readonly(evidence)
        try:
            require(readonly.verify()["valid"], "Evidence chain failed")
            require(retrieval_coverage.get_coverage_freeze(readonly, freeze["id"])["event"] == freeze,
                    "Historical freeze lookup failed after execution")
            require(readonly.events()[-1]["id"] == terminals[-1]["id"], "Assessment changed input evidence")
        finally:
            readonly.close()
        print("Owned synthetic coverage: preparation, two fresh raw processes, evaluation and next action passed.")


if __name__ == "__main__":
    run()
