// Publication is an explicit projection of reviewed, committed catalog inputs.
// This module never opens the evidence ledger or retrieves external sources.
import assert from 'node:assert/strict';
import { createHash, randomUUID } from 'node:crypto';
import { execFileSync } from 'node:child_process';
import { constants, closeSync, fstatSync, fsyncSync, linkSync, lstatSync, mkdirSync, openSync, readSync, renameSync, unlinkSync, writeFileSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import matter from 'gray-matter';

export const POLICY_PATH = 'research/meta-representation/public-map-policy.json';
export const SNAPSHOT_PATH = 'src/data/public-research-map.json';
export const MAX_PUBLIC_BYTES = 262144;
const CATALOG_FILES = ['registry.json', 'sources-control.json', 'sources-representation.json', 'sources-retrieval.json'];
const KINDS = ['claim', 'source', 'document', 'representation', 'transformation', 'experiment'];
const CLAIM_STATUSES = ['definition', 'hypothesis', 'reported_result', 'implementation_finding', 'contested'];
const BASES = ['reported', 'inferred', 'observed'];
const EDGE_KINDS = {
  cites: [['claim'], ['source', 'document']],
  challenges: [['claim'], ['claim']],
  motivates: [['claim'], ['representation', 'transformation', 'experiment']],
  compares: [['experiment'], ['representation']],
  transforms: [['transformation'], ['representation']],
  depends_on: [KINDS, KINDS],
  implements: [['document'], ['representation', 'transformation']],
};
const LIMITS = [
  'This is a reviewed public selection, not the complete research catalog. A citation does not certify that a claim is true.',
  'External sources are bibliographic references; article bytes were not archived by this map. Publication and review dates are not collection receipts.',
  'Claim status and basis are curator attributions. Observed local implementation or synthetic results do not establish predictive advantage or independent execution assurance.',
  'Proposed experiment and representation nodes describe catalog concepts, not the completion status of associated runs. Challenges may describe qualifications or competing mechanisms.',
  'The source commit and document digests identify retained local bytes. They are not independent timestamps or evidence of historical availability.',
];
const compare = (a, b) => a < b ? -1 : a > b ? 1 : 0;
export const sha256 = value => createHash('sha256').update(value).digest('hex');
export function canonical(value) {
  if (Array.isArray(value)) return `[${value.map(canonical).join(',')}]`;
  if (value !== null && typeof value === 'object') {
    return `{${Object.keys(value).sort(compare).map(key => `${JSON.stringify(key)}:${canonical(value[key])}`).join(',')}}`;
  }
  return JSON.stringify(value);
}

function object(value, label) {
  assert.ok(value && typeof value === 'object' && !Array.isArray(value), `${label} must be an object`);
}
function fields(value, required, optional = [], label = 'record') {
  object(value, label);
  assert.ok(required.every(key => Object.hasOwn(value, key)), `${label} is missing required fields`);
  assert.ok(Object.keys(value).every(key => [...required, ...optional].includes(key)), `${label} contains unapproved fields`);
}
function text(value, label, cap = 4096) {
  assert.ok(typeof value === 'string' && value.trim() && Buffer.byteLength(value) <= cap
    && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/u.test(value), `Invalid ${label}`);
  return value;
}
function id(value) {
  assert.ok(typeof value === 'string' && /^[A-Za-z0-9_-]{1,100}$/.test(value), 'Invalid node ID');
  return value;
}
function date(value, label, partial = false) {
  const pattern = partial ? /^\d{4}(?:-\d{2}(?:-\d{2})?)?$/ : /^\d{4}-\d{2}-\d{2}$/;
  assert.ok(typeof value === 'string' && pattern.test(value), `Invalid ${label}`);
  const complete = value + (value.length === 4 ? '-01-01' : value.length === 7 ? '-01' : '');
  const parsed = new Date(`${complete}T00:00:00Z`);
  assert.ok(Number.isFinite(+parsed) && parsed.toISOString().slice(0, 10) === complete, `Invalid ${label}`);
  return value;
}
function externalHref(value) {
  text(value, 'source URL', 2048);
  assert.ok(!/[\s\\]/u.test(value), 'Unsafe source URL');
  const url = new URL(value);
  assert.ok(url.protocol === 'https:' && url.hostname && !url.username && !url.password, 'Source URL must be credential-free HTTPS');
  assert.equal(url.href, value, 'Source URL must be canonical');
  return value;
}
function documentPath(value) {
  assert.ok(typeof value === 'string' && /^docs\/(research|theory|experiments)\/[A-Za-z0-9_-]+(?:\/[A-Za-z0-9_-]+)*\.md$/.test(value),
    'Document path is not an approved public Markdown path');
  assert.ok(!value.split('/').some(part => /^(?:planning|private|internal|drafts?)$/i.test(part)), 'Private document path is forbidden');
  return value;
}
function documentHref(path) {
  return `/${documentPath(path).slice(5, -3).replace(/\/index$/, '')}`;
}

export function readRegular(root, relative, cap = 1_048_576) {
  assert.ok(!relative.startsWith('/') && !relative.includes('\\') && relative.split('/').every(p => p && p !== '.' && p !== '..'), 'Invalid local input path');
  let path = resolve(root);
  for (const part of relative.split('/')) {
    path = join(path, part);
    assert.ok(!lstatSync(path).isSymbolicLink(), 'Symlink inputs are forbidden');
  }
  const fd = openSync(path, constants.O_RDONLY | (constants.O_NOFOLLOW || 0) | (constants.O_NONBLOCK || 0));
  try {
    const before = fstatSync(fd);
    assert.ok(before.isFile() && before.size <= cap, 'Input must be a bounded regular file');
    const buffer = Buffer.alloc(cap + 1);
    let length = 0, amount;
    while (length < buffer.length && (amount = readSync(fd, buffer, length, buffer.length - length, null)) > 0) length += amount;
    const raw = buffer.subarray(0, length);
    const after = fstatSync(fd);
    assert.ok(raw.length <= cap && before.ino === after.ino && before.size === after.size && before.mtimeMs === after.mtimeMs,
      'Input changed or exceeded its bound');
    return raw;
  } finally { closeSync(fd); }
}

// Fixed argument arrays, no inherited Git config/environment, no lazy fetch or transports.
function git(root, args, cap = 1_048_576) {
  return execFileSync('git', ['--no-replace-objects', '--literal-pathspecs', '-c', 'protocol.allow=never', '-C', resolve(root), ...args], {
    env: { PATH: '/usr/bin:/bin:/usr/local/bin', LC_ALL: 'C', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null',
      GIT_OPTIONAL_LOCKS: '0', GIT_NO_LAZY_FETCH: '1', GIT_ALLOW_PROTOCOL: '', GIT_PROTOCOL_FROM_USER: '0' },
    timeout: 10_000, maxBuffer: cap, stdio: ['ignore', 'pipe', 'pipe'],
  });
}
function committedFile(root, commit, path) {
  const entry = git(root, ['ls-tree', '-z', commit, '--', path], 8192).toString('utf8');
  const match = /^(100644|100755) blob ([a-f0-9]{40})\t([^\0]+)\0$/.exec(entry);
  assert.ok(match && match[3] === path, `Missing committed regular file: ${path}`);
  return git(root, ['cat-file', 'blob', match[2]]);
}
function committedAndCurrent(root, commit, path) {
  const raw = committedFile(root, commit, path);
  assert.ok(raw.equals(readRegular(root, path)), `Current input differs from pinned commit: ${path}; review and explicitly export a new snapshot`);
  return raw;
}
function json(raw) { return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(raw)); }
function publishedDocument(raw, label) {
  const { data } = matter(new TextDecoder('utf-8', { fatal: true }).decode(raw));
  text(data.title, `${label} title`);
  assert.ok((data.draft === undefined || data.draft === false) && (data.private === undefined || data.private === false)
    && (data.published === undefined || data.published === true) && (data.visibility === undefined || data.visibility === 'public')
    && !['draft', 'private', 'internal'].includes(data.status), `Document is not published: ${label}`);
}

function policyShape(policy) {
  fields(policy, ['schemaVersion', 'sourceCommit', 'catalogFiles', 'nodeIds', 'documents'], [], 'publication policy');
  assert.equal(policy.schemaVersion, 1);
  assert.match(policy.sourceCommit, /^[a-f0-9]{40}$/);
  assert.deepEqual(policy.catalogFiles, CATALOG_FILES, 'Only the four reviewed catalog files are allowed');
  assert.ok(Array.isArray(policy.nodeIds) && policy.nodeIds.length > 0 && policy.nodeIds.length <= 100, 'Invalid public node count');
  policy.nodeIds.forEach(id);
  assert.equal(new Set(policy.nodeIds).size, policy.nodeIds.length, 'Duplicate approved node ID');
  object(policy.documents, 'document allowlist');
  for (const [key, binding] of Object.entries(policy.documents)) {
    assert.ok(policy.nodeIds.includes(id(key)), 'Document must be explicitly approved');
    fields(binding, ['repoPath', 'href'], [], 'document binding');
    assert.equal(binding.href, documentHref(binding.repoPath), 'Document route does not match its approved path');
  }
}

export function createPublicMap(root, { publishedSlugs } = {}) {
  const policy = json(readRegular(root, POLICY_PATH, 65536));
  policyShape(policy);
  const commit = git(root, ['rev-parse', '--verify', `${policy.sourceCommit}^{commit}`], 128).toString().trim();
  assert.equal(commit, policy.sourceCommit, 'Source must identify the exact retained commit');
  const files = policy.catalogFiles.map(name => {
    const raw = committedAndCurrent(root, commit, `research/meta-representation/${name}`);
    return { name, hash: sha256(raw), value: json(raw) };
  });
  const registry = files[0].value;
  fields(registry, ['schema_version', 'nodes', 'edges'], [], 'registry');
  assert.equal(registry.schema_version, 1);
  assert.ok(Array.isArray(registry.nodes) && Array.isArray(registry.edges), 'Invalid registry arrays');
  const inputNodes = [...registry.nodes];
  for (const { value } of files.slice(1)) {
    assert.ok(Array.isArray(value) && value.every(node => node?.kind === 'source'), 'Source catalogs must contain source nodes');
    inputNodes.push(...value);
  }
  assert.ok(inputNodes.length <= 5000 && registry.edges.length <= 20000, 'Catalog exceeds bounds');
  const byId = new Map();
  for (const node of inputNodes) {
    object(node, 'catalog node');
    assert.ok(!byId.has(id(node.id)), 'Duplicate catalog node ID');
    assert.ok(KINDS.includes(node.kind), 'Unknown node kind');
    byId.set(node.id, node);
  }
  const nodes = policy.nodeIds.map(key => {
    const node = byId.get(key);
    assert.ok(node, `Missing approved node: ${key}`);
    const common = { id: id(node.id), kind: node.kind, title: text(node.title, 'node title', 512) };
    if (node.kind === 'claim') {
      fields(node, ['id', 'kind', 'title', 'statement', 'status', 'basis'], [], `claim ${key}`);
      assert.ok(CLAIM_STATUSES.includes(node.status) && BASES.includes(node.basis), 'Invalid claim status or basis');
      return { ...common, statement: text(node.statement, 'claim statement'), status: node.status, basis: node.basis };
    }
    if (node.kind === 'source') {
      fields(node, ['id', 'kind', 'title', 'url', 'date', 'date_type', 'reviewed_on', 'bibliographic_only', 'claim_supported', 'limitation'],
        ['first_submitted', 'reprint_date', 'revision', 'version_reviewed'], `source ${key}`);
      assert.equal(node.bibliographic_only, true, 'Only bibliographic sources are permitted');
      text(node.claim_supported, 'bibliographic support description');
      if (node.date === null) assert.ok(['undated_live_documentation', 'mutable_main_revision_unverified'].includes(node.date_type), 'Undated source must say why');
      else date(node.date, 'source date', true);
      return { ...common, href: externalHref(node.url), date: node.date, dateType: text(node.date_type, 'date type', 128),
        reviewedOn: date(node.reviewed_on, 'source review date'), bibliographicOnly: true,
        limitations: [text(node.limitation, 'source limitation')] };
    }
    if (node.kind === 'document') {
      fields(node, ['id', 'kind', 'title', 'repo_path'], [], `document ${key}`);
      const binding = policy.documents[key];
      assert.ok(binding && binding.repoPath === node.repo_path, `Document lacks an exact approved route: ${key}`);
      const raw = committedAndCurrent(root, commit, documentPath(node.repo_path));
      publishedDocument(raw, key);
      if (publishedSlugs) assert.ok(publishedSlugs.has(binding.href.slice(1)), `Approved document route is absent from built content: ${binding.href}`);
      return { ...common, href: binding.href, contentHash: sha256(raw), commit };
    }
    fields(node, ['id', 'kind', 'title', 'status'], [], `proposal ${key}`);
    assert.equal(node.status, 'proposed', 'Proposal status must remain proposed');
    return { ...common, status: 'proposed' };
  }).sort((a, b) => compare(a.id, b.id));
  assert.deepEqual(Object.keys(policy.documents).sort(compare), nodes.filter(n => n.kind === 'document').map(n => n.id), 'Document allowlist differs from selected documents');
  const selected = new Set(nodes.map(n => n.id));
  const edges = [], seen = new Set();
  for (const edge of registry.edges) {
    fields(edge, ['source', 'target', 'type'], [], 'relationship');
    const source = byId.get(edge.source), target = byId.get(edge.target), kinds = EDGE_KINDS[edge.type];
    assert.ok(source && target && kinds && kinds[0].includes(source.kind) && kinds[1].includes(target.kind), 'Invalid relationship endpoints or type');
    const key = canonical([edge.source, edge.target, edge.type]);
    assert.ok(!seen.has(key), 'Duplicate relationship');
    seen.add(key);
    if (selected.has(edge.source) && selected.has(edge.target)) edges.push({ source: edge.source, target: edge.target, type: edge.type });
  }
  edges.sort((a, b) => compare(a.source, b.source) || compare(a.target, b.target) || compare(a.type, b.type));
  for (const node of nodes) {
    assert.ok(edges.some(edge => edge.source === node.id || edge.target === node.id), `Approved node has no public relationship: ${node.id}`);
    if (node.kind === 'claim') assert.ok(edges.some(edge => edge.source === node.id && edge.type === 'cites'), `Claim has no public citation: ${node.id}`);
  }
  const payload = { schemaVersion: 1, sourceCommit: commit,
    catalogHash: sha256(canonical({ policy, files: files.map(({ name, hash }) => ({ name, hash })) })), nodes, edges, limits: LIMITS };
  const snapshot = { ...payload, payloadHash: sha256(canonical(payload)) };
  serializePublicMap(snapshot); // Bound the complete exported artifact, including its hash and formatting.
  return snapshot;
}

export function serializePublicMap(snapshot) {
  const raw = Buffer.from(`${JSON.stringify(snapshot, null, 2)}\n`, 'utf8');
  assert.ok(raw.length <= MAX_PUBLIC_BYTES, 'Complete serialized public map exceeds byte budget');
  return raw;
}

function outputDirectory(root) {
  let path = resolve(root);
  const rootInfo = lstatSync(path);
  assert.ok(rootInfo.isDirectory() && !rootInfo.isSymbolicLink(), 'Export root must be a regular directory');
  for (const part of dirname(SNAPSHOT_PATH).split('/')) {
    path = join(path, part);
    try { mkdirSync(path); } catch (error) { if (error.code !== 'EEXIST') throw error; }
    const info = lstatSync(path);
    assert.ok(info.isDirectory() && !info.isSymbolicLink(), 'Export parent must be a non-symlink directory');
  }
  return path;
}

// An initial export is exclusive. Replacing a reviewed version requires its exact raw-byte hash.
// Temporary bytes are fully written before an atomic name change; existing hardlink targets are not edited.
export function writePublicMap(root, snapshot, { replaceHash } = {}) {
  const raw = serializePublicMap(snapshot); // No output path is created on an oversized result.
  if (replaceHash !== undefined) assert.match(replaceHash, /^[a-f0-9]{64}$/, 'Replacement needs the previous raw snapshot SHA-256');
  const directory = outputDirectory(root), path = join(resolve(root), SNAPSHOT_PATH);
  let original;
  try { original = lstatSync(path); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  if (original) {
    assert.ok(original.isFile() && !original.isSymbolicLink(), 'Existing export must be a regular non-symlink file');
    assert.ok(replaceHash, 'Export already exists; reviewed replacement requires --replace=<previous-raw-sha256>');
    assert.equal(sha256(readRegular(root, SNAPSHOT_PATH, MAX_PUBLIC_BYTES)), replaceHash, 'Existing export differs from reviewed replacement hash');
  } else assert.equal(replaceHash, undefined, 'Cannot replace a missing export');
  const temporary = join(directory, `.public-map-${randomUUID()}.tmp`);
  const fd = openSync(temporary, constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | (constants.O_NOFOLLOW || 0), 0o644);
  try {
    try { writeFileSync(fd, raw); fsyncSync(fd); } finally { closeSync(fd); }
    outputDirectory(root); // Recheck that parents remain non-symlink directories before publication.
    if (original) {
      const current = lstatSync(path);
      assert.ok(current.isFile() && !current.isSymbolicLink() && current.dev === original.dev && current.ino === original.ino,
        'Export identity changed during replacement');
      assert.equal(sha256(readRegular(root, SNAPSHOT_PATH, MAX_PUBLIC_BYTES)), replaceHash, 'Export bytes changed during replacement');
      renameSync(temporary, path);
    } else {
      linkSync(temporary, path); // Exclusive final-name creation; a competing file/symlink is never overwritten.
      unlinkSync(temporary);
    }
    return raw;
  } finally {
    try { unlinkSync(temporary); } catch (error) { if (error.code !== 'ENOENT') throw error; }
  }
}

export function readPublishedSlugs(root) {
  const content = json(readRegular(root, 'public/content-data.json', 64 * 1024 * 1024));
  assert.ok(Array.isArray(content.content), 'Run content preprocessing before verifying public routes');
  return new Set(content.content.map(item => item.slug));
}

export function verifyPublicMap(root) {
  const snapshot = json(readRegular(root, SNAPSHOT_PATH, MAX_PUBLIC_BYTES));
  const expected = createPublicMap(root, { publishedSlugs: readPublishedSlugs(root) });
  assert.deepEqual(snapshot, expected, 'Public snapshot differs from approved inputs; review and explicitly export it. Verification never regenerates publication data');
  return expected;
}

export function verifyPublicMapReport(root) {
  const snapshot = verifyPublicMap(root);
  const report = {
    schemaVersion: 1, payloadHash: snapshot.payloadHash, sourceCommit: snapshot.sourceCommit,
    counts: { nodes: snapshot.nodes.length, edges: snapshot.edges.length,
      claims: snapshot.nodes.filter(node => node.kind === 'claim').length,
      publicDocuments: snapshot.nodes.filter(node => node.kind === 'document').length,
      sources: snapshot.nodes.filter(node => node.kind === 'source').length },
    checks: { explicitNodeAndFieldAllowlists: 'passed', committedAndCurrentInputIdentity: 'passed',
      publishedDocumentRoutes: 'passed', safeBibliographicURLs: 'passed', publicClaimCitations: 'passed',
      typedDirectedRelationships: 'passed', savedSnapshotMatchesDeterministicProjection: 'passed' },
    limits: [...snapshot.limits, 'This report checks the public data boundary and saved snapshot. It does not establish browser accessibility, visual quality, user behavior, scientific truth, deployment or controller acceptance.'],
  };
  assert.ok(Buffer.byteLength(canonical(report)) <= 16384, 'Verification report exceeds byte budget');
  return report;
}
