"""Owned fixed-clause probe artifacts and controls; no private evidence."""
from copy import deepcopy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from epiphysics import retrieval_assessment as assessment, retrieval, retrieval_diagnosis as diagnosis, retrieval_probe as probe
from epiphysics.store import Ledger, canonical, digest
from test_retrieval_diagnosis import make_diagnosis_fixture, bind_diagnosis, rehash
from test_retrieval_coverage_preparation import study_files as coverage_files


def observation_ref(event):
    return {"observation_id": event["id"], "event_hash": event["hash"], "content_hash": event["body"]["content_hash"], "size": event["body"]["size"]}


def event_ref(event):
    return {"id": event["id"], "hash": event["hash"]}


def make_probe_fixture(root, evidence, *, origin=None, data=None, subprocess_runs=True, failure=None, wrong_requests=False, late_anchor=False, diverge=False, alternate_corpus=False, extra_trial=False):
    data = make_diagnosis_fixture(root, evidence) if data is None else data
    if origin is None:
        _, request, contract, review = bind_diagnosis(data, evidence, data["origin"])
        core = diagnosis.check_support_diagnosis(evidence, cohort=data["cohort"], freeze_event_id=data["freeze"]["id"],
            run_terminal_ids=request["run_terminal_ids"], origin_transition=data["origin"], declared_contract=contract,
            diagnosis_raw=Path(request["diagnosis_file"]).read_bytes(), review_raw=Path(request["diagnosis_review_file"]).read_bytes())
        temporary = Ledger(root / "owned-c5-origin")
        try:
            origin = temporary.append("improvement_completed", {"run_key": "owned-c5", "result": "assessed",
                "report": {"support_diagnosis": {"schema_version": 3, "phase": "support_diagnosis", "status": "checked",
                    "study_id": data["cohort"]["cohort_id"], "diagnosis_id": contract["diagnosis_id"], **core,
                    "input_bindings": {"prefix_head": {key: evidence.events()[-1][key] for key in ("seq", "id", "hash")}}}},
                "next_step": {"id": "owned-c5:next", "action": "prepare_focused_support_followup", "state": "queued", "scale_change_allowed": False}},
                "improvement:owned-c5:complete")
        finally:
            temporary.close()
    c5 = origin["body"]["report"]["support_diagnosis"]
    facts = c5["machine_findings"]
    target = next(c for c in data["cohort"]["cases"] if c["question_id"] == facts["focus_question_ids"][0])
    origin_raw = canonical(origin).encode()
    queries = [{"query_id": "clause-a", "query": "Delta invoice"}, {"query_id": "clause-b", "query": "Delta quantity"}]
    requests = [{"corpus_id": "corpus", "queries": queries, "run_key": "owned-probe-" + suffix, "indexing_recipe": "raw-window-text-v1"} for suffix in ("a", "b")]
    old = data["runs"][0]
    if extra_trial:
        retrieval.run_lexical_retrieval(evidence, corpus_id="corpus", queries=queries,
            run_key="undeclared-probe", indexing_recipe="raw-window-text-v1")
    if alternate_corpus:
        original_corpus = evidence.get("corpus")
        alternate = evidence.append("retrieval_corpus", deepcopy(original_corpus["body"]), "alternate-corpus")
    tip = evidence.events()[-1]
    protocol = {"schema_version": 1, "protocol_id": "owned-probe", "status": "pre_execution_protocol",
        "scope": "post_execution_builder_visible_development_diagnosis",
        "prerequisites": {"checked_c5_transition": event_ref(origin), "queued_preparation_step": origin["body"]["next_step"]["id"],
            "required_action": "prepare_focused_support_followup", "no_deferred_or_unresolved_failures": True, "origin_file_sha256": digest(origin_raw)},
        "origin": {"study_id": data["cohort"]["cohort_id"], "question_id": target["question_id"], "joint_query": target["query"],
            "joint_bundles": deepcopy(target["support_bundles"]), "cohort_file_sha256": digest(data["cohort_raw"]),
            "measurement_contract_hash": facts["origin_bindings"]["measurement_contract_hash"],
            "c4_terminal_refs": [event_ref(r) for r in data["runs"]], "c4_results_hash": old["body"]["results_hash"]},
        "fixed_candidate": {"corpus_id": "corpus", "corpus_hash": old["body"]["corpus_hash"], "config_hash": old["body"]["config_hash"],
            "indexing_recipe": "raw-window-text-v1", "candidate_algorithm_hash": data["prepared"]["candidate_identity"]["algorithm_hash"],
            "runtime_hash": old["body"]["runtime_hash"], "projection_hash": old["body"]["projection_hash"], "python_executable": sys.executable},
        "evidence_preservation": {"inherited_prefix": {"events": tip["seq"], "head": tip["hash"]}},
        "queries": queries, "executions": requests,
        "execution_limits": {"fresh_processes": 2, "ordered_repeats": True, "queries_per_process": 2, "top_k_per_query": 5,
            "cooperative_seconds_per_process": 30, "outer_seconds_per_process": 60, "model_calls": 0, "external_spend": 0,
            "additional_repeats_or_queries": 0, "config_or_recipe_changes": False, "network_fetches": False},
        "clause_support": [{"query_id": q["query_id"], "support_bundles": deepcopy(target["support_bundles"])} for q in queries]}
    if alternate_corpus:
        protocol["fixed_candidate"].update(corpus_id=alternate["id"], corpus_hash=alternate["hash"])
        for request in requests:
            request["corpus_id"] = alternate["id"]
    protocol_raw = json.dumps(protocol, indent=2).encode()
    review = {"schema_version": 1, "protocol_hash": digest(protocol_raw), "reviewer_id": "owned-probe-reviewer",
        "decision": "approved", "unresolved_findings": [], "scope": protocol["scope"]}
    review_raw = canonical(review).encode()
    prefix = "owned-probe:"
    def capture(role, raw):
        return observation_ref(evidence.capture(prefix + role, raw, event_id=prefix + role))
    envelope = {"schema_version": 1, "protocol": capture("protocol", protocol_raw), "review": capture("review", review_raw),
        "supervisor": capture("supervisor", Path(__file__).read_bytes()), "requests": [], "origin_transition": event_ref(origin),
        "candidate_algorithm_hash": protocol["fixed_candidate"]["candidate_algorithm_hash"], "runtime_hash": old["body"]["runtime_hash"],
        "validation_sources": {name: digest(raw) for name, raw in probe.runtime_sources().items()}}
    request_paths = []
    for index, request in enumerate(requests):
        raw = canonical(request).encode()
        path = root / f"probe-request-{index}.json"
        path.write_bytes(raw)
        request_paths.append(path)
        envelope["requests"].append({"run_key": request["run_key"], "artifact": capture(f"request-{index}", raw)})
    envelope_raw = canonical(envelope).encode()
    anchor = None if late_anchor else evidence.capture("support-probe-envelope:owned-probe", envelope_raw, event_id="support-probe:owned-probe:envelope")
    slots = []
    runs = []
    for index, request in enumerate(requests):
        slot = {"run_key": request["run_key"], "request_hash": envelope["requests"][index]["artifact"]["content_hash"],
            "status": "not_started", **{name: None for name in ("caller_artifact", "stdout_artifact", "stderr_artifact", "start", "terminal")}}
        if index and slots[0]["status"] != "completed":
            slots.append(slot)
            continue
        executed_request = deepcopy(request)
        if wrong_requests:
            executed_request["queries"][0]["query"] += " changed"
            request_paths[index].write_text(canonical(executed_request))
        started = datetime.now(timezone.utc).isoformat()
        began = time.monotonic()
        fail_here = failure is not None and ((index == 0 and not failure.startswith("second_")) or (index == 1 and failure.startswith("second_")))
        kind = failure.removeprefix("second_") if fail_here else None
        if kind == "launch_error":
            out, err, returncode, run = b"", b"Owned simulated launch error", "launch_error", None
        elif kind == "timeout":
            out, err, returncode, run = b"", b"Owned simulated timeout", "timeout", None
        elif kind in ("rejected_before_start", "rejected_after_start"):
            if kind == "rejected_after_start":
                expected_request = retrieval.contracts._request(evidence, "corpus", request["queries"]) | {"indexing_recipe": "raw-window-text-v1"}
                evidence.append("retrieval_started", {"schema_version": 2, "run_key": request["run_key"], "request": expected_request}, f"retrieval:{request['run_key']}:started")
            out, err, returncode, run = b"Owned opaque partial stdout", b"Owned nonzero process exit", 7, None
        elif kind == "rejected":
            expected_request = retrieval.contracts._request(evidence, "corpus", request["queries"]) | {"indexing_recipe": "raw-window-text-v1"}
            evidence.append("retrieval_started", {"schema_version": 2, "run_key": request["run_key"], "request": expected_request}, f"retrieval:{request['run_key']}:started")
            run = evidence.append("retrieval_rejected", {"schema_version": 2, "run_key": request["run_key"], "request": expected_request,
                "result": "rejected", "error": {"type": "OwnedFailure", "message": "Owned bounded rejection control"}}, f"retrieval:{request['run_key']}:terminal")
            out, err, returncode = canonical(run).encode(), b"", 1
        elif subprocess_runs:
            result = subprocess.run([sys.executable, "-s", "-m", "epiphysics", "--store", str(evidence.root), "run-retrieval", str(request_paths[index])],
                env={"PATH": os.defpath, "PYTHONPATH": str(Path(probe.__file__).parents[1]), "PYTHONDONTWRITEBYTECODE": "1"},
                capture_output=True, timeout=60)
            out, err, returncode = result.stdout, result.stderr, result.returncode
            if returncode:
                raise AssertionError(err.decode(errors="replace") + out.decode(errors="replace"))
            run = json.loads(out)
        else:
            run = retrieval.run_lexical_retrieval(evidence, **executed_request)
            out, err, returncode = canonical(run).encode(), b"", 0
        if diverge and index == 1 and run is not None:
            changed = deepcopy(run)
            changed["body"]["results"][0].update(hits=[], status="empty", reason="no_lexical_match")
            changed["body"]["results_hash"] = digest(canonical(changed["body"]["results"]).encode())
            changed["body"]["resources"]["output_bytes"] = len(canonical(changed["body"]["results"]).encode())
            rehash(changed)
            evidence.db.execute("DROP TRIGGER events_no_update")
            evidence.db.execute("UPDATE events SET body=?,hash=? WHERE id=?", (canonical(changed["body"]), changed["hash"], changed["id"]))
            evidence.db.commit()
            run, out = changed, canonical(changed).encode()
        if anchor is None:
            anchor = evidence.capture("support-probe-envelope:owned-probe", envelope_raw, event_id="support-probe:owned-probe:envelope")
        elapsed = time.monotonic() - began
        ended = datetime.now(timezone.utc).isoformat()
        slot["status"] = "rejected" if kind in ("rejected_before_start", "rejected_after_start") else kind or "completed"
        if run is not None:
            slot["terminal"] = event_ref(run)
            slot["start"] = event_ref(evidence.get(f"retrieval:{request['run_key']}:started"))
            runs.append(run)
        start_event = retrieval.contracts._optional(evidence, f"retrieval:{request['run_key']}:started")
        if start_event is not None:
            slot["start"] = event_ref(start_event)
        caller = {"schema_version": 1, "run_key": request["run_key"], "request_hash": slot["request_hash"], "started_at": started,
            "ended_at": ended, "elapsed_seconds": elapsed, "elapsed_scope": "fresh process wall time through exit", "returncode": returncode,
            "stdout_hash": digest(out), "stdout_bytes": len(out), "stderr_hash": digest(err), "stderr_bytes": len(err), "model_calls": 0, "external_spend": 0}
        slot["stdout_artifact"] = capture(f"stdout-{index}", out)
        slot["stderr_artifact"] = capture(f"stderr-{index}", err)
        slot["caller_artifact"] = capture(f"caller-{index}", canonical(caller).encode())
        slots.append(slot)
    tip = evidence.events()[-1]
    executions = {"schema_version": 1, "envelope_hash": digest(envelope_raw), "envelope_capture": event_ref(anchor),
        "evidence_head": {key: tip[key] for key in ("seq", "id", "hash")}, "slots": slots}
    _, request, contract = coverage_files(data, evidence, "evaluation", data["runs"])
    request.pop("run_terminal_ids")
    contract.pop("run_terminal_hashes")
    contract.pop("projection_hashes")
    request["phase"] = contract["phase"] = "support_probe"
    raws = {"probe_protocol": protocol_raw, "probe_review": review_raw, "probe_envelope": envelope_raw, "probe_execution": canonical(executions).encode(), "origin": origin_raw}
    for role, raw in raws.items():
        path = root / (role + ".json")
        path.write_bytes(raw)
        request[role + "_file"] = str(path)
        if role != "origin":
            contract[role + "_hash"] = digest(raw)
    contract.update(origin_transition=event_ref(origin), origin_step_id=origin["body"]["next_step"]["id"])
    path = root / "support-probe.json"
    path.write_text(canonical(request))
    result = {**data, "origin": origin, "probe_protocol": protocol, "probe_review": review, "envelope": envelope, "executions": executions,
        "probe_runs": runs, "request_path": path, "request": request, "contract": contract, "raws": raws}
    result["core_args"] = {"cohort": data["cohort"], "origin_transition": origin, "protocol": protocol, "review": review,
        "envelope": envelope, "executions": executions, "declared_contract": contract}
    return result


def bind_probe(data, evidence, origin):
    return make_probe_fixture(data["root"], evidence, data=data, origin=origin)


class RetrievalProbeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.evidence = Ledger(self.root / "evidence")
        self.addCleanup(self.evidence.close)
        options = {
            "test_two_equally_wrong_requests_fail_exact_binding_and_guard_mutant": {"wrong_requests": True},
            "test_late_envelope_is_rejected_and_guard_mutant_detected": {"late_anchor": True},
            "test_valid_different_repetition_has_no_combined_support_summary": {"diverge": True},
            "test_alternate_same_content_corpus_is_rejected": {"alternate_corpus": True},
            "test_incomplete_first_preserves_actual_failure_and_unstarted_slot": {"failure": "launch_error"},
            "test_incomplete_second_preserves_first_completion": {"failure": "second_rejected"},
            "test_inherited_boundary_cannot_hide_an_extra_clause_trial": {"extra_trial": True},
        }
        self.data = make_probe_fixture(self.root, self.evidence, **options.get(self._testMethodName, {}))

    def check(self, **changes):
        return probe.check_support_probe(self.evidence, **{**self.data["core_args"], **changes})

    def test_two_real_fresh_processes_reproduce_and_preserve_original_evidence(self):
        before = self.evidence.events()
        value = self.check()
        self.assertEqual(1, value["reproducibility"]["value"])
        self.assertEqual(value, self.check())
        self.assertEqual(before, self.evidence.events())
        combined = value["joint_support_union_of_two_top5"]
        self.assertEqual("joint_support_union_of_two_top5", combined["metric"])
        self.assertIsNone(combined["shared_rank"])
        self.assertEqual(2, combined["windows"]["window_occurrences"])
        self.assertEqual(1, combined["windows"]["distinct_windows"])
        self.assertEqual(combined["windows"]["summed_window_bytes"], 2 * combined["windows"]["union_source_bytes"])
        self.assertNotIn("quality", value)


    def test_no_search_projection_or_scoring_entry_point_is_called(self):
        forbidden = {"evaluate_retrieval", "_score_case", "_score_coverage", "_score_coverage_case", "run_lexical_retrieval", "project_index", "lexical_search"}
        def guard(frame, event, arg):
            if event == "call" and frame.f_code.co_name in forbidden:
                raise AssertionError("Unexpected execution: " + frame.f_code.co_name)
        sys.setprofile(guard)
        try:
            self.assertEqual(1, self.check()["reproducibility"]["value"])
        finally:
            sys.setprofile(None)

    def test_exact_request_and_anchor_mutants_preserve_ordinary_positive(self):
        sources = probe.runtime_sources()
        same, event = probe._same, probe._event
        def no_request_binding(a, b):
            if type(a) is dict and type(b) is dict and ("request" in a or "corpus_id" in a and "queries" in a):
                return True
            return same(a, b)
        with patch.object(probe, "runtime_sources", return_value=sources), patch.object(probe, "_same", no_request_binding):
            self.assertEqual(1, self.check()["reproducibility"]["value"])
        with patch.object(probe, "runtime_sources", return_value=sources), patch.object(probe, "_event", side_effect=event):
            self.assertEqual(1, self.check()["reproducibility"]["value"])

    def test_two_equally_wrong_requests_fail_exact_binding_and_guard_mutant(self):
        self.assertEqual(self.data["probe_runs"][0]["body"]["results"], self.data["probe_runs"][1]["body"]["results"])
        with self.assertRaisesRegex(ValueError, "exact request"):
            self.check()
        sources, same = probe.runtime_sources(), probe._same
        def no_request_binding(a, b):
            if type(a) is dict and type(b) is dict and ("request" in a or "corpus_id" in a and "queries" in a):
                return True
            return same(a, b)
        with patch.object(probe, "runtime_sources", return_value=sources), patch.object(probe, "_same", no_request_binding):
            # The neutral terminal check independently receives the declared
            # request, so disabling the outer equality alone still refuses it.
            with self.assertRaisesRegex(ValueError, "earlier v2 claim"):
                self.check()

    def test_late_envelope_is_rejected_and_guard_mutant_detected(self):
        with self.assertRaisesRegex(ValueError, "precedes envelope"):
            self.check()
        sources, event = probe.runtime_sources(), probe._event
        first_start = self.evidence.get(self.data["executions"]["slots"][0]["start"]["id"])
        def no_anchor_order(ledger, ref, expected_id, kind=None):
            value = event(ledger, ref, expected_id, kind)
            if expected_id == "support-probe:owned-probe:envelope":
                value = {**value, "seq": first_start["seq"] - 0.5}
            return value
        with patch.object(probe, "runtime_sources", return_value=sources), patch.object(probe, "_event", no_anchor_order):
            self.assertEqual(1, self.check()["reproducibility"]["value"])

    def test_valid_different_repetition_has_no_combined_support_summary(self):
        self.assertTrue(self.evidence.verify()["valid"])
        for run in self.data["probe_runs"]:
            self.assertEqual(run, retrieval.get_retrieval_run(self.evidence, run["id"]))
        report = self.check()
        self.assertEqual(0, report["reproducibility"]["value"])
        self.assertFalse(report["reproducibility"]["ordered_results_equal"])
        self.assertIsNone(report["clause_support"])
        self.assertIsNone(report["joint_support_union_of_two_top5"])
        self.assertEqual(2, len(report["executions"]))

    def test_inherited_boundary_cannot_hide_an_extra_clause_trial(self):
        accepted = self.data["origin"]["body"]["report"]["support_diagnosis"]["input_bindings"]["prefix_head"]
        self.assertGreater(self.data["probe_protocol"]["evidence_preservation"]["inherited_prefix"]["events"], accepted["seq"])
        self.assertIsNotNone(self.evidence.get("retrieval:undeclared-probe:terminal"))
        with self.assertRaisesRegex(ValueError, "accepted diagnosis prefix"):
            self.check()
        prepared = assessment.prepare_retrieval_study(self.data["request_path"], declared_contract=self.data["contract"])
        with self.assertRaisesRegex(ValueError, "accepted diagnosis prefix"):
            assessment.assess_prepared_retrieval_study(prepared)

    def test_alternate_same_content_corpus_is_rejected(self):
        old = self.evidence.get("corpus")
        other = self.evidence.get("alternate-corpus")
        self.assertEqual(old["body"], other["body"])
        with self.assertRaisesRegex(ValueError, "candidate/runtime/configuration"):
            self.check()

    def test_incomplete_first_preserves_actual_failure_and_unstarted_slot(self):
        before = self.evidence.events()
        slots = self.data["executions"]["slots"]
        self.assertEqual(["launch_error", "not_started"], [slot["status"] for slot in slots])
        self.assertEqual([], probe.terminal_ids(self.data["executions"]))
        self.assertEqual(8, len(probe.capture_references(self.data["envelope"], self.data["executions"])))
        with self.assertRaisesRegex(ValueError, "execution incomplete"):
            self.check()
        self.assertEqual(before, self.evidence.events())

    def test_incomplete_second_preserves_first_completion(self):
        self.assertEqual(["completed", "rejected"], [slot["status"] for slot in self.data["executions"]["slots"]])
        self.assertEqual(2, len(probe.terminal_ids(self.data["executions"])))
        with self.assertRaisesRegex(ValueError, "execution incomplete"):
            self.check()

    def test_omitted_real_execution_or_truncated_prefix_is_rejected(self):
        changed = deepcopy(self.data["executions"])
        changed["slots"][1].update(status="not_started", **{name: None for name in ("start", "terminal", "caller_artifact", "stdout_artifact", "stderr_artifact")})
        with self.assertRaisesRegex(ValueError, "omits an existing"):
            self.check(executions=changed)
        changed = deepcopy(self.data["executions"])
        earlier = self.evidence.get(changed["slots"][0]["terminal"]["id"])
        changed["evidence_head"] = {key: earlier[key] for key in ("seq", "id", "hash")}
        with self.assertRaisesRegex(ValueError, "complete captured prefix"):
            self.check(executions=changed)

    def test_bound_bytes_origin_and_support_changes_are_rejected(self):
        changed = deepcopy(self.data["core_args"]["protocol"])
        changed["origin"]["joint_query"] += " altered"
        with self.assertRaisesRegex(ValueError, "target differs"):
            self.check(protocol=changed)
        changed = deepcopy(self.data["core_args"]["protocol"])
        changed["clause_support"][0]["support_bundles"][0]["spans"][0]["end"] += 1
        with self.assertRaisesRegex(ValueError, "original source intervals"):
            self.check(protocol=changed)
        changed = deepcopy(self.data["core_args"]["origin_transition"])
        changed["body"]["next_step"]["action"] = "something-else"
        rehash(changed)
        with self.assertRaisesRegex(ValueError, "origin differs"):
            self.check(origin_transition=changed)
        raw_hash = self.data["executions"]["slots"][0]["stdout_artifact"]["content_hash"]
        blob = self.evidence.root / "blobs" / raw_hash
        old = blob.read_bytes()
        try:
            blob.write_bytes(b"wrong stdout")
            with self.assertRaises(ValueError):
                self.check()
        finally:
            blob.write_bytes(old)

    def test_source_guard_deadline_and_malformed_shapes(self):
        with patch.object(probe, "IMPLEMENTATION_SOURCE", b"changed"):
            with self.assertRaisesRegex(ValueError, "implementation reloaded"):
                self.check()
        with self.assertRaisesRegex(TimeoutError, "budget"):
            self.check(deadline=time.monotonic() - 1)
        for key in ("envelope", "executions", "review", "protocol"):
            for value in (None, [], "bad"):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.check(**{key: value})
        huge = deepcopy(self.data["envelope"])
        huge["supervisor"]["size"] = probe.MAX_BYTES + 1
        with self.assertRaisesRegex(ValueError, "byte bound"):
            probe.capture_references(huge, self.data["executions"])

    def test_union_bytes_merge_overlap_adjacency_and_duplicate_windows(self):
        rows = [{"observation_id": source, "start": start, "end": end, "sha256": "0" * 64}
            for source, start, end in (("a", 0, 10), ("a", 5, 15), ("a", 15, 20), ("a", 0, 10), ("b", 0, 10))]
        result = probe._window_stats(rows)
        self.assertEqual(5, result["window_occurrences"])
        self.assertEqual(4, result["distinct_windows"])
        self.assertEqual(45, result["summed_window_bytes"])
        self.assertEqual(30, result["union_source_bytes"])
        self.assertEqual({"a": 20, "b": 10}, result["union_source_bytes_by_observation"])


class RetrievalProbeFailureTests(unittest.TestCase):
    def test_timeout_and_actual_first_rejection_preserve_second_unstarted(self):
        for failure in ("timeout", "rejected"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                ledger = Ledger(root / "evidence")
                try:
                    data = make_probe_fixture(root, ledger, failure=failure)
                    self.assertEqual([failure, "not_started"], [slot["status"] for slot in data["executions"]["slots"]])
                    self.assertEqual(int(failure == "rejected"), len(probe.terminal_ids(data["executions"])))
                    before = ledger.events()
                    with self.assertRaisesRegex(ValueError, "execution incomplete"):
                        probe.check_support_probe(ledger, **data["core_args"])
                    self.assertEqual(before, ledger.events())
                finally:
                    ledger.close()


    def _check_partial_nonzero_capture(self, failure):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            ledger = Ledger(root / "evidence")
            try:
                data = make_probe_fixture(root, ledger, failure=failure)
                first, second = data["executions"]["slots"]
                self.assertEqual(("rejected", "not_started"), (first["status"], second["status"]))
                self.assertIsNone(first["terminal"])
                self.assertEqual(failure == "rejected_after_start", first["start"] is not None)
                self.assertEqual([], probe.terminal_ids(data["executions"]))
                prepared = assessment.prepare_retrieval_study(data["request_path"], declared_contract=data["contract"])
                self.assertEqual(data["raws"]["probe_execution"], prepared["artifacts"]["probe_execution"])
                for name in ("caller_artifact", "stdout_artifact", "stderr_artifact"):
                    ref = first[name]
                    raw = prepared["artifacts"]["blob:" + ref["content_hash"]]
                    self.assertEqual(ref["content_hash"], digest(raw))
                before = ledger.events()
                for attempt in range(2):
                    with self.assertRaisesRegex(ValueError, "execution incomplete"):
                        assessment.assess_prepared_retrieval_study(prepared)
                self.assertEqual(before, ledger.events())
            finally:
                ledger.close()

    def test_nonzero_before_start_captures_opaque_output_before_incomplete_failure(self):
        self._check_partial_nonzero_capture("rejected_before_start")

    def test_nonzero_after_start_captures_claim_and_output_before_incomplete_failure(self):
        self._check_partial_nonzero_capture("rejected_after_start")


if __name__ == "__main__":
    unittest.main()
