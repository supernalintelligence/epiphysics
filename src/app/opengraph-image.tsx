import { ImageResponse } from 'next/og';

export const alt = 'Epiphysics: Representations of changing systems.';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default function Image() {
  return new ImageResponse(<div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between', background: '#f5f7f3', color: '#202725', padding: '64px 76px' }}>
    <div style={{ fontSize: 24, letterSpacing: 4, color: '#30634e' }}>EPIPHYSICS</div>
    <div style={{ display: 'flex', flexDirection: 'column', fontSize: 70, letterSpacing: -3, lineHeight: 1.12 }}><span>Representations of</span><span>changing systems.</span></div>
    <div style={{ display: 'flex', fontSize: 23, color: '#606a65' }}>Observe / Represent / Predict / Evaluate / Revise</div>
  </div>, size);
}
