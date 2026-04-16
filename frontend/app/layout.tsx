import type { Metadata } from 'next';
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getMessages, getTranslations } from 'next-intl/server';
import { Navbar } from '@/components/Navbar';
import { AccessibilityBar } from '@/components/AccessibilityBar';
import { AuthGate } from '@/components/AuthGate';
import { Toaster } from '@/components/ui/Toast';
import './globals.css';

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('app');
  return { title: t('title'), description: t('tagline') };
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  const messages = await getMessages();
  const tNav = await getTranslations('nav');
  return (
    <html lang={locale} suppressHydrationWarning>
      <body className="min-h-screen">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <a href="#main" className="skip-link">{tNav('skipToContent')}</a>
          <Navbar />
          <AccessibilityBar />
          <main id="main" className="mx-auto max-w-6xl px-4 py-8" tabIndex={-1}>
            <AuthGate>{children}</AuthGate>
          </main>
          <Toaster />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
