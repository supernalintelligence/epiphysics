"""Run with PYTHONPATH=engine python3 -m epiphysics --help."""

import argparse
import json
import sys
from pathlib import Path

from .store import Ledger, canonical, utc_now
from .cycle import run_cycle


def demo(root):
    clock = ["2026-11-24T10:00:00+00:00"]
    ledger = Ledger(root, clock=lambda: clock[0])
    try:
        if ledger.events():
            raise ValueError("Demo needs an empty store; existing evidence is never replaced")
        ledger.append("demo_notice", {"synthetic": True, "notice": "Synthetic worked example; fictional inputs, outcomes, and clock. Not empirical validation."}, "demo-notice")
        obs = ledger.capture("synthetic:worker-queue", b"Worker A has two pending jobs. Worker B supplies data.", event_id="observation-before")
        snap = ledger.snapshot(event_id="snapshot-before")
        rep = ledger.representation(snap["id"], {"entities": [
            {"id": "worker-a", "label": "Worker A", "basis": "reported", "evidence_ids": [obs["id"]]},
            {"id": "worker-b", "label": "Worker B", "basis": "reported", "evidence_ids": [obs["id"]]}],
            "relations": [{"source": "worker-b", "target": "worker-a", "type": "supplies-data",
                "basis": "reported", "evidence_ids": [obs["id"]]}]}, observer="demo-observer", method="handwritten-example", event_id="representation-before")
        q = ledger.question("Will Worker A finish its queued jobs?", "2026-11-24T10:05:00+00:00",
            "2026-11-24T10:10:00+00:00", "Synthetic completion record reports zero pending jobs.", "synthetic-worker", "question-demo")
        for method, probability in [("baseline", 0.5), ("illustrative-representation", 0.7)]:
            ledger.forecast(q["id"], snap["id"], method, probability,
                model={"identifier": "handwritten-demo", "prompt": "No model was called"}, representation_id=rep["id"], event_id=f"forecast-{method}")
        clock[0] = "2026-11-24T10:11:00+00:00"
        outcome = ledger.capture("synthetic:worker-queue", b"Worker A has zero pending jobs.", revision_of=obs["id"], event_id="observation-after")
        ledger.resolve(q["id"], 1, [outcome["id"]], explanation="The fictional completion record reports zero pending jobs.", event_id="resolution-demo")
        exported = ledger.export()
        exported["synthetic"] = True
        exported["comparison"] = ledger.compare("baseline", "illustrative-representation")
        return exported
    finally:
        ledger.close()


def main():
    parser = argparse.ArgumentParser(description="Epiphysics local evidence and forecast ledger")
    parser.add_argument("--store", default="engine/.data/observatory")
    sub = parser.add_subparsers(dest="command", required=True)
    capture = sub.add_parser("capture", help="Capture exact local file bytes")
    capture.add_argument("file")
    capture.add_argument("--source")
    capture.add_argument("--published-at")
    capture.add_argument("--revision-of")
    snapshot = sub.add_parser("snapshot")
    snapshot.add_argument("--cutoff")
    record = sub.add_parser("record", help="Validated JSON input; see examples")
    record.add_argument("kind", choices=["question", "representation", "forecast", "resolution"])
    record.add_argument("file")
    sub.add_parser("score")
    compare = sub.add_parser("compare")
    compare.add_argument("left")
    compare.add_argument("right")
    sub.add_parser("verify")
    export = sub.add_parser("export")
    export.add_argument("--output")
    demo_parser = sub.add_parser("demo", help="Synthetic demonstration; requires an empty store")
    demo_parser.add_argument("--output")
    cycle = sub.add_parser("cycle", help="Run one bounded collection/evaluation cycle")
    cycle.add_argument("--config", required=True)
    cycle.add_argument("--run-key", required=True, help="Stable scheduler key; duplicate completed runs do nothing")
    args = parser.parse_args()
    ledger = None
    try:
        if args.command == "demo":
            result = demo(args.store)
        else:
            ledger = Ledger(args.store)
            if args.command == "capture":
                result = ledger.capture(args.source or str(Path(args.file).resolve()), Path(args.file).read_bytes(),
                    published_at=args.published_at, revision_of=args.revision_of)
            elif args.command == "snapshot":
                result = ledger.snapshot(args.cutoff)
            elif args.command == "record":
                method = "resolve" if args.kind == "resolution" else args.kind
                result = getattr(ledger, method)(**json.loads(Path(args.file).read_text()))
            elif args.command == "score":
                result = ledger.scores()
            elif args.command == "compare":
                result = ledger.compare(args.left, args.right)
            elif args.command == "verify":
                result = ledger.verify()
            elif args.command == "cycle":
                result = run_cycle(ledger, args.config, args.run_key)
            else:
                result = ledger.export()
        rendered = json.dumps(result, indent=2, allow_nan=False)
        if getattr(args, "output", None):
            output = Path(args.output)
            output.parent.mkdir(parents=True, exist_ok=True)
            # Exports are new artifacts; do not silently overwrite an old one.
            with output.open("x") as stream:
                stream.write(rendered + "\n")
            print(f"Wrote {output}")
        else:
            print(rendered)
        return 1 if args.command == "verify" and not result["valid"] else 0
    except (ValueError, OSError, TypeError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    finally:
        if ledger:
            ledger.close()


if __name__ == "__main__":
    raise SystemExit(main())
