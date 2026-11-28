---
title: "C23: first-attempt producer capture"
description: "Invented execution controls for local exclusive claims and fixed leaf-worker capture."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

This packet adds the [local capture adapter](../prospective-capture.md), a fixed
producer worker and focused controls. The accepted producer/checker and all
historical measurement code/queues remain unchanged. Root-owned DAILY_LOOP/TODO
status changes accompany the complete reviewed diff.

Before the first control execution, source, tests, literal expectations and
runtime/dependency identities are frozen under the private
`.supernal-local/prospective-capture-v1/` evidence directory. Every actual control
attempt and failure remains retained under its original identity. A repeated
invocation cannot reuse the original retained directory.

The small literal source is `leaf\ncapture\n`, with fixed byte slices `[0,5)` and
`[5,13)`. Expected artifact fields and hashes are computed from those explicit
slices, without invoking the producer or quality checker. Empty bytes and 700 LF
bytes are deliberately nonselected boundary inputs. Real calls execute only the
frozen leaf producer. Separate fake-process controls use ready regular files and
explicit wait/kill faults; they do not establish real pipe readiness, signal
delivery or producer behavior.

The control groups cover exact bytes, empty-source output, expected producer
capacity refusal, duplicate first-attempt claims despite changed binding/path,
preflight and path refusal, ledger contention, separate streams, exact caps and
overflow, exit/quality separation, closed-pipe waits, uncertain cleanup, spawn
failure, retention corruption, durable time preservation, clock jumps, publication
boundaries and lost terminal receipt. Failure facts do not become quality=false
or obligation outcomes.

## First execution

The first frozen cohort passed all 25 tests. It made five real fixed-worker
invocations: three complete artifact captures, one expected producer-capacity
refusal and one deliberately interrupted parent capture. That interruption
retained an owned reaped-child observation and incomplete output evidence; it
does not pretend to have drained the producer's original stdout.

Seventeen separately labelled fake-process invocations exercised classification
and injected faults, including an attempted fake spawn that raised before a fake
process existed. Their outputs and timestamps are controls, not producer results.
The exact/late publication pair uses fresh channels. Preflight/path/lock/alarm
refusals did not launch a worker or consume a first claim.

The measured outer control subprocess took 1.144132416 seconds under its 30-second
timeout, within the 180-second builder control allowance. The test runner's
0.990-second report is nested and is not added to that measurement. Whole-agent
time/cost is unknown. The process exited zero, with no test failures or skips.
Original frozen file pins remained unchanged. The actual receipt is
`builder-v1/first-process-receipt.json` in the private evidence directory.

The fake second-alarm control deliberately exhausted the cleanup reserve. It
escaped with the first claim and no terminal receipt, as required, and emitted
four `ResourceWarning` messages for file objects left open when cleanup was
interrupted. Those warnings and original files remain retained. This establishes
bounded escape with unresolved cleanup, not clean resource retirement in that
failure. No unchanged control was rerun to obtain a cleaner report.

## Independent findings and R1 identity

The two independent reviews rejected that first implementation. They identified
three unique defects: an alarm could interrupt `Popen` after a child existed but
before the parent received its handle; middle-read/EOF clock observations could
be discarded; and CPython's unavailable-wait-status fallback could become a
claimed zero exit and reaped child. Duplicate findings across reviewers count once.

The unguided review ran three fresh controls once: one passed and two failed their
predeclared safety expectations. It made three real fixed-worker invocations in
0.526030166 seconds. Its harness retained and reaped the child whose handle was
lost by the adapter. The safety review separately ran four fake-only controls;
all four failed their safety expectations, with zero unexpected harness errors,
zero worker children and zero OS signals. Its outer control subprocess took
0.304422959 seconds. Each reviewer retained its original outputs and verified all
585 original review-freeze records unchanged. Neither reran the builder cohort.

R1 replaces only this new adapter's private launch/wait transport with fixed
`posix_spawn` ownership handoff and direct owned-PID wait status. It adds cumulative
clock observation, preserving first violation/count with bounded memory. The
accepted producer/checker, worker bytes, ledger implementation and historical
queues remain unchanged. Original source snapshots, passing builder results,
ResourceWarnings and failed independent expectations remain immutable evidence.

Fresh R1 controls use `invented-c23-r1` and distinct directories. Real controls
will exercise exact fixed output and pending cancellation at spawn/PID and
wait/status handoffs. Fake-only controls separately exercise discarded-clock
boundaries, unavailable status, spawn failure and stderr overflow; conflicting
signal/descriptor preflight must refuse before any claim. The literal new source
is `R1 leaf\nnew capture\n`, with declared slices `[0,8)` and `[8,20)`. No original
cohort is replayed. Only the separately named R1 controls will run under the new
source/control freeze; adapting older test helpers is not a claim that those
older controls were rerun or passed against R1.

The first R1 execution passed all ten freshly named controls, with three real
fixed-worker invocations and six labelled fake-process invocations. The
signal/descriptor preflight control refused without creating a claim or child.
The outer subprocess took 0.921527708 seconds with a 30-second timeout, zero
failures/skips and no emitted warnings. The runner's 0.648-second value is nested,
not additional cost. All R1 pre-execution file pins stayed unchanged.

The native spawn control delivered a real alarm to its own parent while the
handoff mask was active, then verified that the returned child PID was retained
and reaped. The native wait control delivered another real parent alarm after
`waitpid` returned but before the status handoff, then verified that actual zero
status survived cancellation. Fake ECHILD never became zero or a successful
reaping observation and caused no fake kill. Clock verification stayed false after
middle-read, EOF and receipt violations, even when later samples realigned. Exact new-source output
and changed-binding/directory refusal retained the firstness boundary.

The original builder subprocess and R1 subprocess total 2.065660124 seconds. The
separately measured original freeze/hash observation adds 0.325403083 seconds;
these are accounted program intervals, not whole-agent costs. Independent review
time is attributed to its own workers. Original first-cohort results/warnings and
both independent failed cohorts remain unchanged; they are not replaced by R1.

R1 independent rechecks remain pending at this evidence checkpoint. This is
neither pilot registration nor a real delivery, prediction, causal comparison,
business result or authority increase.

## R1 rechecks and R2 preparation

Both R1 rechecks completed and R1 was not accepted. The clock and unavailable-status
defects were closed, and SIGALRM child publication was repaired. The safety reviewer
showed that default SIGINT still exposed the broader child-ownership handoff.
Both reviewers found a separate descriptor-ownership defect: interruption during
pipe acquisition or close could lose handles. These are distinct from the
original disclosed second-alarm warnings; first alarms with reserve remaining
were sufficient to leak descriptors.

The unguided R1 recheck ran eight fresh controls once (six passed, two failed),
with five real fixed workers, one fake worker and two no-worker controls, in
0.700837833 seconds. The safety R1 recheck ran seven fake-native controls once
(five passed, two failed), with no real worker children or OS signals, in
0.656518916 seconds. Both verified all 967 supplied R1 freeze records unchanged.
Each fixture identified and retired only its own leaked descriptors after
recording the failure. All original files and failed expectations remain retained.

R2 extends the small ownership/status critical sections to SIGALRM and SIGINT,
requires the supported initial signal state, and uses one raw-descriptor owner
across creation and retirement. It removes buffered writers, records uncertain
native close without numeric-FD retry, and ensures a close-only final sweep before
cancellation propagates. Normal completion or caller interruption enters one
cleanup/persistence reserve. That reserve cannot be refreshed after expiration.
Native syscalls that never return remain an explicitly unestablished bound.

Fresh R2 controls are prepared with the literal source
`R2 owned\nnew evidence\n` and slices `[0,9)` and `[9,22)`. They target real
SIGINT/PID and status handoffs, real pipe/file/directory ownership alarms,
uncertain native close with a reused numeric descriptor, final receipt interruption,
one short cleanup reserve, and current byte/clock/status behavior. Fake faults
remain separately labelled. Existing reusable tests stay in source with adapted
transport helpers; this does not claim an original cohort was rerun.

R2 first execution and independent reviews are pending at this preparation
checkpoint. Earlier versions and every first outcome remain immutable.

The first R2 execution then ran thirteen fresh controls: twelve passed and one
failed, with eight real fixed-worker invocations and four fake invocations. Its
outer subprocess took 1.656980125 seconds, with unchanged frozen file pins. The
normal-cleanup-reserve control did not raise its expected deadline because its
delay hook inspected the immediate mock wrapper frame instead of the intended
cleanup frame. The corresponding SIGINT control established propagation, but
did not establish delayed-cleanup timing. Neither result is silently counted as
that missing coverage.

R2b corrects only those test hooks to inspect a bounded stack and adds two fresh
controls with new identities and `Reserve follow-up\nfresh bytes\n` input. They
must positively retain the fired hook and remaining reserve, verify the expected
deadline/KeyboardInterrupt propagation, and track actual owned resource retirement.
Production source remains byte-identical to R2. The original thirteen-control
result stays immutable; the other eleven controls are not replayed. R2b execution
is pending at this test-correction checkpoint.

The two fresh R2b controls passed. Each retained exactly one fired cleanup-delay
hook, with 0.049916 and 0.042396 seconds left in its 0.05-second reserve. The normal
case propagated final `CaptureDeadline` after 0.142995042 seconds; the caller
interrupt case propagated `KeyboardInterrupt` after 0.088259125 seconds. Actual
owned wait statuses were zero and nine respectively. The controls observed 24 and
20 owned-descriptor retirements, no remaining owned descriptors, and no harness
child recovery. These nested intervals are not added to the outer process cost.

R2b made two real fixed-worker invocations and no fake invocation. Its complete
outer subprocess took 2.792435667 seconds under the 30-second cap, with no emitted
warnings and unchanged pre-execution pins. The production capture source stayed
at SHA256 `cdd871ecdfb6988fde9764c75c359470bb690c9bbc7367bb311e47d6fe7a400b`.
The four builder control subprocesses together account for 6.515075916 seconds;
freeze/hash observations and independent reviewer controls remain separately
attributed. Whole-agent time/cost is unknown.

The complete R2 patch, corrected reusable tests, and all original/repair evidence
now await both independent rechecks. No original cohort was rerun, no earlier
failure was removed, and no production source changed for the test-only R2b fix.

## R2 rechecks and R3 preparation

Both independent R2 rechecks completed and R2 was not accepted. Earlier native
PID/status and descriptor handoff defects were closed. Two requirement classes
remain: resume unfinished owned cleanup after a first cancellation at its
admission or during child cleanup, and preserve caller-interruption priority if
a later final deadline interrupts the close-only sweep.

The unguided reviewer ran eight fresh controls: seven passed and one failed,
with six real workers, one fake invocation and one no-worker control, in
0.632162958 seconds. A first SIGINT inside cleanup left an actual, exactly owned
stopped child unreaped despite available reserve; the fixture recorded and
recovered that same child with SIGKILL and wait. No descriptor recovery was needed.
The safety reviewer ran six fresh controls: four passed and two failed, with one
real worker, four fake invocations and one no-worker control, in 0.684428166 seconds.
An actual first timer at cleanup admission skipped fake child cleanup, and an
actual parent SIGINT during cleanup was replaced by a final deadline from a
labelled returning-close delay. There were no harness errors or resource recoveries
in that review. Both reviewers verified all 1,649 supplied pins unchanged.

R3 changes only the new adapter's cleanup-transition block. At most one first
deadline and one supported caller interruption can resume unfinished cleanup,
within the already-started reserve and retained owner state. The producer is not
reexecuted, the timer and cleanup deadline do not restart, unavailable wait status
stays unknown, and final expiration permits only the known-resource close sweep.
The first KeyboardInterrupt remains the propagated exception even if final
expiration interrupts that sweep.

Three fresh R3 controls use `R3 cleanup\nremaining work\n` source with new
instance/channel directories. Two real fixed workers are stopped only by their
own fixture to expose the first cleanup SIGINT and first admission deadline;
their exact wait/kill/reap and descriptor facts must remain recorded. A separate
fake worker exercises cleanup SIGINT followed by the final close deadline, with
positive hook observations and a zero-later-writes expectation. Every expectation
and source/runtime identity will freeze before first execution. Earlier failed
cohorts remain immutable and are not replayed.

After those fresh controls, one separately labelled repeated software regression
of the reusable capture test module is authorized in a wholly new retained root.
It is not new independent coverage, original cohort execution, or a research
assessment. Fresh R3 controls, that regression and both rechecks are pending at
this preparation checkpoint.

The first R3 execution ran three controls in 0.654336417 seconds: both real-worker
controls passed, while the fake exception-priority control had a harness error.
The two real children were stopped and reaped only by their owning fixture/adapter,
with no harness recovery or remaining tracked descriptors. The fake control tried
to send its intended parent SIGINT through the fake child-signal replacement,
which refused that target; a subsequent final deadline surfaced instead. That
original error is retained and supplies no caller-interruption priority coverage.

R3b is a test-only correction using the captured native signal function and a
fresh `Priority follow-up\nkept interruption\n` source/instance. It must record
the exact self-signal, final pending alarm, propagated KeyboardInterrupt and owned
resource retirement. Production source remains byte-identical to the first R3
execution. Only the new R3b control will run; the original three are not replayed
as fresh evidence. The separately authorized repeated software regression is
still pending at this checkpoint.

The fresh R3b control passed in 0.239370791 seconds with one fake invocation and
no real worker. Its retained hook records show an exact self SIGINT, a later final
alarm pending during close, propagated KeyboardInterrupt, no later writes and
no remaining owned descriptors. All frozen pins remained unchanged. This closes
the missing builder-control coverage without replacing the original harness error.
The six builder control subprocesses so far total 7.408783124 seconds; the single
authorized repeated software regression will be attributed separately.

The one repeated software regression passed all 54 reusable test methods in
8.081653791 seconds, under its 30-second subprocess cap. It made 20 real fixed-worker
and 29 fake invocations, with no emitted warnings, in the exclusive
`repeated-regression-r3` evidence directory. Every method used its new local ledger
and output directory. This repeated software coverage does not replace any first
cohort's outcome or become new independent evidence. All 177 source/runtime pins
and 2,037 previously retained private evidence files remained unchanged.

In the first R3 real controls, the admission hook observed 0.088334 seconds left
on the execution timer; the cleanup SIGINT hook observed 0.499974 seconds left
in the original cleanup reserve. Both exactly owned children were reaped with
raw wait status nine. Their 26 and 22 tracked descriptor lifetimes retired without
harness recovery. R3b recorded 0.059986 seconds left at its self SIGINT and
0.059848 seconds at its close-delay hook, then the final alarm pending; all 27
tracked descriptor lifetimes retired, with no later write and KeyboardInterrupt
propagated. These nested intervals are not additional elapsed cost.

The seven builder control/regression subprocesses together account for
15.490436915 seconds. Freeze/hash intervals and independent reviewer programs are
separately attributed; whole-agent time/cost remains unknown. Production capture
and reusable test bytes are now frozen for both independent R3 rechecks. No
original first-attempt directory, queue, registration or outcome was mutated.

## R3 rechecks and R4 preparation

The unguided R3 recheck passed four fresh controls (three real workers, one fake)
in 0.244052292 seconds, closing the cleanup-resumption finding. The safety recheck
ran five fake controls in 0.644876625 seconds: four passed and one failed. Both
deadline/SIGINT orderings and exception priority passed, but a first SIGINT after
timer disarm left the capture's handler installed. The fixture recorded that
mismatch before restoring its own original handler. No child or descriptor
recovery was needed. Both reviewers verified all 2,889 supplied pins unchanged.

The safety review also confirmed a static compatibility defect: package metadata
declares Python 3.10 support, but cleanup used the 3.11-only `sys.exception` API.
No Python 3.10 interpreter was run. These two findings remain retained in the
`independent-critic-r3` and `independent-safety-r3` reports; R3 was not accepted.

R4 replaces that API with `sys.exc_info()[1]` and protects alarm-handler
installation/retirement under the existing short signal handoff. Restoration is
installed before unmasking, can retry bounded admission, and never rearms a timer.
An observed pending owned alarm is consumed before restoring the caller handler;
its deadline evidence is preserved even when KeyboardInterrupt takes priority.
The producer, ledger, byte capture, resource ownership and cleanup-reserve policy
remain unchanged.

Six fresh controls use `R4 signal\nretirement\n` bytes and new local instances:
installation SIGINT without launch, three real-worker retirement signal cases,
ordinary literal output, and a real-worker compatibility simulation with only the
newer exception API removed. That simulation is explicitly not Python 3.10
execution. Positive signal-mask, pending-alarm, prior-handler, deadline-evidence
and owned-resource observations freeze before execution. A further focused
reusable-module regression is authorized afterward in a new root, labelled
repeated software coverage. Both executions and rechecks are pending here.

The first R4 execution passed all six controls in 0.287045875 seconds: five real
fixed workers, no fake worker, and one installation interruption with no claim or
launch. Positive hooks observed both signals masked, restored original handlers,
disabled timers and exact masks. Pending owned alarms did not call the restored
caller handler; the combined interruption retained deadline evidence on the
propagated KeyboardInterrupt. Owned resources retired without fixture recovery.
The compatibility simulation and ordinary literal output passed on Python 3.12.9;
Python 3.10 execution remains unverified. All 177 frozen file pins stayed unchanged,
with no emitted warnings. The new repeated regression remains pending.

The authorized R4 repeated software regression then passed all 60 reusable test
methods in 8.541253709 seconds, with 25 real workers and 29 fake invocations. It
used only the new `repeated-regression-r4` root, emitted no warnings, and left
all 177 source/runtime pins and 3,055 previously retained evidence files unchanged.
It is repeated coverage, not a new independent cohort or study result. The nine
builder control/regression subprocesses total 24.318736499 seconds, excluding
separately recorded freeze/hash intervals and reviewer programs. Whole-agent
cost/time remains unknown. Source and tests are frozen for the R4 rechecks.

## R4 rechecks and R5 preparation

R4 was not accepted. The unguided reviewer ran three fresh real workers on an
independently pinned Python 3.14.8 runtime: one passed and two failed, in
0.258036417 seconds. Already-handled caller exceptions were mistaken for new
capture cancellation: prior CaptureDeadline was rethrown after terminal
publication, and prior KeyboardInterrupt prevented receipt publication. No new
signal was sent, and no resource recovery was needed. This runtime is distinct
from the builder's Python 3.12.9 and establishes no Python 3.10 execution.

The safety reviewer ran five fresh controls (three fake workers, two no-worker)
on Python 3.12.9: four passed and one failed, in 0.199793500 seconds. A first
SIGINT after actual SQLite timeout mutation left the caller's setting at zero
instead of 4,793 ms, before any claim or worker. The fixture recorded and restored
its own setting. Both reviews verified all 3,959 supplied pins unchanged; earlier
signal/API findings closed. Original failures remain retained in their R4 reports.

R5 records only exceptions caught escaping each owned body, with no ambient
exception inspection. Existing caller exception objects remain untouched. A
fixed-purpose context owns the temporary SQLite busy timeout, protecting its
acquisition and bounded restoration before unmasking, without a new timer, ledger
implementation or event policy. Signal/child/FD/clock and cleanup-reserve behavior
otherwise remain unchanged.

Seven fresh controls use `R5 caller\nowned attempt\n` bytes and new local
identities: successful captures inside three prior exception handlers, a genuine
new SIGINT inside an unrelated handler, and real SQLite timeout installation,
retirement and retirement-admission interruptions. They freeze literal artifact,
unchanged caller-object/state, positive hook and exact owned-resource expectations
before first execution. A focused repeated-module regression is separately
authorized afterward in a new retained root. Both batches and rechecks are pending.

The first R5 execution passed all seven controls in 0.286144083 seconds: six real
workers, no fake worker, and one no-worker timeout-installation case. Captures
inside all three prior handlers returned exact artifacts and both events while
preserving caller exception attributes, traceback/context/cause and arguments.
The genuine new SIGINT remained a distinct propagated interruption. All timeout
controls restored exactly 5,371 ms; the retirement-admission case completed on
attempt two. No child, descriptor or timeout fixture recovery was needed. All
177 frozen pins stayed unchanged, with no warnings. The authorized repeated
software regression is still pending at this checkpoint.

The authorized R5 repeated software regression passed all 67 methods in
8.645530666 seconds, with 31 real fixed workers and 29 fake invocations. It used
only the new `repeated-regression-r5` root. All 177 source/runtime pins and 4,116
previously retained evidence files remained unchanged, with no warnings. This is
repeated software coverage; the original R4 failures remain the first outcomes of
their own cohorts. The eleven builder control/regression subprocesses now total
33.250411248 seconds, with freeze/hash intervals and independent reviewer work
separately attributed. Whole-agent time/cost remains unknown. The complete R5
patch and evidence are frozen for root-supervised independent rechecks; the
builder returns idle without accepting, committing or landing the change.


## R6 pre-execution plan

Root adjudicated two R5 defect classes: cleanup admission before a finalizer's
own guard, and Ledger append acquisition before its transaction/flag cleanup.
The R5 critic and safety records stay unchanged in `independent-critic-r5` and
`independent-safety-r5`; root's `adjudication-r5.json` records the decision.

R6 replaces context-manager lifecycle admission with one private fixed ownership
call and preinstalled outer retirement guards. It locally wraps both existing
exclusive appends from an independently verified idle connection, preserving a
committed record when its return is lost. No shared Ledger, worker, producer,
checker, historical queue, pilot binding or original evidence is changed. The
opaque native readiness-selector descriptor is removed by using SelectSelector
for the fixed two streams. Existing reusable fake-readiness and retirement-frame
hooks are adapted to those private implementation changes; their old first
results are not relabelled as rerun.

Twelve fresh controls will be frozen before execution under `builder-r6`:
three real workers with first-instruction cleanup interruption (timer, busy
timeout and capture's owned stopped child); six real-SQLite append controls
(initial/terminal crossed with pre-try flag, native BEGIN, committed-but-lost
return); one ordinary literal worker; and two no-worker real self-signal/owned-FD
controls for all three supported deliveries and interrupted exception recording.
The literal source is `R6 ownership\nlocal first claim\n`, 31 bytes with slices
[0,13) and [13,31). Expectations include exact literal output for the normal
worker, no harness resource recovery, restored timeout/handler/timer/mask, actual
owned wait status, no open transaction/append flag, and unchanged committed
records after lost return. Native self-signals target only the control process.
These are invented software controls, not registered pilot outcomes.

After first outcomes settle, one focused reusable-module regression is authorized
on unchanged source in an exclusive new output/ledger root. It will be labelled
repeated software coverage, preserving all old first-attempt artifacts and all
failures. Python 3.10 execution remains unverified. Builder runtime is Python
3.12.9; the previous independent critic separately used Python 3.14.8.


R6 first execution: all 12 controls passed in 0.347429208 seconds
under the 30-second process cap. Seven fixed workers ran; five controls launched
no worker (three initial-append windows and two direct ownership/signal cases).
No fake worker was used. All 177 pre-execution source/runtime pins stayed
unchanged. No ResourceWarning, child recovery, descriptor recovery, timeout
repair or transaction repair by the fixture was observed.

Each of the three first-retirement-instruction hooks fired on a real SIGINT.
The capture control stopped only its own fixed child, then observed its exact
SIGKILL wait status after adapter cleanup. Initial and terminal flag/BEGIN hooks
left no active transaction or append flag; native-BEGIN controls each observed
one rollback of an active transaction. Native-commit hooks left respectively one
and two committed records, no returned receipt and no rollback of active work.
The three-delivery control observed four retirement admissions and a closed owned
FD; the interrupted-bookkeeping control propagated the identical original local
KeyboardInterrupt object. These are positive observations for these scheduling
hooks, not an exhaustive proof over all interpreter instructions or hosts.


The separately authorized repeated regression ran all 79 reusable methods in a
new `repeated-regression-r6/first-execution` root: 79 passed, 38 real fixed-worker
launches and 29 labelled fake-process calls, 8.691225167 seconds.
All 177 frozen source/runtime pins and all 5,277 pre-existing private
evidence files stayed unchanged. No warnings or failures were observed. This is
repeated software coverage of the changed implementation, not 79 new independent
controls or a replay of any original retained study cohort. Its process receipt
SHA-256 is `d5eee9313d600df9771a25b3bfb7b2ae2a5f2ca0ec18dda6e463db0c81a640d8`.

R6 control and regression subprocess time totals 9.038654375 seconds; cumulative
builder subprocess time is 42.289065623 seconds. Adding the previously measured
4.465441958 seconds of freeze/hash work gives 46.754507581 of the original
180-second execution allowance before the final R6 freeze, whose own elapsed
interval is recorded separately in its manifest. No process exceeded its
30-second cap. Whole-agent elapsed time and cost remain unknown.

Production and test bytes are unchanged after their R6 execution freezes. The
new trace-hook controls use `code.co_qualname` on the pinned Python 3.12.9 runtime;
that test-harness attribute requires Python 3.11 or later. Actual Python 3.10
execution is unverified; the production adapter itself does not depend on
`sys.exception` or `co_qualname`. Neither this coverage nor the finite cleanup
guard argument establishes exhaustive asynchronous safety, native syscall bounds,
descendant isolation or automatic permission to continue. Independent full-boundary
reviews remain pending. All original v1/R1/R2/R2b/R3/R3b/R4/R5 source snapshots,
failed controls, warnings, reviewer counterexamples and adjudications are retained.


## R7 pre-execution plan

Root accepted two R6 final-propagation defects from the independent reports and
`adjudication-r6.json`: close uncertainty omitted under a selected deadline, and
stored interruption priority lost at final dispatch. The original 3-pass/1-fail
critic and 3-pass/1-fail safety cohorts remain immutable. Prior cleanup-entry and
transaction recovery findings passed their fresh reviewed boundaries.

R7 adds an explicit private per-call cancellation/evidence record through the
existing fixed helpers, keeping the four resource guards and public API unchanged.
Alarm selection preserves the first actually caught local interruption, while
local exception selection remains separate from already handled shared evidence.
Short bounded finalization preserves close uncertainty on deadlines/interruption;
receipt close descriptions have their own deduplicated sixteen-entry bound and
sticky truncation flag. An interrupted bookkeeping boundary can recover an
exception only through the exact live owner frame and exact record identity.

Nine fresh controls will freeze before execution under `builder-r7`: native
first alarm followed by an explicitly injected post-close OSError; real-worker
interruption plus final alarm at dispatch; first dispatch SIGINT followed by final
alarm before bookkeeping; composed close uncertainty/interruption/final alarm;
normal literal worker under nested untouched caller exceptions; exclusion of a
callback-only handled interrupt during an actual alarm; seventeen actual owned
FD closes followed by injected uncertainty to exercise deduplication/truncation;
one consumed nonfinal alarm followed by normal cleanup without another reserve;
and close uncertainty observed during final artifact reread retained in the receipt.
The literal source is `R7 propagation\nretained uncertainty\n`, 36 bytes with
slices [0,15) and [15,36). Expectations and exact bytes freeze before the first
execution. Faults after successful native close do not claim real kernel failure.
All native signals target the control's own process. The first/bookkeeping and
recorded-interrupt cases positively record their intended hook, original exception
identity, final-alarm evidence and absence of later writes or fixture recovery.

One separately labelled repeated-module regression is authorized after the fresh
cases settle, with new retained output and Ledger directories. Existing private
signature hooks are adapted to forward the explicit per-call record; no original
first-attempt evidence is rerun or rewritten. Python 3.10 execution remains
unverified; the retained trace harness still requires Python 3.11 or later.


R7 first execution: all 9 fresh controls passed in 0.509229084
seconds under the 30-second process cap. Five fixed workers ran; four controls
used real local signals/FDs/SQLite without a worker. No fake worker was launched.
All 177 pre-execution pins stayed unchanged. No warnings, harness errors or
fixture child/descriptor/state recovery were observed.

Both dispatch hooks positively fired with time left on the original cleanup
reserve; the identical original KeyboardInterrupt reached the caller with final
alarm evidence, including the first-interrupt-before-bookkeeping case. The
composed post-close uncertainty case retained the same interruption and its close
record. No later writes occurred after the final-alarm hook. The first-deadline
receipt and final-reread receipt both retained their known close uncertainty.
Seventeen actual closes followed by labelled injected OSError records retained
sixteen distinct descriptions, flagged truncation and performed no numeric-FD
retry. Ordinary exact literal output under nested caller exceptions and the
callback-only handled-interruption exclusion passed. The consumed first-alarm
control recorded exactly two timer arms: the original execution budget and one
cleanup reserve. These are deterministic controls, not estimates of spontaneous
race frequency or actual kernel-close failure.


The authorized R7 repeated regression ran all 88 reusable methods in a new
`repeated-regression-r7/first-execution` root: 88 passed, 43 real fixed-worker
launches and 29 labelled fake-process calls, 9.204682500 seconds.
All 177 frozen source/runtime pins and all 6,489 earlier private evidence files
stayed unchanged. No warnings, failures or harness errors were observed. This is
repeated software regression, not new independent or study evidence. Its process
receipt SHA-256 is `38186213aa8059844d7d2dfb0b31fefe5b31717d4e370554102e3ce72dfc1b0f`.

R7 fresh and repeated subprocess time totals 9.713911584 seconds. Cumulative
accounted builder execution is 58.987243748 of the original 180-second allowance
before the final R7 freeze; that manifest separately records its own hash/diff
interval. Every control process stayed below 30 seconds. Whole-agent time and
cost remain unknown. Production/test bytes are unchanged after execution freezes;
only these run observations were appended. All v1 through R6 sources, control
failures, warnings, reviewer counterexamples and adjudications remain immutable.

R7 full-boundary independent reviews remain pending. The finite supported signal
delivery argument, native/nonreturning-call and host-failure limitations remain;
there is no descendant isolation or continuation authority. Firstness remains
local to the declared Ledger/instance/channel. Python 3.10 execution remains
unverified, and the deterministic trace harness requires Python 3.11 or later.


## R8 pre-execution plan

Root read both R7 reports and retained their complete evidence. The independent
critic reported no actionable findings (3 fresh passes); guided safety retained
3 passes and 1 failure confirming the builder's pending-alarm concern. Both R6
propagation failures were closed by R7. `adjudication-r7.json` authorizes only the
missing consumed-pending-alarm record update and truthful phase metadata.

R8 records a positively observed and natively consumed first SIGALRM as a
nonfinal `cleanup_admission` deadline inside the existing short handoff. One
bounded first-pending snapshot stays separate from any later `owned_alarm` final
deadline or `signal_retirement` observation. No fabricated timestamps, new guard,
controller, shared Ledger change or renewed reserve is introduced. The existing
reusable pending-retirement expectation is adapted for the explicit snapshot;
its original first execution remains immutable.

Three fresh real fixed-worker controls will freeze under `builder-r8`: paired
normal/interrupted completion after the same actual pending-alarm consumption,
and a later interruption plus actual final self alarm. Each positively records
native sigpending and sigwait observations, exact first interruption identity
where applicable, one execution timer plus one reserve, actual wait status0,
owned-resource retirement, original caller state and unchanged ambient caller
exception. The composed final case records no later write or fsync. No fake
worker or injected kernel-error outcome is planned. Native signals target only
the control process. Literal source is `R8 pending\none reserve\n`, 23 bytes
with slices [0,11) and [11,23); literal expectations and runtime/source identities
freeze before execution. One separately labelled reusable-module regression is
authorized afterward in an exclusive new retained root; all earlier cohorts and
failures remain untouched.


R8 first execution: all 3 fresh controls passed in 0.692977000
seconds under the 30-second process cap. Three actual fixed workers ran, each
observed with raw wait status 0; no fake worker or injected native error was used.
All 177 frozen source/runtime pins stayed unchanged. There were no warnings,
harness errors, resource leaks or fixture recovery.

All three controls positively observed and consumed the self SIGALRM during
masked cleanup admission and recorded exactly two timer arms (execution 3s,
reserve 0.5s). Normal completion retained exact literal output, parent_deadline
and two events without rethrowing shared evidence. The interrupted control
propagated the identical new KeyboardInterrupt with nonfinal cleanup_admission
and pending evidence. The composed final-alarm control retained that same
interruption, latest owned_alarm/final=true and the earlier pending
cleanup_admission/final=false snapshot. Both interrupted cases retained one claim
and no terminal receipt. Caller state and ambient exception objects stayed
unchanged; no writes or fsync followed the final-alarm hook. These are controlled
observations, not a claim of exhaustive asynchronous behavior or natural race
frequency.


The authorized R8 full-module repeated regression remains **90 passed / 1 error**:
91 methods, 46 real fixed-worker launches and 29 labelled fake-process calls,
27.313479292 seconds under the 30-second process cap. All 177 frozen
source/runtime pins and all 7,727 earlier private files stayed unchanged. This
result is not relabelled green. The old
`test_real_parent_alarm_reaps_owned_worker_without_inventing_eof` expected a
returned receipt under 0.15-second execution and 0.5-second cleanup budgets. It
instead received final CaptureDeadline while output-file open for receipt.json
unmasked an alarm. Retained facts show one worker spawn, one committed claim,
empty stdout/stderr and a zero-byte receipt, with no terminal event. That old test
did not instrument actual wait status, descriptor retirement or restored caller
state, so those dispositions remain unknown from that failed run. Host slowdown
is not established as its cause. The API permits a final-deadline return loss;
this fixture required a stronger unconditional receipt outcome.

Root's `r8-regression-design-accepted.json` authorizes one test-only correction,
superseding an unused proposal to increase the cleanup allowance. Production R8
bytes stay identical. The corrected renamed reusable method keeps the original
0.15-second execution and 0.5-second cleanup budgets, uses a positively triggered
first self-alarm immediately after an actual owned spawn/before stream reads, and
retains exact PID/wait/FD/caller-state evidence. Either a returned receipt or
final CaptureDeadline must still demonstrate actual child reaping, exact resource
retirement, original caller state, no invented EOF and zero fixture recovery.
Unknown cleanup fails. A final deadline may follow a terminal commit; any retained
receipt and actual commit are verified without inferring returned publication or
continuation. The distinct literal source is
`R8b alarm\nfirst retained attempt\n`, 33 bytes with slices [0,10), [10,33).

One focused run of only that renamed method will freeze before execution in
`focused-regression-r8b`; the other 90 methods and all original cohorts will not
be replayed. This is a repaired repeated software regression case, not a new
independent control or research result. Its actual branch will be reported; it
does not by itself establish fresh coverage of both possible outcomes.


The single authorized R8b focused repeated regression passed in
0.226952208 seconds, with one actual fixed worker and unchanged
0.15-second execution / 0.5-second cleanup budgets. The actual branch was
`returned_receipt`: the exact owned PID 86694 was reaped with raw status 9, all
26 tracked descriptor lifetimes retired, original caller state restored and
zero fixture recovery. The retained 3,246-byte JSON receipt SHA-256
`aa56f292b0a569bc41db1a1c7406740b81c64503b13e2dd1411bbdfe007e5bcd`
matched the actual terminal commit; no EOF or quality was fabricated. A returned
publication observation existed for this branch, with continuation still false.
The alternative final-deadline branch was not exercised by this focused run.

All 177 frozen source/runtime pins and all 8,699 earlier private evidence files
stayed unchanged. The focused process receipt SHA-256 is
`4ae92c66ac2bca9e8ae2257f574199d845cc215db7b2587d66102446dd415371`.
The original full-module R8 regression is still **90 pass / 1 error**, with receipt
SHA-256 `346e197e47f0130246e8af5fdcbc54b80a60fffdf0d7978018dcf5afb89447e0`.
No other regression method or original first-attempt cohort was rerun. No warning
or harness error occurred in the focused run. Production R8 bytes remained
`3628b87cbe4234b806cae2bef82fd59dab7de3caee66ce797b7d20ca180d306d`
through fresh controls, the failed full regression and the test-only follow-up.

Cumulative accounted builder execution is 88.882184998 of the original
180-second allowance before the final R8 freeze; that manifest separately records
its own diff/hash interval. All three R8/R8b subprocesses stayed under 30 seconds.
Whole-agent time and cost remain unknown. Independent full-boundary reviews are
still required. All previous source snapshots, first outcomes, warnings, failures,
reviewer counterexamples and adjudications remain retained. No pilot, registration,
model/network call, historical queue consumption, commit or landing occurred.
