"""Public aggregate status for the explicitly selected project README monitor."""

from pathlib import Path

from .store import Ledger


def project_status(ledger: Ledger, source_file: str) -> dict:
    source = str(Path(source_file).resolve())
    # Keep every database read on the same snapshot while other collectors append.
    ledger.db.execute("BEGIN")
    try:
        events = ledger.events()
        observations = [r for r in events if r["kind"] == "observation"]
        if not observations:
            raise ValueError("Collect the public project source before publishing status")
        if any(r["body"]["source"] != source for r in observations):
            raise ValueError("Status export requires a dedicated store containing only the selected public source")
        questions = [r for r in events if r["kind"] == "question"]
        if any(r["body"]["family"] != "source:epiphysics-readme" for r in questions):
            raise ValueError("Status export supports only the project README collection baseline")
        forecasts = [r["body"] for r in events if r["kind"] == "forecast"]
        if any(f["method"] != "constant-0.5-v1" or f["status"] != "predicted" or f["probability"] != 0.5
               for f in forecasts):
            raise ValueError("Status export requires constant-0.5-v1 predicted forecasts with probability 0.5")
        integrity = ledger.verify()
        if not integrity["valid"]:
            raise ValueError("Refusing to publish status from a ledger with failed integrity checks")
        methods = ledger.scores()["methods"]
        return {
            "schema_version": 1,
            "recorded_through": events[-1]["recorded_at"],
            "last_capture_at": observations[-1]["recorded_at"],
            "source": "Project README",
            "source_url": "https://github.com/supernalintelligence/epiphysics/blob/main/README.md",
            "scope": "Collection check: exact file-byte changes, constant probability 0.5. Not a test of predictive skill.",
            "integrity": "Local chain and source bytes verified",
            "timestamp_assurance": "Local collector clock; no independent witness",
            "observations": len(observations),
            "forecasts": sum(m["attempts"] for m in methods.values()),
            "resolved": sum(m["resolved"] for m in methods.values()),
            "pending": sum(m["pending"] for m in methods.values()),
            "expired": sum(m["expired"] for m in methods.values()),
            "collection_failures": sum(r["kind"] == "collection_failed" for r in events),
        }
    finally:
        ledger.db.rollback()


def status_destination(output: Path, store: Path, source_file: str) -> Path:
    """Resolve a derived JSON destination without permitting evidence replacement."""
    destination = output.resolve()
    source = Path(source_file).resolve()
    if destination.is_relative_to(store.resolve()):
        raise ValueError("Public status output must be outside the evidence store")
    if destination == source or (destination.exists() and source.exists() and destination.samefile(source)):
        raise ValueError("Public status output must not alias the selected source")
    if destination.suffix.lower() != ".json":
        raise ValueError("Public status output must be a .json artifact")
    return destination
