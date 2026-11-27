'use client';

import { useEffect, useId, useMemo, useRef, useState } from 'react';
import Link from 'next/link';
import Neighborhood from './Neighborhood';
import { BASIS_LABELS, EDGE_LABELS, GROUPS, STATUS_LABELS, claimsIn, edgeKey, filterClaims,
  groupedEdges, immediateEdges, resolveClaim, selectionUrl, type ClaimStatus, type MapNode, type ResearchMapData } from './model';
import s from './ResearchMap.module.css';

const statusMeaning: Record<ClaimStatus, string> = {
  definition: 'A declared meaning; empirical usefulness needs a separate test.',
  hypothesis: 'A proposed relationship that needs a discriminating test.',
  reported_result: 'A recorded result whose scope belongs to its linked evidence.',
  implementation_finding: 'A finding about a particular implementation and its checked scope.',
  contested: 'A claim with a documented qualification or disagreement.',
};

function NodeDetails({ node }: { node: MapNode }) {
  if (node.kind === 'source') return <div className={s.nodeDetails}>
    <p>{node.bibliographicOnly ? 'Bibliographic source' : 'Source'}{node.date ? <> · {node.dateType ? node.dateType.replace(/_/g, ' ') : 'Date'}: <time dateTime={node.date}>{node.date}</time></> : ' · Date not recorded'}{node.reviewedOn && <> · Reviewed <time dateTime={node.reviewedOn}>{node.reviewedOn}</time></>}</p>
    {node.limitations.length > 0 && <ul>{node.limitations.map((limit, index) => <li key={index}>{limit}</li>)}</ul>}
  </div>;
  if (node.kind === 'document') return <div className={s.nodeDetails}>
    <p>Public document · recorded at commit <code title={node.commit}>{node.commit.slice(0, 10)}</code></p>
    <details><summary>Document identity</summary><p className={s.hash}>Content SHA-256: {node.contentHash}<br />Commit: {node.commit}</p></details>
  </div>;
  if (node.kind === 'claim') return <div className={s.nodeDetails}><p>{STATUS_LABELS[node.status]} · {BASIS_LABELS[node.basis]} basis</p><p>{node.statement}</p></div>;
  return <p className={s.nodeDetails}>Proposed {node.kind}. This catalog label does not establish that an experiment or transformation ran.</p>;
}

export default function ResearchMap({ data }: { data: ResearchMapData }) {
  const claims = useMemo(() => claimsIn(data), [data]);
  const [parameter, setParameter] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<ClaimStatus | 'all'>('all');
  const [showGraph, setShowGraph] = useState(false);
  const selectedHeading = useRef<HTMLHeadingElement>(null);
  const focusDetailAfterSelection = useRef(false);
  const diagramId = useId();
  const selected = resolveClaim(claims, parameter);
  const visible = filterClaims(claims, query, status);
  const selectedEdges = selected ? immediateEdges(data.edges, selected.id) : [];
  const groups = groupedEdges(selectedEdges);
  const byId = new Map(data.nodes.map(node => [node.id, node]));
  const statuses = Object.keys(STATUS_LABELS).filter(value => claims.some(claim => claim.status === value)) as ClaimStatus[];

  useEffect(() => {
    const sync = () => setParameter(new URL(window.location.href).searchParams.get('claim'));
    sync();
    window.addEventListener('popstate', sync);
    return () => window.removeEventListener('popstate', sync);
  }, []);

  useEffect(() => {
    if (focusDetailAfterSelection.current) {
      selectedHeading.current?.focus();
      focusDetailAfterSelection.current = false;
    }
  }, [parameter]);

  function selectClaim(id: string, moveFocusToDetail = false) {
    if (new URL(window.location.href).searchParams.get('claim') !== id) {
      window.history.pushState(null, '', selectionUrl(window.location.href, id));
    }
    focusDetailAfterSelection.current = moveFocusToDetail;
    setParameter(id);
  }
  function clearFilters() { setQuery(''); setStatus('all'); }
  function endpoint(id: string) {
    const node = byId.get(id);
    if (!node) return <span>Unlisted node ({id})</span>;
    if (node.id === selected?.id) return <strong>{node.title}</strong>;
    if (node.kind === 'claim') return <button className={s.textButton} onClick={() => selectClaim(node.id, true)}>{node.title}</button>;
    if (node.kind === 'document' || node.kind === 'source') return <Link href={node.href}>{node.title}</Link>;
    return <span>{node.title}</span>;
  }

  return <div className={s.site}>
    <div className={s.container}>
      <nav className={s.breadcrumb} aria-label="Breadcrumb"><Link href="/research">Research</Link><span aria-hidden="true">/</span><span>Research map</span></nav>
      <div className={s.header}>
        <p className={s.eyebrow}>Claims, evidence, and open questions</p>
        <h1>Research map</h1>
        <p className={s.lead}>Follow a claim to its sources, qualifications, and possible next tests.</p>
        <p className={s.scope}>A curated view of the research record. Read the statement and its basis together; connections show recorded relationships, not a score of truth or authority.</p>
      </div>
      <div className={s.workspace}>
        <aside className={s.browser} aria-labelledby="browse-heading">
          <h2 id="browse-heading">Browse claims</h2>
          <div className={s.filters}>
            <label htmlFor="claim-search">Search claims</label>
            <input id="claim-search" type="search" value={query} onChange={event => setQuery(event.target.value)} placeholder="A question, topic, or claim ID" />
            <label htmlFor="claim-status">Status</label>
            <select id="claim-status" value={status} onChange={event => setStatus(event.target.value as ClaimStatus | 'all')}>
              <option value="all">All statuses</option>{statuses.map(value => <option value={value} key={value}>{STATUS_LABELS[value]}</option>)}
            </select>
            <div className={s.filterSummary}><p role="status">{visible.length} of {claims.length} claims</p>{(query || status !== 'all') && <button className={s.textButton} onClick={clearFilters}>Clear filters</button>}</div>
          </div>
          {visible.length ? <ul className={s.claimList}>{visible.map(claim => <li key={claim.id}>
            <button onClick={() => selectClaim(claim.id)} aria-pressed={selected?.id === claim.id} aria-controls="selected-claim" className={s.claimButton}>
              <span className={s.claimTitle}>{claim.title}</span><span className={s.claimStatus}>{STATUS_LABELS[claim.status]} · {BASIS_LABELS[claim.basis]}</span>
            </button>
          </li>)}</ul> : <p className={s.empty}>No claims match these filters. Try another phrase or clear the filters.</p>}
        </aside>
        <section className={s.detail} id="selected-claim" aria-labelledby="selected-heading">
          {selected ? <>
            {!visible.some(claim => claim.id === selected.id) && <p className={s.filterNotice}>This selected claim is outside the current filters. <button className={s.textButton} onClick={clearFilters}>Show all claims</button></p>}
            <div className={s.detailTop}><span className={s.eyebrow}>Selected claim</span><Link href={`/research-map?claim=${encodeURIComponent(selected.id)}`} className={s.permalink}>Permanent link</Link></div>
            <h2 id="selected-heading" ref={selectedHeading} tabIndex={-1} aria-live="polite">{selected.title}</h2>
            <div className={s.badges}><span className={s.badge}>{STATUS_LABELS[selected.status]}</span><span>Basis: {BASIS_LABELS[selected.basis]}</span></div>
            <p className={s.statement}>{selected.statement}</p>
            <p className={s.statusMeaning}>{statusMeaning[selected.status]}</p>
            <p className={s.claimId}>Claim ID: <code>{selected.id}</code></p>
            <div className={s.relationshipHeading}><h3>Connected evidence and ideas</h3><button className={s.diagramButton} aria-expanded={showGraph} aria-controls={diagramId} onClick={() => setShowGraph(value => !value)}>{showGraph ? 'Hide diagram' : 'Show diagram'}</button></div>
            <div id={diagramId} hidden={!showGraph}>{showGraph && <Neighborhood nodes={data.nodes} edges={selectedEdges} selected={selected} />}</div>
            {groups.map(group => {
              const definition = GROUPS.find(item => item.id === group.id)!;
              return <section className={s.relationshipGroup} key={group.id} aria-labelledby={`group-${group.id}`}>
                <h4 id={`group-${group.id}`}>{definition.title} <span>({group.edges.length})</span></h4>
                <p className={s.groupDescription}>{definition.description}</p>
                {group.edges.length ? <ul className={s.relationships}>{group.edges.map(edge => {
                  const other = byId.get(edge.source === selected.id ? edge.target : edge.source);
                  return <li key={edgeKey(edge)} data-edge={edgeKey(edge)}>
                    <p className={s.direction}>{endpoint(edge.source)} <span className={s.relation}>{EDGE_LABELS[edge.type]} <span aria-hidden="true">→</span></span> {endpoint(edge.target)}</p>
                    {other && <NodeDetails node={other} />}
                  </li>;
                })}</ul> : <p className={s.noRelationships}>None recorded in this public map.</p>}
              </section>;
            })}
          </> : <div className={s.empty}><h2 id="selected-heading">{parameter !== null ? 'Claim not found' : 'No claims are available'}</h2><p>{parameter !== null ? 'This link does not identify a claim in the current public map. Select a claim from the list.' : 'The public claim catalog is empty.'}</p>{claims[0] && <button className={s.diagramButton} onClick={() => selectClaim(claims[0].id, true)}>Open the first claim</button>}</div>}
        </section>
      </div>
      <footer className={s.provenance}>
        <h2>About this map</h2>
        <ul>{data.limits.map((limit, index) => <li key={index}>{limit}</li>)}</ul>
        <p><Link href="/research/recursive-research-program">Read the research program</Link><span aria-hidden="true"> · </span><Link href="/research">Browse the research notes</Link></p>
        <details><summary>Snapshot provenance</summary><dl><dt>Source commit</dt><dd>{data.sourceCommit}</dd><dt>Catalog SHA-256</dt><dd>{data.catalogHash}</dd><dt>Payload SHA-256</dt><dd>{data.payloadHash}</dd></dl><p>These identities bind this export. They are not signatures or independent timestamps.</p></details>
      </footer>
    </div>
  </div>;
}
