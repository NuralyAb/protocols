'use client';
import { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Mic, Square, Radio } from 'lucide-react';
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
  type AsrProvider,
  type LiveSession,
  type ProtocolFormat,
  type ProtocolTemplate,
} from '@/lib/api';
import { startMic, type MicStream } from '@/lib/mic';
import { Waveform } from '@/components/Waveform';
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
  openai: 'OpenAI',
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
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">
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
        <div className="flex items-center gap-2">
          {recording ? (
            <>
              {reconnecting ? (
                <Badge tone="warning" dot>{t('reconnecting')}</Badge>
              ) : (
                <Badge tone="danger" dot>{t('recording')}</Badge>
              )}
              <Button variant="danger" onClick={stop}>
                <Square /> {t('stop')}
              </Button>
            </>
          ) : (
            <Button onClick={start} loading={connecting}>
              <Mic /> {t('start')}
            </Button>
          )}
        </div>
      </header>

      {recording && micRef.current && (
        <Waveform
          active={recording && !reconnecting}
          read={(bins) => micRef.current!.getLevels(bins)}
        />
      )}

      <Card>
        <CardHeader className="flex-row flex-wrap items-center justify-between gap-3">
          <div>
            <CardTitle>{t('liveTranscript')}</CardTitle>
            <CardDescription>Snapshot export in any format.</CardDescription>
          </div>
          <div className="flex flex-wrap gap-1.5">
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
              className="max-h-[60vh] space-y-2 overflow-y-auto pr-1 scroll-smooth"
            >
              {segments.map((s) => (
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
                </li>
              ))}
            </ol>
          )}
        </CardBody>
      </Card>

      {!recording && segments.filter((s) => !s.pending).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>{t('protocol.sectionTitle')}</CardTitle>
            <CardDescription>{t('protocol.hint')}</CardDescription>
          </CardHeader>
          <CardBody className="space-y-4">
            <div className="grid gap-3 sm:grid-cols-[1fr_auto_auto] sm:items-end">
              <Field label={t('protocol.templateLabel')} htmlFor="tpl">
                <Select
                  id="tpl"
                  value={templateId}
                  onChange={(e) => setTemplateId(e.target.value)}
                >
                  {templates.length === 0 && (
                    <option value="">{t('protocol.pickTemplate')}</option>
                  )}
                  {templates.map((tpl) => (
                    <option key={tpl.id} value={tpl.id}>
                      {tpl.name}
                    </option>
                  ))}
                </Select>
              </Field>
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
            {templateId && (
              <p className="text-xs text-muted-fg">
                {templates.find((x) => x.id === templateId)?.description}
              </p>
            )}
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
