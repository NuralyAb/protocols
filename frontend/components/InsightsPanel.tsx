'use client';
import { useEffect, useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import {
  BarChart3,
  Cloud,
  Sparkles,
  Vote,
  CheckCircle2,
  AlertTriangle,
  Lightbulb,
  Star,
} from 'lucide-react';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import {
  jobsApi,
  sessionsApi,
  type Insights,
  type KeyMoment,
  type KeyMomentKind,
} from '@/lib/api';
import { Card, CardBody, CardHeader, CardTitle, CardDescription, Badge } from '@/components/ui/Card';
import { useToasts } from '@/components/ui/Toast';

type Source = { kind: 'session' | 'job'; id: string };

const PALETTE = [
  '#6366f1', '#22c55e', '#f59e0b', '#ec4899', '#06b6d4',
  '#a855f7', '#ef4444', '#14b8a6', '#eab308', '#8b5cf6',
];

const KIND_ICON: Record<KeyMomentKind, typeof CheckCircle2> = {
  decision: CheckCircle2,
  disagreement: AlertTriangle,
  vote: Vote,
  proposal: Lightbulb,
  highlight: Star,
};

const KIND_TONE: Record<KeyMomentKind, 'success' | 'danger' | 'info' | 'warning' | 'neutral'> = {
  decision: 'success',
  disagreement: 'danger',
  vote: 'info',
  proposal: 'warning',
  highlight: 'neutral',
};

function mmss(ms: number) {
  const s = Math.max(0, Math.floor(ms / 1000));
  const m = Math.floor(s / 60);
  return `${String(m).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

function speakingMs(ms: number) {
  const s = Math.floor(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const r = s % 60;
  return r === 0 ? `${m}m` : `${m}m ${r}s`;
}

export function InsightsPanel({ source }: { source: Source }) {
  const t = useTranslations('insights');
  const push = useToasts((s) => s.push);
  const [data, setData] = useState<Insights | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function load(opts?: { keyMoments?: boolean }) {
    setLoading(true);
    setError(null);
    try {
      const r =
        source.kind === 'session'
          ? await sessionsApi.insights(source.id, opts)
          : await jobsApi.insights(source.id, opts);
      setData(r.data);
    } catch (e: any) {
      const msg = e?.response?.data?.detail || t('loadError');
      setError(msg);
      push('error', msg);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load({ keyMoments: true });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [source.kind, source.id]);

  const pieData = useMemo(
    () =>
      (data?.speakers ?? []).map((s) => ({
        name: s.label,
        value: Math.max(1, s.speaking_ms),
        share: s.share,
      })),
    [data?.speakers],
  );

  const wordsTop = useMemo(() => (data?.top_words ?? []).slice(0, 30), [data?.top_words]);
  const maxCount = wordsTop[0]?.count ?? 1;

  if (loading && !data) {
    return (
      <Card>
        <CardBody>
          <div className="grid gap-3 sm:grid-cols-2" aria-busy="true" aria-live="polite">
            <div className="h-44 animate-pulse rounded-lg bg-surface-2/50" />
            <div className="h-44 animate-pulse rounded-lg bg-surface-2/50" />
          </div>
        </CardBody>
      </Card>
    );
  }

  if (error && !data) {
    return (
      <Card>
        <CardBody className="text-center text-sm text-muted-fg">{error}</CardBody>
      </Card>
    );
  }

  if (!data) return null;

  if (data.totals.segments === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t('title')}</CardTitle>
          <CardDescription>{t('emptyHint')}</CardDescription>
        </CardHeader>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="flex flex-col gap-1 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <CardTitle className="inline-flex items-center gap-2">
            <Sparkles className="size-4 text-primary" aria-hidden /> {t('title')}
          </CardTitle>
          <CardDescription>{t('subtitle')}</CardDescription>
        </div>
        <div className="text-xs text-muted-fg">
          {t('totalsLine', {
            segments: data.totals.segments,
            speakers: data.totals.speakers,
            duration: mmss(data.totals.speaking_ms),
          })}
        </div>
      </CardHeader>
      <CardBody className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-2">
          <section aria-labelledby="who-spoke">
            <h3
              id="who-spoke"
              className="mb-2 inline-flex items-center gap-2 text-sm font-semibold"
            >
              <BarChart3 className="size-4 text-muted-fg" aria-hidden /> {t('whoSpoke')}
            </h3>
            <div className="grid gap-3 sm:grid-cols-[180px_1fr]">
              <div className="h-[180px]">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={pieData}
                      dataKey="value"
                      nameKey="name"
                      innerRadius={42}
                      outerRadius={72}
                      stroke="hsl(var(--surface-1))"
                      strokeWidth={2}
                    >
                      {pieData.map((_, i) => (
                        <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: 'hsl(var(--surface-1))',
                        border: '1px solid hsl(var(--border))',
                        borderRadius: 8,
                        fontSize: 12,
                      }}
                      formatter={(v: any, _n: any, item: any) => [
                        `${speakingMs(Number(v))} (${Math.round((item?.payload?.share ?? 0) * 100)}%)`,
                        item?.payload?.name,
                      ]}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <ul className="space-y-1.5 text-sm">
                {data.speakers.map((sp, i) => (
                  <li key={sp.id} className="flex items-center gap-2">
                    <span
                      aria-hidden
                      className="size-2.5 shrink-0 rounded-full"
                      style={{ background: PALETTE[i % PALETTE.length] }}
                    />
                    <span className="min-w-0 flex-1 truncate font-medium text-fg">{sp.label}</span>
                    <span className="tabular-nums text-xs text-muted-fg">
                      {Math.round(sp.share * 100)}% · {speakingMs(sp.speaking_ms)}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          <section aria-labelledby="word-cloud">
            <h3
              id="word-cloud"
              className="mb-2 inline-flex items-center gap-2 text-sm font-semibold"
            >
              <Cloud className="size-4 text-muted-fg" aria-hidden /> {t('topics')}
            </h3>
            {wordsTop.length === 0 ? (
              <p className="text-sm text-muted-fg">{t('noWords')}</p>
            ) : (
              <ul className="flex flex-wrap items-baseline gap-x-2 gap-y-1.5">
                {wordsTop.map((w) => {
                  const scale = 0.85 + (w.count / maxCount) * 0.95;
                  return (
                    <li key={w.word}>
                      <span
                        title={`${w.count}`}
                        className="rounded-md text-fg/80 transition-colors hover:text-primary"
                        style={{ fontSize: `${scale}rem`, lineHeight: 1.1 }}
                      >
                        {w.word}
                      </span>
                    </li>
                  );
                })}
              </ul>
            )}
          </section>
        </div>

        {data.key_moments.length > 0 && (
          <section aria-labelledby="key-moments">
            <h3
              id="key-moments"
              className="mb-2 inline-flex items-center gap-2 text-sm font-semibold"
            >
              <Sparkles className="size-4 text-muted-fg" aria-hidden /> {t('keyMoments')}
            </h3>
            <ol className="space-y-2">
              {data.key_moments.map((m, i) => (
                <KeyMomentRow key={i} moment={m} speakers={data.speakers} />
              ))}
            </ol>
          </section>
        )}
      </CardBody>
    </Card>
  );
}

function KeyMomentRow({
  moment,
  speakers,
}: {
  moment: KeyMoment;
  speakers: Insights['speakers'];
}) {
  const Icon = KIND_ICON[moment.kind] || Star;
  const tone = KIND_TONE[moment.kind] || 'neutral';
  const speaker = speakers.find((s) => s.id === moment.speaker);
  return (
    <li className="rounded-lg border border-border bg-surface-1 p-3">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 inline-flex size-7 shrink-0 items-center justify-center rounded-md bg-primary-soft text-primary">
          <Icon className="size-4" aria-hidden />
        </span>
        <div className="min-w-0 flex-1 space-y-1">
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-fg">
            <span className="font-mono text-fg">{mmss(moment.at_ms)}</span>
            {speaker && <span className="font-medium">{speaker.label}</span>}
            <Badge tone={tone}>{moment.kind}</Badge>
          </div>
          <p className="text-sm text-fg">{moment.summary}</p>
        </div>
      </div>
    </li>
  );
}
