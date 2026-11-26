import { Metadata } from 'next';
import ResearchHome from '@/components/home/ResearchHome';
import { loadSiteConfig } from '@/lib/server/config';

export function generateMetadata(): Metadata {
  const { site } = loadSiteConfig();
  return {
    title: 'Epiphysics — Representations of changing systems',
    description: 'An open research program for representations, recursive AI systems, and predictions grounded in dated evidence.',
    metadataBase: new URL(site.url),
    alternates: { canonical: '/' },
    openGraph: { title: 'Epiphysics', description: 'Research on representations, predictions, and dated evidence.', url: '/', type: 'website' },
    twitter: { card: 'summary_large_image' },
  };
}

export default function Home() { return <ResearchHome />; }
