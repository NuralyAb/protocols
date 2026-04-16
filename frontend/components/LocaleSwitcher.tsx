'use client';
import { useLocale } from 'next-intl';
import { useRouter } from 'next/navigation';
import { locales, type Locale } from '@/lib/i18n/config';

export function LocaleSwitcher() {
  const current = useLocale();
  const router = useRouter();
  return (
    <label className="flex items-center gap-2 text-sm">
      <span className="sr-only">Language</span>
      <select
        aria-label="Language"
        value={current}
        onChange={(e) => {
          const next = e.target.value as Locale;
          document.cookie = `locale=${next}; path=/; max-age=31536000`;
          router.refresh();
        }}
        className="rounded border border-border bg-transparent px-2 py-1"
      >
        {locales.map((l) => (
          <option key={l} value={l}>{l.toUpperCase()}</option>
        ))}
      </select>
    </label>
  );
}
