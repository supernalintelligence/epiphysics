import type { Metadata } from 'next';
import Link from 'next/link';

export const metadata: Metadata = {
  title: 'About',
  description: 'What Epiphysics studies, with one bone pun.',
};

export default function AboutPage() {
  return (
    <main className="mx-auto max-w-2xl px-6 py-16">
      <article className="prose dark:prose-invert">
        <h1>About Epiphysics</h1>
        <p>
          Looking for the epiphysis, the end of a long bone? Easy mistake. We also study
          how things grow and hold together, but our bones to pick are with theories.
        </p>
        <p>
          Epimechanics is the framework. Epiphysics is the empirical program that puts it
          to the test.
        </p>
        <p>
          Start with the <Link href="/overview">overview</Link> or the{' '}
          <Link href="/theory/series_map">theory series map</Link>.
        </p>
      </article>
    </main>
  );
}
