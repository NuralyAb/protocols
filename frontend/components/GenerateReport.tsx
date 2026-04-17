'use client';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Sparkles, FileText } from 'lucide-react';
import { jobsApi, sessionsApi, type ProtocolFormat, type ProtocolTemplate } from '@/lib/api';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardBody,
  CardFooter,
} from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { Field, Select } from '@/components/ui/Input';
import { useToasts } from '@/components/ui/Toast';
import { TemplateGallery } from '@/components/TemplateGallery';

export function GenerateReport({
  jobId,
  title,
  hasTranscript,
}: {
  jobId: string;
  title?: string | null;
  hasTranscript: boolean;
}) {
  const t = useTranslations('session.report');
  const push = useToasts((s) => s.push);
  const [templates, setTemplates] = useState<ProtocolTemplate[]>([]);
  const [templateId, setTemplateId] = useState<string>('');
  const [format, setFormat] = useState<ProtocolFormat>('pdf');
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<string>('');

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

  async function onGenerate() {
    if (!templateId || !hasTranscript) return;
    setLoading(true);
    setPreview('');
    try {
      const r = await jobsApi.generateProtocol(jobId, templateId, format);
      const blob = r.data as Blob;
      const safe = (title || 'protocol').replace(/[^\p{L}\p{N}_.-]+/gu, '_');

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
      push('success', t('done'));
    } catch (e: any) {
      let msg = t('error');
      const data = e?.response?.data;
      if (data) {
        try {
          const text = data instanceof Blob ? await data.text() : JSON.stringify(data);
          msg = JSON.parse(text)?.detail || msg;
        } catch {}
      }
      push('error', msg);
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Sparkles className="size-4 text-primary" aria-hidden />
          {t('title')}
        </CardTitle>
        <CardDescription>{t('description')}</CardDescription>
      </CardHeader>
      <CardBody className="space-y-4">
        {!hasTranscript ? (
          <p className="rounded-lg border border-dashed border-border bg-surface-2/50 p-4 text-sm text-muted-fg">
            {t('empty')}
          </p>
        ) : (
          <>
            <TemplateGallery
              templates={templates}
              selectedId={templateId}
              onSelect={setTemplateId}
              onCreated={(tpl) => setTemplates((prev) => [...prev, tpl])}
            />
            <div className="grid gap-3 sm:grid-cols-[180px_1fr] sm:items-end">
              <Field label={t('formatLabel')} htmlFor="fmt">
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
            </div>
          </>
        )}
      </CardBody>
      {hasTranscript && (
        <CardFooter className="justify-end">
          <Button onClick={onGenerate} loading={loading} disabled={!templateId}>
            {!loading && <FileText />}
            {loading ? t('generating') : t('generateBtn')}
          </Button>
        </CardFooter>
      )}
      {preview && (
        <div className="border-t border-border px-5 py-4">
          <pre className="max-h-[60vh] overflow-auto whitespace-pre-wrap rounded-lg border border-border bg-surface-2/50 p-4 font-mono text-xs text-fg">
            {preview}
          </pre>
        </div>
      )}
    </Card>
  );
}
