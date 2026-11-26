---
task: dated-delivery
branch: worktree-dated-delivery
reviewed_patch_id: e99b54d67178a09b5370540e6e4bf5ea2d378d7d
reviewer_model: inherited
reviewer_agent_id: /root/c8_accept_review
reviewer_output_sha256: 2cf46cf69f9e193f6091eef11519c17f3709674e5d7c33ff157e53f30432c4e0
author_session_id: ""
verdict: fixed
findings: { critical: 0, high: 0, medium: 9, low: 1 }
resolved: { fixed: 10, skipped: 0 }
skip_class: ""
skip_reason: ""
size: { files: 21, lines: 3137 }
---

# C10 final integration and publication review

Disposition: ready for local landing. No open actionable findings remain in this reviewed packet. This is not a deployment, browser-quality, general verifier-reliability or public-map implementation approval.

Reviewer: /root/c8_accept_review. Reviewed worktree: /Users/ianderrington/git/ianderrington/epiphysics/.worktrees/dated-delivery. Final commit: f8993bd970d9c4f54553a1a550282084bbdb0fdc; base: a4937d5. The worktree was clean. The final patch contains 21 files, 3,103 insertions and 34 deletions. Independently recomputed SC-compatible verbatim patch ID: e99b54d67178a09b5370540e6e4bf5ea2d378d7d. The exact no-color/no-ext-diff/no-textconv/no-renames/binary/full-index diff is 273,944 bytes, SHA-256 982b7f0220127ba99b491d543dc9420702229ecca72d433ccfeebbce94c8cf8b.

## Independent scope

Reviewed the final protocol, preparation result, first-delivery result, internal run history, homepage status JSON, catalog additions, roadmap/loop instructions and their relevant homepage/guard/map consumers. Compared public claims to the retained registration, first delivery, verification, adjudication and accepted CHECK evidence, including my earlier independently produced 49-check acceptance audit. Rechecked source and test identities, retained validation receipts and stream hashes, frozen archive contents, emitted site artifacts and final compiled graph. This pass did not rerun any producer, verifier, assessment, historical study, test suite or framework build; it did not mutate the ledger or repository. Earlier whole-packet and targeted repair reviews remain applicable only because the nine engine/test/contract/criteria files still match their reviewed hashes.

## Findings and repair accounting

One new publication finding was corrected during this review: P3, docs/experiments/results/2026-11-26-first-dated-delivery.md:50 called 27.891 seconds the enclosing dispatcher call. The retained evidence distinguishes caller wall time 27.890696291 seconds from dispatcher time 26.760515709 seconds. Commit f8993bd changes the label to enclosing caller wall time. The corrected public file is SHA-256 192a4fdfee70024a083488cb6af9ffb061c31de4bdea79347f91633a159ee641. The final internal run note is SHA-256 50aa607a57df661781c82d1d3b93aa4c1c89558145c38cf70034bbc8649364ba.

Historical findings are distinct from that current wording correction and are all closed:

- Committed core: eight distinct P2 findings. The whole-packet review recorded six; the core review contributed two additional findings after deduplicating its late-delivery and future-effective-verification findings. They concern late-delivery rescue, malformed revision metadata, preclaim readiness, overflow chronology, exact prepared protocol bytes, future-effective verification, unproved overflow size and boolean registration versions.
- Committed pure verifier: one P2, expanded result exceeding the bounded output envelope despite a permitted artifact. The repair preserves complete token coverage and the original cap.
- Private preparation caller: one P2, rejecting the current authoritative counts envelope.
- Private producer: one P2, unbounded registration input.
- Private registration utility: two distinct findings. Implicit Git lazy fetching/helper execution was rated P1 by the independent reviewer and P2 in my guided review; both assessments concern the same issue and are not double-counted. Loaded utility/source identity mismatch was P2. Both repairs were independently rechecked.
- Earlier plan review: three P2 lifecycle findings, counted separately from implementation/publication findings: post-registration evidence checkpoint, finite unresolved closure and malformed-first-artifact treatment.

Thus committed-source history comprises nine repaired P2 implementation findings, plus this separate P3 public wording correction. Private invocation programs have four repaired findings with the severity attribution above. The three plan findings are additional design-review history. No blanket severity is assigned to all fourteen implementation/private/publication findings. Initial reports, failures and repair addenda remain retained; missing early raw component logs are disclosed in the run note.

## Accepted outcome and measurement scope

The unchanged acceptance audit JSON is SHA-256 1401005f91d5f190a7c58bc68d20e0ec9de420cc5c1fe1aff1e3024df20f78f5; its 49 checks passed with no findings. It covered 885 ledger events, 847 observation bindings and 257 unique blobs, with an unchanged logical ledger digest. Accepted CHECK event 885 is improvement:dated-delivery-check-20261126:complete, hash 55208f847a68aa8c636b2136c70994c9e3e2668512334f4f239764f60ad92c2f. It records nineteen completed assessments, no unfinished run and successor prepare_public_research_map_view.

Public wording correctly describes one original 7,130-byte artifact, twenty supported link occurrences and twenty-eight exclusions. Agreement is one agreement in one eligible delivery, not twenty independent trials or an accuracy estimate. The inventory digest remains b6062be96ef0bcf55f3b972ff7b948c7131a75920694584e7a9f485be9422d7e. Local producer permission is true; verifier/adjudicator authority remains unknown and external witness is absent. Fragment validity, rendered navigation, external URL reachability, semantic suitability and scientific truth remain unmeasured. The separately recorded producer execution is distinguished from the assessment's zero producer executions. Checker recomputation is disclosed; nested timings are not added and program runtime is not represented as total builder/reviewer effort. Preparation and registration remain historical stages rather than extra delivery trials.

## Validation and frozen evidence

All nine reviewed engine/test/contract/criteria files match prior repaired source. Core SHA-256 remains 26f089f546130d6bf3edabdf51ddc0990b2a14160a6a0953400fa581bf3779ee and verifier SHA-256 remains 2a371b6f215b01c32351f1c22d033c5e50bdc47c431dfec7b3a0015c3951024e. Actual execution used source commit 27eff8581a501f586dd0a8718eb7eed2e97f67d7; later committed changes under review concern publication, not those executing bytes.

Independently checked the retained 246-test decision/delivery receipt and six-test legacy receipt, their stdout/stderr hashes and all 85 pinned source files. The three readiness controls have matching streams and all 37 pins. Reported test windows are 51.208, 40.158 and 2.080 seconds respectively; these are scoped suites, not an unqualified whole-repository pass. Private configured preparation controls, fifteen producer controls and eleven registration controls are separately recorded. The producer's exact Python 3.14.8 receipt supports the final run note; the earlier registration run under another Python environment is not substituted for its accepted-interpreter validation.

Rehashed every frozen-delivery-archive entry: 233 paths, 212 unique blobs, no size/hash mismatches. Index SHA-256 is 1da59972bf104fae9a932b0b2fce6dad034bda4c3d236fa75a0830db5054c06f. That archive intentionally predates the final copyedit; the corrected documents and final graph are bound separately to f8993bd. The earlier preparation archive remains separate. Historical path labels are provenance, not a claim that every current working path still holds the archived bytes.

## Site and graph evidence

The one retained framework-build log reports successful compilation in 18.5 seconds and all sixteen static pages generated; three homepage evidence guards passed. Independently compared all 952 before/after tracked-source hashes: only public/content-data.json changed. All four retained HTML/manifest artifacts match their declared sizes and hashes. The generated content increased from 61 to 64 unique records, adding only the C10 protocol and two results, with none removed. All eight relative links in those public documents resolve. Their homepage claim anchors and the emitted homepage heading/links match. No private filesystem references were found in those new public documents.

The wrapper subsequently exited 1 because it used an incorrect filename for the previous content artifact. The build subprocess return code and total duration were not persisted and remain unknown. The successful compiler/page-generation log and retained outputs do not recover those missing measurements. Recovery preserved outputs, compared the correct prior content artifact and restored the tracked cache exactly. Types and lint were skipped in that build; no browser or deployment check is claimed.

The final wording correction followed that full build. Retained copyedit-checks.json records content preprocessing exit 0 in 2.645491250 seconds and the homepage guard exit 0 in 0.084061917 seconds, without another framework build. The final preprocessed content has 64 unique records and contains the corrected caller label; its SHA-256 is 77487c280c40a5a91d69a797eebf134cc55210ddf252b20c938af35dffa71219. The tracked cache was restored again and the worktree is clean.

Independently recomputed the final graph payload and matched all 37 retained document bodies and digests to final committed Git bytes. Graph counts are 151 nodes, 182 edges and 35 bibliographic sources; catalog nodes/edges match their committed definitions. File .supernal-local/meta-representation/2026-11-26-c10-final.json is SHA-256 5474698b3a83007dd84ca07563300088490389105844036289300c5ad56d6255; payload SHA-256 a584712ac301fd2915d2e597903008b9e836c2e067ace5a81d8d7abf4dab0d92. The artifact remains private and includes internal documentation; it is not approved for wholesale public export. Experiment status follows the existing schema, with observed completion represented by separate result claims/documents. New bibliographic summaries were checked against primary RFC pages: [RFC 3161](https://www.rfc-editor.org/rfc/rfc3161.html), [RFC 7089](https://www.rfc-editor.org/rfc/rfc7089.html) and [RFC 9943](https://www.rfc-editor.org/rfc/rfc9943.html), including the last one's ordering, accuracy and selective-submission qualifications.

The selected public-map successor is correctly represented as work to build and assess, not an accepted map result or measured engagement improvement. Its separate implementation and any later deployment require their own evidence; neither is covered by this local C10 landing review.
