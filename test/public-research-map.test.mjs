import assert from 'node:assert/strict';
import { execFileSync } from 'node:child_process';
import { mkdtempSync, mkdirSync, readFileSync, rmSync, symlinkSync, unlinkSync, writeFileSync, existsSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { canonical, createPublicMap, POLICY_PATH, sha256, SNAPSHOT_PATH, verifyPublicMap, verifyPublicMapReport } from '../scripts/public-research-map.mjs';

const catalogFiles = ['registry.json', 'sources-control.json', 'sources-representation.json', 'sources-retrieval.json'];
function fixture(t) {
  const root = mkdtempSync(join(tmpdir(), 'public-map-owned-'));
  t.after(() => rmSync(root, { recursive: true, force: true }));
  const env = { PATH: '/usr/bin:/bin', GIT_CONFIG_NOSYSTEM: '1', GIT_CONFIG_GLOBAL: '/dev/null',
    GIT_AUTHOR_NAME: 'Owned map fixture', GIT_AUTHOR_EMAIL: 'fixture@example.invalid',
    GIT_COMMITTER_NAME: 'Owned map fixture', GIT_COMMITTER_EMAIL: 'fixture@example.invalid' };
  const git = (...args) => execFileSync('git', ['-c', 'core.hooksPath=/dev/null', '-c', 'commit.gpgsign=false', '-C', root, ...args], { env, stdio: ['ignore', 'pipe', 'pipe'] }).toString().trim();
  const put = (path, value) => { mkdirSync(dirname(join(root, path)), { recursive: true }); writeFileSync(join(root, path), value); };
  const putJSON = (path, value) => put(path, `${JSON.stringify(value, null, 2)}\n`);
  git('init', '-q');
  const registry = { schema_version: 1, nodes: [
    { id: 'claim_a', kind: 'claim', title: 'Owned claim', statement: 'A bounded hypothesis.', status: 'hypothesis', basis: 'inferred' },
    { id: 'claim_b', kind: 'claim', title: 'Qualification', statement: 'A qualification remains visible.', status: 'contested', basis: 'reported' },
    { id: 'doc_public', kind: 'document', title: 'Public owned record', repo_path: 'docs/experiments/results/owned.md' },
    { id: 'exp_owned', kind: 'experiment', title: 'Proposed follow-up', status: 'proposed' },
    { id: 'doc_private', kind: 'document', title: 'PRIVATE_TITLE_SENTINEL', repo_path: 'docs/planning/secret.md', hidden: 'PRIVATE_EXTRA_SENTINEL' },
  ], edges: [
    { source: 'claim_a', target: 'doc_public', type: 'cites' },
    { source: 'claim_a', target: 'doc_private', type: 'cites' },
    { source: 'claim_b', target: 'source_owned', type: 'cites' },
    { source: 'claim_a', target: 'claim_b', type: 'challenges' },
    { source: 'claim_b', target: 'claim_a', type: 'challenges' },
    { source: 'claim_a', target: 'exp_owned', type: 'motivates' },
  ] };
  const sources = [{ id: 'source_owned', kind: 'source', title: 'Owned bibliography', url: 'https://example.org/paper', date: '2025',
    date_type: 'publication', reviewed_on: '2026-11-26', bibliographic_only: true,
    claim_supported: 'Limited reported claim.', limitation: 'Bibliography only; no external source bytes retained.' }];
  const policy = { schemaVersion: 1, sourceCommit: '', catalogFiles, nodeIds: ['claim_a', 'claim_b', 'source_owned', 'doc_public', 'exp_owned'],
    documents: { doc_public: { repoPath: 'docs/experiments/results/owned.md', href: '/experiments/results/owned' } } };
  put('docs/experiments/results/owned.md', '---\ntitle: Owned public result\ndraft: false\n---\nBODY_BYTES_SENTINEL\n');
  // No private document exists: exporting metadata must not even attempt to read it.
  function commit() {
    putJSON('research/meta-representation/registry.json', registry);
    putJSON('research/meta-representation/sources-control.json', sources);
    for (const name of catalogFiles.slice(2)) putJSON(`research/meta-representation/${name}`, []);
    git('add', 'research', 'docs'); git('commit', '--allow-empty', '-qm', 'Owned fixture revision');
    policy.sourceCommit = git('rev-parse', 'HEAD'); putJSON(POLICY_PATH, policy);
  }
  commit();
  putJSON('public/content-data.json', { content: [{ slug: 'experiments/results/owned' }] });
  const save = () => { const value = createPublicMap(root); putJSON(SNAPSHOT_PATH, value); return value; };
  return { root, policy, registry, sources, put, putJSON, git, commit, save };
}

test('deterministic public projection preserves direction, qualifications and limits without private/text fields', t => {
  const f = fixture(t), first = f.save();
  assert.deepEqual(createPublicMap(f.root), first);
  assert.deepEqual(verifyPublicMap(f.root), first);
  const report = verifyPublicMapReport(f.root);
  assert.deepEqual(report.counts, { nodes: 5, edges: 5, claims: 2, publicDocuments: 1, sources: 1 });
  assert.equal(report.payloadHash, first.payloadHash);
  assert.equal(report.sourceCommit, first.sourceCommit);
  assert.ok(Object.values(report.checks).every(value => value === 'passed'));
  assert.ok(Buffer.byteLength(JSON.stringify(report)) < 16384);
  const { payloadHash, ...payload } = first;
  assert.equal(payloadHash, sha256(canonical(payload)));
  assert.equal(first.nodes.filter(n => n.kind === 'claim').length, 2);
  assert.equal(first.edges.filter(e => e.type === 'challenges').length, 2);
  assert.equal(first.edges.length, 5);
  assert.ok(first.limits.length);
  const serialized = JSON.stringify(first);
  for (const secret of ['PRIVATE_', 'BODY_BYTES_SENTINEL', 'repo_path', 'repoPath', 'claim_supported', 'content_sha256', 'docs/planning']) assert.ok(!serialized.includes(secret), secret);
  assert.deepEqual(Object.keys(first.nodes.find(n => n.kind === 'document')).sort(), ['commit', 'contentHash', 'href', 'id', 'kind', 'title']);
  assert.deepEqual(Object.keys(first.nodes.find(n => n.kind === 'source')).sort(), ['bibliographicOnly', 'date', 'dateType', 'href', 'id', 'kind', 'limitations', 'reviewedOn', 'title']);
});

test('publication verification never silently adds an approved or unapproved new node', t => {
  const f = fixture(t), initial = f.save(), saved = readFileSync(join(f.root, SNAPSHOT_PATH));
  f.registry.nodes.push({ id: 'claim_new', kind: 'claim', title: 'New', statement: 'Review before publishing.', status: 'hypothesis', basis: 'inferred' });
  f.registry.edges.push({ source: 'claim_new', target: 'source_owned', type: 'cites' });
  f.commit();
  assert.ok(!createPublicMap(f.root).nodes.some(n => n.id === 'claim_new'));
  assert.throws(() => verifyPublicMap(f.root), /snapshot differs/);
  f.policy.nodeIds.push('claim_new'); f.putJSON(POLICY_PATH, f.policy);
  assert.throws(() => verifyPublicMap(f.root), /snapshot differs/);
  assert.deepEqual(readFileSync(join(f.root, SNAPSHOT_PATH)), saved);
  assert.equal(JSON.parse(saved).payloadHash, initial.payloadHash);
});

test('current catalog edits require a new reviewed committed pin', t => {
  const f = fixture(t); f.save();
  f.registry.nodes[0].statement = 'An uncommitted revised claim'; f.putJSON('research/meta-representation/registry.json', f.registry);
  assert.throws(() => verifyPublicMap(f.root), /Current input differs from pinned commit/);
});

test('current public document edits do not inherit an older digest', t => {
  const f = fixture(t); f.save(); f.put('docs/experiments/results/owned.md', '---\ntitle: Owned\n---\nChanged bytes');
  assert.throws(() => verifyPublicMap(f.root), /Current input differs from pinned commit/);
});

test('private, code, traversal and route-mismatched document bindings are refused', t => {
  for (const path of ['docs/planning/secret.md', 'engine/README.md', 'docs/research/../private.md', 'docs/research/private/secret.md']) {
    const f = fixture(t); f.policy.documents.doc_public.repoPath = path; f.putJSON(POLICY_PATH, f.policy);
    assert.throws(() => createPublicMap(f.root), /approved public|Private document|route/);
  }
  const f = fixture(t); f.policy.documents.doc_public.href = 'https://example.org/private'; f.putJSON(POLICY_PATH, f.policy);
  assert.throws(() => createPublicMap(f.root), /route/);
});

test('committed draft/private documents and missing public routes are refused', t => {
  for (const metadata of ['draft: true', 'draft: "true"', 'private: true', 'private: "true"', 'visibility: internal', 'visibility: confidential', 'published: false', 'published: "false"']) {
    const f = fixture(t); f.put('docs/experiments/results/owned.md', `---\ntitle: Owned\n${metadata}\n---\nBody`); f.commit();
    assert.throws(() => createPublicMap(f.root), /not published/);
  }
  const f = fixture(t); f.save(); f.putJSON('public/content-data.json', { content: [] });
  assert.throws(() => verifyPublicMap(f.root), /route is absent/);
});

test('selected unknown fields fail closed while excluded private nodes stay excluded', t => {
  const f = fixture(t); f.registry.nodes[0].privateNotes = 'DO_NOT_EXPORT'; f.commit();
  assert.throws(() => createPublicMap(f.root), /unapproved fields/);
});

test('unsafe bibliographic URLs cannot become clickable public links', t => {
  for (const url of ['javascript:alert(1)', 'http://example.org/', 'https://user:pass@example.org/', '//example.org', 'https://example.org/\\private']) {
    const f = fixture(t); f.sources[0].url = url; f.commit();
    assert.throws(() => createPublicMap(f.root), /URL|HTTPS/);
  }
});

test('source date precision and bibliographic-only labels are checked', t => {
  const f = fixture(t); f.sources[0].date = null; f.sources[0].date_type = 'undated_live_documentation'; f.commit();
  assert.equal(createPublicMap(f.root).nodes.find(n => n.kind === 'source').date, null);
  f.sources[0].date = '2025-02-30'; f.commit(); assert.throws(() => createPublicMap(f.root), /Invalid source date/);
  f.sources[0].date = '2025'; f.sources[0].bibliographic_only = false; f.commit();
  assert.throws(() => createPublicMap(f.root), /bibliographic/);
});

test('duplicate identifiers, duplicate edges and dangling or mistyped relationships fail', t => {
  const f = fixture(t); f.registry.nodes.push({ ...f.registry.nodes[0] }); f.commit();
  assert.throws(() => createPublicMap(f.root), /Duplicate catalog/);
  f.registry.nodes.pop(); f.registry.edges.push({ ...f.registry.edges[0] }); f.commit();
  assert.throws(() => createPublicMap(f.root), /Duplicate relationship/);
  f.registry.edges.at(-1).target = 'missing'; f.commit();
  assert.throws(() => createPublicMap(f.root), /Invalid relationship/);
  f.registry.edges.at(-1).target = 'exp_owned'; f.commit();
  assert.throws(() => createPublicMap(f.root), /Invalid relationship/);
  f.registry.edges.pop(); f.registry.edges[0].privateNotes = 'PRIVATE_EDGE_SENTINEL'; f.commit();
  assert.throws(() => createPublicMap(f.root), /unapproved fields/);
});

test('claims must retain a real public citation rather than a private-only or missing edge', t => {
  const f = fixture(t); f.registry.edges = f.registry.edges.filter(e => !(e.source === 'claim_a' && e.target === 'doc_public')); f.commit();
  assert.throws(() => createPublicMap(f.root), /Claim has no public citation/);
});

test('snapshot field injection or payload tampering is rejected without rewriting', t => {
  const f = fixture(t); const value = f.save(); value.nodes[0].text = 'PRIVATE_INJECTION'; f.putJSON(SNAPSHOT_PATH, value);
  const before = readFileSync(join(f.root, SNAPSHOT_PATH));
  assert.throws(() => verifyPublicMap(f.root), /snapshot differs/);
  assert.throws(() => verifyPublicMapReport(f.root), /snapshot differs/);
  assert.deepEqual(readFileSync(join(f.root, SNAPSHOT_PATH)), before);
  delete value.nodes[0].text; value.payloadHash = '0'.repeat(64); f.putJSON(SNAPSHOT_PATH, value);
  assert.throws(() => verifyPublicMap(f.root), /snapshot differs/);
});

test('symlink documents cannot bypass committed-file or local-path validation', t => {
  const f = fixture(t), path = join(f.root, 'docs/experiments/results/owned.md');
  const bytes = readFileSync(path); unlinkSync(path); f.put('docs/experiments/results/target.md', bytes); symlinkSync('target.md', path);
  assert.throws(() => createPublicMap(f.root), /Symlink/);
  f.commit(); assert.throws(() => createPublicMap(f.root), /committed regular file/);
});

test('a missing promisor object cannot execute a configured remote helper', t => {
  const f = fixture(t), marker = join(f.root, 'helper-called');
  f.put('owned-helper', `#!/bin/sh\n: > '${marker}'\nexit 1\n`);
  f.git('config', 'remote.origin.url', join(f.root, 'missing-remote'));
  f.git('config', 'remote.origin.promisor', 'true');
  f.git('config', 'remote.origin.partialclonefilter', 'blob:none');
  f.git('config', 'remote.origin.uploadpack', `sh ${join(f.root, 'owned-helper')}`);
  f.policy.sourceCommit = '1'.repeat(40); f.putJSON(POLICY_PATH, f.policy);
  assert.throws(() => createPublicMap(f.root));
  assert.equal(existsSync(marker), false);
});
