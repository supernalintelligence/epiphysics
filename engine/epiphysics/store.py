"""Append-only local evidence ledger. Hashes detect edits; they are not timestamps."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

IMPLEMENTATION_SOURCE = Path(__file__).read_bytes()
IMPLEMENTATION_CODE = sys._getframe().f_code
IMPLEMENTATION_DEPENDENCIES = ()


def canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def instant(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("A timestamp must include its timezone")
    return parsed.astimezone(timezone.utc)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class Ledger:
    """Single SQLite event chain; content-addressed blobs; disposable derived views.

    The clock injection is for tests and the clearly labelled synthetic demo only.
    Production CLI commands always use the system UTC clock. An independent witness
    is required to make an externally verifiable claim about prior existence.
    """

    def __init__(self, root: str | Path, clock: Callable[[], str] = utc_now):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "blobs").mkdir(exist_ok=True)
        self.clock = clock
        self.db = sqlite3.connect(self.root / "ledger.sqlite", timeout=10)
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            PRAGMA journal_mode=WAL;
            CREATE TABLE IF NOT EXISTS events (
                seq INTEGER PRIMARY KEY AUTOINCREMENT,
                id TEXT NOT NULL UNIQUE,
                kind TEXT NOT NULL,
                recorded_at TEXT NOT NULL,
                body TEXT NOT NULL,
                previous_hash TEXT NOT NULL,
                hash TEXT NOT NULL UNIQUE
            );
            CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events
            BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
            CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events
            BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;
        """)

    def close(self):
        self.db.close()

    @staticmethod
    def _decode(row):
        return {**dict(row), "body": json.loads(row["body"])}

    def events(self, kind: str | None = None) -> list[dict]:
        query = "SELECT * FROM events"
        rows = self.db.execute(query + (" WHERE kind=?" if kind else "") + " ORDER BY seq", (kind,) if kind else ())
        return [self._decode(row) for row in rows]

    def get(self, event_id: str, kind: str | None = None) -> dict:
        row = self.db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        if row is None or (kind and row["kind"] != kind):
            raise ValueError(f"Missing {kind or 'event'}: {event_id}")
        return self._decode(row)

    def append(self, kind: str, body: dict, event_id: str | None = None, *,
               validate: Callable[[str], None] | None = None, exclusive: bool = False) -> dict:
        """Validate new events under the write lock, using their recorded timestamp.

        Identical retries return the original event without revalidating time-sensitive
        constraints. Exclusive claims instead reject any existing event with that ID.
        """
        body_text = canonical(body)
        event_id = event_id or str(uuid.uuid4())
        self.db.execute("BEGIN IMMEDIATE")
        try:
            existing = self.db.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
            if existing:
                if existing["kind"] != kind or existing["body"] != body_text:
                    raise ValueError("Idempotency key already has different content")
                if exclusive:
                    raise ValueError("Event already exists; exclusive claim refused")
                self.db.commit()
                return self._decode(existing)
            now = self.clock()
            instant(now)
            last = self.db.execute("SELECT hash,recorded_at FROM events ORDER BY seq DESC LIMIT 1").fetchone()
            if last and instant(now) < instant(last["recorded_at"]):
                raise ValueError("Clock moved backwards; cannot append")
            if validate:
                validate(now)
            record = {"id": event_id, "kind": kind, "recorded_at": now, "body": body,
                      "previous_hash": last["hash"] if last else "0" * 64}
            record_hash = digest(canonical(record).encode())
            self.db.execute("INSERT INTO events(id,kind,recorded_at,body,previous_hash,hash) VALUES(?,?,?,?,?,?)",
                            (event_id, kind, now, body_text, record["previous_hash"], record_hash))
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        return self.get(event_id)

    def capture(self, source: str, content: bytes, *, published_at: str | None = None,
                event_at: str | None = None, media_type: str = "text/plain", revision_of: str | None = None,
                event_id: str | None = None) -> dict:
        if not source.strip():
            raise ValueError("Source is required")
        for timestamp in (published_at, event_at):
            if timestamp:
                instant(timestamp)
        if revision_of:
            previous = self.get(revision_of, "observation")
            if previous["body"]["source"] != source:
                raise ValueError("A revision must refer to the same source")
        content_hash = digest(content)
        path = self.root / "blobs" / content_hash
        try:
            with path.open("xb") as output:
                output.write(content)
        except FileExistsError:
            if digest(path.read_bytes()) != content_hash:
                raise ValueError("Existing blob is corrupted")
        return self.append("observation", {"source": source, "content_hash": content_hash,
            "size": len(content), "media_type": media_type, "published_at": published_at,
            "event_at": event_at, "revision_of": revision_of,
            "timing_basis": "collector clock; source times are claims"}, event_id)

    def snapshot(self, cutoff: str | None = None, event_id: str | None = None) -> dict:
        cutoff = cutoff or self.clock()
        if instant(cutoff) > instant(self.clock()):
            raise ValueError("Cannot snapshot a future information state")
        # First-observed time is the collection event's recorded_at, never publication time.
        observations = [r for r in self.events("observation") if instant(r["recorded_at"]) <= instant(cutoff)]
        manifest = [{"id": r["id"], "event_hash": r["hash"], "content_hash": r["body"]["content_hash"]} for r in observations]
        return self.append("snapshot", {"cutoff": cutoff, "observations": manifest,
            "manifest_hash": digest(canonical(manifest).encode()), "watermark": max((r["seq"] for r in observations), default=0)}, event_id)

    def representation(self, snapshot_id: str, model: dict, *, observer: str, method: str,
                       parent: str | None = None, event_id: str | None = None) -> dict:
        snapshot = self.get(snapshot_id, "snapshot")
        allowed = {r["id"] for r in snapshot["body"]["observations"]}
        if parent:
            previous = self.get(parent, "representation")
            if previous["body"]["observer"] != observer:
                raise ValueError("A lineage must preserve its observer")
            old_cutoff = self.get(previous["body"]["snapshot_id"], "snapshot")["body"]["cutoff"]
            if instant(old_cutoff) > instant(snapshot["body"]["cutoff"]):
                raise ValueError("Cannot use future memory in an earlier snapshot")
        if not observer or not method:
            raise ValueError("Observer and method are required")
        entities = model.get("entities", [])
        ids = [e["id"] for e in entities]
        if len(ids) != len(set(ids)):
            raise ValueError("Entity hypothesis IDs must be unique")
        for item in [*entities, *model.get("relations", [])]:
            if item.get("basis") not in {"observed", "reported", "inferred"}:
                raise ValueError("Every entity/relation needs an epistemic basis")
            if not item.get("evidence_ids") or not set(item["evidence_ids"]) <= allowed:
                raise ValueError("Representation evidence must belong to its snapshot")
        relations = set()
        for relation in model.get("relations", []):
            key = (relation["source"], relation["target"], relation["type"])
            if key[0] not in ids or key[1] not in ids or key in relations:
                raise ValueError("Relationship endpoints must exist; typed directions must be unique")
            relations.add(key)
        return self.append("representation", {"snapshot_id": snapshot_id, "observer": observer,
            "method": method, "parent": parent, "model": model}, event_id)

    def question(self, text: str, deadline: str, resolve_after: str, resolution_rule: str,
                 family: str, event_id: str | None = None) -> dict:
        if not all(s.strip() for s in (text, resolution_rule, family)):
            raise ValueError("Question, resolution rule, and question family are required")
        def validate(now):
            if instant(deadline) <= instant(now) or instant(resolve_after) <= instant(deadline):
                raise ValueError("Require now < forecast deadline < resolution time")
        return self.append("question", {"text": text, "deadline": deadline, "resolve_after": resolve_after,
            "resolution_rule": resolution_rule, "family": family, "outcome_type": "binary"}, event_id, validate=validate)

    def forecast(self, question_id: str, snapshot_id: str, method: str, probability: float | None,
                 *, model: dict, representation_id: str | None = None, status: str = "predicted",
                 reason: str | None = None, cost: dict | None = None, event_id: str | None = None,
                 validate: Callable[[str], None] | None = None) -> dict:
        """Record an attempt, optionally adding trusted validation under the write lock.

        The callback receives the exact recorded_at after core forecast checks.
        Identical retries return the original event without rerunning validation.
        """
        if validate is not None and not callable(validate):
            raise ValueError("Forecast validate must be callable or None")
        q = self.get(question_id, "question")["body"]
        snapshot = self.get(snapshot_id, "snapshot")
        if status not in {"predicted", "failed", "abstained"}:
            raise ValueError("Invalid attempt status")
        if status == "predicted":
            if type(probability) not in (int, float) or not math.isfinite(probability) or not 0 <= probability <= 1:
                raise ValueError("Probability must be a finite number in [0,1]")
        elif probability is not None or not reason:
            raise ValueError("A failed/abstained attempt needs a reason and no probability")
        if not method or not model.get("identifier"):
            raise ValueError("Method and model identifier are required")
        if representation_id:
            r = self.get(representation_id, "representation")["body"]
            if r["snapshot_id"] != snapshot_id:
                raise ValueError("Representation and forecast must use the same snapshot")
        def validate_forecast(now):
            if instant(now) >= instant(q["deadline"]):
                raise ValueError("Forecast deadline has passed")
            if instant(snapshot["recorded_at"]) > instant(now):
                raise ValueError("Snapshot not yet available")
            # One attempt per method/question. Revisions require a new predeclared question.
            for f in self.events("forecast"):
                if f["body"]["question_id"] == question_id and f["body"]["method"] == method:
                    raise ValueError("This method already attempted this question")
            if validate is not None:
                validate(now)
        return self.append("forecast", {"question_id": question_id, "snapshot_id": snapshot_id,
            "representation_id": representation_id, "method": method, "probability": probability,
            "status": status, "reason": reason, "model": model, "cost": cost or {},
            "commitment": "local hash chain only; independently unwitnessed"}, event_id, validate=validate_forecast)

    def resolve(self, question_id: str, outcome: int, evidence_ids: list[str], *,
                explanation: str, supersedes: str | None = None, event_id: str | None = None) -> dict:
        q = self.get(question_id, "question")["body"]
        if type(outcome) is not int or outcome not in (0, 1) or not evidence_ids or not explanation:
            raise ValueError("A binary outcome, explanation, and evidence are required")
        for eid in evidence_ids:
            self.get(eid, "observation")
        def validate(now):
            if instant(now) < instant(q["resolve_after"]):
                raise ValueError("Outcome cannot be resolved yet")
            previous = [r for r in self.events("resolution") if r["body"]["question_id"] == question_id]
            if previous and supersedes != previous[-1]["id"]:
                raise ValueError("A correction must supersede the latest resolution")
            if not previous and supersedes:
                raise ValueError("There is no resolution to supersede")
        return self.append("resolution", {"question_id": question_id, "outcome": outcome,
            "evidence_ids": evidence_ids, "explanation": explanation, "supersedes": supersedes}, event_id, validate=validate)

    def scores(self) -> dict:
        resolutions = {r["body"]["question_id"]: r for r in self.events("resolution")}
        expired = {r["body"]["question_id"] for r in self.events("monitor_expired")}
        methods: dict[str, dict] = {}
        rows = []
        for f in self.events("forecast"):
            b = f["body"]
            m = methods.setdefault(b["method"], {"attempts": 0, "predicted": 0, "failed": 0,
                "abstained": 0, "resolved": 0, "pending": 0, "expired": 0, "brier": None})
            m["attempts"] += 1
            m[b["status"]] += 1
            resolution = resolutions.get(b["question_id"])
            if b["status"] == "predicted":
                if resolution:
                    loss = (b["probability"] - resolution["body"]["outcome"]) ** 2
                    rows.append({"forecast_id": f["id"], "question_id": b["question_id"],
                        "snapshot_id": b["snapshot_id"], "method": b["method"], "brier": loss,
                        "resolution_id": resolution["id"]})
                    m["resolved"] += 1
                elif b["question_id"] in expired:
                    m["expired"] += 1
                else:
                    m["pending"] += 1
        for method, summary in methods.items():
            losses = [r["brier"] for r in rows if r["method"] == method]
            summary["brier"] = sum(losses) / len(losses) if losses else None
            summary["coverage"] = summary["predicted"] / summary["attempts"]
        return {"methods": methods, "rows": rows, "resolution_policy": "latest correction; IDs retained in every score",
                "interpretation": "Descriptive scores, not a significance or causal claim. Compare matched question/snapshot pairs."}

    def compare(self, left: str, right: str) -> dict:
        rows = self.scores()["rows"]
        groups = {method: {(r["question_id"], r["snapshot_id"]): r for r in rows if r["method"] == method}
                  for method in (left, right)}
        common = sorted(groups[left].keys() & groups[right].keys())
        differences = [groups[right][k]["brier"] - groups[left][k]["brier"] for k in common]
        return {"left": left, "right": right, "matched": len(common),
            "right_minus_left_brier": sum(differences) / len(differences) if differences else None,
            "pairs": [{"question_id": k[0], "snapshot_id": k[1]} for k in common],
            "note": "Same questions and snapshots; model/budget matching and family dependence still require protocol review."}

    def verify(self) -> dict:
        errors = []
        previous = "0" * 64
        rows = self.events()
        for row in rows:
            payload = {k: row[k] for k in ("id", "kind", "recorded_at", "body", "previous_hash")}
            if row["previous_hash"] != previous or digest(canonical(payload).encode()) != row["hash"]:
                errors.append(f"Broken chain at {row['id']}")
            previous = row["hash"]
            if row["kind"] == "observation":
                h = row["body"]["content_hash"]
                p = self.root / "blobs" / h
                if not p.is_file() or digest(p.read_bytes()) != h:
                    errors.append(f"Missing or corrupted content: {h}")
        return {"valid": not errors, "events": len(rows), "head": previous, "errors": errors,
            "assurance": "Local integrity only. Truncation or a complete rewrite needs an external trusted checkpoint to detect."}

    def export(self) -> dict:
        return {"schema_version": 1, "exported_at": self.clock(), "integrity": self.verify(),
            "events": self.events(), "scores": self.scores(), "witness_status": "not independently timestamped"}
