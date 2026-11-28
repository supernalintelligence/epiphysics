"""Owned receipt/ledger controls. No actual task, producer or prior study runs."""
import base64
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from epiphysics import dated_delivery as delivery
from epiphysics import dated_delivery_verifier as verifier
from epiphysics import decision_diagnosis as diagnosis
from epiphysics.store import Ledger
from test_decision_diagnosis import make_study as make_c8, identity, calls_named


def raw(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def checkpoint(event):
    return {"seq": event["seq"], **identity(event)}


def append_completion(ledger, prepared, measured, run_key):
    observations = {}
    for role, content in prepared["artifacts"].items():
        full_role = "decision-input:" + role
        event = ledger.capture("improvement-input:" + full_role, content, event_id="improvement:" + run_key + ":input:" + full_role)
        observations[full_role] = event["id"]
    for role, content in measured["artifacts"].items():
        if role not in prepared["artifacts"]:
            full_role = "decision-result:" + role
            event = ledger.capture("improvement-input:" + full_role, content, event_id="improvement:" + run_key + ":input:" + full_role)
            observations[full_role] = event["id"]
    manifest = {"decision-input:" + role: value for role, value in prepared["manifest"].items()}
    report = measured["report"]
    assessment = {"input_manifest": manifest, "decision_assessment_hash": report["assessment_identity"]["hash"]}
    assessment["hash"] = digest(raw(assessment))
    step = {"id": run_key + ":next", "action": report["next_step"]["action"], "state": "queued", "scale_change_allowed": False, "live_effects_allowed": False}
    return ledger.append("improvement_completed", {"run_key": run_key, "result": "assessed",
        "request": {"manifest": manifest, "after_step": prepared["report"]["origin"]["step_id"]},
        "input_observations": observations, "assessment_identity": assessment,
        "report": {"decision_pilot": report}, "next_step": step}, "improvement:" + run_key + ":complete")


def make_study(directory):
    """Return open ledger/request/path with owned accepted C9-shaped provenance.

    Uses the existing exposed C8 transport fixture, never its worker/generator,
    and synthesizes the accepted C9 receipt shape without running diagnosis.
    Caller must close result['ledger']; all bytes live under directory.
    """
    directory = Path(directory).resolve()
    original = make_c8(directory / "history")
    ledger = original["ledger"]
    origin_identity = diagnosis._origin_identity(original["origin"])
    table = raw({"owned_fixture": True, "attempts": []})
    inputs = {"c8:" + role: content for role, content in original["artifacts"].items()}
    inputs.update({"code:epiphysics." + name[:-3]: (Path(diagnosis.__file__).parent / name).read_bytes() for name in diagnosis.SOURCE_NAMES})
    inputs.update(request=raw(original["request"]), contract=raw(diagnosis.CONTRACT))
    manifest = {role: digest(content) for role, content in inputs.items()}
    report = {"schema_version": 1, "status": "checked", "contract_id": diagnosis.CONTRACT_ID,
        "study_id": "owned-c9", "phase": diagnosis.PHASE, "stage": diagnosis.STAGE,
        "origin": {"step_id": original["origin"]["body"]["next_step"]["id"]},
        "assessment_identity": {"schema_version": 1, "hash": digest(raw(manifest))},
        "input_hashes": {role: value for role, value in manifest.items() if not role.startswith("code:")},
        "source_hashes": {name: manifest["code:epiphysics." + name[:-3]] for name in diagnosis.SOURCE_NAMES},
        "evidence_origin": origin_identity, "checks": {"owned_fixture": True},
        "diagnosis": {"detail_sha256": digest(table), "detail_bytes": len(table)},
        "next_step": {"action": "prepare_dated_evidence_quality_protocol"}}
    c9 = append_completion(ledger, {"artifacts": inputs, "manifest": manifest, "report": report},
        {"report": report, "artifacts": {**inputs, "assessment_report": raw(report), "diagnostic_table": table}}, "owned-c9")
    paths = {}
    for name, content in (("contract", raw(delivery.CONTRACT)), ("criteria", raw(verifier.CRITERIA)),
                          ("validation", b"Owned bounded validation receipt: controls passed\n")):
        path = directory / (name + ".json")
        path.write_bytes(content)
        paths[name] = str(path)
    stdout, stderr = b"", b"Ran 1 test in 0.001s\n\nOK\n"
    for name, content in (("validation_stdout", stdout), ("validation_stderr", stderr)):
        path = directory / (name + ".txt")
        path.write_bytes(content)
        paths[name] = str(path)
    execution = {"schema_version": 1, "command": ["owned-fixture", "-m", "unittest", "test_dated_delivery", "test_dated_delivery_verifier"],
        "test_modules": ["test_dated_delivery", "test_dated_delivery_verifier"],
        "source_hashes": {name: digest((Path(delivery.__file__).parent / name).read_bytes()) for name in delivery.SOURCE_NAMES},
        "test_hashes": {name: digest((Path(__file__).parent / name).read_bytes()) for name in ("test_dated_delivery.py", "test_dated_delivery_verifier.py")},
        "started_at": "2000-01-01T00:00:00+00:00", "ended_at": "2000-01-01T00:00:01+00:00", "elapsed_seconds": .001,
        "returncode": 0, "tests_run": 1, "stdout_sha256": digest(stdout), "stderr_sha256": digest(stderr)}
    Path(paths["validation"]).write_bytes(raw(execution))
    packet = {"schema_version": 1, "phase": delivery.PREPARATION,
        "validation": {"status": "passed", "tests": 1, "exit_code": 0,
            "source_hashes": {name: digest((Path(delivery.__file__).parent / name).read_bytes()) for name in delivery.SOURCE_NAMES},
            "receipt_sha256": digest(Path(paths["validation"]).read_bytes())}}
    packet_path = directory / "packet.json"
    packet_path.write_bytes(raw(packet))
    paths["packet"] = str(packet_path)
    request = {"schema_version": 1, "study_id": "owned-dated", "phase": delivery.PREPARATION,
        "origin": {"step_id": c9["body"]["next_step"]["id"]}, "ledger_path": str(ledger.root),
        "evidence_origin": identity(c9), "queue_parent": identity(c9), "evidence_checkpoint": checkpoint(c9), "paths": paths}
    request_path = directory / "request.json"
    request_path.write_bytes(raw(request))
    return {"ledger": ledger, "request": request, "request_path": request_path, "origin": c9,
        "queue_parent": c9, "directory": directory, "packet": packet, "c8": original}


def write_request(study, phase, parent, packet, checkpoint_event=None):
    request = deepcopy(study["request"])
    request.update(phase=phase, origin={"step_id": parent["body"]["next_step"]["id"]}, queue_parent=identity(parent),
        evidence_checkpoint=checkpoint(checkpoint_event or study["ledger"].events()[-1]))
    if phase != delivery.PREPARATION:
        for name in ("validation", "validation_stdout", "validation_stderr"):
            request["paths"].pop(name, None)
    Path(request["paths"]["packet"]).write_bytes(raw(packet))
    study["request_path"].write_bytes(raw(request))
    study.update(request=request, packet=packet, queue_parent=parent)
    return study["request_path"]


def git_fixture(source=b"See [target](target.md#heading).\n"):
    """Tiny complete binary Git tree, built from owned literal bytes only."""
    objects = []
    def put(kind, data):
        oid = hashlib.sha1(kind.encode() + b" " + str(len(data)).encode() + b"\0" + data).hexdigest()
        objects.append({"object_id": oid, "type": kind, "data_base64": base64.b64encode(data).decode()})
        return oid
    def tree(entries):
        return put("tree", b"".join(mode.encode() + b" " + name.encode() + b"\0" + bytes.fromhex(oid) for mode, name, oid in entries))
    source_oid, target_oid = put("blob", source), put("blob", b"Owned target\n")
    theory = tree([("100644", "a.md", source_oid), ("100644", "target.md", target_oid)])
    docs = tree([("40000", "theory", theory)])
    root = tree([("40000", "docs", docs)])
    commit = put("commit", ("tree " + root + "\nauthor Owned <owned@example.invalid> 0 +0000\ncommitter Owned <owned@example.invalid> 0 +0000\n\nOwned fixture\n").encode())
    manifest = {"schema_version": 1, "source_commit": commit, "entries": [
        {"path": "docs", "mode": "040000", "object_id": docs},
        {"path": "docs/theory", "mode": "040000", "object_id": theory},
        {"path": "docs/theory/a.md", "mode": "100644", "object_id": source_oid},
        {"path": "docs/theory/target.md", "mode": "100644", "object_id": target_oid}]}
    return source, manifest, {"schema_version": 1, "objects": objects}


def register_study(study, protocol_event=None, *, accept_registration=True):
    protocol = protocol_event
    if protocol is None:
        prepared = delivery.prepare_dated_delivery(study["request_path"])
        measured = delivery.assess_prepared_dated_delivery(prepared)
        protocol = append_completion(study["ledger"], prepared, measured, "owned-protocol")
    source, manifest, proof = git_fixture()
    backlog = b"- Update cross-references in theory docs\n"
    selection = {"schema_version": 1, "selected_path": "docs/theory/a.md", "candidate_paths": ["docs/theory/a.md", "docs/theory/target.md"],
        "exclusions": {}, "eligible_count": 1, "backlog_span": {"start": 0, "end": len(backlog), "sha256": digest(backlog)}}
    inputs = {"source": source, "tree_manifest": raw(manifest), "git_objects": raw(proof), "backlog": backlog,
        "selection": raw(selection), "authority": raw({"task_id": "owned-links", "registration_id": "owned-registration",
            "grantor": "requester", "subject": "producer", "actions": ["submit"], "effective_at": "2000-01-01T00:00:00+00:00",
            "expires_at": None, "revoked": False})}
    observations = {}
    for role, content in inputs.items():
        event = study["ledger"].capture("improvement-input:dated-delivery:owned-registration:input:" + role, content, event_id="owned:input:" + role)
        observations[role] = event["id"]
    registration = {"schema_version": 1, "task_id": "owned-links", "registration_id": "owned-registration",
        "protocol_sha256": digest(raw(delivery.CONTRACT)), "criteria_sha256": digest(raw(verifier.CRITERIA)),
        "source_commit": manifest["source_commit"], "source_path": "docs/theory/a.md", "source_sha256": digest(source),
        "tree_manifest_sha256": digest(raw(manifest)), "input_observations": observations,
        "roles": {"requester": "requester", "producer": "producer", "verifier": "checker", "adjudicator": "reviewer"},
        "exposure": {"basis": "Owned synthetic test; no actual task", "prior_delivery": False, "external_witness": None}}
    packet = {"schema_version": 1, "phase": delivery.REGISTRATION, "registration": registration}
    write_request(study, delivery.REGISTRATION, protocol, packet)
    accepted = None
    if accept_registration:
        prepared = delivery.prepare_dated_delivery(study["request_path"])
        measured = delivery.assess_prepared_dated_delivery(prepared)
        accepted = append_completion(study["ledger"], prepared, measured, "owned-registration")
    study.update(registration=registration, registration_event=accepted, source=source, tree_manifest=manifest)
    return study


def inventory_bytes(study):
    registration = study["registration"]
    expected = verifier.verify_inventory(registration, study["source"], study["tree_manifest"], b"{}")
    value = {key: registration[key] for key in ("schema_version", "task_id", "registration_id", "protocol_sha256", "criteria_sha256", "source_commit", "source_path", "source_sha256")}
    tokens = verifier.inspect_source(study["source"])["expected_tokens"]
    directory = registration["source_path"].split("/")[:-1]
    for token, row in zip(tokens, expected["expected_tokens"]):
        start, end, shared, suffix, status = row
        assert (token["start"], token["end"]) == (start, end)
        token.update(target=None if shared is None else "/".join(directory[:shared] + ([suffix] if suffix else [])), target_status=status)
    value.update(links=tokens, unsupported=expected["unsupported_tokens"], summary=expected["expected_summary"])
    return raw(value)


def capture(study, kind, value, name=None, at=None):
    content = value if type(value) is bytes else raw(value)
    if at is None:
        return study["ledger"].capture("improvement-input:dated-delivery:owned-registration:" + kind, content, event_id="owned:" + (name or kind))
    with patch.object(study["ledger"], "clock", return_value=at.isoformat()):
        return study["ledger"].capture("improvement-input:dated-delivery:owned-registration:" + kind, content, event_id="owned:" + (name or kind))


def deliver(study, content=None, *, artifact_at=None, verification_effective_at=None, adjudication_at=None):
    if content is None:
        content = inventory_bytes(study)
    registration = study["registration"]
    artifact = capture(study, "inventory", content, at=artifact_at)
    bindings = {"schema_version": 1, "task_id": registration["task_id"], "registration_id": registration["registration_id"], "artifact_sha256": digest(content)}
    capture(study, "claim", {**bindings, "actor": "producer", "criteria_sha256": registration["criteria_sha256"], "verdict": "pass"},
        at=None if artifact_at is None else artifact_at + timedelta(seconds=1))
    result = verifier.verify_inventory(registration, study["source"], study["tree_manifest"], content)
    receipt = {**bindings, "actor": "checker", "criteria_sha256": registration["criteria_sha256"],
        "verifier_sha256": digest(Path(verifier.__file__).read_bytes()), "environment_sha256": "a" * 64,
        "started_at": artifact["recorded_at"], "ended_at": (datetime.now(timezone.utc) if artifact_at is None else artifact_at + timedelta(seconds=2)).isoformat(), "elapsed_seconds": 0.0, "result": result, "error": None}
    if verification_effective_at is not None:
        receipt["effective_at"] = verification_effective_at
    checked = capture(study, "verification", receipt, at=None if artifact_at is None else artifact_at + timedelta(seconds=2))
    capture(study, "adjudication", {**bindings, "actor": "reviewer", "verification_observation": checked["id"], "verdict": result["verdict"]},
        at=adjudication_at if adjudication_at is not None else None if artifact_at is None else artifact_at + timedelta(seconds=3))
    packet = {"schema_version": 1, "phase": delivery.CHECK, "registration_event": identity(study["registration_event"]), "closure_observation": None}
    write_request(study, delivery.CHECK, study["registration_event"], packet)
    return artifact


class DatedDeliveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.study = make_study(self.temp.name)
        self.addCleanup(self.study["ledger"].close)
        self.addCleanup(self.temp.cleanup)

    def test_preparation_retains_origin_and_has_no_task_or_verifier(self):
        with calls_named({"verify_inventory", "_diagnose", "run_fresh_comparison", "build_case"}) as calls:
            prepared = delivery.prepare_dated_delivery(self.study["request_path"])
            result = delivery.assess_prepared_dated_delivery(prepared)
            delivery.check_prepared_dated_delivery(prepared)
        self.assertEqual(calls, [])
        self.assertIsNone(result["report"]["registration"])
        self.assertIsNone(result["report"]["outcome"]["artifact_quality"])
        self.assertEqual(result["report"]["next_step"]["action"], "bind_dated_artifact_delivery")
        self.assertIsNone(result["actual_resources"]["first_verification_elapsed_seconds"])
        self.assertEqual(len(result["report"]["evidence_origin"]["c8_evidence_origin"]["input_manifest"]), 21)

    def test_preparation_replay_is_fixed_after_unrelated_observation(self):
        before = delivery.prepare_dated_delivery(self.study["request_path"])
        self.study["ledger"].capture("improvement-input:unrelated", b"later")
        after = delivery.prepare_dated_delivery(self.study["request_path"])
        self.assertEqual(before, after)
        delivery.validate_lineage(after, self.study["ledger"].events(), self.study["request"]["origin"]["step_id"])

    def test_origin_output_blob_corruption_refuses(self):
        event = self.study["origin"]
        observation_id = event["body"]["input_observations"]["decision-result:diagnostic_table"]
        observation = next(item for item in self.study["ledger"].events() if item["id"] == observation_id)
        (self.study["ledger"].root / "blobs" / observation["body"]["content_hash"]).write_bytes(b"wrong")
        with self.assertRaises(delivery.PreparationError):
            delivery.prepare_dated_delivery(self.study["request_path"])

    def test_failed_validation_is_checked_protocol_repair(self):
        packet = self.study["packet"]
        packet["validation"].update(status="failed", exit_code=1)
        receipt_path = Path(self.study["request"]["paths"]["validation"])
        receipt = json.loads(receipt_path.read_bytes())
        receipt["returncode"] = 1
        receipt_path.write_bytes(raw(receipt))
        packet["validation"]["receipt_sha256"] = digest(raw(receipt))
        Path(self.study["request"]["paths"]["packet"]).write_bytes(raw(packet))
        result = delivery.assess_prepared_dated_delivery(delivery.prepare_dated_delivery(self.study["request_path"]))
        self.assertFalse(result["report"]["checks"]["protocol_conformance"])
        self.assertEqual(result["report"]["next_step"]["action"], "repair_dated_evidence_quality_protocol")

    def test_registered_first_delivery_checks_and_checkpoint_is_later(self):
        register_study(self.study)
        artifact = deliver(self.study)
        prepared = delivery.prepare_dated_delivery(self.study["request_path"])
        result = delivery.assess_prepared_dated_delivery(prepared)
        self.assertGreater(prepared["report"]["evidence_checkpoint"]["seq"], self.study["registration_event"]["seq"])
        self.assertEqual(result["report"]["outcome"]["first_submission"]["observation_id"], artifact["id"])
        self.assertTrue(result["report"]["outcome"]["artifact_quality"])
        self.assertEqual(result["report"]["outcome"]["claim_agreement"]["denominator"], 1)
        self.assertEqual(result["report"]["next_step"]["action"], "prepare_public_research_map_view")
        self.assertIsNotNone(result["actual_resources"]["first_verification_elapsed_seconds"])

    def test_malformed_first_artifact_is_negative_and_correction_not_replacement(self):
        register_study(self.study)
        first = deliver(self.study, b'{"schema_version":1,"schema_version":1}')
        capture(self.study, "inventory", inventory_bytes(self.study), "correction")
        write_request(self.study, delivery.CHECK, self.study["registration_event"], self.study["packet"])
        measured = delivery.assess_prepared_dated_delivery(delivery.prepare_dated_delivery(self.study["request_path"]))
        self.assertFalse(measured["report"]["outcome"]["artifact_quality"])
        self.assertEqual(measured["report"]["outcome"]["first_submission"]["observation_id"], first["id"])
        self.assertEqual(measured["report"]["outcome"]["claim_agreement"], {"numerator": 0, "denominator": 1, "value": 0.0})

    def test_checkpoint_cannot_omit_scoped_capture(self):
        register_study(self.study)
        deliver(self.study)
        prepared = delivery.prepare_dated_delivery(self.study["request_path"])
        capture(self.study, "claim", b"late receipt", "later-claim")
        with self.assertRaisesRegex(ValueError, "omits later scoped"):
            delivery.validate_lineage(prepared, self.study["ledger"].events(), self.study["request"]["origin"]["step_id"])

    def test_no_delivery_terminal_closure(self):
        register_study(self.study)
        event = self.study["registration_event"]
        at = datetime.fromisoformat(event["recorded_at"]) + timedelta(hours=24)
        closure = capture(self.study, "closure", {"schema_version": 1, "task_id": "owned-links", "registration_id": "owned-registration",
            "actor": "reviewer", "state": "no_delivery", "missing": ["artifact"]}, at=at)
        packet = {"schema_version": 1, "phase": delivery.CHECK, "registration_event": identity(event), "closure_observation": closure["id"]}
        write_request(self.study, delivery.CHECK, event, packet)
        result = delivery.assess_prepared_dated_delivery(delivery.prepare_dated_delivery(self.study["request_path"]))
        self.assertEqual(result["report"]["outcome"]["status"], "no_delivery")
        self.assertEqual(result["report"]["outcome"]["claim_agreement"]["denominator"], 0)
        self.assertIsNone(result["report"]["outcome"]["artifact_quality"])
        self.assertEqual(result["report"]["next_step"]["action"], "prepare_public_research_map_view")

    def test_unresolved_review_closes_once_without_quality_invention(self):
        register_study(self.study)
        event = self.study["registration_event"]
        capture(self.study, "inventory", inventory_bytes(self.study))
        at = datetime.fromisoformat(event["recorded_at"]) + timedelta(hours=48)
        closure_value = {"schema_version": 1, "task_id": "owned-links", "registration_id": "owned-registration", "actor": "reviewer",
            "state": "unresolved", "missing": ["verification", "adjudication"]}
        closure = capture(self.study, "closure", closure_value, at=at)
        packet = {"schema_version": 1, "phase": delivery.CHECK, "registration_event": identity(event), "closure_observation": closure["id"]}
        write_request(self.study, delivery.CHECK, event, packet)
        prepared = delivery.prepare_dated_delivery(self.study["request_path"])
        result = delivery.assess_prepared_dated_delivery(prepared)
        with patch.object(self.study["ledger"], "clock", return_value=(at + timedelta(seconds=1)).isoformat()):
            checked = append_completion(self.study["ledger"], prepared, result, "owned-check")
        self.assertEqual(result["report"]["next_step"]["action"], "review_dated_delivery_evidence")
        closure_value["review_of"] = identity(checked)
        review = capture(self.study, "closure", closure_value, "review-closure", at + timedelta(seconds=2))
        packet.update(phase=delivery.REVIEW, closure_observation=review["id"])
        write_request(self.study, delivery.REVIEW, checked, packet)
        next_result = delivery.assess_prepared_dated_delivery(delivery.prepare_dated_delivery(self.study["request_path"]))
        self.assertEqual(next_result["report"]["next_step"]["action"], "prepare_public_research_map_view")
        self.assertEqual(next_result["report"]["outcome"]["status"], "terminal_unresolved")
        self.assertIsNone(next_result["report"]["outcome"]["artifact_quality"])
        self.assertEqual(next_result["report"]["outcome"]["claim_agreement"]["denominator"], 0)


    def test_validation_claim_without_bound_process_output_refuses(self):
        Path(self.study["request"]["paths"]["validation_stderr"]).write_bytes(b"passed\n")
        with self.assertRaisesRegex(delivery.PreparationError, "validation output"):
            delivery.prepare_dated_delivery(self.study["request_path"])

    def test_incomplete_git_manifest_cannot_prove_missing_target(self):
        source, manifest, proof = git_fixture()
        registration = {"source_commit": manifest["source_commit"], "source_path": "docs/theory/a.md", "source_sha256": digest(source)}
        manifest["entries"].pop()
        with self.assertRaisesRegex(ValueError, "Complete retained Git tree"):
            delivery._git_proof(registration, manifest, proof, source)

    def test_invalid_utf8_first_delivery_is_criterion_negative(self):
        register_study(self.study)
        deliver(self.study, b"\xff")
        result = delivery.assess_prepared_dated_delivery(delivery.prepare_dated_delivery(self.study["request_path"]))
        self.assertFalse(result["report"]["outcome"]["artifact_quality"])
        self.assertEqual(result["report"]["next_step"]["action"], "prepare_public_research_map_view")

    def test_oversize_prefix_never_becomes_complete_artifact_hash(self):
        register_study(self.study)
        prefix = b"x" * (delivery.MAX_INVENTORY_BYTES + 1)
        observed = capture(self.study, "overflow_prefix", prefix)
        receipt = {"schema_version": 1, "task_id": "owned-links", "registration_id": "owned-registration",
            "retained_bytes": len(prefix), "prefix_sha256": digest(prefix), "prefix_observation": observed["id"],
            "truncated": True, "observed_bytes_lower_bound": len(prefix), "complete_sha256": None}
        capture(self.study, "oversize", receipt)
        capture(self.study, "inventory", inventory_bytes(self.study), "later-good")
        packet = {"schema_version": 1, "phase": delivery.CHECK, "registration_event": identity(self.study["registration_event"]), "closure_observation": None}
        write_request(self.study, delivery.CHECK, self.study["registration_event"], packet)
        result = delivery.assess_prepared_dated_delivery(delivery.prepare_dated_delivery(self.study["request_path"]))
        outcome = result["report"]["outcome"]
        self.assertEqual(outcome["status"], "rejected_over_limit")
        self.assertIsNone(outcome["first_submission"]["artifact_sha256"])
        self.assertEqual(outcome["claim_agreement"]["denominator"], 0)
        self.assertIsNone(result["actual_resources"]["first_verification_elapsed_seconds"])

    def test_future_effective_revocation_visible_but_inert(self):
        register_study(self.study)
        deliver(self.study)
        cutoff = datetime.fromisoformat(self.study["registration_event"]["recorded_at"]) + timedelta(hours=24)
        record = {"task_id": "owned-links", "registration_id": "owned-registration", "grantor": "requester", "subject": "producer",
            "actions": ["submit"], "effective_at": (cutoff + timedelta(seconds=1)).isoformat(), "expires_at": None, "revoked": True}
        capture(self.study, "authority", record)
        write_request(self.study, delivery.CHECK, self.study["registration_event"], self.study["packet"])
        result = delivery.assess_prepared_dated_delivery(delivery.prepare_dated_delivery(self.study["request_path"]))
        self.assertTrue(result["report"]["outcome"]["authority"]["producer"]["effective_permission"])
        self.assertIsNone(result["report"]["outcome"]["authority"]["verifier"]["effective_permission"])
        self.assertEqual(result["report"]["outcome"]["witness"], {"status": "none", "proof": None, "time_bound": None})


    def test_primary_cutoff_boundary_and_late_first_do_not_rescue_outcome(self):
        for offset, malformed in ((0, False), (1, False), (1, True)):
            with self.subTest(offset=offset, malformed=malformed), tempfile.TemporaryDirectory() as directory:
                study = make_study(directory)
                try:
                    register_study(study)
                    cutoff = datetime.fromisoformat(study["registration_event"]["recorded_at"]) + timedelta(hours=24)
                    first = deliver(study, b'{"broken":true}' if malformed else None,
                        artifact_at=cutoff + timedelta(seconds=offset))
                    if offset:
                        with self.assertRaisesRegex(delivery.PreparationError, "deadline closure"):
                            delivery.prepare_dated_delivery(study["request_path"])
                        closure = capture(study, "closure", {"schema_version": 1, "task_id": "owned-links", "registration_id": "owned-registration",
                            "actor": "reviewer", "state": "no_delivery", "missing": ["artifact"]}, at=cutoff + timedelta(seconds=5))
                        study["packet"]["closure_observation"] = closure["id"]
                        write_request(study, delivery.CHECK, study["registration_event"], study["packet"])
                    with calls_named({"verify_inventory"}) as called:
                        prepared = delivery.prepare_dated_delivery(study["request_path"])
                        measured = delivery.assess_prepared_dated_delivery(prepared)
                    outcome = measured["report"]["outcome"]
                    if offset:
                        self.assertEqual(called, [])
                        self.assertEqual(outcome["status"], "no_delivery")
                        self.assertIsNone(outcome["first_submission"])
                        self.assertEqual(outcome["late_submission"]["observation_id"], first["id"])
                        self.assertIsNone(outcome["artifact_quality"])
                        self.assertEqual(outcome["claim_agreement"], {"numerator": 0, "denominator": 0, "value": None})
                    else:
                        self.assertTrue(outcome["delivery_timely"])
                        self.assertTrue(outcome["artifact_quality"])
                finally:
                    study["ledger"].close()

    def test_verification_effective_time_at_each_boundary(self):
        for effective_offset in (24, 36, 49):
            with self.subTest(hours=effective_offset), tempfile.TemporaryDirectory() as directory:
                study = make_study(directory)
                try:
                    register_study(study)
                    registered = datetime.fromisoformat(study["registration_event"]["recorded_at"])
                    deliver(study, artifact_at=registered + timedelta(seconds=1),
                        verification_effective_at=(registered + timedelta(hours=effective_offset)).isoformat(),
                        adjudication_at=registered + timedelta(hours=effective_offset) if effective_offset <= 48 else None)
                    if effective_offset > 48:
                        with self.assertRaisesRegex(delivery.PreparationError, "fixed-deadline closure"):
                            delivery.prepare_dated_delivery(study["request_path"])
                        closure = capture(study, "closure", {"schema_version": 1, "task_id": "owned-links", "registration_id": "owned-registration",
                            "actor": "reviewer", "state": "unresolved", "missing": ["verification", "adjudication"]}, at=registered + timedelta(hours=48))
                        study["packet"]["closure_observation"] = closure["id"]
                        write_request(study, delivery.CHECK, study["registration_event"], study["packet"])
                    measured = delivery.assess_prepared_dated_delivery(delivery.prepare_dated_delivery(study["request_path"]))
                    outcome = measured["report"]["outcome"]
                    self.assertEqual(outcome["verification_available_by_cutoff"], effective_offset == 24)
                    if effective_offset > 48:
                        self.assertEqual(outcome["status"], "unresolved")
                        self.assertIsNone(outcome["artifact_quality"])
                        self.assertEqual(outcome["claim_agreement"]["denominator"], 0)
                    else:
                        self.assertTrue(outcome["artifact_quality"])
                        self.assertEqual(outcome["claim_agreement"]["denominator"], 1)
                finally:
                    study["ledger"].close()

    def test_unsubstantiated_overflow_and_bad_order_refuse_without_verifier(self):
        for size, lower_bound, late_prefix in ((0, delivery.MAX_INVENTORY_BYTES + 1, False),
                (5, delivery.MAX_INVENTORY_BYTES + 1, False),
                (delivery.MAX_INVENTORY_BYTES + 1, delivery.MAX_INVENTORY_BYTES + 2, False),
                (delivery.MAX_INVENTORY_BYTES + 1, delivery.MAX_INVENTORY_BYTES + 1, True)):
            with self.subTest(size=size, lower=lower_bound, late=late_prefix), tempfile.TemporaryDirectory() as directory:
                study = make_study(directory)
                try:
                    register_study(study)
                    prefix = b"x" * size
                    prefix_id = "owned:overflow_prefix"
                    receipt = {"schema_version": 1, "task_id": "owned-links", "registration_id": "owned-registration", "retained_bytes": size,
                        "prefix_sha256": digest(prefix), "prefix_observation": prefix_id, "truncated": True,
                        "observed_bytes_lower_bound": lower_bound, "complete_sha256": None}
                    if not late_prefix:
                        capture(study, "overflow_prefix", prefix)
                    capture(study, "oversize", receipt)
                    if late_prefix:
                        capture(study, "overflow_prefix", prefix)
                    packet = {"schema_version": 1, "phase": delivery.CHECK, "registration_event": identity(study["registration_event"]), "closure_observation": None}
                    write_request(study, delivery.CHECK, study["registration_event"], packet)
                    before = study["ledger"].events()
                    with calls_named({"verify_inventory"}) as called, self.assertRaises(delivery.PreparationError):
                        delivery.prepare_dated_delivery(study["request_path"])
                    self.assertEqual(called, [])
                    self.assertEqual(study["ledger"].events(), before)
                finally:
                    study["ledger"].close()

    def test_prefix_before_registration_is_not_a_future_delivery(self):
        register_study(self.study, accept_registration=False)
        capture(self.study, "overflow_prefix", b"x" * (delivery.MAX_INVENTORY_BYTES + 1))
        parent = self.study["queue_parent"]
        write_request(self.study, delivery.REGISTRATION, parent, self.study["packet"])
        with self.assertRaisesRegex(delivery.PreparationError, "submission before registration"):
            delivery.prepare_dated_delivery(self.study["request_path"])

    def test_control_boolean_versions_and_verifier_input_contract_refuse(self):
        register_study(self.study, accept_registration=False)
        packet = deepcopy(self.study["packet"])
        packet["registration"]["schema_version"] = True
        Path(self.study["request"]["paths"]["packet"]).write_bytes(raw(packet))
        with calls_named({"verify_inventory"}) as called, self.assertRaisesRegex(delivery.PreparationError, "registration version"):
            delivery.prepare_dated_delivery(self.study["request_path"])
        self.assertEqual(called, [])
        packet["registration"]["schema_version"] = 1
        packet["schema_version"] = True
        Path(self.study["request"]["paths"]["packet"]).write_bytes(raw(packet))
        with self.assertRaisesRegex(delivery.PreparationError, "phase packet"):
            delivery.prepare_dated_delivery(self.study["request_path"])
        packet["schema_version"] = 1
        packet["registration"]["source_path"] = "docs/theory/../theory/a.md"
        Path(self.study["request"]["paths"]["packet"]).write_bytes(raw(packet))
        with self.assertRaisesRegex(delivery.PreparationError, "Registration source identity"):
            delivery.prepare_dated_delivery(self.study["request_path"])

    def test_lone_surrogate_revision_is_retained_negative_with_safe_metadata(self):
        register_study(self.study)
        first = deliver(self.study, b'{"revision_of":"\\ud800"}')
        measured = delivery.assess_prepared_dated_delivery(delivery.prepare_dated_delivery(self.study["request_path"]))
        outcome = measured["report"]["outcome"]
        self.assertFalse(outcome["artifact_quality"])
        row = next(row for row in outcome["dated_records"] if row["observation_id"] == first["id"])
        self.assertIsNone(row["revision_of"])
        self.assertIn("revision_of", row["invalid_declared_fields"])
        self.assertEqual(measured["artifacts"]["blob:" + digest(b'{"revision_of":"\\ud800"}')], b'{"revision_of":"\\ud800"}')
        self.assertFalse(delivery._operative({"effective_at": {}}, datetime.now(timezone.utc)))

    def test_known_incomplete_checks_refuse_in_preparation_without_verifier(self):
        for kind in ("missing", "inventory", "premature_closure"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as directory:
                study = make_study(directory)
                try:
                    register_study(study)
                    event = study["registration_event"]
                    closure_id = None
                    if kind == "inventory":
                        capture(study, "inventory", inventory_bytes(study))
                    elif kind == "premature_closure":
                        closure = capture(study, "closure", {"schema_version": 1, "task_id": "owned-links", "registration_id": "owned-registration",
                            "actor": "reviewer", "state": "no_delivery", "missing": ["artifact"]},
                            at=datetime.fromisoformat(event["recorded_at"]) + timedelta(hours=23))
                        closure_id = closure["id"]
                    packet = {"schema_version": 1, "phase": delivery.CHECK, "registration_event": identity(event), "closure_observation": closure_id}
                    write_request(study, delivery.CHECK, event, packet)
                    before = study["ledger"].events()
                    with calls_named({"verify_inventory"}) as called, self.assertRaisesRegex(delivery.PreparationError, "closure"):
                        delivery.prepare_dated_delivery(study["request_path"])
                    self.assertEqual(called, [])
                    self.assertEqual(study["ledger"].events(), before)
                finally:
                    study["ledger"].close()

    def test_registration_binds_original_contract_and_criteria_bytes(self):
        register_study(self.study, accept_registration=False)
        original_packet = deepcopy(self.study["packet"])
        for role, binding in (("contract", "protocol_sha256"), ("criteria", "criteria_sha256")):
            with self.subTest(role=role):
                path = Path(self.study["request"]["paths"][role])
                original = path.read_bytes()
                changed = original + b"\n"
                path.write_bytes(changed)
                packet = deepcopy(original_packet)
                packet["registration"][binding] = digest(changed)
                Path(self.study["request"]["paths"]["packet"]).write_bytes(raw(packet))
                with self.assertRaisesRegex(delivery.PreparationError, "Accepted preparation " + role + " bytes"):
                    delivery.prepare_dated_delivery(self.study["request_path"])
                path.write_bytes(original)


if __name__ == "__main__":
    unittest.main()
