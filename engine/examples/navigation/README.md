# Textual navigation contract

This directory contains the public C12 protocol contract, not the actual six-case cohort or private answer key. The unrelated marble-crate fixtures live only in tests. No study has been run by creating these examples.

The candidate public wire interface is implemented by `epiphysics.navigation_contracts`. It receives one fixed map and one public case on stdin, and returns one bounded JSON answer. Its source is frozen before independent task/key authorship. The task/key author must differ from the candidate and design authors; the reviewer must differ from candidate/task/key authors. These are locally reviewed attributions, not proof against a malicious host.

Preparation uses the existing `epiphysics.improvement assess --decision-study REQUEST` path with phase `evidence_navigation_preparation`, the contract in this directory and a packet selecting six captured inputs: `map`, `tasks`, `key`, `candidate`, `runtime`, `authorship`. Each input is an observation whose source is `improvement-input:evidence-navigation-preparation:STUDY_ID:ROLE`. The map must exactly match the accepted C11 map bytes. Latest scoped inputs are selected explicitly; an unchanged unsuccessful preparation cannot be retried. The accepted preparation registers all input hashes, the three execution/scoring source hashes, the runtime and fixed case order. It has no performance score.

After accepted registration, the fixed execution entry is:

```text
python -m epiphysics.navigation_runner --store ABSOLUTE_OWNED_STORE --registration-id ACCEPTED_EVENT_ID --registration-hash ACCEPTED_EVENT_HASH
```

This executes only the registered candidate source with the registered Python runtime and `-I`. The runner reads no key or authorship blob. Its exclusive directory and observation IDs prevent blind retry. It retains raw stdout/stderr prefixes and process facts before the post-process source audit. The six first attempts consume their slots even on nonzero exit, timeout, malformed JSON or output overflow. An interrupted run remains incomplete; absent attempts are never reported as executed.

The runner has a 750-second outer bound including its at-most-30-second preflight; each child has at most 120 seconds. This reserves 60 seconds for separate evaluation and 90 for closing within the 900-second total. An enclosing deadline stops later cases and captures: only bounded process cleanup and raw failure facts may be finalized within one closing reserve; alarms at setup, cleanup or persistence boundaries receive the same disposition. A second alarm ends finalization without another reserve. The deadline then propagates and the run remains unsealed. Cleanup PermissionError and other failures are retained without claiming successful cleanup; later cases remain unstarted. Timer enforcement requires the local POSIX supervisor to remain alive. The separate evaluator tightens its 60-second deadline to the remaining whole-run budget:

```text
python -m epiphysics.navigation_evaluation --run-directory RETAINED_RUN_DIRECTORY --key PRIVATE_SEALED_KEY
```

The evaluator requires the execution seal before opening the key, launches no candidate, reads no ledger, and writes its own exclusive claim and retained report. Scores remain provisional until final source and budget checks pass. A failed evaluator report preserves its error, null accepted scores and a false budget-success flag; it cannot retain a successful next action. The root caller independently observes the actual evaluator process exit, bounded monotonic/wall duration, streams and cleanup outcome. It captures the exact report as `improvement-input:evidence-navigation-execution:REGISTRATION_EVENT_HASH:evaluation`, then the independently observed `evaluation_execution` outcome, using existing capture guards. A report file is provisional even when it says scored: interrupted successful-looking bytes remain immutable evidence and cannot authorize acceptance without successful external completion. Accepted scores additionally require exact fixed evaluator argv/engine/run-directory, registered runtime/source/key hash, exact report hash and canonical stdout, complete bounded streams, exit zero and no supervisor/cleanup error. No automatic dispatch follows execution or evaluation.

The later `evidence_navigation_check` packet contains the six original base inputs, every captured execution role prefixed with `execution:`, and the `evaluation` and `evaluation_execution` observations. The retained-only adapter recomputes scores, checks prospective capture chronology and source/input identities, and uses the existing atomic controller completion/queue path. Generic assessments cannot consume these navigation steps. Existing ledger-prefix limits are separate from the 4 MiB study-evidence limit.

Both evaluation capture and final acceptance must occur within 900 seconds of execution start and within 90 seconds of evaluator end. After all completion revalidation, the existing ledger lock guards a final clock/deadline check, including the original monotonic duration. Late capture produces a negative timing result with descriptive scores retained. Late final completion produces a durable execution-contract failure, retains the prior report observation and first attempts, and queues repair without an accepted score or comparison successor. It does not authorize another attempt.

Strict completion is exact agreement with one reviewed answer alternative. Valid additional metadata can be **unpermitted by the key** without being false; reference integrity and target labels are checked separately. Denominators remain six overall, five for directed relationships and two per family, including failures and unknowns. Results describe these six selected textual tasks only. Human comprehension, browser usability, graph benefit and general accuracy remain unmeasured. No paid/model/network calls are part of this protocol.

Owned validation:

```text
PYTHONPATH=engine:engine/tests python -m unittest test_navigation_contracts test_navigation_runner test_navigation_evaluation test_navigation_assessment test_navigation_controller -v
```
