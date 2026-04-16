import { getRequestConfig } from 'next-intl/server';
import { cookies, headers } from 'next/headers';
import { defaultLocale, locales, type Locale } from './config';

function pickLocale(): Locale {
  const c = cookies().get('locale')?.value;
  if (c && (locales as readonly string[]).includes(c)) return c as Locale;
  const accept = headers().get('accept-language') ?? '';
  for (const loc of locales) if (accept.toLowerCase().includes(loc)) return loc;
  return defaultLocale;
}

export default getRequestConfig(async () => {
  const locale = pickLocale();
  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
