#!/usr/bin/env node
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createPublicMap, readPublishedSlugs, writePublicMap } from './public-research-map.mjs';

try {
  const args = process.argv.slice(2);
  if (args.length && !(args.length === 1 && /^--replace=[a-f0-9]{64}$/.test(args[0]))) {
    throw new Error('Review public-map-policy.json first; replacement requires --replace=<previous-raw-sha256>');
  }
  const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const snapshot = createPublicMap(root, { publishedSlugs: readPublishedSlugs(root) });
  writePublicMap(root, snapshot, { replaceHash: args[0]?.slice('--replace='.length) });
  console.log(`Public map explicitly exported: ${snapshot.nodes.length} reviewed nodes, ${snapshot.edges.length} relationships; ${snapshot.payloadHash}`);
} catch (error) { console.error(`Public map export refused: ${error.message}`); process.exitCode = 1; }
