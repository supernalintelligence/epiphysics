---
title: "Saved prospective artifact compatibility"
description: "A bounded invented-byte connection between the accepted producer and independent content checker."
date: 2026-11-27
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

C22 connects the accepted [pure producer](prospective-producer.md) and
[independent content checker](prospective-quality.md) through actual saved files.
The integration author is neither component's author. Both implementations and
the proposed declaration's `obligation_contract` stay unchanged. The reusable
test is `engine/tests/test_prospective_artifact_roundtrip.py`; it adds no
production entry point, broker, receipt store or generic runner.

## Fixed compatibility question

For each of six fresh invented sources, does one producer call return the exact
canonical artifact independently expected from literal raw-byte partitions, or
the declared capacity refusal? For each returned complete artifact, do its saved,
reread bytes retain that identity and receive the expected independent content
judgment? The six planned cases stay in the denominator: five expected complete
artifacts and one expected refusal. Quality is assessed only for an available,
verified complete artifact; refusal never becomes `quality=false`.

Before any component call, the test writes every planned source, every complete
expected artifact, literal slice bytes/offsets/hashes, exact expected fields,
compatibility outcomes and control expectations. Expected slices do not use
either implementation or a splitting helper. The repeated-LF capacity case uses
the explicit numeric family `[i,i+1)` for `0 <= i < 700`, each containing one LF.
Standard-library JSON and SHA256 primitives are shared dependencies.

Two sources meet the declared 256–8,192-byte and at-most-128-line bounds; they are
still invented data with no selected-public-source status. Short multibyte,
empty and adjacent-LF examples are boundary-only. The 700-byte/700-line source
fits source processing capacity but exceeds the selection line bound; its
expected canonical artifact is 69,920 bytes, above the 65,536-byte artifact cap.
The retained expected artifact is a hypothetical expectation, not producer output.

## Save, verify, then check

Each source is saved exclusively, reread and bound to its frozen size and SHA256.
The producer is called once per case. A complete return is saved exclusively;
its recorded length/hash bind the actual returned bytes. The test independently
reads the saved source and output, verifies both bindings, then supplies only
those reread bytes to `check_line_index`. The typed `QualityResult` and exact
source/artifact identities are retained. Expected artifact bytes are compared
with actual saved output after the content check; they are never substituted for
the producer output sent to the checker.

An explicit refusal is retained with its class, exact message bytes and hash;
there is no artifact and no checker call. Unexpected errors remain test failures.
Original outputs are not regenerated to repair an outcome. A separate read-only
audit hashes all original saved files with an external SHA256 command, checks
their bindings and compares them to the pre-execution expectations. It invokes
neither component.

The focused controls distinguish retention from content:

- Missing source/output files, wrong source/output bindings, a same-length
  corrupted copy and a shortened copy raise `RetentionFailure` before any
  checker call. Their quality result is absent. The intact original control
  artifact remains retained; a known prefix is never passed as complete.
- Two deliberately authored, complete negative artifacts have their own
  identities: malformed JSON and structurally valid wrong content. Both are
  saved, verified and passed as complete fixtures, with expected `false` content
  results. Neither is a corrupted original producer submission.
- An attempted second exclusive save raises `FileExistsError` and leaves the
  original bytes unchanged. This is local file behavior, not first-submission
  monitoring or a guarantee against arbitrary host changes.

## Reuse and limits

Run only the focused module from the repository root, with the approved Python
runtime and `PYTHONPATH=engine`:

```sh
/Users/ianderrington/miniconda3/bin/python -m unittest discover -s engine/tests -p test_prospective_artifact_roundtrip.py -v
```

With no `C22_RETAIN_DIRECTORY`, it owns temporary files. For a separately
authorized future execution, that variable may name a new, nonexistent directory
for retained files. An existing directory refuses before component calls; the
original C22 first-run directory must never be reused. This test requires no
private fixtures and does not treat unavailable private data as passing evidence.

The [execution record](runs/2026-11-27-artifact-roundtrip.md) records the original
outputs, controls, timings and review state. These checks establish bounded
saved-byte/content compatibility only. They establish no firstness, real
receipt/time, complete process capture, registration, selected-source eligibility,
obligation outcome, predictive/causal/business advantage or hostile-host isolation.
Source selection/collection, broker and process lifecycle, deadline/receipt
resolution, registration/binding and runtime gates remain separate work.
