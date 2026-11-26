---
title: "Checking a delivery against the evidence"
description: "One future maintenance artifact, fixed acceptance criteria, and a record that keeps the first result even when it fails."
date: 2026-11-25
draft: false
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

A delivered file and a claim that it is correct are different things. In the [retained decision diagnosis](results/2026-11-26-decision-information-limits.md), three positive verification claims accompanied invalid simulated artifacts. Keeping a complete record did not prevent those deliveries from being accepted.

The next test uses a real, small maintenance task: inventory the links in one committed theory document. Its purpose is to determine whether a delivered inventory can be checked against fixed source bytes and criteria. It does not test the scientific truth of the document or establish a reliable verifier for every kind of artifact.

**Status: protocol under implementation.** Protocol preparation, task registration and delivery evaluation are separate steps. No real delivery result is reported here.

## An ordinary task with a checkable result

The project already needs to inspect cross-references left by a document migration. An inventory helps that work even if it finds no broken links. The test chooses one eligible theory document from a fixed, committed snapshot after the protocol is accepted. Selection uses a declared ordering and supported link syntax; it does not select whichever document produces a desirable outcome.

The producer delivers a new JSON file listing the supported links, their exact positions in the source, and whether their target files exist in the pinned repository tree. It separately states whether that artifact meets the criteria, fails them, or warrants abstention. The first submission is the unit of evaluation. A correction can be retained later, but it cannot replace an unsuccessful first submission.

A separate author builds the checker. It reads the retained source, repository-tree evidence, registration and delivered bytes. It does not import the producer's parser, change the inventory or ask a model whether it looks right. Its output identifies the criteria checked and the source spans behind discrepancies.

A correctly reported missing target is a successful inventory observation. It is not a failed delivery merely because the document contains a broken link.

## What the checker must establish

| Requirement | Evidence |
| --- | --- |
| The artifact belongs to this task | Registered task, criteria version, source commit, document identity and content digests |
| The inventory covers its declared scope | Every supported link appears once, in source order, with exact UTF-8 byte positions |
| Each target is classified correctly | Relative path direction and a complete retained Git-tree manifest, bound to its commit and objects |
| The counts describe the rows | Reconciled eligible, unsupported and target-status counts |
| The first submission remains visible | Its original bytes or explicitly bounded over-limit rejection receipt, followed by any separate revisions |

Version one supports a limited inline Markdown link grammar. Code, images, web URLs, reference-style links and unsupported syntax are excluded with explicit scope rules. Fragments are retained, but heading existence is unmeasured. The resulting counts do not establish full Markdown coverage, rendered navigation or semantic suitability of a link.

Malformed delivered JSON is a negative artifact result. It must not disappear as an invalid experiment request. The capture envelope still binds the original bytes to the task, even when the content cannot be decoded. An oversized submission retains a bounded prefix and an over-limit receipt; its prefix hash is never presented as a digest of the complete file. The retained prefix must actually include the byte beyond the permitted limit. A size assertion without those bytes leaves the claimed overflow unestablished. Neither case permits substituting a later successful artifact.

## Keep quality, identity and time separate

| Dimension | Question |
| --- | --- |
| Quality | Does the first artifact meet these particular frozen criteria? |
| Attribution | Who submitted the claim, and what evidence binds it to the artifact? |
| Availability | Which exact bytes were captured by the cutoff? |
| Effective authority | What narrow submission or checking permission was in effect, including known revocations? |
| Time assurance | Which times are local observations, issuer claims, or independently witnessed facts? |

A known issuer can make a wrong claim. Correct content can arrive late. A local record can be internally consistent without providing an independent witness of when it existed. This slice has no external timestamp witness; absent assurance remains explicit.

Registration fixes a delivery cutoff 24 hours later and a separate adjudication deadline 24 hours after that. A source's old issue date cannot make newly captured bytes available before their actual capture. A visible permission with a future effective date is not yet active. These distinctions matter when later investigators reconstruct what a decision maker could have known.

The queue parent identifies the task being consumed. A separate fixed evidence checkpoint includes observations made after registration. Both must match the authoritative local ledger. This lets a later check use genuine delivery evidence while preserving the earlier registration and a stable replay record.

## A finite path through success and failure

The supervisor first accepts checked protocol preparation, then registers one eligible task before producing the inventory. The first artifact and producer claim are captured. The independent checker runs, and a non-producer reviewer records the criterion-based adjudication or the reason it remains unresolved. These are explicit records; an agent saying “done” is not a substitute.

If there is no eligible document, registration remains pending with its reason and no quality score. The supervisor can continue other authorized work. It must not manufacture an eligible task or keep assessing an unchanged empty queue.

If no delivery arrives by the cutoff, a deadline-backed closure records that absence. A late artifact remains visible but cannot turn the original outcome into a pass or a failure. If delivery occurs but verification or adjudication is missing, one bounded review can close the task as unresolved. Evidence must be available and effective within the relevant window. The review cannot move a deadline, invent missing evidence or issue another unchanged review. Missing quality remains unknown, rather than becoming an artifact failure or a pass.

A closed first-delivery record selects preparation of the public research-map view. Positive, negative and explicitly unresolved results can all inform the next useful task. The next view will connect the project's real claims, sources, results and open questions; the moving lattice on the landing page remains an illustration.

The program uses local files and bounded processes, with no program model calls, network retrieval, payment, publication or production-control effects. Builder and reviewer effort is separate from the checker's runtime. One delivered artifact gives a concrete engineering observation, not a general accuracy estimate, predictive advantage or proof of autonomous improvement.
