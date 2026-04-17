import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getMessages, getTranslations } from 'next-intl/server';
import { Navbar } from '@/components/Navbar';
import { AccessibilityBar } from '@/components/AccessibilityBar';
import { AuthGate } from '@/components/AuthGate';
import { Toaster } from '@/components/ui/Toast';
import './globals.css';

const inter = Inter({
  subsets: ['latin', 'cyrillic'],
  display: 'swap',
  variable: '--font-sans',
});

const jetbrains = JetBrains_Mono({
  subsets: ['latin'],
  display: 'swap',
  variable: '--font-mono',
});

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations('app');
  return { title: t('title'), description: t('tagline') };
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const locale = await getLocale();
  const messages = await getMessages();
  const tNav = await getTranslations('nav');
  return (
    <html lang={locale} suppressHydrationWarning className={`${inter.variable} ${jetbrains.variable}`}>
      <body className="min-h-screen antialiased">
        <NextIntlClientProvider locale={locale} messages={messages}>
          <a href="#main" className="skip-link">{tNav('skipToContent')}</a>
          <div className="shell">
            <Navbar />
            <AccessibilityBar />
            <main
              id="main"
              tabIndex={-1}
              className="container py-8 focus-visible:outline-none sm:py-10"
            >
              <AuthGate>{children}</AuthGate>
            </main>
            <footer className="border-t border-border bg-surface-1/60">
              <div className="container flex flex-wrap items-center justify-between gap-2 py-4 text-xs text-muted-fg">
                <span>© {new Date().getFullYear()} Protocol AI</span>
                <span>v0.1 · build preview</span>
              </div>
            </footer>
          </div>
          <Toaster />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
