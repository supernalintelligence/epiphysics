# Local research engine

This first slice preserves observations, information snapshots, representation hypotheses, prospective binary forecasts, and corrected outcomes in a local SQLite event ledger. It runs with Python 3.10+ and the standard library. It does **not** yet learn representations, call an AI model, pay agents, or obtain independent timestamps.

## Run and verify

Run from the repository root:

```sh
PYTHONPATH=engine python3 -m unittest discover -s engine/tests -v
PYTHONPATH=engine python3 -m epiphysics --store engine/.data/demo demo --output engine/.data/demo-export.json
PYTHONPATH=engine python3 -m epiphysics --store engine/.data/demo verify
```

The demo uses fictional evidence, probabilities, outcome, and clock. It requires an empty store and never overwrites an existing export. Choose a new directory and filename to rerun. `src/components/home/observatory-demo.json` is the generated artifact displayed by `/observatory`.

## A bounded collection cycle

```sh
PYTHONPATH=engine python3 -m epiphysics --store engine/.data/local cycle --config engine/examples/local-cycle.json --run-key first
# Run later with a new scheduler key, at least two minutes after the first run.
PYTHONPATH=engine python3 -m epiphysics --store engine/.data/local cycle --config engine/examples/local-cycle.json --run-key second
PYTHONPATH=engine python3 -m epiphysics --store engine/.data/local score
```

Each cycle captures up to ten explicitly configured sources, resolves eligible earlier byte-change questions, creates new questions, and records a constant 0.5 forecast. Duplicate completed run keys return the original result. An interrupted run requires inspection and a new key; partial records remain. There is no retry loop or shell execution. This is a collection and scheduling test, not a substantive forecast of an institution or an AI system.

A source is either `{"id":"signal","kind":"file","path":"signal.txt"}` (relative to the configuration file) or `{"id":"public-source","kind":"https","url":"https://example.org/data"}`. Each response is limited to 1 MB and a ten-second network timeout; redirects are refused. Use only sources appropriate to archive. The configuration is trusted operator input, not a public API. It can read explicitly selected local files and network addresses; do not expose it to untrusted callers.

`horizon_seconds` must be at least 120. `max_lateness_seconds` is the allowed delay after that horizon, from zero through seven days. The question is whether exact bytes differ at the **first successful capture within that window**. Missing windows remain unresolved and receive an expiration record on a later cycle, even when collection fails. Dynamic timestamps in a page count as byte changes. Semantic interpretation is not implemented.

`engine/examples/project-cycle.json` monitors this project's README on a daily horizon with a 36-hour grace period. It is a plumbing baseline and can be invoked by the bounded research cadence in `DAILY_LOOP.md`. Manual examples use ignored `engine/.data/`. Scheduled project evidence uses the shared checkout’s `.supernal-local/observatory`, outside disposable worktrees; back it up separately. Run the scheduled configuration from that shared checkout so source paths remain stable. A scheduler invocation is required: the CLI does not run a daemon.

## Record contracts

Use `capture FILE --source LABEL [--published-at TIME] [--revision-of ID]`, then `snapshot [--cutoff TIME]`. `record KIND INPUT.json` accepts the following keyword fields; generated IDs from earlier commands must be substituted by the caller:

| Kind | Required fields | Optional fields |
| --- | --- | --- |
| `question` | `text`, `deadline`, `resolve_after`, `resolution_rule`, `family` | `event_id` |
| `representation` | `snapshot_id`, `model`, `observer`, `method` | `parent`, `event_id` |
| `forecast` | `question_id`, `snapshot_id`, `method`, `probability`, `model` | `representation_id`, `status`, `reason`, `cost`, `event_id` |
| `resolution` | `question_id`, `outcome`, `evidence_ids`, `explanation` | `supersedes`, `event_id` |

Times must include a timezone. Questions require now < deadline < resolution time. Each method gets one forecast attempt per question. Forecast model metadata must contain `identifier`; record the prompt hash, model version, input manifest, seed, and budget where relevant. A failed or abstained attempt uses `probability: null` and a reason. Costs are recorded metadata, not enforced budgets.

Representation models have `entities` and `relations` arrays. Entities need an `id`; relations need `source`, `target`, and `type`. Both need an epistemic `basis` (`observed`, `reported`, or `inferred`) and nonempty `evidence_ids` from the selected snapshot. A→B and B→A are distinct; no boundary is declared the uniquely real entity. Parent representations must preserve the observer and cannot point back from a later information cutoff.

Outcomes are integer 0 or 1 with evidence and an explanation. A correction must explicitly supersede the latest resolution. Scores retain the resolution ID used. `compare METHOD_A METHOD_B` matches the same question and snapshot and reports Brier(B)−Brier(A). It does not certify matched model budgets or statistical significance. `score` also reports pending and expired outcomes, failures, abstentions, and coverage.

`export --output NEW_FILE.json` writes metadata and event hashes; raw blobs remain in the store. `verify` checks every chain link and stored source blob, returning a nonzero status on detected corruption. No command deletes evidence.

## Assurance limits

Append-only triggers and hashes protect against accidental edits through this interface. An operator controlling the database, code, or clock can rewrite the entire history. Without an independently witnessed checkpoint, truncation and wholesale rewriting are not externally detectable. A blockchain anchor would establish prior existence of committed bytes under its assumptions; it would not establish truth, completeness, collection time, or a model's actual information access.

Snapshot selection uses collection time, never a source's publication claim. A model's training data, hidden memory, undeclared tools, or manual reasoning can still leak later information. Process isolation, model-access manifests, signed witness adapters, immutable public bundles, prospective holdouts, and independent resolution are next implementation gates. The current ledger is intended for a trusted local operator; it is not a multi-tenant service.

See `docs/planning/2026-11-24-recursive-observatory.md` for the component roadmap and `docs/experiments/prospective-observatory.md` for the evaluation protocol.

## Updating the site's collection record

The site imports `src/components/home/observatory-status.json`. This is a recorded aggregate refreshed by the daily app automation through reviewed commits/deployments, not a browser connection to a private local database. The first real collection was recorded on 25 November 2026; the example forecast remains clearly synthetic.

After collecting and verifying the dedicated README monitor, run from the checkout containing the engine:

```sh
PYTHONPATH=engine python3 -m epiphysics --store /absolute/shared-checkout/.supernal-local/observatory publish-status --source /absolute/shared-checkout/README.md --output src/components/home/observatory-status.json
```

This explicit command atomically replaces only the derived status file. It exports timestamps, counts, source link, and local assurance labels. It refuses a mixed-source store or a failed integrity check, and omits raw contents, local paths, prompts, and internal event IDs. Publish the changed artifact through the normal reviewed site workflow. A missed scheduler wake leaves an older visible capture time; it must not appear as a fresh successful run.
