"""Bounded, deterministic collection/evaluation cycle; no model calls or shell execution."""

from __future__ import annotations

import json
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener

from .store import Ledger, instant


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError("Redirect refused; configure the final source URL explicitly")


def fetch(source: dict, config_dir: Path, max_bytes: int = 1_000_000) -> bytes:
    if source["kind"] == "file":
        path = (config_dir / source["path"]).resolve()
        with path.open("rb") as stream:
            content = stream.read(max_bytes + 1)
    elif source["kind"] == "https":
        url = urlparse(source["url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            raise ValueError("Only explicit credential-free HTTPS sources are supported")
        request = Request(source["url"], headers={"User-Agent": "Epiphysics-Observatory/0.1"})
        with build_opener(NoRedirect()).open(request, timeout=10) as response:
            content = response.read(max_bytes + 1)
    else:
        raise ValueError("Unknown source kind")
    if len(content) > max_bytes:
        raise ValueError("Source exceeds collection size limit")
    return content


class _MonitorNotExpirable(ValueError):
    """A concurrent resolution or the current time prevents expiry."""


def _expire_monitors(ledger: Ledger) -> list[str]:
    expired = []
    closed = {r["body"]["question_id"] for kind in ("resolution", "monitor_expired") for r in ledger.events(kind)}
    for monitor in ledger.events("monitor"):
        body = monitor["body"]
        question_id = body["question_id"]
        if question_id in closed:
            continue
        question = ledger.get(question_id, "question")["body"]
        window_end = instant(question["resolve_after"]) + timedelta(seconds=body["max_lateness_seconds"])
        if instant(ledger.clock()) <= window_end:
            continue

        def validate(now):
            if instant(now) <= window_end or any(
                r["body"]["question_id"] == question_id
                for kind in ("resolution", "monitor_expired") for r in ledger.events(kind)
            ):
                raise _MonitorNotExpirable()

        try:
            event = ledger.append("monitor_expired", {"question_id": question_id,
                "reason": "No successful capture inside resolution window"},
                f"monitor:{question_id}:expired", validate=validate)
        except _MonitorNotExpirable:
            continue
        expired.append(event["id"])
        closed.add(question_id)
    return expired


def run_cycle(ledger: Ledger, config_path: str | Path, run_key: str) -> dict:
    path = Path(config_path).resolve()
    config = json.loads(path.read_text())
    sources = config.get("sources", [])
    if not 1 <= len(sources) <= 10 or len({s["id"] for s in sources}) != len(sources):
        raise ValueError("Configure 1–10 sources with unique IDs")
    horizon = int(config.get("horizon_seconds", 86400))
    lateness = int(config.get("max_lateness_seconds", 3600))
    if horizon < 120 or not 0 <= lateness <= 604800:
        raise ValueError("Horizon must be >=120 seconds; lateness between 0 and 7 days")
    starts = [r for r in ledger.events("cycle_started") if r["body"]["run_key"] == run_key]
    complete = [r for r in ledger.events("cycle_completed") if r["body"]["run_key"] == run_key]
    if complete:
        return complete[-1]["body"]
    if starts:
        raise ValueError("Interrupted cycle: inspect its records, then use a new run key; no blind replay")
    ledger.append("cycle_started", {"run_key": run_key, "config": config}, f"cycle:{run_key}:start", exclusive=True)
    captured, failures, resolved = [], [], []
    for source in sources:
        label = source.get("url") or str((path.parent / source.get("path", "")).resolve())
        try:
            content = fetch(source, path.parent)
            earlier = [e for e in ledger.events("observation") if e["body"]["source"] == label]
            observation = ledger.capture(label, content, revision_of=earlier[-1]["id"] if earlier else None)
            captured.append(observation["id"])
        except Exception as error:
            failure = ledger.append("collection_failed", {"run_key": run_key, "source_id": source["id"],
                "source": label, "error": type(error).__name__, "message": str(error)[:400]})
            failures.append(failure["id"])
            continue
        resolutions = {r["body"]["question_id"] for r in ledger.events("resolution")}
        expired = {r["body"]["question_id"] for r in ledger.events("monitor_expired")}
        for monitor in ledger.events("monitor"):
            b = monitor["body"]
            if b["source"] != label or b["question_id"] in resolutions | expired:
                continue
            q = ledger.get(b["question_id"], "question")["body"]
            due = instant(q["resolve_after"])
            now = instant(observation["recorded_at"])
            if due <= now <= due + timedelta(seconds=b["max_lateness_seconds"]):
                result = ledger.resolve(b["question_id"], int(observation["body"]["content_hash"] != b["initial_hash"]),
                    [observation["id"]], explanation="Compare exact content hashes at the first successful scheduled capture in the declared window.")
                resolved.append(result["id"])
        snapshot = ledger.snapshot()
        now = instant(ledger.clock())
        question = ledger.question(f"Will the captured bytes of {source['id']} change at the first successful collection after the horizon?",
            (now + timedelta(seconds=60)).isoformat(), (now + timedelta(seconds=horizon)).isoformat(),
            f"SHA-256 differs from the current capture. First successful capture at/after the horizon, at most {lateness}s late. Otherwise unresolved/expired. This measures bytes, not semantic change.",
            f"source:{source['id']}")
        ledger.append("monitor", {"question_id": question["id"], "source": label,
            "initial_hash": observation["body"]["content_hash"], "max_lateness_seconds": lateness})
        ledger.forecast(question["id"], snapshot["id"], "constant-0.5-v1", 0.5,
            model={"identifier": "constant-0.5-v1", "kind": "deterministic", "input": "registered question"},
            cost={"model_calls": 0, "tokens": 0})
    expired = _expire_monitors(ledger)
    result = {"run_key": run_key, "captured": captured, "collection_failures": failures, "resolved": resolved, "expired": expired,
        "scores": ledger.scores(), "scope": "Collection baseline; learned predictions and semantic resolution are not enabled"}
    ledger.append("cycle_completed", result, f"cycle:{run_key}:complete")
    return result
