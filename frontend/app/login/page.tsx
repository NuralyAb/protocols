'use client';
import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { AudioLines, LogIn } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { Button } from '@/components/ui/Button';
import { Input, Field } from '@/components/ui/Input';
import { useToasts } from '@/components/ui/Toast';

export default function LoginPage() {
  const t = useTranslations('auth');
  const tApp = useTranslations('app');
  const router = useRouter();
  const params = useSearchParams();
  const login = useAuth((s) => s.login);
  const push = useToasts((s) => s.push);
  const [email, setEmail] = useState('demo@protocol.ai');
  const [password, setPassword] = useState('demo12345');
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    try {
      await login(email, password);
      const next = params.get('next') || '/';
      router.replace(next);
    } catch (err: any) {
      push('error', err?.response?.data?.detail || t('error'));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto flex min-h-[70vh] w-full max-w-sm flex-col justify-center">
      <div className="mb-6 flex flex-col items-center gap-3 text-center">
        <span
          aria-hidden
          className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-fg shadow-sm"
        >
          <AudioLines className="size-5" />
        </span>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="mt-1 text-sm text-muted-fg">{t('subtitle')}</p>
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-surface-1 p-6 shadow-sm">
        <form onSubmit={onSubmit} className="space-y-4">
          <Field label={t('email')} htmlFor="email">
            <Input
              id="email"
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </Field>
          <Field label={t('password')} htmlFor="password">
            <Input
              id="password"
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>
          <Button type="submit" loading={loading} className="w-full" size="lg">
            {!loading && <LogIn />}
            {t('signIn')}
          </Button>
        </form>
      </div>

      <p className="mt-4 text-center text-xs text-muted-fg">{t('demoHint')}</p>
      <p className="mt-6 text-center text-[11px] uppercase tracking-widest text-muted-fg/70">
        {tApp('title')}
      </p>
    </div>
  );
}
