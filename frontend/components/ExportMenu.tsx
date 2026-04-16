'use client';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/Button';
import { jobsApi } from '@/lib/api';
import { useAuth } from '@/lib/auth';

const FORMATS = ['pdf', 'docx', 'json', 'txt', 'srt', 'vtt'] as const;

export function ExportMenu({ jobId, title }: { jobId: string; title?: string | null }) {
  const t = useTranslations('session.export');
  const token = useAuth((s) => s.token);

  async function download(format: (typeof FORMATS)[number]) {
    // Need auth header — can't just use a plain <a>. Fetch, blob, anchor trick.
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
    <div className="flex flex-wrap gap-2" role="group" aria-label={t('aria')}>
      {FORMATS.map((f) => (
        <Button key={f} variant="secondary" size="sm" onClick={() => download(f)}>
          {f.toUpperCase()}
        </Button>
      ))}
    </div>
  );
}
