'use client';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';

export function AccessibilityBar() {
  const t = useTranslations('accessibility');
  const [contrast, setContrast] = useState(false);
  const [largeCaptions, setLargeCaptions] = useState(false);

  useEffect(() => {
    document.documentElement.classList.toggle('contrast-high', contrast);
    document.documentElement.classList.toggle('captions-large', largeCaptions);
  }, [contrast, largeCaptions]);

  return (
    <div role="region" aria-label="Accessibility" className="border-b border-border bg-muted/10">
      <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-4 px-4 py-2 text-sm">
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
    <label className="inline-flex cursor-pointer items-center gap-2">
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="h-4 w-4"
        aria-label={label}
      />
      <span>{label}</span>
    </label>
  );
}
