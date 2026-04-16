'use client';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { jobsApi, type JobBrief, type Participant } from '@/lib/api';
import { Card, Badge } from '@/components/ui/Card';
import { useAuth } from '@/lib/auth';
import { useToasts } from '@/components/ui/Toast';
import { TranscriptView } from '@/components/TranscriptView';
import { SpeakerEditor } from '@/components/SpeakerEditor';
import { ExportMenu } from '@/components/ExportMenu';

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

  if (loading) return <p className="text-muted">…</p>;
  if (!job) return <p className="text-muted">Not found</p>;

  const statusTone = job.status === 'completed' ? 'success' : job.status === 'failed' ? 'danger' : 'info';

  const proto = job.result?.protocol;
  const meta = job.result?.metadata;

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">{job.title || job.source_filename || 'Protocol'}</h1>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-sm text-muted">
            <Badge tone={statusTone}>{t(`status.${job.status}`)}</Badge>
            {job.status === 'processing' && <span>{job.progress}%</span>}
            {meta?.duration_ms ? <span>• {Math.round(meta.duration_ms / 1000)}s</span> : null}
            {meta?.languages_detected?.length ? (
              <span>• {meta.languages_detected.join(', ')}</span>
            ) : null}
          </div>
          {job.status === 'processing' && (
            <div className="mt-2 h-1.5 w-64 overflow-hidden rounded-full bg-muted/20" aria-hidden>
              <div className="h-full bg-accent transition-all" style={{ width: `${job.progress}%` }} />
            </div>
          )}
        </div>
        {job.status === 'completed' && (
          <ExportMenu jobId={job.id} title={job.title || job.source_filename || undefined} />
        )}
      </header>

      {proto?.title || proto?.agenda?.length ? (
        <Card>
          {proto.title && <h2 className="text-lg font-semibold">{proto.title}</h2>}
          {proto.date && <p className="text-sm text-muted">{proto.date}</p>}
          {proto.agenda?.length ? (
            <>
              <h3 className="mt-4 font-medium">{t('agenda')}</h3>
              <ol className="mt-1 list-decimal pl-5">
                {proto.agenda.map((a, i) => (
                  <li key={i}>{a}</li>
                ))}
              </ol>
            </>
          ) : null}
        </Card>
      ) : null}

      {proto?.decisions?.length ? (
        <Card>
          <h3 className="font-medium">{t('decisions')}</h3>
          <ol className="mt-2 list-decimal space-y-1 pl-5">
            {proto.decisions.map((d, i) => (
              <li key={i}>
                {d.text}
                {d.votes && (
                  <span className="ml-2 text-xs text-muted">
                    ({t('voteFor')}: {d.votes.for ?? 0} · {t('voteAgainst')}: {d.votes.against ?? 0} · {t('voteAbstain')}: {d.votes.abstain ?? 0})
                  </span>
                )}
              </li>
            ))}
          </ol>
        </Card>
      ) : null}

      {proto?.action_items?.length ? (
        <Card>
          <h3 className="font-medium">{t('actions')}</h3>
          <ul className="mt-2 space-y-1 text-sm">
            {proto.action_items.map((a, i) => (
              <li key={i}>
                <strong>{a.task}</strong>
                {a.assignee ? ` — ${a.assignee}` : ''}
                {a.deadline ? ` · ${a.deadline}` : ''}
              </li>
            ))}
          </ul>
        </Card>
      ) : null}

      {proto?.participants?.length ? (
        <SpeakerEditor jobId={job.id} participants={proto.participants} onSaved={load} />
      ) : null}

      {job.result ? (
        <section aria-labelledby="tr-head">
          <h3 id="tr-head" className="mb-2 text-lg font-medium">{t('transcript')}</h3>
          <TranscriptView result={job.result} speakers={speakersById} />
        </section>
      ) : null}
    </div>
  );
}
