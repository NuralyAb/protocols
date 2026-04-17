'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { FileAudio, Mic, Upload, ArrowUpRight } from 'lucide-react';
import { jobsApi, type JobBrief, type JobStatus } from '@/lib/api';
import { Badge, Card, CardBody, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
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
        <div className="space-y-1">
          <h1 className="text-3xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="text-muted-fg">{t('subtitle')}</p>
        </div>
        <div className="flex gap-2">
          <Link href="/upload">
            <Button>
              <Upload /> {tCta('upload')}
            </Button>
          </Link>
          <Link href="/live">
            <Button variant="secondary">
              <Mic /> {tCta('startLive')}
            </Button>
          </Link>
        </div>
      </header>

      {jobs === null ? (
        <ul className="grid gap-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <li
              key={i}
              aria-hidden
              className="h-[76px] animate-pulse rounded-xl border border-border bg-surface-2/50"
            />
          ))}
        </ul>
      ) : jobs.length === 0 ? (
        <Card>
          <CardBody className="flex flex-col items-center gap-3 py-14 text-center">
            <div className="flex size-10 items-center justify-center rounded-full bg-primary-soft text-primary">
              <FileAudio className="size-5" />
            </div>
            <div className="space-y-1">
              <h2 className="text-base font-semibold">{t('empty')}</h2>
              <p className="text-sm text-muted-fg">Upload a file or start a live session to begin.</p>
            </div>
            <div className="flex gap-2 pt-2">
              <Link href="/upload">
                <Button size="sm"><Upload /> {tCta('upload')}</Button>
              </Link>
              <Link href="/live">
                <Button size="sm" variant="secondary"><Mic /> {tCta('startLive')}</Button>
              </Link>
            </div>
          </CardBody>
        </Card>
      ) : (
        <ul className="grid gap-3">
          {jobs.map((j) => {
            const title = j.title || j.source_filename || j.id.slice(0, 8);
            return (
              <li key={j.id}>
                <Link
                  href={`/session/${j.id}`}
                  className="group block rounded-xl border border-border bg-surface-1 p-4 shadow-xs transition-all hover:border-primary/40 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
                >
                  <div className="flex items-center gap-3">
                    <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary">
                      <FileAudio className="size-4" aria-hidden />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="flex items-center gap-2">
                        <h2 className="truncate text-sm font-semibold text-fg">{title}</h2>
                        <Badge tone={statusTone(j.status)} dot>
                          {t(`status.${j.status}`)}
                        </Badge>
                      </div>
                      <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-fg">
                        <span>{new Date(j.created_at).toLocaleString()}</span>
                        {j.duration_ms ? <span>· {formatDuration(j.duration_ms)}</span> : null}
                        {j.status === 'processing' && <span>· {j.progress}%</span>}
                      </div>
                    </div>
                    <ArrowUpRight
                      aria-hidden
                      className="size-4 text-muted-fg transition-colors group-hover:text-primary"
                    />
                  </div>
                  {j.status === 'processing' && (
                    <div
                      className="mt-3 h-1 overflow-hidden rounded-full bg-muted-bg"
                      aria-hidden
                    >
                      <div
                        className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
                        style={{ width: `${j.progress}%` }}
                      />
                    </div>
                  )}
                </Link>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}
