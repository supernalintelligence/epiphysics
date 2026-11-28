---
title: "Making research claims inspectable"
description: "A public view of claims, citations, qualifications and proposed tests, with an explicit publication boundary and measurable checks."
date: 2026-11-25
draft: false
tts:
  enabled: true
  provider: openai
  voice: onyx
feedback:
  enabled: true
---

A research map should help a reader answer two ordinary questions: what is being claimed, and where can I inspect its basis?

The [first maintenance delivery](results/2026-11-26-first-dated-delivery.md) selected this work as its successor. The map connects a reviewed subset of the project's existing claims, sources, results, qualifications and proposed tests. It does not discover new entities or establish the truth of a claim by connecting it to other nodes.

The [map route](/research-map) has a claim browser, a readable relationship list and an optional diagram. This is a local preparation protocol: publication, real-browser behavior and user benefit require separate evidence. The checks below define what the preparation step can establish and what it leaves unmeasured.

## Read the statement and its basis together

Each claim retains its statement, status and basis. A hypothesis remains a hypothesis. A reported result belongs to the task and population described in its evidence; one successful artifact is not a general accuracy estimate. An implementation finding does not establish a scientific theory.

Citations are recorded relationships, not automatic endorsements. A qualification can coexist with the claim it qualifies: mechanisms that concentrate control and mechanisms that improve portability can operate together. Proposed experiments remain labeled as proposals even when a separate result reports related completed work.

The list and graph expose the same immediate relationships for the selected claim. Every relationship is also readable as text, including its direction. Search and status filters help narrow the list, and a permanent claim link preserves the selected record. The diagram is optional; its shape is not an importance, confidence or authority score.

## Publish a deliberate subset

The internal research artifact includes planning records, code and full document text. The public map must not receive that artifact wholesale. An explicit policy selects public node identities and document routes; an exporter constructs only the permitted fields for each kind of record. Excluded nodes and their incident relationships are absent.

Public documents must match their committed bytes, publication metadata and generated public routes. Source records are bibliographic references with dates and limitations, not archived article snapshots. A source's publication date does not establish when its contents became available to this project. Export hashes identify bytes and versions; they are not external timestamp witnesses.

The export command is separate from ordinary builds. A build verifies the existing public dataset against its pinned inputs and refuses an unexpected change. It does not silently add new records or regenerate the publication policy. Source changes require a new, reviewed version; earlier Git versions and execution evidence remain available.

## Preparation checks

| Check | What it establishes |
| --- | --- |
| Publication policy and dataset | Only selected identities and fields appear; private and draft records are excluded; routes and source identities match |
| Relationship consistency | Every displayed edge has retained endpoints and its declared direction; the graph and readable list use the same relationships |
| Exporter controls | Invalid publication metadata, changed inputs, unsafe paths and oversized artifacts are rejected |
| Component controls | Search, selection, URL handling and focused keyboard-state cases behave as specified in isolated tests |
| Type and lint checks | The actual page, generated data and relevant source satisfy the selected static checks |
| Production build | The checked source and dataset produce the expected local application artifacts |

These checks have distinct scopes. Simulated component events are not real-browser accessibility or visual verification. A completed build does not measure whether a person understands a claim. The preparation record must keep those outcomes unknown when no corresponding evidence exists.

## Failures must remain usable evidence

The supervisor captures actual process outcomes, exact input and source identities, and raw validation output. The acceptance program checks these retained records; it does not execute supplied scripts or start another build.

A valid failed validator invocation can have no success report. That is a negative check result, with unavailable quantities left unknown. An unbound receipt or stale queue parent is a different problem and cannot complete the task. A malformed dataset under a valid capture is an artifact failure. The system must not discard it merely because its contents fail to parse.

Passing preparation selects a bounded evidence-navigation evaluation. A failed required check selects repair with changed relevant evidence; repeating unchanged failures under fresh run names is not progress. These transitions record what the local programs and reviews established, without treating local receipts as proof against a malicious host.

## What to measure next

The next proposed evaluation uses six fixed textual tasks: finding two sources, finding two qualifications, and distinguishing two proposed follow-ups from established results. Freeze the map version and separate answer key before attempts. Score correct evidence references, relationship direction, status interpretation and unresolved answers separately.

That is a test of the information available through this representation. Browser usability, useful corrections, completed reproductions and sharing behavior require their own observations. No engagement or viral-growth result is implied by adding a graph or a permanent link.
