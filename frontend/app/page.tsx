'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { jobsApi, type JobBrief, type JobStatus } from '@/lib/api';
import { Card, Badge } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useAuth } from '@/lib/auth';
import { useToasts } from '@/components/ui/Toast';

function statusTone(s: JobStatus): 'success' | 'info' | 'warning' | 'danger' {
  return s === 'completed' ? 'success' : s === 'processing' ? 'info' : s === 'failed' ? 'danger' : 'warning';
}

function formatDuration(ms?: number | null) {
  if (!ms) return '—';
  const total = Math.floor(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0 ? `${h}h ${m}m` : `${m}:${String(s).padStart(2, '0')}`;
}

export default function Dashboard() {
  const t = useTranslations('dashboard');
  const tCta = useTranslations('cta');
  const token = useAuth((s) => s.token);
  const push = useToasts((s) => s.push);
  const [jobs, setJobs] = useState<JobBrief[] | null>(null);

  useEffect(() => {
    if (!token) return;
    let alive = true;
    const load = async () => {
      try {
        const r = await jobsApi.list();
        if (alive) setJobs(r.data);
      } catch (e: any) {
        if (alive) push('error', e?.response?.data?.detail || 'Load failed');
      }
    };
    load();
    // auto-refresh while something is processing
    const id = setInterval(() => {
      if (!jobs) return;
      if (jobs.some((j) => j.status === 'pending' || j.status === 'processing')) load();
    }, 3000);
    return () => {
      alive = false;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  return (
    <div className="space-y-8">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold">{t('title')}</h1>
          <p className="text-muted">{t('subtitle')}</p>
        </div>
        <div className="flex gap-2">
          <Link href="/upload"><Button>{tCta('upload')}</Button></Link>
          <Link href="/live"><Button variant="secondary">{tCta('startLive')}</Button></Link>
        </div>
      </header>

      {jobs === null ? (
        <p className="text-muted">…</p>
      ) : jobs.length === 0 ? (
        <Card>
          <p className="text-muted">{t('empty')}</p>
        </Card>
      ) : (
        <ul className="grid gap-3">
          {jobs.map((j) => (
            <li key={j.id}>
              <Link
                href={`/session/${j.id}`}
                className="block rounded-lg border border-border p-4 hover:border-accent focus-visible:border-accent"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <h2 className="font-medium">{j.title || j.source_filename || j.id.slice(0, 8)}</h2>
                  <Badge tone={statusTone(j.status)}>{t(`status.${j.status}`)}</Badge>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-xs text-muted">
                  <span>{new Date(j.created_at).toLocaleString()}</span>
                  {j.duration_ms ? <span>• {formatDuration(j.duration_ms)}</span> : null}
                  {j.status === 'processing' && <span>• {j.progress}%</span>}
                </div>
                {j.status === 'processing' && (
                  <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-muted/20" aria-hidden>
                    <div className="h-full bg-accent transition-all" style={{ width: `${j.progress}%` }} />
                  </div>
                )}
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
