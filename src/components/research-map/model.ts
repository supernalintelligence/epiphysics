export type ClaimStatus = 'definition' | 'hypothesis' | 'reported_result' | 'implementation_finding' | 'contested';
export type ClaimBasis = 'reported' | 'inferred' | 'observed';
export type ClaimNode = {
  id: string; kind: 'claim'; title: string; statement: string;
  status: ClaimStatus; basis: ClaimBasis;
};
export type SourceNode = {
  id: string; kind: 'source'; title: string; href: string;
  date?: string | null; dateType?: string | null; reviewedOn?: string | null;
  bibliographicOnly: boolean; limitations: string[];
};
export type DocumentNode = {
  id: string; kind: 'document'; title: string; href: string; contentHash: string; commit: string;
};
export type ProposalNode = {
  id: string; kind: 'representation' | 'transformation' | 'experiment'; title: string; status: 'proposed';
};
export type MapNode = ClaimNode | SourceNode | DocumentNode | ProposalNode;
export type EdgeType = 'cites' | 'challenges' | 'motivates' | 'compares' | 'transforms' | 'depends_on' | 'implements';
export type MapEdge = { source: string; target: string; type: EdgeType };
export type ResearchMapData = {
  schemaVersion: 1; sourceCommit: string; catalogHash: string; payloadHash: string;
  nodes: MapNode[]; edges: MapEdge[]; limits: string[];
};

export const STATUS_LABELS: Record<ClaimStatus, string> = {
  definition: 'Definition', hypothesis: 'Hypothesis', reported_result: 'Reported result',
  implementation_finding: 'Implementation finding', contested: 'Contested',
};
export const BASIS_LABELS: Record<ClaimBasis, string> = {
  reported: 'Reported', inferred: 'Inferred', observed: 'Observed',
};
export const EDGE_LABELS: Record<EdgeType, string> = {
  cites: 'cites', challenges: 'qualifies or challenges', motivates: 'motivates',
  compares: 'compares', transforms: 'transforms', depends_on: 'depends on', implements: 'implements',
};
export const GROUPS = [
  { id: 'citations', title: 'Citations', description: 'Sources connected to this claim. A citation does not by itself establish the claim.' },
  { id: 'qualifications', title: 'Qualifications', description: 'Recorded limits, disagreements, and competing claims.' },
  { id: 'followups', title: 'Follow-up ideas', description: 'Proposed directions connected to the claim; this label is not an execution status.' },
  { id: 'context', title: 'Methods and context', description: 'Other explicit dependencies and research relationships.' },
] as const;
export type GroupId = typeof GROUPS[number]['id'];

export function claimsIn(data: ResearchMapData): ClaimNode[] {
  return data.nodes.filter((node): node is ClaimNode => node.kind === 'claim');
}

export function filterClaims(claims: ClaimNode[], query: string, status: ClaimStatus | 'all'): ClaimNode[] {
  const terms = query.trim().toLocaleLowerCase('en').split(/\s+/).filter(Boolean);
  return claims.filter(claim => {
    if (status !== 'all' && claim.status !== status) return false;
    const haystack = [claim.id, claim.title, claim.statement, STATUS_LABELS[claim.status], BASIS_LABELS[claim.basis]]
      .join(' ').toLocaleLowerCase('en');
    return terms.every(term => haystack.includes(term));
  });
}

export function resolveClaim(claims: ClaimNode[], parameter: string | null): ClaimNode | null {
  if (parameter === null) return claims[0] ?? null;
  return claims.find(claim => claim.id === parameter) ?? null;
}

export function selectionUrl(currentUrl: string, claimId: string): string {
  const url = new URL(currentUrl);
  url.searchParams.set('claim', claimId);
  return `${url.pathname}${url.search}${url.hash}`;
}

export function edgeKey(edge: MapEdge): string {
  return JSON.stringify([edge.source, edge.type, edge.target]);
}

export function immediateEdges(edges: MapEdge[], selectedId: string): MapEdge[] {
  return edges.filter(edge => edge.source === selectedId || edge.target === selectedId)
    .slice().sort((a, b) => edgeKey(a).localeCompare(edgeKey(b), 'en'));
}

export function edgeGroup(type: EdgeType): GroupId {
  if (type === 'cites') return 'citations';
  if (type === 'challenges') return 'qualifications';
  if (type === 'motivates') return 'followups';
  return 'context';
}

export function groupedEdges(edges: MapEdge[]): { id: GroupId; edges: MapEdge[] }[] {
  return GROUPS.map(group => ({ id: group.id, edges: edges.filter(edge => edgeGroup(edge.type) === group.id) }));
}

// The graph consumes exactly the text view's immediate edges, without adding inferred relationships.
export function neighborhood(nodes: MapNode[], edges: MapEdge[], selectedId: string) {
  const ids = new Set(edges.flatMap(edge => [edge.source, edge.target]));
  ids.add(selectedId);
  return {
    nodes: nodes.filter(node => ids.has(node.id)).slice().sort((a, b) => a.id.localeCompare(b.id, 'en')),
    edges,
  };
}
