# Owned release-or-hold development pilot

One delegated-work simulation compares a chronological retention recipe with a
task-proximity recipe. Both use the same dated public input, conservative policy,
and 2,048-byte view ceiling. Separate 32,768-byte controls preserve every available
record. The independent evaluator has world rights and later artifact outcomes;
candidate processes receive only the public header/tape, recipe and byte limit.

This folder contains twelve exposed owned fixtures, the reviewed contracts, the
exact format-check program/output, and a summary of the single recorded comparison.
No protected final cohort exists here. Neither the policy nor the effect reducer
is a payment service. Full-source provenance verification costs are included.

To reproduce in a new output directory, from the repository root with Python 3.14:

```bash
mkdir /tmp/owned-decision-reproduction
PYTHONPATH=engine python3.14 -s -m epiphysics.decision_pilot \
  --cohort engine/examples/control-exchange/development-traces.json \
  --output /tmp/owned-decision-reproduction/result.json
```

The command refuses an existing result or attempt journal. It writes each returned
worker output and evaluated attempt before proceeding. Worker time/output bounds
apply; a 30-second computation alarm also covers the parent. Use a separately
bounded caller for the whole process including final persistence. Interrupted
runs retain available evidence and have no complete-cohort metrics. Do not rerun
an interrupted registered experiment without diagnosing its saved claim/receipts.

The result records four arms with twelve attempts each, per-mechanism counts,
numerators/denominators, serialized views, exact output bytes, and nonoverlapping
stage times. Nested wall times must not be added. Builder/reviewer cost and memory
remain unmeasured. The included summary is descriptive development evidence, not
an independent execution witness or adoption decision.

`decision_assessment` checks retained outputs without running either candidate.
The improvement controller accepts a checked study through `--decision-study` and
atomically records its successor with completion. A study request contains
`schema_version: 1`, `study_id`, `phase: "development"`, `origin: {"step_id": ...}`
and `paths` for `cohort`, `report`, `journal`, `decision_contract`, and
`evaluation_contract`. The origin must be the current queued decision-pilot step.
Private machine paths and process receipts belong outside this public folder.

The selector first requires conformance and completed execution. Failed checks
select repair; a checked development result selects preparation of one new
24-case exploratory comparison. That successor grants no live effects, extra
spend, automatic deployment, or increased authority.
