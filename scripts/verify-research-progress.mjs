#!/usr/bin/env node

// Checks the reviewed homepage snapshot against its public records, not live research state.
// Update research-progress.json when accepting a new result. Keep the small status anchors;
// unrelated prose corrections do not require a homepage refresh.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import matter from 'gray-matter';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const normalize = text => text.replace(/\*\*/g, '').replace(/\s+/g, ' ').trim();

export function verifyResearchProgress(progress, records, publishedSlugs) {
  assert.match(progress.recordDate, /^\d{4}-\d{2}-\d{2}$/, 'Use the public record date');
  const evidence = new Map(progress.evidence.map(item => [item.id, item]));
  assert.equal(evidence.size, progress.evidence.length, 'Evidence IDs must be unique');
  for (const item of evidence.values()) {
    assert.match(item.href, /^\/[a-z0-9-]+(?:\/[a-z0-9-]+)*$/, `Invalid evidence link: ${item.href}`);
    const record = records.get(item.href);
    assert.ok(record, `Missing public evidence: ${item.href}`);
    assert.ok(record.data.title && record.data.draft !== true, `Evidence must be published: ${item.href}`);
    assert.ok(publishedSlugs.has(item.href.slice(1)), `Evidence missing from built content: ${item.href}`);
    assert.ok(item.requiredText.length, `Evidence needs a reviewed claim: ${item.id}`);
    for (const claim of item.requiredText) {
      assert.ok(normalize(record.content).includes(normalize(claim)),
        `Evidence changed; review the homepage claim for ${item.id}: ${claim}`);
    }
  }
  assert.deepEqual(progress.results.map(item => item.id), ['coverage', 'diagnosis'],
    'This summary covers the reviewed coverage and diagnosis records');
  for (const result of progress.results) {
    assert.ok(evidence.has(result.id), `Result has no evidence: ${result.id}`);
    assert.equal(result.status, 'completed', `Review the completion status of ${result.id}`);
    for (const field of ['label', 'value', 'measure', 'summary', 'linkLabel']) {
      assert.ok(typeof result[field] === 'string' && result[field].trim(), `Missing ${result.id}.${field}`);
    }
  }
  assert.equal(progress.next.status, 'planned', 'The linked record says the follow-up has not run');
  assert.equal(progress.next.evidenceId, 'protocol', 'The planned follow-up must link to its rules');
  assert.ok(evidence.has(progress.next.evidenceId), 'The planned follow-up has no published evidence link');
  const recordDate = new Date(records.get(evidence.get('diagnosis').href).data.date).toISOString().slice(0, 10);
  assert.equal(progress.recordDate, recordDate, 'Homepage date must match the public diagnosis record');
  return evidence.size;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try {
    const progress = JSON.parse(readFileSync(resolve(root, 'src/components/home/research-progress.json'), 'utf8'));
    const records = new Map(progress.evidence.map(item => {
      assert.match(item.href, /^\/[a-z0-9-]+(?:\/[a-z0-9-]+)*$/, 'Evidence links must be local document routes');
      return [item.href, matter(readFileSync(resolve(root, `docs${item.href}.md`), 'utf8'))];
    }));
    const content = JSON.parse(readFileSync(resolve(root, 'public/content-data.json'), 'utf8'));
    const count = verifyResearchProgress(progress, records, new Set(content.content.map(item => item.slug)));
    console.log(`Homepage evidence checked: ${count} published links, reviewed claims and planned follow-up status.`);
  } catch (error) {
    console.error(`Homepage evidence check failed: ${error.message}`);
    process.exitCode = 1;
  }
}
