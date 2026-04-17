'use client';
import { useTranslations } from 'next-intl';
import type { JobResult, Participant, TranscriptSegment } from '@/lib/api';

function mmss(ms: number) {
  const s = Math.floor(ms / 1000);
  return `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(s % 60).padStart(2, '0')}`;
}

export function TranscriptView({
  result,
  speakers,
}: {
  result: JobResult;
  speakers: Record<string, Participant>;
}) {
  const t = useTranslations('session');
  if (!result.transcript?.length) {
    return (
      <p className="rounded-lg border border-dashed border-border bg-surface-2/40 p-6 text-center text-sm text-muted-fg">
        {t('empty')}
      </p>
    );
  }
  return (
    <ol className="space-y-2">
      {result.transcript.map((s: TranscriptSegment, i) => {
        const label = speakers[s.speaker]?.label || s.speaker;
        const role = speakers[s.speaker]?.role;
        return (
          <li
            key={i}
            className="rounded-lg border border-border bg-surface-1 p-3 transition-colors hover:border-border/80"
          >
            <div className="flex flex-wrap items-center gap-2 text-xs text-muted-fg">
              <span className="font-mono">{mmss(s.start_time)}</span>
              <span className="font-semibold text-fg">{label}</span>
              {role && <span>· {role}</span>}
              {s.language && <span>· {s.language}</span>}
              {typeof s.confidence === 'number' && (
                <span className="ml-auto tabular-nums">
                  {Math.round(s.confidence * 100)}%
                </span>
              )}
            </div>
            <p className="mt-1 captions whitespace-pre-wrap text-sm text-fg">{s.text}</p>
          </li>
        );
      })}
    </ol>
  );
}
