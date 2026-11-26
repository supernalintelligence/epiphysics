---
title: "Bounded autonomous research cadence"
description: "Supervisor instructions for immediate measured follow-up within hourly research wakes."
date: 2026-11-25
tts:
  enabled: false
feedback:
  enabled: false
---

# Bounded autonomous research cadence

The supervisor cadence is hourly, with immediate continuation during each bounded wake. The filename is retained for existing links. Read the [stepwise loop](docs/planning/stepwise-improvement-loop.md), [metric contracts](docs/experiments/representation-metrics.md), `TODO.md`, the current build plan, and latest decisions. Coordinate overlapping scientific direction or file ownership with SCI through the existing authorized project channel.

An active cycle lasts at most **30 minutes or three core steps**, whichever comes first. Keep one core step in progress; delegate bounded construction to builder subagents and fixed assessments to program workers while the primary supervises. Support work can run in parallel with separate ownership and within that same budget. Do not wait for the next hourly wake when a reviewed successor is ready and time remains.

1. Read improvement status from its dedicated persistent store outside disposable worktrees. Verify integrity before writes; on failure, preserve the store and diagnose. Do not mix improvement and observatory events. Inspect unfinished claims and worker receipts before resuming; never blindly replay an interrupted worker.
2. Dispatch the queued action to the appropriate worker. A program can run the fixed offline evaluator; a scoped builder implements a code packet. The current ordered rule is time integrity, provenance, coverage, weakest family, then missing source-span capability. Its success probability and cost estimates are null. Use the active worktree until reviewed changes land.
3. Have the worker return actual changes, relevant checks, failures, and resource use. Obtain independent review before accepting a code packet. Do not treat an oracle fixture pass or the free-text `completed_work` field as proof that a build completed.
4. Assess the candidate through `epiphysics.improvement dispatch`, using current `next_step.id` as `--after-step` and a new run key for changed inputs. Assessment completion and its successor are recorded atomically. Compare changes only when suite/evaluator/policy hashes match; `incomparable_contract_change` has no delta or target judgment. Candidate/controller changes alone can remain comparable, without implying causality. Read the new authoritative state and immediately dispatch the next eligible action while the cycle budget remains; otherwise preserve the handoff for the next wake.
5. Close Packet A only with source-span implementation, new reviewed fixtures and metric contract version, and a selector update that can recognize the completed capability. The present evaluator does not measure `source_span_resolution`; its unconditional fallback would otherwise keep queuing A. Do not repeat a known control run simply to fill a wake.
6. Maintain observatory collection separately when its daily window is due. Run `PYTHONPATH=engine python3 -m epiphysics --store .supernal-local/observatory cycle --config engine/examples/project-cycle.json --run-key YYYY-MM-DD-project` from the shared checkout, using the current UTC date and its canonical source paths. One attempt per configured source per run; the same completed key is a no-op. An hourly supervisor does not change this collector's daily key or invent missed windows.
7. Refresh `src/components/home/observatory-status.json` with `publish-status` only when a new verified aggregate is available. Use the persistent observatory store and canonical shared-checkout README; write the artifact in the managed worktree. Keep private ledger contents, captured inputs, and process receipts out of public exports.
8. Preserve an evidence-backed run entry under `docs/planning/runs/`, including incomplete work and failures, remaining queue, and the reason for stopping. Use normal repository checks, independent review, and landing policy. Report only a meaningful completed change, failure, or decision needed. Draft publication artifacts for review; no unsolicited outreach or automatic social posting.

Program commands and receipt details are in the stepwise loop. `dispatch` allows only a fresh Python process running the offline assessment, with at most 60 seconds and 1 MB output. The example assessment policy is 30 seconds, offline fixtures only, zero external spend, and no scale change. This is trusted local process supervision, not a security sandbox. Its timeout requires the dispatcher to remain alive; a start receipt without a finish receipt requires process investigation after a crash.

A nonzero exit does not always mean the assessment failed. For `assessment_completed_delivery_failed`, inspect `delivery_status`, `authoritative_transition_id`, the bounded `authoritative_transition`, and current status. Preserve that completion and consume its queued successor; do not rerun work because result output hit the cap. With no confirmed transition, inspect the receipts and ledger. Invalid JSON/policy can be refused before claiming a step, leaving the queue unchanged and the refusal in dispatched-child receipts/output. Dispatcher validation can fail even before receipts exist. Recovery may close only its own reaped child's unfinished claim, never an unrelated claim or completed result.

Default research limits remain zero paid model calls, no purchases, and at most ten explicitly configured collection sources. HTTPS additions require documented provenance and a collection purpose. Expanded model use requires an explicit authorized budget and implemented guard. The controller cannot grant itself new access, spending, deployment, or settlement rights. Shadow, canary, and multiple-service stages remain gated future work.

The heartbeat depends on host/session availability; the queue does not execute itself. Local evidence becomes a prospective archive through actual observations and remains without independent timestamp assurance until a witness adapter is implemented. Archive local data separately from Git. Keep final evaluation separate from search and tuning; a bad result creates a next question, not permission to revise an earlier forecast or outcome rule.

## Existing falsification cycle

The following project protocol remains available for substantive theory experiments. Its time estimates are cumulative work across bounded cycles, not permission to exceed the 30-minute/three-step supervisor window. Preserve the same experiment identity and stopping rule between wakes.

## Epiphysics falsification loop

Purpose: keep theory work, experiments, and issue execution moving every day with auditable outputs.

## 0) Open the loop (5 min)

- Read:
  - `docs/experiments/epiphy-7day-falsification-plan.md`
  - `DECISIONS.md`
- Confirm active cycle/day and current gating status.

**Output:** one-line "today objective" entry in `DECISIONS.md`.

---

## 1) Check issues / queue (15–25 min)

Scope:
- repo TODOs
- experiment blockers
- theory consistency gaps
- externally reported issues

Rules:
- classify each item: `critical`, `today`, `queued`, `parked`
- cap active WIP to 1 core hypothesis lane + 2 support tasks

**Output:** prioritized short list for today.

---

## 2) Simple research pass (45–90 min)

Goal:
- gather only what is needed to unblock current experiment/issue
- avoid broad speculative research

Method:
- run a focused question list (max 3)
- save only decision-relevant findings
- tag findings with source links/paths

**Output:** short research memo (bullets + citations + impact on plan).

---

## 3) Prioritize + plan updates (20–30 min)

- update day plan against active gates:
  - Track A reliability gate
  - Track B theory-test eligibility
- lock any thresholds/ranges before running
- note expected stop condition for each phase

**Output:** updated day plan and explicit kill criteria for today’s run.

---

## 4) Execute issues + experiments (2–6h blocks)

Execution rules:
- hard timebox per phase
- run null/baseline checks first where required
- do not promote claims if Track A gate fails
- capture failures as first-class results

**Output:**
- run artifacts (tables/plots/logs)
- pass/fail/inconclusive judgment per experiment

---

## 5) Report (15–30 min)

Daily report format:
1. What was run
2. What passed/failed
3. What changed in assumptions
4. What is next
5. What needs independent review or an explicit decision

**Output:** concise local run record and `DECISIONS.md` entry. Send external status only through an authorized channel when requested.

---

## Cadence Guardrails

- Evidence over narrative
- One active core hypothesis lane
- No application-note drafting until cycle gates pass
- Max 2 full falsification cycles before mandatory framework-review memo

---

## Ownership

- Primary supervisor: selects and supervises work, maintains the queue and synthesis, dispatches the successor within the active window.
- Builder subagents: perform scoped implementation or research and return checkable artifacts.
- Allowlisted program workers: run fixed assessment programs and retain process receipts.
- Independent reviewer/evaluator: reviews rigor and acceptance; preserves separation from candidate optimization. Historical role labels do not establish a currently running agent or grant extra authority.
