'use client';
import { useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { useAuth } from '@/lib/auth';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { useToasts } from '@/components/ui/Toast';

export default function LoginPage() {
  const t = useTranslations('auth');
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
    <div className="mx-auto flex min-h-[70vh] max-w-md items-center">
      <Card className="w-full">
        <h1 className="mb-1 text-2xl font-semibold">{t('title')}</h1>
        <p className="mb-6 text-sm text-muted">{t('subtitle')}</p>
        <form onSubmit={onSubmit} className="space-y-4">
          <label className="block">
            <span className="mb-1 block text-sm">{t('email')}</span>
            <Input
              type="email"
              required
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </label>
          <label className="block">
            <span className="mb-1 block text-sm">{t('password')}</span>
            <Input
              type="password"
              required
              autoComplete="current-password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <Button type="submit" loading={loading} className="w-full">
            {t('signIn')}
          </Button>
        </form>
        <p className="mt-4 text-xs text-muted">{t('demoHint')}</p>
      </Card>
    </div>
  );
}
