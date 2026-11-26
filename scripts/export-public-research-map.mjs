#!/usr/bin/env node
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createPublicMap, readPublishedSlugs, SNAPSHOT_PATH } from './public-research-map.mjs';

try {
  if (process.argv.length !== 2) throw new Error('This command takes no arguments; review public-map-policy.json first');
  const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const snapshot = createPublicMap(root, { publishedSlugs: readPublishedSlugs(root) });
  const path = resolve(root, SNAPSHOT_PATH);
  mkdirSync(dirname(path), { recursive: true });
  writeFileSync(path, `${JSON.stringify(snapshot, null, 2)}\n`, { mode: 0o644 });
  console.log(`Public map explicitly exported: ${snapshot.nodes.length} reviewed nodes, ${snapshot.edges.length} relationships; ${snapshot.payloadHash}`);
} catch (error) { console.error(`Public map export refused: ${error.message}`); process.exitCode = 1; }
