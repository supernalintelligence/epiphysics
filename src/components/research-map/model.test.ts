/** @jest-environment node */
import { claimsIn, edgeKey, filterClaims, groupedEdges, immediateEdges, neighborhood,
  resolveClaim, selectionUrl, type ClaimNode, type MapEdge, type ResearchMapData } from './model';

const claims: ClaimNode[] = [
  { id: 'claim:one', kind: 'claim', title: 'Dated evidence', statement: 'Preserve exact source versions.', status: 'implementation_finding', basis: 'observed' },
  { id: 'claim:two', kind: 'claim', title: 'Uncertain model', statement: 'Representation may improve prediction.', status: 'hypothesis', basis: 'inferred' },
  { id: 'claim:three', kind: 'claim', title: 'A qualification', statement: 'A dated source does not establish truth.', status: 'contested', basis: 'reported' },
];
const edges: MapEdge[] = [
  { source: 'claim:one', target: 'source:one', type: 'cites' },
  { source: 'claim:three', target: 'claim:one', type: 'challenges' },
  { source: 'claim:one', target: 'experiment:one', type: 'motivates' },
  { source: 'document:one', target: 'claim:one', type: 'implements' },
  { source: 'experiment:one', target: 'claim:two', type: 'compares' },
  { source: 'claim:two', target: 'source:one', type: 'cites' },
];
const data: ResearchMapData = {
  schemaVersion: 1, sourceCommit: 'owned', catalogHash: 'owned', payloadHash: 'owned', limits: ['Owned fixture'],
  nodes: [...claims,
    { id: 'source:one', kind: 'source', title: 'Source', href: 'https://example.org/paper', date: null, dateType: 'publication', reviewedOn: '2026-11-26', bibliographicOnly: true, limitations: ['A citation alone is not validation.'] },
    { id: 'document:one', kind: 'document', title: 'Protocol', href: '/experiments/owned', contentHash: 'owned', commit: 'owned' },
    { id: 'experiment:one', kind: 'experiment', title: 'Future test', status: 'proposed' }], edges,
};

describe('public research map browsing', () => {
  it('searches all words across title, statement, status, and basis, without changing source order', () => {
    expect(filterClaims(claims, '  DATED observed ', 'all').map(node => node.id)).toEqual(['claim:one']);
    expect(filterClaims(claims, 'truth reported', 'all').map(node => node.id)).toEqual(['claim:three']);
    expect(filterClaims(claims, '', 'all')).toEqual(claims);
    expect(claims.map(node => node.id)).toEqual(['claim:one', 'claim:two', 'claim:three']);
  });
  it('combines the status filter with search and preserves honest zero matches', () => {
    expect(filterClaims(claims, 'dated', 'contested').map(node => node.id)).toEqual(['claim:three']);
    expect(filterClaims(claims, 'dated', 'hypothesis')).toEqual([]);
    expect(filterClaims(claims, 'unlisted phrase', 'all')).toEqual([]);
  });
  it('browses claims only, never interpreting proposal status as a result', () => {
    expect(claimsIn(data)).toEqual(claims);
    expect(filterClaims(claimsIn(data), 'proposed', 'all')).toEqual([]);
  });
  it('defaults only absent parameters and leaves invalid, empty, or non-claim IDs unresolved', () => {
    expect(resolveClaim(claims, null)).toBe(claims[0]);
    expect(resolveClaim(claims, 'claim:two')).toBe(claims[1]);
    for (const id of ['', 'unknown', 'source:one', 'CLAIM:TWO']) expect(resolveClaim(claims, id)).toBeNull();
    expect(resolveClaim([], null)).toBeNull();
  });
  it('writes a stable encoded selection URL while preserving other query parameters and fragments', () => {
    expect(selectionUrl('https://example.org/research-map?view=plain&claim=old#details', 'claim:one & two'))
      .toBe('/research-map?view=plain&claim=claim%3Aone+%26+two#details');
    const url = selectionUrl('https://example.org/research-map', 'claim:three');
    expect(resolveClaim(claims, new URL(url, 'https://example.org').searchParams.get('claim'))).toBe(claims[2]);
  });
  it('resolves a restored URL independently of the currently filtered list', () => {
    const urls = ['https://example.org/research-map', 'https://example.org/research-map?claim=claim%3Atwo', 'https://example.org/research-map?claim=claim%3Athree'];
    expect([2, 1, 0, 1].map(index => resolveClaim(claims, new URL(urls[index]).searchParams.get('claim'))?.id))
      .toEqual(['claim:three', 'claim:two', 'claim:one', 'claim:two']);
    expect(filterClaims(claims, '', 'hypothesis')).not.toContain(claims[2]);
    expect(resolveClaim(claims, 'claim:three')).toBe(claims[2]);
  });
});

describe('public research map relationship parity', () => {
  it('includes both directed endpoints without adding a second-hop connection', () => {
    const selected = immediateEdges(edges, 'claim:one');
    expect(selected).toHaveLength(4);
    expect(selected).toContainEqual({ source: 'claim:three', target: 'claim:one', type: 'challenges' });
    expect(selected).not.toContainEqual(edges[4]);
    expect(edges[0]).toEqual({ source: 'claim:one', target: 'source:one', type: 'cites' });
  });
  it('uses precisely the same edges for all text groups and the optional graph', () => {
    const selected = immediateEdges(edges, 'claim:one');
    const listed = groupedEdges(selected).flatMap(group => group.edges);
    const graph = neighborhood(data.nodes, selected, 'claim:one');
    expect(graph.edges).toBe(selected);
    expect(listed.map(edgeKey).sort()).toEqual(graph.edges.map(edgeKey).sort());
    expect(new Set(listed.map(edgeKey)).size).toBe(selected.length);
    expect(graph.nodes.map(node => node.id).sort()).toEqual(['claim:one', 'claim:three', 'document:one', 'experiment:one', 'source:one']);
    expect(graph.nodes.some(node => node.id === 'claim:two')).toBe(false);
  });
  it('represents every supported edge type once without replacing its direction or type', () => {
    const all: MapEdge[] = ['cites', 'challenges', 'motivates', 'compares', 'transforms', 'depends_on', 'implements']
      .map(type => ({ source: 'a', target: 'b', type: type as MapEdge['type'] }));
    const listed = groupedEdges(all).flatMap(group => group.edges);
    expect(listed.map(edgeKey).sort()).toEqual(all.map(edgeKey).sort());
    expect(groupedEdges(all).find(group => group.id === 'qualifications')?.edges).toEqual([all[1]]);
  });
  it('keeps an isolated claim and empty edge groups honest', () => {
    const selected = immediateEdges(edges, 'unconnected');
    expect(selected).toEqual([]);
    expect(groupedEdges(selected).every(group => group.edges.length === 0)).toBe(true);
    expect(neighborhood(data.nodes, [], 'claim:two')).toEqual({ nodes: [claims[1]], edges: [] });
  });
});
