'use client';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { CheckCircle2, ListChecks, FileText } from 'lucide-react';
import { jobsApi, type JobBrief, type Participant } from '@/lib/api';
import {
  Badge,
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardBody,
} from '@/components/ui/Card';
import { useAuth } from '@/lib/auth';
import { useToasts } from '@/components/ui/Toast';
import { TranscriptView } from '@/components/TranscriptView';
import { SpeakerEditor } from '@/components/SpeakerEditor';
import { ExportMenu } from '@/components/ExportMenu';
import { AudioPlayer } from '@/components/AudioPlayer';
import { GenerateReport } from '@/components/GenerateReport';
import { InsightsPanel } from '@/components/InsightsPanel';

export default function SessionPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations('session');
  const push = useToasts((s) => s.push);
  const token = useAuth((s) => s.token);
  const [job, setJob] = useState<JobBrief | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const r = await jobsApi.result(id);
      setJob(r.data);
    } catch (e: any) {
      push('error', e?.response?.data?.detail || 'Load failed');
    } finally {
      setLoading(false);
    }
  }, [id, push]);

  useEffect(() => {
    if (!token) return;
    load();
  }, [token, load]);

  useEffect(() => {
    if (!job) return;
    if (job.status === 'pending' || job.status === 'processing') {
      const iv = setInterval(load, 3000);
      return () => clearInterval(iv);
    }
  }, [job, load]);

  const speakersById = useMemo<Record<string, Participant>>(() => {
    const r = job?.result?.protocol?.participants || [];
    return Object.fromEntries(r.map((p) => [p.id, p]));
  }, [job]);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="h-8 w-48 animate-pulse rounded-md bg-muted-bg" />
        <div className="h-24 animate-pulse rounded-xl border border-border bg-surface-2/50" />
        <div className="h-40 animate-pulse rounded-xl border border-border bg-surface-2/50" />
      </div>
    );
  }
  if (!job) return <p className="text-muted-fg">Not found</p>;

  const statusTone = job.status === 'completed' ? 'success' : job.status === 'failed' ? 'danger' : 'info';

  const proto = job.result?.protocol;
  const meta = job.result?.metadata;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-4">
        <div className="min-w-0 space-y-2">
          <h1 className="truncate text-2xl font-semibold tracking-tight">
            {job.title || job.source_filename || 'Protocol'}
          </h1>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-fg">
            <Badge tone={statusTone} dot>{t(`status.${job.status}`)}</Badge>
            {job.status === 'processing' && (
              <span className="tabular-nums">{job.progress}%</span>
            )}
            {meta?.duration_ms ? (
              <span>· {Math.round(meta.duration_ms / 1000)}s</span>
            ) : null}
            {meta?.languages_detected?.length ? (
              <span>· {meta.languages_detected.join(', ').toUpperCase()}</span>
            ) : null}
          </div>
          {job.status === 'processing' && (
            <div
              className="h-1 w-64 overflow-hidden rounded-full bg-muted-bg"
              aria-hidden
            >
              <div
                className="h-full rounded-full bg-primary transition-all duration-500"
                style={{ width: `${job.progress}%` }}
              />
            </div>
          )}
        </div>
        {job.status === 'completed' && (
          <ExportMenu jobId={job.id} title={job.title || job.source_filename || undefined} />
        )}
      </header>

      <div className="grid gap-4 lg:grid-cols-2">
        <AudioPlayer jobId={job.id} />
        <GenerateReport
          jobId={job.id}
          title={job.title || job.source_filename || undefined}
          hasTranscript={Boolean(job.result?.transcript?.length)}
        />
      </div>

      {proto?.title || proto?.agenda?.length ? (
        <Card>
          <CardHeader>
            {proto?.title && <CardTitle>{proto.title}</CardTitle>}
            {proto?.date && <CardDescription>{proto.date}</CardDescription>}
          </CardHeader>
          {proto?.agenda?.length ? (
            <CardBody>
              <h3 className="mb-2 text-sm font-medium text-muted-fg">{t('agenda')}</h3>
              <ol className="list-decimal space-y-1 pl-5 text-sm text-fg marker:text-muted-fg">
                {proto.agenda.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ol>
            </CardBody>
          ) : null}
        </Card>
      ) : null}

      {proto?.decisions?.length ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="size-4 text-success" aria-hidden />
              {t('decisions')}
            </CardTitle>
          </CardHeader>
          <CardBody>
            <ol className="list-decimal space-y-2 pl-5 text-sm text-fg marker:text-muted-fg">
              {proto.decisions.map((d, i) => (
                <li key={i}>
                  <span>{d.text}</span>
                  {d.votes && (
                    <span className="ml-2 text-xs text-muted-fg">
                      ({t('voteFor')}: {d.votes.for ?? 0} · {t('voteAgainst')}: {d.votes.against ?? 0} · {t('voteAbstain')}: {d.votes.abstain ?? 0})
                    </span>
                  )}
                </li>
              ))}
            </ol>
          </CardBody>
        </Card>
      ) : null}

      {proto?.action_items?.length ? (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ListChecks className="size-4 text-primary" aria-hidden />
              {t('actions')}
            </CardTitle>
          </CardHeader>
          <CardBody>
            <ul className="space-y-2 text-sm">
              {proto.action_items.map((a, i) => (
                <li
                  key={i}
                  className="flex flex-wrap items-baseline gap-x-2 gap-y-1 rounded-lg border border-border bg-surface-1 px-3 py-2"
                >
                  <span className="font-medium text-fg">{a.task}</span>
                  {a.assignee ? (
                    <span className="text-muted-fg">— {a.assignee}</span>
                  ) : null}
                  {a.deadline ? (
                    <Badge tone="neutral" className="ml-auto">{a.deadline}</Badge>
                  ) : null}
                </li>
              ))}
            </ul>
          </CardBody>
        </Card>
      ) : null}

      {job.status === 'completed' && job.result?.transcript?.length ? (
        <InsightsPanel source={{ kind: 'job', id: job.id }} />
      ) : null}

      {proto?.participants?.length ? (
        <SpeakerEditor jobId={job.id} participants={proto.participants} onSaved={load} />
      ) : null}

      {job.result ? (
        <section aria-labelledby="tr-head">
          <div className="mb-3 flex items-center gap-2">
            <FileText className="size-4 text-muted-fg" aria-hidden />
            <h3 id="tr-head" className="text-base font-semibold tracking-tight">
              {t('transcript')}
            </h3>
          </div>
          <TranscriptView result={job.result} speakers={speakersById} />
        </section>
      ) : null}
    </div>
  );
}
