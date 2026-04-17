'use client';
import { useTranslations } from 'next-intl';
import { Download } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { jobsApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';

const FORMATS = ['pdf', 'docx', 'json', 'txt', 'srt', 'vtt'] as const;

export function ExportMenu({ jobId, title }: { jobId: string; title?: string | null }) {
  const t = useTranslations('session.export');
  const token = useAuth((s) => s.token);

  async function download(format: (typeof FORMATS)[number]) {
    const res = await fetch(jobsApi.exportUrl(jobId, format), {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${title || 'protocol'}.${format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div
      className="flex flex-wrap items-center gap-1.5 rounded-lg border border-border bg-surface-1 p-1"
      role="group"
      aria-label={t('aria')}
    >
      <span className="flex items-center gap-1.5 px-2 text-xs font-medium text-muted-fg">
        <Download className="size-3.5" aria-hidden />
        Export
      </span>
      {FORMATS.map((f) => (
        <Button
          key={f}
          variant="ghost"
          size="sm"
          onClick={() => download(f)}
          className="h-7 px-2.5 text-xs"
        >
          {f.toUpperCase()}
        </Button>
      ))}
    </div>
  );
}
