import type { Metadata } from 'next';
import ResearchMap from '@/components/research-map/ResearchMap';
import type { ResearchMapData } from '@/components/research-map/model';
import data from '@/data/public-research-map.json';

export const metadata: Metadata = {
  title: 'Research map | Epiphysics',
  description: 'Explore research claims, their evidence, qualifications, and proposed next tests in a curated public map.',
  alternates: { canonical: '/research-map' },
};

export default function ResearchMapPage() {
  return <ResearchMap data={data as ResearchMapData} />;
}
