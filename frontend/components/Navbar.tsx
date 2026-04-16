'use client';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { LocaleSwitcher } from './LocaleSwitcher';
import { useAuth } from '@/lib/auth';
import { Button } from './ui/Button';

export function Navbar() {
  const t = useTranslations('nav');
  const tApp = useTranslations('app');
  const tAuth = useTranslations('auth');
  const { token, user, logout } = useAuth();
  const router = useRouter();

  const links = [
    { href: '/', label: t('dashboard') },
    { href: '/upload', label: t('upload') },
    { href: '/live', label: t('live') },
    { href: '/settings', label: t('settings') },
  ];
  return (
    <header className="border-b border-border">
      <nav aria-label="Primary" className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-3">
        <Link href="/" className="text-lg font-semibold">{tApp('title')}</Link>
        <ul className="flex flex-1 flex-wrap items-center gap-5">
          {token &&
            links.map((l) => (
              <li key={l.href}>
                <Link href={l.href} className="hover:underline">{l.label}</Link>
              </li>
            ))}
        </ul>
        <div className="flex items-center gap-3">
          <LocaleSwitcher />
          {token ? (
            <>
              {user?.email && <span className="hidden text-xs text-muted sm:inline">{user.email}</span>}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  logout();
                  router.replace('/login');
                }}
              >
                {tAuth('signOut')}
              </Button>
            </>
          ) : (
            <Link href="/login">
              <Button size="sm" variant="secondary">{tAuth('signIn')}</Button>
            </Link>
          )}
        </div>
      </nav>
    </header>
  );
}
