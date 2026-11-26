"""Compile an offline curated research map from metadata and committed documents."""

from __future__ import annotations

import argparse
import json
import re
import stat
import subprocess
import sys
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from .store import canonical, digest, utc_now


MAX_NODES = 5000
MAX_FILES = 100
MAX_DOCUMENT_BYTES = 1_000_000
MAX_TOTAL_BYTES = 10_000_000
KINDS = {"source", "document", "claim", "representation", "transformation", "experiment"}
CLAIM_STATUSES = {"definition", "hypothesis", "reported_result", "implementation_finding", "contested"}
EDGE_KINDS = {
    "cites": ({"claim"}, {"source", "document"}),
    "challenges": ({"claim"}, {"claim"}),
    "motivates": ({"claim"}, {"representation", "transformation", "experiment"}),
    "compares": ({"experiment"}, {"representation"}),
    "transforms": ({"transformation"}, {"representation"}),
    "depends_on": (KINDS, KINDS),
    "implements": ({"document"}, {"representation", "transformation"}),
}
ASSURANCE = {
    "purpose": "Curated research map, not a truth engine or empirical validation.",
    "sources": "Bibliographic metadata only; external source bytes were not retrieved or archived.",
    "documents": "Exact UTF-8 bytes from the pinned Git commit; working-tree contents are excluded.",
    "timing": "Compilation time is not a historical evidence cutoff or independent timestamp.",
}


def _git(repo: Path, *arguments: str) -> bytes:
    result = subprocess.run(["git", "--no-optional-locks", "--literal-pathspecs", "-C", str(repo), *arguments],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise ValueError(f"Git object read failed: {result.stderr.decode('utf-8', errors='replace').strip()}")
    return result.stdout


def _text(node: dict, field: str) -> str:
    value = node.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Node {node.get('id', '?')}: {field} must be a nonempty string")
    return value


def _date(value: str, field: str, *, partial: bool = False):
    pattern = r"\d{4}(?:-\d{2}(?:-\d{2})?)?" if partial else r"\d{4}-\d{2}-\d{2}"
    if not re.fullmatch(pattern, value):
        raise ValueError(f"Invalid {field}: {value}")
    parts = [int(part) for part in value.split("-")]
    date(*(parts + [1] * (3 - len(parts))))


def _node(node: object) -> dict:
    if not isinstance(node, dict):
        raise ValueError("Every node must be an object")
    _text(node, "id")
    kind = _text(node, "kind")
    _text(node, "title")
    if kind not in KINDS:
        raise ValueError(f"Unknown node kind: {kind}")
    if kind == "source":
        if node.get("bibliographic_only") is not True:
            raise ValueError("Source nodes require bibliographic_only: true")
        url = urlsplit(_text(node, "url"))
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            raise ValueError("Source URL must be credential-free HTTPS")
        date_type = _text(node, "date_type")
        if "date" not in node:
            raise ValueError("Source nodes require date, including null when explicitly undated")
        if node["date"] is None:
            if date_type not in {"undated_live_documentation", "mutable_main_revision_unverified"}:
                raise ValueError("A null source date requires an explicitly undated date_type")
        else:
            _date(_text(node, "date"), "date", partial=True)
        _date(_text(node, "reviewed_on"), "reviewed_on")
        _text(node, "claim_supported")
        _text(node, "limitation")
    elif kind == "document":
        _text(node, "repo_path")
        if {"text", "content_sha256", "commit"} & node.keys():
            raise ValueError("Document text, content_sha256, and commit are compiler-owned fields")
    elif kind == "claim":
        if node.get("status") not in CLAIM_STATUSES:
            raise ValueError("Invalid claim status")
        _text(node, "statement")
        if node.get("basis") not in {"reported", "inferred", "observed"}:
            raise ValueError("Invalid claim basis")
        if {"probability", "probabilities", "confidence"} & node.keys():
            raise ValueError("Claims do not accept probability or confidence fields")
    elif node.get("status") != "proposed":
        raise ValueError(f"{kind} nodes must have status: proposed")
    return dict(node)


def _document(repo: Path, commit: str, repo_path: str) -> bytes:
    # Treat names literally, and prohibit absolute paths, traversal, and ambiguous separators.
    if "\\" in repo_path or "\x00" in repo_path or any(part in {"", ".", ".."} for part in repo_path.split("/")):
        raise ValueError(f"Document repo_path must be a relative path without traversal: {repo_path}")
    entries = _git(repo, "ls-tree", "-z", commit, "--", repo_path).split(b"\x00")
    entries = [entry for entry in entries if entry]
    if len(entries) != 1:
        raise ValueError(f"Document is not a committed regular file: {repo_path}")
    metadata, path = entries[0].split(b"\t", 1)
    mode, kind, object_id = metadata.split()
    if path != repo_path.encode("utf-8") or mode not in {b"100644", b"100755"} or kind != b"blob":
        raise ValueError(f"Document is not a committed regular file (symlinks are forbidden): {repo_path}")
    oid = object_id.decode("ascii")
    if int(_git(repo, "cat-file", "-s", oid)) > MAX_DOCUMENT_BYTES:
        raise ValueError(f"Document exceeds {MAX_DOCUMENT_BYTES} bytes: {repo_path}")
    content = _git(repo, "cat-file", "blob", oid)
    if len(content) > MAX_DOCUMENT_BYTES:
        raise ValueError(f"Document exceeds {MAX_DOCUMENT_BYTES} bytes: {repo_path}")
    return content


def _json_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON field: {key}")
        result[key] = value
    return result


def compile_catalog(repo: str | Path, catalog: str | Path) -> dict:
    """Read local catalog JSON, but embed only explicitly named documents at one Git HEAD."""
    repository = Path(_git(Path(repo).resolve(), "rev-parse", "--show-toplevel").decode("utf-8").strip())
    commit = _git(repository, "rev-parse", "--verify", "HEAD^{commit}").decode("ascii").strip()
    directory = Path(catalog)
    if not directory.is_absolute():
        directory = repository / directory
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("Catalog must be a directory, not a symlink")
    source_paths = sorted(directory.glob("sources-*.json"))
    paths = [directory / "registry.json", *source_paths]
    if len(paths) > MAX_FILES:
        raise ValueError(f"Catalog exceeds {MAX_FILES} files")
    total_bytes = 0
    documents_bytes = 0
    loaded = []
    for path in paths:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"Catalog inputs must be regular files, not symlinks: {path.name}")
        if info.st_size > MAX_TOTAL_BYTES - total_bytes:
            raise ValueError(f"Catalog exceeds {MAX_TOTAL_BYTES} total bytes")
        with path.open("rb") as stream:
            raw = stream.read(MAX_TOTAL_BYTES - total_bytes + 1)
        total_bytes += len(raw)
        if total_bytes > MAX_TOTAL_BYTES:
            raise ValueError(f"Catalog exceeds {MAX_TOTAL_BYTES} total bytes")
        loaded.append(json.loads(raw.decode("utf-8"), object_pairs_hook=_json_object))
    registry = loaded[0]
    if not isinstance(registry, dict) or type(registry.get("schema_version")) is not int or registry["schema_version"] != 1:
        raise ValueError("Registry requires schema_version: 1")
    if not isinstance(registry.get("nodes"), list) or not isinstance(registry.get("edges"), list):
        raise ValueError("Registry nodes and edges must be arrays")
    raw_nodes = list(registry["nodes"])
    for sources in loaded[1:]:
        if not isinstance(sources, list) or any(not isinstance(item, dict) or item.get("kind") != "source" for item in sources):
            raise ValueError("Each sources-*.json file must be an array of source nodes")
        raw_nodes.extend(sources)
    if len(raw_nodes) > MAX_NODES:
        raise ValueError(f"Catalog exceeds {MAX_NODES} nodes")
    nodes = {}
    document_count = 0
    for raw_node in raw_nodes:
        node = _node(raw_node)
        if node["id"] in nodes:
            raise ValueError(f"Duplicate node ID: {node['id']}")
        if node["kind"] == "document":
            document_count += 1
            if len(paths) + document_count > MAX_FILES:
                raise ValueError(f"Catalog and documents exceed {MAX_FILES} files")
            content = _document(repository, commit, node["repo_path"])
            documents_bytes += len(content)
            total_bytes += len(content)
            if total_bytes > MAX_TOTAL_BYTES:
                raise ValueError(f"Catalog exceeds {MAX_TOTAL_BYTES} total bytes")
            node.update(text=content.decode("utf-8"), content_sha256=digest(content), commit=commit)
        nodes[node["id"]] = node
    edges = []
    seen_edges = set()
    for edge in registry["edges"]:
        if not isinstance(edge, dict):
            raise ValueError("Every edge must be an object")
        source, target, kind = (_text(edge, field) for field in ("source", "target", "type"))
        if source not in nodes or target not in nodes:
            raise ValueError(f"Dangling edge: {source} -> {target}")
        if kind not in EDGE_KINDS:
            raise ValueError(f"Unknown edge type: {kind}")
        source_kinds, target_kinds = EDGE_KINDS[kind]
        if nodes[source]["kind"] not in source_kinds or nodes[target]["kind"] not in target_kinds:
            raise ValueError(f"Invalid endpoint kinds for {kind}: {source} -> {target}")
        key = (source, target, kind)
        if key in seen_edges:
            raise ValueError(f"Duplicate edge: {source} -{kind}-> {target}")
        seen_edges.add(key)
        edges.append(dict(edge))
    payload = {"schema_version": 1, "commit": commit, "nodes": sorted(nodes.values(), key=lambda node: node["id"]),
        "edges": sorted(edges, key=lambda edge: (edge["source"], edge["target"], edge["type"]))}
    encoded = canonical(payload).encode("utf-8")
    if len(encoded) > MAX_TOTAL_BYTES:
        raise ValueError(f"Compiled graph exceeds {MAX_TOTAL_BYTES} total bytes")
    return {**payload, "generated_at": utc_now(), "graph_payload_hash": digest(encoded), "assurance": dict(ASSURANCE),
        "stats": {"nodes": len(nodes), "edges": len(edges), "catalog_files": len(paths),
            "document_files": document_count, "document_bytes": documents_bytes,
            "nodes_by_kind": {kind: sum(node["kind"] == kind for node in nodes.values()) for kind in sorted(KINDS)}}}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Validate and compile a curated offline research map")
    parser.add_argument("--repo", default=".")
    parser.add_argument("--catalog", required=True, help="Catalog directory; relative paths are relative to the repository root")
    parser.add_argument("--output", help="New JSON artifact; existing files are never replaced")
    args = parser.parse_args(argv)
    try:
        graph = compile_catalog(args.repo, args.catalog)
        rendered = json.dumps(graph, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
        if args.output:
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            with output.open("x", encoding="utf-8") as stream:
                stream.write(rendered)
        summary = {key: value for key, value in graph.items() if key not in {"nodes", "edges"}}
        if args.output:
            summary["output"] = str(Path(args.output))
        print(json.dumps(summary, indent=2, ensure_ascii=False, allow_nan=False))
        return 0
    except (ValueError, OSError, TypeError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
