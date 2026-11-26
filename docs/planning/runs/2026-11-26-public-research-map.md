---
title: "C11 public research map"
description: "Public evidence navigation, publication checks and the retained validation record."
date: 2026-11-25
draft: true
tts:
  enabled: false
feedback:
  enabled: true
---

C11 is in progress. The public selection and page are implemented; the first export has been checked independently. Final page validation and controller acceptance have not run. There is no browser, deployment, human-use or predictive-improvement result for this packet.

The accepted C10 delivery selected `dated-delivery-check-20261126:next / prepare_public_research_map_view`. Its immutable evidence origin is `improvement:dated-delivery-check-20261126:complete`, sequence 885, hash `55208f847a68aa8c636b2136c70994c9e3e2668512334f4f239764f60ad92c2f`. C10 is already complete and must not be rerun. Its local landing is `56899eef99972284e4dc933e99ed8de118d4ca83`.

The managed `public-research-map` worktree contains this packet. Separate workers own the public exporter, page/controller implementation and independent review. Root owns coordination, the focused navigation repair, documentation and final integration. Private process output, receipts, reviews and caller configuration are retained under `.supernal-local/public-research-map-v1/` in the persistent shared checkout. These records are not public site content.

## Public view and information boundary

The new `/research-map` route lets a reader search claims, follow directed relationships, inspect qualifications and open the cited documents. Stable claim URLs permit sharing a particular selection. The optional neighborhood drawing uses the same immediate edges as the HTML list; position and visual prominence carry no scientific score. Proposed experiments are identified as proposals. Bibliographic publication dates are distinct from collection receipts.

The explicit reviewed policy exports 20 claims in 61 nodes and 70 directed edges: 12 public documents, 16 bibliographic sources, 10 proposed experiments, one representation and two transformations accompany the claims. This is a selected public view, not the complete research catalog. It exports approved metadata rather than document bodies, arbitrary catalog fields, private planning records or ledger contents. All selected claims retain at least one public citation.

Catalog and document bytes are pinned to `f01a44f2371b49658aef61759e22377363e46788`. The source references include RFC 3161, RFC 7089 and RFC 9943; their bibliographic records do not establish an archived historical corpus, complete historical availability or the truth of a claim. The local Git pin is not an independent timestamp.

The public protocol is [Public research map](../../experiments/public-research-map.md). The home page and research overview link to the new view. The original simplex-inspired landing illustration remains a separate explanatory component; neither illustration is evidence that a representation predicts better.

## Development checks and repairs

The initial exporter suite passed 14 controls. Independent review then found that the size guard measured compact JSON before pretty serialization and the added payload digest; an accepted artifact could exceed its own reader's 256 KiB cap. The fix applies the bound to the complete serialized output. A further output-path finding showed that a leaf or parent symlink could redirect writing. Creation is now exclusive; replacement requires the exact prior raw digest and checked regular paths. Atomic replacement does not claim compare-and-swap protection against uncooperative concurrent writers.

The repaired exporter suite passed 17 controls in 12.687 seconds, 12.731 seconds for its enclosing process, with unchanged source bytes. Receipt SHA-256: `bdd0b5d4e2ca5eb3a9b7fb42216a67a561faf1743a66ec20f78ac525c2ff2e70`. Independent repair review, including eight additional writer controls, cleared these defects. Review SHA-256: `2cccc070edd286c6a424e303981d8c00d6fd1ae8176189e03407b22d6fb75c38`.

The initial page checks passed 10 pure model tests and scoped lint. An initial isolated typecheck failed with three missing CSS-module declaration errors because the fresh worktree had no generated Next declaration file. This remains a failed initial check. The replacement helper checks the real page and dataset using the installed Next CSS declaration, whose digest is reported; its final invocation is pending.

Independent component inspection also found that following a related claim removed the focused link without restoring focus. The repair moves focus to the selected heading for related-claim navigation and unknown-link recovery, while preserving the browse-list button's focus for list selection. Three actual React/jsdom component tests passed in 1.3 seconds, 4.016 seconds for the enclosing process, with four pinned files unchanged. These are simulated component interactions, not a real-browser accessibility or visual inspection.

The implementation was committed as `f01a44f2371b49658aef61759e22377363e46788`; repaired export, focus, policy, dataset and public protocol followed in `6150315`. Reviewed working-tree exporter repairs were used during the first export before the latter commit; committed input pins and code-under-review are separate facts.

## First actual export

The exporter created the dataset once, using exclusive creation, and the read-only verifier then passed its seven fixed checks. No export was repeated. `src/data/public-research-map.json` is 33,112 bytes, raw SHA-256 `7608ebe0f4627481cd8befc9f9561c58958e6317f1270e329d4cc59050b9abd9`, payload hash `a77a2c1c8c763117a850c471802f8b062921c6d8d146101fbb979432d835b7d2`, catalog hash `5b5d766e8de7c4ef7ad8923727a208cada2f164501b40342b5bddeea74d69a09`.

The enclosing receipt correctly sampled sequence inputs before and after execution. Its original per-command field named `before` was actually sampled after that command; it was renamed `observedAfter` and the correction disclosed. The original receipt remains retained, SHA-256 `4cd0df6e28ffb908ee6cd15fe91cbd17b648dca9ada56ea84a76a63964767d84`; the corrected receipt is `6f37ea1e252fc75f166bc1c59c91635d7fa48d1220116dc54310bbdb528b3cb3`. No command was replayed to hide this bookkeeping defect.

An independent audit passed 31 checks without rerunning the export or verifier. It recomputed the exact projection and payload/catalog hashes, checked all 12 committed/current document byte bindings, approved fields and URLs, input/runtime/output identities, and the receipt correction. Audit JSON SHA-256: `83d3645bba9ba7273cfd9acb3b85cd8e196c4cb6725d9deba703c17712205830`; report SHA-256: `507a0e8a83b0c1cd9636e24c13d57e2c5b3f0a4fa8500611803e96c15f9eaebb`.

## Acceptance work in progress

The second acceptance-plan version, SHA-256 `ff7c35a0f0aa0a61a28ebb188c132d108c2717d74e4417cbeb44f7adf6aebd43`, corrects a failure-path mistake: a real failed verifier may emit no success JSON. Its retained nonzero outcome must remain negative evidence. Malformed datasets under valid captures are artifact failures; malformed or unbound study requests are refused before claim. A reported success contradicted by retained bytes must fail the relevant criterion.

The adapter will inspect retained output from six fixed validation categories: exporter controls, page controls, typecheck, lint, production build and final public-data verification. The build precedes the final verifier. Generated public content is an output with a retained identity, not an immutable prebuild input. Raw process outcomes are persisted before later postprocessing. The caller has fixed commands, source/runtime identities, limits and an exclusive run claim; it is trusted local execution evidence, not proof against a malicious host.

Initial owned adapter controls passed 13 tests. The initial controller run exposed two incorrect test assertions, which were fixed without changing production behavior; the failed run remains retained. The corrected controller module passed 53 tests, including eight real lifecycle controls, in 48.511 seconds, 48.777 seconds for the outer process.

Independent source review then reproduced two acceptance defects using synthetic ledgers only: consistently rebound private/draft document bytes could contradict a reported pass without failing independent validation, and provenance-label changes alone could qualify an unchanged failed packet for another attempt. The first repaired owned window passed 24 tests (16 adapter controls and eight controller controls) in 33.288 seconds, 33.627 seconds for the enclosing process, with unchanged source/test bytes. These findings do not imply a private document was exported or an actual C11 retry occurred.

The broader affected-path window then passed 270 tests in 89.422 seconds (89.866 outer), followed by six existing lifecycle/dispatcher controls in 63.424 seconds (63.962 outer). Engine, test and contract pins remained unchanged in both windows. These are affected-path and selected legacy checks, not a complete repository test run.

The next independent recheck closed the original defects but found two narrower repair boundaries: `title: # comment` was mistakenly treated as a nonempty title, and correcting only an invalid derived payload hash was wrongly refused as an unchanged attempt. The final repair treats a comment-only scalar as empty and retains derived-integrity validity in the separate repair fingerprint. Consistently rebound provenance labels still do not qualify as changed content, while a real invalid-to-valid integrity correction can. The publication parser deliberately supports a conservative scalar-frontmatter subset; it does not claim general YAML equivalence.

The final focused window passed 25 tests in 15.754 seconds (16.006 outer), with unchanged source/test bytes. Only the adapter and its tests changed after the broader run. An independent four-case recheck confirmed both original cases and both repair boundaries. Final adapter SHA-256: `b50017efd222b77faaff57613f10dd7dda3b22f692df4c5a7ed5ccddea0549b8`; tests: `29c23ce33bb59d128abc984a9bfbd72b1f18f18e17be9ab403d907d271c5c535`. No actual C11 invocation occurred during these controls.

A passed preparation will select `prepare_evidence_navigation_evaluation`; a measured failure will select `repair_public_research_map_preparation`. The proposed next evaluation has six textual cases covering source lookup, qualifications and proposed follow-ups, with a separate answer key and fixed map version. It will measure information retrieval and interpretation, not browser usability or viral growth. Metric-based successors remain explicit rules; there is no calibrated prediction of the best action's return.

## Site coordination

SCI acknowledged C10 ownership and later reported that its earlier release of `a4937d5` is complete and its push hold removed. SCI reports production `2a0d1ea` has that release's tree and was checked live. C10 and C11 are not part of that release. These are SCI's observations, not a new live inspection by this supervisor.

SCI also reported a timezone-dependent React hydration error on 55 of 63 live pages in America/Los_Angeles and none in UTC, and two CI runs exceeding the 20-minute job limit. SCI declined the requested date-repair ownership; the supervisor acknowledged this and assigned a separate worker in managed worktree `date-rendering`. Its sources and validation are separate from the frozen C11 worktree. The CI capacity issue is queued for follow-up. Neither issue is treated as repaired here.
