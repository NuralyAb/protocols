'use client';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Download, FileAudio, AlertTriangle } from 'lucide-react';
import { jobsApi, type JobAudio } from '@/lib/api';
import { Card, CardHeader, CardTitle, CardDescription, CardBody } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';

function formatDuration(ms?: number | null) {
  if (!ms || ms <= 0) return null;
  const total = Math.floor(ms / 1000);
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  return h > 0
    ? `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
    : `${m}:${String(s).padStart(2, '0')}`;
}

export function AudioPlayer({ jobId }: { jobId: string }) {
  const t = useTranslations('session.recording');
  const [data, setData] = useState<JobAudio | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    jobsApi
      .audio(jobId)
      .then((r) => alive && setData(r.data))
      .catch((e) => {
        if (!alive) return;
        if (e?.response?.status === 404) setError(t('unavailable'));
        else setError(e?.response?.data?.detail || t('loadError'));
      });
    return () => {
      alive = false;
    };
  }, [jobId, t]);

  return (
    <Card>
      <CardHeader className="flex-row items-center justify-between gap-3">
        <div>
          <CardTitle className="flex items-center gap-2">
            <FileAudio className="size-4 text-primary" aria-hidden />
            {t('title')}
          </CardTitle>
          <CardDescription>{t('description')}</CardDescription>
        </div>
        {data && (
          <a href={data.download_url} download={data.filename}>
            <Button size="sm" variant="secondary">
              <Download /> {t('download')}
            </Button>
          </a>
        )}
      </CardHeader>
      <CardBody>
        {error ? (
          <div className="flex items-center gap-2 rounded-lg border border-dashed border-border bg-surface-2/50 p-4 text-sm text-muted-fg">
            <AlertTriangle className="size-4 text-warning" aria-hidden />
            {error}
          </div>
        ) : !data ? (
          <div className="h-14 animate-pulse rounded-lg bg-muted-bg" />
        ) : (
          <div className="space-y-2">
            <audio
              controls
              preload="metadata"
              src={data.url}
              className="w-full rounded-lg"
              aria-label={data.filename}
            >
              {t('unsupported')}
            </audio>
            <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-muted-fg">
              <span className="truncate font-mono">{data.filename}</span>
              {formatDuration(data.duration_ms) && (
                <span className="tabular-nums">{formatDuration(data.duration_ms)}</span>
              )}
            </div>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
