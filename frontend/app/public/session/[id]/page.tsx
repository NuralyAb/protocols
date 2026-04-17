'use client';
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Languages, Radio, AudioLines } from 'lucide-react';
import {
  sessionsApi,
  translateApi,
  type PublicSession,
  type TranscriptSegment,
  type TranslateLang,
} from '@/lib/api';
import { Card, CardBody, CardHeader, CardTitle, CardDescription, Badge } from '@/components/ui/Card';
import { Select } from '@/components/ui/Input';
import { cn } from '@/lib/cn';

type Segment = {
  id: number;
  start_ms: number;
  end_ms: number;
  speaker: string;
  language: string | null;
  text: string;
  pending?: boolean;
};

function mmss(ms: number) {
  const s = Math.max(0, Math.floor(ms / 1000));
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

export default function PublicSessionPage() {
  const t = useTranslations('publicViewer');
  const params = useParams<{ id: string }>();
  const search = useSearchParams();
  const sessionId = params?.id;
  const token = search?.get('token') || '';

  const [meta, setMeta] = useState<PublicSession | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [partial, setPartial] = useState('');
  const [connected, setConnected] = useState(false);
  const [translateTo, setTranslateTo] = useState<TranslateLang | 'off'>('off');
  const [translations, setTranslations] = useState<
    Record<string, { text?: string; error?: string; loading?: boolean }>
  >({});
  const inFlightRef = useRef<Set<string>>(new Set());
  const nextIdRef = useRef(1);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const reconnectAttemptRef = useRef(0);
  const stoppedRef = useRef(false);
  const transcriptListRef = useRef<HTMLOListElement>(null);
  const stickToBottomRef = useRef(true);

  const wsUrl = (process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000').replace(/\/$/, '');

  const seedFromHistory = useCallback(async () => {
    if (!sessionId || !token) return;
    try {
      const r = await sessionsApi.publicTranscript(sessionId, token);
      const items: Segment[] = (r.data.transcript ?? []).map((seg: TranscriptSegment) => ({
        id: nextIdRef.current++,
        start_ms: seg.start_time,
        end_ms: seg.end_time,
        speaker: seg.speaker,
        language: seg.language ?? null,
        text: seg.text,
      }));
      setSegments(items);
    } catch {
      // Polling history is best-effort; ignore failures.
    }
  }, [sessionId, token]);

  const connectWs = useCallback(() => {
    if (!sessionId || !token) return;
    const ws = new WebSocket(
      `${wsUrl}/ws/public/session/${sessionId}?token=${encodeURIComponent(token)}`,
    );
    wsRef.current = ws;
    ws.onopen = () => {
      setConnected(true);
      reconnectAttemptRef.current = 0;
    };
    ws.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data as string);
        if (data.type === 'partial') {
          setPartial((p) => (p + (data.text || '')).slice(-400));
          return;
        }
        if (data.type === 'utterance_queued') {
          setSegments((rs) => [
            ...rs,
            {
              id: nextIdRef.current++,
              start_ms: data.start_ms,
              end_ms: data.end_ms,
              speaker: 'SPEAKER_00',
              language: null,
              text: '…',
              pending: true,
            },
          ]);
        } else if (data.type === 'final') {
          setPartial('');
          setSegments((rs) => {
            const copy = [...rs];
            let idx = copy.findIndex(
              (r) => r.pending && r.start_ms === data.start_ms && r.end_ms === data.end_ms,
            );
            if (idx < 0) idx = copy.findIndex((r) => r.pending);
            const entry: Segment = {
              id: idx >= 0 ? copy[idx].id : nextIdRef.current++,
              start_ms: data.start_ms ?? (idx >= 0 ? copy[idx].start_ms : 0),
              end_ms: data.end_ms ?? (idx >= 0 ? copy[idx].end_ms : 0),
              speaker: data.speaker || 'SPEAKER_00',
              language: data.language,
              text: data.text,
              pending: false,
            };
            if (idx >= 0) copy[idx] = entry;
            else copy.push(entry);
            return copy;
          });
        } else if (data.type === 'ended') {
          setMeta((m) => (m ? { ...m, is_active: false } : m));
        }
      } catch {}
    };
    ws.onclose = () => {
      wsRef.current = null;
      setConnected(false);
      if (stoppedRef.current) return;
      const attempt = Math.min(reconnectAttemptRef.current + 1, 6);
      reconnectAttemptRef.current = attempt;
      const delay = Math.min(30_000, 800 * 2 ** (attempt - 1));
      reconnectTimerRef.current = setTimeout(() => {
        if (stoppedRef.current) return;
        connectWs();
      }, delay);
    };
    ws.onerror = () => {};
  }, [sessionId, token, wsUrl]);

  useEffect(() => {
    if (!sessionId || !token) {
      setError(t('missingToken'));
      return;
    }
    stoppedRef.current = false;
    let alive = true;
    sessionsApi
      .publicMeta(sessionId, token)
      .then((r) => {
        if (alive) setMeta(r.data);
      })
      .catch((e) => {
        if (alive)
          setError(e?.response?.status === 404 ? t('notFound') : t('loadError'));
      });
    seedFromHistory().then(() => {
      if (!alive) return;
      connectWs();
    });
    return () => {
      alive = false;
      stoppedRef.current = true;
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      try {
        wsRef.current?.close();
      } catch {}
    };
  }, [sessionId, token, t, seedFromHistory, connectWs]);

  useEffect(() => {
    if (translateTo === 'off') return;
    const target = translateTo;
    segments.forEach((seg) => {
      if (seg.pending || !seg.text?.trim()) return;
      const src = (seg.language || '').toLowerCase();
      if (src && src === target) return;
      const key = `${seg.id}:${target}`;
      if (inFlightRef.current.has(key)) return;
      if (translations[key]?.text || translations[key]?.error) return;
      inFlightRef.current.add(key);
      setTranslations((prev) => ({ ...prev, [key]: { loading: true } }));
      translateApi
        .translate({ text: seg.text, source: src || null, target })
        .then((r) =>
          setTranslations((prev) => ({ ...prev, [key]: { text: r.data.text } })),
        )
        .catch((e) =>
          setTranslations((prev) => ({
            ...prev,
            [key]: { error: e?.response?.data?.detail || 'translation failed' },
          })),
        )
        .finally(() => inFlightRef.current.delete(key));
    });
  }, [segments, translateTo, translations]);

  const onScroll = useCallback(() => {
    const el = transcriptListRef.current;
    if (!el) return;
    stickToBottomRef.current = el.scrollHeight - el.scrollTop - el.clientHeight < 80;
  }, []);

  useLayoutEffect(() => {
    if (!stickToBottomRef.current) return;
    const el = transcriptListRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [segments]);

  if (error) {
    return (
      <div className="mx-auto max-w-md py-16 text-center">
        <h1 className="text-xl font-semibold">{t('errorTitle')}</h1>
        <p className="mt-2 text-sm text-muted-fg">{error}</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <header className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-end sm:justify-between">
        <div className="space-y-1">
          <p className="inline-flex items-center gap-1.5 text-xs font-medium uppercase tracking-wider text-muted-fg">
            <AudioLines className="size-3.5" aria-hidden /> {t('viewerLabel')}
          </p>
          <h1 className="text-2xl font-semibold tracking-tight">
            {meta?.title || t('untitled')}
          </h1>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-fg">
            {meta?.is_active ? (
              <Badge tone="info" dot>
                <Radio className="size-3" aria-hidden /> {t('live')}
              </Badge>
            ) : (
              <Badge tone="neutral">{t('ended')}</Badge>
            )}
            {meta?.languages?.length ? (
              <span>{meta.languages.join(', ').toUpperCase()}</span>
            ) : null}
            {connected ? (
              <span className="text-success">{t('connected')}</span>
            ) : (
              <span>{t('connecting')}</span>
            )}
          </div>
        </div>
        <label className="inline-flex items-center gap-1.5 text-xs text-muted-fg">
          <Languages className="size-3.5" aria-hidden />
          <span>{t('translate.label')}</span>
          <Select
            value={translateTo}
            onChange={(e) => setTranslateTo(e.target.value as TranslateLang | 'off')}
            className="h-8 text-xs"
          >
            <option value="off">{t('translate.off')}</option>
            <option value="ru">RU</option>
            <option value="kk">KK</option>
            <option value="en">EN</option>
          </Select>
        </label>
      </header>

      <Card>
        <CardHeader>
          <CardTitle>{t('transcriptTitle')}</CardTitle>
          <CardDescription>{t('transcriptHint')}</CardDescription>
        </CardHeader>
        <CardBody>
          {partial && (
            <p className="mb-3 rounded-lg border border-dashed border-border bg-surface-2/60 p-3 text-sm italic text-muted-fg">
              {partial}
              <span className="ml-0.5 inline-block w-[1ch] animate-pulse">▍</span>
            </p>
          )}
          {segments.length === 0 && !partial ? (
            <p className="py-12 text-center text-sm text-muted-fg">{t('waiting')}</p>
          ) : (
            <ol
              ref={transcriptListRef}
              onScroll={onScroll}
              aria-live="polite"
              className="max-h-[60vh] space-y-2 overflow-y-auto pr-1 scroll-smooth sm:max-h-[70vh]"
            >
              {segments.map((s) => {
                const tk = translateTo !== 'off' ? `${s.id}:${translateTo}` : '';
                const tEntry = tk ? translations[tk] : undefined;
                const sameLang =
                  translateTo !== 'off' &&
                  (s.language || '').toLowerCase() === translateTo;
                return (
                  <li
                    key={s.id}
                    className={cn(
                      'rounded-lg border border-border bg-surface-1 p-3 transition-opacity',
                      s.pending && 'opacity-60',
                    )}
                  >
                    <div className="flex flex-wrap items-center gap-2 text-xs text-muted-fg">
                      <span className="font-mono">{mmss(s.start_ms)}</span>
                      <span className="font-semibold text-fg">{s.speaker}</span>
                      {s.language && <span>· {s.language}</span>}
                    </div>
                    <p className="mt-1 captions whitespace-pre-wrap text-sm text-fg">
                      {s.text}
                      {s.pending && <span className="animate-pulse"> …</span>}
                    </p>
                    {translateTo !== 'off' && !s.pending && !sameLang && (
                      <div
                        className="mt-2 border-t border-dashed border-border pt-2 text-sm"
                        aria-live="polite"
                      >
                        <div className="mb-0.5 flex items-center gap-1.5 text-[10px] font-medium uppercase tracking-wide text-muted-fg">
                          <Languages className="size-3" aria-hidden />
                          <span>{translateTo}</span>
                        </div>
                        {tEntry?.text ? (
                          <p className="captions whitespace-pre-wrap text-fg/80">{tEntry.text}</p>
                        ) : tEntry?.error ? (
                          <p className="text-xs text-danger">{tEntry.error}</p>
                        ) : (
                          <p className="text-xs italic text-muted-fg">{t('translate.loading')}</p>
                        )}
                      </div>
                    )}
                  </li>
                );
              })}
            </ol>
          )}
        </CardBody>
      </Card>
    </div>
  );
}
