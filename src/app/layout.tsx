// src/app/layout.tsx
import './globals.css';
import 'katex/dist/katex.min.css';
import '@fontsource/inter/400.css';
import '@fontsource/inter/600.css';
import '@fontsource/inter/700.css';
import { Providers } from '@/app/providers';
import { getCachedSections } from '@/lib/content';
import { getRootPagesConfig } from '@/lib/content/pages-config';
import PageLayout from '@/components/PageLayout';
import { Metadata } from 'next';
import { Analytics } from '@/components/Analytics';
import { loadSiteConfig } from '@/lib/server/config';
import { PersonSchema, WebSiteSchema } from '@/components/seo';
import TTSInit from '@/components/TTSInitializer';
import SiteResume from '@/components/SiteResume';



export const metadata: Metadata = {
  alternates: {
    types: {
      'application/rss+xml': '/api/feed',
      'application/atom+xml': '/api/feed?format=atom',
      'application/json': '/api/feed?format=json',
    },
  },
};

export default async function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const sections = await getCachedSections();
  const pagesConfig = await getRootPagesConfig();
  const config = loadSiteConfig();

  const formattedSections = sections.map(section => ({
    id: section.id,
    title: section.name
  }));

  const orderedSections = pagesConfig?.nav
    ? pagesConfig.nav
        .map(navItem => formattedSections.find(s => s.id === navItem || s.id === `${navItem}.md` || s.id.replace(/\.md$/, '') === navItem))
        .filter((s): s is NonNullable<typeof s> => s !== undefined)
    : formattedSections;

  return (
    <html lang="en" suppressHydrationWarning>
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover" />
        <PersonSchema />
        <WebSiteSchema />
      </head>
      <body className="bg-white dark:bg-gray-900 text-gray-900 dark:text-gray-100" suppressHydrationWarning>
        <Analytics />
        <div style={{ fontFamily: "Inter, sans-serif" }}>
          <Providers>
            <PageLayout sections={orderedSections} config={config}>
              {children}
            </PageLayout>
          </Providers>
        </div>
        <TTSInit />
        <SiteResume />
      </body>
    </html>
  );
}
