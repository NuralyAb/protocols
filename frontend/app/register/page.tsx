'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { AudioLines, UserPlus } from 'lucide-react';
import { useAuth } from '@/lib/auth';
import { Button } from '@/components/ui/Button';
import { Input, Field } from '@/components/ui/Input';
import { useToasts } from '@/components/ui/Toast';

export default function RegisterPage() {
  const t = useTranslations('auth');
  const tApp = useTranslations('app');
  const router = useRouter();
  const register = useAuth((s) => s.register);
  const push = useToasts((s) => s.push);
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (password.length < 8) {
      push('error', t('passwordTooShort'));
      return;
    }
    if (password !== confirm) {
      push('error', t('passwordMismatch'));
      return;
    }
    setLoading(true);
    try {
      await register(email, password, fullName.trim() || undefined);
      router.replace('/');
    } catch (err: any) {
      push('error', err?.response?.data?.detail || t('registerError'));
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
          <h1 className="text-2xl font-semibold tracking-tight">{t('registerTitle')}</h1>
          <p className="mt-1 text-sm text-muted-fg">{t('registerSubtitle')}</p>
        </div>
      </div>

      <div className="rounded-2xl border border-border bg-surface-1 p-6 shadow-sm">
        <form onSubmit={onSubmit} className="space-y-4">
          <Field label={t('fullName')} htmlFor="fullName">
            <Input
              id="fullName"
              type="text"
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </Field>
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
              minLength={8}
              autoComplete="new-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </Field>
          <Field label={t('confirmPassword')} htmlFor="confirm">
            <Input
              id="confirm"
              type="password"
              required
              minLength={8}
              autoComplete="new-password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </Field>
          <Button type="submit" loading={loading} className="w-full" size="lg">
            {!loading && <UserPlus />}
            {t('signUp')}
          </Button>
        </form>
      </div>

      <p className="mt-4 text-center text-sm text-muted-fg">
        {t('haveAccount')}{' '}
        <Link href="/login" className="font-medium text-primary hover:underline">
          {t('signIn')}
        </Link>
      </p>
      <p className="mt-6 text-center text-[11px] uppercase tracking-widest text-muted-fg/70">
        {tApp('title')}
      </p>
    </div>
  );
}
