"""Fresh C24 literal evidence controls; no capture/producer/ledger execution."""

from copy import deepcopy
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from epiphysics import prospective_quality_evidence as consumer
from epiphysics.prospective_quality import QualityResult


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


SOURCE = b"C24 stone \xe2\x98\x86\r\nplum\rharbor\nfin"
PARTITIONS = ((0, 15, b"C24 stone \xe2\x98\x86\r\n"), (15, 27, b"plum\rharbor\n"), (27, 30, b"fin"))
# Literal offsets are preparation assertions, not inferred from the consumer.
GOOD_FIELDS = {"schema_version": 1, "source_sha256": sha(SOURCE), "source_byte_length": 30,
               "lines": [{"start": start, "end": end, "sha256": sha(raw)} for start, end, raw in PARTITIONS]}
GOOD_ARTIFACT = encoded(GOOD_FIELDS)
STAMP = {"utc": "2034-04-05T06:07:08+00:00", "monotonic": 501.25}


def event(kind, event_id, body, seq, previous):
    value = {"id": event_id, "kind": kind, "recorded_at": STAMP["utc"], "body": body, "previous_hash": previous}
    return {**value, "seq": seq, "hash": sha(encoded(value))}


def seal(expected, claim, receipt, terminal):
    """Construct invented retained bytes; never call the code under test."""
    claim["hash"] = sha(encoded({key: claim[key] for key in ("id", "kind", "recorded_at", "body", "previous_hash")}))
    receipt["claim_hash"] = terminal["body"]["claim_hash"] = claim["hash"]
    receipt_raw = encoded(receipt)
    terminal["body"]["receipt_sha256"] = sha(receipt_raw)
    terminal["hash"] = sha(encoded({key: terminal[key] for key in ("id", "kind", "recorded_at", "body", "previous_hash")}))
    claim_raw, terminal_raw = encoded(claim), encoded(terminal)
    expected["claim_bytes_sha256"], expected["terminal_bytes_sha256"] = sha(claim_raw), sha(terminal_raw)
    return {"expected_bytes": encoded(expected), "claim_bytes": claim_raw, "terminal_bytes": terminal_raw,
            "receipt_bytes": receipt_raw, "source_bytes": SOURCE, "stdout_bytes": GOOD_ARTIFACT}


def invented_bundle(artifact=GOOD_ARTIFACT):
    binding = {"instance_id": "C24-invented-quartz", "question_id": "C24-question-ivy", "slot_id": "C24-slot-amber",
               "channel_id": "C24-channel-river", "acceptance_sha256": "1" * 64, "declaration_sha256": "2" * 64,
               "source_sha256": sha(SOURCE), "schema_sha256": "3" * 64, "producer_sha256": "4" * 64,
               "worker_sha256": "5" * 64}
    runtime = {"path": "/invented/runtime/python", "sha256": "6" * 64, "version": "invented-runtime-metadata"}
    claim_id = "prospective-capture:" + sha(encoded([binding["instance_id"], binding["channel_id"]])) + ":first"
    body = {"schema_version": 1, "binding": binding, "runtime": runtime, "capture_sha256": "7" * 64,
            "timing": {"not_before": "2034-04-05T06:07:00Z", "latest_start": "2034-04-05T06:07:09Z",
                       "artifact_due": "2034-04-05T06:08:00Z", "wall_seconds": 2, "cleanup_seconds": 1},
            "channel_directory": "/invented/c24/quartz", "epoch": "89abcdef" * 4,
            "firstness_scope": "this local ledger, instance and channel; no registration authentication"}
    claim = event("prospective_capture_started", claim_id, body, 41, "8" * 64)

    def stream(raw, name):
        return {"observed_prefix_bytes": len(raw), "observed_prefix_sha256": sha(raw), "retained_bytes": len(raw),
                "retained_sha256": sha(raw), "observed_bytes_lower_bound": len(raw), "eof_observed": True,
                "complete_bytes_observed": True, "full_sha256": sha(raw),
                "first_byte_observed": STAMP if raw else None, "last_byte_observed": STAMP if raw else None,
                "file_durable_observed": STAMP, "path": body["channel_directory"] + "/" + name + ".bin",
                "retention_verified": True}
    receipt = {"schema_version": 1, "claim_id": claim_id, "claim_hash": claim["hash"], "epoch": body["epoch"],
               "binding": binding, "started": STAMP, "ended": STAMP, "pid": 23456, "spawn_returned": True,
               "launch_requested": STAMP, "launch_returned": STAMP, "start_window_observed": True,
               "returncode": 0, "child_reaped": True, "wait_status": 0, "wait_observed": STAMP,
               "wait_status_unavailable": False, "termination": None, "errors": [], "close_errors": [],
               "close_errors_truncated": False, "clock_interval_verified": True,
               "clock_observations": {"consistent": True, "observations": 12, "violation_count": 0, "first_violation": None},
               "descendant_isolation": False, "quality": None, "obligation_outcome": None, "registered": False,
               "streams": {"stdout": stream(artifact, "stdout"), "stderr": stream(b"", "stderr")}}
    # Interleaving is intentional: the terminal is neither adjacent nor chained
    # directly to the claim. No full ledger provenance is represented here.
    terminal = event("prospective_capture_finished", claim_id + ":finished",
                     {"claim_id": claim_id, "claim_hash": claim["hash"], "receipt_path": body["channel_directory"] + "/receipt.json",
                      "receipt_sha256": sha(encoded(receipt)), "receipt_file_durable_observed": STAMP}, 44, "9" * 64)
    expected = {"schema_version": 1, "binding": deepcopy(binding), "runtime": deepcopy(runtime),
                "capture_sha256": "7" * 64, "source_byte_length": 30,
                "claim_bytes_sha256": sha(encoded(claim)), "terminal_bytes_sha256": sha(encoded(terminal))}
    return deepcopy((expected, claim, receipt, terminal))


def expected_output(inputs, status, reason, quality_reason=None, observed=None):
    identities = {}
    limits = {"expected": 16384, "claim": 65536, "terminal": 65536, "receipt": 65536, "source": 8192, "stdout": 65536}
    for name, cap in limits.items():
        raw = inputs[name + "_bytes"]
        identities[name] = {"byte_length": len(raw) if type(raw) is bytes else None,
                            "sha256": sha(raw) if type(raw) is bytes and len(raw) <= cap else None}
    result = None
    if quality_reason is not None:
        result = {"quality": True if quality_reason == "matches" else None if quality_reason == "checker_capacity" else False,
                  "reason": quality_reason, "source_sha256": sha(inputs["source_bytes"]),
                  "source_byte_length": len(inputs["source_bytes"]), "artifact_sha256": sha(inputs["stdout_bytes"]),
                  "artifact_byte_length": len(inputs["stdout_bytes"])}
    return encoded({"schema_version": 1, "evaluation_contract": "captured-line-index-evidence-v1",
                    "scope": "conditional_supplied_byte_consistency_and_content", "status": status, "reason": reason,
                    "input_identities": identities, "quality_result": result, "observed_stdout_bytes_lower_bound": observed,
                    "publication": "not_assessed", "firstness": "not_established", "obligation_outcome": None,
                    "continuation_allowed": False})


def fresh_cases():
    assert len(SOURCE) == 30 and b"".join(raw for _, _, raw in PARTITIONS) == SOURCE
    assert all(SOURCE[start:end] == raw and end - start == len(raw) for start, end, raw in PARTITIONS)
    cases = []

    def add(name, inputs, status="unavailable", reason="metadata_schema", quality=None, observed=None, calls=0, mode="real"):
        cases.append({"id": name, "inputs": inputs, "expected": expected_output(inputs, status, reason, quality, observed),
                      "checker_calls": calls, "checker_mode": mode, "exception": None})

    baseline = seal(*invented_bundle())
    add("complete_interleaved", baseline, "checked", "content_checked", "matches", len(GOOD_ARTIFACT), 1)
    for name, artifact, quality in (
        ("complete_malformed", b"C24 complete: not JSON", "artifact_json"),
        ("complete_invalid_utf8", b"\xffC24", "artifact_utf8"),
        ("complete_wrong_content", encoded({**GOOD_FIELDS, "source_byte_length": 31}), "content_mismatch"),
        ("complete_whitespace", json.dumps(GOOD_FIELDS, indent=2).encode() + b"\n", "matches"),
        ("artifact_exact_cap", GOOD_ARTIFACT + b" " * (65536 - len(GOOD_ARTIFACT)), "matches"),
    ):
        inputs = seal(*invented_bundle(artifact)); inputs["stdout_bytes"] = artifact
        add(name, inputs, "checked", "content_checked", quality, len(artifact), 1)
    cap_source = b"C" * 8192
    cap_artifact = encoded({"schema_version": 1, "source_sha256": sha(cap_source), "source_byte_length": 8192,
                            "lines": [{"start": 0, "end": 8192, "sha256": sha(cap_source)}]})
    e, c, r, t = invented_bundle(cap_artifact)
    e["source_byte_length"] = 8192
    e["binding"]["source_sha256"] = c["body"]["binding"]["source_sha256"] = r["binding"]["source_sha256"] = sha(cap_source)
    inputs = seal(e, c, r, t); inputs.update(source_bytes=cap_source, stdout_bytes=cap_artifact)
    add("source_exact_cap", inputs, "checked", "content_checked", "matches", len(cap_artifact), 1)
    for name in ("nonzero_exit", "unreaped_child", "clock_uncertain", "stderr_unretained", "close_uncertain"):
        e, c, r, t = invented_bundle()
        if name == "nonzero_exit": r.update(returncode=7, wait_status=1792)
        if name == "unreaped_child": r.update(child_reaped=False, returncode=None, wait_status=None, wait_observed=None,
                                              wait_status_unavailable=True, termination="wait_status_unavailable")
        if name == "clock_uncertain":
            r.update(clock_interval_verified=False, clock_observations={"consistent": False, "observations": 12,
                     "violation_count": 1, "first_violation": STAMP})
        if name == "stderr_unretained":
            r["streams"]["stderr"].update(retention_verified=False, file_durable_observed=None, retained_bytes=None,
                                          retained_sha256=None, eof_observed=False, complete_bytes_observed=False, full_sha256=None)
        if name == "close_uncertain":
            r["close_errors"] = [{"operation": "close_stdout_file", "error_type": "OSError", "native_close_uncertain": True}]
            r["errors"] = deepcopy(r["close_errors"])
        add(name, seal(e, c, r, t), "checked", "content_checked", "matches", len(GOOD_ARTIFACT), 1)
    empty = seal(*invented_bundle(b"")); empty["stdout_bytes"] = b""
    add("closed_empty", empty, "closed_empty", "zero_bytes_no_content_check", observed=0)
    for name, raw, count, status, reason in (
        ("overflow_prefix", b"P" * 65536, 65537, "overflow_observed", "stdout_overflow_no_content_check"),
        ("incomplete_prefix", b'{"C24":', 7, "unavailable", "stdout_incomplete"),
    ):
        e, c, r, t = invented_bundle(raw)
        r["streams"]["stdout"].update(eof_observed=False, complete_bytes_observed=False, full_sha256=None,
                                      observed_bytes_lower_bound=count)
        if name == "overflow_prefix": r["termination"] = "stdout_overflow"
        inputs = seal(e, c, r, t); inputs["stdout_bytes"] = raw
        add(name, inputs, status, reason, observed=count)
    for name in ("expected", "claim", "terminal", "receipt", "source", "stdout"):
        inputs = dict(baseline); inputs[name + "_bytes"] = None
        add("missing_" + name, inputs, reason="missing_" + name)
        inputs = dict(baseline); inputs[name + "_bytes"] = bytearray(b"wrong built-in type")
        add("type_" + name, inputs, reason="input_type_" + name)
        cap = {"expected": 16384, "claim": 65536, "terminal": 65536, "receipt": 65536, "source": 8192, "stdout": 65536}[name]
        inputs = dict(baseline); inputs[name + "_bytes"] = b"X" * (cap + 1)
        add("cap_" + name, inputs, reason="input_capacity_" + name)
    for name, field, raw, reason in (
        ("duplicate_metadata", "expected_bytes", b'{"x":1,"x":2}', "metadata_duplicate_key"),
        ("nonfinite_metadata", "receipt_bytes", b'{"x":NaN}', "metadata_number"),
        ("overflow_float", "receipt_bytes", b'{"x":1e9999}', "metadata_number"),
        ("huge_integer", "receipt_bytes", b'{"x":' + b"9" * 5000 + b'}', "metadata_number"),
        ("deep_metadata", "claim_bytes", b"[" * 40 + b"0" + b"]" * 40, "metadata_capacity"),
        ("bad_utf8_metadata", "terminal_bytes", b"\xff", "metadata_invalid"),
        ("noncanonical_metadata", "claim_bytes", baseline["claim_bytes"] + b"\n", "metadata_noncanonical"),
    ):
        inputs = dict(baseline); inputs[field] = raw
        add(name, inputs, reason=reason)
    for name, reason in (
        ("expected_capture_mismatch", "capture_contract_binding"), ("expected_runtime_mismatch", "capture_contract_binding"),
        ("expected_binding_mismatch", "capture_contract_binding"), ("source_length_mismatch", "source_binding"),
        ("receipt_epoch_mismatch", "receipt_binding"), ("receipt_path_mismatch", "capture_path_binding"),
        ("stdout_path_mismatch", "capture_path_binding"), ("terminal_sequence", "event_binding"),
        ("boolean_sequence", "metadata_schema"), ("extra_receipt_field", "metadata_schema"),
        ("missing_stream_field", "metadata_schema"), ("wrong_full_hash", "stream_consistency"),
        ("missing_durability", "stream_consistency"), ("false_retention", "stdout_retention_unverified"),
        ("boolean_eof", "metadata_schema"), ("receipt_claim_id", "receipt_binding"),
    ):
        e, c, r, t = invented_bundle()
        if name == "expected_capture_mismatch": e["capture_sha256"] = "a" * 64
        if name == "expected_runtime_mismatch": e["runtime"]["sha256"] = "a" * 64
        if name == "expected_binding_mismatch": e["binding"]["question_id"] = "C24-other"
        if name == "source_length_mismatch": e["source_byte_length"] = 29
        if name == "receipt_epoch_mismatch": r["epoch"] = "a" * 32
        if name == "receipt_path_mismatch": t["body"]["receipt_path"] = "/invented/elsewhere/receipt.json"
        if name == "stdout_path_mismatch": r["streams"]["stdout"]["path"] = "/invented/elsewhere/stdout.bin"
        if name == "terminal_sequence": t["seq"] = 41
        if name == "boolean_sequence": c["seq"] = True
        if name == "extra_receipt_field": r["extra"] = "not declared"
        if name == "missing_stream_field": del r["streams"]["stdout"]["eof_observed"]
        if name == "wrong_full_hash": r["streams"]["stdout"]["full_sha256"] = "a" * 64
        if name == "missing_durability": r["streams"]["stdout"]["file_durable_observed"] = None
        if name == "false_retention": r["streams"]["stdout"]["retention_verified"] = False
        if name == "boolean_eof": r["streams"]["stdout"]["eof_observed"] = 1
        if name == "receipt_claim_id": r["claim_id"] = "not-the-claim"
        add(name, seal(e, c, r, t), reason=reason, observed=len(GOOD_ARTIFACT) if name == "false_retention" else None)
    for name, reason in (("source_swapped", "source_binding"), ("stdout_swapped", "stdout_binding"),
                         ("receipt_swapped", "receipt_hash"), ("claim_anchor", "caller_event_anchor"),
                         ("terminal_anchor", "caller_event_anchor"), ("claim_event_hash", "event_hash"),
                         ("terminal_event_hash", "event_hash")):
        inputs = dict(baseline)
        if name == "source_swapped": inputs["source_bytes"] = b"X" + SOURCE[1:]
        if name == "stdout_swapped": inputs["stdout_bytes"] = b"!" + GOOD_ARTIFACT[1:]
        if name == "receipt_swapped":
            value = json.loads(inputs["receipt_bytes"]); value["pid"] = 23457; inputs["receipt_bytes"] = encoded(value)
        if name in ("claim_anchor", "terminal_anchor"):
            value = json.loads(inputs["expected_bytes"]); value[name.split("_")[0] + "_bytes_sha256"] = "a" * 64
            inputs["expected_bytes"] = encoded(value)
        if name in ("claim_event_hash", "terminal_event_hash"):
            key = name.split("_")[0] + "_bytes"; value = json.loads(inputs[key]); value["hash"] = "a" * 64; inputs[key] = encoded(value)
        add(name, inputs, reason=reason, observed=len(GOOD_ARTIFACT) if name == "stdout_swapped" else None)
    for mode, reason, quality in (("unavailable", "checker_unavailable", "checker_capacity"),
                                  ("error", "checker_error", None), ("wrong_identity", "checker_contract_mismatch", None),
                                  ("wrong_type", "checker_contract_mismatch", None), ("integer_quality", "checker_contract_mismatch", None)):
        add("checker_" + mode, dict(baseline), reason=reason, quality=quality, observed=len(GOOD_ARTIFACT), calls=1, mode=mode)
    for exception in ("KeyboardInterrupt", "SystemExit"):
        cases.append({"id": "checker_" + exception, "inputs": dict(baseline), "expected": None,
                      "checker_calls": 1, "checker_mode": exception, "exception": exception})
    return cases


def save_once(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


class QualityEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.started = time.perf_counter()
        cls.temporary = None
        directory = os.environ.get("C24_RETAIN_DIRECTORY")
        if directory:
            cls.root = Path(directory); cls.root.mkdir()
        else:
            cls.temporary = tempfile.TemporaryDirectory(prefix="c24-evidence-"); cls.root = Path(cls.temporary.name)
        cls.cases = fresh_cases()
        cls.checker_calls = cls.actual_checker_calls = cls.consumer_calls = 0
        plan = []
        for case in cls.cases:
            folder = cls.root / case["id"]; folder.mkdir()
            descriptions = {}
            for name, raw in case["inputs"].items():
                descriptions[name] = {"python_type": type(raw).__name__, "sha256": None, "byte_length": None}
                if isinstance(raw, (bytes, bytearray)):
                    saved = bytes(raw); save_once(folder / (name + ".bin"), saved)
                    descriptions[name].update(sha256=sha(saved), byte_length=len(saved))
            if case["expected"] is not None:
                save_once(folder / "expected-output.json", case["expected"])
            plan.append({"id": case["id"], "inputs": descriptions, "expected_output_sha256": sha(case["expected"]) if case["expected"] else None,
                         "expected_exception": case["exception"], "checker_mode": case["checker_mode"],
                         "expected_checker_calls": case["checker_calls"]})
        save_once(cls.root / "controls.freeze.json", encoded({"cases": plan, "source_hex": SOURCE.hex(),
                  "literal_partitions": [{"start": a, "end": b, "raw_hex": raw.hex()} for a, b, raw in PARTITIONS],
                  "expected_artifact_hex": GOOD_ARTIFACT.hex(), "prior_cohort_replay": False,
                  "capture_producer_ledger_calls": 0, "metadata_is_invented_not_actual_runtime_pin": True}))

    @classmethod
    def tearDownClass(cls):
        save_once(cls.root / "execution-summary.json", encoded({"consumer_calls": cls.consumer_calls,
                  "checker_boundary_calls": cls.checker_calls, "actual_c20_calls": cls.actual_checker_calls,
                  "capture_producer_ledger_calls": 0, "nested_body_seconds": time.perf_counter() - cls.started,
                  "whole_agent_cost": None}))
        if cls.temporary:
            cls.temporary.cleanup()

    def test_frozen_intake_controls(self):
        before = (sys.getrecursionlimit(), sys.get_int_max_str_digits())
        original_checker = consumer.check_line_index
        for case in self.cases:
            with self.subTest(case=case["id"]):
                folder = self.root / case["id"]
                mode = case["checker_mode"]
                inputs = case["inputs"]
                source, artifact = inputs["source_bytes"], inputs["stdout_bytes"]
                quality = QualityResult(True, "matches", sha(SOURCE), len(SOURCE), sha(GOOD_ARTIFACT), len(GOOD_ARTIFACT))
                if mode == "real": effect = original_checker
                elif mode == "error": effect = RuntimeError("invented checker failure")
                elif mode in ("KeyboardInterrupt", "SystemExit"): effect = {"KeyboardInterrupt": KeyboardInterrupt, "SystemExit": SystemExit}[mode]("invented cancellation")
                else:
                    if mode == "unavailable": quality = QualityResult(None, "checker_capacity", quality.source_sha256, quality.source_byte_length, quality.artifact_sha256, quality.artifact_byte_length)
                    if mode == "wrong_identity": quality = QualityResult(True, "matches", "0" * 64, quality.source_byte_length, quality.artifact_sha256, quality.artifact_byte_length)
                    if mode == "integer_quality": quality = QualityResult(1, "matches", quality.source_sha256, quality.source_byte_length, quality.artifact_sha256, quality.artifact_byte_length)
                    if mode == "wrong_type": quality = asdict(quality)
                    effect = lambda *_args, supplied=quality: supplied
                receipt = {"case_id": case["id"], "output_sha256": None, "exception": None}
                with patch.object(consumer, "check_line_index", side_effect=effect) as checker:
                    type(self).consumer_calls += 1
                    began = time.perf_counter()
                    try:
                        output = consumer.assess_captured_artifact(**inputs)
                        save_once(folder / "actual-output.json", output)
                        receipt.update(output_sha256=sha(output), output_byte_length=len(output))
                    except BaseException as error:
                        receipt["exception"] = type(error).__name__
                        if type(error).__name__ != case["exception"]:
                            raise
                    finally:
                        receipt.update(checker_calls=checker.call_count, nested_seconds=time.perf_counter() - began)
                        type(self).checker_calls += checker.call_count
                        if mode == "real": type(self).actual_checker_calls += checker.call_count
                        save_once(folder / "result.json", encoded(receipt))
                    self.assertEqual(checker.call_count, case["checker_calls"])
                    if checker.call_count:
                        self.assertEqual(checker.call_args.args, (source, artifact))
                    self.assertEqual(receipt["exception"], case["exception"])
                    if case["expected"] is not None:
                        self.assertIs(type(output), bytes)
                        self.assertLessEqual(len(output), 4096)
                        self.assertEqual(output, (folder / "expected-output.json").read_bytes())
        self.assertEqual((sys.getrecursionlimit(), sys.get_int_max_str_digits()), before)

    def test_pure_dependency_surface(self):
        # Discovery may legitimately have imported these modules in the parent.
        # Inspect only the fresh interpreter's imports; never clear parent state.
        probe = """
import ast, json, sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from epiphysics import prospective_quality_evidence as consumer
tree = ast.parse(Path(consumer.__file__).read_text())
print(json.dumps({
    'forbidden_modules_imported': [name for name in (
        'epiphysics.prospective_capture', 'epiphysics.prospective_producer',
        'epiphysics.store') if name in sys.modules],
    'from_imports': [node.module for node in ast.walk(tree) if isinstance(node, ast.ImportFrom)]
}, sort_keys=True))
"""
        command = [sys.executable, "-I", "-B", "-c", probe, str(Path(consumer.__file__).resolve().parents[1])]
        began = time.perf_counter()
        try:
            completed = subprocess.run(command, capture_output=True, timeout=10)
        except subprocess.TimeoutExpired as error:
            save_once(self.root / "dependency-probe.stdout", error.stdout or b"")
            save_once(self.root / "dependency-probe.stderr", error.stderr or b"")
            save_once(self.root / "dependency-probe-process.json", encoded({
                "returncode": None, "timed_out": True, "timeout_seconds": 10,
                "nested_subprocess_seconds": time.perf_counter() - began}))
            raise
        save_once(self.root / "dependency-probe.stdout", completed.stdout)
        save_once(self.root / "dependency-probe.stderr", completed.stderr)
        save_once(self.root / "dependency-probe-process.json", encoded({
            "returncode": completed.returncode, "timed_out": False, "timeout_seconds": 10,
            "nested_subprocess_seconds": time.perf_counter() - began}))
        self.assertEqual(completed.returncode, 0, completed.stderr.decode(errors="replace"))
        observed = json.loads(completed.stdout)
        save_once(self.root / "dependency-control.json", encoded(observed))
        self.assertEqual(observed, {"forbidden_modules_imported": [],
                                  "from_imports": ["dataclasses", "datetime", "prospective_quality"]})


if __name__ == "__main__":
    unittest.main()
