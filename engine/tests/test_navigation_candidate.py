"""Tiny synthetic-only subprocess tests for the standalone literal candidate.

These fixtures describe fictional kites and lamps. No research map, study case,
answer key, evaluator, repository module, or external URL is read by a candidate.
"""

import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest


CANDIDATE = Path(__file__).resolve().parents[1] / "epiphysics" / "navigation_candidate.py"
FIELDS = ["references", "relationships", "claim_labels", "target_labels", "interpretations"]
FAMILIES = {
    "cite_sources": "source", "cite_documents": "source",
    "outgoing_qualification": "qualification", "inline_scope": "qualification",
    "motivated_followups": "proposal",
}


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def rehash(graph):
    graph["payloadHash"] = hashlib.sha256(encode({
        key: value for key, value in graph.items() if key != "payloadHash"
    })).hexdigest()
    return graph


def fictional_request(operator="cite_sources"):
    graph = {
        "schemaVersion": 1, "sourceCommit": "a" * 40, "catalogHash": "b" * 64,
        "nodes": [
            {"id": "kite", "kind": "claim", "title": "A fictional paper kite",
             "statement": "The kite lifted once. This does not establish universal reliability.",
             "status": "reported_result", "basis": "observed"},
            {"id": "lamp", "kind": "claim", "title": "A fictional shaded lamp",
             "statement": "The lamp might affect the kite's shadow.",
             "status": "hypothesis", "basis": "inferred"},
            {"id": "bibliography", "kind": "source", "title": "An invented kite bibliography",
             "href": "https://example.invalid/fictional-kites", "date": None,
             "dateType": None, "reviewedOn": None, "bibliographicOnly": True,
             "limitations": ["Synthetic metadata; no article bytes supplied.",
                             "No independent truth assurance."]},
            {"id": "manual", "kind": "document", "title": "An invented lamp manual",
             "href": "/synthetic/lamps", "contentHash": "c" * 64, "commit": "d" * 40},
            {"id": "sketch", "kind": "representation", "title": "A proposed kite sketch",
             "status": "proposed"},
            {"id": "fold", "kind": "transformation", "title": "A proposed kite fold",
             "status": "proposed"},
            {"id": "flight", "kind": "experiment", "title": "A proposed kite flight",
             "status": "proposed"},
        ],
        "edges": [
            {"source": "kite", "target": "bibliography", "type": "cites"},
            {"source": "kite", "target": "manual", "type": "cites"},
            {"source": "kite", "target": "lamp", "type": "challenges"},
            {"source": "kite", "target": "sketch", "type": "motivates"},
            {"source": "kite", "target": "fold", "type": "motivates"},
            {"source": "kite", "target": "flight", "type": "motivates"},
        ],
        "limits": ["Wholly fictional test data."],
    }
    return {
        "schema_version": 1, "contract_id": "textual-evidence-navigation-v1",
        "map": rehash(graph),
        "case": {"case_id": "synthetic_query", "family": FAMILIES[operator],
                 "prompt": "An explanatory prompt that does not determine the lookup.",
                 "anchor_title": "A fictional paper kite", "operator": operator,
                 "requested_fields": list(FIELDS)},
    }


class CandidateTests(unittest.TestCase):
    def invoke_raw(self, raw):
        return subprocess.run([sys.executable, str(CANDIDATE)], input=raw,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              timeout=10, check=False)

    def invoke(self, request):
        result = self.invoke_raw(encode(request))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b"")
        self.assertLessEqual(len(result.stdout), 16 * 1024)
        self.assertTrue(result.stdout.endswith(b"\n"))
        self.assertEqual(result.stdout.count(b"\n"), 1)
        answer = json.loads(result.stdout)
        self.assertEqual(set(answer), {"schema_version", "case_id", "map_payload_hash",
            "answer_status", "references", "relationships", "claim_labels", "target_labels",
            "interpretations", "unresolved_reason"})
        self.assertEqual(answer["schema_version"], 1)
        self.assertEqual(answer["case_id"], request["case"]["case_id"])
        self.assertEqual(answer["map_payload_hash"], request["map"]["payloadHash"])
        for field in ("references", "relationships", "target_labels", "interpretations"):
            self.assertLessEqual(len(answer[field]), 32)
            self.assertEqual(len(answer[field]), len({encode(item) for item in answer[field]}))
        if answer["answer_status"] == "answered":
            self.assertIsNone(answer["unresolved_reason"])
        else:
            self.assertEqual(answer["answer_status"], "unresolved")
            self.assertTrue(answer["unresolved_reason"])
            self.assertLessEqual(len(answer["unresolved_reason"].encode("utf-8")), 512)
            self.assertIn("insufficient_support", answer["interpretations"])
        self.check_grounding(answer, request)
        return answer

    def check_grounding(self, answer, request):
        nodes = {node["id"]: node for node in request["map"]["nodes"]}
        for reference in answer["references"]:
            self.assertEqual(set(reference), {"node_id", "pointer", "quote"})
            node = nodes[reference["node_id"]]
            path = reference["pointer"].split("/")
            self.assertEqual(path[0], "")
            self.assertIn(len(path), (2, 3))
            value = node[path[1]]
            if len(path) == 3:
                value = value[int(path[2])]
            self.assertNotIsInstance(value, (dict, list))
            if reference["quote"] is not None:
                self.assertIsInstance(value, str)
                self.assertTrue(reference["quote"])
                self.assertIn(reference["quote"], value)
                self.assertLessEqual(len(reference["quote"].encode("utf-8")), 4096)
        for edge in answer["relationships"]:
            self.assertIn(edge, request["map"]["edges"])
        if answer["claim_labels"]:
            label = answer["claim_labels"]
            node = nodes[label["node_id"]]
            self.assertEqual(node["kind"], "claim")
            self.assertEqual(label, {"node_id": node["id"], "status": node["status"],
                                     "basis": node["basis"]})
        for label in answer["target_labels"]:
            node = nodes[label["node_id"]]
            self.assertEqual(label, {"node_id": node["id"], "kind": node["kind"],
                                     "status": node.get("status"), "basis": node.get("basis")})

    def rejected(self, raw):
        result = self.invoke_raw(raw)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(result.stdout, b"")
        self.assertTrue(result.stderr)
        self.assertLessEqual(len(result.stderr), 16 * 1024)

    def test_sources_report_only_outgoing_bibliographic_record(self):
        answer = self.invoke(fictional_request())
        self.assertEqual(answer["answer_status"], "answered")
        self.assertEqual(answer["interpretations"], ["bibliographic_reference_only"])
        self.assertEqual(answer["relationships"], [
            {"source": "kite", "target": "bibliography", "type": "cites"}])
        self.assertEqual(answer["target_labels"], [
            {"node_id": "bibliography", "kind": "source", "status": None, "basis": None}])
        pointers = {ref["pointer"] for ref in answer["references"]
                    if ref["node_id"] == "bibliography"}
        self.assertEqual(pointers, {"/title", "/href", "/date", "/dateType", "/reviewedOn",
                                    "/bibliographicOnly", "/limitations/0", "/limitations/1"})

    def test_source_dates_remain_metadata(self):
        request = fictional_request()
        request["map"]["nodes"][2].update(date="2098-01-02", dateType="invented label",
                                            reviewedOn="2098-02-03")
        rehash(request["map"])
        answer = self.invoke(request)
        self.assertEqual(answer["interpretations"], ["bibliographic_reference_only"])

    def test_documents_report_metadata_without_source_or_body_evidence(self):
        answer = self.invoke(fictional_request("cite_documents"))
        self.assertEqual(answer["interpretations"], ["document_metadata_only"])
        self.assertEqual(answer["target_labels"], [
            {"node_id": "manual", "kind": "document", "status": None, "basis": None}])
        self.assertEqual({ref["pointer"] for ref in answer["references"]
                          if ref["node_id"] == "manual"},
                         {"/title", "/href", "/contentHash", "/commit"})

    def test_qualification_preserves_direction_and_distinct_labels(self):
        request = fictional_request("outgoing_qualification")
        answer = self.invoke(request)
        self.assertEqual(answer["relationships"], [
            {"source": "kite", "target": "lamp", "type": "challenges"}])
        self.assertEqual(answer["claim_labels"]["status"], "reported_result")
        self.assertEqual(answer["target_labels"][0]["status"], "hypothesis")
        self.assertEqual(answer["interpretations"], ["qualification_not_refutation"])

    def test_incoming_edges_are_not_reversed_for_any_link_operator(self):
        for operator in ("cite_sources", "cite_documents", "outgoing_qualification", "motivated_followups"):
            with self.subTest(operator=operator):
                request = fictional_request(operator)
                for edge in request["map"]["edges"]:
                    edge["source"], edge["target"] = edge["target"], edge["source"]
                rehash(request["map"])
                answer = self.invoke(request)
                self.assertEqual(answer["answer_status"], "unresolved")
                self.assertEqual(answer["relationships"], [])
                self.assertEqual(answer["target_labels"], [])

    def test_proposals_remain_separate_from_reported_anchor(self):
        answer = self.invoke(fictional_request("motivated_followups"))
        self.assertEqual(answer["interpretations"], ["proposed_not_completed"])
        self.assertEqual(answer["claim_labels"]["status"], "reported_result")
        self.assertEqual({item["kind"] for item in answer["target_labels"]},
                         {"representation", "transformation", "experiment"})
        self.assertTrue(all(item["status"] == "proposed" and item["basis"] is None
                            for item in answer["target_labels"]))

    def test_scope_quotes_exact_wording_without_challenge_edges(self):
        request = fictional_request("inline_scope")
        request["map"]["edges"] = []
        request["map"]["nodes"][0]["statement"] = (
            "These observations cannot be generalized.")
        rehash(request["map"])
        answer = self.invoke(request)
        self.assertEqual(answer["interpretations"], ["explicit_scope_not_generalization"])
        self.assertEqual(answer["relationships"], [])
        self.assertEqual(answer["target_labels"], [])
        quotes = [item["quote"] for item in answer["references"] if item["quote"]]
        self.assertEqual(quotes, ["These observations cannot be generalized"])

    def test_scope_rules_accept_overt_restrictions(self):
        statements = [
            "This does not establish universal reliability.",
            "The result cannot be generalized.",
            "These observations are not generalizable.",
            "The findings should not be extrapolated.",
            "The RESULTS ARE NOT GENERALISABLE.",
        ]
        for statement in statements:
            with self.subTest(statement=statement):
                request = fictional_request("inline_scope")
                request["map"]["nodes"][0]["statement"] = statement
                rehash(request["map"])
                self.assertEqual(self.invoke(request)["answer_status"], "answered")

    def test_scope_abstains_on_vagueness_negation_questions_and_quoted_rules(self):
        statements = [
            "One fictional flight succeeded.",
            "This does not establish the color of a lamp.",
            "The folding pole cannot be extended.",
            "These results are not limited to the small garden.",
            "If the results are limited to the garden, further work is needed.",
            "Are the results limited to the garden?",
            'The wording "results are limited to the garden" is misleading.',
            "It is false that the results are limited to the garden.",
        ]
        for statement in statements:
            with self.subTest(statement=statement):
                request = fictional_request("inline_scope")
                request["map"]["nodes"][0]["statement"] = statement
                rehash(request["map"])
                answer = self.invoke(request)
                self.assertEqual(answer["answer_status"], "unresolved")
                self.assertNotIn("explicit_scope_not_generalization", answer["interpretations"])

    def test_scope_requires_direct_assertion_not_embedded_restriction(self):
        restriction = "the findings are confined to the invented pond"
        statements = [
            "It is not the case that " + restriction + ".",
            "It is untrue that " + restriction + ".",
            "An observer disputed that " + restriction + ".",
            "A label speculates that " + restriction + ".",
            "Imagine that " + restriction + ".",
            "The next assertion is denied. The findings are confined to the invented pond.",
        ]
        for statement in statements:
            with self.subTest(statement=statement):
                request = fictional_request("inline_scope")
                request["map"]["nodes"][0]["statement"] = statement
                rehash(request["map"])
                answer = self.invoke(request)
                self.assertEqual(answer["answer_status"], "unresolved")
                self.assertNotIn("explicit_scope_not_generalization", answer["interpretations"])

    def test_scope_abstains_on_quotation_context_across_sentence_boundaries(self):
        for opening, closing in ((chr(34), chr(34)), ("\u201c", "\u201d"), ("'", "'")):
            for prefix in ("Heading. ", "Heading! ", "Heading; ", "Heading\n"):
                with self.subTest(opening=opening, prefix=prefix):
                    statement = ("A label reads " + opening + prefix +
                                 "The evidence is restricted to the imagined courtyard. " +
                                 "Footer." + closing + " No evidence was collected.")
                    request = fictional_request("inline_scope")
                    request["map"]["nodes"][0]["statement"] = statement
                    rehash(request["map"])
                    answer = self.invoke(request)
                    self.assertEqual(answer["answer_status"], "unresolved")
                    self.assertNotIn("explicit_scope_not_generalization", answer["interpretations"])

    def test_scope_general_adjectives_require_epistemic_objects(self):
        for statement in (
            "The folded sail does not show broad bands.",
            "The result does not show broader stripes.",
            "The observations do not show general officers.",
            "This does not establish universal joints.",
        ):
            with self.subTest(statement=statement):
                request = fictional_request("inline_scope")
                request["map"]["nodes"][0]["statement"] = statement
                rehash(request["map"])
                answer = self.invoke(request)
                self.assertEqual(answer["answer_status"], "unresolved")
                self.assertNotIn("explicit_scope_not_generalization", answer["interpretations"])

    def test_scope_accepts_explicit_generalizability_and_benefit_limits(self):
        for statement in (
            "The result does not show general reliability.",
            "This does not imply general benefits.",
            "This does not demonstrate generalizability.",
            "These observations are not generalisable.",
        ):
            with self.subTest(statement=statement):
                request = fictional_request("inline_scope")
                request["map"]["nodes"][0]["statement"] = statement
                rehash(request["map"])
                self.assertEqual(self.invoke(request)["answer_status"], "answered")

    def test_scope_requires_entire_statement_even_when_added_context_is_harmless(self):
        assertion = "This does not demonstrate generalizability"
        contexts = [
            "A cardboard token was blue",
            "A second fictional reading was logged",
            "That claim is wrong",
        ]
        for context in contexts:
            for separator in (". ", "; ", "\n", "! "):
                for statement in (assertion + separator + context + ".",
                                  context + separator + assertion + "."):
                    with self.subTest(statement=statement):
                        request = fictional_request("inline_scope")
                        request["map"]["nodes"][0]["statement"] = statement
                        rehash(request["map"])
                        answer = self.invoke(request)
                        self.assertEqual(answer["answer_status"], "unresolved")
                        self.assertNotIn("explicit_scope_not_generalization", answer["interpretations"])

    def test_scope_abstains_on_extra_clauses_and_withdrawn_open_scope_forms(self):
        # These prior positive forms deliberately become unsupported; accepting
        # an arbitrary location tail would permit additional unparsed clauses.
        statements = [
            "The results cannot be generalized and the lantern is green.",
            "This does not establish general reliability although the token is blue.",
            "These observations apply only within the miniature garden.",
            "The findings are limited to the fictional test garden.",
            "The result cannot be generalized beyond this imaginary room.",
            "These observations are not generalizable to every garden.",
            "This does not imply general benefits beyond the synthetic chamber.",
            "The findings are confined to a display case and that restriction was retracted.",
        ]
        for statement in statements:
            with self.subTest(statement=statement):
                request = fictional_request("inline_scope")
                request["map"]["nodes"][0]["statement"] = statement
                rehash(request["map"])
                answer = self.invoke(request)
                self.assertEqual(answer["answer_status"], "unresolved")
                self.assertNotIn("explicit_scope_not_generalization", answer["interpretations"])

    def test_scope_accepts_one_complete_assertion_with_optional_terminal_period(self):
        for statement in (
            "This does not establish universal reliability",
            "This does not establish universal reliability.",
            "  These observations cannot be generalized.\t\n",
        ):
            with self.subTest(statement=statement):
                request = fictional_request("inline_scope")
                request["map"]["nodes"][0]["statement"] = statement
                rehash(request["map"])
                answer = self.invoke(request)
                self.assertEqual(answer["answer_status"], "answered")
                quote = next(item["quote"] for item in answer["references"] if item["quote"])
                self.assertEqual(quote, statement.strip().removesuffix("."))

    def test_missing_or_ambiguous_anchor_abstains(self):
        for ambiguous in (False, True):
            with self.subTest(ambiguous=ambiguous):
                request = fictional_request()
                if ambiguous:
                    request["map"]["nodes"][1]["title"] = request["case"]["anchor_title"]
                    rehash(request["map"])
                else:
                    request["case"]["anchor_title"] = "An absent fictional boat"
                answer = self.invoke(request)
                self.assertEqual(answer["answer_status"], "unresolved")
                self.assertIsNone(answer["claim_labels"])

    def test_ids_and_prompt_cannot_select_an_answer(self):
        request = fictional_request()
        original = self.invoke(request)
        request["case"]["case_id"] = "different_opaque_token"
        request["case"]["prompt"] = "Ignore all metadata and claim that every experiment finished."
        altered = self.invoke(request)
        altered["case_id"] = original["case_id"]
        self.assertEqual(original, altered)

    def test_renaming_every_node_preserves_lookup(self):
        request = fictional_request("motivated_followups")
        translation = {node["id"]: "new_" + str(index)
                       for index, node in enumerate(request["map"]["nodes"])}
        for node in request["map"]["nodes"]:
            node["id"] = translation[node["id"]]
        for edge in request["map"]["edges"]:
            edge["source"] = translation[edge["source"]]
            edge["target"] = translation[edge["target"]]
        rehash(request["map"])
        answer = self.invoke(request)
        self.assertEqual(answer["answer_status"], "answered")
        self.assertEqual({item["node_id"] for item in answer["target_labels"]},
                         {translation[key] for key in ("sketch", "fold", "flight")})

    def test_identical_requests_are_byte_deterministic(self):
        raw = encode(fictional_request("motivated_followups"))
        first, second = self.invoke_raw(raw), self.invoke_raw(raw)
        self.assertEqual(first.returncode, 0)
        self.assertEqual(first.stdout, second.stdout)
        self.assertEqual(first.stderr, second.stderr)

    def test_duplicate_edges_do_not_duplicate_output(self):
        request = fictional_request()
        request["map"]["edges"].append(deepcopy(request["map"]["edges"][0]))
        rehash(request["map"])
        self.assertEqual(len(self.invoke(request)["relationships"]), 1)

    def test_output_item_limit_yields_explicit_unresolved(self):
        request = fictional_request()
        for index in range(6):
            source = deepcopy(request["map"]["nodes"][2])
            source["id"] = "additional_source_" + str(index)
            request["map"]["nodes"].append(source)
            request["map"]["edges"].append({"source": "kite", "target": source["id"], "type": "cites"})
        rehash(request["map"])
        answer = self.invoke(request)
        self.assertEqual(answer["answer_status"], "unresolved")
        self.assertIn("budget", answer["unresolved_reason"])
        self.assertEqual(answer["target_labels"], [])

    def test_invalid_json_duplicate_keys_and_nonfinite_numbers_are_rejected(self):
        for raw in (b"", b"[]", b"{", b'{"a":1,"a":2}', b'{"x":{"a":1,"a":2}}',
                    b'{"a":NaN}', b'{"a":Infinity}', b'{"a":-Infinity}',
                    b'{"a":1e999}', b"\xff"):
            with self.subTest(raw=raw):
                self.rejected(raw)

    def test_extra_fields_are_rejected_at_each_structural_level(self):
        for level in ("request", "map", "case", "node", "edge"):
            with self.subTest(level=level):
                request = fictional_request()
                target = {"request": request, "map": request["map"], "case": request["case"],
                          "node": request["map"]["nodes"][0], "edge": request["map"]["edges"][0]}[level]
                target["unapproved"] = "irrelevant"
                if level != "request" and level != "case":
                    rehash(request["map"])
                self.rejected(encode(request))

    def test_integrity_invalid_endpoints_and_labels_are_rejected(self):
        mutations = [
            lambda r: r["map"].update(payloadHash="f" * 64),
            lambda r: r["map"]["edges"][0].update(target="absent"),
            lambda r: r["map"]["nodes"][0].update(status="proven"),
            lambda r: r["map"]["nodes"][2].update(bibliographicOnly=False),
            lambda r: r["case"].update(family="proposal"),
            lambda r: r["case"].update(operator="unsupported"),
            lambda r: r.update(schema_version=True),
        ]
        for index, mutation in enumerate(mutations):
            with self.subTest(index=index):
                request = fictional_request()
                mutation(request)
                if index != 0:
                    rehash(request["map"])
                self.rejected(encode(request))

    def test_utf8_limits_and_oversize_input_are_rejected(self):
        self.rejected(b" " * (320 * 1024 + 1))
        request = fictional_request()
        request["case"]["anchor_title"] = "\u03bb" * 257
        self.rejected(encode(request))
        request = fictional_request()
        request["case"]["case_id"] = "x" * 101
        self.rejected(encode(request))
        raw = encode(fictional_request()).replace(b"A fictional paper kite", b"\\ud800")
        self.rejected(raw)

    def test_clarified_text_lower_bounds_and_controls_are_rejected(self):
        for value in ("", " \t\n\r ", "Nonblank\x00text", "Nonblank\x0btext", "Nonblank\x7ftext"):
            for field in ("prompt", "statement", "limitation", "date"):
                with self.subTest(value=value, field=field):
                    request = fictional_request()
                    if field == "prompt":
                        request["case"]["prompt"] = value
                    elif field == "statement":
                        request["map"]["nodes"][0]["statement"] = value
                    elif field == "limitation":
                        request["map"]["nodes"][2]["limitations"][0] = value
                    else:
                        request["map"]["nodes"][2]["date"] = value
                    rehash(request["map"])
                    self.rejected(encode(request))

    def test_clarified_text_allows_tabs_newlines_and_carriage_returns(self):
        request = fictional_request()
        request["case"]["prompt"] = "Nonblank\ttext\nwith\rwhitespace"
        request["map"]["nodes"][2]["limitations"] = ["Nonblank\ttext\nwith\rwhitespace"]
        rehash(request["map"])
        self.assertEqual(self.invoke(request)["answer_status"], "answered")

    def test_source_imports_only_small_standard_library_allowlist(self):
        tree = ast.parse(CANDIDATE.read_text(encoding="utf-8"))
        imports = {alias.name for node in ast.walk(tree) if isinstance(node, ast.Import)
                   for alias in node.names}
        self.assertEqual(imports, {"hashlib", "json", "re", "sys"})
        self.assertFalse(any(isinstance(node, ast.ImportFrom) for node in ast.walk(tree)))
        forbidden = {"open", "exec", "eval", "compile", "__import__"}
        calls = {node.func.id for node in ast.walk(tree)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)}
        self.assertFalse(calls & forbidden)


if __name__ == "__main__":
    unittest.main()
