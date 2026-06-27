---
title: "Publishing Pathway: The Physics of Common Sense (KDP, under one week)"
description: >-
  A verified, day-by-day pathway to self-publish "The Physics of Common Sense" on Amazon KDP
  in under a week, assembled from existing Epiphysics docs. Skips paid proofreading in favor
  of a meta-proofread loop (multi-persona reads, humanization, de-AI-ing) and covers AI image
  generation for the cover and interior. KDP facts verified June 2026.
date: 2026-06-17T00:00:00.000Z
draft: true
author:
  name: "Ian Derrington"
  role: "Framework Author"
authors:
  - name: "Ian Derrington"
  - name: "Parnian Barekatain"
contentType: article
mediaTypes:
  - text
series: "Epimechanics"
categories:
  - Publishing
  - Systems thinking
tts: false
feedback: true
---

# Publishing Pathway: The Physics of Common Sense

A concrete plan to take existing Epiphysics writing to a live, purchasable Amazon book in under one week. KDP-specific facts in this document were verified against Amazon KDP help pages and current (June 2026) publishing sources; see [Sources](#sources-verified-june-2026). Where the agent's first draft was stale, this version corrects it (notably: KDP categories).

## Source-material survey (where the book actually lives)

The two candidate corpora are not equally useful.

- **Epiphysics repo (`docs/`) is the book.** Roughly 45,000 to 60,000 words are already book-ready with light edits, concentrated in the A-list below. `docs/applications/index.md` also references an existing "physics_of_common_sense" blog series on ian.ceo, which proves the popular-science framing already exists in the author's voice.
- **The ian.ceo blog repo is the real chapter source.** `../nextjs-github-markdown-blog/docs/musings/existence_physics_and_life/physics_of_common_sense/` already holds a drafted **"Physics of Common Sense" series** (~11 posts: messy desk, habits, house cost, best description wins, energy of knowledge, and more), written in the anecdote-first voice the book uses. The [Book Outline](./book_outline_physics_of_common_sense.md) builds the everyday edition directly on these. This is the head start that makes the one-week build realistic, and it shifts the Day 1 to 2 work from "de-math theory docs" to "order existing posts + write the ~10 gap chapters on the same template."
- **Supernal-nova blog is off-target.** Every post in `families/supernal-interface/docs-site/.../blog` concerns the Supernal Interface developer tool (UX, testing). Topical fit is near zero. Ignore it for this book.

### A-list: chapter skeleton

> The full section plan, with each chapter mapped to the common-sense literature and a proverb-to-physics catalog, is in the companion doc: [Book Outline](./book_outline_physics_of_common_sense.md). The table below is the condensed source-file view.

Target a 45,000 to 55,000 word book. Trade non-fiction of 50k words reads as a real book and prints to roughly 180 to 200 pages.

| # | Working chapter title | Source file | Note |
|---|---|---|---|
| Preface | Why common sense is physics | `docs/ELEVATOR_PITCH.md` | Tightest thesis |
| 1 | The map is not the territory | `docs/theory/00_prelude.md` | X as representation; causation primitive |
| 2 | When does a thing become real? | `docs/theory/02_meta_entities.md` | Markets, companies, religions as entities |
| 3 | The gap between mind and world | `docs/theory/belief_field.md` | Delusion, surprise, learning |
| 4 | Life is a thermodynamic accident that stuck | `docs/theory/01c_thermodynamic_emergence_of_life.md` | Standout accessible narrative |
| 5 | Everything is coupled to everything | `docs/theory/coupling_chains.md` | Concrete stress, health, economic chains |
| 6 | Your company is a creature | `docs/applications/companies_as_entities.md` | Strip math; add efficiency_limits "lightbulb in a closet" |
| 7 | The weight of an idea | `docs/theory/01_generalized_mechanics.md` | Mine prose; sidebar the math |
| 8 | Time, memory, and the shape of a self | `docs/theory/04_time_and_soul.md` | Soul as measurable causal biography |
| 9 | Can we test any of this? | `docs/experiments/prompt_prediction_experiment.md` + `docs/research/representation_derivation_problem.md` | Honest open-problem close |
| Conclusion | The discipline of honest prediction | new (~1,500 words) | Tie back to falsifiability |
| Glossary | Plain-language terms | `docs/theory/glossary.md` | Light edit to appendix |

**Keep out** (appendix-only or omit): cause-plex and amplitude papers, `05_ontology`, `self_application_and_lawvere`, and the `research/audits|brainstorms|handoffs|tensor_programs|working-papers` subtrees. They would sink a popular-science book.

**Preserve as a differentiator:** the framework labels every claim Definition / Postulate / Consequence and repeatedly states "testable, not yet tested." That honesty is the marketable edge over typical pop-science overreach. Do not edit it out during humanization.

## The critical path

KDP's review queue is the only hard external gate. Amazon states **up to 3 business days** (commonly 24 to 72 hours) from submission to live. To be live by Day 6 or 7, **hit Publish by Day 4 midday.** Everything before Day 4 is what you compress; the review window you cannot. First-time-publisher status can push toward the full 72 hours, so treat the early end as optimistic.

Two timeline traps:
1. **Paperback physical proof shipping (3 to 5 days) breaks the deadline for print.** Ship the eBook on time; let the paperback fast-follow. Approve via KDP's online previewer to publish print without waiting for a physical proof.
2. **Anything with external turnaround must be ordered Day 2 to 3** or it will not return in time. With paid proofreading removed (see below), the remaining external item is an optional cover, and even that can be done same-day in-house.

## Day-by-day plan

### Day 1 — Assemble the manuscript
1. Lock the table of contents from the A-list. Decide eBook + paperback (format once, publish both). (~1h, $0)
2. Concatenate sources into one `book/manuscript.md` in order. Strip equations heavier than a single inline expression; demote surviving math into `[!sidenote]` / box callouts rendered as block quotes. (~3 to 4h, $0)
3. Write connective tissue: a 1 to 2 paragraph bridge per chapter head, a ~1,500-word Introduction (the one big idea, who it is for), and a ~1,500-word Conclusion. (~3h, $0)
4. Draft front and back matter: title page, copyright page (template below), TOC placeholder, About the Author. (~1h, $0)

> **Copyright page:** *The Physics of Common Sense. Copyright (c) 2026 Ian Derrington. All rights reserved. No part of this book may be reproduced without written permission except brief quotations in reviews. First edition, 2026. [ISBN]. Published independently via Amazon KDP.*

**Day 1 deliverable:** a single ~50k-word `manuscript.md` that reads start to finish.

### Day 2 — Self-edit + style enforcement (no paid proofread)
The professional proofread is **deliberately skipped.** It is replaced by the meta-proofread loop on Day 3 (multi-persona reads, humanization, de-AI-ing). Day 2 is your own structural and mechanical pass.

5. Full read-aloud line edit for flow and de-jargoning. Replace each domain term's first use with a plain-English gloss. (~4h, $0)
6. Enforce documented style rules programmatically, then by eye:
   - **No em dashes.** `grep -nE '—| - ' book/manuscript.md` and replace by context (comma, colon, semicolon, parens).
   - **No value-laden words** ("interesting," "trivial," "obviously," "elegant," "fascinating"). `grep -nEi '\b(interesting|trivial|obviously|elegant|fascinating|simply)\b' book/manuscript.md` and rewrite each hit.
   (~1.5h, $0)
7. Mechanical-only tooling pass (free): ProWritingAid free tier or LanguageTool. Accept spelling and agreement fixes; **ignore its em-dash suggestions** (they conflict with house style). (~2h, $0)

### Day 3 — Meta-proofread loop, format, cover, and start KDP upload
This is the day to protect. Run the meta-proofread loop, then format and cover in parallel, and open the KDP draft.

#### 3a. Meta-proofread: multi-persona reads, humanization, de-AI-ing
Replace one professional proofreader with several simulated readers plus a de-AI pass. Run each as a separate focused read (a subagent per persona works well), each producing a margin-note list, then reconcile.

**Reader personas (read the whole manuscript through each lens):**
| Persona | Reads for | Flags |
|---|---|---|
| The skeptical scientist | Is each claim labeled and falsifiable? | Overreach, hand-waving, unlabeled postulates |
| The curious non-expert | Can I follow without the math? | First-use jargon, undefined terms, lost threads |
| The busy executive | Does each chapter earn its place in 5 minutes? | Slow openings, buried payoffs |
| The hostile reviewer | What is the weakest sentence to quote against you? | Sloppy analogies, unguarded absolutes |
| The reader who loves prose | Does it sound like a person? | Flat rhythm, repetition, lifeless transitions |

**Humanization pass.** After persona notes, rewrite flagged passages toward natural voice: vary sentence length, cut throat-clearing ("It is important to note that"), prefer concrete nouns and active verbs, keep the author's actual cadence from the ian.ceo series as the target register.

**De-AI-ing pass (the AI-writing tells to remove):**
- Em dashes (already enforced) and the "not only X but also Y" cadence.
- Tricolon overuse ("clear, concise, and compelling"); triplet lists where two items suffice.
- Hedge stacks ("can potentially help to"), "delve," "tapestry," "underscore," "testament to," "navigate the landscape," "in today's world."
- Uniform paragraph length and identical topic-sentence openings.
- Sectional summaries that restate the section verbatim.
- Run a final grep for the worst offenders and rewrite by hand.

Reconcile all persona + humanization + de-AI notes into one edit pass on `manuscript.md`. (~4 to 5h, $0)

#### 3b. Format: markdown to EPUB + print PDF
Given a Mac and markdown source:
- **eBook:** Pandoc to EPUB (free, native to the markdown).
  `pandoc manuscript.md --toc --toc-depth=1 --metadata title="The Physics of Common Sense" --metadata author="Ian Derrington" --css epub.css -o book.epub`
  Validate by importing into **Kindle Previewer** (free Mac app) to catch reflow issues.
- **Paperback:** **Reedsy Studio** (free, browser) for a clean print PDF, or **Vellum** ($249 one-time, Mac, near-zero effort, professional typesetting) if the print edition's look matters for credibility. For a first book on a tight clock, Reedsy free is the pragmatic call.

| Tool | Cost | Best for |
|---|---|---|
| Pandoc | Free | eBook EPUB from markdown |
| Reedsy Studio | Free | Free path to print PDF + EPUB |
| Vellum (Mac) | $249 one-time | Polished EPUB + print PDF, trivial UI |
| Atticus | $147 one-time | Cross-platform Vellum alternative |
| Kindle Create | Free | KDP-native eBook fallback |

(~2 to 4h, $0 to 249)

#### 3c. Cover + interior images (AI image generation)
**Cover.** A wrap cover (back + spine + front) is needed for paperback; the eBook needs the front only.
- **AI-generated front art** for an abstract "physics of ideas" motif: Midjourney, DALL-E, or Ideogram (Ideogram handles in-image text best). Generate the art, then set title and author typography in Canva over it. ($10 to 30, ~2 to 3h)
- **Specs.** eBook front: 1600 x 2560 px, 1.6:1, RGB JPG/TIFF, under 50 MB. Paperback wrap: use **KDP's cover template generator** with the final trim size (6x9), page count, and paper type; it returns exact dimensions with bleed. Generate the wrap only after the formatting step gives the final page count.
- **Fallbacks:** Canva book-cover templates (free, full control, same-day) or a Fiverr designer ($25 to 150, 24 to 48h, order at the start of Day 3 if used).

**Interior images.** Most chapters need none. Where a diagram clarifies (coupling chains, the belief-field gap, the company-as-entity sketch), generate clean line-style figures with an AI tool or draw them in Excalidraw / Figma and export grayscale PNGs. **Print interior is black-and-white** unless you pay for color print (expensive); design figures to read in grayscale. Keep figure count low to protect the timeline. ($0 to 20, time as available)

#### 3d. Open the KDP draft
Create the KDP account early (tax info W-9/W-8, bank for royalties) and start the title setup; save a draft even before files are final. (~1h, $0)

### Day 4 — Final QA and SUBMIT (triggers the review clock)
8. Final QA in Kindle Previewer (eBook) and a PDF read-through (paperback): TOC links, chapter breaks, no orphaned equations, correct front matter. (~2h, $0)
9. Fill KDP metadata and upload by midday. **This starts the up-to-72-hour clock.**
   - **Title:** The Physics of Common Sense.
   - **Subtitle (do keyword work here):** e.g. *A New Science of How Ideas, Minds, and Markets Become Real.* Front-load discoverable terms.
   - **Description (~4,000 char, simple HTML allowed):** hook in the first two lines, three "you will learn" bullets, a credibility line, a call to action. Weave keywords naturally (representation, prediction, complexity, emergence, systems thinking).
   - **7 keyword phrases, up to 50 characters each:** e.g. `physics of ideas`, `systems thinking science`, `how markets become real`, `prediction and complexity`, `representation vs reality`, `emergence and entropy explained`, `science of common sense`. Test them against KDP search-bar autocomplete first.
   - **Categories (CORRECTED):** you now select **up to 3 Amazon store categories per format directly in the KDP dashboard.** Amazon replaced BISAC selection with its own store categories in mid-2023, and the old "email KDP for up to 10 categories" route is gone. Pick 3 of: `Science > Physics`, `Science > System Theory`, `Philosophy > Epistemology`, `Business & Economics > Systems & Complexity`.
   - **ISBN:** take the **free KDP-assigned ISBN** for paperback (none needed for Kindle eBook). Buy a Bowker ISBN ($125) only if you want your own imprint of record or to sell paperback outside Amazon. For under a week, take the free one.
   - **Pricing:** list the eBook at **$4.99 to $6.99** to stay inside the **$2.99 to $9.99 window required for the 70% royalty tier** (outside it you earn 35%; the 70% tier also deducts a small per-MB delivery cost and requires the list price be at least 20% below any physical edition). Paperback: KDP sets a print-cost minimum (~$4.50 for a 200-page B&W 6x9); list at **$12.99 to $14.99**.
   - **KDP Select / Kindle Unlimited:** enrolling requires **90-day eBook exclusivity to Amazon** (print and audio can still go anywhere; the term auto-renews and cannot be exited mid-cycle) and grants Kindle Unlimited page-read royalties plus Countdown and Free-promo days. **Recommendation: enroll** — for an unknown author, KU reach and promo tools outweigh near-zero non-Amazon launch sales.
   - Upload EPUB + cover (and paperback interior PDF + wrap), preview in KDP's online previewer, click **Publish.** (~3h, $0)
10. **Paperback proof decision:** a physical proof adds 3 to 5 days and breaks the deadline. Approve via the online previewer to publish print on time, or publish the eBook now and let print fast-follow. The eBook is the deadline-critical product. (~0h)

### Day 5 — In review (launch prep)
11. KDP is reviewing; it cannot be rushed. Write launch assets: a 200-word announcement, three social posts, a list email, and an ian.ceo post linking the existing "physics of common sense" series to the book. (~3h, $0)
12. Set up an Amazon Author Central page (bio + photo) to link the author name to the book. (~1h, $0)

### Day 6–7 — Live + launch
13. Book goes live when review clears (typically Day 5 to 6 if submitted Day 4 midday).
14. Launch checklist: verify the live listing (title, cover, price, Look Inside); optionally run a 48-hour $0.99 or free launch price via a Countdown/Free promo to drive early rank, then raise to $4.99; publish the ian.ceo post and announce everywhere; ask 5 to 10 colleagues to buy and leave honest reviews in week one (early reviews drive the algorithm). (~2 to 3h, $0; paid promo lists usually not bookable on under a week's notice — skip for launch.)

## Cost summary

| Item | Lean path | Polished path |
|---|---|---|
| Content assembly / writing | $0 | $0 |
| Editing | $0 (self + free tools) | $0 (paid proofread removed by request) |
| Meta-proofread loop | $0 (personas + humanization + de-AI) | $0 |
| Formatting | $0 (Pandoc + Reedsy Studio) | $249 (Vellum) |
| Cover + interior images | $0 (Canva) | $10 to 150 (AI art + optional Fiverr) |
| ISBN | $0 (free KDP) | $0 or $125 (own Bowker) |
| KDP account / publishing | $0 | $0 |
| Launch promo | $0 | $0 to 150 (optional, likely skipped) |
| **Total** | **$0** | **~$260 to 525** |

With the paid proofread removed, even the polished path stays modest. The biggest discretionary spend is Vellum ($249) for paperback typesetting.

## Compressed timeline

```
            D1      D2        D3                  D4            D5         D6-7
Content   ████████
Self-edit          ████████
Meta-proofread               ████ (personas + humanize + de-AI)
Format/convert               ████
Cover + AI images            ████ (Canva/AI same-day)
KDP setup                    ████ start draft
Final QA + SUBMIT                                ████ ◄── 72h review clock STARTS (hard gate)
KDP review                                       ░░░░░░░░░░░░░░ (up to 3 business days)
Launch prep                                                ████
GO LIVE + launch                                                      ████
```

**The one thing that matters most:** protect Day 4 midday as the submit-by deadline. Assemble and de-math fast (Days 1 to 2), run the meta-proofread + format + cover in parallel (Day 3), submit the eBook Day 4. The review window lands you live by Day 6 to 7. Paperback fast-follows; everything else is optional polish you can layer in via a KDP republish after launch.

## Sources (verified June 2026)

- KDP review and timeline: [KDP Timelines](https://kdp.amazon.com/en_US/help/topic/G202173620), [KDP Book Status](https://kdp.amazon.com/en_US/help/topic/G200627450), [Vappingo: KDP publishing timeline](https://www.vappingo.com/word-blog/kdp-publishing-timeline/)
- Royalties and pricing: [KDP eBook Royalties](https://kdp.amazon.com/en_US/help/topic/G200644210), [KDP Digital Book Pricing](https://kdp.amazon.com/en_US/help/topic/G200634500), [KDP Paperback Royalty](https://kdp.amazon.com/en_US/help/topic/G201834330)
- Keywords and categories (3-category change): [KDP Categories](https://kdp.amazon.com/en_US/help/topic/G200652170), [How Amazon KDP Categories and Keywords Work in 2026](https://www.ebookpbook.com/2026/06/01/kdp-categories-keywords-explained/), [Manuscript Report: KDP category selection](https://manuscriptreport.com/blog/kdp-category-selection-guide)
- KDP Select / Kindle Unlimited exclusivity: [KDP Select](https://kdp.amazon.com/en_US/help/topic/G200798990), [Reedsy: KDP Select guide](https://reedsy.com/blog/guide/kdp/kdp-select/)
