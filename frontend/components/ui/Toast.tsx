'use client';
import { create } from 'zustand';
import { useEffect } from 'react';
import { AlertTriangle, CheckCircle2, Info, X } from 'lucide-react';
import { cn } from '@/lib/cn';

type ToastKind = 'success' | 'error' | 'info';
type Toast = { id: number; kind: ToastKind; text: string };

type ToastStore = {
  items: Toast[];
  push: (kind: ToastKind, text: string) => void;
  dismiss: (id: number) => void;
};

export const useToasts = create<ToastStore>((set) => ({
  items: [],
  push: (kind, text) => {
    const id = Date.now() + Math.random();
    set((s) => ({ items: [...s.items, { id, kind, text }] }));
    setTimeout(() => set((s) => ({ items: s.items.filter((t) => t.id !== id) })), 4000);
  },
  dismiss: (id) => set((s) => ({ items: s.items.filter((t) => t.id !== id) })),
}));

const kindStyles: Record<ToastKind, { wrap: string; icon: React.ReactNode }> = {
  success: {
    wrap: 'border-success/30 bg-success-soft text-success',
    icon: <CheckCircle2 className="size-4" aria-hidden />,
  },
  error: {
    wrap: 'border-danger/30 bg-danger-soft text-danger',
    icon: <AlertTriangle className="size-4" aria-hidden />,
  },
  info: {
    wrap: 'border-border bg-surface-1 text-fg',
    icon: <Info className="size-4 text-primary" aria-hidden />,
  },
};

export function Toaster() {
  const { items, dismiss } = useToasts();

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') items.forEach((t) => dismiss(t.id));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [items, dismiss]);

  return (
    <div
      aria-live="polite"
      aria-atomic
      className="pointer-events-none fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2"
    >
      {items.map((t) => {
        const style = kindStyles[t.kind];
        return (
          <div
            key={t.id}
            role="status"
            className={cn(
              'pointer-events-auto flex items-start gap-3 rounded-xl border px-4 py-3 text-sm shadow-md animate-fade-in',
              style.wrap
            )}
          >
            <span className="mt-0.5">{style.icon}</span>
            <p className="flex-1 text-fg">{t.text}</p>
            <button
              type="button"
              onClick={() => dismiss(t.id)}
              className="rounded-md p-1 text-muted-fg transition-colors hover:bg-muted-bg hover:text-fg"
              aria-label="Dismiss"
            >
              <X className="size-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
