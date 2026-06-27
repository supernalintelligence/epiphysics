"""
Entity Registry: persistent storage of entities, states, and couplings.

Entities are tracked across prediction cycles. Each entity has a state
that evolves over time (tranched by date) and couplings to other entities.

Data is stored as JSON for human readability and easy visualization.
"""

import json
import re
from pathlib import Path
from typing import Optional

from config import ROOT

REGISTRY_DIR = ROOT / "data" / "entity_registry"
REGISTRY_FILE = REGISTRY_DIR / "registry.json"
SNAPSHOTS_DIR = REGISTRY_DIR / "snapshots"

# Entity types
ENTITY_TYPES = {"person", "org", "country", "market", "indicator", "event_class", "concept"}

# Coupling types
COUPLING_TYPES = {"influence", "co_occurrence", "causal", "reactive"}

# Default coupling EMA alpha
COUPLING_ALPHA = 0.3


def _slugify(name: str) -> str:
    """Convert name to a stable ID slug."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


def _make_coupling_id(source: str, target: str) -> str:
    """Consistent coupling ID (alphabetical order)."""
    a, b = sorted([source, target])
    return f"{a}::{b}"


class EntityRegistry:
    """Persistent registry of entities, their states, and couplings."""

    def __init__(self, path: Optional[Path] = None):
        self.path = path or REGISTRY_FILE
        self.entities: dict[str, dict] = {}
        self.couplings: dict[str, dict] = {}
        self.metadata: dict = {
            "last_tranche": None,
            "total_entities": 0,
            "total_couplings": 0,
            "tranches_processed": [],
        }
        self._load()

    # ── Persistence ──────────────────────────────────────────────

    def _load(self):
        if self.path.exists():
            with open(self.path) as f:
                data = json.load(f)
            self.entities = data.get("entities", {})
            self.couplings = data.get("couplings", {})
            self.metadata = data.get("metadata", self.metadata)

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.metadata["total_entities"] = len(self.entities)
        self.metadata["total_couplings"] = len(self.couplings)
        with open(self.path, "w") as f:
            json.dump({
                "entities": self.entities,
                "couplings": self.couplings,
                "metadata": self.metadata,
            }, f, indent=2, default=str)

    def snapshot(self, tranche: str):
        """Save a timestamped copy of the registry."""
        SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
        dest = SNAPSHOTS_DIR / f"{tranche}.json"
        with open(dest, "w") as f:
            json.dump({
                "entities": self.entities,
                "couplings": self.couplings,
                "metadata": self.metadata,
            }, f, indent=2, default=str)

        if tranche not in self.metadata["tranches_processed"]:
            self.metadata["tranches_processed"].append(tranche)
            self.metadata["last_tranche"] = tranche

    def reset(self):
        """Clear the registry (for fresh experiments)."""
        self.entities = {}
        self.couplings = {}
        self.metadata = {
            "last_tranche": None,
            "total_entities": 0,
            "total_couplings": 0,
            "tranches_processed": [],
        }

    # ── Entity CRUD ──────────────────────────────────────────────

    def add_entity(
        self,
        canonical_name: str,
        entity_type: str = "concept",
        domain: str = "general",
        aliases: Optional[list[str]] = None,
        state: Optional[dict] = None,
        tranche: Optional[str] = None,
    ) -> str:
        """Add or update an entity. Returns the entity ID."""
        eid = _slugify(canonical_name)

        if eid in self.entities:
            # Update existing
            e = self.entities[eid]
            if aliases:
                existing = set(e.get("aliases", []))
                existing.update(aliases)
                e["aliases"] = sorted(existing)
            if state:
                self._update_entity_state(eid, state, tranche)
            return eid

        # Create new
        self.entities[eid] = {
            "id": eid,
            "canonical_name": canonical_name,
            "aliases": sorted(set([canonical_name] + (aliases or []))),
            "type": entity_type,
            "domain": domain,
            "state": state or {
                "trajectory": "unknown",
                "activity_level": 0.5,
                "key_attributes": {},
                "summary": "",
            },
            "history": [],
            "first_seen": tranche or "unknown",
            "last_updated": tranche or "unknown",
        }

        if tranche and state:
            self.entities[eid]["history"].append({
                "tranche": tranche,
                "state": dict(state),
            })

        return eid

    def get_entity(self, eid: str) -> Optional[dict]:
        return self.entities.get(eid)

    def _update_entity_state(self, eid: str, state: dict, tranche: Optional[str] = None):
        """Update entity state and append to history."""
        e = self.entities.get(eid)
        if not e:
            return

        # Merge state (update, don't replace)
        for k, v in state.items():
            if k == "key_attributes" and isinstance(v, dict):
                e["state"].setdefault("key_attributes", {}).update(v)
            else:
                e["state"][k] = v

        e["last_updated"] = tranche or e["last_updated"]

        if tranche:
            e["history"].append({
                "tranche": tranche,
                "state": dict(e["state"]),
            })
            # Keep history bounded (last 20 tranches)
            if len(e["history"]) > 20:
                e["history"] = e["history"][-20:]

    def update_entity(self, eid: str, state: dict, tranche: Optional[str] = None):
        """Public interface for state updates."""
        self._update_entity_state(eid, state, tranche)

    # ── Coupling CRUD ────────────────────────────────────────────

    def update_coupling(
        self,
        source: str,
        target: str,
        strength: float,
        asymmetry: float = 0.0,
        coupling_type: str = "influence",
        domains: Optional[list[str]] = None,
        evidence: str = "",
        tranche: Optional[str] = None,
    ):
        """Update or create a coupling between two entities."""
        cid = _make_coupling_id(source, target)

        if cid in self.couplings:
            c = self.couplings[cid]
            # EMA update
            old_s = c["strength"]
            c["strength"] = round(COUPLING_ALPHA * strength + (1 - COUPLING_ALPHA) * old_s, 4)
            old_a = c.get("asymmetry", 0.0)
            c["asymmetry"] = round(COUPLING_ALPHA * asymmetry + (1 - COUPLING_ALPHA) * old_a, 4)
            if evidence:
                c["evidence"] = evidence
            if domains:
                c["domains"] = sorted(set(c.get("domains", []) + domains))
            if tranche:
                c["history"].append({
                    "tranche": tranche,
                    "strength": c["strength"],
                    "asymmetry": c["asymmetry"],
                })
                if len(c["history"]) > 20:
                    c["history"] = c["history"][-20:]
        else:
            self.couplings[cid] = {
                "id": cid,
                "source": source,
                "target": target,
                "strength": round(strength, 4),
                "asymmetry": round(asymmetry, 4),
                "type": coupling_type,
                "domains": domains or [],
                "evidence": evidence,
                "history": [{"tranche": tranche, "strength": strength, "asymmetry": asymmetry}] if tranche else [],
            }

    def get_coupling(self, source: str, target: str) -> Optional[dict]:
        cid = _make_coupling_id(source, target)
        return self.couplings.get(cid)

    def get_entity_couplings(self, eid: str) -> list[dict]:
        """Get all couplings involving an entity."""
        return [c for c in self.couplings.values()
                if c["source"] == eid or c["target"] == eid]

    # ── Query ────────────────────────────────────────────────────

    def get_relevant_entities(self, text: str, max_entities: int = 10) -> list[dict]:
        """Find entities mentioned in text by matching aliases."""
        text_lower = text.lower()
        matches = []
        for eid, e in self.entities.items():
            score = 0
            for alias in e.get("aliases", []):
                if alias.lower() in text_lower:
                    score += len(alias)  # Longer alias matches score higher
            if score > 0:
                matches.append((score, e))

        matches.sort(key=lambda x: x[0], reverse=True)
        return [e for _, e in matches[:max_entities]]

    def get_entity_context(self, entity_ids: list[str], include_couplings: bool = True) -> str:
        """Format entity states and couplings as prompt-ready text."""
        lines = []
        for eid in entity_ids:
            e = self.entities.get(eid)
            if not e:
                continue
            s = e["state"]
            lines.append(f"[{e['canonical_name']}] ({e['type']}, {e['domain']})")
            lines.append(f"  Trajectory: {s.get('trajectory', '?')} | Activity: {s.get('activity_level', '?')}")
            if s.get("key_attributes"):
                attrs = ", ".join(f"{k}={v}" for k, v in s["key_attributes"].items())
                lines.append(f"  Attributes: {attrs}")
            if s.get("summary"):
                lines.append(f"  State: {s['summary'][:200]}")

        if include_couplings:
            # Find couplings between the requested entities
            eid_set = set(entity_ids)
            relevant_couplings = [
                c for c in self.couplings.values()
                if c["source"] in eid_set or c["target"] in eid_set
            ]
            if relevant_couplings:
                lines.append("\nCouplings:")
                for c in sorted(relevant_couplings, key=lambda x: x["strength"], reverse=True)[:10]:
                    src_name = self.entities.get(c["source"], {}).get("canonical_name", c["source"])
                    tgt_name = self.entities.get(c["target"], {}).get("canonical_name", c["target"])
                    arrow = "→" if c["asymmetry"] > 0.2 else "←" if c["asymmetry"] < -0.2 else "↔"
                    lines.append(f"  {src_name} {arrow} {tgt_name}: strength={c['strength']:.2f} ({c['type']})")
                    if c.get("evidence"):
                        lines.append(f"    Evidence: {c['evidence'][:100]}")

        return "\n".join(lines)

    # ── Visualization Export ─────────────────────────────────────

    def export_graph(self, domain_filter: Optional[str] = None) -> dict:
        """Export as nodes + edges dict for visualization (D3, networkx, etc.)."""
        nodes = []
        for eid, e in self.entities.items():
            if domain_filter and not e.get("domain", "").startswith(domain_filter):
                continue
            nodes.append({
                "id": eid,
                "label": e["canonical_name"],
                "type": e["type"],
                "domain": e.get("domain", "general"),
                "size": e["state"].get("activity_level", 0.5),
                "trajectory": e["state"].get("trajectory", "unknown"),
            })

        node_ids = {n["id"] for n in nodes}
        edges = []
        for cid, c in self.couplings.items():
            if c["source"] in node_ids and c["target"] in node_ids:
                edges.append({
                    "source": c["source"],
                    "target": c["target"],
                    "weight": c["strength"],
                    "asymmetry": c.get("asymmetry", 0),
                    "type": c["type"],
                    "domains": c.get("domains", []),
                })

        return {"nodes": nodes, "edges": edges}

    def stats(self) -> dict:
        """Summary statistics."""
        domains = {}
        for e in self.entities.values():
            d = e.get("domain", "unknown")
            domains[d] = domains.get(d, 0) + 1

        return {
            "entities": len(self.entities),
            "couplings": len(self.couplings),
            "domains": domains,
            "tranches": self.metadata.get("tranches_processed", []),
            "last_tranche": self.metadata.get("last_tranche"),
        }

    def __repr__(self):
        s = self.stats()
        return f"EntityRegistry({s['entities']} entities, {s['couplings']} couplings, {len(s['tranches'])} tranches)"


if __name__ == "__main__":
    # Quick test
    reg = EntityRegistry(Path("/tmp/test_registry.json"))
    reg.reset()

    reg.add_entity("Donald Trump", "person", "politics.us",
                    aliases=["Trump", "POTUS"],
                    state={"trajectory": "escalating", "activity_level": 0.9,
                           "key_attributes": {"tariff_stance": "aggressive"},
                           "summary": "Escalating trade tensions"},
                    tranche="2026-01-04")

    reg.add_entity("Federal Reserve", "org", "economics.monetary",
                    aliases=["Fed", "the Fed"],
                    state={"trajectory": "stable", "activity_level": 0.6,
                           "summary": "Holding rates steady"},
                    tranche="2026-01-04")

    reg.add_entity("Iraq", "country", "conflict.iraq",
                    state={"trajectory": "volatile", "activity_level": 0.7,
                           "key_attributes": {"conflict_level": "high"},
                           "summary": "Ongoing sectarian tensions"},
                    tranche="2026-01-04")

    reg.update_coupling("donald_trump", "federal_reserve", 0.7, asymmetry=0.6,
                        domains=["politics.us", "economics.monetary"],
                        evidence="Trump pressures Fed on rate cuts",
                        tranche="2026-01-04")

    reg.save()
    reg.snapshot("2026-01-04")

    print(reg)
    print("\nRelevant to 'Trump tariff policy':")
    for e in reg.get_relevant_entities("Trump tariff policy on China"):
        print(f"  {e['canonical_name']} ({e['domain']})")

    print("\nEntity context:")
    print(reg.get_entity_context(["donald_trump", "federal_reserve"]))

    print("\nGraph export:")
    g = reg.export_graph()
    print(f"  Nodes: {len(g['nodes'])}, Edges: {len(g['edges'])}")

    print("\nStats:", reg.stats())
