'use client';
import { useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import { useAuth } from '@/lib/auth';

const PUBLIC = new Set(['/login']);

export function AuthGate({ children }: { children: React.ReactNode }) {
  const { token, hydrated, fetchMe, user } = useAuth();
  const router = useRouter();
  const pathname = usePathname();
  const isPublic = PUBLIC.has(pathname);

  useEffect(() => {
    if (!hydrated) return;
    if (!token && !isPublic) {
      router.replace(`/login?next=${encodeURIComponent(pathname)}`);
      return;
    }
    if (token && !user) fetchMe().catch(() => {});
  }, [hydrated, token, user, pathname, isPublic, router, fetchMe]);

  if (!hydrated) return <div className="p-8 text-muted">…</div>;
  if (!token && !isPublic) return null;
  return <>{children}</>;
}
