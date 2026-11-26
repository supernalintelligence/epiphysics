'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import RepresentationLattice from './RepresentationLattice';
import { researchStages } from './research-stages';
import s from './ResearchExperience.module.css';

const notes = [
  'A page published last year may have been revised yesterday. Store both the source’s claimed date and the first time our collector actually saw those bytes.',
  'A company, a model, a team, and a transaction network can all be useful entities at different scales. We want the predictive task to help choose the boundary.',
  'The question, evidence cutoff, method, probability, and outcome rule belong in one record. An independent witness is planned; today the ledger provides local integrity checks.',
  'A complex representation must earn its extra cost. Compare against a simple baseline using the same evidence, and preserve failures and corrections.',
  'AI systems can alter the environment they predict. Revision should change the next experiment while preserving the commitments and results of earlier experiments.',
];

export default function ResearchOverview() {
  const [stage, setStage] = useState(0);
  const [paused, setPaused] = useState(false);
  const [message, setMessage] = useState('');
  useEffect(() => {
    const read = () => {
      const id = new URL(window.location.href).searchParams.get('stage');
      const index = researchStages.findIndex(s => s.id === id);
      setStage(index < 0 ? 0 : index);
    };
    read(); window.addEventListener('popstate', read);
    return () => window.removeEventListener('popstate', read);
  }, []);
  const select = (i: number) => {
    setStage(i); setMessage('');
    const url = new URL(window.location.href); url.searchParams.set('stage', researchStages[i].id);
    window.history.pushState(null, '', url);
  };
  const share = async () => {
    const url = new URL(window.location.href); url.searchParams.set('stage', researchStages[stage].id);
    try { await navigator.clipboard.writeText(url.toString()); setMessage('Link copied.'); }
    catch { setMessage('Copy this page’s address to share this step.'); }
  };
  return <div className={s.site}><div className={s.container}>
    <div className={s.topline}><Link href="/">Epiphysics</Link><span>A five-step introduction</span></div>
    <section className={s.presentation}>
      <div className={s.steps} aria-label="Presentation steps">{researchStages.map((item, i) => <button className={s.step} key={item.id} aria-pressed={stage === i} onClick={() => select(i)}><span>0{i + 1}</span>{item.label}</button>)}</div>
      <div className={s.presentationGrid}>
        <div aria-live="polite"><p className={s.eyebrow}>{researchStages[stage].label} · 0{stage + 1} / 05</p><h1 className={s.title}>{researchStages[stage].title}</h1><p className={s.lead}>{researchStages[stage].description}</p><p className={s.intro}>{notes[stage]}</p></div>
        <div className={s.visual}><div className={s.visualTop}><span>Changing representations</span><button className={s.pause} aria-pressed={paused} onClick={() => setPaused(!paused)}>{paused ? 'Resume motion' : 'Pause motion'}</button></div><div className={s.canvas}><RepresentationLattice stage={stage} paused={paused} /></div><p className={s.caption}>Illustration only. Stable points; different relationships.</p></div>
      </div>
      <div className={s.actions}><button className={s.secondary} disabled={stage === 0} onClick={() => select(stage - 1)}>Previous</button>{stage < 4 ? <button className={s.primary} onClick={() => select(stage + 1)}>Next step</button> : <Link className={s.primary} href="/observatory">Inspect the example</Link>}<button className={s.secondary} onClick={share}>Copy step link</button><span className={s.fine} role="status">{message}</span></div>
    </section>
  </div></div>;
}
