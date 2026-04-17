'use client';
import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';

const PUBLIC = new Set(['/', '/login', '/register']);
const PUBLIC_PREFIXES = ['/public/'];

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { token, hydrated, fetchMe, user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const isPublic =
    PUBLIC.has(pathname) || PUBLIC_PREFIXES.some((p) => pathname.startsWith(p));

  useEffect(() => {
    if (!hydrated) return;
    if (!token && !isPublic) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    if (token && !user) fetchMe().catch(() => {});
  }, [hydrated, token, user, pathname, isPublic, router, fetchMe]);

  if (!hydrated) {
    return (
      <div
        className="space-y-3"
        aria-busy="true"
        aria-live="polite"
        aria-label="Loading"
      >
        <div className="h-8 w-40 animate-pulse rounded-md bg-muted-bg" />
        <div className="h-24 animate-pulse rounded-xl border border-border bg-surface-2/50" />
      </div>
    );
  }
  if (!token && !isPublic) return null;
  return <>{children}</>;
}
