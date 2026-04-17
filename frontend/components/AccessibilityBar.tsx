'use client';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Accessibility } from 'lucide-react';
import { cn } from '@/lib/cn';

export function AccessibilityBar() {
  const t = useTranslations('accessibility');
  const [contrast, setContrast] = useState(false);
  const [largeCaptions, setLargeCaptions] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle('contrast-high', contrast);
    document.documentElement.classList.toggle('captions-large', largeCaptions);
  }, [contrast, largeCaptions]);

  return (
    <div role="region" aria-label="Accessibility" className="border-b border-border bg-surface-2/60">
      <div className="container flex flex-wrap items-center gap-4 py-2 text-xs">
        <span className="inline-flex items-center gap-1.5 text-muted-fg">
          <Accessibility className="size-3.5" aria-hidden />
          <span className="sr-only sm:not-sr-only">A11y</span>
        </span>
        <Toggle checked={contrast} onChange={setContrast} label={t('highContrast')} />
        <Toggle checked={largeCaptions} onChange={setLargeCaptions} label={t('largeCaptions')} />
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
