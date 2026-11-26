'use client';

import { useState } from 'react';
import Link from 'next/link';
import RepresentationLattice from './RepresentationLattice';
import { researchStages } from './research-stages';
import s from './ResearchExperience.module.css';

export default function ResearchHome() {
  const [stage, setStage] = useState(1);
  const [paused, setPaused] = useState(false);
  return <div className={s.site}>
    <div className={s.container}>
      <section className={s.hero}>
        <div>
          <p className={s.eyebrow}>An open research project</p>
          <h1 className={s.title}>How should we model a changing world?</h1>
          <p className={s.lead}>Epiphysics studies whether different representations of a system help us predict what happens next.</p>
          <p className={s.intro}>We are building the means to compare them: dated observations, explicit predictions, and a record of what worked and what failed.</p>
          <div className={s.actions}><Link className={s.primary} href="/overview">An introduction</Link><Link className={s.secondary} href="/observatory">Example forecast record</Link></div>
        </div>
        <div className={s.visual}>
          <div className={s.visualTop}><span>Alternative representations</span><button className={s.pause} onClick={() => setPaused(!paused)} aria-pressed={paused}>{paused ? 'Resume' : 'Pause'}</button></div>
          <div className={s.canvas}><RepresentationLattice stage={stage} paused={paused} /></div>
          <p className={s.caption}>The points stay the same while their groupings change. An illustration, not measured data.</p>
        </div>
      </section>
      <div className={s.status}><span><strong>Software:</strong> local evidence ledger</span><span><strong>Evaluation:</strong> prospective protocol in development</span></div>
      <section className={s.section} id="method">
        <h2>The research method</h2>
        <p className={s.intro}>Epimechanics proposes a mathematical language for change. Epiphysics tests its usefulness. A representation might describe a physical system, an organization, or an AI agent; its value depends on the question being asked.</p>
        <div className={s.steps} aria-label="Research stages">{researchStages.map((item, i) => <button key={item.id} className={s.step} aria-pressed={stage === i} onClick={() => setStage(i)}>{item.label}</button>)}</div>
        <div className={s.stageDetail} aria-live="polite"><h3>{researchStages[stage].title}</h3><p>{researchStages[stage].description}</p></div>
        <Link href="/overview" className={s.secondary}>Follow the five steps</Link>
      </section>
    </div>
    <section className={s.dark}><div className={`${s.container} ${s.split}`}>
      <div><h2>Systems that change themselves</h2><p>An AI company uses its models to make decisions. Those decisions affect its resources, dependencies, and what its next models can learn. The system being predicted is partly changed by predictions made inside it.</p><p>We want to study how capability and control accumulate, how value moves between participants, and when open alternatives remain viable.</p><Link href="/research/recursive-research-program">Research program</Link></div>
      <div className={s.loop}>Models influence decisions.<br />Decisions change dependencies.<br />Dependencies shape what can be learned.<small>This is a set of mechanisms to investigate. It does not assume that concentration or decentralization is inevitable.</small></div>
    </div></section>
    <div className={s.container}>
      <section className={s.section}><h2>Current work</h2>
        <div className={s.cards}>
          <article className={s.card}><span className={s.badge}>Implemented</span><h3><Link href="/observatory">Evidence and forecast ledger</Link></h3><p>Source versions, snapshots, predictions, outcomes, and corrections. The worked example shows the format with synthetic data.</p></article>
          <article className={s.card}><span className={s.badge}>Protocol draft</span><h3><Link href="/experiments/prospective-observatory">Comparing representations</Link></h3><p>A plan for testing simpler and learned representations on the same future questions, with costs and failures included.</p></article>
          <article className={s.card}><span className={s.badge}>Next component</span><h3><Link href="/research/recursive-research-program#temporal-evidence">Independent timestamps</Link></h3><p>Witnesses for when records existed, alongside an archive of what they contained. Local hashes alone cannot establish this.</p></article>
        </div>
      </section>
      <section className={s.closing}><div className={s.split}><div><h2>Contribute a question or a result</h2><p className={s.intro}>A clean source, a reproducible comparison, or a correction is useful whether or not you agree with the theory.</p><div className={s.actions}><a className={s.primary} href="https://github.com/supernalintelligence/epiphysics/issues">Project discussions and issues</a><Link className={s.secondary} href="/theory/series_map">Theory and assumptions</Link></div></div><div><p className={s.fine}>Ian Derrington and Parnian Barekatain<br />With AI assistance in development and review.</p><p className={s.fine}>Predictive advantage and transfer across domains remain open research questions.</p></div></div></section>
    </div>
  </div>;
}
