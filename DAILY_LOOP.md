---
title: "Bounded autonomous research cadence"
description: "Supervisor instructions for continuous authorized work, measured checkpoints, and recovery wakes."
date: 2026-11-25
tts:
  enabled: false
feedback:
  enabled: false
---

# Bounded autonomous research cadence

The supervisor continues ready, authorized work while its session is active. A 15-minute heartbeat is a recovery backstop, not the pace of execution. The filename is retained for existing links. Read the [stepwise loop](docs/planning/stepwise-improvement-loop.md), [metric contracts](docs/experiments/representation-metrics.md), `TODO.md`, the current build plan, and latest decisions. Coordinate overlapping scientific direction or file ownership with SCI through the existing authorized project channel.

Reach a **checkpoint every 30 minutes or three core steps**, whichever comes first: record progress, review outcomes and resources, refresh priorities, and continue the next eligible step immediately. A checkpoint is not a reason to end active work. Keep one core step in progress; delegate scoped construction to builder subagents and fixed assessments to program workers while the primary supervises. Support work can run in parallel with separate ownership. Check the existing active job before any wake dispatch; join or inspect it rather than starting a duplicate. Stop or hand off only for an actual blocker, exhausted authorized resource limit, user instruction, completed scope, or unavailable session.

1. Read improvement status from its dedicated persistent store outside disposable worktrees. Verify integrity before writes; on failure, preserve the store and diagnose. Do not mix improvement and observatory events. Inspect unfinished claims and worker receipts before resuming; never blindly replay an interrupted worker.
2. Dispatch the queued action to the appropriate worker. A program can run the fixed offline evaluator; a scoped builder implements a code packet. The current ordered rule is time integrity, provenance, coverage, weakest family, then source-span/history, manifest, fixed-transform, graph-view and materialization capability failures. Passing all preceding gates selects the frozen retrieval baseline (Packet C) until actual retrieval is measured. A validated study then selects reproduction repair, a support-ranking comparison or bounded coverage evaluation from its separate metrics. A valid completed raw/HTML comparison consumes that comparison task and advances to fresh coverage for a gain, tie or regression; it does not select the same experiment again from the same visible errors. Its success probability and cost estimates are null. Use the active worktree until reviewed changes land.
3. Have the worker return actual changes, relevant checks, failures, and resource use. Obtain independent review before accepting a code packet. Do not treat an oracle fixture pass or the free-text `completed_work` field as proof that a build completed.
4. Assess the candidate through `epiphysics.improvement dispatch`, using current `next_step.id` as `--after-step` and a new run key for changed inputs. Assessment completion and its successor are recorded atomically. Compare changes only when the registered measurement contract matches; `incomparable_contract_change` has no delta or target judgment. Candidate/controller changes alone can remain comparable, without implying causality. Read the new authoritative state and immediately dispatch the next eligible action. At a checkpoint, review and record the handoff, then continue while the session and authorized resources remain available.
5. Inspect the actual capability probes as well as representation scores. `source-span-probes-v1` has eight source-span and six assertion-history checks; both metrics must reach 1 before the selector recommends Packet B. A failure queues `repair_source_span_assertions`. The later gates are twenty-two manifest, twenty-six identity/projection, forty-five partition/merge and thirty output-materialization checks. Supply the declared actual study through `--retrieval-study FILE` to measure `retrieval_baseline_reproducibility`: close Packet C only after two distinct actual executions over a frozen eligible corpus validate against reviewed questions and an explicit evaluation contract. Keep the source archive read-only and the captured improvement inputs private; absent input remains unmeasured. Do not repeat a known control run simply to fill a wake.
6. Maintain observatory collection separately when its daily window is due. Run `PYTHONPATH=engine python3 -m epiphysics --store .supernal-local/observatory cycle --config engine/examples/project-cycle.json --run-key YYYY-MM-DD-project` from the shared checkout, using the current UTC date and its canonical source paths. One attempt per configured source per run; the same completed key is a no-op. A 15-minute heartbeat does not change this collector's daily key or invent missed windows.
7. Refresh `src/components/home/observatory-status.json` with `publish-status` only when a new verified aggregate is available. Use the persistent observatory store and canonical shared-checkout README; write the artifact in the managed worktree. Keep private ledger contents, captured inputs, and process receipts out of public exports.
8. Preserve an evidence-backed internal run entry under `docs/planning/runs/` with `draft: true`, including incomplete work and failures, remaining queue, and any reason for stopping. Put a reviewed public result under `docs/experiments/results/`; public pages and homepage summaries must link only to published records. Use normal repository checks, independent review, and landing policy. Report only a meaningful completed change, failure, or decision needed. No unsolicited outreach or automatic social posting.

Program commands and receipt details are in the stepwise loop. `dispatch` allows only a fresh Python process running the offline assessment, with at most 60 seconds and 1 MB output. The example assessment policy is 30 seconds, offline fixtures only, zero external spend, and no scale change. This is trusted local process supervision, not a security sandbox. Its timeout requires the dispatcher to remain alive; a start receipt without a finish receipt requires process investigation after a crash.

A nonzero exit does not always mean the assessment failed. For `assessment_completed_delivery_failed`, inspect `delivery_status`, `authoritative_transition_id`, the bounded `authoritative_transition`, and current status. Preserve that completion and consume its queued successor; do not rerun work because result output hit the cap. With no confirmed transition, inspect the receipts and ledger. Invalid JSON/policy can be refused before claiming a step, leaving the queue unchanged and the refusal in dispatched-child receipts/output. Dispatcher validation can fail even before receipts exist. Recovery may close only its own reaped child's unfinished claim, never an unrelated claim or completed result.

Default research limits remain zero paid model calls, no purchases, and at most ten explicitly configured collection sources. HTTPS additions require documented provenance and a collection purpose. Expanded model use requires an explicit authorized budget and implemented guard. The controller cannot grant itself new access, spending, deployment, or settlement rights. Shadow, canary, and multiple-service stages remain gated future work.

The heartbeat depends on host/session availability; the queue does not execute itself. Local evidence becomes a prospective archive through actual observations and remains without independent timestamp assurance until a witness adapter is implemented. Archive local data separately from Git. Keep final evaluation separate from search and tuning; a bad result creates a next question, not permission to revise an earlier forecast or outcome rule.

The accepted C9 diagnosis selects `prepare_dated_evidence_quality_protocol`. It reconciled the retained 96 attempts, including 4/22 verification disagreements and two bounded-retention losses per compact method; it did not rerun a candidate. Continue into preparation immediately after checking its actual acceptance and audit. Freeze one future artifact-delivery protocol with exact criteria, bytes, actor roles, verification method and date semantics. Preparation needs its own checked completion and executable successor; do not consume the queue with a generic fixture assessment. Keep evidence origin separate from the immediate queue parent. The C8/C9 results and prior site builds are already observed and cannot become a prospective holdout. An empty future-data queue is an honest waiting state, not permission to fabricate work or repeat exposed tests. Continue independent eligible backlog work while waiting.

## Verified SCI coordination

The user authorized coordination with SCI in this work. A local mailbox write alone is not delivery. The B2c run verified an existing native Claude session delivery receipt and an actual SCI reply confirming separate file ownership; see [the run record](docs/planning/runs/2026-11-25-graph-materialization.md). SCI owns its canonical mathematics note and reports no engine dependency. Preserve its files and unrelated shared-checkout edits.

Use an available live-session message tool when it can reach the intended agent. If only the persistent mailbox is available, inspect the documented native-session adapter and the exact existing session state before using it; do not choose “latest,” start a duplicate conversation, resume a busy session, or equate queue acceptance with receipt. Keep delivery evidence and the actual reply in the local coordination record. No idle polling should launch model turns. This is a coordination path for an authorized recipient, not a general outreach permission.

C6 exposed a concrete transport limitation: the installed `agent-msg native-receive` implementation invokes native resume without checking idleness. Its description is not an idle-session guard. An active SCI session was reached instead through its live `ListAgents` and `SendMessage` tools, using a delivery-only Claude CLI bridge when those tools were unavailable in Codex. Restrict such a bridge to the two messaging tools and one authorized message; do not resume the working session or give the bridge editing tools. Preserve the target, message identifier and actual reply. A short-lived bridge may close before the reply arrives; check the recipient's recorded outgoing reply before resending. Record this agent usage separately from experiment-program calls and costs. The verified C6 reply also keeps local landing separate from SCI's release promotion and preserves unrelated shared-checkout changes.

At each checkpoint and before repeating a failed check, also inspect the bounded mailbox addressed to this Codex chat (`agent-msg inbox --to <chat-id>`), fetch relevant message IDs with `agent-msg get --id`, and record the consumed IDs and resulting decisions in the coordination receipt. A recipient can reply there after the delivery bridge exits. C7 recovered an earlier SCI report of the same coverage-freeze race from that mailbox; watching only the bridge had missed it. Do not equate an unread mailbox entry, an accepted delivery, or another agent's unverified release report with a verified result. Keep the actual reply and distinguish independently checked facts from reported status.

## Existing falsification cycle

The following project protocol remains available for substantive theory experiments. Its longer work estimates include regular 30-minute/three-step checkpoints and must respect each experiment's resource ceilings. Checkpoints preserve continuity; they do not end an active research session. Preserve the same experiment identity and stopping rule between wakes.

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

- Primary supervisor: selects and supervises work, maintains the queue and synthesis, reviews checkpoints, and dispatches ready successors throughout the active session.
- Builder subagents: perform scoped implementation or research and return checkable artifacts.
- Allowlisted program workers: run fixed assessment programs and retain process receipts.
- Independent reviewer/evaluator: reviews rigor and acceptance; preserves separation from candidate optimization. Historical role labels do not establish a currently running agent or grant extra authority.
