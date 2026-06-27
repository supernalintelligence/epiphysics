"""
Knowledge Graph: entity store using networkx + Wikidata for hierarchy.

Scales to 100-1000s of entities with:
- Hierarchical containment (Trump ⊂ US Government ⊂ USA)
- Typed relationships (competitive, causal, temporal, structural)
- Wikidata-backed entity lookup for standard ontology
- Export to standard formats (GraphML, GEXF, JSON, pyvis HTML)
"""

import json
import time
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Optional

import networkx as nx

from config import ROOT

KG_DIR = ROOT / "data" / "knowledge_graph"
KG_FILE = KG_DIR / "graph.graphml"
KG_JSON = KG_DIR / "graph.json"
WIKIDATA_CACHE_FILE = KG_DIR / "wikidata_cache.json"

UA = {"User-Agent": "EpiphysicsResearch/1.0 (epiphysics.xyz)"}

# ── Wikidata Lookup ──────────────────────────────────────────

_wikidata_cache = {}


def _load_wikidata_cache():
    global _wikidata_cache
    if WIKIDATA_CACHE_FILE.exists():
        with open(WIKIDATA_CACHE_FILE) as f:
            _wikidata_cache = json.load(f)


def _save_wikidata_cache():
    KG_DIR.mkdir(parents=True, exist_ok=True)
    with open(WIKIDATA_CACHE_FILE, "w") as f:
        json.dump(_wikidata_cache, f, indent=2)


def wikidata_search(query: str, limit: int = 3) -> list[dict]:
    """Search Wikidata for entities matching a query."""
    cache_key = f"search:{query}"
    if cache_key in _wikidata_cache:
        return _wikidata_cache[cache_key]

    url = (
        f"https://www.wikidata.org/w/api.php?action=wbsearchentities"
        f"&search={urllib.parse.quote(query)}&language=en&format=json&limit={limit}"
    )
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        results = [
            {"qid": item["id"], "label": item["label"], "description": item.get("description", "")}
            for item in data.get("search", [])
        ]
        _wikidata_cache[cache_key] = results
        time.sleep(0.1)  # Rate limit
        return results
    except Exception as e:
        return []


def wikidata_get_hierarchy(qid: str) -> dict:
    """Get hierarchy relationships for a Wikidata entity."""
    cache_key = f"hierarchy:{qid}"
    if cache_key in _wikidata_cache:
        return _wikidata_cache[cache_key]

    url = (
        f"https://www.wikidata.org/w/api.php?action=wbgetentities"
        f"&ids={qid}&props=claims|labels|descriptions&languages=en&format=json"
    )
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            entity = json.loads(r.read())["entities"].get(qid, {})

        label = entity.get("labels", {}).get("en", {}).get("value", qid)
        desc = entity.get("descriptions", {}).get("en", {}).get("value", "")
        claims = entity.get("claims", {})

        def extract_refs(prop_id):
            refs = []
            for c in claims.get(prop_id, []):
                val = c.get("mainsnak", {}).get("datavalue", {}).get("value", {})
                if isinstance(val, dict) and "id" in val:
                    refs.append(val["id"])
            return refs

        hierarchy = {
            "qid": qid,
            "label": label,
            "description": desc,
            "instance_of": extract_refs("P31"),     # what type it is
            "subclass_of": extract_refs("P279"),     # broader category
            "part_of": extract_refs("P361"),         # contained in
            "has_part": extract_refs("P527"),        # contains
            "country": extract_refs("P17"),          # country
            "league": extract_refs("P118"),          # sports league
            "located_in": extract_refs("P131"),      # location
        }
        _wikidata_cache[cache_key] = hierarchy
        time.sleep(0.1)
        return hierarchy
    except Exception:
        return {"qid": qid, "label": qid, "description": ""}


def resolve_qid(qid: str) -> str:
    """Resolve a Wikidata QID to a human label."""
    cache_key = f"label:{qid}"
    if cache_key in _wikidata_cache:
        return _wikidata_cache[cache_key]

    url = (
        f"https://www.wikidata.org/w/api.php?action=wbgetentities"
        f"&ids={qid}&props=labels&languages=en&format=json"
    )
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
        label = data["entities"].get(qid, {}).get("labels", {}).get("en", {}).get("value", qid)
        _wikidata_cache[cache_key] = label
        time.sleep(0.05)
        return label
    except Exception:
        return qid


# ── Knowledge Graph ──────────────────────────────────────────

class KnowledgeGraph:
    """Entity graph with hierarchy, couplings, and Wikidata integration."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or KG_JSON
        self.G = nx.DiGraph()
        _load_wikidata_cache()
        self._load()

    # ── Persistence ──────────────────────────────────────────

    def _load(self):
        if self.path.exists():
            with open(self.path) as f:
                data = json.load(f)
            for n in data.get("nodes", []):
                nid = n.pop("id")
                self.G.add_node(nid, **n)
            for e in data.get("edges", []):
                src = e.pop("source")
                tgt = e.pop("target")
                self.G.add_edge(src, tgt, **e)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        nodes = [{"id": n, **self.G.nodes[n]} for n in self.G.nodes]
        edges = [{"source": u, "target": v, **self.G.edges[u, v]} for u, v in self.G.edges]
        with open(self.path, "w") as f:
            json.dump({"nodes": nodes, "edges": edges}, f, indent=2, default=str)
        # Also save GraphML — clean None values first
        try:
            clean = self.G.copy()
            for n in clean.nodes:
                for k, v in list(clean.nodes[n].items()):
                    if v is None:
                        clean.nodes[n][k] = ""
            for u, v in clean.edges:
                for k, val in list(clean.edges[u, v].items()):
                    if val is None:
                        clean.edges[u, v][k] = ""
            nx.write_graphml(clean, str(self.path.with_suffix(".graphml")))
        except Exception:
            pass  # GraphML export is optional
        _save_wikidata_cache()

    def snapshot(self, tranche: str):
        snap_dir = self.path.parent / "snapshots"
        snap_dir.mkdir(parents=True, exist_ok=True)
        nodes = [{"id": n, **self.G.nodes[n]} for n in self.G.nodes]
        edges = [{"source": u, "target": v, **self.G.edges[u, v]} for u, v in self.G.edges]
        with open(snap_dir / f"{tranche}.json", "w") as f:
            json.dump({"nodes": nodes, "edges": edges, "tranche": tranche}, f, indent=2, default=str)

    def reset(self):
        self.G.clear()

    # ── Entity Management ────────────────────────────────────

    def add_entity(
        self,
        entity_id: str,
        label: str,
        entity_type: str = "concept",
        domain: str = "general",
        wikidata_qid: str = None,
        **kwargs,
    ) -> str:
        """Add or update an entity node."""
        if entity_id in self.G:
            self.G.nodes[entity_id].update(kwargs)
            return entity_id

        defaults = {
            "label": label,
            "entity_type": entity_type,
            "domain": domain,
            "wikidata_qid": wikidata_qid or "",
            "trajectory": "unknown",
            "activity_level": 0.5,
            "summary": "",
            "base_rate": None,
        }
        defaults.update(kwargs)
        self.G.add_node(entity_id, **defaults)
        return entity_id

    def add_entity_from_wikidata(self, query: str, entity_type: str = None, domain: str = None) -> Optional[str]:
        """Search Wikidata, add entity with hierarchy."""
        results = wikidata_search(query)
        if not results:
            # Fall back to manual entity
            eid = query.lower().replace(" ", "_").replace("'", "")
            self.add_entity(eid, query, entity_type or "concept", domain or "general")
            return eid

        hit = results[0]
        qid = hit["qid"]
        hierarchy = wikidata_get_hierarchy(qid)

        import re as _re
        eid = _re.sub(r"[^a-z0-9]+", "_", hierarchy["label"].lower()).strip("_")
        etype = entity_type or _infer_type(hierarchy)
        edomain = domain or _infer_domain(hierarchy)

        self.add_entity(
            eid, hierarchy["label"], etype, edomain,
            wikidata_qid=qid,
            wikidata_description=hierarchy.get("description", ""),
        )

        # Add container relationships from hierarchy
        for container_qid in hierarchy.get("part_of", []) + hierarchy.get("league", []) + hierarchy.get("country", []):
            container_label = resolve_qid(container_qid)
            container_id = container_label.lower().replace(" ", "_").replace("'", "")
            if container_id != eid:
                self.add_entity(container_id, container_label, "container", edomain, wikidata_qid=container_qid)
                self.add_edge(eid, container_id, relation="contained_in", edge_type="hierarchical")

        return eid

    def update_entity_state(self, entity_id: str, tranche: str = None, **state_updates):
        """Update entity state attributes."""
        if entity_id not in self.G:
            return
        node = self.G.nodes[entity_id]
        for k, v in state_updates.items():
            node[k] = v
        if tranche:
            history = json.loads(node.get("history", "[]"))
            history.append({"tranche": tranche, **state_updates})
            if len(history) > 20:
                history = history[-20:]
            node["history"] = json.dumps(history)

    # ── Edge/Coupling Management ─────────────────────────────

    def add_edge(
        self,
        source: str,
        target: str,
        relation: str = "influences",
        edge_type: str = "direct",
        strength: float = 0.5,
        asymmetry: float = 0.0,
        evidence: str = "",
        **kwargs,
    ):
        """Add or update a directed edge (coupling)."""
        if self.G.has_edge(source, target):
            # EMA update for strength
            old = self.G.edges[source, target].get("strength", 0.5)
            self.G.edges[source, target]["strength"] = round(0.3 * strength + 0.7 * old, 4)
            if evidence:
                self.G.edges[source, target]["evidence"] = evidence
            self.G.edges[source, target].update(kwargs)
        else:
            self.G.add_edge(
                source, target,
                relation=relation,
                edge_type=edge_type,
                strength=round(strength, 4),
                asymmetry=round(asymmetry, 4),
                evidence=evidence,
                **kwargs,
            )

    # ── Query ────────────────────────────────────────────────

    def get_entity(self, entity_id: str) -> Optional[dict]:
        if entity_id in self.G:
            return {"id": entity_id, **self.G.nodes[entity_id]}
        return None

    def find_entities(self, text: str, max_results: int = 10) -> list[dict]:
        """Find entities whose labels appear in text."""
        text_lower = text.lower()
        matches = []
        for nid in self.G.nodes:
            node = self.G.nodes[nid]
            label = node.get("label", nid)
            if label.lower() in text_lower or nid in text_lower:
                matches.append((len(label), {"id": nid, **node}))
        matches.sort(key=lambda x: x[0], reverse=True)
        return [m for _, m in matches[:max_results]]

    def get_containers(self, entity_id: str) -> list[dict]:
        """Get all containers (parent entities) via contained_in edges."""
        containers = []
        for _, target, data in self.G.out_edges(entity_id, data=True):
            if data.get("relation") == "contained_in":
                containers.append({"id": target, **self.G.nodes.get(target, {})})
        return containers

    def get_competitors(self, entity_id: str) -> list[dict]:
        """Get entities that share a container (competitive peers)."""
        containers = self.get_containers(entity_id)
        competitors = []
        for container in containers:
            cid = container["id"]
            for source, target, data in self.G.in_edges(cid, data=True):
                if data.get("relation") == "contained_in" and source != entity_id:
                    competitors.append({"id": source, **self.G.nodes.get(source, {})})
        return competitors

    def get_neighborhood(self, entity_id: str, depth: int = 1) -> nx.DiGraph:
        """Get subgraph around an entity."""
        nodes = {entity_id}
        frontier = {entity_id}
        for _ in range(depth):
            next_frontier = set()
            for n in frontier:
                next_frontier.update(self.G.successors(n))
                next_frontier.update(self.G.predecessors(n))
            nodes.update(next_frontier)
            frontier = next_frontier
        return self.G.subgraph(nodes).copy()

    def get_entity_context(self, entity_ids: list[str]) -> str:
        """Format entity states + hierarchy + couplings for prompt injection."""
        lines = []
        for eid in entity_ids:
            if eid not in self.G:
                continue
            n = self.G.nodes[eid]
            lines.append(f"[{n.get('label', eid)}] ({n.get('entity_type', '?')}, {n.get('domain', '?')})")
            if n.get("trajectory") and n["trajectory"] != "unknown":
                lines.append(f"  Trajectory: {n['trajectory']} | Activity: {n.get('activity_level', '?')}")
            if n.get("summary"):
                lines.append(f"  State: {n['summary'][:200]}")
            if n.get("base_rate") is not None:
                lines.append(f"  Base rate: {n['base_rate']}")

            # Show containers
            containers = self.get_containers(eid)
            if containers:
                cnames = [c.get("label", c["id"]) for c in containers]
                lines.append(f"  Part of: {', '.join(cnames)}")

            # Show couplings
            for _, target, data in self.G.out_edges(eid, data=True):
                if data.get("relation") != "contained_in":
                    tgt_label = self.G.nodes.get(target, {}).get("label", target)
                    lines.append(f"  → {tgt_label}: {data.get('relation', '?')} (strength={data.get('strength', '?')})")

        return "\n".join(lines)

    # ── Visualization ────────────────────────────────────────

    def export_pyvis(self, output_path: str = None, domain_filter: str = None) -> str:
        """Export interactive HTML visualization via pyvis."""
        from pyvis.network import Network

        net = Network(height="600px", width="100%", directed=True, notebook=False)

        domain_colors = {
            "politics": "#e74c3c",
            "economics": "#2ecc71",
            "conflict": "#e67e22",
            "tech": "#3498db",
            "sports": "#9b59b6",
            "general": "#95a5a6",
        }

        for nid in self.G.nodes:
            n = self.G.nodes[nid]
            if domain_filter and not n.get("domain", "").startswith(domain_filter):
                continue
            domain_root = n.get("domain", "general").split(".")[0]
            color = domain_colors.get(domain_root, "#95a5a6")
            size = max(10, int((n.get("activity_level", 0.5) or 0.5) * 30))
            label = n.get("label", nid)
            title = f"{label}\n{n.get('entity_type', '?')} | {n.get('domain', '?')}\n{n.get('summary', '')[:100]}"
            net.add_node(nid, label=label, color=color, size=size, title=title)

        shown_nodes = {n["id"] for n in net.nodes}
        for u, v, data in self.G.edges(data=True):
            if u in shown_nodes and v in shown_nodes:
                width = max(1, int((data.get("strength", 0.5) or 0.5) * 5))
                color = "#ccc" if data.get("edge_type") == "hierarchical" else "#333"
                net.add_edge(u, v, width=width, color=color, title=data.get("relation", ""))

        path = output_path or str(KG_DIR / "graph.html")
        net.save_graph(path)
        return path

    # ── Stats ────────────────────────────────────────────────

    def stats(self) -> dict:
        domains = {}
        types = {}
        for n in self.G.nodes:
            d = self.G.nodes[n].get("domain", "unknown")
            t = self.G.nodes[n].get("entity_type", "unknown")
            domains[d] = domains.get(d, 0) + 1
            types[t] = types.get(t, 0) + 1

        edge_types = {}
        for u, v, data in self.G.edges(data=True):
            et = data.get("edge_type", "unknown")
            edge_types[et] = edge_types.get(et, 0) + 1

        return {
            "nodes": self.G.number_of_nodes(),
            "edges": self.G.number_of_edges(),
            "domains": domains,
            "entity_types": types,
            "edge_types": edge_types,
        }

    def __repr__(self):
        s = self.stats()
        return f"KnowledgeGraph({s['nodes']} entities, {s['edges']} edges)"


# ── Helpers ──────────────────────────────────────────────────

def _infer_type(hierarchy: dict) -> str:
    """Infer entity type from Wikidata instance_of."""
    type_map = {
        "Q5": "person",           # human
        "Q6256": "country",       # country
        "Q515": "country",        # city (treat as location)
        "Q4830453": "org",        # business
        "Q891723": "org",         # public company
        "Q13393265": "org",       # basketball team
        "Q476028": "org",         # football club
        "Q66344": "org",          # central bank
        "Q131569": "concept",     # treaty
        "Q223371": "market",      # stock market index
    }
    for iof in hierarchy.get("instance_of", []):
        if iof in type_map:
            return type_map[iof]
    return "concept"


def _infer_domain(hierarchy: dict) -> str:
    """Infer domain from Wikidata properties."""
    desc = hierarchy.get("description", "").lower()
    if any(w in desc for w in ["basketball", "football", "tennis", "sport", "athlete"]):
        return "sports"
    if any(w in desc for w in ["president", "politician", "political", "government"]):
        return "politics"
    if any(w in desc for w in ["company", "bank", "stock", "market", "economic"]):
        return "economics"
    if any(w in desc for w in ["military", "conflict", "war", "armed"]):
        return "conflict"
    if any(w in desc for w in ["technology", "software", "ai", "computer"]):
        return "tech"
    # Check if it's a country
    if hierarchy.get("instance_of") and any(q in ["Q6256", "Q3624078"] for q in hierarchy["instance_of"]):
        return "politics"
    return "general"


if __name__ == "__main__":
    kg = KnowledgeGraph(Path("/tmp/test_kg.json"))
    kg.reset()

    # Add entities from Wikidata
    print("Adding entities from Wikidata...")
    for query in ["Detroit Pistons", "Donald Trump", "Gibraltar", "Federal Reserve", "S&P 500"]:
        eid = kg.add_entity_from_wikidata(query)
        print(f"  Added: {eid}")

    # Add a manual coupling
    kg.add_edge("donald_trump", "federal_reserve_system",
                relation="pressures_on_rates", edge_type="direct",
                strength=0.7, asymmetry=0.6,
                evidence="Public rhetoric on rate policy")

    kg.save()
    print(f"\n{kg}")
    print(f"Stats: {json.dumps(kg.stats(), indent=2)}")

    print(f"\nDetroit Pistons context:")
    print(kg.get_entity_context(["detroit_pistons"]))

    print(f"\nContainers for Detroit Pistons:")
    for c in kg.get_containers("detroit_pistons"):
        print(f"  {c.get('label', c['id'])}")

    # Export visualization
    try:
        path = kg.export_pyvis("/tmp/test_kg.html")
        print(f"\nVisualization: {path}")
    except ImportError:
        print("\npyvis not available for visualization")
