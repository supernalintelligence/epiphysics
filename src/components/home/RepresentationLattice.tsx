'use client';

import { useEffect, useRef } from 'react';

type Point = [number, number, number];
const COUNT = 84;
const noise = (i: number, j: number) => {
  const n = Math.sin(i * 17.13 + j * 41.79) * 43758.5453;
  return n - Math.floor(n) - .5;
};
const corners: Point[] = [[-.72, -.42, -.4], [.72, -.42, -.4], [0, .72, -.4], [0, 0, .8]];
const shapes: Point[][] = Array.from({ length: 5 }, (_, stage) => Array.from({ length: COUNT }, (_, i): Point => {
  const a = i / COUNT * Math.PI * 2;
  const c = corners[Math.floor(i / 21)];
  if (stage === 0) return [noise(i, 1) * 1.8, noise(i, 2) * 1.5, noise(i, 3) * 1.6];
  if (stage === 1) return [c[0] + noise(i, 1) * .48, c[1] + noise(i, 2) * .48, c[2] + noise(i, 3) * .48];
  if (stage === 2) return [(i % 21) / 14 - .72, Math.sin(i / 5) * .27 + (Math.floor(i / 21) - 1.5) * .32, noise(i, 1) * .7];
  if (stage === 3) return [Math.cos(a) * .78, Math.sin(a) * .78, noise(i, 3) * .25];
  const d = corners[i % 4];
  return [d[0] * .75 + noise(i, 1) * .6, d[1] * .75 + noise(i, 2) * .6, d[2] * .75 + noise(i, 3) * .6];
}));

/** Original procedural geometry: stable point identities, changing proposed groupings. */
export default function RepresentationLattice({ stage, paused = false }: { stage: number; paused?: boolean }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const stageRef = useRef(stage);
  const pauseRef = useRef(paused);
  const wake = useRef<() => void>(() => {});
  useEffect(() => { stageRef.current = stage; wake.current(); }, [stage]);
  useEffect(() => { pauseRef.current = paused; wake.current(); }, [paused]);

  useEffect(() => {
    const el = canvas.current;
    const ctx = el?.getContext('2d');
    if (!el || !ctx) return;
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
    let visible = true, frame = 0, last = 0, rotation = .2, width = 400, height = 400;
    const positions = shapes[stageRef.current].map(p => [...p] as Point);
    const schedule = () => { if (!frame && visible && !document.hidden) frame = requestAnimationFrame(draw); };
    const draw = (time: number) => {
      frame = 0;
      if (!visible || document.hidden) return;
      if (time - last < 32) { schedule(); return; }
      const dt = Math.min((time - last) / 1000, .05); last = time;
      const moving = !pauseRef.current && !reduced.matches;
      if (moving) rotation += dt * .12;
      const target = shapes[stageRef.current];
      for (let i = 0; i < COUNT; i++) for (let axis = 0; axis < 3; axis++) {
        const delta = target[i][axis] - positions[i][axis];
        positions[i][axis] += delta * (reduced.matches || pauseRef.current ? 1 : .08);
      }
      const scale = Math.min(width, height) * .35;
      const points = positions.map(([x, y, z]) => {
        const rx = x * Math.cos(rotation) + z * Math.sin(rotation);
        const rz = z * Math.cos(rotation) - x * Math.sin(rotation);
        return [width / 2 + rx * scale, height / 2 - y * scale, rz] as Point;
      });
      ctx.clearRect(0, 0, width, height);
      for (let i = 0; i < COUNT; i++) for (let j = i + 1; j < COUNT; j++) {
        const distance = Math.hypot(...positions[i].map((v, k) => v - positions[j][k]));
        if (distance > .47) continue;
        ctx.strokeStyle = `rgba(19,110,102,${(.47 - distance) * .75})`;
        ctx.lineWidth = .7;
        ctx.beginPath(); ctx.moveTo(points[i][0], points[i][1]); ctx.lineTo(points[j][0], points[j][1]); ctx.stroke();
      }
      points.forEach(([x, y, z], i) => {
        ctx.fillStyle = i % 7 === 0 ? '#cc654d' : '#136e66';
        ctx.beginPath(); ctx.arc(x, y, 2.2 + (z + 1) * .7, 0, Math.PI * 2); ctx.fill();
      });
      if (moving) schedule();
    };
    const resize = new ResizeObserver(() => {
      width = el.clientWidth; height = el.clientHeight;
      const dpr = Math.min(window.devicePixelRatio || 1, 2);
      el.width = width * dpr; el.height = height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0); schedule();
    });
    const visibility = new IntersectionObserver(([entry]) => { visible = entry.isIntersecting; schedule(); });
    resize.observe(el); visibility.observe(el);
    document.addEventListener('visibilitychange', schedule);
    reduced.addEventListener('change', schedule);
    wake.current = schedule; schedule();
    return () => {
      cancelAnimationFrame(frame); resize.disconnect(); visibility.disconnect();
      document.removeEventListener('visibilitychange', schedule); reduced.removeEventListener('change', schedule);
      wake.current = () => {};
    };
  }, []);
  return <canvas ref={canvas} aria-hidden="true" style={{ width: '100%', height: '100%', display: 'block' }} />;
}
