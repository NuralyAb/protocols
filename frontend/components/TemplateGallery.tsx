'use client';
import { useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Check, FileText, Plus, Upload, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input, Field, Select } from '@/components/ui/Input';
import { useToasts } from '@/components/ui/Toast';
import { sessionsApi, type ProtocolTemplate } from '@/lib/api';
import { cn } from '@/lib/cn';

function LanguageBadge({ lang }: { lang: string }) {
  return (
    <span className="inline-flex items-center rounded-full border border-border bg-surface-2/60 px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide text-muted-fg">
      {lang}
    </span>
  );
}

export function TemplateGallery({
  templates,
  selectedId,
  onSelect,
  onCreated,
}: {
  templates: ProtocolTemplate[];
  selectedId: string;
  onSelect: (id: string) => void;
  onCreated?: (tpl: ProtocolTemplate) => void;
}) {
  const t = useTranslations('templates');
  const push = useToasts((s) => s.push);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [language, setLanguage] = useState('ru');
  const [body, setBody] = useState('');
  const [file, setFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  function resetForm() {
    setName('');
    setDescription('');
    setLanguage('ru');
    setBody('');
    setFile(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
  }

  async function onUpload(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return push('error', t('nameRequired'));
    if (!file && !body.trim()) return push('error', t('bodyRequired'));
    setUploading(true);
    try {
      const r = await sessionsApi.uploadTemplate({
        name: name.trim(),
        description: description.trim() || undefined,
        language,
        file: file || undefined,
        body: file ? undefined : body,
      });
      push('success', t('uploaded'));
      onCreated?.(r.data);
      onSelect(r.data.id);
      resetForm();
      setDialogOpen(false);
    } catch (err: any) {
      push('error', err?.response?.data?.detail || t('uploadError'));
    } finally {
      setUploading(false);
    }
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-medium text-fg">{t('galleryLabel')}</span>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => setDialogOpen(true)}
        >
          <Plus className="size-4" aria-hidden />
          {t('addCustom')}
        </Button>
      </div>

      {templates.length === 0 ? (
        <p className="rounded-lg border border-dashed border-border bg-surface-2/50 p-4 text-sm text-muted-fg">
          {t('empty')}
        </p>
      ) : (
        <div
          role="radiogroup"
          aria-label={t('galleryLabel')}
          className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3"
        >
          {templates.map((tpl) => {
            const active = tpl.id === selectedId;
            return (
              <button
                key={tpl.id}
                type="button"
                role="radio"
                aria-checked={active}
                onClick={() => onSelect(tpl.id)}
                className={cn(
                  'group relative flex h-full flex-col gap-2 rounded-xl border bg-surface-1 p-4 text-left shadow-sm transition',
                  'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary',
                  active
                    ? 'border-primary ring-2 ring-primary/30'
                    : 'border-border hover:border-primary/60 hover:shadow-md'
                )}
              >
                <div className="flex items-start justify-between gap-2">
                  <span
                    className={cn(
                      'flex size-8 items-center justify-center rounded-lg',
                      active ? 'bg-primary text-primary-fg' : 'bg-surface-2 text-muted-fg'
                    )}
                    aria-hidden
                  >
                    <FileText className="size-4" />
                  </span>
                  {active && (
                    <span
                      className="flex size-5 items-center justify-center rounded-full bg-primary text-primary-fg"
                      aria-hidden
                    >
                      <Check className="size-3" />
                    </span>
                  )}
                </div>
                <div className="flex-1">
                  <div className="text-sm font-semibold text-fg">{tpl.name}</div>
                  {tpl.description && (
                    <div className="mt-1 line-clamp-3 text-xs text-muted-fg">
                      {tpl.description}
                    </div>
                  )}
                </div>
                <div className="flex items-center justify-between">
                  <LanguageBadge lang={tpl.language} />
                  {tpl.id.startsWith('custom-') && (
                    <span className="text-[10px] uppercase tracking-wide text-primary/80">
                      {t('customBadge')}
                    </span>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      )}

      {dialogOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="tpl-upload-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
          onClick={(e) => {
            if (e.target === e.currentTarget) setDialogOpen(false);
          }}
        >
          <form
            onSubmit={onUpload}
            className="w-full max-w-lg space-y-4 rounded-2xl border border-border bg-surface-1 p-6 shadow-xl"
          >
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 id="tpl-upload-title" className="text-lg font-semibold">
                  {t('uploadTitle')}
                </h2>
                <p className="mt-1 text-xs text-muted-fg">{t('uploadHint')}</p>
              </div>
              <button
                type="button"
                aria-label="Close"
                onClick={() => setDialogOpen(false)}
                className="text-muted-fg hover:text-fg"
              >
                <X className="size-5" />
              </button>
            </div>

            <Field label={t('nameLabel')} htmlFor="tpl-name">
              <Input
                id="tpl-name"
                required
                maxLength={120}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={t('namePlaceholder')}
              />
            </Field>

            <Field label={t('descriptionLabel')} htmlFor="tpl-desc">
              <Input
                id="tpl-desc"
                maxLength={500}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            </Field>

            <Field label={t('languageLabel')} htmlFor="tpl-lang">
              <Select
                id="tpl-lang"
                value={language}
                onChange={(e) => setLanguage(e.target.value)}
              >
                <option value="ru">RU</option>
                <option value="kk">KK</option>
                <option value="en">EN</option>
              </Select>
            </Field>

            <Field label={t('fileLabel')} htmlFor="tpl-file">
              <input
                ref={fileInputRef}
                id="tpl-file"
                type="file"
                accept=".md,.txt,text/markdown,text/plain"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
                className="block w-full text-sm file:mr-3 file:rounded-md file:border-0 file:bg-primary file:px-3 file:py-1.5 file:text-primary-fg hover:file:bg-primary/90"
              />
            </Field>

            {!file && (
              <Field label={t('bodyLabel')} htmlFor="tpl-body">
                <textarea
                  id="tpl-body"
                  rows={8}
                  value={body}
                  onChange={(e) => setBody(e.target.value)}
                  placeholder={t('bodyPlaceholder')}
                  className="w-full rounded-lg border border-border bg-surface-2/50 p-3 font-mono text-xs text-fg focus:border-primary focus:outline-none"
                />
              </Field>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="secondary" onClick={() => setDialogOpen(false)}>
                {t('cancel')}
              </Button>
              <Button type="submit" loading={uploading}>
                {!uploading && <Upload className="size-4" />}
                {uploading ? t('uploading') : t('submit')}
              </Button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
