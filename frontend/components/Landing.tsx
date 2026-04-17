'use client';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { Mic, Upload, FileText, Sparkles, Languages, ShieldCheck, ArrowRight } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardBody } from '@/components/ui/Card';

export function Landing() {
  const t = useTranslations('landing');
  const tAuth = useTranslations('auth');

  const features = [
    { icon: Mic, key: 'live' },
    { icon: Upload, key: 'upload' },
    { icon: FileText, key: 'protocol' },
    { icon: Languages, key: 'multilingual' },
    { icon: Sparkles, key: 'ai' },
    { icon: ShieldCheck, key: 'private' },
  ] as const;

  const steps = ['record', 'transcribe', 'export'] as const;

  return (
    <div className="space-y-16 sm:space-y-20">
      <section className="relative overflow-hidden rounded-3xl border border-border bg-gradient-to-br from-primary-soft via-surface-1 to-surface-2 px-6 py-14 sm:px-10 sm:py-20">
        <div
          aria-hidden
          className="pointer-events-none absolute -right-24 -top-24 size-72 rounded-full bg-primary/20 blur-3xl"
        />
        <div
          aria-hidden
          className="pointer-events-none absolute -bottom-32 -left-20 size-72 rounded-full bg-primary/10 blur-3xl"
        />
        <div className="relative mx-auto max-w-3xl text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-primary/20 bg-surface-1/70 px-3 py-1 text-xs font-medium text-primary backdrop-blur">
            <Sparkles className="size-3.5" aria-hidden />
            {t('badge')}
          </span>
          <h1 className="mt-5 text-4xl font-semibold tracking-tight sm:text-5xl">
            {t('hero.title')}
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-base text-muted-fg sm:text-lg">
            {t('hero.subtitle')}
          </p>
          <div className="mt-7 flex flex-wrap justify-center gap-3">
            <Link href="/register">
              <Button size="lg">
                {t('hero.cta')} <ArrowRight />
              </Button>
            </Link>
            <Link href="/login">
              <Button size="lg" variant="secondary">
                {tAuth('signIn')}
              </Button>
            </Link>
          </div>
          <p className="mt-3 text-xs text-muted-fg">{t('hero.demoHint')}</p>
        </div>
      </section>

      <section aria-labelledby="how-it-works" className="space-y-6">
        <div className="text-center">
          <h2 id="how-it-works" className="text-2xl font-semibold tracking-tight sm:text-3xl">
            {t('steps.title')}
          </h2>
          <p className="mt-2 text-sm text-muted-fg">{t('steps.subtitle')}</p>
        </div>
        <ol className="grid gap-3 sm:grid-cols-3">
          {steps.map((key, idx) => (
            <li key={key}>
              <Card>
                <CardBody className="space-y-2">
                  <span className="inline-flex size-7 items-center justify-center rounded-full bg-primary-soft text-xs font-semibold text-primary">
                    {idx + 1}
                  </span>
                  <h3 className="text-base font-semibold">{t(`steps.${key}.title`)}</h3>
                  <p className="text-sm text-muted-fg">{t(`steps.${key}.body`)}</p>
                </CardBody>
              </Card>
            </li>
          ))}
        </ol>
      </section>

      <section aria-labelledby="features" className="space-y-6">
        <div className="text-center">
          <h2 id="features" className="text-2xl font-semibold tracking-tight sm:text-3xl">
            {t('features.title')}
          </h2>
          <p className="mt-2 text-sm text-muted-fg">{t('features.subtitle')}</p>
        </div>
        <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {features.map(({ icon: Icon, key }) => (
            <li key={key}>
              <Card>
                <CardBody className="flex gap-3">
                  <span className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary">
                    <Icon className="size-4" aria-hidden />
                  </span>
                  <div className="space-y-1">
                    <h3 className="text-sm font-semibold">{t(`features.${key}.title`)}</h3>
                    <p className="text-sm text-muted-fg">{t(`features.${key}.body`)}</p>
                  </div>
                </CardBody>
              </Card>
            </li>
          ))}
        </ul>
      </section>

      <section className="rounded-2xl border border-border bg-surface-1 p-8 text-center sm:p-10">
        <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">{t('finalCta.title')}</h2>
        <p className="mx-auto mt-2 max-w-lg text-sm text-muted-fg">{t('finalCta.body')}</p>
        <div className="mt-5 flex flex-wrap justify-center gap-3">
          <Link href="/register">
            <Button>
              {t('finalCta.button')} <ArrowRight />
            </Button>
          </Link>
        </div>
      </section>
    </div>
  );
}
