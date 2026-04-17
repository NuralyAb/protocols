'use client';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { LayoutDashboard, Upload, Mic, Settings, LogOut, AudioLines } from 'lucide-react';
import { LocaleSwitcher } from './LocaleSwitcher';
import { useAuth } from '@/lib/auth';
import { Button } from './ui/Button';
import { cn } from '@/lib/cn';

export function Navbar() {
  const t = useTranslations('nav');
  const tApp = useTranslations('app');
  const tAuth = useTranslations('auth');
  const { token, user, logout } = useAuth();
  const router = useRouter();
  const pathname = usePathname();

  const links = [
    { href: '/', label: t('dashboard'), icon: LayoutDashboard },
    { href: '/upload', label: t('upload'), icon: Upload },
    { href: '/live', label: t('live'), icon: Mic },
    { href: '/settings', label: t('settings'), icon: Settings },
  ];

  return (
    <header className="sticky top-0 z-40 border-b border-border bg-bg/80 backdrop-blur supports-[backdrop-filter]:bg-bg/70">
      <nav
        aria-label="Primary"
        className="container flex h-14 items-center gap-6"
      >
        <Link
          href="/"
          className="flex items-center gap-2 font-semibold tracking-tight text-fg"
        >
          <span
            aria-hidden
            className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-fg shadow-xs"
          >
            <AudioLines className="size-4" />
          </span>
          <span>{tApp('title')}</span>
        </Link>

        {token && (
          <ul className="hidden flex-1 items-center gap-1 md:flex">
            {links.map((l) => {
              const active = pathname === l.href || (l.href !== '/' && pathname.startsWith(l.href));
              const Icon = l.icon;
              return (
                <li key={l.href}>
                  <Link
                    href={l.href}
                    aria-current={active ? 'page' : undefined}
                    className={cn(
                      'inline-flex items-center gap-2 rounded-lg px-3 py-1.5 text-sm font-medium transition-colors',
                      active
                        ? 'bg-primary-soft text-primary'
                        : 'text-muted-fg hover:bg-muted-bg hover:text-fg'
                    )}
                  >
                    <Icon className="size-4" aria-hidden />
                    {l.label}
                  </Link>
                </li>
              );
            })}
          </ul>
        )}

        <div className={cn('flex items-center gap-2', !token && 'ml-auto')}>
          <LocaleSwitcher />
          {token ? (
            <>
              {user?.email && (
                <span className="hidden text-xs text-muted-fg lg:inline">{user.email}</span>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  logout();
                  router.replace('/login');
                }}
              >
                <LogOut className="size-4" />
                <span className="hidden sm:inline">{tAuth('signOut')}</span>
              </Button>
            </>
          ) : (
            <Link href="/login">
              <Button size="sm" variant="secondary">{tAuth('signIn')}</Button>
            </Link>
          )}
        </div>
      </nav>

      {token && (
        <ul className="container flex items-center gap-1 overflow-x-auto pb-2 md:hidden no-scrollbar">
          {links.map((l) => {
            const active = pathname === l.href || (l.href !== '/' && pathname.startsWith(l.href));
            const Icon = l.icon;
            return (
              <li key={l.href}>
                <Link
                  href={l.href}
                  aria-current={active ? 'page' : undefined}
                  className={cn(
                    'inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium',
                    active
                      ? 'bg-primary-soft text-primary'
                      : 'text-muted-fg hover:text-fg'
                  )}
                >
                  <Icon className="size-4" aria-hidden />
                  {l.label}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </header>
  );
}
