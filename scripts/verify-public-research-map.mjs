#!/usr/bin/env node
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { verifyPublicMapReport } from './public-research-map.mjs';

try {
  const args = process.argv.slice(2);
  if (args.length && !(args.length === 1 && args[0] === '--json')) throw new Error('Only the optional --json argument is supported');
  const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
  const report = verifyPublicMapReport(root);
  console.log(args[0] === '--json' ? JSON.stringify(report)
    : `Public map verified without regeneration: ${report.counts.nodes} approved nodes, ${report.counts.edges} relationships and published document routes.`);
} catch (error) { console.error(`Public map verification failed: ${error.message}`); process.exitCode = 1; }
