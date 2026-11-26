import '@testing-library/jest-dom';
import { render, screen } from '@testing-library/react';
import type { Post } from '@/lib/content';
import CollectionDisplay from './CollectionDisplay';

jest.mock('./CollectionViewWrapper', () => ({ __esModule: true, default: () => <div>Collection items</div> }));
jest.mock('./CollectionFloatingTools', () => ({ __esModule: true, default: () => null }));
jest.mock('./media/Media', () => ({ __esModule: true, default: () => null }));

const indexPost: Post = {
  slug: 'research', path: ['research'], content: '', html: '', excerpt: '',
  metadata: { title: 'Research', date: '2026-11-25' }, isIndex: true, childPosts: [], childSlugs: [], displayStyle: 'collection',
};

function display(post: Post) {
  return <CollectionDisplay indexPost={post} items={[]} section="research" breadcrumbPath={[]} getImagePath={() => '/unused.png'} />;
}

describe('collection index title integration', () => {
  it.each(['', '   ', '<h2>Current focus</h2>'])('renders a metadata heading even when index HTML is %j', html => {
    render(display({ ...indexPost, html }));
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Research');
    expect(screen.getByText('Collection items')).toBeInTheDocument();
  });

  it('passes the authored heading through without adding a duplicate', () => {
    render(display({ ...indexPost, html: '<h1>Research introduction</h1>' }));
    expect(screen.getAllByRole('heading', { level: 1 })).toHaveLength(1);
    expect(screen.getByRole('heading', { level: 1 })).toHaveTextContent('Research introduction');
  });

  it('honors explicit title hiding for an empty-body index', () => {
    render(display({ ...indexPost, metadata: { ...indexPost.metadata, hide: ['title'] } }));
    expect(screen.queryByRole('heading', { level: 1 })).not.toBeInTheDocument();
  });
});
