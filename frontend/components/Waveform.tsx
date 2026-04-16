'use client';
import { useEffect, useRef } from 'react';

/** Live frequency-bar visualization driven by a pull-based `read()` callback. */
export function Waveform({
  read,
  active,
  bins = 32,
  height = 40,
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
      const barW = Math.max(1, (w - (bins - 1) * 2) / bins);
      for (let i = 0; i < bins; i++) {
        const amp = data[i] ?? 0;
        const bh = Math.max(2, amp * h);
        const x = i * (barW + 2);
        const y = (h - bh) / 2;
        ctx.fillStyle = `hsl(${210 + amp * 40} 85% ${35 + amp * 25}%)`;
        ctx.fillRect(x, y, barW, bh);
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
      className="rounded-md border border-border bg-muted/10"
    />
  );
}
