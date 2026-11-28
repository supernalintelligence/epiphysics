"""Pure, bounded production of the public version-1 line-index artifact.

Processing these bytes does not select a source or establish a delivery. The
execution driver must bind obligation identity, schema and submission channel.
"""

import hashlib
import json


SOURCE_BYTE_LIMIT = 8192
ARTIFACT_BYTE_LIMIT = 65536


class ProducerRefusal(ValueError):
    """A fixed capacity bound prevents returning a complete artifact."""


def produce_line_index(source: bytes) -> bytes:
    """Return canonical UTF-8 JSON for the exact supplied built-in bytes.

    Wrong types raise TypeError; exceeded capacities raise ProducerRefusal.
    Neither case returns partial output. UTF-8 validity, NUL exclusion, public
    provenance, minimum length and line-count eligibility belong to selection.
    """
    if type(source) is not bytes:
        raise TypeError("source must be built-in bytes")
    if len(source) > SOURCE_BYTE_LIMIT:
        raise ProducerRefusal("source byte limit exceeded")

    metadata = {
        "schema_version": 1,
        "source_byte_length": len(source),
        "source_sha256": hashlib.sha256(source).hexdigest(),
    }
    tail = b"]," + json.dumps(
        metadata, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False, allow_nan=False,
    ).encode("utf-8")[1:]
    artifact = bytearray(b'{"lines":[')
    start = 0
    for index, value in enumerate(source):
        if value != 10 and index + 1 != len(source):
            continue
        end = index + 1
        row = json.dumps(
            {
                "start": start,
                "end": end,
                "sha256": hashlib.sha256(source[start:end]).hexdigest(),
            },
            sort_keys=True, separators=(",", ":"),
            ensure_ascii=False, allow_nan=False,
        ).encode("utf-8")
        separator = b"," if start else b""
        if len(artifact) + len(separator) + len(row) + len(tail) > ARTIFACT_BYTE_LIMIT:
            raise ProducerRefusal("artifact byte limit exceeded")
        artifact.extend(separator)
        artifact.extend(row)
        start = end
    artifact.extend(tail)
    return bytes(artifact)
