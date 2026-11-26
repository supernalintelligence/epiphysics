---
title: "A Science of Mathematics: Verified, Valid and Understood"
description: >-
  Machine-checked proofs separate three properties that used to arrive together: a representation
  can be verified by a checker, valid for its purpose, and understood by a person. This note
  defines the three, tests the definitions on two November 2026 cases (the Lean-certified
  Riemann Hypothesis proof and a hard-constrained model of chaotic systems), and maps them to
  the Epimechanics vocabulary. It makes no claim about the truth of the Riemann Hypothesis.
date: 2026-11-24T00:00:00.000Z
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
  - Mathematics
  - Systems thinking
tags:
  - Formal verification
  - Lean
  - Representation
  - Validation
  - Verification
tts:
  enabled: true
  provider: openai
  voice: onyx
  enableSpeed: true
  enableProgress: true
feedback:
  enabled: true
---

## Scope

This note applies the Epimechanics vocabulary to how a representation becomes accepted. Statements carry the corpus tags: **relabeling** (a known result in framework terms), **structural** (follows from the framework's definitions) and **novel** (a prediction the framework adds). The corpus contains no derivation about primes or the zeta function, and nothing here argues that Epiphysics bears on the Riemann Hypothesis.

## Three properties

Engineering separates verification (was the thing built correctly?) from validation (was the right thing built?). Machine-checked mathematics needs a third property, because a proof can pass both a checker and expert review while no person can say why it holds.

| Property | Relation | Checked by | Scales by | Fails when |
|---|---|---|---|---|
| Verified | Representation to checker | A deterministic procedure | Compute | The checker has a fault, or an axiom was added |
| Valid | Representation to referent, for a stated purpose | People or AI that hold the referent | More independent reviewers | The formal statement says something other than the intended claim |
| Understood | Representation to a reader | A person who can rebuild the argument | Compression into a form a reader can hold | The argument is too large or too unstructured to hold |

A representation can have any combination of the three. The definitions give a plain description of mathematics: **representations that can be verified by a deterministic procedure**. A science of mathematics studies how verified representations become valid and understood.

> [!sidenote] Relabeling
> The first two rows restate the standard verification and validation split. Proof assistants state the verification side as the de Bruijn criterion: a small trusted kernel checks proofs that larger, untrusted programs produce. The third row, and the observation that each property scales by a different resource, is the part the framework adds.

## Case 1: the Lean-certified Riemann Hypothesis proof

The verification details come from the joint statement of the Lean FRO and the Mathlib Initiative (21 November 2026), which is a primary source. The rest comes from news coverage and a Wikipedia current-events page dated 24 November 2026. Two further primary sources were read in part: Andrew Sutherland's verification log (page updated 24 November 2026) and a 265-page explanatory draft described below. Alpöge's own four-page note (alpo.ge/remark.pdf) and the arXiv version of the MIT paper were also read. The Lean code and the PNAS version of the paper were not, so the remaining details are provisional.

- **Verified.** Levent Alpöge released a Lean 4 formalization of about 17 million lines on 20 November 2026. The Lean FRO and Mathlib Initiative certified it a day later, citing four criteria that the Lean community had published before the claim (the Xena Project post cited in the certification carries the date 12 November 2026). The statement is Mathlib's own `RiemannHypothesis`, vetted by experts. Dozens of people reproduced the same raw proof export. Two independent tools, `comparator` and `con-leche --compare`, confirmed that the theorem proved is exactly Mathlib's statement. Several checkers in different languages accepted the export, including `con-leche` and `con-ron`, which come with a formal proof, relative to set theory, that they cannot accept a false proof. The checks ran on an inert export, out of reach of any malicious code in the Lean sources. Andrew Sutherland's log adds counts: all 175,187 modules compile, the five headline theorems use only the three standard axioms (`propext`, `Classical.choice`, `Quot.sound`), an independent sandboxed rebuild reproduced the export byte for byte, and two independently written kernels accepted the full export. Lean's default kernel took 48 hours on one thread, and its paranoid mode took 72 hours. These are measurements of replication and trust base (items 1 and 2 below).
- **Valid.** The question of whether the Lean statement is the Riemann Hypothesis went to reviewers. Kevin Buzzard raised it as the first question to ask. The imported definition and the comparison tools answer it, and people still judge that answer. The certification names this link explicitly and assigns it to expert vetting.
- **Understood.** Not yet. Daniel Litt summarized the position in two lines: the formalized proof is exceedingly likely to be correct, and no human understands it yet. Andrew Granville, James Maynard and Maksym Radziwill each commented on the lack of a readable account.

A 265-page draft shows the understanding work in progress. Michael Rubinstein commissioned it, and it is credited to three AI systems working at his behest (version 2, working draft, 22 November 2026). It explains the argument for the Riemann zeta function only. Its own abstract lists what it does not do:

- It quotes the main inequality, called (M), from the Lean development and does not prove it.
- It reduces (M) to thirteen numbered hypotheses stated in classical terms, and proves none of them outright.
- It lists 195 statements that the Lean development takes as published results, and says its attributions for them are "from memory".

So understood is being built in layers, here by an AI-written exposition commissioned by a human, and each layer states which links it has not yet closed. This note has not checked whether humans have reviewed the draft. Its length of 265 pages is consistent with Wikipedia's report that the 250,000-page figure was a joke.
- **Who validates.** The work is spread across a team that includes AI. An AI-led teardown of the proof ran in a number theory Zulip chat that Terence Tao cited.

One figure needs care. Alpöge's own note says in a footnote that he "amused myself, and hit 250,000+ pages" with an AI-written English version, and that posting it would have been a "massive unreadable travesty of slop", so he released only the Lean. Wikipedia reports that he said on 23 November that the page figure was a joke. The note itself does not call it a joke. Either way, the reading problem is 17 million lines of Lean with no written proof, and this note leaves the page count out of its arguments.

The author's own note shows the gap from the inside. He writes that he is presenting "a complete argument before having mastered a massive neighbourhood around its mathematics", that "Claude far outpaced me near the finish line", and that for parts where Claude was the expert he is "paraphrasing a slop summary, which might make zero sense", adding that the Lean "should suffice to clarify everything". So verified and valid do not require that any one person, the author included, holds the whole argument. He commits to "understand and impart understanding of this argument", and he expects it to be "massively simplified".

Terence Tao's post of 20 November 2026 gives a direct ordering on the understood axis. He lists three results from the same group, "in decreasing order of how digested the results currently are":

1. A proof of finite-time blowup for the unforced 3D Euler equations (Alpöge, Buckmaster and Coiculescu). It is human-readable and formalized in Lean.
2. A proof of finite-time blowup for the unforced 3D Navier-Stokes equations (Alpöge and Buckmaster). The paper is technically human-readable and the strategy is broadly clear: build an approximate self-similar solution numerically, then use rigorous perturbation theory to make it exact. It has a Lean formalization, and it still needs a professionally written proof.
3. The Lean-only proof of the Generalized Riemann Hypothesis.

Tao adds that in the third case there is at least a human author to ask. These are Tao's reports. This note has not checked the first two results.

The ordering shows that verified, valid and understood can be at different stages in results from one source, and that a written account is the main thing that moves a result along the understood axis.

## Case 2: a hard-constrained model of chaotic systems

An MIT News story dated 20 November 2026 describes a PNAS paper by Sunbochen Tang, Navid Azizan and Themistoklis Sapsis (MIT LIDS). The model learns an energy-like function and a boundary. A projection layer then forces the energy to decrease outside the boundary. That construction guarantees bounded trajectories over arbitrarily long forecast horizons. The authors contrast this with soft constraints, which are training penalties and carry no guarantee at test time. They report matching true outcomes on known systems while conventional models diverged. The arXiv abstract (2410.00976, version 4) adds that the learned level set gives an outer estimate of the strange attractor, and that tests used Lorenz 96 and a reduced-order Kuramoto-Sivashinsky model. The arXiv text (version 4) states one trade-off: the algebraic condition it uses is "strictly stronger" than the conditions in its Propositions 1 and 2, and it is "slightly more conservative", accepted because it can be checked and built into the model architecture. This note relies on the news story and the arXiv version. The PNAS version was not read.

The same split applies:

- **Verified by construction.** Boundedness holds for every input, including inputs the model has not seen.
- **Valid.** Whether the learned energy function and boundary fit the real system is settled against data. Bounded output does not show a correct model.

## Mapping to the framework

- **Verified uses the selection idea, not the basin.** In the glossary, extant describes a loop whose basin depth ΔV clears a perturbation ΔE. A proof object is static and has no basin, so ΔV and ΔE do not transfer. What transfers is the selection rule: a representation persists in an environment if it survives every test that environment applies. Each test here is a checker with a binary outcome, so the surviving set 𝒮(ℰ) is the set of certificates every checker accepts. A new, independently written checker widens ℰ.
- **Environments are plural.** A representation can be extant under machine checkers and fall outside the human reader's environment. The Riemann Hypothesis proof sits in that gap. Understood is a second compression: a representation small enough for a reader's capacity.
- **Valid depends on purpose.** The corpus holds that accuracy is matched to purpose and not maximized. Valid therefore reads as fit to a stated purpose, and the purpose has to be named each time the word is used.
- **The referent differs from physics.** A physical model faces measurement. A mathematical statement's referent is the theorem mathematicians intend, and it exists in their agreement. Validation in mathematics is therefore social, which is the quasi-empirical view of Lakatos.

## A related position: reality as a vector in Hilbert space

Sean Carroll's "Reality as a Vector in Hilbert Space" (arXiv:2103.09780, 2021, a contribution to a volume on quantum mechanics and fundamentality) defends one ontological claim: the world is a vector in Hilbert space evolving under the Schrödinger equation, and the laws follow from the energy spectrum of the Hamiltonian. Space, objects and fields are then emergent descriptions. This note read the abstract and the passages quoted below.

Two points from the paper bear on the three properties.

- **A thing and its representation come apart.** Carroll writes that the choice between position and momentum space "is simply a change of basis in Hilbert space, which presumably has no physical importance". The physical state is the vector, and each basis is one representation of it. This is the referent-versus-representation split used above, in a case where checking one representation does not settle the referent.
- **A usable emergent description is a rare event.** He notes that most Hamiltonians admit no local decomposition and most factorizations admit no classical limit. The descriptions we use exist only for non-generic Hamiltonians. This parallels the corpus's surviving set: usable representations are a small subset of all candidates. It does not test the Efficiency Conjecture, which concerns cost and not rarity.

> [!caveat] Where the positions differ
> Carroll's claim is ontological: the vector is reality. The corpus follows the interface view, in which X is a representation and not reality. The paper therefore supports the representation-versus-referent split as a method. It does not support the interface view, and this note takes no side between them. He also calls the reconstruction program ambitious and says it "may ultimately fail".

## What can be measured

1. **Trust base size.** The count of components whose fault would void acceptance, from a published list: the kernel, each axiom beyond the three standard ones, each use of `native_decide` or `Lean.ofReduceBool` (these extend trust to the compiler), and each checker binary.
2. **Replication.** The number of checkers that accept, and the number of distinct codebases among them. Lean's kernel and nanoda count as two codebases. Two runs of one kernel count as one.
3. **Reviewer agreement on validity.** The fraction of expert reviewers who, reading the formal statement cold, agree it expresses the intended claim. Fix the number of reviewers before the review.
4. **Explanation gap.** Certificate size divided by the size of the shortest account a reader can use to rebuild the argument.
5. **Time to understanding.** The interval between verification and the first written account that independent readers confirm.

## Open questions

- Does the time to understanding shrink as AI-assisted validation teams form, or does it grow with proof size?
- Can a proof be shaped for readers, and what does that cost in length? Or does reader capacity alone set the explanation gap?
- Case 2 imposes structure on a model so that a checkable property holds by construction. Do proofs have an analogue, where a constraint placed on the search guarantees a property the checker can confirm?
- One point touches the Representational Efficiency Conjecture: does structural regularity predict shorter proofs? Testing it needs a definition of mechanical structure distinct from compressibility. That is open question 1 in `STATE.md`. It also needs one named cost measure. Source lines and the size of the elaborated kernel term disagree, because tactic automation, hand-shortened proofs and library refactors change source length without changing the mathematics.

## What this note does not claim

- That Epimechanics or Epiphysics proves, supports or constrains the Riemann Hypothesis.
- That mathematical objects emerge from causal structure.
- That the five measurements are validated. They are definitions awaiting a first data pass.
