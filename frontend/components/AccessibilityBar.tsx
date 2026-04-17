'use client';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Accessibility, Moon, Sun } from 'lucide-react';
import { cn } from '@/lib/cn';

const STORAGE_KEY = 'protocol-ai:prefs';

type Prefs = { contrast: boolean; largeCaptions: boolean; dark: boolean };

function loadPrefs(): Prefs {
  if (typeof window === 'undefined') return { contrast: false, largeCaptions: false, dark: false };
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { contrast: false, largeCaptions: false, dark: false, ...JSON.parse(raw) };
  } catch {}
  const dark = window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false;
  return { contrast: false, largeCaptions: false, dark };
}

export function AccessibilityBar() {
  const t = useTranslations('accessibility');
  const [prefs, setPrefs] = useState<Prefs>({ contrast: false, largeCaptions: false, dark: false });
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setPrefs(loadPrefs());
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    document.documentElement.classList.toggle('contrast-high', prefs.contrast);
    document.documentElement.classList.toggle('captions-large', prefs.largeCaptions);
    document.documentElement.classList.toggle('dark', prefs.dark);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
    } catch {}
  }, [prefs, hydrated]);

  const set = <K extends keyof Prefs>(k: K, v: Prefs[K]) =>
    setPrefs((p) => ({ ...p, [k]: v }));

  return (
    <div role="region" aria-label="Accessibility" className="border-b border-border bg-surface-2/60">
      <div className="container flex flex-wrap items-center gap-4 py-2 text-xs">
        <span className="inline-flex items-center gap-1.5 text-muted-fg">
          <Accessibility className="size-3.5" aria-hidden />
          <span className="sr-only sm:not-sr-only">A11y</span>
        </span>
        <Toggle checked={prefs.contrast} onChange={(v) => set('contrast', v)} label={t('highContrast')} />
        <Toggle checked={prefs.largeCaptions} onChange={(v) => set('largeCaptions', v)} label={t('largeCaptions')} />
        <button
          type="button"
          role="switch"
          aria-checked={prefs.dark}
          aria-label={t('darkMode')}
          onClick={() => set('dark', !prefs.dark)}
          className="ml-auto inline-flex items-center gap-1.5 rounded-md px-1.5 py-0.5 text-xs text-fg transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
        >
          {prefs.dark ? (
            <Sun className="size-3.5" aria-hidden />
          ) : (
            <Moon className="size-3.5" aria-hidden />
          )}
          <span className="hidden sm:inline">{t('darkMode')}</span>
        </button>
      </div>
    </div>
  );
}

function Toggle({
  checked, onChange, label,
}: { checked: boolean; onChange: (v: boolean) => void; label: string }) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="inline-flex items-center gap-2 rounded-md px-1 py-0.5 text-xs text-fg transition-colors hover:text-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
    >
      <span
        aria-hidden
        className={cn(
          'relative inline-flex h-4 w-7 items-center rounded-full transition-colors',
          checked ? 'bg-primary' : 'bg-muted-bg'
        )}
      >
        <span
          className={cn(
            'absolute left-0.5 size-3 rounded-full bg-white shadow-xs transition-transform',
            checked && 'translate-x-3'
          )}
        />
      </span>
      {label}
    </button>
  );
}
