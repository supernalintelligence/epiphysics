"""Independent invented byte controls; no producer or query helpers are used."""

import hashlib
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from epiphysics.prospective_quality import check_line_index


# Literal source bytes, partitions and hashes were frozen before execution.
# These short sources are boundary fixtures, not selected pilot documents.
SOURCE = b"alpha\nbeta"
ARTIFACT = (
    b'{"schema_version":1,"source_sha256":"bbfb79e82216bd2db1ad2c507d44ddf80'
    b'aeb12f64f9562056afe93aad43154d9","source_byte_length":10,"lines":['
    b'{"start":0,"end":6,"sha256":"b6a98d9ce9a2d9149288fa3df42d377c3'
    b'e42737afdcdaf714e33c0a100b51060"},'
    b'{"start":6,"end":10,"sha256":"f44e64e75f3948e9f73f8dfa94721c4ce'
    b'8cbb4f265c4790c702b2d41cfbf2753"}]}'
)
EMPTY_ARTIFACT = (
    b'{"schema_version":1,"source_sha256":"e3b0c44298fc1c149afbf4c8996fb924'
    b'27ae41e4649b934ca495991b7852b855","source_byte_length":0,"lines":[]}'
)
UNICODE_ARTIFACT = (
    b'{"schema_version":1,"source_sha256":"6e0a4f15f3c71dca9525183391531407'
    b'3f48208e8f88d95fd6a4059eb5785744","source_byte_length":10,"lines":['
    b'{"start":0,"end":3,"sha256":"edd3a863872a04239eb29ad4bc12fc892'
    b'b3d4ae57cc7e786a3697816f8e141c2"},'
    b'{"start":3,"end":9,"sha256":"f6a9d5888070c5e4ed7df32b38b59518'
    b'898fd82800dad89bdf6e21be61771033"},'
    b'{"start":9,"end":10,"sha256":"594e519ae499312b29433b7dd8a97ff0'
    b'68defcba9755b6d5d00e84c524d67b06"}]}'
)


class ProspectiveQualityTests(unittest.TestCase):
    def assert_quality(self, source, artifact, quality, reason):
        result = check_line_index(source, artifact)
        self.assertIs(result.quality, quality)
        self.assertEqual(result.reason, reason)
        return result

    def test_literal_sources_and_exact_identities(self):
        for source, artifact in (
            (SOURCE, ARTIFACT),
            (b"", EMPTY_ARTIFACT),
            (b"\xc3\xa9\n\xf0\x9f\x99\x82\r\nz", UNICODE_ARTIFACT),
        ):
            with self.subTest(source=source):
                result = self.assert_quality(source, artifact, True, "matches")
                self.assertEqual(result.source_sha256, hashlib.sha256(source).hexdigest())
                self.assertEqual(result.artifact_sha256, hashlib.sha256(artifact).hexdigest())
                self.assertEqual(result.source_byte_length, len(source))
                self.assertEqual(result.artifact_byte_length, len(artifact))

    def test_whitespace_changes_identity_but_not_quality(self):
        first = self.assert_quality(SOURCE, ARTIFACT, True, "matches")
        second = self.assert_quality(SOURCE, b" \n" + ARTIFACT + b"\t", True, "matches")
        self.assertEqual(first.source_sha256, second.source_sha256)
        self.assertNotEqual(first.artifact_sha256, second.artifact_sha256)

    def test_wrong_offset_hash_and_line_order(self):
        variants = [
            ARTIFACT.replace(b'"end":6', b'"end":5'),
            ARTIFACT.replace(b"b6a98d9c", b"00000000"),
            UNICODE_ARTIFACT.replace(b'"start":3', b'"start":2'),
        ]
        for index, artifact in enumerate(variants):
            source = SOURCE if index < 2 else b"\xc3\xa9\n\xf0\x9f\x99\x82\r\nz"
            self.assert_quality(source, artifact, False, "content_mismatch")
        value = json.loads(ARTIFACT)
        value["lines"].reverse()
        self.assert_quality(SOURCE, json.dumps(value).encode(), False, "content_mismatch")

    def test_types_extra_fields_and_nonfinite(self):
        for token in (b"true", b"null", b'"1"', b"1.0", b"1e99999999999999999999"):
            self.assert_quality(SOURCE, ARTIFACT.replace(b'"schema_version":1', b'"schema_version":' + token), False, "artifact_schema")
        for token in (b"NaN", b"Infinity", b"-Infinity"):
            self.assert_quality(SOURCE, ARTIFACT.replace(b'"schema_version":1', b'"schema_version":' + token), False, "artifact_nonfinite")
        self.assert_quality(SOURCE, ARTIFACT[:-1] + b',"extra":0}', False, "artifact_schema")

    def test_duplicate_keys_including_escaped_spelling(self):
        for duplicate in (b'"schema_version":1,', b'"schema_versi\\u006fn":1,'):
            self.assert_quality(SOURCE, b"{" + duplicate + ARTIFACT[1:], False, "artifact_duplicate_key")
        self.assert_quality(SOURCE, ARTIFACT.replace(b'"start":0', b'"start":0,"start":0'), False, "artifact_duplicate_key")

    def test_json_encoding_and_closed_malformed_bytes(self):
        for artifact, reason in (
            (b"", "artifact_json"),
            (b"\xef\xbb\xbf" + ARTIFACT, "artifact_json"),
            (ARTIFACT + b"\xff", "artifact_utf8"),
            (ARTIFACT + b"{}", "artifact_json"),
            (ARTIFACT[:-1], "artifact_json"),
        ):
            self.assert_quality(SOURCE, artifact, False, reason)

    def test_byte_caps_have_different_meanings(self):
        self.assert_quality(SOURCE, ARTIFACT + b" " * (65536 - len(ARTIFACT)), True, "matches")
        oversize = ARTIFACT + b" " * (65537 - len(ARTIFACT))
        result = self.assert_quality(SOURCE, oversize, False, "artifact_size")
        self.assertEqual(result.artifact_sha256, hashlib.sha256(oversize).hexdigest())
        self.assert_quality(b"x" * 8193, ARTIFACT, None, "source_capacity")

    def test_missing_inputs_remain_unknown_and_bind_available_bytes(self):
        a = self.assert_quality(None, ARTIFACT, None, "missing_source")
        b = self.assert_quality(SOURCE, None, None, "missing_artifact")
        self.assert_quality(None, None, None, "missing_source")
        self.assertIsNone(a.source_sha256)
        self.assertEqual(a.artifact_sha256, hashlib.sha256(ARTIFACT).hexdigest())
        self.assertEqual(b.source_sha256, hashlib.sha256(SOURCE).hexdigest())
        self.assertIsNone(b.artifact_sha256)

    def test_nonbytes_are_unavailable(self):
        for value in ("alpha\nbeta", bytearray(SOURCE), memoryview(SOURCE), 10):
            self.assert_quality(value, ARTIFACT, None, "input_type")
        self.assert_quality(SOURCE, ARTIFACT.decode(), None, "input_type")

    def test_numeric_and_recursion_guards_are_not_modified(self):
        before = (sys.get_int_max_str_digits(), sys.getrecursionlimit())
        huge = ARTIFACT.replace(b'"schema_version":1', b'"schema_version":' + b"9" * 5000)
        self.assert_quality(SOURCE, huge, False, "content_mismatch")
        self.assert_quality(SOURCE, ARTIFACT.replace(b'"start":0', b'"start":-0'), True, "matches")
        # Observed capacity control for the pinned Python 3.12.9 runtime;
        # Python's recursionlimit is not the JSON scanner's portable threshold.
        depth = 32000
        self.assertLess(depth * 2 + 1, 65536)
        self.assert_quality(SOURCE, b"[" * depth + b"0" + b"]" * depth, None, "checker_capacity")
        self.assertEqual(before, (sys.get_int_max_str_digits(), sys.getrecursionlimit()))

    def test_parser_resource_failure_remains_unavailable(self):
        with patch("epiphysics.prospective_quality.json.loads", side_effect=MemoryError):
            self.assert_quality(SOURCE, ARTIFACT, None, "checker_capacity")

    def test_frozen_private_controls_if_available(self):
        location = os.environ.get("EPIPHYSICS_QUALITY_CONTROLS")
        if not location:
            self.skipTest("private pre-execution controls unavailable; no evidence claim")
        root = Path(location)
        if not (root / "controls.json").is_file():
            self.skipTest("private pre-execution controls missing; no evidence claim")
        manifest = json.loads((root / "controls.json").read_bytes())
        for case in manifest["cases"]:
            with self.subTest(case=case["id"]):
                values = []
                for name in ("source", "artifact"):
                    reference = case[name]
                    if reference is None:
                        values.append(None)
                    else:
                        raw = (root / reference["path"]).read_bytes()
                        self.assertEqual(len(raw), reference["bytes"])
                        self.assertEqual(hashlib.sha256(raw).hexdigest(), reference["sha256"])
                        values.append(raw)
                self.assert_quality(*values, case["quality"], case["reason"])


if __name__ == "__main__":
    unittest.main()
