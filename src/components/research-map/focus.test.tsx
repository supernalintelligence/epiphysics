/** @jest-environment jsdom */
import { fireEvent, render, screen, within } from '@testing-library/react';
import ResearchMap from './ResearchMap';
import type { ResearchMapData } from './model';

const data: ResearchMapData = {
  schemaVersion: 1, sourceCommit: 'owned', catalogHash: 'owned', payloadHash: 'owned',
  limits: ['Synthetic component fixture; no browser or real dataset.'],
  nodes: [
    { id: 'a', kind: 'claim', title: 'First claim', statement: 'First statement', status: 'hypothesis', basis: 'inferred' },
    { id: 'b', kind: 'claim', title: 'Second claim', statement: 'Second statement', status: 'contested', basis: 'reported' },
    { id: 's', kind: 'source', title: 'Owned source', href: 'https://example.invalid/source', date: null,
      dateType: 'publication', reviewedOn: '2026-11-25', bibliographicOnly: true, limitations: ['Owned fixture'] },
  ],
  edges: [
    { source: 'a', target: 's', type: 'cites' },
    { source: 'b', target: 's', type: 'cites' },
    { source: 'b', target: 'a', type: 'challenges' },
  ],
};

describe('public research map focus', () => {
  beforeEach(() => window.history.replaceState(null, '', '/research-map?claim=a'));

  it('moves focus to the selected heading after following a related claim', () => {
    render(<ResearchMap data={data} />);
    const detail = document.getElementById('selected-claim')!;
    const button = within(detail).getByRole('button', { name: 'Second claim' });
    button.focus();
    expect(document.activeElement).toBe(button);
    fireEvent.click(button);
    expect(button.isConnected).toBe(false);
    expect(document.activeElement).toBe(screen.getByRole('heading', { name: 'Second claim', level: 2 }));
    expect(new URL(window.location.href).searchParams.get('claim')).toBe('b');
  });

  it('preserves browse-list focus when selecting a claim from the list', () => {
    render(<ResearchMap data={data} />);
    const browser = screen.getByRole('complementary', { name: 'Browse claims' });
    const button = within(browser).getByRole('button', { name: /Second claim/ });
    button.focus();
    fireEvent.click(button);
    expect(document.activeElement).toBe(button);
    expect(button.getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByRole('heading', { name: 'Second claim', level: 2 })).toBeTruthy();
  });

  it('moves focus to the selected heading when recovering from an unknown claim link', () => {
    window.history.replaceState(null, '', '/research-map?claim=missing');
    render(<ResearchMap data={data} />);
    const button = screen.getByRole('button', { name: 'Open the first claim' });
    button.focus();
    fireEvent.click(button);
    expect(button.isConnected).toBe(false);
    expect(document.activeElement).toBe(screen.getByRole('heading', { name: 'First claim', level: 2 }));
  });
});
