'use client';
import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Users } from 'lucide-react';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card, CardHeader, CardTitle, CardBody, CardFooter } from '@/components/ui/Card';
import { useToasts } from '@/components/ui/Toast';
import { jobsApi, type Participant } from '@/lib/api';

type Row = { diarization_id: string; label: string; role: string };

export function SpeakerEditor({
  jobId,
  participants,
  onSaved,
}: {
  jobId: string;
  participants: Participant[];
  onSaved?: () => void;
}) {
  const t = useTranslations('session.speakers');
  const push = useToasts((s) => s.push);
  const initial = useMemo<Row[]>(
    () =>
      participants.map((p) => ({
        diarization_id: p.id,
        label: p.label || p.id,
        role: p.role || '',
      })),
    [participants]
  );
  const [rows, setRows] = useState<Row[]>(initial);
  const [saving, setSaving] = useState(false);

  function update(i: number, patch: Partial<Row>) {
    setRows((rs) => rs.map((r, idx) => (idx === i ? { ...r, ...patch } : r)));
  }

  async function save() {
    setSaving(true);
    try {
      await jobsApi.patchSpeakers(
        jobId,
        rows.map((r) => ({
          diarization_id: r.diarization_id,
          label: r.label || undefined,
          role: r.role || undefined,
        }))
      );
      push('success', t('saved'));
      onSaved?.();
    } catch (e: any) {
      push('error', e?.response?.data?.detail || t('error'));
    } finally {
      setSaving(false);
    }
  }

  if (rows.length === 0) return <p className="text-muted-fg">{t('empty')}</p>;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Users className="size-4 text-muted-fg" aria-hidden />
          {t('title')}
        </CardTitle>
      </CardHeader>
      <CardBody className="overflow-x-auto">
        <table className="w-full min-w-[480px] text-sm">
          <thead>
            <tr className="border-b border-border text-left text-xs uppercase tracking-wide text-muted-fg">
              <th className="pb-2 pr-3 font-medium">{t('id')}</th>
              <th className="pb-2 pr-3 font-medium">{t('label')}</th>
              <th className="pb-2 font-medium">{t('role')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((r, i) => (
              <tr key={r.diarization_id}>
                <td className="py-2 pr-3 align-middle">
                  <span className="inline-flex items-center rounded-md bg-surface-2 px-2 py-1 font-mono text-xs text-muted-fg">
                    {r.diarization_id}
                  </span>
                </td>
                <td className="py-2 pr-3">
                  <Input
                    value={r.label}
                    onChange={(e) => update(i, { label: e.target.value })}
                  />
                </td>
                <td className="py-2">
                  <Input
                    value={r.role}
                    placeholder={t('rolePh')}
                    onChange={(e) => update(i, { role: e.target.value })}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </CardBody>
      <CardFooter className="justify-end">
        <Button size="sm" loading={saving} onClick={save}>
          {t('save')}
        </Button>
      </CardFooter>
    </Card>
  );
}
