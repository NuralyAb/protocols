'use client';
import { useEffect, useRef } from 'react';

export function Waveform({
  read,
  active,
  bins = 48,
  height = 56,
}: {
  read: (bins: number) => Float32Array;
  active: boolean;
  bins?: number;
  height?: number;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const rafRef = useRef<number | null>(null);

  useEffect(() => {
    if (!active) {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
      const c = canvasRef.current;
      const g = c?.getContext('2d');
      if (c && g) g.clearRect(0, 0, c.width, c.height);
      return;
    }

    function readColor() {
      const styles = getComputedStyle(document.documentElement);
      const v = styles.getPropertyValue('--primary').trim() || '231 70% 55%';
      return `hsl(${v})`;
    }

    const color = readColor();

    function tick() {
      const canvas = canvasRef.current;
      if (!canvas) return;
      const ctx = canvas.getContext('2d');
      if (!ctx) return;
      const dpr = window.devicePixelRatio || 1;
      const w = canvas.clientWidth;
      const h = canvas.clientHeight;
      if (canvas.width !== w * dpr || canvas.height !== h * dpr) {
        canvas.width = w * dpr;
        canvas.height = h * dpr;
      }
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);

      const data = read(bins);
      const gap = 3;
      const barW = Math.max(2, (w - (bins - 1) * gap) / bins);
      ctx.fillStyle = color;
      for (let i = 0; i < bins; i++) {
        const amp = data[i] ?? 0;
        const bh = Math.max(3, amp * h * 0.9);
        const x = i * (barW + gap);
        const y = (h - bh) / 2;
        const r = Math.min(barW / 2, 3);
        roundRect(ctx, x, y, barW, bh, r);
      }
      rafRef.current = requestAnimationFrame(tick);
    }
    rafRef.current = requestAnimationFrame(tick);
    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [active, read, bins]);

  return (
    <canvas
      ref={canvasRef}
      aria-label="microphone level"
      role="img"
      style={{ width: '100%', height }}
      className="rounded-xl border border-border bg-surface-1"
    />
  );
}

function roundRect(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  w: number,
  h: number,
  r: number
) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
  ctx.fill();
}
