'use client';
import { useMemo, useState } from 'react';
import { useTranslations } from 'next-intl';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Card } from '@/components/ui/Card';
import { useToasts } from '@/components/ui/Toast';
import { jobsApi, type Participant } from '@/lib/api';

type Row = {
  diarization_id: string;
  label: string;
  role: string;
};

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

  if (rows.length === 0) return <p className="text-muted">{t('empty')}</p>;

  return (
    <Card>
      <h3 className="mb-3 font-medium">{t('title')}</h3>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] text-sm">
          <thead className="text-xs text-muted">
            <tr>
              <th className="py-1 text-left">{t('id')}</th>
              <th className="py-1 text-left">{t('label')}</th>
              <th className="py-1 text-left">{t('role')}</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={r.diarization_id} className="border-t border-border">
                <td className="py-2 font-mono text-xs text-muted">{r.diarization_id}</td>
                <td className="py-2 pr-2">
                  <Input value={r.label} onChange={(e) => update(i, { label: e.target.value })} />
                </td>
                <td className="py-2 pr-2">
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
      </div>
      <div className="mt-3">
        <Button size="sm" loading={saving} onClick={save}>
          {t('save')}
        </Button>
      </div>
    </Card>
  );
}
