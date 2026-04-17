'use client';
import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useTranslations } from 'next-intl';
import { FileAudio, Mic, Upload, ArrowUpRight, Radio, Search, X } from 'lucide-react';
import {
  jobsApi,
  sessionsApi,
  type JobBrief,
  type JobStatus,
  type LiveSession,
} from '@/lib/api';
import { Badge, Card, CardBody } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Input, Select, Field } from '@/components/ui/Input';
import { useAuth } from '@/lib/auth';
import { useToasts } from '@/components/ui/Toast';
import { Landing } from '@/components/Landing';

type Item =
  | { kind: 'job'; at: number; data: JobBrief }
  | { kind: 'session'; at: number; data: LiveSession };

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

export default function Home() {
  const { token, hydrated } = useAuth();
  if (!hydrated) {
    return (
      <div className="space-y-3" aria-busy="true" aria-live="polite">
        <div className="h-8 w-40 animate-pulse rounded-md bg-muted-bg" />
        <div className="h-24 animate-pulse rounded-xl border border-border bg-surface-2/50" />
      </div>
    );
  }
  if (!token) return <Landing />;
  return <Dashboard />;
}

function Dashboard() {
  const t = useTranslations('dashboard');
  const tCta = useTranslations('cta');
  const token = useAuth((s) => s.token);
  const push = useToasts((s) => s.push);
  const [jobs, setJobs] = useState<JobBrief[] | null>(null);
  const [sessions, setSessions] = useState<LiveSession[] | null>(null);
  const [query, setQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'all' | JobStatus | 'live'>('all');
  const [dateFilter, setDateFilter] = useState<'all' | '24h' | '7d' | '30d'>('all');

  useEffect(() => {
    if (!token) return;
    let alive = true;
    const load = async () => {
      try {
        const [jr, sr] = await Promise.all([jobsApi.list(), sessionsApi.list()]);
        if (!alive) return;
        setJobs(jr.data);
        setSessions(sr.data);
      } catch (e: any) {
        if (alive) push('error', e?.response?.data?.detail || 'Load failed');
      }
    };
    load();
    const id = setInterval(() => {
      const hasActive =
        (jobs?.some((j) => j.status === 'pending' || j.status === 'processing') ?? false) ||
        (sessions?.some((s) => s.is_active) ?? false);
      if (hasActive) load();
    }, 3000);
    return () => {
      alive = false;
      clearInterval(id);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  const items: Item[] | null = useMemo(() => {
    if (jobs === null || sessions === null) return null;
    const j: Item[] = jobs.map((x) => ({
      kind: 'job' as const,
      at: new Date(x.created_at).getTime(),
      data: x,
    }));
    const s: Item[] = sessions.map((x) => ({
      kind: 'session' as const,
      at: new Date(x.started_at).getTime(),
      data: x,
    }));
    return [...j, ...s].sort((a, b) => b.at - a.at);
  }, [jobs, sessions]);

  const filtered = useMemo(() => {
    if (!items) return null;
    const now = Date.now();
    const cutoff =
      dateFilter === '24h' ? now - 86_400_000 :
      dateFilter === '7d'  ? now - 7 * 86_400_000 :
      dateFilter === '30d' ? now - 30 * 86_400_000 : 0;
    const q = query.trim().toLowerCase();
    return items.filter((it) => {
      if (cutoff && it.at < cutoff) return false;
      if (statusFilter !== 'all') {
        if (statusFilter === 'live') {
          if (!(it.kind === 'session' && it.data.is_active)) return false;
        } else if (it.kind !== 'job' || it.data.status !== statusFilter) {
          return false;
        }
      }
      if (q) {
        const title =
          it.kind === 'job'
            ? (it.data.title || it.data.source_filename || it.data.id)
            : (it.data.title || it.data.id);
        if (!title.toLowerCase().includes(q)) return false;
      }
      return true;
    });
  }, [items, query, statusFilter, dateFilter]);

  const filtersActive =
    !!query.trim() || statusFilter !== 'all' || dateFilter !== 'all';

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

      {items === null ? (
        <ul className="grid gap-3" aria-busy="true" aria-live="polite">
          {Array.from({ length: 3 }).map((_, i) => (
            <li
              key={i}
              aria-hidden
              className="h-[76px] animate-pulse rounded-xl border border-border bg-surface-2/50"
            />
          ))}
        </ul>
      ) : items.length === 0 ? (
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
        <>
          <div
            role="search"
            className="grid gap-2 sm:grid-cols-[1fr_auto_auto_auto] sm:items-end"
          >
            <Field label={t('search.label')} htmlFor="dash-search">
              <div className="relative">
                <Search
                  aria-hidden
                  className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-fg"
                />
                <Input
                  id="dash-search"
                  value={query}
                  onChange={(e) => setQuery(e.target.value)}
                  placeholder={t('search.placeholder')}
                  className="pl-9 pr-9"
                />
                {query && (
                  <button
                    type="button"
                    onClick={() => setQuery('')}
                    aria-label={t('search.clear')}
                    className="absolute right-2 top-1/2 -translate-y-1/2 rounded-md p-1 text-muted-fg hover:text-fg focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
                  >
                    <X className="size-3.5" />
                  </button>
                )}
              </div>
            </Field>
            <Field label={t('filters.statusLabel')} htmlFor="dash-status">
              <Select
                id="dash-status"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value as typeof statusFilter)}
              >
                <option value="all">{t('filters.all')}</option>
                <option value="live">{t('filters.live')}</option>
                <option value="processing">{t('status.processing')}</option>
                <option value="completed">{t('status.completed')}</option>
                <option value="failed">{t('status.failed')}</option>
                <option value="pending">{t('status.pending')}</option>
              </Select>
            </Field>
            <Field label={t('filters.dateLabel')} htmlFor="dash-date">
              <Select
                id="dash-date"
                value={dateFilter}
                onChange={(e) => setDateFilter(e.target.value as typeof dateFilter)}
              >
                <option value="all">{t('filters.allTime')}</option>
                <option value="24h">{t('filters.last24h')}</option>
                <option value="7d">{t('filters.last7d')}</option>
                <option value="30d">{t('filters.last30d')}</option>
              </Select>
            </Field>
            {filtersActive && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  setQuery('');
                  setStatusFilter('all');
                  setDateFilter('all');
                }}
              >
                <X /> {t('filters.reset')}
              </Button>
            )}
          </div>

          {filtered && filtered.length === 0 ? (
            <Card>
              <CardBody className="flex flex-col items-center gap-2 py-10 text-center">
                <p className="text-sm font-semibold">{t('search.noResultsTitle')}</p>
                <p className="text-sm text-muted-fg">{t('search.noResultsBody')}</p>
              </CardBody>
            </Card>
          ) : (
            <ul className="grid gap-3">
              {filtered!.map((item) =>
                item.kind === 'job' ? (
                  <JobRow key={`j-${item.data.id}`} job={item.data} t={t} />
                ) : (
                  <SessionRow key={`s-${item.data.id}`} session={item.data} t={t} />
                )
              )}
            </ul>
          )}
        </>
      )}
    </div>
  );
}

function JobRow({ job, t }: { job: JobBrief; t: (k: string) => string }) {
  const title = job.title || job.source_filename || job.id.slice(0, 8);
  return (
    <li>
      <Link
        href={`/session/${job.id}`}
        className="group block rounded-xl border border-border bg-surface-1 p-4 shadow-xs transition-all hover:border-primary/40 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
      >
        <div className="flex items-center gap-3">
          <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary">
            <FileAudio className="size-4" aria-hidden />
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h2 className="truncate text-sm font-semibold text-fg">{title}</h2>
              <Badge tone={statusTone(job.status)} dot>
                {t(`status.${job.status}`)}
              </Badge>
            </div>
            <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-fg">
              <span>{new Date(job.created_at).toLocaleString()}</span>
              {job.duration_ms ? <span>· {formatDuration(job.duration_ms)}</span> : null}
              {job.status === 'processing' && <span>· {job.progress}%</span>}
            </div>
          </div>
          <ArrowUpRight
            aria-hidden
            className="size-4 text-muted-fg transition-colors group-hover:text-primary"
          />
        </div>
        {job.status === 'processing' && (
          <div
            className="mt-3 h-1 overflow-hidden rounded-full bg-muted-bg"
            role="progressbar"
            aria-label={`Processing ${title}`}
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={job.progress}
          >
            <div
              className="h-full rounded-full bg-primary transition-all duration-500 ease-out"
              style={{ width: `${job.progress}%` }}
            />
          </div>
        )}
      </Link>
    </li>
  );
}

function SessionRow({
  session,
  t,
}: {
  session: LiveSession;
  t: (k: string) => string;
}) {
  const title = session.title || `Live · ${session.id.slice(0, 8)}`;
  const active = session.is_active;
  const tone: 'info' | 'success' = active ? 'info' : 'success';
  const label = active ? t('status.processing') : t('status.completed');

  const body = (
    <div className="flex items-center gap-3">
      <div
        className={`flex size-9 shrink-0 items-center justify-center rounded-lg ${
          active ? 'bg-primary-soft text-primary' : 'bg-surface-2 text-muted-fg'
        }`}
      >
        {active ? <Radio className="size-4" aria-hidden /> : <Mic className="size-4" aria-hidden />}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <h2 className="truncate text-sm font-semibold text-fg">{title}</h2>
          <Badge tone={tone} dot>
            {label}
          </Badge>
          <span className="rounded-full border border-border bg-surface-2 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-fg">
            Live
          </span>
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-2 text-xs text-muted-fg">
          <span>{new Date(session.started_at).toLocaleString()}</span>
          {session.languages?.length ? (
            <span>· {session.languages.join(', ')}</span>
          ) : null}
        </div>
      </div>
      <ArrowUpRight
        aria-hidden
        className="size-4 text-muted-fg transition-colors group-hover:text-primary"
      />
    </div>
  );

  const href = `/session-live/${session.id}`;
  return (
    <li>
      <Link
        href={href}
        className="group block rounded-xl border border-border bg-surface-1 p-4 shadow-xs transition-all hover:border-primary/40 hover:shadow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40"
      >
        {body}
      </Link>
    </li>
  );
}
