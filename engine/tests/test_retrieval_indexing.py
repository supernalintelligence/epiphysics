"""Owned conformance fixtures for the two fixed C3 indexing recipes."""

from copy import deepcopy
import html.entities
import html.parser
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from epiphysics import retrieval_contracts as contracts
from epiphysics import retrieval_indexing as indexing


def source(raw, media_type="text/html", oid="owned"):
    return {oid: {"raw": raw, "media_type": media_type}}


def span(raw, start=0, end=None, oid="owned"):
    end = len(raw) if end is None else end
    return {"observation_id": oid, "start": start, "end": end, "sha256": contracts.digest(raw[start:end])}


def windows(sources):
    rows = contracts._passages({oid: item["raw"] for oid, item in sources.items()}, contracts.DEFAULT_CONFIG)
    return [{key: row[key] for key in ("observation_id", "start", "end", "sha256")} for row in rows]


def project(sources, recipe=indexing.HTML_RECIPE, manifest=None):
    return indexing.project_index(sources, windows(sources) if manifest is None else manifest,
                                  recipe, deadline=time.monotonic() + 30)


def search(rows, queries=None):
    return indexing.lexical_search(rows, [{"query_id": "q", "query": "cobalt"}] if queries is None else queries,
                                    contracts.DEFAULT_CONFIG, deadline=time.monotonic() + 30)


class ProjectionTests(unittest.TestCase):
    def test_raw_recipe_keeps_exact_windows_hashes_order_and_one_copy_map(self):
        raw = ("🦉café alpha " * 600).encode()
        sources = source(raw)
        manifest = windows(sources)
        result = project(sources, indexing.RAW_RECIPE)
        self.assertEqual(manifest, [{key: row[key] for key in manifest[0]} for row in result["rows"]])
        for row in result["rows"]:
            selected = raw[row["start"]:row["end"]]
            self.assertEqual(selected, row["indexed_text"].encode())
            self.assertEqual(row["sha256"], row["indexed_text_sha256"])
            self.assertEqual([{"kind": "copy", "start": 0, "end": len(selected), "source": {
                "start": row["start"], "end": row["end"], "sha256": contracts.digest(selected)}}], row["mapping"])

    def test_non_html_markdown_is_verbatim_in_both_recipes(self):
        raw = b'# Cobalt\n<script>literal Markdown</script> &amp; <b>words</b>'
        sources = source(raw, "text/markdown; charset=utf-8")
        raw_rows = project(sources, indexing.RAW_RECIPE)["rows"]
        html_rows = project(sources)["rows"]
        self.assertEqual(raw_rows, html_rows)
        self.assertEqual(raw, html_rows[0]["indexed_text"].encode())

    def test_selected_media_metadata_controls_html_route(self):
        raw = b'<b>cobalt</b>'
        self.assertEqual("cobalt", project(source(raw, " TEXT/HTML ; charset=UTF-8"))["rows"][0]["indexed_text"])
        self.assertEqual(raw.decode(), project(source(raw, "application/example"))["rows"][0]["indexed_text"])

    def test_empty_sources_and_empty_html_windows_are_preserved(self):
        self.assertEqual([], project(source(b""))["rows"])
        raw = b'<head>cobalt</head>'
        projected = project(source(raw))
        self.assertEqual(1, len(projected["rows"]))
        row = projected["rows"][0]
        self.assertEqual("", row["indexed_text"])
        self.assertEqual(0, row["indexed_bytes"])
        self.assertEqual([], row["mapping"])
        self.assertEqual(contracts.digest(raw), row["sha256"])
        self.assertEqual("no_lexical_match", search(projected["rows"])[0]["reason"])

    def test_input_bounds_and_shapes_refuse_before_parser_construction(self):
        valid = source(b"<b>cobalt</b>")
        invalid = [({}, []), ({"owned": {"raw": b"x" * 1_000_001, "media_type": "text/html"}}, []),
                   ({str(i): {"raw": b"x" * 900_000, "media_type": "text/html"} for i in range(5)}, []),
                   ({"owned": {**valid["owned"], "gold": []}}, windows(valid)),
                   (valid, [{**windows(valid)[0], "gold": []}]),
                   (valid, [span(b"wrong", oid="not-selected")]),
                   (valid, [windows(valid)[0]] * 4097),
                   (valid, [windows(valid)[0], windows(valid)[0]])]
        with patch.object(indexing, "_TextNodes", side_effect=AssertionError("Parsed invalid input")):
            for sources, manifest in invalid:
                with self.subTest(source_count=len(sources)), self.assertRaises(ValueError):
                    project(sources, manifest=manifest)
        with self.assertRaisesRegex(ValueError, "fixed indexing recipe"):
            project(valid, "caller-defined")

    def test_invalid_full_utf8_and_mid_codepoint_windows_refuse(self):
        with self.assertRaises(UnicodeDecodeError):
            project(source(b"cobalt\xff"), manifest=[])
        raw = "é cobalt".encode()
        with self.assertRaises(UnicodeDecodeError):
            project(source(raw), manifest=[span(raw, 1)])

    def test_pure_projection_and_search_do_not_read_files(self):
        with patch.object(Path, "open", side_effect=AssertionError("Pure candidate opened a file")), \
                patch.object(Path, "read_bytes", side_effect=AssertionError("Pure candidate read a file")):
            rows = project(source(b'<p>cobalt &amp; archive</p>'))["rows"]
            self.assertEqual("matched", search(rows)[0]["status"])

    def test_mapping_text_and_projection_bounds_fail_during_construction(self):
        sources = source(b'<p>cobalt</p><b>archive</b>')
        for name, maximum in (("MAX_MAPPING_PIECES", 2), ("MAX_INDEXED_WINDOW_BYTES", 5),
                              ("MAX_INDEXED_TOTAL_BYTES", 5), ("MAX_MAPPING_BYTES", 20),
                              ("MAX_PROJECTION_BYTES", 100)):
            with self.subTest(bound=name), patch.object(contracts, name, maximum), self.assertRaises(ValueError):
                project(sources)


class HTMLProjectionTests(unittest.TestCase):
    def text(self, raw):
        return project(source(raw))["rows"][0]["indexed_text"]

    def test_excludes_markup_attributes_comments_and_head_script_style_only(self):
        raw = (b'<!doctype html><head><title>headword</title></head><body>'
               b'<p data-url="https://example.invalid/cobalt" hidden>visible</p>'
               b'<!-- cobalt --><script>cobalt</script><style>.cobalt{}</style><?cobalt?>'
               b'<noscript>fallback</noscript><template>templateword</template></body>')
        result = project(source(raw))
        self.assertEqual("visible fallback templateword", result["rows"][0]["indexed_text"])
        self.assertEqual("empty", search(result["rows"])[0]["status"])
        queries = [{"query_id": "body", "query": "visible"}]
        self.assertEqual("matched", search(result["rows"], queries)[0]["status"])

    def test_nested_mismatched_unmatched_selfclosing_and_unclosed_exclusions(self):
        cases = {
            b'<head>hidden<head>also hidden</head>hidden</head>shown': 'shown',
            b'<head><style>hidden</style></head>shown': 'shown',
            b'</head><head/>shown': 'shown',
            b'<head>hidden<body>still hidden': '',
            b'a<script>if (a < b) { "<p>hidden</p>"; }</script>b': 'a b',
            b'co<b>balt</b>': 'co balt',
        }
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(expected, self.text(raw))

    def test_complete_document_context_excludes_window_starting_inside_head(self):
        raw = b'<head>' + b'cobalt ' * 600 + b'</head><p>archive</p>'
        rows = project(source(raw))["rows"]
        self.assertGreater(len(rows), 2)
        self.assertEqual("", rows[1]["indexed_text"])
        self.assertEqual("archive", rows[-1]["indexed_text"])
        self.assertFalse(any("cobalt" in row["indexed_text"] for row in rows))

    def test_utf8_crlf_and_repeated_nodes_use_exact_original_offsets(self):
        raw = '<p>🦉 café</p>\r\n<p>🦉 café</p>'.encode()
        row = project(source(raw))["rows"][0]
        self.assertEqual('🦉 café \r\n 🦉 café', row["indexed_text"])
        copied = [piece for piece in row["mapping"] if piece["kind"] == "copy"]
        expected_starts = [raw.index('🦉'.encode()), raw.index(b'\r\n'), raw.rindex('🦉'.encode())]
        self.assertEqual(expected_starts, [piece["source"]["start"] for piece in copied])
        for piece in copied:
            selected = raw[piece["source"]["start"]:piece["source"]["end"]]
            self.assertEqual(contracts.digest(selected), piece["source"]["sha256"])
            self.assertEqual(selected, row["indexed_text"].encode()[piece["start"]:piece["end"]])

    def test_entities_are_decoded_once_with_disjoint_source_lexemes(self):
        raw = b'<p>a&amp;b &#65; &#x1F989; &NotEqualTilde; &amp;lt; &notit; &copy next</p>'
        row = project(source(raw))["rows"][0]
        self.assertEqual('a&b A 🦉 ≂̸ &lt; &notit; &copy next', row["indexed_text"])
        entities = [piece for piece in row["mapping"] if piece["kind"] == "entity"]
        self.assertEqual(5, len(entities))
        self.assertFalse(any(piece["kind"] == "separator" for piece in row["mapping"]))
        for piece in entities:
            lexeme = raw[piece["source"]["start"]:piece["source"]["end"]]
            self.assertEqual(contracts.decode_entity(lexeme), row["indexed_text"].encode()[piece["start"]:piece["end"]])

    def test_invalid_numeric_and_zero_output_entities_keep_mapping_without_edge_spaces(self):
        cases = {b'a&#11;b': 'ab', b'a<b/>&#11;b': 'a b', b'&#11;<b/>b': 'b',
                 b'a<b/>&#11;': 'a', b'&#11;': '', b'&#0; &#xD800; &#x110000;': '� � �'}
        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                row = project(source(raw))["rows"][0]
                self.assertEqual(expected, row["indexed_text"])
                if b'&#11;' in raw:
                    self.assertTrue(any(piece["kind"] == "entity" and piece["start"] == piece["end"]
                                        for piece in row["mapping"]))

    def test_oversized_unknown_and_semicolonless_references_stay_literal(self):
        raw = b'&#' + b'1' * 65 + b'; &unknown; &copy &#65 next'
        self.assertEqual(raw.decode(), self.text(raw))

    def test_entity_crossing_a_raw_window_is_omitted_without_partial_provenance(self):
        raw = b'<p>ab&amp;cd</p>'
        manifest = [span(raw, 0, 7), span(raw, 3, 12)]
        rows = project(source(raw), manifest=manifest)["rows"]
        self.assertEqual(['ab', 'ab&cd'], [row["indexed_text"] for row in rows])
        self.assertFalse(any(piece["kind"] == "entity" for piece in rows[0]["mapping"]))
        for row in rows:
            for piece in row["mapping"]:
                if piece["source"]:
                    self.assertGreaterEqual(piece["source"]["start"], row["start"])
                    self.assertLessEqual(piece["source"]["end"], row["end"])

    def test_separators_have_no_source_support_and_citations_stay_raw(self):
        raw = b'<p>cobalt</p><!-- omitted --><p>archive</p>'
        row = project(source(raw))["rows"][0]
        self.assertEqual('cobalt archive', row["indexed_text"])
        separators = [piece for piece in row["mapping"] if piece["kind"] == "separator"]
        self.assertEqual(1, len(separators))
        self.assertIsNone(separators[0]["source"])
        self.assertEqual(contracts.digest(raw), row["sha256"])
        self.assertNotEqual(row["sha256"], row["indexed_text_sha256"])
        hit = search([row])[0]["hits"][0]
        self.assertEqual(span(raw), {key: hit[key] for key in span(raw)})
        self.assertEqual(set(span(raw)) | {"rank", "score"}, set(hit))

    def test_depth_and_parser_callback_offset_failures_are_explicit(self):
        raw = b'<head>' * 257 + b'owned'
        with self.assertRaisesRegex(ValueError, "nesting"):
            project(source(raw))
        original = indexing._TextNodes.handle_data

        def wrong_callback(parser, data):
            return original(parser, data + 'not in the source')

        with patch.object(indexing._TextNodes, "handle_data", wrong_callback), self.assertRaisesRegex(ValueError, "lexeme"):
            project(source(b'<p>cobalt</p>'))

    def test_deadline_expiring_during_html_callbacks_is_a_failure(self):
        original = indexing._TextNodes.handle_data
        clock, callbacks = [0.0], []

        def observed(parser, data):
            callbacks.append(data)
            if len(callbacks) == 2:
                clock[0] = 30.0
            return original(parser, data)

        sources = source(b'<p>first</p><p>second</p>')
        with patch.object(indexing.time, "monotonic", lambda: clock[0]), \
                patch.object(indexing._TextNodes, "handle_data", observed), self.assertRaises(TimeoutError):
            indexing.project_index(sources, windows(sources), indexing.HTML_RECIPE, deadline=30.0)
        self.assertEqual(['first', 'second'], callbacks)


class IndexedSearchTests(unittest.TestCase):
    def test_raw_reference_exact_scores_ties_and_empty_reasons(self):
        raw = b'alpha beta release date'
        sources = {**source(raw, "text/plain", "b"), **source(raw, "text/plain", "a")}
        rows = project(sources, indexing.RAW_RECIPE)["rows"]
        queries = [{"query_id": "hit", "query": "alpha beta"}, {"query_id": "miss", "query": "zygomaticnebula"},
                   {"query_id": "empty", "query": '?!_"'}]
        result = search(rows, queries)
        expected_hits = [{"rank": rank, **span(raw, oid=oid), "score": -2e-6} for rank, oid in enumerate(('a', 'b'), 1)]
        self.assertEqual(expected_hits, result[0]["hits"])
        self.assertEqual([('empty', 'no_lexical_match'), ('empty', 'no_query_terms')],
                         [(row["status"], row["reason"]) for row in result[1:]])
        self.assertEqual(result, search(rows, queries))

    def test_empty_rows_keep_fts_population_and_rowids(self):
        sources = {**source(b'<p>cobalt</p>', oid='a'), **source(b'<head>hidden</head>', oid='b'),
                   **source(b'<p>cobalt</p>', oid='c')}
        rows = project(sources)["rows"]
        original_connect, inserts = sqlite3.connect, []

        class TracedConnection(sqlite3.Connection):
            def execute(self, sql, parameters=(), /):
                if sql.startswith('INSERT INTO passages'):
                    inserts.append(parameters)
                return super().execute(sql, parameters)

        with patch.object(sqlite3, "connect", lambda *args, **kwargs: original_connect(*args, **kwargs, factory=TracedConnection)):
            full = search(rows)
        self.assertEqual([(1, 'cobalt'), (2, ''), (3, 'cobalt')], [(row[0], row[1]) for row in inserts])
        dropped = search([rows[0], rows[2]])
        self.assertNotEqual(full[0]["hits"][0]["score"], dropped[0]["hits"][0]["score"])

    def test_literal_queries_cannot_execute_fts_syntax_or_carry_gold(self):
        rows = project(source(b'<p>cobalt archive</p>'))["rows"]
        queries = [{"query_id": "literal", "query": '"cobalt" OR archive NOT NEAR(foo*) : (receipt)'}]
        self.assertEqual('matched', search(rows, queries)[0]['status'])
        with self.assertRaises(ValueError):
            search(rows, [{"query_id": "gold", "query": "cobalt", "gold_spans": []}])

    def test_malformed_indexed_text_hash_or_raw_span_refuses(self):
        original = project(source(b'<p>cobalt</p>'))["rows"]
        for field, value in (("indexed_text", 'changed'), ("indexed_bytes", True),
                             ("start", True), ("sha256", 'not-a-hash'), ("mapping", {})):
            rows = deepcopy(original)
            rows[0][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                search(rows)

    def test_deadline_and_sqlite_failures_never_become_successful_empty(self):
        sources = source(b'<p>cobalt</p>')
        with self.assertRaises(TimeoutError):
            indexing.project_index(sources, windows(sources), indexing.HTML_RECIPE, deadline=0)
        rows = project(sources)["rows"]
        with self.assertRaises(TimeoutError):
            indexing.lexical_search(rows, [{"query_id": "q", "query": "cobalt"}], contracts.DEFAULT_CONFIG, deadline=0)
        with patch.object(sqlite3, "connect", side_effect=sqlite3.OperationalError('owned failure')):
            with self.assertRaisesRegex(sqlite3.OperationalError, 'owned failure'):
                search(rows)


class IndexingIdentityTests(unittest.TestCase):
    def test_identity_retains_exact_fixed_sources_and_entity_table(self):
        sources = indexing.runtime_sources()
        self.assertEqual({'epiphysics.retrieval_indexing', 'html', 'html.parser', 'html.entities',
                          '_markupbase', 'html.entities.html5'}, set(sources))
        self.assertEqual(Path(indexing.__file__).read_bytes(), sources['epiphysics.retrieval_indexing'])
        self.assertEqual(contracts.canonical(html.entities.html5).encode(), sources['html.entities.html5'])

    def test_changed_parser_method_class_or_entity_table_refuses_identity(self):
        with patch.object(html.parser.HTMLParser, 'feed', lambda *args: None), self.assertRaisesRegex(ValueError, 'callable'):
            indexing.runtime_sources()
        with patch.object(indexing, '_TextNodes', object), self.assertRaisesRegex(ValueError, 'class changed'):
            indexing.runtime_sources()
        with patch.dict(html.entities.html5, {'owned;': 'changed'}), self.assertRaisesRegex(ValueError, 'entity table'):
            indexing.runtime_sources()

    def test_stale_timestamp_valid_candidate_bytecode_refuses_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shutil.copytree(Path(indexing.__file__).parent, root / 'epiphysics', ignore=shutil.ignore_patterns('__pycache__'))
            program = r'''
import json, os, py_compile
from pathlib import Path
path=Path('epiphysics/retrieval_indexing.py').resolve()
raw=path.read_bytes(); stat=path.stat()
py_compile.compile(str(path),doraise=True,invalidation_mode=py_compile.PycInvalidationMode.TIMESTAMP)
changed=raw.replace(b'MAX_EXCLUDED_DEPTH = 256',b'MAX_EXCLUDED_DEPTH = 255',1)
assert changed != raw and len(changed) == len(raw)
path.write_bytes(changed); os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
from epiphysics import retrieval_indexing as indexing
try:
    indexing.runtime_sources()
    outcome={'status':'unexpected_success'}
except ValueError as error:
    outcome={'status':'refused','message':str(error),'loaded_depth':indexing.MAX_EXCLUDED_DEPTH}
print(json.dumps(outcome))
'''
            completed = subprocess.run([sys.executable, '-s', '-c', program], cwd=root,
                env={**os.environ, 'PYTHONPATH': str(root), 'PYTHONDONTWRITEBYTECODE': '1'},
                capture_output=True, text=True, timeout=15)
            self.assertEqual(0, completed.returncode, completed.stderr)
            result = json.loads(completed.stdout)
            self.assertEqual('refused', result['status'])
            self.assertEqual(256, result['loaded_depth'])
            self.assertIn('retained source', result['message'])


if __name__ == '__main__':
    unittest.main()
