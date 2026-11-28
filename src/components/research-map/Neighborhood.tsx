import { useId } from 'react';
import { EDGE_LABELS, edgeKey, neighborhood, type ClaimNode, type MapEdge, type MapNode } from './model';
import s from './ResearchMap.module.css';

function lines(title: string): string[] {
  const words = title.split(/\s+/);
  const result = [''];
  for (const word of words) {
    const last = result.length - 1;
    if (result[last].length + word.length > 31 && result[last]) result.push(word);
    else result[last] += (result[last] ? ' ' : '') + word;
  }
  return result.length > 2 ? [result[0], `${result[1].slice(0, 28)}…`] : result;
}

export default function Neighborhood({ nodes, edges, selected }: {
  nodes: MapNode[]; edges: MapEdge[]; selected: ClaimNode;
}) {
  const marker = useId().replace(/:/g, '');
  const graph = neighborhood(nodes, edges, selected.id);
  const neighbors = graph.nodes.filter(node => node.id !== selected.id);
  const height = Math.max(220, neighbors.length * 100 + 40);
  const centerY = height / 2;
  return <figure className={s.figure}>
    <div className={s.graphScroll} tabIndex={0} aria-label="Scrollable relationship diagram">
      <svg viewBox={`0 0 800 ${height}`} width="800" height={height} role="img" aria-labelledby={`${marker}-title ${marker}-description`}>
        <title id={`${marker}-title`}>Immediate relationships of {selected.title}</title>
        <desc id={`${marker}-description`}>Arrows follow the recorded source-to-target direction. The complete relationships and titles appear in the text lists below. Positions do not represent importance or authority.</desc>
        <defs><marker id={marker} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M 0 0 L 10 5 L 0 10 z" fill="#597564" /></marker></defs>
        {graph.edges.map((edge, index) => {
          const other = edge.source === selected.id ? edge.target : edge.source;
          const row = neighbors.findIndex(node => node.id === other);
          const y = row < 0 ? centerY : 70 + row * 100;
          const offset = (index % 3 - 1) * 8;
          const incoming = edge.target === selected.id;
          const path = other === selected.id
            ? `M 230 ${centerY - 43} C 380 ${centerY - 115}, 380 ${centerY + 115}, 230 ${centerY + 43}`
            : incoming
            ? `M 500 ${y + offset} C 410 ${y + offset}, 395 ${centerY + offset}, 295 ${centerY + offset}`
            : `M 295 ${centerY + offset} C 395 ${centerY + offset}, 410 ${y + offset}, 500 ${y + offset}`;
          return <g key={edgeKey(edge)} data-edge={edgeKey(edge)}>
            <path d={path} fill="none" stroke="#597564" strokeWidth="1.5" markerEnd={`url(#${marker})`} />
            <title>{nodes.find(node => node.id === edge.source)?.title} {EDGE_LABELS[edge.type]} {nodes.find(node => node.id === edge.target)?.title}</title>
          </g>;
        })}
        <rect x="24" y={centerY - 43} width="271" height="86" rx="3" fill="#eef3ed" stroke="#30634e" />
        <text x="42" y={centerY - 17} className={s.graphKind}>Selected claim</text>
        <text x="42" y={centerY + 6} className={s.graphTitle}>{lines(selected.title).map((line, i) => <tspan key={i} x="42" dy={i ? 18 : 0}>{line}</tspan>)}</text>
        {neighbors.map((node, index) => <g key={node.id}>
          <title>{node.title}</title>
          <rect x="500" y={32 + index * 100} width="276" height="76" rx="3" fill="#fff" stroke="#c8d1c9" />
          <text x="516" y={52 + index * 100} className={s.graphKind}>{node.kind}</text>
          <text x="516" y={73 + index * 100} className={s.graphTitle}>{lines(node.title).map((line, i) => <tspan key={i} x="516" dy={i ? 17 : 0}>{line}</tspan>)}</text>
        </g>)}
      </svg>
    </div>
    <figcaption>Arrows preserve direction. Position and distance carry no evidence weight. Every relationship is listed below.</figcaption>
  </figure>;
}
