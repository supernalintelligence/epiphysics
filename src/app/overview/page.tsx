import type { Metadata } from 'next';
import ResearchOverview from '@/components/home/ResearchOverview';

export const metadata: Metadata = {
  title: 'A five-step introduction | Epiphysics',
  description: 'Observe, represent, predict, evaluate, revise: a research program that can learn from being wrong.',
};
export default function Overview() { return <ResearchOverview />; }
