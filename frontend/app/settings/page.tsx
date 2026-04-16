import { getTranslations } from 'next-intl/server';

export default async function SettingsPage() {
  const t = await getTranslations('nav');
  return (
    <section>
      <h1 className="text-2xl font-semibold">{t('settings')}</h1>
      <p className="mt-2 text-muted">Profile, protocol templates, accessibility defaults — coming in later stages.</p>
    </section>
  );
}
