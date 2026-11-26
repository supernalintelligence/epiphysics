"""Run with PYTHONPATH=engine python3 -m epiphysics --help."""

import argparse
import json
import sys
import os
import tempfile
from pathlib import Path

from .store import Ledger, canonical, utc_now
from .cycle import run_cycle
from .public_status import project_status, status_destination
from .assertions import record_assertion, assertions_as_of
from .manifests import register_manifest, forecast_manifest
from .transforms import execute_graph_transform
from .graph_views import execute_graph_views
from .materialization import materialize_graph_outputs


def _record_input(path):
    with Path(path).open("rb") as stream:
        raw = stream.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError("Record input exceeds 1 MB")
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"Duplicate JSON field: {key}")
            result[key] = value
        return result
    value = json.loads(raw, object_pairs_hook=pairs)
    if not isinstance(value, dict):
        raise ValueError("Record input must be a JSON object")
    canonical(value)
    return value


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
    record.add_argument("kind", choices=["question", "representation", "forecast", "resolution", "assertion", "manifest", "manifest-forecast"])
    record.add_argument("file")
    transform = sub.add_parser("graph-transform", help="Execute a retained recipe for a fixed identity or induced-subgraph operation")
    transform.add_argument("file", help="Bounded JSON with parent_manifest_id, recipe_observation_id, and run_key")
    graph_views = sub.add_parser("graph-views", help="Execute retained graph partition or strict merge recipes")
    graph_views.add_argument("file", help="Bounded JSON with parent_manifest_ids, recipe_observation_id, and run_key")
    materialize = sub.add_parser("materialize-graphs", help="Atomically materialize verified graph outputs into representations and manifests")
    materialize.add_argument("file", help="Bounded JSON with completion_id and run_key")
    assertions = sub.add_parser("assertions", help="Query unsuperseded assertions at a recorded knowledge time")
    assertions.add_argument("--known-at", required=True)
    assertions.add_argument("--valid-at")
    assertions.add_argument("--observer")
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
    public = sub.add_parser("publish-status", help="Replace a public aggregate status artifact; no source bytes or local paths")
    public.add_argument("--source", required=True, help="Exact public README file captured by this dedicated store")
    public.add_argument("--output", required=True)
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
                data = _record_input(args.file)
                if args.kind == "assertion":
                    result = record_assertion(ledger, **data)
                elif args.kind == "manifest":
                    result = register_manifest(ledger, **data)
                elif args.kind == "manifest-forecast":
                    result = forecast_manifest(ledger, **data)
                else:
                    method = "resolve" if args.kind == "resolution" else args.kind
                    result = getattr(ledger, method)(**data)
            elif args.command == "assertions":
                result = assertions_as_of(ledger, args.known_at, valid_at=args.valid_at, observer=args.observer)
            elif args.command == "graph-transform":
                result = execute_graph_transform(ledger, **_record_input(args.file))
            elif args.command == "graph-views":
                result = execute_graph_views(ledger, **_record_input(args.file))
            elif args.command == "materialize-graphs":
                result = materialize_graph_outputs(ledger, **_record_input(args.file))
            elif args.command == "score":
                result = ledger.scores()
            elif args.command == "compare":
                result = ledger.compare(args.left, args.right)
            elif args.command == "verify":
                result = ledger.verify()
            elif args.command == "cycle":
                result = run_cycle(ledger, args.config, args.run_key)
            elif args.command == "publish-status":
                result = project_status(ledger, args.source)
            else:
                result = ledger.export()
        rendered = json.dumps(result, indent=2, allow_nan=False)
        if getattr(args, "output", None):
            output = Path(args.output)
            if args.command == "publish-status":
                output = status_destination(output, ledger.root, args.source)
            output.parent.mkdir(parents=True, exist_ok=True)
            if args.command == "publish-status":
                # This explicit command replaces only the derived public status, never evidence.
                with tempfile.NamedTemporaryFile(mode="w", dir=output.parent, delete=False) as stream:
                    stream.write(rendered + "\n")
                    temporary = stream.name
                try:
                    os.replace(temporary, output)
                finally:
                    if os.path.exists(temporary):
                        os.unlink(temporary)
            else:
                # Evidence exports are new artifacts; never silently replace an old one.
                with output.open("x") as stream:
                    stream.write(rendered + "\n")
            print(f"Wrote {output}")
        else:
            print(rendered)
        if args.command == "graph-transform" and result["kind"] == "graph_transform_rejected":
            return 2
        if args.command == "graph-views" and result["kind"] == "graph_views_rejected":
            return 2
        if args.command == "materialize-graphs" and result["kind"] == "graph_materialization_rejected":
            return 2
        return 1 if args.command == "verify" and not result["valid"] else 0
    except (ValueError, OSError, TypeError, KeyError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 2
    finally:
        if ledger:
            ledger.close()


if __name__ == "__main__":
    raise SystemExit(main())
