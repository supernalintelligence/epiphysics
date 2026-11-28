"""C22 saved-byte compatibility; invented fixtures, never delivery evidence.

Run this module alone. C22_RETAIN_DIRECTORY optionally names a NEW directory
outside the worktree for one retained execution; otherwise files are temporary.
All expectations are frozen before any producer/checker call. No private fixture
is needed and neither component's standalone tests or fixtures are imported.
"""

from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from epiphysics.prospective_producer import ProducerRefusal, produce_line_index
from epiphysics.prospective_quality import QualityResult, check_line_index


# Source literals and explicit raw partitions were authored separately. The
# 700-row boundary uses the declared numeric family [i, i+1) containing one LF;
# it is not inferred by splitting the source or inspecting either implementation.
CASES = (
    (
        "ordinary_lf", True,
        b"C22 maple log: keep this invented first line exactly as written, including its final LF.\n"
        b"The second entry records a copper kite beside a quiet stone bridge in an imaginary town.\n"
        b"The third entry ends this raw byte example with a terminal newline and no phantom row.\n",
        (
            (0, 89, b"C22 maple log: keep this invented first line exactly as written, including its final LF.\n"),
            (89, 178, b"The second entry records a copper kite beside a quiet stone bridge in an imaginary town.\n"),
            (178, 265, b"The third entry ends this raw byte example with a terminal newline and no phantom row.\n"),
        ), None,
    ),
    (
        "crlf_lone_cr", True,
        b"C22 cedar log: this first invented record closes with CRLF and preserves both bytes.\r\n"
        b"A carriage return\rinside this second record is content; only the later LF closes its row.\r\n"
        b"The final invented record has no terminal newline, retains another\rreturn, and stops here.",
        (
            (0, 86, b"C22 cedar log: this first invented record closes with CRLF and preserves both bytes.\r\n"),
            (86, 177, b"A carriage return\rinside this second record is content; only the later LF closes its row.\r\n"),
            (177, 267, b"The final invented record has no terminal newline, retains another\rreturn, and stops here."),
        ), None,
    ),
    (
        "multibyte", False, b"C22 caf\xc3\xa9 \xe2\x98\x82\n\xe7\x8c\xab\r\nfin\xf0\x9f\x8c\x97",
        ((0, 14, b"C22 caf\xc3\xa9 \xe2\x98\x82\n"), (14, 19, b"\xe7\x8c\xab\r\n"), (19, 26, b"fin\xf0\x9f\x8c\x97")), None,
    ),
    ("empty", False, b"", (), None),
    (
        "adjacent_lf", False, b"\nC22 blank-edge\n\ntrail",
        ((0, 1, b"\n"), (1, 16, b"C22 blank-edge\n"), (16, 17, b"\n"), (17, 22, b"trail")), None,
    ),
    (
        "artifact_capacity", False, b"\n" * 700,
        tuple((i, i + 1, b"\n") for i in range(700)),
        "artifact byte limit exceeded",
    ),
)


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def expected_artifact(source, partitions):
    """Encode declared literal partitions, without a line-splitting algorithm."""
    assert b"".join(raw for _, _, raw in partitions) == source
    for start, end, raw in partitions:
        assert source[start:end] == raw and end - start == len(raw)
    return canonical({
        "schema_version": 1,
        "source_sha256": hashlib.sha256(source).hexdigest(),
        "source_byte_length": len(source),
        "lines": [{"start": start, "end": end, "sha256": hashlib.sha256(raw).hexdigest()}
                  for start, end, raw in partitions],
    })


@dataclass(frozen=True)
class Binding:
    sha256: str
    byte_length: int

    @classmethod
    def of(cls, raw):
        return cls(hashlib.sha256(raw).hexdigest(), len(raw))


class RetentionFailure(ValueError):
    """No content judgment is licensed for missing or mismatched saved bytes."""


def save_once(path, raw):
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())


def verified_read(path, binding):
    try:
        raw = path.read_bytes()
    except FileNotFoundError as exc:
        raise RetentionFailure("missing_file") from exc
    if Binding.of(raw) != binding:
        raise RetentionFailure("binding_mismatch")
    return raw


def check_saved(source_path, source_binding, artifact_path, artifact_binding):
    # A corruption, missing file or known prefix is stopped before the checker.
    source = verified_read(source_path, source_binding)
    artifact = verified_read(artifact_path, artifact_binding)
    return check_line_index(source, artifact)


class SavedArtifactRoundtripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.started = time.perf_counter()
        cls.temporary = None
        retained = os.environ.get("C22_RETAIN_DIRECTORY")
        if retained:
            cls.root = Path(retained)
            cls.root.mkdir()  # Existing runs cannot be overwritten or replayed.
        else:
            cls.temporary = tempfile.TemporaryDirectory(prefix="c22-roundtrip-")
            cls.root = Path(cls.temporary.name)
        cls.producer_calls = cls.checker_calls = 0
        cls.planned = []
        for name, size_line_eligible, source, partitions, refusal in CASES:
            expected = expected_artifact(source, partitions)
            folder = cls.root / name
            folder.mkdir()
            save_once(folder / "source.raw", source)
            save_once(folder / "expected-complete-artifact.json", expected)
            cls.planned.append({
                "case_id": name, "invented": True,
                "meets_size_and_line_bounds_only": size_line_eligible,
                "selected_public_source": False,
                "source": asdict(Binding.of(source)),
                "partitions": [{"start": a, "end": b, "raw_hex": raw.hex(), "sha256": Binding.of(raw).sha256}
                               for a, b, raw in partitions],
                "expected_complete_artifact": asdict(Binding.of(expected)),
                "expected_fields": json.loads(expected),
                "expected_producer": "refusal" if refusal else "complete",
                "expected_refusal": refusal,
                "expected_quality": None if refusal else True,
                "expected_reason": None if refusal else "matches",
            })
        cls.negative_source = b"C22 sealed negative control\n"
        # Both are intentionally authored COMPLETE content fixtures. Neither is
        # a lost/truncated producer output, despite the malformed JSON syntax.
        cls.negatives = (
            ("complete_malformed", b'{"lines": nope}', "artifact_json"),
            ("complete_wrong_content", canonical({
                "schema_version": 1, "source_sha256": "0" * 64,
                "source_byte_length": 28, "lines": [],
            }), "content_mismatch"),
        )
        cls.retention_controls = (
            "missing_source", "missing_artifact", "wrong_source_binding",
            "wrong_artifact_binding", "corrupt_copy", "truncated_copy",
        )
        # This complete manifest and all expected artifact bytes exist before
        # the first call into either accepted component.
        save_once(cls.root / "cohort.freeze.json", canonical({
            "record_type": "c22_invented_plan_v1", "cases": cls.planned,
            "retention_controls": [{"id": name, "checker_calls": 0, "quality": None,
                                    "expected_error": "missing_file" if name.startswith("missing") else "binding_mismatch"}
                                   for name in cls.retention_controls],
            "complete_negative_controls": [{"id": name, "source_hex": cls.negative_source.hex(),
                                            "artifact_hex": raw.hex(), "expected_quality": False,
                                            "expected_reason": reason}
                                           for name, raw, reason in cls.negatives],
            "exclusive_save_control": {"expected_error": "FileExistsError", "retains_original": True},
        }))

    @classmethod
    def tearDownClass(cls):
        save_once(cls.root / "execution-summary.json", canonical({
            "record_type": "c22_execution_counts_v1",
            "producer_calls": cls.producer_calls, "checker_calls": cls.checker_calls,
            "nested_test_body_seconds": time.perf_counter() - cls.started,
            "first_submission_established": False, "registration": False,
            "whole_agent_cost": None,
        }))
        if cls.temporary is not None:
            cls.temporary.cleanup()

    def test_10_planned_saved_roundtrips(self):
        for case, plan in zip(CASES, self.planned):
            name, eligible, original, partitions, refusal = case
            with self.subTest(case=name):
                folder = self.root / name
                source_binding = Binding(**plan["source"])
                source = verified_read(folder / "source.raw", source_binding)
                receipt = {"record_type": "c22_case_result_v1", "case_id": name,
                           "source": asdict(source_binding), "producer_calls": 1,
                           "checker_calls": 0, "artifact": None, "quality_result": None}
                type(self).producer_calls += 1
                began = time.perf_counter()
                try:
                    artifact = produce_line_index(source)
                except ProducerRefusal as exc:
                    raw_refusal = str(exc).encode("utf-8")
                    save_once(folder / "producer-refusal.txt", raw_refusal)
                    receipt.update(producer_status="refusal", refusal_type=type(exc).__name__,
                                   refusal_message=str(exc), refusal=asdict(Binding.of(raw_refusal)),
                                   retention_status="source_verified_no_artifact")
                except Exception as exc:
                    receipt.update(producer_status="unexpected_error", error_type=type(exc).__name__, error=str(exc))
                    raise
                else:
                    artifact_binding = Binding.of(artifact)
                    save_once(folder / "producer-output.json", artifact)
                    receipt.update(producer_status="complete", artifact=asdict(artifact_binding))
                    with patch(__name__ + ".check_line_index", wraps=check_line_index) as checker:
                        try:
                            result = check_saved(folder / "source.raw", source_binding,
                                                 folder / "producer-output.json", artifact_binding)
                        finally:
                            receipt["checker_calls"] = checker.call_count
                            type(self).checker_calls += checker.call_count
                    receipt.update(retention_status="verified", quality_result=asdict(result),
                                   quality_result_type=type(result).__name__)
                finally:
                    receipt["nested_case_seconds"] = time.perf_counter() - began
                    save_once(folder / "result.json", canonical(receipt))
                self.assertEqual(eligible, 256 <= len(original) <= 8192 and len(partitions) <= 128)
                self.assertEqual(receipt["producer_status"], plan["expected_producer"])
                if refusal:
                    self.assertEqual(receipt["refusal_message"], refusal)
                    self.assertGreater(plan["expected_complete_artifact"]["byte_length"], 65536)
                    self.assertIsNone(receipt["quality_result"])
                    self.assertEqual(receipt["checker_calls"], 0)
                else:
                    self.assertEqual(verified_read(folder / "producer-output.json", artifact_binding),
                                     verified_read(folder / "expected-complete-artifact.json",
                                                   Binding(**plan["expected_complete_artifact"])))
                    self.assertIsInstance(result, QualityResult)
                    self.assertEqual(asdict(result), {
                        "quality": True, "reason": "matches",
                        "source_sha256": source_binding.sha256,
                        "source_byte_length": source_binding.byte_length,
                        "artifact_sha256": artifact_binding.sha256,
                        "artifact_byte_length": artifact_binding.byte_length,
                    })

    def test_20_retention_failures_never_enter_quality(self):
        source = b""
        artifact = expected_artifact(source, ())
        for name in self.retention_controls:
            with self.subTest(control=name):
                folder = self.root / name
                folder.mkdir()
                save_once(folder / "intact-original-artifact.json", artifact)
                source_binding, artifact_binding = Binding.of(source), Binding.of(artifact)
                saved = artifact
                if name == "corrupt_copy":
                    saved = b"!" + artifact[1:]
                if name == "truncated_copy":
                    saved = artifact[:-1]
                if name == "wrong_source_binding":
                    source_binding = Binding.of(b"different source")
                if name == "wrong_artifact_binding":
                    artifact_binding = Binding.of(b"different artifact")
                if name != "missing_source":
                    save_once(folder / "source.raw", source)
                if name != "missing_artifact":
                    save_once(folder / "retained-copy.bin", saved)
                with patch(__name__ + ".check_line_index", wraps=check_line_index) as checker:
                    with self.assertRaises(RetentionFailure) as raised:
                        check_saved(folder / "source.raw", source_binding,
                                    folder / "retained-copy.bin", artifact_binding)
                    save_once(folder / "result.json", canonical({
                        "record_type": "c22_retention_control_v1", "control_id": name,
                        "source_binding": asdict(source_binding), "artifact_binding": asdict(artifact_binding),
                        "observed_source": None if name == "missing_source" else asdict(Binding.of(source)),
                        "observed_artifact": None if name == "missing_artifact" else asdict(Binding.of(saved)),
                        "error_type": type(raised.exception).__name__, "error": str(raised.exception),
                        "quality_result": None, "checker_calls": checker.call_count,
                        "is_original_producer_submission": False,
                    }))
                    checker.assert_not_called()
                    self.assertEqual(str(raised.exception), "missing_file" if name.startswith("missing") else "binding_mismatch")

    def test_30_intentionally_complete_negative_artifacts(self):
        for name, complete, reason in self.negatives:
            with self.subTest(control=name):
                folder = self.root / name
                folder.mkdir()
                source_binding, artifact_binding = Binding.of(self.negative_source), Binding.of(complete)
                save_once(folder / "source.raw", self.negative_source)
                save_once(folder / "complete-negative-artifact.bin", complete)
                with patch(__name__ + ".check_line_index", wraps=check_line_index) as checker:
                    result = check_saved(folder / "source.raw", source_binding,
                                         folder / "complete-negative-artifact.bin", artifact_binding)
                    type(self).checker_calls += checker.call_count
                save_once(folder / "result.json", canonical({
                    "record_type": "c22_complete_negative_v1", "control_id": name,
                    "intentionally_complete": True, "is_original_producer_submission": False,
                    "source": asdict(source_binding), "artifact": asdict(artifact_binding),
                    "quality_result_type": type(result).__name__, "quality_result": asdict(result),
                    "checker_calls": checker.call_count,
                }))
                self.assertEqual(result, QualityResult(False, reason, source_binding.sha256,
                                                      source_binding.byte_length, artifact_binding.sha256,
                                                      artifact_binding.byte_length))

    def test_40_exclusive_save_preserves_original(self):
        folder = self.root / "exclusive_save"
        folder.mkdir()
        original = b"C22 original retained bytes"
        save_once(folder / "original.raw", original)
        with self.assertRaises(FileExistsError):
            save_once(folder / "original.raw", b"replacement must never win")
        reread = verified_read(folder / "original.raw", Binding.of(original))
        save_once(folder / "result.json", canonical({
            "record_type": "c22_exclusive_save_control_v1", "error_type": "FileExistsError",
            "original": asdict(Binding.of(original)), "reread": asdict(Binding.of(reread)),
            "producer_calls": 0, "checker_calls": 0,
        }))
        self.assertEqual(reread, original)


if __name__ == "__main__":
    unittest.main()
