'use client';
import { useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import { Globe } from 'lucide-react';
import { locales, type Locale } from '@/lib/i18n/config';

export function LocaleSwitcher() {
  const current = useLocale();
  const router = useRouter();
  return (
    <div className="relative">
      <Globe
        aria-hidden
        className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-fg"
      />
      <select
        aria-label="Language"
        value={current}
        onChange={(e) => {
          const next = e.target.value as Locale;
          document.cookie = `locale=${next}; path=/; max-age=31536000`;
          router.refresh();
        }}
        className="h-8 appearance-none rounded-lg border border-border bg-surface-1 pl-8 pr-3 text-xs font-medium text-fg transition-colors hover:bg-surface-2 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
      >
        {locales.map((l) => (
          <option key={l} value={l}>{l.toUpperCase()}</option>
        ))}
      </select>
    </div>
  );
}
