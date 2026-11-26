import type { Metadata } from 'next';
import ObservatoryExample from '@/components/home/ObservatoryExample';

export const metadata: Metadata = {
  title: 'A forecast you can inspect | Epiphysics',
  description: 'A clearly labelled synthetic example: dated evidence, a forecast, an outcome, and a reproducible score.',
};
export default function Observatory() { return <ObservatoryExample />; }
