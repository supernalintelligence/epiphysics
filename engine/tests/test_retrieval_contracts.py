"""Owned contract fixtures: historical validation never executes retained code."""
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from epiphysics import retrieval_contracts as contracts
from epiphysics import retrieval_evaluation as evaluation
from epiphysics.store import Ledger, canonical, digest


def span(raw, start=0, end=None):
    end = len(raw) if end is None else end
    return {"observation_id": "source", "start": start, "end": end, "sha256": digest(raw[start:end])}


def piece(raw, kind, output_start, output_end, source_start=None, source_end=None):
    source = None if kind == "separator" else {"start": source_start, "end": source_end,
                                               "sha256": digest(raw[source_start:source_end])}
    return {"kind": kind, "start": output_start, "end": output_end, "source": source}


def projection(raw, text=None, mapping=None, recipe=contracts.RAW_RECIPE):
    text = raw.decode() if text is None else text
    mapping = [piece(raw, "copy", 0, len(raw), 0, len(raw))] if mapping is None else mapping
    return {"schema_version": 1, "recipe": recipe, "rows": [{**span(raw), "indexed_text": text,
            "indexed_text_sha256": digest(text.encode()), "indexed_bytes": len(text.encode()), "mapping": mapping}]}


def validate(raw, value, media_type="text/html", **kwargs):
    return contracts.validate_projection({"source": {"raw": raw, "media_type": media_type}}, [span(raw)], value, **kwargs)


class ProjectionContractTests(unittest.TestCase):
    def test_raw_and_non_html_copy_are_exact_and_pure(self):
        raw = "café <tag>&amp;\r\n".encode()
        for recipe, media in ((contracts.RAW_RECIPE, "text/html"), (contracts.HTML_RECIPE, "text/markdown")):
            value = projection(raw, recipe=recipe)
            with patch.object(Path, "open", side_effect=AssertionError("Pure validation cannot read files")), patch.object(Path, "read_bytes", side_effect=AssertionError("No file reads")):
                self.assertEqual(value, validate(raw, value, media))
        self.assertEqual("text/html", contracts.normalize_media_type("  TeXt/HTML ; charset=UTF-8"))

    def test_entity_decoder_is_bounded_literal_and_nonrecursive(self):
        for raw, expected in ((b"&amp;", b"&"), (b"&NotEqualTilde;", "≂̸".encode()),
                              (b"&#65;", b"A"), (b"&#x41;", b"A"), (b"&#0;", "�".encode()),
                              (b"&#11;", b""), (b"&amp;lt;", None), (b"&unknown;", None),
                              (b"&amp", None), (b"&#65", None), (b"&#" + b"1" * 64 + b";", None)):
            with self.subTest(raw=raw):
                self.assertEqual(expected, contracts.decode_entity(raw))
        with self.assertRaises(ValueError):
            contracts.decode_entity("&amp;")

    def test_copy_entity_separator_mapping_uses_exact_source_intervals(self):
        raw = b"a<b>&amp;</b>z"
        value = projection(raw, "a & z", [piece(raw, "copy", 0, 1, 0, 1), piece(raw, "separator", 1, 2),
            piece(raw, "entity", 2, 3, 4, 9), piece(raw, "separator", 3, 4), piece(raw, "copy", 4, 5, 13, 14)], contracts.HTML_RECIPE)
        # Correct final byte is at 13 only when counted against the complete raw source.
        value["rows"][0]["mapping"][-1] = piece(raw, "copy", 4, 5, len(raw) - 1, len(raw))
        self.assertEqual(value, validate(raw, value))
        for alter in (
            lambda v: v["rows"][0]["mapping"][1].update(source={"start": 1, "end": 4, "sha256": digest(raw[1:4])}),
            lambda v: v["rows"][0]["mapping"][2]["source"].update(sha256="0" * 64),
            lambda v: v["rows"][0]["mapping"][2].update(start=1),
            lambda v: v["rows"][0].update(indexed_text_sha256="0" * 64),
            lambda v: v.update(recipe=contracts.RAW_RECIPE),
        ):
            bad = deepcopy(value)
            alter(bad)
            with self.assertRaises(ValueError):
                validate(raw, bad)

    def test_zero_output_entities_preserve_deferred_gap_without_edge_spaces(self):
        raw = b"a<tag/>&#11;b"
        begin, end = raw.index(b"&"), raw.index(b";") + 1
        value = projection(raw, "a b", [piece(raw, "copy", 0, 1, 0, 1),
            piece(raw, "entity", 1, 1, begin, end), piece(raw, "separator", 1, 2),
            piece(raw, "copy", 2, 3, len(raw) - 1, len(raw))], contracts.HTML_RECIPE)
        self.assertEqual(value, validate(raw, value))
        raw = b"&#11;"
        value = projection(raw, "", [piece(raw, "entity", 0, 0, 0, len(raw))], contracts.HTML_RECIPE)
        self.assertEqual(value, validate(raw, value))
        raw = b"a&#11;b"
        value = projection(raw, "ab", [piece(raw, "copy", 0, 1, 0, 1), piece(raw, "entity", 1, 1, 1, len(raw)-1),
                                      piece(raw, "copy", 1, 2, len(raw)-1, len(raw))], contracts.HTML_RECIPE)
        self.assertEqual(value, validate(raw, value))

    def test_gaps_utf8_boundaries_and_fabricated_text_fail(self):
        raw = b"a<tag/>b"
        value = projection(raw, "ab", [piece(raw, "copy", 0, 1, 0, 1), piece(raw, "copy", 1, 2, len(raw)-1, len(raw))], contracts.HTML_RECIPE)
        with self.assertRaisesRegex(ValueError, "separator"):
            validate(raw, value)
        raw = "é".encode()
        value = projection(raw, "x", [piece(raw, "copy", 0, 1, 1, 2)], contracts.HTML_RECIPE)
        with self.assertRaises(ValueError):
            validate(raw, value)
        raw = b"&amp;"
        value = projection(raw, "x", [piece(raw, "entity", 0, 1, 0, len(raw))], contracts.HTML_RECIPE)
        with self.assertRaisesRegex(ValueError, "reconstruct"):
            validate(raw, value)

    def test_projection_bounds_and_deadline_are_explicit(self):
        raw = b"alpha"
        value = projection(raw)
        for key, maximum in (("MAX_MAPPING_PIECES", 0), ("MAX_INDEXED_WINDOW_BYTES", 4),
                             ("MAX_INDEXED_TOTAL_BYTES", 4), ("MAX_MAPPING_BYTES", 1), ("MAX_PROJECTION_BYTES", 1)):
            with self.subTest(key=key), patch.object(contracts, key, maximum), self.assertRaises(ValueError):
                validate(raw, value)
        with self.assertRaises(TimeoutError):
            validate(raw, value, deadline=time.monotonic() - 1)
        for malformed in ([], None, "projection", {"schema_version": 1, "recipe": contracts.RAW_RECIPE, "rows": []}):
            with self.assertRaises(ValueError):
                validate(raw, malformed)


class ReceiptContractTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.ledger = Ledger(Path(self.temp.name) / "evidence")
        self.addCleanup(self.ledger.close)
        self.raw = b"alpha &amp; beta"
        self.ledger.capture("owned:source", self.raw, media_type="text/html", event_id="source")
        self.snapshot = self.ledger.snapshot(event_id="snapshot")
        body, _ = contracts._build_corpus(self.ledger, "snapshot", ["source"], contracts._config(None),
                                         contracts._time(self.ledger.clock(), "now"))
        self.corpus = self.ledger.append("retrieval_corpus", body, "corpus")
        self.queries = [{"query_id": "q", "query": "alpha"}]
        self.cohort = {"schema_version": 1, "snapshot_id": "snapshot", "cohort": "development", "cases": [
            {"question_id": "q", "query": "alpha", "answerability": "answerable", "gold_spans": [span(self.raw)]}]}
        self.runtime = {"python_version": "owned", "python_implementation": "owned", "python_cache_tag": "owned", "python_optimize": 0,
            "unicode_version": "owned", "sqlite_version": "owned", "sqlite_source_id": "owned", "sqlite_compile_options": []}

    def receipt(self, key, version=1, recipe=contracts.RAW_RECIPE, mutate=None):
        request = contracts._request(self.ledger, "corpus", self.queries)
        if version == 2:
            request["indexing_recipe"] = recipe
        self.ledger.append("retrieval_started", {"schema_version": version, "run_key": key, "request": request}, f"retrieval:{key}:started")
        def retain(role, raw):
            event = self.ledger.capture(f"retrieval-input:{key}:{role}", raw, event_id=f"retrieval:{key}:input:{role}")
            return {"observation_id": event["id"], "event_hash": event["hash"], "content_hash": event["body"]["content_hash"], "size": len(raw)}
        deps = contracts.DEPENDENCY_NAMES if version == 1 else contracts.DEPENDENCY_NAMES_V2
        artifacts = {"config": retain("config", canonical(self.corpus["body"]["config"]).encode()),
            "queries": retain("queries", canonical(self.queries).encode()),
            "implementation": retain("code:epiphysics.retrieval", b"# historical bytes, never executed"),
            "dependencies": {name: retain("code:" + name, b"# retained " + name.encode()) for name in deps}}
        results = [{"query_id": "q", "query": "alpha", "status": "matched", "reason": None,
                    "hits": [{**span(self.raw), "rank": 1, "score": -1.0}]}]
        resources = {"elapsed_seconds": 0.0, "elapsed_scope": contracts.ELAPSED_SCOPE, "execution_budget_seconds": 30,
            "input_bytes": len(self.raw), "passages": 1, "queries": 1, "output_bytes": len(canonical(results).encode()), "model_calls": 0, "external_spend": 0}
        body = {"schema_version": version, "run_key": key, "request": request, "result": "completed", "corpus_id": "corpus",
            "corpus_hash": self.corpus["hash"], "config_hash": self.corpus["body"]["config_hash"], "query_hash": request["query_hash"],
            "artifacts": artifacts, "runtime": deepcopy(self.runtime), "runtime_hash": digest(canonical(self.runtime).encode()),
            "implementation_hash": artifacts["implementation"]["content_hash"], "results": results, "results_hash": digest(canonical(results).encode()),
            "resources": resources, "scope": contracts.SCOPE}
        if version == 2:
            value = projection(self.raw, recipe=recipe)
            if recipe == contracts.HTML_RECIPE:
                value = projection(self.raw, "alpha & beta", [piece(self.raw, "copy", 0, 6, 0, 6),
                    piece(self.raw, "entity", 6, 7, 6, 11), piece(self.raw, "copy", 7, 12, 11, 16)], recipe)
                value["rows"][0]["mapping"][-1] = piece(self.raw, "copy", 7, 12, 11, len(self.raw))
            raw = canonical(value).encode()
            artifacts["recipe"] = retain("recipe", canonical({"schema_version": 1, "indexing_recipe": recipe}).encode())
            artifacts["projection"] = {"schema_version": 1, "sha256": digest(raw), "size": len(raw), "chunks": [retain("projection:0000", raw)]}
            decoder = contracts._decoder_sources()
            artifacts["stdlib"] = {name: retain(("data:" if name == "html.entities.html5" else "code:") + name,
                decoder.get(name, b"# retained " + name.encode())) for name in contracts.STDLIB_NAMES}
            body.update(indexing_recipe=recipe, projection_hash=digest(raw))
            resources.update(projection_bytes=len(raw), indexed_bytes=sum(row["indexed_bytes"] for row in value["rows"]),
                             mapping_pieces=sum(len(row["mapping"]) for row in value["rows"]), empty_windows=0)
        if mutate:
            mutate(body)
        return self.ledger.append("retrieval_completed", body, f"retrieval:{key}:terminal")

    def test_legacy_literal_artifact_namespace_and_exact_receipt_survive(self):
        event = self.receipt("legacy")
        before = self.ledger.events()
        self.assertEqual(event, contracts.get_retrieval_run(self.ledger, event["id"]))
        self.assertEqual(event, contracts.get_retrieval_run(self.ledger, event["id"], verify_bytes=False))
        report = evaluation.evaluate_retrieval(self.ledger, self.cohort, event["id"])
        self.assertEqual(1, report["metrics"]["gold_span_recall_at_k"]["5"]["value"])
        self.assertEqual("legacy-coupled-v1", report["identity"]["candidate"]["algorithm"]["kind"])
        self.assertEqual(before, self.ledger.events())

    def test_v2_both_recipes_keep_raw_window_scoring_and_neutral_measurement(self):
        raw = self.receipt("raw", 2)
        html = self.receipt("html", 2, contracts.HTML_RECIPE)
        reports = [evaluation.evaluate_retrieval(self.ledger, self.cohort, event["id"]) for event in (raw, html)]
        self.assertEqual(reports[0]["metrics"], reports[1]["metrics"])
        self.assertEqual(reports[0]["per_case"], reports[1]["per_case"])
        self.assertEqual(reports[0]["identity"]["evaluator"], reports[1]["identity"]["evaluator"])
        self.assertNotEqual(reports[0]["identity"]["candidate"]["algorithm_hash"], reports[1]["identity"]["candidate"]["algorithm_hash"])
        self.assertNotIn("epiphysics.retrieval", reports[0]["identity"]["evaluator"]["dependencies"])
        self.assertNotIn("epiphysics.retrieval_indexing", reports[0]["identity"]["evaluator"]["dependencies"])
        for event in (raw, html):
            self.assertEqual(event, contracts.get_retrieval_run(self.ledger, event["id"]))

    def test_unknown_schema_wrong_projection_binding_and_counts_refuse(self):
        variants = [lambda body: body.update(schema_version=3),
                    lambda body: body.update(projection_hash="0" * 64),
                    lambda body: body["resources"].update(indexed_bytes=0),
                    lambda body: body["artifacts"]["projection"].update(size=contracts.MAX_PROJECTION_BYTES + 1),
                    lambda body: body.update(indexing_recipe=contracts.HTML_RECIPE)]
        for index, mutate in enumerate(variants):
            event = self.receipt(f"bad-{index}", 2, mutate=mutate)
            with self.subTest(index=index), self.assertRaises(ValueError):
                contracts.get_retrieval_run(self.ledger, event["id"])

    def test_historical_metadata_lookup_is_not_blob_availability(self):
        event = self.receipt("history", 2)
        ref = event["body"]["artifacts"]["projection"]["chunks"][0]
        (self.ledger.root / "blobs" / ref["content_hash"]).unlink()
        self.assertEqual(event, contracts.get_retrieval_run(self.ledger, event["id"], verify_bytes=False))
        with self.assertRaises(ValueError):
            contracts.get_retrieval_run(self.ledger, event["id"])

    def test_declared_chunk_bound_refuses_before_blob_read(self):
        event = self.receipt("huge", 2, mutate=lambda body: body["artifacts"]["projection"]["chunks"][0].update(size=contracts.MAX_BYTES + 1))
        with self.assertRaisesRegex(ValueError, "chunk exceeds"):
            contracts.get_retrieval_run(self.ledger, event["id"])

    def test_coherent_wrong_decoder_artifact_refuses_current_byte_validation(self):
        def mutate(body):
            event = self.ledger.capture("retrieval-input:wrong-decoder:code:html", b"different decoder", event_id="wrong-html")
            body["artifacts"]["stdlib"]["html"] = {"observation_id": event["id"], "event_hash": event["hash"],
                "content_hash": event["body"]["content_hash"], "size": event["body"]["size"]}
        event = self.receipt("wrong-decoder", 2, mutate=mutate)
        self.assertEqual(event, contracts.get_retrieval_run(self.ledger, event["id"], verify_bytes=False))
        with self.assertRaisesRegex(ValueError, "decoder differs"):
            contracts.get_retrieval_run(self.ledger, event["id"])

    def test_replaced_ledger_method_and_neutral_alias_refuse(self):
        with patch.object(Ledger, "get", lambda *args: {}), self.assertRaisesRegex(ValueError, "ledger method changed"):
            contracts._runtime_sources()
        with patch.object(contracts, "digest", lambda *args: "0" * 64), self.assertRaisesRegex(ValueError, "alias changed"):
            contracts._runtime_sources()


if __name__ == "__main__":
    unittest.main()
