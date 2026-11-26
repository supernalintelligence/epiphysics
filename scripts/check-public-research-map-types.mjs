#!/usr/bin/env node
// Fixed, non-emitting typecheck of the real public map and its imported UI boundary.
import { createHash } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { dirname, relative, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import ts from 'typescript';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const entries = [
  'src/app/research-map/page.tsx', 'src/data/public-research-map.json',
  'src/components/research-map/ResearchMap.tsx', 'src/components/research-map/Neighborhood.tsx',
  'src/components/research-map/model.ts', 'src/components/research-map/model.test.ts',
  'src/components/research-map/focus.test.tsx',
  'src/components/home/ResearchHome.tsx',
];
const hash = raw => createHash('sha256').update(raw).digest('hex');
try {
  if (process.argv.slice(2).some(arg => arg !== '--json') || process.argv.length > 3) throw new Error('Only --json is supported');
  const configPath = resolve(root, 'tsconfig.json');
  const config = ts.readConfigFile(configPath, ts.sys.readFile);
  if (config.error) throw new Error(ts.flattenDiagnosticMessageText(config.error.messageText, '\n'));
  const parsed = ts.parseJsonConfigFileContent(config.config, ts.sys, root, { noEmit: true, incremental: false });
  const tests = ts.sys.readDirectory(resolve(root, 'src/components/research-map'), ['.ts', '.tsx'], [], ['**/*.test.ts', '**/*.test.tsx']);
  const roots = [...new Set([...entries.map(path => resolve(root, path)), ...tests,
    resolve(root, 'node_modules/next/types/global.d.ts')])];
  // Next's installed declaration supplies its CSS module contract; no generated
  // next-env file, fake dataset or replacement project is needed.
  const program = ts.createProgram(roots, parsed.options);
  const diagnostics = [...parsed.errors, ...ts.getPreEmitDiagnostics(program)];
  const files = program.getSourceFiles().map(file => file.fileName).filter(path => path.startsWith(root + '/')
    && !relative(root, path).startsWith('node_modules/')).sort();
  const report = { schema_version: 1, status: diagnostics.length ? 'failed' : 'passed', entries,
    files: Object.fromEntries(files.map(path => [relative(root, path), hash(readFileSync(path))])),
    next_css_declaration_sha256: hash(readFileSync(resolve(root, 'node_modules/next/types/global.d.ts'))),
    diagnostics: diagnostics.map(item => ({ file: item.file ? relative(root, item.file.fileName) : null,
      code: item.code, message: ts.flattenDiagnosticMessageText(item.messageText, '\n') })) };
  const raw = JSON.stringify(report);
  if (Buffer.byteLength(raw) > 65536) throw new Error('Typecheck report exceeds 64 KiB');
  console.log(raw);
  process.exitCode = diagnostics.length ? 1 : 0;
} catch (error) {
  console.error(`Public map typecheck failed: ${error.message}`);
  process.exitCode = 1;
}
