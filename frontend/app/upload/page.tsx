'use client';
import { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { UploadCloud, FileAudio, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Card, CardBody, CardHeader, CardTitle, CardDescription } from '@/components/ui/Card';
import { Input, Field, Chip, Select } from '@/components/ui/Input';
import { useToasts } from '@/components/ui/Toast';
import { jobsApi, type AsrProvider } from '@/lib/api';
import { cn } from '@/lib/cn';

const ACCEPT = '.wav,.mp3,.m4a,.ogg,.flac,.webm,audio/*';

export default function UploadPage() {
  const t = useTranslations('upload');
  const tLive = useTranslations('live');
  const router = useRouter();
  const push = useToasts((s) => s.push);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [langs, setLangs] = useState({ kk: true, ru: true, en: false });
  const [asrProvider, setAsrProvider] = useState<AsrProvider>('openai_transcribe');

  const providerHint =
    asrProvider === 'openai'
      ? tLive('providerOpenaiHint')
      : asrProvider === 'openai_transcribe'
      ? tLive('providerOpenaiTranscribeHint')
      : asrProvider === 'hf_space'
      ? tLive('providerHfSpaceHint')
      : asrProvider === 'hf_kazakh'
      ? tLive('providerHfKazakhHint')
      : asrProvider === 'local_kazakh'
      ? tLive('providerLocalKazakhHint')
      : tLive('providerLocalHint');
  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [dragging, setDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  function onPick(f: File | null) {
    if (!f) return;
    if (f.size > 500 * 1024 * 1024) {
      push('error', t('tooBig'));
      return;
    }
    setFile(f);
  }

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!file) return;
    const active = Object.entries(langs).filter(([, v]) => v).map(([k]) => k);
    if (active.length === 0) {
      push('error', t('selectLang'));
      return;
    }
    setUploading(true);
    setProgress(0);
    try {
      const r = await jobsApi.upload(
        file,
        active.join(','),
        title || undefined,
        setProgress,
        asrProvider,
      );
      push('success', t('queued'));
      router.push(`/session/${r.data.job_id}`);
    } catch (err: any) {
      push('error', err?.response?.data?.detail || t('error'));
      setUploading(false);
    }
  }

  return (
    <div className="mx-auto w-full max-w-2xl space-y-6">
      <header className="space-y-1">
        <h1 className="text-2xl font-semibold tracking-tight">{t('title')}</h1>
        <p className="text-muted-fg">{t('subtitle')}</p>
      </header>

      <form onSubmit={onSubmit} className="space-y-6">
        <div
          role="button"
          tabIndex={0}
          aria-label={t('dropzoneAria')}
          onClick={() => !file && inputRef.current?.click()}
          onKeyDown={(e) => {
            if (!file && (e.key === 'Enter' || e.key === ' ')) {
              e.preventDefault();
              inputRef.current?.click();
            }
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragging(true);
          }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragging(false);
            onPick(e.dataTransfer.files[0] ?? null);
          }}
          className={cn(
            'relative flex flex-col items-center justify-center gap-3 rounded-2xl border-2 border-dashed p-10 text-center transition-colors',
            'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring/40',
            dragging
              ? 'border-primary bg-primary-soft'
              : file
              ? 'border-border bg-surface-1'
              : 'border-border bg-surface-1 hover:border-primary/50 hover:bg-surface-2/40 cursor-pointer'
          )}
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            onChange={(e) => onPick(e.target.files?.[0] ?? null)}
            className="sr-only"
          />

          {file ? (
            <div className="flex w-full items-center gap-3 text-left">
              <div className="flex size-10 items-center justify-center rounded-lg bg-primary-soft text-primary">
                <FileAudio className="size-5" aria-hidden />
              </div>
              <div className="min-w-0 flex-1">
                <p className="truncate text-sm font-medium">{file.name}</p>
                <p className="text-xs text-muted-fg">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
              </div>
              {!uploading && (
                <button
                  type="button"
                  onClick={() => setFile(null)}
                  className="rounded-md p-1.5 text-muted-fg transition-colors hover:bg-muted-bg hover:text-danger"
                  aria-label={t('reset')}
                >
                  <X className="size-4" />
                </button>
              )}
            </div>
          ) : (
            <>
              <div className="flex size-12 items-center justify-center rounded-full bg-primary-soft text-primary">
                <UploadCloud className="size-6" aria-hidden />
              </div>
              <div className="space-y-1">
                <p className="text-sm font-medium text-fg">{t('dropzone')}</p>
                <p className="text-xs text-muted-fg">{t('formats')}</p>
              </div>
            </>
          )}
        </div>

        <Field label={t('titleLabel')} htmlFor="title">
          <Input
            id="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={t('titlePlaceholder')}
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
          <p className="text-xs text-muted-fg">{t('languagesHint')}</p>
        </fieldset>

        <Field label={tLive('providerLabel')} htmlFor="asr" hint={providerHint}>
          <Select
            id="asr"
            value={asrProvider}
            onChange={(e) => setAsrProvider(e.target.value as AsrProvider)}
          >
            <option value="openai_transcribe">{tLive('providerOpenaiTranscribe')}</option>
            <option value="openai">{tLive('providerOpenai')}</option>
            <option value="hf_space">{tLive('providerHfSpace')}</option>
            <option value="hf_kazakh">{tLive('providerHfKazakh')}</option>
            <option value="local_kazakh">{tLive('providerLocalKazakh')}</option>
            <option value="local">{tLive('providerLocal')}</option>
          </Select>
        </Field>

        {uploading && (
          <div className="space-y-1.5" aria-live="polite">
            <div
              className="h-1.5 overflow-hidden rounded-full bg-muted-bg"
              role="progressbar"
              aria-label={t('uploading', { pct: progress })}
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={progress}
            >
              <div
                className="h-full rounded-full bg-primary transition-all duration-300 ease-out"
                style={{ width: `${progress}%` }}
              />
            </div>
            <p className="text-xs text-muted-fg">{t('uploading', { pct: progress })}</p>
          </div>
        )}

        <div className="flex items-center gap-3 pt-1">
          <Button type="submit" loading={uploading} disabled={!file}>
            {t('submit')}
          </Button>
          {file && !uploading && (
            <Button type="button" variant="ghost" onClick={() => setFile(null)}>
              {t('reset')}
            </Button>
          )}
        </div>
      </form>
    </div>
  );
}
