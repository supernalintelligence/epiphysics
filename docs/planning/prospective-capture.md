---
title: "Local first-attempt producer capture"
description: "A fixed leaf-worker capture adapter with independent byte, retention, exit and timing evidence."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

`prospective_capture.capture_first_delivery` executes the frozen line-index
producer once within one local ledger/instance/channel authority. It uses the
existing `Ledger.append(..., exclusive=True)` transaction. Its first claim key
depends only on instance and channel, so changing the source, acceptance
reference, question, timing or output directory cannot create another first
attempt. A failed, interrupted or incompletely published attempt keeps that
claim. Inspection is allowed; replay is refused.

This is unregistered capture evidence. Supplied declaration/acceptance hashes and
times are references, not verified registration or actor authentication. The
function never selects public documents, registers a study, checks quality,
resolves obligations, mutates an improvement queue, runs a model or schedules
itself. `quality` and `obligation_outcome` remain null and
`continuation_allowed` remains false.

## Fixed input and execution boundary

The call accepts an exact built-in source byte string, an exact binding map, the
current Python interpreter's path/hash/version, a new channel directory and five
timing fields. The timing fields are `not_before`, `latest_start`, `artifact_due`,
`wall_seconds` and `cleanup_seconds`. Actual execution is limited to 120 seconds
and cleanup to five seconds; shorter invented test limits do not revise pilot
policy. The source is bounded at 8,192 bytes. Selection eligibility is separate.

Preflight verifies source identity, the accepted producer's fixed hash, worker
bytes, runtime bytes/version, the frozen public schema hash, directory state,
start window and SQLite FULL durability. It refuses an active transaction or a
read-only ledger. The parent temporarily uses a zero SQLite busy timeout so a
contending first claim fails instead of waiting through its launch window.
The fixed-purpose timeout context installs restoration protection before changing
that setting, publishes the restored value before unmasking, and permits bounded
retirement admission retry without arming a timer. Original connection settings
are restored after supported cancellation as well as ordinary completion.

The caller must have a single thread, unblocked/nonpending SIGALRM and SIGINT,
no existing alarm timer, the standard Python KeyboardInterrupt handler, default
unblocked SIGCHLD handling, and valid standard descriptors
0, 1 and 2. A bounded, read-only `/dev/fd` inventory rejects unexpected inheritable
descriptors. It inspects only this process and neither reads descriptor contents
nor closes another owner's descriptors. These are trusted caller assumptions,
not protection against a hostile process mutating its own state concurrently.

The child receives retained raw source stdin and the obligation/schema binding.
The frozen worker reads and verifies the copied producer, then executes those
already-read bytes. The public entry offers no command, import or candidate-code
argument. The trusted fixed worker is a leaf process with no network/model call
or child creation. The parent signals only the exact child PID it owns. It does
not scan processes, terminate unrelated work or establish descendant isolation.
This is not a hostile-code containment boundary.

The native `posix_spawn` call uses explicit source/stdout/stderr descriptor
duplication followed by closing its owned extra ends. The worker has an absolute
path; the parent never changes process-wide working directory. SIGALRM and SIGINT
are masked around native spawn and publication of its returned PID into preallocated
parent state. The prior mask is restored immediately, and the child receives that
intended original mask. A pending alarm therefore reaches cleanup with the child
identity already recorded. This contains no Python constructor or exec-pipe wait.
A kernel spawn that never returns remains an unestablished time bound; this code
does not label it a deadline guarantee. KeyboardInterrupt propagates after owned
cleanup; it is never converted into an ordinary successful return.

One private raw-descriptor owner covers pipe, source, output, receipt and directory
handles. Acquisition publishes ownership before unmasking. Close records its
outcome before retiring ownership. A failed native close is uncertain and the
numeric descriptor is never blindly retried. The final sweep closes only known
owned descriptors, performs no flush/fsync or buffered destructor writes, and
then propagates supported cancellation. A cancellation before close begins can
receive one further bounded attempt while ownership is still known. Repeated
forced interruptions or nonreturning native calls remain unresolved.

Alarm-handler installation and retirement use the same short signal handoff,
with restoration protection installed before unmasking. Retirement disables the
owned timer, consumes an observed pending owned alarm before restoring the
caller's handler, and never arms a replacement timer. The pending alarm remains
CaptureDeadline evidence; when KeyboardInterrupt takes priority, its
`capture_deadline` attribute retains that evidence. Only exceptions actually
escaping each owned body become its cancellation state. An exception already
handled by the caller is neither rethrown nor annotated. The code does not infer
local failure from ambient thread exception state; actual Python 3.10 execution
remains unverified.

## Evidence that stays separate

Stdout has an independent 65,536-byte cap and stderr a 16,384-byte cap. Reads retain
bounded raw prefixes, observed byte-count lower bounds, EOF observations, exact
retained hashes and a full observed-byte hash only when EOF and the size bound
permit it. Stderr never becomes part of the artifact. EOF does not establish
durability, successful receipt publication, reaping, content quality or an
obligation outcome.

First and last byte timestamps are parent read observations, not producer emission
times. Complete-file retention is observed only after EOF, flush, file fsync and
directory fsync. Later cleanup does not replace that earlier observation. A saved
file is reread and compared before its retention verification is recorded. Failed
or missing retention remains explicit. A complete malformed nonempty stream is
still complete submitted bytes; zero-byte closure and an incomplete stream have
different evidence. No absence or quality judgment is inferred here.

Child exit code, reaping, termination reason and cleanup errors remain independent
fields. In particular, nonzero exit after complete output does not imply bad
artifact quality. Uncertain reaping cannot be treated as confirmed absence.
Only direct `waitpid` status for the owned PID establishes an observed exit. The
PID/status or unavailable-status condition reaches parent state before unmasking
cancellation. ECHILD is unknown status/ownership, never a synthetic zero exit, and
prevents further signals to that PID. Raw wait status remains distinct from the
decoded return code.
The parent uses a main-thread POSIX alarm and bounded child waits, with one
cleanup/persistence reserve. Normal completion and supported caller interruption
enter that reserve instead of leaving persistence under unused execution time.
An already-expired reserve cannot be restarted. A second alarm escapes through
the close-only sweep without retrying execution or persistence. A first execution
deadline or caller interrupt arriving at cleanup admission or during unfinished
cleanup resumes only that cleanup, within the same reserve. At most one of each
transition is supported; a remembered KeyboardInterrupt keeps priority through
the final close-only sweep. An existing alarm is
refused and its handler/timer remain unchanged. Host death, uninterruptible kernel
work or lost supervision can leave only partial evidence; no external lifecycle
guarantee is claimed.

The receipt file is written exclusively and fsynced before a terminal ledger
record references its exact hash. The terminal event's timestamp precedes its
commit, so it is not described as post-commit publication time. The returned
`publication_observed` is sampled after that commit returns. A future consumer
must retain that returned observation separately; reading ledger status alone
cannot establish timely publication. Lost return delivery leaves this distinction
unresolved and does not authorize another producer attempt.

Every captured clock sample compares UTC elapsed time with monotonic elapsed
time, including middle reads and EOF. A constant-size accumulator keeps a sticky
failure flag, first violation and count. Differences greater than one second make
the interval unverified, including an intermediate jump that later returns.
Publication at the supplied artifact
deadline is inclusive; post-deadline persistence is reported late. These are
local clock-consistency observations, not externally witnessed timestamps.

## Integration and remaining work

The adapter reuses the ledger's exclusive transaction and append-only event
implementation. It does not change historical dispatcher, navigation, shared-work
or outcome code. The existing assessment dispatcher merges output streams and
does not supply these artifact facts; the historical navigation runner is coupled
to its original contract. No new queue, ledger implementation or general
controller is introduced.

Prospective use still requires verified registration/acceptance binding, frozen
runtime dependencies, launch admission, a surviving monitor, an independently
authored outcome resolver and independent quality evidence. This component does
not certify monitoring through a future deadline. A caller must stop on uncertain
ownership, clock or cleanup evidence; this function never authorizes subsequent
work. The [implementation record](runs/2026-11-27-prospective-capture.md) separates
real fixed-worker calls from fake-process fault controls.


## R6 ownership repair under review

The preceding R5 controls did not cover the first instruction of finalizer
admission. Independent review demonstrated leaked caller signal/timeout state
there, plus a real SQLite transaction begun before the existing Ledger assigned
its Python ownership flag. Those failures remain retained; this repair does not
change the shared Ledger or its historical users.

The private fixed-purpose ownership call installs four enclosing retirement
guards before invoking an acquiring body. Retirement state is allocated before
acquisition. An interruption at an inner cleanup entry reaches an already
installed outer guard; only unfinished owned work is resumed. Four levels allow
three supported deliveries (one SIGINT and the two owned alarm transitions) to
interrupt cleanup admission, leaving a final guard. This finite argument is not
exhaustive asynchronous safety: repeated forced interruptions, interpreter/host
failure and a nonreturning native operation remain limitations. Callback bodies
and child waiting are not run under a blanket mask. Known raw descriptors use
the same guard, while the fixed two-stream readiness check uses SelectSelector,
which owns no extra native selector descriptor.

Only caught escaping exceptions count. If cancellation interrupts the recording
of an earlier exception, bounded inspection follows at most four context links
and sixteen traceback frames per link; a context is eligible only if it escaped
this exact current ownership frame. Earlier ambient caller exception objects are
neither adopted nor modified. The first owned KeyboardInterrupt keeps priority;
observed pending deadlines remain evidence. No reserve or producer work restarts.

The local append wrapper requires the identical independent connection, no open
transaction, no active append, and no atomic group before entry. In the trusted
single-threaded contract, the caller and its clock callback must not mutate or
reenter Ledger/connection state. These observed idle baselines justify recovering
an append flag and rolling back a transaction still open after that call. A
completed commit has no open transaction to roll back: committed claim or terminal
records remain, even if cancellation prevents return delivery. This is local
adapter recovery, not a general transaction repair or proof of global firstness.


## R7 final propagation repair under review

R6 review retained two counterexamples after resource retirement: an owned final
alarm replaced the already-recorded first KeyboardInterrupt during final dispatch,
and a nonfinal deadline omitted known close uncertainty from the returned receipt.
R7 preserves the four existing resource guards. One explicit private record is
passed through this fixed call's helpers; there is no global cancellation state,
new controller or replacement SIGINT handler. It remembers evidence separately
from each helper's locally pending exception. A normally completing cleanup
helper therefore does not rethrow an already handled nonfinal deadline or an
interrupt remembered for its enclosing owner.

An owned alarm records its deadline and selects the first actually caught local
KeyboardInterrupt when present, including after the owner's except block ends.
If an alarm arrives before exception bookkeeping, recovery inspects at most
sixteen live frames, four context links and sixteen traceback frames per link.
Both the exact current per-call record and actual live `_owned` frame must match.
An ambient earlier caller exception or an exception handled only inside a callback
has no qualifying owner-frame traceback and is excluded. Final alarm state still
selects close-only retirement. No timer reserve is renewed.

Final selection and annotation use a short bounded signal/data handoff, with no
filesystem, SQLite, wait or user callback inside it. Exception metadata is written
to the actual BaseException dictionary, without invoking a subclass attribute
hook. Close uncertainty is recorded before native-FD ownership is retired and
propagates with either CaptureDeadline or KeyboardInterrupt. Both the returned
receipt's `close_errors` and exception `capture_close_errors` retain at most
sixteen distinct generated descriptions. Equal descriptions are deduplicated;
they are evidence categories, not an event count. A sticky corresponding
`close_errors_truncated` flag reports an exceeded bound; it is not a dropped-event
count. Uncertain numeric descriptors are never blindly retried. Ordinary receipt
errors remain separately bounded. These are local evidence semantics, not an
assertion that an injected post-close fault is an actual kernel close failure.


## R8 pending-alarm observation under review

When cleanup admission positively observes a pending first SIGALRM and native
sigwait consumes it, the same short existing signal handoff now records the
nonfinal deadline before unmasking. It records `cleanup_admission` as the actual
observation phase, plus one bounded first pending-alarm snapshot (phase and final
flag only). No observation time is invented. An interrupted call therefore keeps
this evidence even when it cannot publish a receipt. Ordinary cleanup still does
not throw merely because the shared record remembers the consumed deadline.

The latest deadline phase is distinct from the first pending observation. A later
actual final alarm is `owned_alarm`, with `final=true`, while its annotation keeps
the earlier `cleanup_admission`, `final=false` snapshot. Pending consumption at
handler retirement is `signal_retirement`. The snapshot is copied into exception
metadata, remains constant-size and is not a log of all observations. There is
still exactly one cleanup reserve and no additional ownership guard or retry.
