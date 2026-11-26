# Bounded autonomous research cadence

Run one bounded cycle per scheduled wake, then at most one ready research or engineering task. Use the active worktree until its reviewed changes are landed. Read the current build plan, queue, and latest decisions before editing; coordinate with SCI through the existing authorized project channel when scientific direction or file ownership overlaps.

1. Verify the local ledger before adding evidence. On a failed integrity check, stop writes and preserve the store for diagnosis.
2. Run `PYTHONPATH=engine python3 -m epiphysics --store .supernal-local/observatory cycle --config engine/examples/project-cycle.json --run-key YYYY-MM-DD-project`, using the current UTC date and running collection from the shared checkout after the slice is landed. Keep that persistent store outside disposable worktrees. Reusing the same completed key is a no-op. Never rewrite timestamps or resolve a missed window from memory.
3. Refresh `src/components/home/observatory-status.json` with `publish-status`, selecting the canonical shared-checkout README and persistent store. Do this in the managed worktree for the status change; the collector always uses the shared source path. Publish only verified aggregate status through the normal reviewed site workflow. Never copy the private ledger or its raw contents into the website.
4. Choose the highest-priority unblocked item in `TODO.md`. Work on one item, with a 30-minute active-work limit. Preserve an evidence-backed progress entry under `docs/planning/runs/`; record failures and incomplete work as well as success.
5. Run checks relevant to that change. Keep final evaluation data separate from search and prompt tuning. A bad result creates a question for the next run, not permission to change an earlier prediction or outcome rule.
6. Obtain independent review and use the repository's normal landing process for code. Keep public claims tied to actual test results. Draft posts and publication artifacts for review; no unsolicited outreach or automatic social posting.
7. Report a meaningful completed change, failed run, or decision needed. The scheduler can wake the work; it cannot guarantee research progress or growth.

Default limits: zero paid model calls, no purchases, at most ten explicitly configured sources, one collection attempt per source per run, one core task in progress. HTTPS source additions require documented provenance and a collection purpose; the local README monitor is the initial scheduling test. Expanding model use requires an explicit budget and an implemented budget guard.

The local scheduling service depends on the host being available. Local evidence is not a historical archive until enough forward observations accumulate, and it is not independently timestamped until a witness adapter is implemented. Archive local data separately from Git.

## Existing falsification cycle

The following project protocol remains available for substantive theory experiments; its longer timeboxes do not override the bounded scheduler run above.

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
5. What needs review/escalation (e.g., FLUX/VERIFY)

**Output:** concise status update to Mission Control + `DECISIONS.md` entry.

---

## Cadence Guardrails

- Evidence over narrative
- One active core hypothesis lane
- No application-note drafting until cycle gates pass
- Max 2 full falsification cycles before mandatory framework-review memo

---

## Ownership

- EPIPHYSICS: lead execution + synthesis
- FLUX: optimization review / process tuning
- VERIFY: rigor audits / anti-bias checks
