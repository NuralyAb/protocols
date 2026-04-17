'use client';
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Mic, Square, Radio, WifiOff, RefreshCw, Languages } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import {
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  CardDescription,
  Badge,
} from '@/components/ui/Card';
import { Input, Select, Field, Chip } from '@/components/ui/Input';
import { useAuth } from '@/lib/auth';
import { useToasts } from '@/components/ui/Toast';
import {
  sessionsApi,
  translateApi,
  type AsrProvider,
  type LiveSession,
  type ProtocolFormat,
  type ProtocolTemplate,
  type TranslateLang,
} from '@/lib/api';
import { startMic, type MicStream } from '@/lib/mic';
import { Waveform } from '@/components/Waveform';
import { TemplateGallery } from '@/components/TemplateGallery';
import { ShareViewerCard } from '@/components/ShareViewerCard';
import { InsightsPanel } from '@/components/InsightsPanel';
import { cn } from '@/lib/cn';

type Segment = {
  id: number;
  start_ms: number;
  end_ms: number;
  speaker: string;
  language: string | null;
  text: string;
  confidence?: number | null;
  pending?: boolean;
};

function mmss(ms: number) {
  const s = Math.floor(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

const PROVIDER_LABELS: Record<AsrProvider, string> = {
  openai: 'OpenAI Realtime',
  openai_transcribe: 'gpt-4o-transcribe',
  openai_whisper: 'whisper-1',
  hf_space: 'HF Space',
  hf_kazakh: 'HF Kazakh',
  local_kazakh: 'Local Kazakh',
  local: 'Local GPU',
};

export default function LivePage() {
  const t = useTranslations('live');
  const token = useAuth((s) => s.token);
  const push = useToasts((s) => s.push);

  const [session, setSession] = useState<LiveSession | null>(null);
  const [title, setTitle] = useState('');
  const [langs, setLangs] = useState({ kk: true, ru: true, en: false });
  const [provider, setProvider] = useState<AsrProvider>('openai');
  const [partial, setPartial] = useState<string>('');
  const [recording, setRecording] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const [nextRetryAt, setNextRetryAt] = useState<number | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);

  const wsRef = useRef<WebSocket | null>(null);
  const micRef = useRef<MicStream | null>(null);
  const nextIdRef = useRef(1);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const userStoppedRef = useRef(false);

  const [templates, setTemplates] = useState<ProtocolTemplate[]>([]);
  const [templateId, setTemplateId] = useState<string>('');
  const [protoFormat, setProtoFormat] = useState<ProtocolFormat>('markdown');
  const [protoLoading, setProtoLoading] = useState(false);
  const [protoMarkdown, setProtoMarkdown] = useState<string>('');

  const [translateTo, setTranslateTo] = useState<TranslateLang | 'off'>('off');
  // segment.id -> { text } | { error }; one entry per (segId, target).
  const [translations, setTranslations] = useState<
    Record<string, { text?: string; error?: string; loading?: boolean }>
  >({});
  const inFlightRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    sessionsApi
      .listTemplates()
      .then((r) => {
        setTemplates(r.data);
        if (r.data.length && !templateId) setTemplateId(r.data[0].id);
      })
      .catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  const transcriptListRef = useRef<HTMLOListElement>(null);
  const stickToBottomRef = useRef(true);

  const wsUrl = (process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000').replace(/\/$/, '');

  async function create() {
    const active = Object.entries(langs).filter(([, v]) => v).map(([k]) => k);
    if (!active.length) return push('error', t('selectLang'));
    try {
      const r = await sessionsApi.create({
        title: title || undefined,
        languages: active,
        asr_provider: provider,
      });
      setSession(r.data);
      setSegments([]);
      push('success', t('sessionCreated'));
    } catch (e: any) {
      push('error', e?.response?.data?.detail || t('error'));
    }
  }

  const cleanupWs = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    try {
      wsRef.current?.close();
    } catch {}
    wsRef.current = null;
  }, []);

  const stop = useCallback(async () => {
    userStoppedRef.current = true;
    try {
      wsRef.current?.send(JSON.stringify({ type: 'end' }));
    } catch {}
    cleanupWs();
    await micRef.current?.stop();
    micRef.current = null;
    setRecording(false);
    setReconnecting(false);
    setReconnectAttempt(0);
    setNextRetryAt(null);
    reconnectAttemptRef.current = 0;
  }, [cleanupWs]);

  const connectWs = useCallback(
    (sessionId: string, onReady: () => void) => {
      if (!token) return;
      const ws = new WebSocket(`${wsUrl}/ws/session/${sessionId}?token=${encodeURIComponent(token)}`);
      ws.binaryType = 'arraybuffer';
      wsRef.current = ws;

      let opened = false;
      ws.onopen = () => {
        opened = true;
        reconnectAttemptRef.current = 0;
        setReconnecting(false);
        setReconnectAttempt(0);
        setNextRetryAt(null);
        onReady();
      };
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data as string);
          if (data.type === 'partial') {
            setPartial((prev) => (prev + (data.text || '')).slice(-400));
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
                (r) => r.pending && r.start_ms === data.start_ms && r.end_ms === data.end_ms
              );
              if (idx < 0) idx = copy.findIndex((r) => r.pending);
              const entry: Segment = {
                id: idx >= 0 ? copy[idx].id : nextIdRef.current++,
                start_ms: data.start_ms ?? (idx >= 0 ? copy[idx].start_ms : 0),
                end_ms: data.end_ms ?? (idx >= 0 ? copy[idx].end_ms : 0),
                speaker: data.speaker || 'SPEAKER_00',
                language: data.language,
                text: data.text,
                confidence: data.confidence,
                pending: false,
              };
              if (idx >= 0) copy[idx] = entry;
              else copy.push(entry);
              return copy;
            });
          } else if (data.type === 'error') {
            push('error', data.message || 'ASR error');
          }
        } catch {}
      };
      ws.onclose = (e) => {
        wsRef.current = null;
        if (userStoppedRef.current) return;
        if (opened && micRef.current?.isRunning()) {
          const attempt = Math.min(reconnectAttemptRef.current + 1, 6);
          reconnectAttemptRef.current = attempt;
          const delay = Math.min(30_000, 500 * 2 ** (attempt - 1));
          setReconnecting(true);
          setReconnectAttempt(attempt);
          setNextRetryAt(Date.now() + delay);
          reconnectTimerRef.current = setTimeout(() => {
            if (userStoppedRef.current) return;
            connectWs(sessionId, () => {});
          }, delay);
        } else if (!opened) {
          push('error', `WS closed (${e.code})`);
        }
      };
      ws.onerror = () => {};
    },
    [token, wsUrl, push]
  );

  const manualReconnect = useCallback(() => {
    if (!session) return;
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    setNextRetryAt(null);
    reconnectAttemptRef.current = 0;
    setReconnectAttempt(0);
    setReconnecting(true);
    connectWs(session.id, () => {});
  }, [session, connectWs]);

  const [retryCountdown, setRetryCountdown] = useState<number>(0);
  useEffect(() => {
    if (!nextRetryAt) {
      setRetryCountdown(0);
      return;
    }
    const tick = () => setRetryCountdown(Math.max(0, Math.ceil((nextRetryAt - Date.now()) / 1000)));
    tick();
    const id = setInterval(tick, 500);
    return () => clearInterval(id);
  }, [nextRetryAt]);

  async function start() {
    if (!session || !token) return;
    setConnecting(true);
    userStoppedRef.current = false;
    try {
      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error('ws_open_timeout')), 8000);
        connectWs(session.id, () => {
          clearTimeout(timeout);
          resolve();
        });
      });
      const mic = await startMic((buf) => {
        const ws = wsRef.current;
        if (ws && ws.readyState === WebSocket.OPEN) ws.send(buf);
      });
      micRef.current = mic;
      setRecording(true);
    } catch (e: any) {
      push('error', e?.message || 'mic/ws failed');
      await stop();
    } finally {
      setConnecting(false);
    }
  }

  useEffect(() => () => { stop(); }, [stop]);

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

  async function generateProtocol() {
    if (!session || !templateId) return;
    setProtoLoading(true);
    setProtoMarkdown('');
    try {
      const r = await sessionsApi.generateProtocol(session.id, templateId, protoFormat);
      const blob = r.data as Blob;
      const safe = (session.title || 'protocol').replace(/[^\p{L}\p{N}_.-]+/gu, '_');
      if (protoFormat === 'markdown') {
        const text = await blob.text();
        setProtoMarkdown(text);
      } else {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${safe}.${protoFormat}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      }
      push('success', t('protocol.done'));
    } catch (e: any) {
      let msg = t('protocol.error');
      const data = e?.response?.data;
      if (data) {
        try {
          const text = data instanceof Blob ? await data.text() : JSON.stringify(data);
          const parsed = JSON.parse(text);
          msg = parsed?.detail || msg;
        } catch {}
      }
      push('error', msg);
    } finally {
      setProtoLoading(false);
    }
  }

  async function downloadSnapshot(format: 'pdf' | 'docx' | 'json' | 'txt' | 'srt' | 'vtt') {
    if (!session || !token) return;
    const r = await fetch(sessionsApi.exportUrl(session.id, format), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!r.ok) return push('error', 'Export failed');
    const blob = await r.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${session.title || 'session'}.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  if (!session) {
    return (
      <div className="mx-auto w-full max-w-xl space-y-6">
        <header className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
          <p className="text-muted-fg">{t('subtitle')}</p>
        </header>

        <Card>
          <CardHeader>
            <CardTitle>New session</CardTitle>
            <CardDescription>
              Choose languages and provider before starting to record.
            </CardDescription>
          </CardHeader>
          <CardBody className="space-y-5">
            <Field label={t('sessionTitle')} htmlFor="session-title">
              <Input
                id="session-title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={t('sessionTitlePh')}
              />
            </Field>

            <fieldset className="space-y-2">
              <legend className="text-sm font-medium">{t('languages')}</legend>
              <div className="flex flex-wrap gap-2">
                {(['kk', 'ru', 'en'] as const).map((k) => (
                  <Chip
                    key={k}
                    active={langs[k]}
                    onClick={() => setLangs((s) => ({ ...s, [k]: !s[k] }))}
                  >
                    {k.toUpperCase()}
                  </Chip>
                ))}
              </div>
            </fieldset>

            <Field
              label={t('providerLabel')}
              htmlFor="provider"
              hint={
                provider === 'openai'
                  ? t('providerOpenaiHint')
                  : provider === 'openai_transcribe'
                  ? t('providerOpenaiTranscribeHint')
                  : provider === 'hf_space'
                  ? t('providerHfSpaceHint')
                  : provider === 'hf_kazakh'
                  ? t('providerHfKazakhHint')
                  : provider === 'local_kazakh'
                  ? t('providerLocalKazakhHint')
                  : t('providerLocalHint')
              }
            >
              <Select
                id="provider"
                value={provider}
                onChange={(e) => setProvider(e.target.value as AsrProvider)}
              >
                <option value="openai">{t('providerOpenai')}</option>
                <option value="openai_transcribe">{t('providerOpenaiTranscribe')}</option>
                <option value="hf_space">{t('providerHfSpace')}</option>
                <option value="hf_kazakh">{t('providerHfKazakh')}</option>
                <option value="local_kazakh">{t('providerLocalKazakh')}</option>
                <option value="local">{t('providerLocal')}</option>
              </Select>
            </Field>
          </CardBody>
          <div className="flex items-center justify-end gap-2 border-t border-border px-5 py-3">
            <Button onClick={create}>
              <Radio /> {t('createSession')}
            </Button>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <header className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-1">
          <h1 className="truncate text-xl font-semibold tracking-tight sm:text-2xl">
            {session.title || t('title')}
          </h1>
          <div className="flex flex-wrap items-center gap-2 text-xs text-muted-fg">
            <span className="font-mono">{session.id.slice(0, 8)}</span>
            <span aria-hidden>•</span>
            <span>{session.languages?.join(', ').toUpperCase()}</span>
            {session.asr_provider && (
              <>
                <span aria-hidden>•</span>
                <Badge tone="neutral">{PROVIDER_LABELS[session.asr_provider]}</Badge>
              </>
            )}
          </div>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:flex-nowrap">
          {recording ? (
            <>
              {reconnecting ? (
                <Badge tone="warning" dot>{t('reconnecting')}</Badge>
              ) : (
                <Badge tone="danger" dot>{t('recording')}</Badge>
              )}
              <Button variant="danger" onClick={stop} className="flex-1 sm:flex-none">
                <Square /> {t('stop')}
              </Button>
            </>
          ) : (
            <Button onClick={start} loading={connecting} className="flex-1 sm:flex-none">
              <Mic /> {t('start')}
            </Button>
          )}
        </div>
      </header>

      <ShareViewerCard sessionId={session.id} />

      {recording && reconnecting && (
        <div
          role="alert"
          aria-live="assertive"
          className="flex flex-wrap items-center gap-3 rounded-xl border border-warning/40 bg-warning-soft px-4 py-3 text-sm"
        >
          <WifiOff className="size-4 shrink-0 text-warning" aria-hidden />
          <div className="min-w-0 flex-1">
            <p className="font-medium text-fg">{t('connection.lostTitle')}</p>
            <p className="text-xs text-muted-fg">
              {retryCountdown > 0
                ? t('connection.retryingIn', { seconds: retryCountdown, attempt: reconnectAttempt })
                : t('connection.retryingNow', { attempt: reconnectAttempt })}
            </p>
          </div>
          <Button size="sm" variant="outline" onClick={manualReconnect}>
            <RefreshCw /> {t('connection.reconnect')}
          </Button>
        </div>
      )}

      {recording && micRef.current && (
        <Waveform
          active={recording && !reconnecting}
          read={(bins) => micRef.current!.getLevels(bins)}
        />
      )}

      <Card>
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center sm:justify-between">
          <div>
            <CardTitle>{t('liveTranscript')}</CardTitle>
            <CardDescription>{t('snapshotHint')}</CardDescription>
          </div>
          <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap sm:items-center">
            <label className="inline-flex items-center gap-1.5 text-xs text-muted-fg">
              <Languages className="size-3.5" aria-hidden />
              <span className="sr-only sm:not-sr-only">{t('translate.label')}</span>
              <Select
                value={translateTo}
                onChange={(e) => setTranslateTo(e.target.value as TranslateLang | 'off')}
                className="h-8 text-xs"
                aria-label={t('translate.label')}
              >
                <option value="off">{t('translate.off')}</option>
                <option value="ru">RU</option>
                <option value="kk">KK</option>
                <option value="en">EN</option>
              </Select>
            </label>
            <div className="grid grid-cols-3 gap-1.5 sm:flex sm:flex-wrap">
              {(['pdf', 'docx', 'json', 'txt', 'srt', 'vtt'] as const).map((f) => (
                <Button
                  key={f}
                  variant="outline"
                  size="sm"
                  onClick={() => downloadSnapshot(f)}
                >
                  {f.toUpperCase()}
                </Button>
              ))}
            </div>
          </div>
        </CardHeader>
        <CardBody>
          {partial && (
            <p className="mb-3 rounded-lg border border-dashed border-border bg-surface-2/60 p-3 text-sm italic text-muted-fg">
              {partial}
              <span className="ml-0.5 inline-block w-[1ch] animate-pulse">▍</span>
            </p>
          )}
          {segments.length === 0 && !partial ? (
            <p className="py-8 text-center text-sm text-muted-fg">{t('empty')}</p>
          ) : segments.length === 0 ? null : (
            <ol
              ref={transcriptListRef}
              onScroll={onScroll}
              aria-live="polite"
              className="max-h-[45vh] space-y-2 overflow-y-auto pr-1 scroll-smooth sm:max-h-[55vh] lg:max-h-[60vh]"
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
                    s.pending && 'opacity-60'
                  )}
                >
                  <div className="flex flex-wrap items-center gap-2 text-xs text-muted-fg">
                    <span className="font-mono">{mmss(s.start_ms)}</span>
                    <span className="font-semibold text-fg">{s.speaker}</span>
                    {s.language && <span>· {s.language}</span>}
                    {typeof s.confidence === 'number' && (
                      <span className="ml-auto tabular-nums">
                        {Math.round(s.confidence * 100)}%
                      </span>
                    )}
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

      {!recording && segments.filter((s) => !s.pending).length > 0 && (
        <InsightsPanel source={{ kind: 'session', id: session.id }} />
      )}

      {!recording && segments.filter((s) => !s.pending).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t('protocol.sectionTitle')}</CardTitle>
            <CardDescription>{t('protocol.hint')}</CardDescription>
          </CardHeader>
          <CardBody className="space-y-4">
            <TemplateGallery
              templates={templates}
              selectedId={templateId}
              onSelect={setTemplateId}
              onCreated={(tpl) => setTemplates((prev) => [...prev, tpl])}
            />
            <div className="grid gap-3 sm:grid-cols-[180px_auto] sm:items-end">
              <Field label={t('protocol.formatLabel')} htmlFor="fmt">
                <Select
                  id="fmt"
                  value={protoFormat}
                  onChange={(e) => setProtoFormat(e.target.value as ProtocolFormat)}
                >
                  <option value="markdown">Markdown</option>
                  <option value="docx">DOCX</option>
                  <option value="pdf">PDF</option>
                </Select>
              </Field>
              <Button
                onClick={generateProtocol}
                loading={protoLoading}
                disabled={!templateId}
              >
                {protoLoading ? t('protocol.generating') : t('protocol.generateBtn')}
              </Button>
            </div>
            {protoMarkdown && (
              <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-surface-2/50 p-4 font-mono text-xs text-fg">
                {protoMarkdown}
              </pre>
            )}
          </CardBody>
        </Card>
      )}
    </div>
  );
}
