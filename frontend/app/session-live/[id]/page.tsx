'use client';
import { useCallback, useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { useParams } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { AlertTriangle, Download, FileText, Mic, Radio, Sparkles } from 'lucide-react';
import {
  sessionsApi,
  type JobResult,
  type LiveSession,
  type Participant,
  type ProtocolFormat,
  type ProtocolTemplate,
  type TranscriptSegment,
} from '@/lib/api';

type TranscriptLang = 'original' | 'ru' | 'kk' | 'en';
import {
  Badge,
  Card,
  CardBody,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Field, Select } from '@/components/ui/Input';
import { useAuth } from '@/lib/auth';
import { useToasts } from '@/components/ui/Toast';
import { TranscriptView } from '@/components/TranscriptView';
import { SpeakerEditor } from '@/components/SpeakerEditor';
import { TemplateGallery } from '@/components/TemplateGallery';

type AudioInfo = {
  url: string;
  download_url: string;
  filename: string;
  content_type: string;
};

export default function LiveSessionPage() {
  const { id } = useParams<{ id: string }>();
  const t = useTranslations('session');
  const tLive = useTranslations('live');
  const token = useAuth((s) => s.token);
  const push = useToasts((s) => s.push);

  const [session, setSession] = useState<LiveSession | null>(null);
  const [result, setResult] = useState<JobResult | null>(null);
  const [audio, setAudio] = useState<AudioInfo | null>(null);
  const [audioError, setAudioError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const [activeLang, setActiveLang] = useState<TranscriptLang>('original');
  const [translations, setTranslations] = useState<Record<'ru' | 'kk' | 'en', TranscriptSegment[] | null>>({
    ru: null,
    kk: null,
    en: null,
  });
  const [translating, setTranslating] = useState<TranscriptLang | null>(null);

  const [templates, setTemplates] = useState<ProtocolTemplate[]>([]);
  const [templateId, setTemplateId] = useState<string>('');
  const [format, setFormat] = useState<ProtocolFormat>('pdf');
  const [generating, setGenerating] = useState(false);
  const [preview, setPreview] = useState('');

  const load = useCallback(async () => {
    try {
      const [s, snap] = await Promise.all([sessionsApi.get(id), sessionsApi.snapshot(id)]);
      setSession(s.data);
      setResult(snap.data);
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
    if (!session) return;
    if (!session.audio_key) {
      setAudio(null);
      setAudioError(null);
      return;
    }
    let alive = true;
    sessionsApi
      .audio(id)
      .then((r) => {
        if (alive) setAudio(r.data);
      })
      .catch((e: any) => {
        if (alive) setAudioError(e?.response?.data?.detail || 'Cannot load audio');
      });
    return () => {
      alive = false;
    };
  }, [id, session]);

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

  const speakers = useMemo(() => {
    const map: Record<string, Participant> = {};
    result?.protocol?.participants?.forEach((p) => {
      map[p.id] = p;
    });
    return map;
  }, [result]);

  async function onSelectLang(lang: TranscriptLang) {
    setActiveLang(lang);
    if (lang === 'original') return;
    if (translations[lang]) return;
    setTranslating(lang);
    try {
      const r = await sessionsApi.translate(id, lang);
      setTranslations((prev) => ({ ...prev, [lang]: r.data.segments }));
    } catch (e: any) {
      push('error', e?.response?.data?.detail || 'Translation failed');
      setActiveLang('original');
    } finally {
      setTranslating(null);
    }
  }

  const displayResult = useMemo<JobResult | null>(() => {
    if (!result) return null;
    if (activeLang === 'original') return result;
    const segs = translations[activeLang];
    if (!segs) return result;
    return { ...result, transcript: segs };
  }, [result, activeLang, translations]);

  async function onGenerate() {
    if (!templateId || !result) return;
    setGenerating(true);
    setPreview('');
    try {
      const r = await sessionsApi.generateProtocol(id, templateId, format);
      const blob = r.data as Blob;
      const safe = (session?.title || 'protocol').replace(/[^\p{L}\p{N}_.-]+/gu, '_');
      if (format === 'markdown') {
        setPreview(await blob.text());
      } else {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${safe}.${format}`;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      }
      push('success', t('report.done'));
    } catch (e: any) {
      let msg = t('report.error');
      const data = e?.response?.data;
      if (data) {
        try {
          const text = data instanceof Blob ? await data.text() : JSON.stringify(data);
          msg = JSON.parse(text)?.detail || msg;
        } catch {}
      }
      push('error', msg);
    } finally {
      setGenerating(false);
    }
  }

  if (loading) {
    return <div className="h-32 animate-pulse rounded-xl border border-border bg-surface-2/50" />;
  }
  if (!session || !result) {
    return (
      <Card>
        <CardBody>
          <p className="text-sm text-muted-fg">Session not found.</p>
        </CardBody>
      </Card>
    );
  }

  const hasTranscript = (result.transcript?.length || 0) > 0;

  return (
    <div className="space-y-6">
      <header className="space-y-2">
        <div className="flex flex-wrap items-center gap-2">
          <h1 className="text-2xl font-semibold tracking-tight">
            {session.title || `Live · ${session.id.slice(0, 8)}`}
          </h1>
          <Badge tone={session.is_active ? 'info' : 'success'} dot>
            {session.is_active ? t('status.processing') : t('status.completed')}
          </Badge>
          <span className="rounded-full border border-border bg-surface-2 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-fg">
            Live
          </span>
        </div>
        <p className="text-sm text-muted-fg">
          {new Date(session.started_at).toLocaleString()}
          {session.languages?.length ? ` · ${session.languages.join(', ')}` : ''}
          {session.asr_provider ? ` · ${session.asr_provider}` : ''}
        </p>
        {session.is_active && (
          <Link
            href="/live"
            className="inline-flex items-center gap-1.5 rounded-lg border border-primary/40 bg-primary/10 px-3 py-1.5 text-sm font-medium text-primary hover:bg-primary/15"
          >
            <Radio className="size-4" aria-hidden />
            {tLive('recording')} →
          </Link>
        )}
      </header>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Mic className="size-4 text-primary" aria-hidden />
            {t('recording.title')}
          </CardTitle>
          <CardDescription>{t('recording.description')}</CardDescription>
        </CardHeader>
        <CardBody>
          {session.is_active ? (
            <p className="rounded-lg border border-dashed border-border bg-surface-2/50 p-4 text-sm text-muted-fg">
              {tLive('recording')}…
            </p>
          ) : !session.audio_key ? (
            <p className="rounded-lg border border-dashed border-border bg-surface-2/50 p-4 text-sm text-muted-fg">
              {t('recording.unavailable')}
            </p>
          ) : audioError ? (
            <div className="flex items-center gap-2 rounded-lg border border-danger/40 bg-danger/10 p-3 text-sm text-danger">
              <AlertTriangle className="size-4" aria-hidden />
              <span>{audioError}</span>
            </div>
          ) : audio ? (
            <div className="space-y-3">
              <audio controls src={audio.url} className="w-full">
                {t('recording.unsupported')}
              </audio>
              <a
                href={audio.download_url}
                className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
                download={audio.filename}
              >
                <Download className="size-4" aria-hidden />
                {t('recording.download')}
              </a>
            </div>
          ) : (
            <div className="h-12 animate-pulse rounded-lg bg-surface-2/50" />
          )}
        </CardBody>
      </Card>

      {result.protocol?.participants?.length ? (
        <SpeakerEditor
          sessionId={id}
          participants={result.protocol.participants}
          onSaved={load}
        />
      ) : null}

      <Card>
        <CardHeader>
          <CardTitle>{t('transcript')}</CardTitle>
        </CardHeader>
        <CardBody className="space-y-3">
          <div role="tablist" className="flex flex-wrap gap-1 border-b border-border pb-2">
            {([
              ['original', 'Оригинал'],
              ['ru', 'RU'],
              ['kk', 'KK'],
              ['en', 'EN'],
            ] as const).map(([key, label]) => {
              const active = activeLang === key;
              const loading = translating === key;
              return (
                <button
                  key={key}
                  role="tab"
                  aria-selected={active}
                  type="button"
                  onClick={() => onSelectLang(key)}
                  disabled={loading}
                  className={
                    'rounded-md px-3 py-1.5 text-sm font-medium transition-colors ' +
                    (active
                      ? 'bg-primary text-primary-fg'
                      : 'text-muted-fg hover:bg-surface-2 hover:text-fg')
                  }
                >
                  {loading ? '…' : label}
                </button>
              );
            })}
          </div>
          {displayResult ? (
            <TranscriptView result={displayResult} speakers={speakers} />
          ) : null}
        </CardBody>
      </Card>

      {hasTranscript && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="size-4 text-primary" aria-hidden />
              {t('report.title')}
            </CardTitle>
            <CardDescription>{t('report.description')}</CardDescription>
          </CardHeader>
          <CardBody className="space-y-4">
            <TemplateGallery
              templates={templates}
              selectedId={templateId}
              onSelect={setTemplateId}
              onCreated={(tpl) => setTemplates((prev) => [...prev, tpl])}
            />
            <div className="flex flex-wrap items-end gap-3">
              <Field label={t('report.formatLabel')} htmlFor="fmt">
                <Select
                  id="fmt"
                  value={format}
                  onChange={(e) => setFormat(e.target.value as ProtocolFormat)}
                >
                  <option value="pdf">PDF</option>
                  <option value="docx">DOCX</option>
                  <option value="markdown">Markdown</option>
                </Select>
              </Field>
              <Button onClick={onGenerate} loading={generating} disabled={!templateId}>
                {!generating && <FileText />}
                {generating ? t('report.generating') : t('report.generateBtn')}
              </Button>
            </div>
            {preview && (
              <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-surface-2/50 p-4 font-mono text-xs text-fg">
                {preview}
              </pre>
            )}
          </CardBody>
        </Card>
      )}
    </div>
  );
}
