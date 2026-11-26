"""Two fixed source-window projections and pure, bounded FTS5 search.

Projection and search receive selected bytes and values only. Filesystem access
is confined to import-time source pinning and the separate runtime_sources
receipt helper. Neither path imports a runner, ledger, evaluator, or gold data.
"""

from __future__ import annotations

from array import array
from bisect import bisect_right
import _markupbase
import html
import html.entities
import html.parser
import math
from pathlib import Path
import sqlite3
import sys
import time
from types import CodeType

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code

from . import retrieval_contracts as contracts

IMPLEMENTATION_DEPENDENCIES = ((contracts.__name__, contracts.IMPLEMENTATION_CODE),)
RAW_RECIPE = contracts.RAW_RECIPE
HTML_RECIPE = contracts.HTML_RECIPE
RECIPE_IDS = contracts.RECIPE_IDS
MAX_EXCLUDED_DEPTH = 256
_SPAN_FIELDS = {"observation_id", "start", "end", "sha256"}
_ROW_FIELDS = _SPAN_FIELDS | {"indexed_text", "indexed_text_sha256", "indexed_bytes", "mapping"}
_EXCLUDED = frozenset(("head", "script", "style"))
_HTML_PARSER = html.parser.HTMLParser
_CONTRACT_CODE = contracts.IMPLEMENTATION_CODE
_CONTRACT_ALIASES = tuple((name, getattr(contracts, name)) for name in (
    "decode_entity", "normalize_media_type", "validate_projection", "_config", "_queries", "_terms",
    "_bounded_size", "_identifier", "_span_key", "_hash", "_keys", "canonical", "digest"))


def _deadline(deadline):
    if type(deadline) not in (int, float) or not math.isfinite(deadline):
        raise ValueError("Candidate deadline must be a finite monotonic timestamp")
    if time.monotonic() >= deadline:
        raise TimeoutError("Retrieval cooperative execution budget exceeded")


def _source_inputs(source_inputs, raw_manifest, deadline):
    if type(source_inputs) is not dict or not 1 <= len(source_inputs) <= contracts.MAX_SOURCES:
        raise ValueError("Candidate requires 1–64 explicitly selected sources")
    total = 0
    for oid, source in source_inputs.items():
        _deadline(deadline)
        contracts._identifier(oid, "Source observation ID")
        contracts._keys(source, {"raw", "media_type"}, "candidate source")
        if type(source["raw"]) is not bytes or len(source["raw"]) > contracts.MAX_BYTES:
            raise ValueError("Candidate source must be at most 1 MB of bytes")
        total += len(source["raw"])
        if total > contracts.MAX_TOTAL_BYTES:
            raise ValueError("Candidate source bytes exceed 4 MB")
        contracts.normalize_media_type(source["media_type"])
    if type(raw_manifest) is not list or len(raw_manifest) > contracts.MAX_PASSAGES:
        raise ValueError("Candidate requires at most 4096 raw windows")
    previous = None
    for span in raw_manifest:
        _deadline(deadline)
        contracts._keys(span, _SPAN_FIELDS, "raw window")
        contracts._identifier(span["observation_id"], "Window observation ID")
        contracts._hash(span["sha256"], "Raw window SHA-256")
        oid, start, end = span["observation_id"], span["start"], span["end"]
        if (oid not in source_inputs or type(start) is not int or type(end) is not int
                or not 0 <= start < end <= len(source_inputs[oid]["raw"]) or end - start > 2048):
            raise ValueError("Raw window must be a bounded selected source span")
        raw = source_inputs[oid]["raw"][start:end]
        raw.decode("utf-8", errors="strict")
        if contracts.digest(raw) != span["sha256"]:
            raise ValueError("Raw window hash mismatch")
        key = contracts._span_key(span)
        if previous is not None and key <= previous:
            raise ValueError("Raw windows must have distinct canonical ordering")
        previous = key
    # Bound all complete inputs before decoding even sources with no windows.
    return {oid: source["raw"].decode("utf-8", errors="strict")
            for oid, source in source_inputs.items()}


class _TextNodes(_HTML_PARSER):
    """Static text callbacks, with verified original UTF-8 byte positions."""

    def __init__(self, text, raw, deadline, maximum_pieces):
        self.text, self.raw, self.deadline = text, raw, deadline
        self.maximum_pieces = maximum_pieces
        self.atoms = []
        self.excluded = []
        self.byte_offsets = array("I", [0])
        self.line_starts = array("I", [0])
        offset = 0
        for index, char in enumerate(text):
            if index % 1024 == 0:
                _deadline(deadline)
            offset += len(char.encode("utf-8"))
            self.byte_offsets.append(offset)
            if char == "\n":
                self.line_starts.append(index + 1)
        super().__init__(convert_charrefs=False)

    def _position(self):
        _deadline(self.deadline)
        line, column = self.getpos()
        if not 1 <= line <= len(self.line_starts):
            raise ValueError("HTML callback line is outside its source")
        index = self.line_starts[line - 1] + column
        if not 0 <= index <= len(self.text):
            raise ValueError("HTML callback offset is outside its source")
        return index

    def _atom(self, kind, lexeme, decoded=None):
        index = self._position()
        stop = index + len(lexeme)
        if stop > len(self.text) or self.text[index:stop] != lexeme:
            raise ValueError("HTML callback lexeme does not match original source")
        start, end = self.byte_offsets[index], self.byte_offsets[stop]
        if not start < end or self.raw[start:end] != lexeme.encode("utf-8"):
            raise ValueError("HTML callback has invalid original byte bounds")
        if self.atoms and start < self.atoms[-1]["end"]:
            raise ValueError("HTML callback source intervals overlap or go backwards")
        if kind == "copy" and self.atoms and self.atoms[-1]["kind"] == "copy" and self.atoms[-1]["end"] == start:
            self.atoms[-1]["end"] = end
            return
        if len(self.atoms) >= self.maximum_pieces:
            raise ValueError("HTML projection exceeds its mapping piece limit")
        self.atoms.append({"kind": kind, "start": start, "end": end, "decoded": decoded})

    def handle_starttag(self, tag, attrs):
        _deadline(self.deadline)
        if tag in _EXCLUDED:
            if len(self.excluded) >= MAX_EXCLUDED_DEPTH:
                raise ValueError("HTML excluded nesting exceeds 256 levels")
            self.excluded.append(tag)

    def handle_endtag(self, tag):
        _deadline(self.deadline)
        if tag in self.excluded:
            index = len(self.excluded) - 1 - self.excluded[::-1].index(tag)
            del self.excluded[index:]

    def handle_startendtag(self, tag, attrs):
        _deadline(self.deadline)

    def handle_data(self, data):
        _deadline(self.deadline)
        if data and not self.excluded:
            self._atom("copy", data)

    def _reference(self, prefix, name):
        index = self._position()
        if self.excluded:
            return
        lexeme = prefix + name
        if self.text[index + len(lexeme):index + len(lexeme) + 1] == ";":
            lexeme += ";"
        decoded = contracts.decode_entity(lexeme.encode("utf-8"))
        self._atom("copy" if decoded is None else "entity", lexeme, decoded)

    def handle_entityref(self, name):
        self._reference("&", name)

    def handle_charref(self, name):
        self._reference("&#", name)

    def handle_comment(self, data):
        _deadline(self.deadline)

    def handle_decl(self, decl):
        _deadline(self.deadline)

    def handle_pi(self, data):
        _deadline(self.deadline)

    def unknown_decl(self, data):
        _deadline(self.deadline)


def project_index(source_inputs, raw_manifest, recipe, *, deadline):
    """Project two fixed recipes onto every supplied raw window, including empties.

    source_inputs maps selected IDs to exactly {raw: bytes, media_type: str}.
    No query is available to projection, and returned citations stay raw spans.
    """
    if sys._getframe().f_code is not project_index.__code__:
        raise ValueError("Stale indexing projector; use a fresh reviewed process")
    _deadline(deadline)
    if type(recipe) is not str or recipe not in RECIPE_IDS:
        raise ValueError("Unsupported fixed indexing recipe")
    decoded = _source_inputs(source_inputs, raw_manifest, deadline)
    atoms_by_source, ends_by_source, atom_count = {}, {}, 0
    for oid in sorted(source_inputs, key=lambda value: value.encode("utf-8")):
        _deadline(deadline)
        source = source_inputs[oid]
        if recipe == HTML_RECIPE and contracts.normalize_media_type(source["media_type"]) == "text/html":
            parser = _TextNodes(decoded[oid], source["raw"], deadline,
                                contracts.MAX_MAPPING_PIECES - atom_count)
            parser.feed(decoded[oid])
            parser.close()
            atoms = parser.atoms
        else:
            atoms = [{"kind": "copy", "start": 0, "end": len(source["raw"]), "decoded": None}] if source["raw"] else []
        atom_count += len(atoms)
        if atom_count > contracts.MAX_MAPPING_PIECES:
            raise ValueError("Projection exceeds its mapping piece limit")
        atoms_by_source[oid] = atoms
        ends_by_source[oid] = array("I", (atom["end"] for atom in atoms))
    projection = {"schema_version": 1, "recipe": recipe, "rows": []}
    projection_size = contracts._bounded_size(projection, contracts.MAX_PROJECTION_BYTES, "Projection")
    indexed_total, mapping_count, mapping_bytes = 0, 0, 0
    for span in raw_manifest:
        _deadline(deadline)
        raw = source_inputs[span["observation_id"]]["raw"]
        pieces, chunks, size, previous_end = [], [], 0, None
        has_output, pending_gap = False, False
        mapping_bytes += 2
        if mapping_bytes > contracts.MAX_MAPPING_BYTES:
            raise ValueError("Projection exceeds its mapping byte limit")

        def append_piece(kind, output, start=None, end=None):
            nonlocal size, mapping_count, mapping_bytes
            _deadline(deadline)
            if (size + len(output) > contracts.MAX_INDEXED_WINDOW_BYTES
                    or indexed_total + size + len(output) > contracts.MAX_INDEXED_TOTAL_BYTES):
                raise ValueError("Projection exceeds indexed text byte limits")
            if mapping_count >= contracts.MAX_MAPPING_PIECES:
                raise ValueError("Projection exceeds its mapping piece limit")
            source = None if kind == "separator" else {
                "start": start, "end": end, "sha256": contracts.digest(raw[start:end])}
            piece = {"kind": kind, "start": size, "end": size + len(output), "source": source}
            piece_size = contracts._bounded_size(piece, contracts.MAX_MAPPING_BYTES - mapping_bytes, "Mapping")
            if mapping_bytes + piece_size + bool(pieces) > contracts.MAX_MAPPING_BYTES:
                raise ValueError("Projection exceeds its mapping byte limit")
            mapping_bytes += piece_size + bool(pieces)
            mapping_count += 1
            pieces.append(piece)
            chunks.append(output)
            size += len(output)

        atoms = atoms_by_source[span["observation_id"]]
        first_atom = bisect_right(ends_by_source[span["observation_id"]], span["start"])
        for atom_index in range(first_atom, len(atoms)):
            atom = atoms[atom_index]
            _deadline(deadline)
            if atom["end"] <= span["start"]:
                continue
            if atom["start"] >= span["end"]:
                break
            if atom["kind"] == "entity":
                if atom["start"] < span["start"] or atom["end"] > span["end"]:
                    continue
                start, end, output = atom["start"], atom["end"], atom["decoded"]
            else:
                start, end = max(atom["start"], span["start"]), min(atom["end"], span["end"])
                output = raw[start:end]
                output.decode("utf-8", errors="strict")
            if previous_end is not None and previous_end != start:
                pending_gap = True
            if output and has_output and pending_gap:
                append_piece("separator", b" ")
            append_piece(atom["kind"], output, start, end)
            if output:
                has_output = True
                pending_gap = False
            previous_end = end
        indexed = b"".join(chunks)
        row = {**span, "indexed_text": indexed.decode("utf-8", errors="strict"),
               "indexed_text_sha256": contracts.digest(indexed), "indexed_bytes": size, "mapping": pieces}
        row_size = contracts._bounded_size(row, contracts.MAX_PROJECTION_BYTES - projection_size, "Projection row")
        projection_size += row_size + bool(projection["rows"])
        if projection_size > contracts.MAX_PROJECTION_BYTES:
            raise ValueError("Projection exceeds its canonical byte limit")
        indexed_total += size
        projection["rows"].append(row)
    _deadline(deadline)
    contracts.validate_projection(source_inputs, raw_manifest, projection, deadline=deadline)
    _deadline(deadline)
    return projection


def lexical_search(index_rows, queries, config, *, deadline):
    """Search validated projected rows in the unchanged disposable FTS5 table."""
    if sys._getframe().f_code is not lexical_search.__code__:
        raise ValueError("Stale indexed search; use a fresh reviewed process")
    _deadline(deadline)
    config, queries = contracts._config(config), contracts._queries(queries)
    if type(index_rows) is not list or len(index_rows) > contracts.MAX_PASSAGES:
        raise ValueError("Candidate requires at most 4096 indexed windows")
    contracts._bounded_size(index_rows, contracts.MAX_PROJECTION_BYTES, "Indexed windows")
    sizes, previous, indexed_total, mapping_count = {}, None, 0, 0
    for row in index_rows:
        _deadline(deadline)
        contracts._keys(row, _ROW_FIELDS, "indexed window")
        contracts._identifier(row["observation_id"], "Window observation ID")
        contracts._hash(row["sha256"], "Raw window SHA-256")
        if (type(row["start"]) is not int or type(row["end"]) is not int
                or not 0 <= row["start"] < row["end"] <= contracts.MAX_BYTES
                or row["end"] - row["start"] > 2048):
            raise ValueError("Indexed window must retain a bounded raw span")
        text = row["indexed_text"]
        if type(text) is not str or len(text) > contracts.MAX_INDEXED_WINDOW_BYTES:
            raise ValueError("Indexed text exceeds its window byte limit")
        encoded = text.encode("utf-8")
        if (len(encoded) > contracts.MAX_INDEXED_WINDOW_BYTES or type(row["indexed_bytes"]) is not int
                or row["indexed_bytes"] != len(encoded) or contracts.digest(encoded) != row["indexed_text_sha256"]):
            raise ValueError("Indexed text hash or size mismatch")
        if type(row["mapping"]) is not list:
            raise ValueError("Indexed window requires a mapping list")
        mapping_count += len(row["mapping"])
        indexed_total += len(encoded)
        sizes[row["observation_id"]] = max(sizes.get(row["observation_id"], 0), row["end"])
        if (mapping_count > contracts.MAX_MAPPING_PIECES or indexed_total > contracts.MAX_INDEXED_TOTAL_BYTES
                or len(sizes) > contracts.MAX_SOURCES or sum(sizes.values()) > contracts.MAX_TOTAL_BYTES):
            raise ValueError("Indexed corpus exceeds its bounds")
        key = contracts._span_key(row)
        if previous is not None and key <= previous:
            raise ValueError("Indexed windows require distinct canonical ordering")
        previous = key
    results = []
    connection = sqlite3.connect(":memory:")
    connection.row_factory = sqlite3.Row
    try:
        connection.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        connection.execute("CREATE VIRTUAL TABLE passages USING fts5(text, observation_id UNINDEXED, start UNINDEXED, end UNINDEXED, sha256 UNINDEXED, tokenize='unicode61 remove_diacritics 2')")
        for rowid, row in enumerate(index_rows, 1):
            _deadline(deadline)
            connection.execute("INSERT INTO passages(rowid,text,observation_id,start,end,sha256) VALUES(?,?,?,?,?,?)",
                (rowid, row["indexed_text"], row["observation_id"], row["start"], row["end"], row["sha256"]))
        for query in queries:
            _deadline(deadline)
            terms, hits = contracts._terms(query["query"]), []
            if terms:
                expression = " OR ".join('"' + term.replace('"', '""') + '"' for term in terms)
                rows = connection.execute("SELECT observation_id,start,end,sha256,bm25(passages) AS score FROM passages WHERE passages MATCH ? ORDER BY score ASC,observation_id COLLATE BINARY ASC,start ASC,end ASC,sha256 ASC LIMIT ?",
                    (expression, config["top_k"]))
                for rank, row in enumerate(rows, 1):
                    if not math.isfinite(row["score"]):
                        raise ValueError("Nonfinite BM25 score")
                    hits.append({"rank": rank, **dict(row)})
            results.append({**query, "status": "matched" if hits else "empty",
                "reason": None if hits else ("no_query_terms" if not terms else "no_lexical_match"), "hits": hits})
        _deadline(deadline)
    except sqlite3.OperationalError as error:
        if time.monotonic() >= deadline:
            raise TimeoutError("Retrieval cooperative execution budget exceeded") from error
        raise
    finally:
        connection.close()
    contracts._bounded_size(results, contracts.MAX_BYTES, "Retrieval results")
    return results


def _source_bytes(module):
    path = Path(module.__file__)
    if path.suffix != ".py" or path.is_symlink() or not path.is_file():
        raise ValueError(f"Fixed indexing source must be an available regular Python file: {module.__name__}")
    with path.open("rb") as stream:
        raw = stream.read(contracts.MAX_BYTES + 1)
    if len(raw) > contracts.MAX_BYTES:
        raise ValueError("Fixed indexing source exceeds 1 MB")
    return path, raw


def _callables(module):
    values = []
    for name, value in vars(module).items():
        if getattr(value, "__module__", None) != module.__name__:
            continue
        if hasattr(value, "__code__"):
            values.append((module, name, value, value.__code__))
        elif isinstance(value, type):
            for method_name, method in vars(value).items():
                if isinstance(method, (staticmethod, classmethod)):
                    method = method.__func__
                if hasattr(method, "__code__"):
                    values.append((value, method_name, method, method.__code__))
    return tuple(values)


def _compiled_codes(code):
    result = [code]
    for constant in code.co_consts:
        if isinstance(constant, CodeType):
            result.extend(_compiled_codes(constant))
    return result


def runtime_sources():
    """Fixed receipt helper; source reads never occur in project_index/search.

    Loaded functions must match retained source, including timestamp-valid stale
    bytecode. These local guards are not a security boundary against Python edits.
    """
    if sys._getframe().f_code is not runtime_sources.__code__:
        raise ValueError("Stale indexing identity helper; use a fresh reviewed process")
    if contracts.IMPLEMENTATION_CODE is not _CONTRACT_CODE:
        raise ValueError("Indexing contracts reloaded; use a fresh reviewed process")
    for name, function in _CONTRACT_ALIASES:
        if getattr(contracts, name) is not function:
            raise ValueError(f"Indexing contract callable changed: {name}")
    for module, name, cls in _PINNED_CLASSES:
        if getattr(module, name) is not cls:
            raise ValueError(f"Indexing class changed: {module.__name__}.{name}")
    sources = {}
    for module, path, retained, callables in _PINNED_SOURCES:
        if _source_bytes(module) != (path, retained):
            raise ValueError(f"Indexing source changed: {module.__name__}")
        compiled = _compiled_codes(compile(retained, str(path), "exec", dont_inherit=True, optimize=sys.flags.optimize))
        for owner, name, function, code in callables:
            current = vars(owner).get(name)
            if isinstance(current, (staticmethod, classmethod)):
                current = current.__func__
            if current is not function or function.__code__ is not code or code not in compiled:
                raise ValueError(f"Indexing loaded callable differs from retained source: {module.__name__}.{name}")
        if module is _MODULE and (module.IMPLEMENTATION_CODE is not IMPLEMENTATION_CODE
                or module.IMPLEMENTATION_SOURCE != retained or IMPLEMENTATION_CODE != compiled[0]):
            raise ValueError("Indexing module reloaded or does not match retained source")
        sources[module.__name__] = retained
    table = contracts.canonical(html.entities.html5).encode("utf-8")
    if table != _ENTITY_TABLE or html.parser.HTMLParser is not _HTML_PARSER:
        raise ValueError("Indexing parser or entity table changed")
    sources["html.entities.html5"] = table
    return sources


_MODULE = sys.modules[__name__]
_ENTITY_TABLE = contracts.canonical(html.entities.html5).encode("utf-8")
_PINNED_SOURCES = tuple((module, *_source_bytes(module), _callables(module))
    for module in (_MODULE, html, html.parser, html.entities, _markupbase))
_PINNED_CLASSES = tuple((module, name, value) for module, *_ in _PINNED_SOURCES
    for name, value in vars(module).items()
    if isinstance(value, type) and getattr(value, "__module__", None) == module.__name__)
