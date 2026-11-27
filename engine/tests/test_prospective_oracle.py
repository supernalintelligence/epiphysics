"""Invented raw fixtures and hand-declared expected query values/support.

No candidate implementation, normalized packet, view, producer, store or prior
study data is imported. ORACLE_EVIDENCE_DIR retains exact cases and process outputs
for this engineering run; it is never read by the oracle under test.
"""

import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from datetime import datetime, timedelta, timezone

from epiphysics.prospective_oracle import OracleUnavailable, expected_queries_from_raw_sources


PIN = "ed9f98c0155d41e67a5c1fd38b9f1d5075fdf829eea6133faf48ec16d4cf7f65"
URL = "https://api.github.com/repos/modelcontextprotocol/python-sdk/releases?per_page=5"
HEADERS = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "Accept-Encoding": "identity", "User-Agent": "Epiphysics-Prospective-Integrity-Pilot-v1"}
SOURCE = ("# Invented oracle fixture\r\n" + "αβ raw source bytes. " * 20 + "\n").encode("utf-8")


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def instant(seconds):
    return (datetime(2026, 12, 1, tzinfo=timezone.utc) + timedelta(seconds=seconds)).isoformat(timespec="microseconds").replace("+00:00", "Z")


def receipt(ident, kind, raw, start, observed=None, retained=None):
    observed = start + 1 if observed is None else observed
    retained = observed + 1 if retained is None else retained
    return {
        "id": ident, "kind": kind, "content_sha256": digest(raw),
        "retained_byte_length": len(raw), "observed_byte_length": len(raw), "complete": True,
        "observed_at": instant(observed), "validated_at": instant(retained), "retained_at": instant(retained),
        "time_basis": "local_clock",
        "clock": {"start_utc": instant(start), "start_ns": 100,
                  "observed_ns": 100 + (observed - start) * 1_000_000_000,
                  "validated_ns": 100 + (retained - start) * 1_000_000_000,
                  "retained_ns": 100 + (retained - start) * 1_000_000_000,
                  "start_epoch": "invented-epoch", "end_epoch": "invented-epoch"},
    }


def sample(ident, slot, raw, start, headers=b"[]", observed=None, retained=None):
    r = receipt(ident, "release_sample", raw, start, observed, retained)
    r.update(slot_id=slot, http={"request_url": URL, "request_method": "GET", "request_headers": dict(HEADERS),
                               "status_code": 200, "completion": "completed", "headers_sha256": digest(headers),
                               "headers_complete": True, "headers_observed_byte_length": len(headers)})
    return r


def release_fixture(prior=None, opening=None):
    prior = b'[{"id":41,"draft":true,"prerelease":false},{"id":9007199254740993,"draft":false,"prerelease":true}]' if prior is None else prior
    opening = b'[{"id":9007199254740993,"draft":false,"prerelease":false,"published_at":"1900-01-01T00:00:00.123456789Z"},{"id":57,"draft":false,"prerelease":true},{"id":8,"draft":false,"prerelease":false,"tag_name":null}]' if opening is None else opening
    q = {"schema_version": 1, "family": "software_component", "question_id": "question:invented-release", "subject_id": "component:fixture-Ω",
         "knowledge_cutoff_utc": instant(300), "forecast_deadline_utc": instant(600), "outcome_cutoff_utc": instant(900), "resolution_rule_id": "bounded-release-observation-v1",
         "evidence": {"source_id": "github-python-sdk-release-sample", "request_url": URL, "opening_slot_id": "slot-open",
                      "slots": [{"id": "slot-prior", "nominal_at": instant(0)}, {"id": "slot-open", "nominal_at": instant(120)}]}}
    qb = encoded(q)
    bodies = {"q-release": qb, "z-prior": prior, "z-prior:headers": b"[]", "a-open": opening, "a-open:headers": b"[]"}
    m = {"raw_input_schema_version": 1, "declaration_sha256": PIN, "question_observation_id": "q-release",
         "observations": [sample("a-open", "slot-open", opening, 120), receipt("q-release", "question_contract", qb, 240), sample("z-prior", "slot-prior", prior, 0)]}
    return m, bodies


def obligation_fixture(source=SOURCE, algorithm="sha1"):
    blob = hashlib.new(algorithm, b"blob " + str(len(source)).encode("ascii") + b"\0" + source).hexdigest()
    binding = {"acceptance_event_id": "event:fixture-accept", "promisor_role_id": "role:named-beneficiary-but-promises", "beneficiary_role_id": "role:named-promisor-but-benefits",
               "authorized_submission_channel_id": "channel:exclusive-fixture", "quality_rule_hash": "a" * 64, "quality_parameters": {"line_rule": "raw-LF", "version": 1},
               "source_sha256": digest(source), "source_byte_length": len(source), "source_path": "docs/research/invented-oracle.md", "source_blob_id": blob,
               "git_object_format": algorithm, "source_commit_id": "c" * (40 if algorithm == "sha1" else 64)}
    a = dict(binding, schema_version=1, obligation_id="obligation:fixture", due_utc=instant(900))
    ab = encoded(a)
    q = {"schema_version": 1, "family": "local_delivery_obligation", "question_id": "question:invented-obligation", "subject_id": "obligation:fixture",
         "knowledge_cutoff_utc": instant(300), "forecast_deadline_utc": instant(600), "outcome_cutoff_utc": instant(900), "resolution_rule_id": "first-artifact-quality-v1",
         "evidence": dict(binding, acceptance_observation_id="a-accept", acceptance_sha256=digest(ab), source_observation_id="s-source")}
    qb = encoded(q)
    bodies = {"q-obligation": qb, "a-accept": ab, "s-source": source}
    m = {"raw_input_schema_version": 1, "declaration_sha256": PIN, "question_observation_id": "q-obligation",
         "observations": [receipt("s-source", "source_blob", source, 0), receipt("q-obligation", "question_contract", qb, 240), receipt("a-accept", "acceptance", ab, 10)]}
    return m, bodies


def replace_body(m, bodies, ident, raw):
    bodies[ident] = raw
    r = next(r for r in m["observations"] if r["id"] == ident)
    r.update(content_sha256=digest(raw), retained_byte_length=len(raw), observed_byte_length=len(raw))


def change_question(m, bodies, update):
    ident = m["question_observation_id"]
    q = json.loads(bodies[ident])
    update(q)
    replace_body(m, bodies, ident, encoded(q))


def raw_record(ident="1", draft="false", prerelease="false", extra=""):
    return ('[{"id":' + ident + ',"draft":' + draft + ',"prerelease":' + prerelease + extra + '}]').encode("utf-8")


# These values were specified from the raw fixture and public declaration before
# running the oracle. Hash values below are frozen literal bindings, not oracle output.
RELEASE_ANSWERS = {
    "subject_id": "component:fixture-Ω", "knowledge_cutoff_utc": "2026-12-01T00:05:00.000000Z", "outcome_cutoff_utc": "2026-12-01T00:15:00.000000Z",
    "source_observation_ids": ["a-open", "q-release", "z-prior"], "seen_id_set": [8, 41, 57, 9007199254740993],
    "opening_eligibility": {"8": True, "57": False, "9007199254740993": True},
}
RELEASE_SUPPORT = {
    "subject_id": ["q-release"], "knowledge_cutoff_utc": ["q-release"], "outcome_cutoff_utc": ["q-release"],
    "source_observation_ids": ["a-open", "q-release", "z-prior"], "seen_id_set": ["a-open", "q-release", "z-prior"], "opening_eligibility": ["a-open", "q-release"],
}
OBLIGATION_ANSWERS = {
    "subject_id": "obligation:fixture", "knowledge_cutoff_utc": "2026-12-01T00:05:00.000000Z", "outcome_cutoff_utc": "2026-12-01T00:15:00.000000Z",
    "source_observation_ids": ["a-accept", "q-obligation", "s-source"], "promisor_role_id": "role:named-beneficiary-but-promises", "beneficiary_role_id": "role:named-promisor-but-benefits",
    "source_sha256": "d6edf933313f6c6831bf9c95a7b172f680412cc3a670ea7ed30f9ac30e92593e", "quality_rule_hash": "a" * 64, "acceptance_event_id": "event:fixture-accept", "authorized_submission_channel_id": "channel:exclusive-fixture",
}
OBLIGATION_SUPPORT = {
    "subject_id": ["q-obligation"], "knowledge_cutoff_utc": ["q-obligation"], "outcome_cutoff_utc": ["q-obligation"],
    "source_observation_ids": ["a-accept", "q-obligation", "s-source"], "source_sha256": ["a-accept", "q-obligation", "s-source"],
    "promisor_role_id": ["a-accept", "q-obligation"], "beneficiary_role_id": ["a-accept", "q-obligation"], "quality_rule_hash": ["a-accept", "q-obligation"],
    "acceptance_event_id": ["a-accept", "q-obligation"], "authorized_submission_channel_id": ["a-accept", "q-obligation"],
}


def retain_case(directory, label, manifest, bodies, extra=None):
    """Only test-side retention. Numeric filenames never interpret observation IDs."""
    folder = directory / label
    folder.mkdir(exist_ok=False)
    (folder / "manifest.json").write_bytes(manifest)
    inventory = []
    for index, key in enumerate(sorted(bodies)):
        name = f"body-{index:02d}.bin"
        raw = bodies[key]
        (folder / name).write_bytes(raw)
        inventory.append({"key": key, "filename": name, "sha256": digest(raw), "bytes": len(raw)})
    (folder / "bodies.json").write_bytes(encoded(inventory))
    if extra is not None:
        (folder / "expected.json").write_bytes(encoded(extra))
    return folder


def freeze_expected(directory):
    directory.mkdir(exist_ok=False)
    for name, fixture, answers, support in (
        ("release", release_fixture, RELEASE_ANSWERS, RELEASE_SUPPORT),
        ("obligation", obligation_fixture, OBLIGATION_ANSWERS, OBLIGATION_SUPPORT),
    ):
        m, b = fixture()
        retain_case(directory, name, encoded(m), b, {"answers": answers, "required_support": support})
    (directory / "authority.json").write_bytes(encoded({"declaration_sha256": PIN, "basis": "invented raw fixtures and literal required answers/support; no candidate outputs consulted", "status": "pre-registration engineering only"}))


def disqualified_prior_fixture(mode, headers):
    m, b = release_fixture()
    r = m["observations"][2]
    if mode == "incomplete": r["complete"] = False
    if mode == "missing": del b["z-prior"]
    if mode == "hash": r["content_sha256"] = "0" * 64
    if mode == "epoch": r["clock"]["end_epoch"] = "other-epoch"
    if mode == "start": r = sample("z-prior", "slot-prior", b["z-prior"], 61)
    if mode == "duration": r = sample("z-prior", "slot-prior", b["z-prior"], 0, observed=11)
    if mode == "retention": r = sample("z-prior", "slot-prior", b["z-prior"], 0, retained=121)
    if mode == "cutoff": r = sample("z-prior", "slot-prior", b["z-prior"], 0, retained=301)
    b["z-prior:headers"] = headers
    r["http"].update(headers_sha256=digest(headers), headers_observed_byte_length=len(headers))
    m["observations"][2] = r
    return m, b


DISQUALIFICATIONS = (
    ("incomplete", "body_incomplete"), ("missing", "body_missing"), ("hash", "body_hash_mismatch"),
    ("epoch", "clock_epoch_mismatch"), ("start", "request_start_outside_window"),
    ("duration", "request_duration_invalid"), ("retention", "slot_receipt_late"), ("cutoff", "after_knowledge_cutoff"),
)
BAD_HEADER_CONTROLS = (b'[["X-Extra",1e400]]', b'[["X-Extra",NaN]]', b'{')


def freeze_repair_expected(directory):
    directory.mkdir(exist_ok=False)
    for mode, reason in DISQUALIFICATIONS:
        for n, headers in enumerate(BAD_HEADER_CONTROLS):
            m, b = disqualified_prior_fixture(mode, headers)
            retain_case(directory, mode + "-" + str(n), encoded(m), b, {
                "status": "available", "prior_status": "excluded", "required_exclusion_reason": reason,
                "seen_id_set": [8, 57, 9007199254740993], "source_observation_ids": ["a-open", "q-release"],
                "seen_and_membership_support": ["a-open", "q-release"],
            })
    m, b = disqualified_prior_fixture("eligible", BAD_HEADER_CONTROLS[0])
    retain_case(directory, "potentially-eligible-runtime", encoded(m), b, {
        "status": "unavailable", "prior_status": "unavailable", "reason": "runtime_decimal_unavailable",
        "seen_id_set": None, "source_observation_ids": None,
    })


class RawOracleTests(unittest.TestCase):
    def setUp(self):
        self.case_number = 0

    def call(self, m, bodies, label="case", expected_exception=None):
        self.case_number += 1
        raw = m if type(m) is bytes else encoded(m)
        original = copy.deepcopy(bodies)
        path = None
        if os.environ.get("ORACLE_EVIDENCE_DIR"):
            base = Path(os.environ["ORACLE_EVIDENCE_DIR"])
            base.mkdir(parents=True, exist_ok=True)
            path = retain_case(base, f"{self._testMethodName}-{self.case_number:03d}-{label}", raw, bodies)
        try:
            result = expected_queries_from_raw_sources(raw, bodies)
        except Exception as exc:
            if path:
                (path / "exception.json").write_bytes(encoded({"class": type(exc).__name__, "reason": str(exc)}))
            if expected_exception is None:
                raise
            self.assertIsInstance(exc, expected_exception)
            if expected_exception is ValueError:
                self.assertNotIsInstance(exc, OracleUnavailable)
            return exc
        finally:
            self.assertEqual(original, bodies)
        if expected_exception:
            self.fail("expected refusal")
        if path:
            (path / "oracle.json").write_bytes(result)
        self.assertLessEqual(len(result), 65_536)
        parsed = json.loads(result)
        self.assertEqual(result, encoded(parsed))
        self.assertEqual(parsed["manifest_sha256"], digest(raw))
        self.assertEqual(parsed["declaration_sha256"], PIN)
        self.assertEqual(parsed["timing_assurance"], "caller_claims_only")
        self.assertIs(parsed["independent_collection_verified"], False)
        return parsed

    def admitted(self, p, ident, status, reason=None):
        row = next(r for r in p["observations"] if r["id"] == ident)
        self.assertEqual(row["status"], status)
        if reason:
            self.assertIn(reason, row["reasons"])

    def test_release_literal_answers_and_support(self):
        p = self.call(*release_fixture())
        self.assertEqual(p["status"], "available")
        self.assertEqual(p["answers"], RELEASE_ANSWERS)
        self.assertEqual(p["required_support"], RELEASE_SUPPORT)
        self.assertEqual(len(p["required_fields"]), 6)
        self.assertEqual(len(p["inapplicable_fields"]), 6)

    def test_obligation_literal_answers_and_support(self):
        p = self.call(*obligation_fixture())
        self.assertEqual(p["status"], "available")
        self.assertEqual(p["answers"], OBLIGATION_ANSWERS)
        self.assertEqual(p["required_support"], OBLIGATION_SUPPORT)
        self.assertEqual(len(p["required_fields"]), 10)
        self.assertEqual(p["inapplicable_fields"], ["seen_id_set", "opening_eligibility"])

    def test_valid_empty_opening_retains_history(self):
        p = self.call(*release_fixture(opening=b"[]"))
        self.assertEqual(p["answers"]["seen_id_set"], [41, 9007199254740993])
        self.assertEqual(p["answers"]["opening_eligibility"], {})
        self.assertEqual(p["required_support"]["seen_id_set"], ["a-open", "q-release", "z-prior"])
        self.admitted(p, "a-open", "admitted")

    def test_valid_empty_universe_still_has_observation_manifest(self):
        p = self.call(*release_fixture(prior=b"[]", opening=b"[]"))
        self.assertEqual(p["answers"]["seen_id_set"], [])
        self.assertEqual(p["answers"]["source_observation_ids"], ["a-open", "q-release", "z-prior"])
        self.assertEqual(p["status"], "available")

    def test_missing_invalid_late_opening_is_unknown(self):
        for failure in ("missing", "invalid", "late", "incomplete", "hash"):
            with self.subTest(failure=failure):
                m, b = release_fixture()
                r = m["observations"][0]
                if failure == "missing": del b["a-open"]
                if failure == "invalid": replace_body(m, b, "a-open", b"not-json")
                if failure == "late": m["observations"][0] = sample("a-open", "slot-open", b["a-open"], 120, retained=241)
                if failure == "incomplete": r["complete"] = False
                if failure == "hash": r["content_sha256"] = "0" * 64
                p = self.call(m, b, failure)
                self.assertEqual(p["status"], "unavailable")
                self.assertIsNone(p["answers"]["seen_id_set"])
                self.assertIsNone(p["answers"]["opening_eligibility"])
                self.assertEqual(p["field_status"]["subject_id"], "known")
                self.admitted(p, "a-open", "excluded")

    def test_invalid_prior_excluded_not_empty_admitted(self):
        for failure in ("missing", "invalid", "late"):
            m, b = release_fixture()
            if failure == "missing": del b["z-prior"]
            if failure == "invalid": replace_body(m, b, "z-prior", b"{")
            if failure == "late": m["observations"][2] = sample("z-prior", "slot-prior", b["z-prior"], 0, retained=121)
            p = self.call(m, b, failure)
            self.assertEqual(p["answers"]["seen_id_set"], [8, 57, 9007199254740993])
            self.assertEqual(p["answers"]["source_observation_ids"], ["a-open", "q-release"])
            self.admitted(p, "z-prior", "excluded")

    def test_missing_prior_receipt_not_unknown_empty_history(self):
        m, b = release_fixture()
        m["observations"] = m["observations"][:2]
        del b["z-prior"]; del b["z-prior:headers"]
        p = self.call(m, b)
        self.assertEqual(p["missing_slots"], ["slot-prior"])
        self.assertIsNone(p["answers"]["seen_id_set"])
        self.assertEqual(p["answers"]["opening_eligibility"], RELEASE_ANSWERS["opening_eligibility"])

    def test_later_slot_excluded_despite_early_claimed_retention(self):
        m, b = release_fixture()
        change_question(m, b, lambda q: q["evidence"]["slots"].append({"id": "slot-future", "nominal_at": instant(360)}))
        b["future"] = raw_record("99"); b["future:headers"] = b"[]"
        m["observations"].append(sample("future", "slot-future", b["future"], 150))
        p = self.call(m, b)
        self.assertEqual(p["answers"], RELEASE_ANSWERS)
        self.admitted(p, "future", "excluded", "after_opening_slot")

    def test_required_release_types_and_duplicates(self):
        cases = [raw_record("true"), raw_record("1.0"), raw_record("0"), raw_record("-1"), raw_record('"7"'), raw_record(draft="0"), raw_record(prerelease="null"),
                 b'[{"id":1,"draft":false}]', b'[{"id":1,"id":2,"draft":false,"prerelease":false}]',
                 b'[{"id":1,"draft":false,"prerelease":false},{"id":1,"draft":false,"prerelease":false}]', b"{}"]
        for n, raw in enumerate(cases):
            p = self.call(*release_fixture(opening=raw), str(n))
            self.assertEqual(p["status"], "unavailable")
            self.admitted(p, "a-open", "excluded")

    def test_optional_fields_do_not_determine_eligibility(self):
        for extra in (',"tag_name":null', ',"published_at":"late nonsense"', ',"created_at":true', ',"tag_name":{"a":1}', ',"published_at":"2000-01-01T00:00:00.١Z"', ',"unused_api_field":{"price":0.1}'):
            p = self.call(*release_fixture(opening=raw_record(extra=extra)))
            self.assertEqual(p["answers"]["opening_eligibility"], {"1": True})
            self.admitted(p, "a-open", "admitted")

    def test_empty_and_five_record_and_six_record_arrays(self):
        for count in (0, 5, 6):
            raw = encoded([{"id": n + 1, "draft": False, "prerelease": False} for n in range(count)])
            p = self.call(*release_fixture(opening=raw), str(count))
            self.assertEqual(p["status"], "available" if count <= 5 else "unavailable")

    def test_http_headers_are_retained_bounded_claims(self):
        valid = [b"[]", b'[["Link","<https://example.test/?page=2>; rel=next"]]', b'[["Link","this is unparseable"]]', b'[["Content-Encoding","identity"],["X-Meta","a"],["X-Meta","b"]]']
        invalid = [b'[["Content-Encoding","gzip"]]', b'[["Content-Encoding","identity"],["content-encoding","identity"]]', b'[["Bad Header","ok"]]', b'[["X-Test","bad\\rvalue"]]', b'[["X-Test",1]]', b"{}"]
        for n, raw in enumerate(valid + invalid):
            m, b = release_fixture()
            b["a-open:headers"] = raw
            m["observations"][0]["http"].update(headers_sha256=digest(raw), headers_observed_byte_length=len(raw))
            p = self.call(m, b, str(n))
            self.assertEqual(p["status"], "available" if n < len(valid) else "unavailable")

    def test_http_refusals(self):
        for key, value in (("status_code", 304), ("request_method", "POST"), ("request_url", URL + "&page=2"), ("completion", "timeout"), ("headers_complete", False), ("headers_sha256", "0" * 64), ("headers_observed_byte_length", 3), ("request_headers", {})):
            m, b = release_fixture(); m["observations"][0]["http"][key] = value
            p = self.call(m, b, key)
            self.admitted(p, "a-open", "excluded")

    def test_exact_timing_windows_and_clock_disagreement(self):
        controls = [(180, 190, 240, True), (181, 182, 183, False), (120, 131, 132, False), (120, 130, 241, False)]
        for start, observed, retained, valid in controls:
            m, b = release_fixture(); m["observations"][0] = sample("a-open", "slot-open", b["a-open"], start, observed=observed, retained=retained)
            p = self.call(m, b)
            self.assertEqual(p["status"], "available" if valid else "unavailable")
        for ns, valid in ((1_000_000_000, True), (1_000_000_001, False)):
            m, b = release_fixture(); c = m["observations"][0]["clock"]
            for key in ("observed_ns", "validated_ns", "retained_ns"): c[key] += ns
            p = self.call(m, b)
            self.assertEqual(p["status"], "available" if valid else "unavailable")

    def test_epoch_order_and_cutoff_controls(self):
        for mode in ("epoch", "utc-order", "ns-order", "basis", "cutoff"):
            m, b = release_fixture(); r = m["observations"][0]
            if mode == "epoch": r["clock"]["end_epoch"] = "other-epoch"
            if mode == "utc-order": r["validated_at"] = instant(120)
            if mode == "ns-order": r["clock"]["validated_ns"] = 1
            if mode == "basis": r["time_basis"] = "publisher_clock"
            if mode == "cutoff":
                change_question(m, b, lambda q: q.update(knowledge_cutoff_utc=instant(121)))
                m["observations"][1] = receipt("q-release", "question_contract", b["q-release"], 100)
            p = self.call(m, b, mode)
            self.assertEqual(p["status"], "unavailable")

    def test_equivalent_times_and_order_do_not_change_answers(self):
        m, b = release_fixture()
        q = json.loads(b["q-release"])
        q["knowledge_cutoff_utc"] = "2026-12-01T00:05:00+00:00"
        replace_body(m, b, "q-release", encoded(q))
        m["observations"].reverse()
        for r in m["observations"]:
            for key in ("observed_at", "retained_at", "validated_at"): r[key] = r[key].replace(".000000Z", "+00:00")
        p = self.call(m, b)
        self.assertEqual(p["answers"], RELEASE_ANSWERS)
        self.assertEqual(p["required_support"], RELEASE_SUPPORT)

    def test_exact_integer_runtime_boundary(self):
        self.assertEqual(sys.get_int_max_str_digits(), 4300, "This run records only the specified tested runtime boundary")
        before = sys.get_int_max_str_digits()
        p = self.call(*release_fixture(opening=raw_record("9" * 4300)), "4300")
        self.assertEqual(p["status"], "available")
        self.assertIn("9" * 4300, p["answers"]["opening_eligibility"])
        for where in ("prior", "opening"):
            p = self.call(*release_fixture(**{where: raw_record("9" * 4301)}), where)
            self.assertEqual(p["status"], "unavailable")
            self.admitted(p, "z-prior" if where == "prior" else "a-open", "unavailable", "runtime_integer_unavailable")
            self.assertIsNone(p["answers"]["seen_id_set"])
        self.assertEqual(sys.get_int_max_str_digits(), before)

    def test_finite_decimal_limits_are_unavailable_not_rounded(self):
        for token in ("1e400", "1e-400", "0.12345678901234567890123456789"):
            p = self.call(*release_fixture(opening=raw_record(extra=',"unselected":' + token)), token)
            self.admitted(p, "a-open", "unavailable", "runtime_decimal_unavailable")
        for token in ("NaN", "Infinity", "-Infinity"):
            p = self.call(*release_fixture(opening=raw_record(extra=',"unselected":' + token)), token)
            self.admitted(p, "a-open", "excluded", "nonfinite_json_literal")
        for token in ("0.1", "1e-100", "1.00"):
            p = self.call(*release_fixture(opening=raw_record(extra=',"unselected":' + token)), token)
            self.assertEqual(p["status"], "available")

    def test_runtime_envelope_limits_distinct_from_malformed(self):
        m, b = release_fixture()
        raw = encoded(m)
        marker = b'"retained_byte_length":' + str(m["observations"][0]["retained_byte_length"]).encode()
        raw = raw.replace(marker, b'"retained_byte_length":' + b"9" * 4301, 1)
        self.call(raw, b, expected_exception=OracleUnavailable)
        self.call(b"[" * 2000 + b"0" + b"]" * 2000, {}, expected_exception=ValueError)
        self.call(b"[" * 10000 + b"0" + b"]" * 10000, {}, expected_exception=OracleUnavailable)
        self.call(b'{"raw_input_schema_version":NaN}', {}, expected_exception=ValueError)

    def test_strict_json_envelope_and_caps(self):
        m, b = release_fixture()
        for raw in (b"\xef\xbb\xbf" + encoded(m), encoded(m) + b"x", b"\xff", b'{"raw_input_schema_version":1,"raw_input_schema_version":1}', b" " * 262145):
            self.call(raw, b, expected_exception=ValueError)
        p = self.call(*release_fixture(opening=b" " * 1048577), "body-cap")
        self.admitted(p, "a-open", "excluded", "body_over_limit")
        m, b = release_fixture(); b["a-open:headers"] = b" " * 16385
        m["observations"][0]["http"].update(headers_observed_byte_length=16385, headers_sha256=digest(b["a-open:headers"]))
        self.admitted(self.call(m, b, "headers-cap"), "a-open", "excluded", "headers_over_limit")

    def test_manifest_receipt_types_and_identity_refuse(self):
        for mode in ("version-bool", "pin", "extra", "duplicate", "complete-int", "length-bool", "status-bool", "epoch-empty", "slot-unknown", "slot-duplicate", "undeclared-body", "header-key-collision"):
            m, b = release_fixture()
            if mode == "version-bool": m["raw_input_schema_version"] = True
            if mode == "pin": m["declaration_sha256"] = "0" * 64
            if mode == "extra": m["extra"] = 1
            if mode == "duplicate": m["observations"].append(copy.deepcopy(m["observations"][0]))
            if mode == "complete-int": m["observations"][0]["complete"] = 1
            if mode == "length-bool": m["observations"][0]["retained_byte_length"] = True
            if mode == "status-bool": m["observations"][0]["http"]["status_code"] = True
            if mode == "epoch-empty": m["observations"][0]["clock"]["start_epoch"] = ""
            if mode == "slot-unknown": m["observations"][0]["slot_id"] = "unknown"
            if mode == "slot-duplicate": m["observations"][2]["slot_id"] = "slot-open"
            if mode == "undeclared-body": b["extra"] = b"x"
            if mode == "header-key-collision": m["observations"][1]["id"] = "a-open:headers"; m["question_observation_id"] = "a-open:headers"
            self.call(m, b, mode, ValueError)

    def test_question_invalid_or_missing_does_not_invent_family(self):
        for raw in (None, b"{}", b"" , b" " * 65537):
            m, b = release_fixture()
            if raw is None: del b["q-release"]
            else: replace_body(m, b, "q-release", raw)
            p = self.call(m, b)
            self.assertEqual(p["status"], "unavailable")
            self.assertIsNone(p["family"])
            self.assertEqual(p["answers"], {})
            self.assertEqual(set(p["required_fields_by_family"]), {"software_component", "local_delivery_obligation"})

    def test_obligation_source_bytes_blob_and_direction(self):
        for source in (SOURCE, b"x" * 256, b"x" * 8192, b"x\n" * 128, b"x\r" * 128, "é".encode() * 128):
            for algorithm in ("sha1", "sha256"):
                p = self.call(*obligation_fixture(source, algorithm))
                self.assertEqual(p["status"], "available")
                self.assertEqual(p["answers"]["promisor_role_id"], "role:named-beneficiary-but-promises")
                self.assertEqual(p["answers"]["source_sha256"], digest(source))
        for source in (b"", b"x" * 255, b"x" * 8193, b"x\n" * 128 + b"x", b"\xff" * 256, b"\0" * 256):
            p = self.call(*obligation_fixture(source))
            self.assertEqual(p["status"], "unavailable")
            self.assertIsNone(p["answers"]["source_sha256"])

    def test_obligation_acceptance_bindings_exact_types(self):
        for key, value in (("promisor_role_id", "role:named-promisor-but-benefits"), ("authorized_submission_channel_id", "channel:substitute"), ("quality_rule_hash", "b" * 64), ("quality_parameters", {"line_rule": "raw-LF", "version": True}), ("source_byte_length", float(len(SOURCE))), ("source_blob_id", "d" * 40), ("due_utc", instant(901)), ("obligation_id", "obligation:other")):
            m, b = obligation_fixture(); a = json.loads(b["a-accept"]); a[key] = value
            replace_body(m, b, "a-accept", encoded(a))
            change_question(m, b, lambda q: q["evidence"].update(acceptance_sha256=digest(b["a-accept"])))
            p = self.call(m, b, key)
            self.assertEqual(p["status"], "unavailable")
            self.admitted(p, "a-accept", "excluded")

    def test_obligation_missing_invalid_late_and_hash_controls(self):
        for ident in ("a-accept", "s-source"):
            for mode in ("missing-body", "missing-receipt", "late", "hash"):
                m, b = obligation_fixture()
                r = next(r for r in m["observations"] if r["id"] == ident)
                if mode == "missing-body": del b[ident]
                if mode == "missing-receipt": m["observations"].remove(r); del b[ident]
                if mode == "late": m["observations"][m["observations"].index(r)] = receipt(ident, r["kind"], b[ident], 299, retained=301)
                if mode == "hash": r["content_sha256"] = "0" * 64
                p = self.call(m, b, ident + mode)
                self.assertEqual(p["status"], "unavailable")
                self.assertIsNone(p["answers"]["source_observation_ids"])
                self.assertIsNone(p["answers"]["promisor_role_id"])

    def test_obligation_source_binding_mismatches(self):
        for key, value in (("source_sha256", "b" * 64), ("source_byte_length", len(SOURCE) + 1), ("source_blob_id", "d" * 40)):
            m, b = obligation_fixture()
            a = json.loads(b["a-accept"]); a[key] = value; replace_body(m, b, "a-accept", encoded(a))
            change_question(m, b, lambda q: q["evidence"].update({key: value, "acceptance_sha256": digest(b["a-accept"])}))
            p = self.call(m, b, key)
            self.assertEqual(p["status"], "unavailable")
            self.admitted(p, "s-source", "excluded")

    def test_obligation_path_and_acceptance_identity_controls(self):
        for path in ("docs/theory/../x.md", "docs/theory//x.md", "/docs/theory/x.md", "docs/theory/x.txt", "docs/private/x.md", "docs/theory/x\\z.md", "docs/theory/x\x00.md"):
            m, b = obligation_fixture()
            change_question(m, b, lambda q: q["evidence"].update(source_path=path))
            self.assertEqual(self.call(m, b)["status"], "unavailable")
        m, b = obligation_fixture()
        change_question(m, b, lambda q: q["evidence"].update(source_observation_id="a-accept"))
        self.call(m, b, expected_exception=ValueError)

    def test_entity_namespace_collision_controls(self):
        m, b = release_fixture()
        for release_id in (8, 41):
            m, b = release_fixture()
            collision = "release:" + digest(encoded(["component:fixture-Ω", release_id]))
            change_question(m, b, lambda q: q.update(question_id=collision))
            self.call(m, b, expected_exception=ValueError)
        m, b = obligation_fixture()
        change_question(m, b, lambda q: q["evidence"].update(authorized_submission_channel_id=q["evidence"]["promisor_role_id"]))
        self.assertEqual(self.call(m, b)["status"], "unavailable")

    def test_same_kind_role_reuse_is_allowed(self):
        m, b = obligation_fixture()
        a = json.loads(b["a-accept"])
        a["beneficiary_role_id"] = a["promisor_role_id"]
        replace_body(m, b, "a-accept", encoded(a))
        change_question(m, b, lambda q: q["evidence"].update(beneficiary_role_id=a["promisor_role_id"], acceptance_sha256=digest(b["a-accept"])))
        p = self.call(m, b)
        self.assertEqual(p["status"], "available")
        self.assertEqual(p["answers"]["promisor_role_id"], p["answers"]["beneficiary_role_id"])

    def test_output_bound_is_explicit_unavailable(self):
        m, b = release_fixture(prior=b"[]", opening=b"[]")
        # Sixteen samples, eighty distinct exact 4,300-digit IDs. Inputs stay
        # within raw caps, while the complete answer cannot fit this API cap.
        slots = [{"id": "s" + str(n), "nominal_at": instant(n * 180)} for n in range(16)]
        change_question(m, b, lambda q: q.update(
            knowledge_cutoff_utc=instant(3000), forecast_deadline_utc=instant(3100), outcome_cutoff_utc=instant(3200),
            evidence={"source_id": "github-python-sdk-release-sample", "request_url": URL, "opening_slot_id": "s15", "slots": slots}))
        qb = b["q-release"]
        b = {"q-release": qb}
        m["observations"] = [receipt("q-release", "question_contract", qb, 2900)]
        for n in range(16):
            ident = "sample" + str(n)
            rows = [raw_record(str(1000 + n * 5 + j) + "0" * 4296)[1:-1] for j in range(5)]
            raw = b"[" + b",".join(rows) + b"]"
            b[ident] = raw; b[ident + ":headers"] = b"[]"
            m["observations"].append(sample(ident, "s" + str(n), raw, n * 180))
        exc = self.call(m, b, expected_exception=OracleUnavailable)
        self.assertEqual(str(exc), "oracle_output_limit_unavailable")

    def test_known_prior_exclusion_survives_unreadable_headers(self):
        for mode, reason in DISQUALIFICATIONS:
            for n, headers in enumerate(BAD_HEADER_CONTROLS):
                p = self.call(*disqualified_prior_fixture(mode, headers), mode + "-" + str(n))
                self.assertEqual(p["status"], "available")
                self.admitted(p, "z-prior", "excluded", reason)
                self.assertEqual(p["answers"]["seen_id_set"], [8, 57, 9007199254740993])
                self.assertEqual(p["answers"]["source_observation_ids"], ["a-open", "q-release"])
                self.assertEqual(p["required_support"]["seen_id_set"], ["a-open", "q-release"])

    def test_potentially_eligible_unreadable_headers_stay_unknown(self):
        p = self.call(*disqualified_prior_fixture("eligible", BAD_HEADER_CONTROLS[0]))
        self.assertEqual(p["status"], "unavailable")
        self.admitted(p, "z-prior", "unavailable", "runtime_decimal_unavailable")
        self.assertIsNone(p["answers"]["seen_id_set"])
        self.assertIsNone(p["answers"]["source_observation_ids"])
        self.assertEqual(p["answers"]["opening_eligibility"], RELEASE_ANSWERS["opening_eligibility"])

    def test_known_opening_exclusion_survives_unreadable_headers(self):
        m, b = release_fixture()
        m["observations"][0]["complete"] = False
        b["a-open:headers"] = BAD_HEADER_CONTROLS[0]
        m["observations"][0]["http"].update(headers_sha256=digest(b["a-open:headers"]), headers_observed_byte_length=len(b["a-open:headers"]))
        p = self.call(m, b)
        self.admitted(p, "a-open", "excluded", "body_incomplete")
        self.assertEqual(p["status"], "unavailable")
        self.assertIsNone(p["answers"]["seen_id_set"])

    def test_header_disqualification_precedes_body_runtime_inability(self):
        m, b = release_fixture(prior=raw_record(extra=',"unselected":1e400'))
        m["observations"][2]["http"]["status_code"] = 404
        p = self.call(m, b)
        self.admitted(p, "z-prior", "excluded", "http_status_invalid")
        self.assertEqual(p["status"], "available")

    def test_no_candidate_dependency_or_effect_calls(self):
        import ast
        module = Path(importlib.util.find_spec("epiphysics.prospective_oracle").origin)
        tree = ast.parse(module.read_text())
        allowed = {"hashlib", "json", "math", "re", "datetime", "decimal"}
        imports = {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
        imports |= {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertLessEqual(imports, allowed)
        forbidden = {"open", "exec", "eval", "compile", "__import__", "set_int_max_str_digits"}
        self.assertFalse([n for n in ast.walk(tree) if isinstance(n, ast.Call) and ((isinstance(n.func, ast.Name) and n.func.id in forbidden) or (isinstance(n.func, ast.Attribute) and n.func.attr in forbidden and not (isinstance(n.func.value, ast.Name) and n.func.value.id == "re" and n.func.attr == "compile")))])


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--freeze-expected":
        freeze_expected(Path(sys.argv[2]))
    elif len(sys.argv) == 3 and sys.argv[1] == "--freeze-repair-expected":
        freeze_repair_expected(Path(sys.argv[2]))
    else:
        unittest.main()
