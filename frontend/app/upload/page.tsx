'use client';
import { useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Input } from '@/components/ui/Input';
import { useToasts } from '@/components/ui/Toast';
import { jobsApi } from '@/lib/api';

const ACCEPT = '.wav,.mp3,.m4a,.ogg,.flac,.webm,audio/*';

export default function UploadPage() {
  const t = useTranslations('upload');
  const router = useRouter();
  const push = useToasts((s) => s.push);
  const [file, setFile] = useState<File | null>(null);
  const [title, setTitle] = useState('');
  const [langs, setLangs] = useState({ kk: true, ru: true, en: false });
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
      const r = await jobsApi.upload(file, active.join(','), title || undefined, setProgress);
      push('success', t('queued'));
      router.push(`/session/${r.data.job_id}`);
    } catch (err: any) {
      push('error', err?.response?.data?.detail || t('error'));
      setUploading(false);
    }
  }

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <header>
        <h1 className="text-2xl font-semibold">{t('title')}</h1>
        <p className="text-muted">{t('subtitle')}</p>
      </header>

      <form onSubmit={onSubmit} className="space-y-5">
        <Card
          role="button"
          tabIndex={0}
          aria-label={t('dropzoneAria')}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
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
          className={
            'cursor-pointer text-center transition ' +
            (dragging ? 'border-accent bg-accent/5' : '')
          }
        >
          <input
            ref={inputRef}
            type="file"
            accept={ACCEPT}
            onChange={(e) => onPick(e.target.files?.[0] ?? null)}
            className="sr-only"
          />
          <p className="text-base font-medium">{file ? file.name : t('dropzone')}</p>
          <p className="mt-1 text-xs text-muted">{t('formats')}</p>
          {file && (
            <p className="mt-1 text-xs text-muted">
              {(file.size / 1024 / 1024).toFixed(1)} MB
            </p>
          )}
        </Card>

        <label className="block">
          <span className="mb-1 block text-sm">{t('titleLabel')}</span>
          <Input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder={t('titlePlaceholder')}
          />
        </label>

        <fieldset className="space-y-2">
          <legend className="text-sm font-medium">{t('languages')}</legend>
          <div className="flex gap-4">
            {(['kk', 'ru', 'en'] as const).map((k) => (
              <label key={k} className="inline-flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={langs[k]}
                  onChange={(e) => setLangs((s) => ({ ...s, [k]: e.target.checked }))}
                />
                <span>{k.toUpperCase()}</span>
              </label>
            ))}
          </div>
          <p className="text-xs text-muted">{t('languagesHint')}</p>
        </fieldset>

        {uploading && (
          <div className="space-y-1">
            <div className="h-2 overflow-hidden rounded-full bg-muted/20">
              <div className="h-full bg-accent transition-all" style={{ width: `${progress}%` }} />
            </div>
            <p className="text-xs text-muted">{t('uploading', { pct: progress })}</p>
          </div>
        )}

        <div className="flex gap-3">
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
