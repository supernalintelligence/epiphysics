/** @jest-environment node */
import { execFileSync } from 'node:child_process';
import { resolve } from 'node:path';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { formatDate } from './dates';
import { formatDate as legacyLibraryDate } from '../dateFormatter';
import { formatDate as legacyUtilityDate } from '../../utils/dateFormatter';
import PostCard from '@/components/PostCard';
import FeaturedPosts from '@/components/home/FeaturedPosts';
import type { Post } from '@/lib/content';

jest.mock('@/components/SafeImage', () => ({ __esModule: true, default: () => null }));
jest.mock('@/components/SocialShare', () => ({ __esModule: true, default: () => null }));
jest.mock('@/lib/content/markdown', () => ({ markdownToHtml: () => '' }));

const samples = [
  ['2026-11-26T00:00:00.000Z', 'November 26, 2026'],
  ['2026-11-26T23:30:00Z', 'November 26, 2026'],
  ['2026-03-01T00:00:00Z', 'March 1, 2026'],
  ['2026-11-26', 'November 26, 2026'],
  ['2024-02-29', 'February 29, 2024'],
  ['2026-01-01T00:30:00+14:00', 'December 31, 2025'],
  ['2026-12-31T23:30:00-08:00', 'January 1, 2027'],
  ['2026-03-08T01:30:00-08:00', 'March 8, 2026'],
  ['2026-11-26T23:30:00', 'November 26, 2026'],
  ['2026-11-26T23:59:59.999999999Z', 'November 26, 2026'],
];

const invalid = ['not a date', 'May 1, 2026', '2026-02-29', '2024-02-30', '2026-00-01', '2026-13-01',
  '2026-04-31T12:00:00Z', '2026-11-26T24:00:00Z', '2026-11-26T00:60:00Z', '2026-11-26T00:00:60Z',
  '2026-11-26T00:00:00+25:00'];

describe('UTC publication calendar', () => {
  test.each(samples)('formats %s as %s', (input, expected) => {
    expect(formatDate(input)).toBe(expected);
  });

  test.each(invalid)('preserves invalid or unsupported input %s without normalization', input => {
    expect(formatDate(input)).toBe(input);
  });

  test('missing values remain empty and legacy imports share the same policy', () => {
    expect(formatDate(null)).toBe('');
    expect(formatDate(undefined)).toBe('');
    expect(formatDate('')).toBe('');
    expect(formatDate(42 as unknown as string)).toBe('');
    expect(legacyLibraryDate).toBe(formatDate);
    expect(legacyUtilityDate).toBe(formatDate);
  });

  test('preserves short, compact and month presentations under the UTC policy', () => {
    const input = '2026-01-01T00:30:00+14:00';
    expect(formatDate(input, 'short')).toBe('Dec 31, 2025');
    expect(formatDate(input, 'compact')).toBe('Dec 31');
    expect(formatDate(input, 'month')).toBe('December 2025');
  });

  test.each([
    ['midnight ISO string', '2026-11-26T00:00:00Z'], ['late ISO string', '2026-11-26T23:30:00Z'],
    ['midnight Date object', new Date('2026-11-26T00:00:00Z')], ['late Date object', new Date('2026-11-26T23:30:00Z')],
  ])('real post and featured cards render UTC publication date from %s', (_label, date) => {
    // The existing loader's declared string type also carries Date at runtime.
    const post = { slug: 'owned-date', metadata: { title: 'Owned date', date } } as Post;
    const card = renderToStaticMarkup(React.createElement(PostCard, { post, section: 'research', imagePath: null }));
    expect(card).toContain('<span class="date">Nov 26, 2026</span>');
    const featured = renderToStaticMarkup(React.createElement(FeaturedPosts, {
      title: 'Owned posts', posts: { research: [post] },
      categories: { kids_corner: {}, cerebral_songs: {}, fiction: {}, projects: {} },
    }));
    expect(featured).toContain('>Nov 26</span>');
    expect(featured).not.toContain('Nov 25');
  });

  test('Date instances preserve UTC presentation, invalid values and legacy entry points', () => {
    const instant = new Date('2026-01-01T00:30:00+14:00');
    for (const formatter of [formatDate, legacyLibraryDate, legacyUtilityDate]) {
      expect(formatter(instant)).toBe('December 31, 2025');
      expect(formatter(instant, 'short')).toBe('Dec 31, 2025');
      expect(formatter(instant, 'compact')).toBe('Dec 31');
      expect(formatter(instant, 'month')).toBe('December 2025');
      expect(formatter(new Date(NaN))).toBe('Invalid Date');
    }
    expect(instant.toISOString()).toBe('2025-12-31T10:30:00.000Z');
  });

  test('real frontmatter parser Date values retain their dates in all three timezones', () => {
    const root = resolve(__dirname, '../../..');
    const script = `
      const fs = require('node:fs'), ts = require('typescript'), esbuild = require('esbuild');
      require.extensions['.ts'] = (module, filename) => module._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
        compilerOptions: { module: ts.ModuleKind.CommonJS }
      }).outputText, filename);
      const {formatDate} = require('./src/lib/utils/dates.ts');
      // Bundle the actual parser export with the installed ESM dependencies;
      // do not replace its parser or invoke the full filesystem HTML renderer.
      const bundled = esbuild.buildSync({stdin: {contents: 'export { parseFrontmatter } from "./src/lib/content/markdown";',
        resolveDir: process.cwd(), loader: 'ts'}, bundle: true, write: false, platform: 'node', format: 'cjs', logLevel: 'silent'});
      const loaded = {exports: {}};
      new Function('module', 'exports', 'require', bundled.outputFiles[0].text)(loaded, loaded.exports, require);
      const texts = ['docs/applications/costly_signaling.md', 'docs/experiments/retrieval-fixed-clause-probe.md'].map(path => fs.readFileSync(path, 'utf8'));
      texts.push(${JSON.stringify('---\ntitle: Owned date-only value\ndate: 2024-02-29\n---\nOwned text.')} );
      console.log(JSON.stringify(texts.map(text => {
        const input = loaded.exports.parseFrontmatter(text).metadata.date;
        return {kind: Object.prototype.toString.call(input), iso: input.toISOString(), output: formatDate(input)};
      })));
    `;
    const expected = [
      {kind: '[object Date]', iso: '2026-06-11T00:00:00.000Z', output: 'June 11, 2026'},
      {kind: '[object Date]', iso: '2026-11-25T00:00:00.000Z', output: 'November 25, 2026'},
      {kind: '[object Date]', iso: '2024-02-29T00:00:00.000Z', output: 'February 29, 2024'},
    ];
    for (const TZ of ['UTC', 'America/Los_Angeles', 'Pacific/Kiritimati']) {
      const observed = JSON.parse(execFileSync(process.execPath, ['-e', script], {
        cwd: root, env: {...process.env, TZ}, encoding: 'utf8', timeout: 15000,
      }));
      expect(observed).toEqual(expected);
    }
  });

  test('separate UTC, Los Angeles and UTC+14 processes produce identical results', () => {
    const root = resolve(__dirname, '../../..');
    const inputs = [...samples.map(([input]) => input), ...invalid, null, ''];
    // Transpile the real TypeScript entry points in each fresh process. TZ is
    // fixed before Date initializes; no Jest environment mutation is assumed.
    const script = `
      const fs = require('node:fs');
      const ts = require('typescript');
      require.extensions['.ts'] = (module, filename) => module._compile(ts.transpileModule(fs.readFileSync(filename, 'utf8'), {
        compilerOptions: { module: ts.ModuleKind.CommonJS }
      }).outputText, filename);
      const modules = ['./src/lib/utils/dates.ts', './src/lib/dateFormatter.ts', './src/utils/dateFormatter.ts'].map(path => require(path));
      const inputs = ${JSON.stringify(inputs)};
      console.log(JSON.stringify({
        offset: new Date('2026-11-26T00:00:00Z').getTimezoneOffset(),
        oldMidnightDay: new Date('2026-11-26T00:00:00Z').getDate(),
        oldLateDay: new Date('2026-11-26T23:30:00Z').getDate(),
        values: modules.map(module => inputs.map(input => module.formatDate(input))),
        styles: ['short', 'compact', 'month'].map(style => modules[0].formatDate('2026-01-01T00:30:00+14:00', style))
      }));`;
    const outputs = ['UTC', 'America/Los_Angeles', 'Pacific/Kiritimati'].map(TZ => JSON.parse(execFileSync(process.execPath, ['-e', script], {
      cwd: root, env: { ...process.env, TZ }, encoding: 'utf8', timeout: 15000,
    })));
    expect(outputs.map(output => output.offset)).toEqual([0, 480, -840]);
    // The prior local-getter pattern crosses both the day and month boundaries.
    expect(outputs.map(output => output.oldMidnightDay)).toEqual([26, 25, 26]);
    expect(outputs.map(output => output.oldLateDay)).toEqual([26, 26, 27]);
    const expected = [...samples.map(([, value]) => value), ...invalid, '', ''];
    for (const output of outputs) {
      expect(output.values).toEqual([expected, expected, expected]);
      expect(output.styles).toEqual(['Dec 31, 2025', 'Dec 31', 'December 2025']);
    }
  });
});
