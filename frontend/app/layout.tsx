import type { Metadata } from 'next';
import { Inter, JetBrains_Mono } from 'next/font/google';
import { NextIntlClientProvider } from 'next-intl';
import { getLocale, getMessages, getTranslations } from 'next-intl/server';
import { Navbar } from '@/components/Navbar';
import { AccessibilityBar } from '@/components/AccessibilityBar';
import { AuthGate } from '@/components/AuthGate';
import { PageTransition } from '@/components/PageTransition';
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
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var p=JSON.parse(localStorage.getItem('protocol-ai:prefs')||'{}');var d=typeof p.dark==='boolean'?p.dark:window.matchMedia('(prefers-color-scheme: dark)').matches;if(d)document.documentElement.classList.add('dark');if(p.contrast)document.documentElement.classList.add('contrast-high');if(p.largeCaptions)document.documentElement.classList.add('captions-large');}catch(e){}})();`,
          }}
        />
      </head>
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
              <AuthGate>
                <PageTransition>{children}</PageTransition>
              </AuthGate>
            </main>
            <footer className="border-t border-border bg-surface-1/60">
              <div className="container flex flex-wrap items-center justify-between gap-2 py-4 text-xs text-muted-fg">
                <span>© {new Date().getFullYear()} Protocol AI</span>
                <span className="inline-flex items-center gap-2">
                  <span>{tNav('madeWith')}</span>
                  <span aria-hidden>·</span>
                  <span>KK · RU · EN</span>
                </span>
              </div>
            </footer>
          </div>
          <Toaster />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
