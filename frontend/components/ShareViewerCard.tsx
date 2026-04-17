'use client';
import { useEffect, useState } from 'react';
import { useTranslations } from 'next-intl';
import { QrCode, Copy, RefreshCw, Check } from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { sessionsApi } from '@/lib/api';
import { Button } from '@/components/ui/Button';
import { useToasts } from '@/components/ui/Toast';

export function ShareViewerCard({ sessionId }: { sessionId: string }) {
  const t = useTranslations('live.share');
  const push = useToasts((s) => s.push);
  const [token, setToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [copied, setCopied] = useState(false);

  const origin = typeof window !== 'undefined' ? window.location.origin : '';
  const url = token ? `${origin}/public/session/${sessionId}?token=${token}` : '';

  async function ensureToken(rotate = false) {
    setLoading(true);
    try {
      const r = await sessionsApi.mintViewerToken(sessionId, { rotate });
      setToken(r.data.viewer_token);
    } catch (e: any) {
      push('error', e?.response?.data?.detail || t('error'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    ensureToken(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sessionId]);

  async function copy() {
    if (!url) return;
    try {
      await navigator.clipboard.writeText(url);
      setCopied(true);
      setTimeout(() => setCopied(false), 1800);
    } catch {
      push('error', t('copyFailed'));
    }
  }

  return (
    <div className="rounded-xl border border-border bg-surface-1 p-4 sm:p-5">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
        <div
          aria-hidden={!url}
          className="flex size-32 shrink-0 items-center justify-center rounded-lg bg-surface-2 p-2 sm:size-36"
        >
          {url ? (
            <QRCodeSVG value={url} size={128} level="M" includeMargin={false} />
          ) : (
            <QrCode className="size-10 text-muted-fg" />
          )}
        </div>
        <div className="min-w-0 flex-1 space-y-2">
          <div className="space-y-1">
            <h3 className="text-sm font-semibold">{t('title')}</h3>
            <p className="text-xs text-muted-fg">{t('hint')}</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <input
              type="text"
              readOnly
              value={url}
              aria-label={t('linkLabel')}
              className="min-w-0 flex-1 rounded-md border border-border bg-surface-2 px-2 py-1 font-mono text-xs text-fg"
              onFocus={(e) => e.currentTarget.select()}
            />
            <Button size="sm" variant="outline" onClick={copy} disabled={!url}>
              {copied ? <Check /> : <Copy />}
              {copied ? t('copied') : t('copy')}
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={() => ensureToken(true)}
              loading={loading}
              title={t('rotate')}
              aria-label={t('rotate')}
            >
              <RefreshCw />
              <span className="sr-only sm:not-sr-only">{t('rotate')}</span>
            </Button>
          </div>
        </div>
      </div>
    </div>
  );
}
