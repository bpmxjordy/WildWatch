import type { Metadata } from "next";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/next";
import Navbar from "@/components/Navbar";
import Providers from "@/components/Providers";
import "./globals.css";

export const metadata: Metadata = {
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
      </head>
      <body>
        <Providers>
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
