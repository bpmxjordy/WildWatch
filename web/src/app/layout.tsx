import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/next";
import Navbar from "@/components/Navbar";
import BootSplash from "@/components/BootSplash";
import Providers from "@/components/Providers";
import "./globals.css";

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL || "https://thewildwatch.vercel.app"
  ),
  title: "WildWatch — Live Wildlife Detection",
  description:
    "Browse wildlife livestreams with real-time AI species detection powered by SpeciesNet.",
  icons: {
    icon: "/icon.svg",
    apple: "/icon.svg",
  },
  openGraph: {
    title: "WildWatch — Live Wildlife Detection",
    description:
      "Browse wildlife livestreams with real-time AI species detection.",
    siteName: "WildWatch",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Source+Serif+4:ital,opsz,wght@0,8..60,300..700;1,8..60,300..600&family=DM+Sans:opsz,wght@9..40,300..700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
          crossOrigin=""
        />
        <link
          rel="stylesheet"
          href="https://unpkg.com/leaflet.markercluster@1.5.3/dist/MarkerCluster.css"
          crossOrigin=""
        />
        {/*
          Decide whether the splash runs BEFORE first paint.

          It can't be decided in React: the server has no access to
          sessionStorage, so it always renders the overlay, and by the time
          hydration could remove it the browser has already painted it — a
          flash of splash on every repeat load. A blocking inline script sets
          the class first, and the CSS keys off it, so a skipped splash is
          never painted at all.
        */}
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{
  var force = location.search.indexOf('splash') > -1;
  var nav = performance.getEntriesByType('navigation')[0];
  var isReload = nav && nav.type === 'reload';
  var seen = sessionStorage.getItem('ww-splash-seen');
  var reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (force || (!reduced && !isReload && !seen)) {
    document.documentElement.className += ' ww-splash-on';
    sessionStorage.setItem('ww-splash-seen','1');
  }
}catch(e){}})();`,
          }}
        />
      </head>
      <body>
        <Providers>
          <BootSplash />
          <Navbar />
          <main className="mx-auto max-w-page px-7 py-9">{children}</main>
          <footer className="border-t border-rule mt-12">
            <div className="mx-auto max-w-page px-7 py-8 flex flex-col sm:flex-row items-center justify-between gap-4">
              <p className="font-mono text-[10.5px] uppercase tracking-[0.14em] text-muted">
                WildWatch — AI-powered wildlife detection
              </p>
              <a
                href="mailto:JordanCartwright2000@gmail.com"
                className="font-mono text-[10.5px] tracking-[0.06em] text-muted hover:text-ink transition-colors"
              >
                JordanCartwright2000@gmail.com
              </a>
            </div>
          </footer>
        </Providers>
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
