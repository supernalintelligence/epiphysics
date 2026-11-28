import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import CollectionTTSContent from './CollectionTTSContent';

describe('collection headings', () => {
  it('supplies a main heading for an index with only lower-level body headings', () => {
    render(<CollectionTTSContent title="Research" isIndex html="<h2>Current focus</h2>" content="" />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Research');
    expect(screen.queryByText(/AI Contributors:/)).not.toBeInTheDocument();
  });

  it('keeps an authored index heading without adding a duplicate metadata title', () => {
    render(<CollectionTTSContent title="Research" isIndex html='<section><h1 id="intro">Authored introduction</h1></section>' content="" />);
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Authored introduction');
  });

  it.each([
    '<!-- <h1>Comment only</h1> --><p>Introduction</p>',
    '<pre><code>&lt;h1&gt;Example&lt;/h1&gt;</code></pre>',
    '<template><h1>Template only</h1></template><p>Introduction</p>',
  ])('ignores non-rendered heading markup: %s', html => {
    render(<CollectionTTSContent title="Research" isIndex html={html} content="" />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Research');
  });

  it('honors explicit title hiding on an index', () => {
    render(<CollectionTTSContent title="Research" isIndex hide={['title']} html="<p>Introduction</p>" content="" />);
    expect(screen.queryByRole('heading', { level: 1 })).not.toBeInTheDocument();
  });

  it('preserves an authored heading when the metadata title is hidden', () => {
    render(<CollectionTTSContent title="Research" isIndex hide={['title']} html="<h1>Authored introduction</h1>" content="" />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Authored introduction');
  });

  it('updates the heading decision when index content changes', () => {
    const { rerender } = render(<CollectionTTSContent title="Research" isIndex html="<p>Introduction</p>" content="" />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Research');
    rerender(<CollectionTTSContent title="Research" isIndex html="<h1>Authored introduction</h1>" content="" />);
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Authored introduction');
  });

  it('preserves the article title and byline for non-index content', () => {
    render(<CollectionTTSContent title="An article" html="<p>Body</p>" content="" authorName="Author" authorUrl="https://example.invalid/author" aiAuthors={['Contributor']} />);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('An article');
    expect(screen.getByRole('link', { name: 'Author' })).toHaveAttribute('href', 'https://example.invalid/author');
    expect(screen.getByText('AI Contributors: Contributor')).toBeInTheDocument();
  });

  it('preserves explicit article title and byline hiding', () => {
    render(<CollectionTTSContent title="An article" hide={['title']} html="<p>Body</p>" content="" />);
    expect(screen.queryByRole('heading', { level: 1 })).not.toBeInTheDocument();
    expect(screen.queryByText(/AI Contributors:/)).not.toBeInTheDocument();
  });
});
