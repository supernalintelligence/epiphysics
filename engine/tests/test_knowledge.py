import copy
import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from epiphysics import knowledge
from epiphysics.store import canonical, digest


class KnowledgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.repo = Path(self.temp.name)
        self.git("init", "-q")
        self.document = self.repo / "docs" / "evidence.md"
        self.document.parent.mkdir()
        self.committed_bytes = "# Evidence\r\nA café supports claim A.\r\n".encode("utf-8")
        self.document.write_bytes(self.committed_bytes)
        self.git("add", "docs/evidence.md")
        self.git("commit", "-qm", "Initial document")
        self.commit = self.git("rev-parse", "HEAD").strip()
        self.catalog = self.repo / "research" / "catalog"
        self.catalog.mkdir(parents=True)
        self.sources = [{"id": "paper", "kind": "source", "title": "Example paper",
            "url": "https://example.org/paper", "bibliographic_only": True,
            "date": "2020", "date_type": "publication", "reviewed_on": "2026-11-25",
            "claim_supported": "A reported observation", "limitation": "Bibliography only; no source bytes archived"}]
        self.registry = {"schema_version": 1, "nodes": [
            {"id": "document", "kind": "document", "title": "Local evidence", "repo_path": "docs/evidence.md"},
            {"id": "claim-a", "kind": "claim", "title": "Claim A", "status": "hypothesis",
             "statement": "The representation preserves the property", "basis": "inferred"},
            {"id": "claim-b", "kind": "claim", "title": "Opposing claim", "status": "contested",
             "statement": "The representation does not preserve the property", "basis": "reported"},
            {"id": "representation", "kind": "representation", "title": "Candidate representation", "status": "proposed"},
            {"id": "transformation", "kind": "transformation", "title": "Candidate transformation", "status": "proposed"},
            {"id": "experiment", "kind": "experiment", "title": "Candidate experiment", "status": "proposed"},
        ], "edges": [
            {"source": "claim-a", "target": "paper", "type": "cites"},
            {"source": "claim-b", "target": "document", "type": "cites"},
            {"source": "claim-a", "target": "claim-b", "type": "challenges"},
            {"source": "claim-b", "target": "claim-a", "type": "challenges"},
            {"source": "claim-a", "target": "claim-b", "type": "depends_on"},
            {"source": "claim-a", "target": "representation", "type": "motivates"},
            {"source": "claim-a", "target": "transformation", "type": "motivates"},
            {"source": "claim-a", "target": "experiment", "type": "motivates"},
            {"source": "experiment", "target": "representation", "type": "compares"},
            {"source": "transformation", "target": "representation", "type": "transforms"},
            {"source": "document", "target": "representation", "type": "implements"},
            {"source": "document", "target": "transformation", "type": "implements"},
        ]}
        self.write_catalog()

    def tearDown(self):
        self.temp.cleanup()

    def git(self, *arguments):
        return subprocess.run(["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgSign=false",
            "-c", "user.name=Knowledge test", "-c", "user.email=knowledge@example.invalid",
            "-C", str(self.repo), *arguments], check=True, capture_output=True, text=True).stdout

    def write_catalog(self, registry=None, sources=None):
        (self.catalog / "registry.json").write_text(json.dumps(self.registry if registry is None else registry), encoding="utf-8")
        (self.catalog / "sources-test.json").write_text(json.dumps(self.sources if sources is None else sources), encoding="utf-8")

    def compile(self):
        return knowledge.compile_catalog(self.repo, "research/catalog")

    def command(self, *arguments):
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            result = knowledge.main(["--repo", str(self.repo), "--catalog", "research/catalog", *arguments])
        return result, stdout.getvalue(), stderr.getvalue()

    def test_embeds_exact_committed_bytes_ignoring_dirty_and_untracked_contents(self):
        self.document.write_text("DIRTY content must not appear")
        (self.document.parent / "untracked.md").write_text("UNTRACKED content must not appear")
        graph = self.compile()
        document = next(node for node in graph["nodes"] if node["id"] == "document")
        self.assertEqual(self.committed_bytes, document["text"].encode("utf-8"))
        self.assertEqual(digest(self.committed_bytes), document["content_sha256"])
        self.assertEqual(self.commit, document["commit"])
        self.assertEqual(self.commit, graph["commit"])
        self.assertNotIn("DIRTY", canonical(graph))
        self.assertNotIn("UNTRACKED", canonical(graph))
        self.assertEqual(1, graph["stats"]["document_files"])
        self.assertEqual(len(self.committed_bytes), graph["stats"]["document_bytes"])
        self.assertTrue(next(node for node in graph["nodes"] if node["id"] == "paper")["bibliographic_only"])
        self.assertIn("not a historical evidence cutoff", graph["assurance"]["timing"])

    def test_rejects_untracked_symlink_and_traversal_documents(self):
        (self.document.parent / "untracked.md").write_text("Untracked")
        (self.document.parent / "link.md").symlink_to("evidence.md")
        (self.repo / "alias").symlink_to("docs", target_is_directory=True)
        self.git("add", "docs/link.md", "alias")
        self.git("commit", "-qm", "Add symlink fixtures")
        paths = ["docs/untracked.md", "docs/link.md", "alias/evidence.md", "../outside.md",
            "/etc/passwd", "docs/../evidence.md", "docs\\evidence.md", "docs//evidence.md", "docs/"]
        for path in paths:
            with self.subTest(path=path):
                registry = copy.deepcopy(self.registry)
                registry["nodes"][0]["repo_path"] = path
                self.write_catalog(registry=registry)
                with self.assertRaises(ValueError):
                    self.compile()

    def test_rejects_non_utf8_committed_document(self):
        self.document.write_bytes(b"\xff\xfe")
        self.git("add", "docs/evidence.md")
        self.git("commit", "-qm", "Binary fixture")
        with self.assertRaises(UnicodeDecodeError):
            self.compile()

    def test_contradictory_claims_parallel_types_and_opposite_directions_survive(self):
        graph = self.compile()
        actual = {(edge["source"], edge["target"], edge["type"]) for edge in graph["edges"]}
        expected = {(edge["source"], edge["target"], edge["type"]) for edge in self.registry["edges"]}
        self.assertEqual(expected, actual)
        self.assertEqual(12, len(graph["edges"]))
        claims = [node for node in graph["nodes"] if node["kind"] == "claim"]
        self.assertEqual(2, len(claims))
        self.assertEqual({"hypothesis", "contested"}, {node["status"] for node in claims})

    def test_rejects_duplicate_nodes_edges_dangling_edges_and_invalid_types(self):
        mutations = [
            lambda registry: registry["nodes"].append(dict(registry["nodes"][1])),
            lambda registry: registry["nodes"][0].update(id="paper"),
            lambda registry: registry["edges"].append(dict(registry["edges"][0])),
            lambda registry: registry["edges"][0].update(target="missing"),
            lambda registry: registry["edges"][0].update(type="proves"),
            lambda registry: registry["edges"][0].update(source="representation"),
            lambda registry: registry["edges"][0].update(target="experiment"),
            lambda registry: registry["nodes"][0].update(kind="truth"),
            lambda registry: registry.update(schema_version=True),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(case=index):
                registry = copy.deepcopy(self.registry)
                mutate(registry)
                self.write_catalog(registry=registry)
                with self.assertRaises(ValueError):
                    self.compile()

    def test_rejects_claim_fields_and_non_proposed_protocol_statuses(self):
        mutations = [
            lambda node: node.update(status="proven"),
            lambda node: node.update(statement=""),
            lambda node: node.update(basis="certain"),
            lambda node: node.update(probability=0.9),
            lambda node: node.update(confidence=0.9),
            lambda node: node.pop("title"),
        ]
        for index, mutate in enumerate(mutations):
            with self.subTest(claim_case=index):
                registry = copy.deepcopy(self.registry)
                mutate(registry["nodes"][1])
                self.write_catalog(registry=registry)
                with self.assertRaises(ValueError):
                    self.compile()
        for kind in ("representation", "transformation", "experiment"):
            with self.subTest(kind=kind):
                registry = copy.deepcopy(self.registry)
                next(node for node in registry["nodes"] if node["kind"] == kind)["status"] = "validated"
                self.write_catalog(registry=registry)
                with self.assertRaisesRegex(ValueError, "status: proposed"):
                    self.compile()

    def test_source_dates_metadata_and_https_are_validated(self):
        for value, date_type in [("2020", "publication"), ("2020-02", "publication"), ("2020-02-29", "publication"),
            (None, "undated_live_documentation"), (None, "mutable_main_revision_unverified")]:
            with self.subTest(date=value, date_type=date_type):
                sources = copy.deepcopy(self.sources)
                sources[0].update(date=value, date_type=date_type)
                self.write_catalog(sources=sources)
                self.assertEqual(value, next(node for node in self.compile()["nodes"] if node["kind"] == "source")["date"])
        invalid = [{"url": "http://example.org/paper"}, {"bibliographic_only": False}, {"date": "2020-02-30"},
            {"date": None}, {"reviewed_on": "2026-11"}, {"claim_supported": ""}, {"limitation": ""}, {"date_type": ""}]
        for changes in invalid:
            with self.subTest(changes=changes):
                sources = copy.deepcopy(self.sources)
                sources[0].update(changes)
                self.write_catalog(sources=sources)
                with self.assertRaises(ValueError):
                    self.compile()
        sources = copy.deepcopy(self.sources)
        del sources[0]["date"]
        self.write_catalog(sources=sources)
        with self.assertRaisesRegex(ValueError, "require date"):
            self.compile()

    def test_payload_hash_is_stable_under_reordering_and_excludes_generated_at(self):
        with patch.object(knowledge, "utc_now", return_value="2026-11-25T10:00:00+00:00"):
            first = self.compile()
        self.registry["nodes"].reverse()
        self.registry["edges"].reverse()
        self.write_catalog()
        with patch.object(knowledge, "utc_now", return_value="2026-11-26T10:00:00+00:00"):
            second = self.compile()
        self.assertNotEqual(first["generated_at"], second["generated_at"])
        self.assertEqual(first["graph_payload_hash"], second["graph_payload_hash"])
        payload = {key: second[key] for key in ("schema_version", "commit", "nodes", "edges")}
        self.assertEqual(digest(canonical(payload).encode("utf-8")), second["graph_payload_hash"])
        (self.repo / "unrelated.txt").write_text("A new commit")
        self.git("add", "unrelated.txt")
        self.git("commit", "-qm", "Advance HEAD")
        self.assertNotEqual(first["graph_payload_hash"], self.compile()["graph_payload_hash"])

    def test_head_is_pinned_even_if_repository_advances_during_compilation(self):
        git_read = knowledge._git
        advanced = False

        def advance_before_document_read(repo, *arguments):
            nonlocal advanced
            if arguments[0] == "ls-tree" and not advanced:
                advanced = True
                self.document.write_text("Later committed bytes")
                self.git("add", "docs/evidence.md")
                self.git("commit", "-qm", "Concurrent commit")
            return git_read(repo, *arguments)

        with patch.object(knowledge, "_git", side_effect=advance_before_document_read):
            graph = self.compile()
        self.assertNotEqual(self.commit, self.git("rev-parse", "HEAD").strip())
        self.assertEqual(self.commit, graph["commit"])
        self.assertEqual(self.committed_bytes.decode("utf-8"),
            next(node for node in graph["nodes"] if node["kind"] == "document")["text"])

    def test_limits_and_symlinked_catalog_inputs_are_rejected(self):
        for name, limit in [("MAX_NODES", 6), ("MAX_FILES", 2), ("MAX_DOCUMENT_BYTES", 4), ("MAX_TOTAL_BYTES", 100)]:
            with self.subTest(limit=name), patch.object(knowledge, name, limit):
                with self.assertRaisesRegex(ValueError, "exceeds|exceed"):
                    self.compile()
        source_file = self.catalog / "sources-test.json"
        other = self.repo / "other-sources.json"
        source_file.rename(other)
        source_file.symlink_to(other)
        with self.assertRaisesRegex(ValueError, "not symlinks"):
            self.compile()

    def test_cli_summary_exclusive_output_and_no_file_on_validation_failure(self):
        code, stdout, stderr = self.command()
        self.assertEqual((0, ""), (code, stderr))
        summary = json.loads(stdout)
        self.assertNotIn("nodes", summary)
        self.assertEqual(7, summary["stats"]["nodes"])
        output = self.repo / "artifacts" / "catalog.json"
        code, _, error = self.command("--output", str(output))
        self.assertEqual((0, ""), (code, error))
        original = output.read_bytes()
        artifact = json.loads(original)
        self.assertEqual(summary["graph_payload_hash"], artifact["graph_payload_hash"])
        self.assertEqual(2, self.command("--output", str(output))[0])
        self.assertEqual(original, output.read_bytes())
        self.registry["edges"][0]["target"] = "missing"
        self.write_catalog()
        invalid_output = self.repo / "must-not-exist" / "invalid.json"
        code, _, error = self.command("--output", str(invalid_output))
        self.assertEqual(2, code)
        self.assertIn("Dangling", error)
        self.assertFalse(invalid_output.exists())
        self.assertFalse(invalid_output.parent.exists())


if __name__ == "__main__":
    unittest.main()
