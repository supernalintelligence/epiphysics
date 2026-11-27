"""Independent content predicate for the declared raw-byte line index.

Only complete supplied artifact bytes belong here. This module has no evidence
access, producer dependency, submission broker, selection or outcome authority.
"""

from dataclasses import dataclass
import hashlib
import json


SOURCE_CAPACITY_BYTES = 8192
ARTIFACT_MAX_BYTES = 65536


@dataclass(frozen=True)
class QualityResult:
    """True/False are content judgments; None means checking was unavailable.

    Hashes identify exactly the supplied bytes, not a receipt or full stream.
    One reason identifies the first decisive check, not all possible defects.
    """

    quality: bool | None
    reason: str
    source_sha256: str | None
    source_byte_length: int | None
    artifact_sha256: str | None
    artifact_byte_length: int | None


@dataclass(frozen=True)
class _Integer:
    # Preserve unbounded JSON integer spelling without int conversion or a
    # process-wide digit-limit change. JSON's -0 denotes the integer zero.
    text: str


class _DuplicateKey(ValueError):
    pass


class _Nonfinite(ValueError):
    pass


def _integer(text: str) -> _Integer:
    return _Integer("0" if text == "-0" else text)


def _nonfinite(text: str) -> None:
    raise _Nonfinite(text)


def _object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(key)
        result[key] = value
    return result


def _nonnegative(value: object) -> bool:
    return type(value) is _Integer and not value.text.startswith("-")


def _digest(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(char in "0123456789abcdef" for char in value)
    )


def _content(source: bytes, artifact: bytes, source_hash: str) -> tuple[bool, str]:
    """Capacity exceptions are handled separately from invalid content."""
    try:
        text = artifact.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        return False, "artifact_utf8"
    try:
        value = json.loads(
            text,
            object_pairs_hook=_object,
            parse_int=_integer,
            # Every public numeric field requires an integer JSON primitive.
            # A float token is therefore wrong even if mathematically integral;
            # do not round or overflow an enormous exponent into a Python float.
            parse_float=lambda token: None,
            parse_constant=_nonfinite,
        )
    except _DuplicateKey:
        return False, "artifact_duplicate_key"
    except _Nonfinite:
        return False, "artifact_nonfinite"
    except json.JSONDecodeError:
        return False, "artifact_json"

    if type(value) is not dict or set(value) != {
        "schema_version", "source_sha256", "source_byte_length", "lines"
    }:
        return False, "artifact_schema"
    if (
        not _nonnegative(value["schema_version"])
        or not _digest(value["source_sha256"])
        or not _nonnegative(value["source_byte_length"])
        or type(value["lines"]) is not list
    ):
        return False, "artifact_schema"
    for line in value["lines"]:
        if type(line) is not dict or set(line) != {"start", "end", "sha256"}:
            return False, "artifact_schema"
        if (
            not _nonnegative(line["start"])
            or not _nonnegative(line["end"])
            or not _digest(line["sha256"])
        ):
            return False, "artifact_schema"
    if (
        value["schema_version"].text != "1"
        or value["source_byte_length"].text != str(len(source))
        or value["source_sha256"] != source_hash
    ):
        return False, "content_mismatch"

    # Walk original bytes. LF closes the current slice; CR is never removed.
    # Reaching length, including on a terminal LF, creates no additional line.
    start = 0
    index = 0
    while start < len(source):
        lf = source.find(b"\n", start)
        end = len(source) if lf == -1 else lf + 1
        if index >= len(value["lines"]):
            return False, "content_mismatch"
        line = value["lines"][index]
        if (
            line["start"].text != str(start)
            or line["end"].text != str(end)
            or line["sha256"] != hashlib.sha256(source[start:end]).hexdigest()
        ):
            return False, "content_mismatch"
        start = end
        index += 1
    if index != len(value["lines"]):
        return False, "content_mismatch"
    return True, "matches"


def check_line_index(source_bytes: bytes | None, artifact_bytes: bytes | None) -> QualityResult:
    """Check exact source bytes against one complete supplied artifact.

    None means unavailable input, not an empty stream. Only exact ``bytes``
    inputs are accepted. The caller is responsible for establishing completeness
    before supplying an artifact: a retained prefix must never enter this API.

    Source capacity is 8192 bytes, independent of selection eligibility. Source
    UTF-8/NUL/line-count/path/publication rules are not checked here. Artifact
    size above 65536 is a content failure; parser/runtime capacity is unknown.
    Empty artifact bytes fail JSON here; only the broker can decide whether a
    closed zero-byte stream represents no submission. No timing, acceptance,
    firstness, source eligibility, rights, payment or obligation result follows.
    """
    source_hash = artifact_hash = None
    source_length = len(source_bytes) if type(source_bytes) is bytes else None
    artifact_length = len(artifact_bytes) if type(artifact_bytes) is bytes else None

    def result(quality: bool | None, reason: str) -> QualityResult:
        return QualityResult(
            quality, reason, source_hash, source_length, artifact_hash, artifact_length
        )

    try:
        if type(source_bytes) is bytes:
            source_hash = hashlib.sha256(source_bytes).hexdigest()
        if type(artifact_bytes) is bytes:
            artifact_hash = hashlib.sha256(artifact_bytes).hexdigest()
        if source_bytes is None:
            return result(None, "missing_source")
        if artifact_bytes is None:
            return result(None, "missing_artifact")
        if type(source_bytes) is not bytes or type(artifact_bytes) is not bytes:
            return result(None, "input_type")
        if len(artifact_bytes) > ARTIFACT_MAX_BYTES:
            return result(False, "artifact_size")
        if len(source_bytes) > SOURCE_CAPACITY_BYTES:
            return result(None, "source_capacity")
        quality, reason = _content(source_bytes, artifact_bytes, source_hash)
        return result(quality, reason)
    except (MemoryError, RecursionError, OverflowError):
        return result(None, "checker_capacity")
