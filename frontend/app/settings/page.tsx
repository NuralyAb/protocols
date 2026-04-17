import { getTranslations } from 'next-intl/server';
import { Cog, User, FileText, Accessibility } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardBody, Badge } from '@/components/ui/Card';

export default async function SettingsPage() {
  const t = await getTranslations('nav');

  const groups = [
    {
      icon: User,
      title: 'Profile',
      description: 'Name, email, and authentication preferences.',
    },
    {
      icon: FileText,
      title: 'Protocol templates',
      description: 'Manage templates used for protocol generation.',
    },
    {
      icon: Accessibility,
      title: 'Accessibility defaults',
      description: 'Persistent caption size and contrast preferences.',
    },
  ];

  return (
    <div className="mx-auto w-full max-w-3xl space-y-6">
      <header className="flex items-center gap-3">
        <span
          aria-hidden
          className="flex size-9 items-center justify-center rounded-lg bg-surface-2 text-muted-fg"
        >
          <Cog className="size-4" />
        </span>
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{t('settings')}</h1>
          <p className="text-sm text-muted-fg">Workspace, templates, and accessibility.</p>
        </div>
      </header>

      <ul className="grid gap-3 sm:grid-cols-2">
        {groups.map(({ icon: Icon, title, description }) => (
          <li key={title}>
            <Card>
              <CardBody className="flex items-start gap-4">
                <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary-soft text-primary">
                  <Icon className="size-4" aria-hidden />
                </div>
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <h2 className="text-sm font-semibold">{title}</h2>
                    <Badge tone="neutral">Soon</Badge>
                  </div>
                  <p className="text-sm text-muted-fg">{description}</p>
                </div>
              </CardBody>
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}
