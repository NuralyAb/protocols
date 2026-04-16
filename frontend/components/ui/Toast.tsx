'use client';
import { create } from 'zustand';
import { useEffect } from 'react';

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

export function Toaster() {
  const { items, dismiss } = useToasts();
  // Keyboard: Esc clears all
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') items.forEach((t) => dismiss(t.id));
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [items, dismiss]);

  return (
    <div aria-live="polite" aria-atomic className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {items.map((t) => (
        <div
          key={t.id}
          role="status"
          className={
            'rounded-md border px-4 py-2 text-sm shadow ' +
            (t.kind === 'error'
              ? 'border-red-500/40 bg-red-500/10 text-red-700'
              : t.kind === 'success'
              ? 'border-green-500/40 bg-green-500/10 text-green-700'
              : 'border-border bg-bg')
          }
        >
          {t.text}
        </div>
      ))}
    </div>
  );
}
